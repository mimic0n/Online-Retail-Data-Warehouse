"""Export SQL results and median runtime of five EXPLAIN ANALYZE executions."""
import csv
import json
import platform
import statistics
from pathlib import Path
from .config import DATABASE_URL, ROOT

def main():
    import psycopg2
    out = ROOT/'docs/results'
    out.mkdir(exist_ok=True)
    queries = [q.strip() for q in (ROOT/'sql/04_analysis_queries.sql').read_text().split(';') if q.strip()]
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT version()')
            metadata = {'postgres':cur.fetchone()[0], 'platform':platform.platform(), 'cpu':platform.processor()}
            cur.execute('SELECT count(*) FROM dw.fact_sales')
            metadata['fact_rows'] = cur.fetchone()[0]
            cur.execute("SELECT indexdef FROM pg_indexes WHERE schemaname='dw'")
            metadata['indexes'] = [r[0] for r in cur.fetchall()]
            results = []
            for i,q in enumerate(queries,1):
                times, plans = [], []
                for _ in range(5):
                    cur.execute('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+q)
                    plan = cur.fetchone()[0][0]
                    times.append(plan['Execution Time'])
                    plans.append(plan)
                cur.execute(q)
                with (out/f'query_{i}.csv').open('w',newline='') as f:
                    w = csv.writer(f); w.writerow([d.name for d in cur.description]); w.writerows(cur.fetchall())
                results.append({'query':i,'median_ms':statistics.median(times),'runs_ms':times,'plans':plans})
            (out/'benchmark.json').write_text(json.dumps({'machine':metadata,'queries':results},indent=2))
if __name__=='__main__': main()
