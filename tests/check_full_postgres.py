"""Full-workbook acceptance check via an isolated PostgreSQL single-user cluster.
No sockets or Python database driver required. Uses the production cleaning and loader SQL.
This is a validation tool; use etl.run_etl for the operational database.
"""
import argparse
import csv
import inspect
import json
import re
import subprocess
import tempfile
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from etl.extract import sheets, fingerprint, COLUMNS
from etl.clean import clean
from etl.load_dims import load_dims
from etl.load_fact import load_fact
from etl.run_etl import process
from tests.check_postgres import Capture


def literal(value): return "'"+str(value).replace("'","''")+"'"

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',default='data/raw/online-retail-ii.xlsx')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    file_id=fingerprint(args.source)
    cap=Capture();load_dims(cap);dims=';'.join(cap.sql)+';'
    cap.sql=[];load_fact(cap);fact=cap.sql[0]+';'
    temp_table=re.search(r"cur.execute\('''(CREATE TEMP TABLE tmp_valid .*?)'''\)",inspect.getsource(process),re.S).group(1)
    with tempfile.TemporaryDirectory(prefix='retail-full-') as temp:
        base=Path(temp)
        db=base/'pg'
        subprocess.run(['initdb','-D',str(db),'-A','trust','--no-locale','--encoding=UTF8'],check=True,capture_output=True)
        statements=[(root/'sql'/name).read_text() for name in ['01_schemas.sql','02_staging.sql','03_dw.sql']]
        report=[]
        for batch,(name,records) in enumerate(sheets(args.source),1):
            valid_file=base/f'valid{batch}.csv'
            count=valid=0;totals=defaultdict(Decimal);errors=defaultdict(int)
            with valid_file.open('w',newline='') as f:
                w=csv.writer(f,quoting=csv.QUOTE_ALL)
                for row_id,raw in records:
                    count+=1
                    try: row=clean(raw)
                    except ValueError as exc:
                        errors[str(exc)]+=1;continue
                    valid+=1;totals[row[-1]]+=row[-2]
                    values=(file_id,row_id,batch,*row)
                    f.write(','.join('' if v is None else '"'+str(v).replace('"','""')+'"' for v in values)+'\n')
            print(f'Prepared {name}: {count} read / {valid} valid',flush=True)
            statements += ['BEGIN;',f"INSERT INTO staging.etl_batch(source_file_id,file_name,sheet_name) VALUES('{file_id}',{literal(Path(args.source).name)},{literal(name)});",temp_table+';',
                           f"COPY tmp_valid FROM {literal(valid_file)} WITH (FORMAT CSV);",dims,fact]
            for kind,total in totals.items():
                statements.append(f"DO $$ BEGIN IF (SELECT sum(f.line_amount) FROM dw.fact_sales f JOIN tmp_valid t USING(source_file_id,source_row_id) WHERE f.transaction_type={literal(kind)}) <> {total} THEN RAISE EXCEPTION 'amount mismatch'; END IF; END $$;")
            statements.append(f"DO $$ BEGIN IF (SELECT count(*) FROM dw.fact_sales f JOIN tmp_valid t USING(source_file_id,source_row_id)) <> {valid} THEN RAISE EXCEPTION 'row mismatch'; END IF; END $$;")
            # Exact same source rows loaded again must result in zero INSERTs.
            statements.append('DO $$ DECLARE n bigint; BEGIN '+fact+' GET DIAGNOSTICS n = ROW_COUNT; IF n<>0 THEN RAISE EXCEPTION \'rerun duplicated rows\'; END IF; END $$;')
            statements.append(f"UPDATE staging.etl_batch SET status='SUCCESS',finished_at=clock_timestamp(),rows_read={count},rows_valid={valid},rows_rejected={count-valid},rows_inserted={valid} WHERE batch_id={batch}; COMMIT;")
            report.append({'sheet':name,'read':count,'valid':valid,'rejected':count-valid,'rejections':dict(errors),'totals':{k:str(v) for k,v in totals.items()}})
        expected=sum(b['valid'] for b in report)
        statements.append(f"DO $$ BEGIN IF (SELECT count(*) FROM dw.fact_sales)<>{expected} OR {expected}<=100000 THEN RAISE EXCEPTION 'fact count mismatch'; END IF; END $$;")
        # Compare one batch loading with the two sheet batches in the same isolated cluster.
        statements.append('BEGIN; CREATE TEMP TABLE snapshot AS SELECT transaction_type,count(*) AS n,sum(line_amount) AS amount FROM dw.fact_sales GROUP BY transaction_type;')
        statements.append(temp_table+';')
        for batch in range(1,len(report)+1):
            statements.append(f"COPY tmp_valid FROM {literal(base/f'valid{batch}.csv')} WITH (FORMAT CSV);")
        statements += ['TRUNCATE dw.fact_sales;',dims,fact,
                       "DO $$ BEGIN IF EXISTS ((SELECT transaction_type,count(*) AS n,sum(line_amount) AS amount FROM dw.fact_sales GROUP BY transaction_type EXCEPT SELECT * FROM snapshot) UNION ALL (SELECT * FROM snapshot EXCEPT SELECT transaction_type,count(*) AS n,sum(line_amount) AS amount FROM dw.fact_sales GROUP BY transaction_type)) THEN RAISE EXCEPTION 'single batch differs'; END IF; END $$; ROLLBACK;"]
        for name in ['04_analysis_queries.sql','05_checks.sql']:
            statements.append((root/'sql'/name).read_text())
        sql=re.sub(r'--[^\n]*','','\n'.join(statements)).replace('\n',' ')+'\n'
        result=subprocess.run(['postgres','--single','-D',str(db),'postgres'],input=sql,text=True,capture_output=True)
        log=result.stdout+result.stderr
        (root/'docs/results/full_postgres.log').write_text(log)
        passed=result.returncode==0 and 'ERROR:' not in log and 'FATAL:' not in log
        payload={'passed':passed,'source_sha256':file_id,'fact_rows':expected,'sheets':report,
                 'scope':'Production SQL and cleaning; full workbook, per-sheet load, rerun insert=0, money, single-batch equivalence. Operational psycopg2 orchestration not tested.'}
        (root/'docs/results/full_postgres.json').write_text(json.dumps(payload,indent=2))
        if not passed: raise SystemExit(log[-6000:])
        print(json.dumps(payload,indent=2))

if __name__=='__main__': main()
