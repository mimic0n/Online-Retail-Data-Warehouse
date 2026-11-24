-- Q1: Monthly sales revenue (GBP)
SELECT d.year,d.month,SUM(f.line_amount) AS sales_revenue
FROM dw.fact_sales f JOIN dw.dim_date d USING(date_key)
WHERE transaction_type='SALE' GROUP BY d.year,d.month ORDER BY d.year,d.month;
-- Q2: Sales by country
SELECT k.country,SUM(f.line_amount) AS sales_revenue
FROM dw.fact_sales f JOIN dw.dim_country k USING(country_key)
WHERE transaction_type='SALE' GROUP BY k.country ORDER BY sales_revenue DESC;
-- Q3: Top 10 products
SELECT p.stock_code,p.description,SUM(f.line_amount) AS sales_revenue
FROM dw.fact_sales f JOIN dw.dim_product p USING(product_key)
WHERE transaction_type='SALE' GROUP BY p.stock_code,p.description ORDER BY sales_revenue DESC,p.stock_code LIMIT 10;
-- Q4: Top 10 known customers
SELECT c.customer_id,SUM(f.line_amount) AS sales_revenue
FROM dw.fact_sales f JOIN dw.dim_customer c USING(customer_key)
WHERE transaction_type='SALE' AND f.customer_key<>0
GROUP BY c.customer_id ORDER BY sales_revenue DESC,c.customer_id LIMIT 10;
-- Q5: Monthly cancellation and negative adjustment amount
SELECT d.year,d.month,ABS(SUM(f.line_amount)) AS cancel_adjust_amount
FROM dw.fact_sales f JOIN dw.dim_date d USING(date_key)
WHERE transaction_type IN ('RETURN_CANCELLATION','ADJUSTMENT')
GROUP BY d.year,d.month ORDER BY d.year,d.month;
-- KPI reconciliation (compare rounded values to Power BI)
WITH k AS (
 SELECT COALESCE(SUM(line_amount) FILTER(WHERE transaction_type='SALE'),0) AS sales_revenue,
 ABS(COALESCE(SUM(line_amount) FILTER(WHERE transaction_type IN ('RETURN_CANCELLATION','ADJUSTMENT')),0)) AS cancel_adjust_amount,
 COUNT(DISTINCT invoice_no) FILTER(WHERE transaction_type='SALE') AS sale_invoices,
 COUNT(DISTINCT customer_key) FILTER(WHERE transaction_type='SALE' AND customer_key<>0) AS known_customers
 FROM dw.fact_sales)
SELECT *,sales_revenue-cancel_adjust_amount AS adjusted_revenue,
sales_revenue/NULLIF(sale_invoices,0) AS avg_invoice_value FROM k;
-- Comparable December windows: days 01 through 09 only
SELECT d.year,SUM(f.line_amount) AS sales_revenue
FROM dw.fact_sales f JOIN dw.dim_date d USING(date_key)
WHERE transaction_type='SALE' AND d.month=12 AND d.day<=9 GROUP BY d.year ORDER BY d.year;
