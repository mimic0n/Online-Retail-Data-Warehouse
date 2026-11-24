CREATE TABLE IF NOT EXISTS dw.dim_date (
 date_key integer PRIMARY KEY, full_date date NOT NULL UNIQUE, day integer NOT NULL,
 month integer NOT NULL, quarter integer NOT NULL, year integer NOT NULL);
CREATE TABLE IF NOT EXISTS dw.dim_product (
 product_key serial PRIMARY KEY, stock_code text NOT NULL UNIQUE, description text NOT NULL,
 description_at timestamp, description_source char(64), description_row integer);
CREATE TABLE IF NOT EXISTS dw.dim_customer (
 customer_key serial PRIMARY KEY, customer_id text UNIQUE,
 CHECK ((customer_key=0 AND customer_id IS NULL) OR (customer_key>0 AND customer_id IS NOT NULL)));
INSERT INTO dw.dim_customer(customer_key,customer_id) VALUES(0,NULL) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS dw.dim_country(country_key serial PRIMARY KEY,country text NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS dw.fact_sales (
 sales_key bigserial PRIMARY KEY, source_file_id char(64) NOT NULL, source_row_id integer NOT NULL,
 batch_id integer NOT NULL REFERENCES staging.etl_batch, invoice_no text NOT NULL,
 invoice_datetime timestamp NOT NULL, date_key integer NOT NULL REFERENCES dw.dim_date,
 product_key integer NOT NULL REFERENCES dw.dim_product, customer_key integer NOT NULL REFERENCES dw.dim_customer,
 country_key integer NOT NULL REFERENCES dw.dim_country, quantity integer NOT NULL CHECK(quantity<>0),
 unit_price numeric(12,4) NOT NULL CHECK(unit_price>0), line_amount numeric(14,4) NOT NULL,
 transaction_type text NOT NULL CHECK(transaction_type IN ('SALE','RETURN_CANCELLATION','ADJUSTMENT')),
 UNIQUE(source_file_id,source_row_id), CHECK(line_amount=quantity*unit_price));
CREATE INDEX IF NOT EXISTS ix_fact_date ON dw.fact_sales(date_key);
CREATE INDEX IF NOT EXISTS ix_fact_product ON dw.fact_sales(product_key);
CREATE INDEX IF NOT EXISTS ix_fact_customer ON dw.fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS ix_fact_country ON dw.fact_sales(country_key);
CREATE INDEX IF NOT EXISTS ix_fact_invoice ON dw.fact_sales(invoice_no);
