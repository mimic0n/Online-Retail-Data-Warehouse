"""Run with python -m etl.run_etl."""
import argparse
import json
from itertools import islice
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from . import config
from .extract import sheets, fingerprint
from .clean import clean
from .load_fact import copy_rows, load_fact
from .load_dims import load_dims
from .reconcile import reconcile

VALID_COLUMNS = 'source_file_id,source_row_id,batch_id,invoice_no,invoice_datetime,date_key,stock_code,description,customer_id,country,quantity,unit_price,line_amount,transaction_type'
RAW_COLUMNS = 'source_file_id,source_row_id,batch_id,sheet_name,invoice,stock_code,description,quantity,invoice_date,price,customer_id,country'

def process(conn, source, file_id, name, records, chunk_size):
    from psycopg2.extras import Json
    with conn:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO staging.etl_batch(source_file_id,file_name,sheet_name) VALUES(%s,%s,%s) RETURNING batch_id',(file_id,Path(source).name,name))
            batch = cur.fetchone()[0]
    read = valid = rejected = 0
    expected_totals = defaultdict(Decimal)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute('''CREATE TEMP TABLE tmp_valid (
                source_file_id char(64),source_row_id integer PRIMARY KEY,batch_id integer,invoice_no text,
                invoice_datetime timestamp,date_key integer,stock_code text,description text,customer_id text,
                country text,quantity integer,unit_price numeric(12,4),line_amount numeric(14,4),transaction_type text) ON COMMIT DROP''')
                cur.execute('CREATE TEMP TABLE tmp_raw (LIKE staging.raw_online_retail INCLUDING DEFAULTS) ON COMMIT DROP')
                while chunk := list(islice(records, chunk_size)):
                    raws, goods, errors = [], [], []
                    for row_id, sheet_name, raw in chunk:
                        read += 1
                        raws.append((file_id,row_id,batch,sheet_name,*(raw[k] for k in ['Invoice','StockCode','Description','Quantity','InvoiceDate','Price','Customer ID','Country'])))
                        try:
                            row = clean(raw)
                            goods.append((file_id,row_id,batch,*row))
                            expected_totals[row[-1]] += row[-2]
                            valid += 1
                        except ValueError as exc:
                            errors.append((batch,row_id,str(exc),json.dumps(raw,ensure_ascii=False)))
                            rejected += 1
                    copy_rows(cur,'tmp_raw',RAW_COLUMNS,raws)
                    cur.execute('INSERT INTO staging.raw_online_retail SELECT * FROM tmp_raw ON CONFLICT DO NOTHING')
                    cur.execute('TRUNCATE tmp_raw')
                    copy_rows(cur,'tmp_valid',VALID_COLUMNS,goods)
                    copy_rows(cur,'staging.etl_error','batch_id,source_row_id,reason,raw_values',errors)
                    print(json.dumps({'batch':batch,'read':read,'valid':valid,'rejected':rejected}),flush=True)
                load_dims(cur)
                inserted = load_fact(cur)
                result = reconcile(cur,read,valid,rejected,inserted,expected_totals)
                cur.execute('''UPDATE staging.etl_batch SET finished_at=clock_timestamp(), rows_read=%s,
                rows_valid=%s,rows_rejected=%s,rows_inserted=%s,rows_existing=%s,status='SUCCESS',reconciliation=%s
                WHERE batch_id=%s''',(read,valid,rejected,inserted,valid-inserted,Json(result),batch))
        print(json.dumps({'batch':batch,'status':'SUCCESS','rows_inserted':inserted,**result}),flush=True)
    except Exception as exc:
        with conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE staging.etl_batch SET status='FAILED',finished_at=clock_timestamp(),error_message=%s WHERE batch_id=%s",(str(exc),batch))
        raise

def main():
    p = argparse.ArgumentParser(description='Online Retail II PostgreSQL warehouse')
    p.add_argument('--source',default=config.SOURCE_FILE)
    p.add_argument('--init',action='store_true',help='Create schemas before loading')
    p.add_argument('--init-only',action='store_true')
    p.add_argument('--single-batch',action='store_true')
    p.add_argument('--sheet',help='Load one sheet; global source row IDs are preserved')
    p.add_argument('--chunk-size',type=int,default=config.CHUNK_SIZE)
    args = p.parse_args()
    if args.chunk_size < 1: p.error('chunk-size must be positive')
    if args.single_batch and args.sheet: p.error('--single-batch cannot combine with --sheet')
    import psycopg2
    conn = psycopg2.connect(config.DATABASE_URL)
    try:
        # Session lock serializes migrations, dimensions and fact loads across all ETL clients.
        with conn.cursor() as cur: cur.execute('SELECT pg_advisory_lock(5021067371)')
        conn.commit()
        if args.init or args.init_only:
            with conn:
                with conn.cursor() as cur:
                    for filename in ['01_schemas.sql','02_staging.sql','03_dw.sql']:
                        cur.execute((config.ROOT/'sql'/filename).read_text())
        if args.init_only: return
        file_id = fingerprint(args.source)
        if args.single_batch:
            def all_rows():
                for name, records in sheets(args.source):
                    for row_id, raw in records: yield row_id,name,raw
            process(conn,args.source,file_id,'ALL_SHEETS',all_rows(),args.chunk_size)
        else:
            found = False
            for name, records in sheets(args.source):
                if args.sheet and name != args.sheet:
                    for _ in records: pass
                    continue
                found = True
                process(conn,args.source,file_id,name,((i,name,r) for i,r in records),args.chunk_size)
            if not found: raise ValueError('Sheet not found')
    finally: conn.close()

if __name__ == '__main__': main()
