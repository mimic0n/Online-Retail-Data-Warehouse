import io

def copy_rows(cur, table, columns, rows):
    if not rows: return
    buf = io.StringIO()
    for row in rows:
        # Quote every non-null field, including empty strings. SQL NULL is unquoted.
        buf.write(','.join('' if v is None else '"'+str(v).replace('"','""')+'"' for v in row)+'\n')
    buf.seek(0)
    cur.copy_expert(f"COPY {table} ({columns}) FROM STDIN WITH (FORMAT CSV)", buf)

def load_fact(cur):
    cur.execute("""INSERT INTO dw.fact_sales(source_file_id,source_row_id,batch_id,invoice_no,invoice_datetime,
    date_key,product_key,customer_key,country_key,quantity,unit_price,line_amount,transaction_type)
    SELECT t.source_file_id,t.source_row_id,t.batch_id,t.invoice_no,t.invoice_datetime,t.date_key,
    p.product_key,COALESCE(c.customer_key,0),k.country_key,t.quantity,t.unit_price,t.line_amount,t.transaction_type
    FROM tmp_valid t JOIN dw.dim_product p USING(stock_code) JOIN dw.dim_country k USING(country)
    LEFT JOIN dw.dim_customer c USING(customer_id)
    ON CONFLICT(source_file_id,source_row_id) DO NOTHING""")
    return cur.rowcount
