def load_dims(cur):
    cur.execute("""INSERT INTO dw.dim_date
    SELECT to_char(d,'YYYYMMDD')::integer,d::date,extract(day FROM d),extract(month FROM d),
    extract(quarter FROM d),extract(year FROM d)
    FROM generate_series(LEAST('2009-12-01'::date,(SELECT min(invoice_datetime)::date FROM tmp_valid)),
    GREATEST('2011-12-31'::date,(SELECT max(invoice_datetime)::date FROM tmp_valid)),interval '1 day') d
    ON CONFLICT DO NOTHING""")
    cur.execute("INSERT INTO dw.dim_country(country) SELECT DISTINCT country FROM tmp_valid ON CONFLICT DO NOTHING")
    cur.execute("INSERT INTO dw.dim_customer(customer_id) SELECT DISTINCT customer_id FROM tmp_valid WHERE customer_id IS NOT NULL ON CONFLICT DO NOTHING")
    cur.execute("""INSERT INTO dw.dim_product(stock_code,description,description_at,description_source,description_row)
    SELECT DISTINCT ON(stock_code) stock_code,COALESCE(NULLIF(description,''),'Unknown product'),
    CASE WHEN description<>'' THEN invoice_datetime END,source_file_id,source_row_id
    FROM tmp_valid ORDER BY stock_code,(description<>'') DESC,invoice_datetime DESC,source_file_id DESC,source_row_id DESC
    ON CONFLICT(stock_code) DO UPDATE SET description=excluded.description,description_at=excluded.description_at,
    description_source=excluded.description_source,description_row=excluded.description_row
    WHERE excluded.description_at IS NOT NULL AND
    (dw.dim_product.description_at IS NULL OR
    (excluded.description_at,excluded.description_source,excluded.description_row) >
    (dw.dim_product.description_at,dw.dim_product.description_source,dw.dim_product.description_row))""")
