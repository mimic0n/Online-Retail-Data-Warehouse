"""Verify real loader SQL without sockets, using PostgreSQL single-user mode.
Requires initdb/postgres binaries on PATH. Uses an isolated temporary cluster.
"""
import inspect
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from etl.load_dims import load_dims
from etl.load_fact import load_fact
from etl.reconcile import reconcile
from etl.run_etl import process

class Capture:
    rowcount=3
    def __init__(self): self.sql=[]
    def execute(self,sql,*args): self.sql.append(sql)
    def fetchone(self): return (3,True)
    def fetchall(self): return []

def main():
    if not shutil.which('postgres') or not shutil.which('initdb'):
        raise SystemExit('PostgreSQL binaries are required')
    root=Path(__file__).resolve().parents[1]
    cap=Capture()
    load_dims(cap)
    dims=list(cap.sql)
    cap.sql=[]; load_fact(cap); fact=cap.sql[0]
    cap.sql=[]; reconcile(cap,3,3,0,3); checks=cap.sql
    src=inspect.getsource(process)
    temp=re.search(r"cur.execute\('''(CREATE TEMP TABLE tmp_valid .*?)'''\)",src,re.S).group(1)
    sql='\n'.join((root/'sql'/name).read_text() for name in ['01_schemas.sql','02_staging.sql','03_dw.sql'])
    sql+=''' BEGIN;
    INSERT INTO staging.etl_batch(source_file_id,file_name,sheet_name) VALUES(repeat('a',64),'fixture','sheet');
    '''+temp+''';
    INSERT INTO tmp_valid VALUES
    (repeat('a',64),1,1,'100','2010-12-01',20101201,'X','New name','123','UK',2,1.2500,2.5000,'SALE'),
    (repeat('a',64),2,1,'C100','2010-12-02',20101202,'X','',NULL,'UK',-1,1.2500,-1.2500,'RETURN_CANCELLATION'),
    (repeat('a',64),3,1,'101','2010-12-03',20101203,'X','Latest',NULL,'UK',-1,1.2500,-1.2500,'ADJUSTMENT');
    '''+';'.join(dims)+';'+fact+';'+ ';'.join(checks)+';'+fact+''';
    DO $$ BEGIN
      IF (SELECT count(*) FROM dw.fact_sales)<>3 THEN RAISE EXCEPTION 'duplicate/missing facts'; END IF;
      IF (SELECT sum(line_amount) FROM dw.fact_sales)<>0 THEN RAISE EXCEPTION 'incorrect amount'; END IF;
      IF (SELECT count(*) FROM dw.fact_sales WHERE customer_key=0)<>2 THEN RAISE EXCEPTION 'unknown customer'; END IF;
      IF (SELECT description FROM dw.dim_product WHERE stock_code='X')<>'Latest' THEN RAISE EXCEPTION 'latest description'; END IF;
    END $$;
    UPDATE tmp_valid SET description='Older',invoice_datetime='2009-12-01';
    '''+';'.join(dims)+''';
    DO $$ BEGIN
      IF (SELECT description FROM dw.dim_product WHERE stock_code='X')<>'Latest' THEN RAISE EXCEPTION 'older overwrite'; END IF;
    END $$;
    COMMIT;
    '''
    for name in ['04_analysis_queries.sql','05_checks.sql']:
        sql+='\n'+(root/'sql'/name).read_text()
    # Single-user postgres treats each newline as the end of a command.
    sql=re.sub(r'--[^\n]*','',sql).replace('\n',' ')+'\n'
    with tempfile.TemporaryDirectory(prefix='retail-sql-') as tempdir:
        db=Path(tempdir)/'pg'
        subprocess.run(['initdb','-D',str(db),'-A','trust','--no-locale','--encoding=UTF8'],check=True,capture_output=True)
        run=subprocess.run(['postgres','--single','-D',str(db),'postgres'],input=sql,text=True,capture_output=True)
        log=run.stdout+run.stderr
        (root/'docs/results/postgres_fixture.log').write_text(log)
        if run.returncode or 'ERROR:' in log or 'FATAL:' in log: raise SystemExit(log)
    print('PASS: schema, actual loader SQL, rerun, unknown customer, latest description, reconciliation SQL, Q1-Q5 and checks')

if __name__=='__main__': main()
