SELECT transaction_type,COUNT(*) AS rows_n,ROUND(SUM(line_amount),2) AS total_amount
FROM dw.fact_sales GROUP BY transaction_type ORDER BY transaction_type;
SELECT source_file_id,source_row_id,COUNT(*) FROM dw.fact_sales
GROUP BY source_file_id,source_row_id HAVING COUNT(*)>1;
SELECT COUNT(*) AS rows_unknown_customer FROM dw.fact_sales WHERE customer_key=0;
SELECT batch_id,sheet_name,status,rows_read,rows_valid,rows_rejected,rows_inserted,rows_existing,
(rows_read=rows_valid+rows_rejected) AS eq_read_ok,
(rows_valid=rows_inserted+rows_existing) AS eq_valid_ok,finished_at-started_at AS elapsed
FROM staging.etl_batch ORDER BY batch_id;
SELECT COUNT(*) AS fact_rows,COUNT(*)>100000 AS meets_size_target,
COUNT(*)=(SELECT COALESCE(SUM(rows_inserted),0) FROM staging.etl_batch WHERE status='SUCCESS') AS matches_inserted
FROM dw.fact_sales;
SELECT COUNT(*) AS orphan_rows FROM dw.fact_sales f
LEFT JOIN dw.dim_date d USING(date_key) LEFT JOIN dw.dim_product p USING(product_key)
LEFT JOIN dw.dim_customer c USING(customer_key) LEFT JOIN dw.dim_country k USING(country_key)
WHERE d.date_key IS NULL OR p.product_key IS NULL OR c.customer_key IS NULL OR k.country_key IS NULL;
SELECT table_name,constraint_name,constraint_type FROM information_schema.table_constraints
WHERE table_schema='dw' ORDER BY table_name,constraint_type;
