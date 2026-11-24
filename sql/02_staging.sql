CREATE TABLE IF NOT EXISTS staging.etl_batch (
 batch_id serial PRIMARY KEY, source_file_id char(64) NOT NULL, file_name text NOT NULL,
 sheet_name text NOT NULL, started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 rows_read integer NOT NULL DEFAULT 0, rows_valid integer NOT NULL DEFAULT 0,
 rows_rejected integer NOT NULL DEFAULT 0, rows_inserted integer NOT NULL DEFAULT 0,
 rows_existing integer NOT NULL DEFAULT 0, status text NOT NULL DEFAULT 'RUNNING'
 CHECK(status IN ('RUNNING','SUCCESS','FAILED')), error_message text, reconciliation jsonb);
CREATE TABLE IF NOT EXISTS staging.raw_online_retail (
 source_file_id char(64) NOT NULL, source_row_id integer NOT NULL,
 batch_id integer NOT NULL REFERENCES staging.etl_batch, sheet_name text NOT NULL,
 invoice text, stock_code text, description text, quantity text, invoice_date text,
 price text, customer_id text, country text, PRIMARY KEY(source_file_id,source_row_id));
CREATE TABLE IF NOT EXISTS staging.etl_error (
 error_id bigserial PRIMARY KEY, batch_id integer NOT NULL REFERENCES staging.etl_batch,
 source_row_id integer NOT NULL, reason text NOT NULL, raw_values jsonb NOT NULL);
