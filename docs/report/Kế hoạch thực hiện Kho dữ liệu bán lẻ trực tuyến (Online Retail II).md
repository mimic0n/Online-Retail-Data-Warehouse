# Kế hoạch thực hiện: Kho dữ liệu bán lẻ trực tuyến (Online Retail II)

Nov 15, 2026 · @Miku who cannot sing

## Tổng quan

Dự án hoàn thành khi có kho dữ liệu PostgreSQL với hơn 100.000 dòng hợp lệ, chương trình Python nạp lại được mà không nhân đôi dữ liệu, và dashboard Power BI khớp với kết quả SQL. Với Online Retail II, nguồn có 1.067.371 dòng, gấp khoảng hai lần bản Online Retail trong báo cáo (541.909 dòng), nên yêu cầu 100.000 dòng được đáp ứng với biên rất rộng.

Công việc gồm sáu giai đoạn nối tiếp:

1. Cập nhật báo cáo và dữ liệu nguồn cho khớp Online Retail II (tuần 1).
2. Dựng PostgreSQL: schema `staging`, schema `dw`, khóa và ràng buộc (tuần 1–2).
3. Viết ETL Python: đọc, làm sạch, phân loại, nạp, đối chiếu (tuần 2–3).
4. Viết 5 truy vấn SQL và kiểm tra các chỉ số (tuần 3–4).
5. Dựng Power BI 3 trang và đối chiếu với SQL (tuần 4).
6. Kiểm thử, hoàn thiện báo cáo PDF, chuẩn bị demo (tuần 5).

Thiết kế star schema trong báo cáo (1 bảng fact, 4 bảng dimension) giữ nguyên. Chỉ các chi tiết gắn với dữ liệu cần đổi, được liệt kê ở mục tiếp theo.

## Điểm báo cáo cần sửa cho khớp Online Retail II

Có 8 chỗ trong báo cáo hiện tại còn mô tả dataset Online Retail cũ; sửa trước khi viết mã để mọi số liệu về sau nhất quán.

| Vị trí trong báo cáo | Hiện tại (Online Retail) | Sửa thành (Online Retail II) |
| --- | --- | --- |
| Mục 3.2, tên và quy mô | UCI Online Retail, 541.909 dòng, 8 cột | UCI Online Retail II, 1.067.371 dòng, 8 cột; hai sheet: 2009–2010 (525.461 dòng) và 2010–2011 (541.910 dòng) |
| Mục 3.2, khoảng thời gian | 01/12/2010 đến 09/12/2011 | 01/12/2009 đến 09/12/2011 |
| Bảng 1, tên cột | InvoiceNo, UnitPrice, CustomerID | Tên trong file Excel là Invoice, Price, Customer ID; ánh xạ về tên chuẩn ở bước làm sạch |
| Mục 3.4, bước 1 | Đọc một sheet | Đọc cả hai sheet (`sheet_name=None`), gộp lại, thêm cột sheet nguồn |
| Mục 3.4, bước 5 | Chia dữ liệu thành hai đợt nạp tùy ý | Dùng hai sheet làm hai đợt nạp tự nhiên |
| Mục 4.2, lưu ý tháng 12 | Tháng 12/2011 chỉ đến ngày 09, tháng 12/2010 từ ngày 01 | Có thêm tháng 12/2009 (từ ngày 01); chỉ so sánh 01–09/12 giữa ba năm, hoặc so 12/2009 với 12/2010 |
| Tài liệu \[1\] | DOI 10.24432/C5BW33, dataset 352 | DOI 10.24432/C5CG6D, dataset 502, tác giả D. Chen (2012) |
| Giấy phép | Chưa nêu | CC BY 4.0: ghi rõ nguồn và tác giả trong báo cáo |

Sau khi sửa, tiêu chí "hơn 100.000 dòng hợp lệ" vẫn đúng nhưng nên ghi thêm số dòng thực tế sau xử lý ở mục 4 khi có kết quả.

Nguồn: [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii), [OpenML 43368](https://api.openml.org/d/43368), số dòng từng sheet theo [mô tả trên Kaggle](https://www.kaggle.com/datasets/lakshmi25npathi/online-retail-dataset).

## Chuẩn bị môi trường và công cụ

Cả nhóm cài cùng một bộ công cụ trong ngày đầu của tuần 1, để mã chạy giống nhau trên mọi máy.

| Công cụ | Việc cần làm | Kiểm tra xong khi |
| --- | --- | --- |
| Python 3.11 trở lên | Tạo môi trường ảo `venv` cho dự án | `python --version` chạy được trên mọi máy |
| Thư viện Python | Cài `pandas`, `openpyxl`, `SQLAlchemy`, `psycopg2-binary`, `python-dotenv`; ghi vào `requirements.txt` | `pip install -r requirements.txt` không lỗi |
| PostgreSQL | Cài bản 15 hoặc 16, tạo database `retail_dwh` và một user riêng | Kết nối được bằng pgAdmin hoặc DBeaver |
| Power BI Desktop | Cài trên máy Windows | Kết nối thử tới PostgreSQL thành công |
| Git | Tạo repo chung, thêm `.gitignore` cho `data/` và `.env` | Mọi thành viên clone và push được |

Power BI Desktop chỉ chạy trên Windows. Nếu có thành viên dùng macOS hoặc Linux, giao phần Power BI cho người dùng Windows hoặc dùng chung một máy khi dựng dashboard.

Cấu trúc thư mục đề xuất:

```text
retail-dwh/
  data/raw/online_retail_II.xlsx     (không đưa lên Git)
  data/interim/                      (bản CSV tạm để chạy thử nhanh)
  sql/01_schemas.sql
  sql/02_staging.sql
  sql/03_dw.sql
  sql/04_analysis_queries.sql
  sql/05_checks.sql
  etl/config.py
  etl/extract.py
  etl/clean.py
  etl/classify.py
  etl/load_dims.py
  etl/load_fact.py
  etl/reconcile.py
  etl/run_etl.py
  powerbi/retail.pbix
  docs/data_profile.md
  docs/report/
  requirements.txt
  .env.example
```

Thông tin kết nối (host, user, mật khẩu) chỉ nằm trong `.env`; repo chỉ giữ `.env.example` với giá trị mẫu.

Đọc file Excel hơn một triệu dòng bằng `read_excel` mất vài phút và tốn nhiều RAM. Khi viết và gỡ lỗi, lưu một bản CSV vào `data/interim/` để chạy nhanh; bản chạy chính thức vẫn đọc file Excel gốc.

## Chuẩn bị dữ liệu nguồn

Mục tiêu của tuần 1 là biết chính xác dữ liệu có gì trước khi thiết kế bảng. Mỗi bước dưới đây có một kết quả ghi lại được.

1. Tải `online_retail_II.xlsx` (khoảng 43,5 MB) từ trang UCI, ghi ngày tải và tính mã băm SHA-256 của file. Mã băm này sau đó dùng làm `source_file_id`.
2. Đọc thử bằng `pandas.read_excel(..., sheet_name=None, dtype=str)` để giữ mã sản phẩm và mã hóa đơn dạng văn bản. Xác nhận có hai sheet và tổng 1.067.371 dòng.
3. Lập hồ sơ dữ liệu và ghi vào `docs/data_profile.md`, gồm các số liệu ở bảng bên dưới.
4. Chọn khoảng 20 hóa đơn (bán, hủy, thiếu mã khách) và ghi tay tổng tiền, dùng để đối chiếu thủ công ở tuần 5.
5. Chốt cách xử lý ngày (xem cuối mục này).

Các số liệu cần có trong hồ sơ dữ liệu:

| Kiểm tra | Ghi nhận | Dùng cho |
| --- | --- | --- |
| Số dòng mỗi sheet và tổng | Phải khớp 525.461 + 541.910 = 1.067.371 | Đối chiếu số dòng nguồn |
| Dòng thiếu `Customer ID` | OpenML ghi 243.007 dòng (khoảng 22,8%) | Dòng "Không xác định" trong `dim_customer` |
| Dòng thiếu `Description` | OpenML ghi 4.474 dòng | Quy tắc chọn tên sản phẩm |
| Mã hóa đơn bắt đầu bằng `C` | Đếm số dòng | Nhóm `RETURN_CANCELLATION` |
| `Quantity` bằng 0, âm; `Price` bằng 0, âm | Đếm theo từng tổ hợp | Nhóm `ADJUSTMENT` và dòng cần tách |
| `StockCode` không phải mã sản phẩm thông thường | Liệt kê giá trị khác dạng 5 chữ số | Quyết định có loại khỏi `dim_product` không |
| Dòng trùng hoàn toàn | Đếm, chưa xóa | Thống kê để xem xét, không tự bỏ |
| Số chữ số thập phân của `Price` | Tối đa bao nhiêu | Chọn kiểu `numeric` |
| Giá trị `Country` | Liệt kê, chú ý các giá trị không phải tên nước | Nội dung `dim_country` |

Về năm trong dữ liệu: nếu môn học chỉ yêu cầu hơn 100.000 dòng thì không cần đổi gì, và nên giữ nguyên năm gốc 2009–2011. Nếu bắt buộc dữ liệu từ năm 2020 trở lên, dịch cả cột `InvoiceDate` đồng đều +11 năm (2009–2011 thành 2020–2022) bằng `pd.DateOffset(years=11)`, không chỉ thay riêng năm 2010. Làm thế giữ được thứ tự thời gian và khoảng cách giữa các hóa đơn. Dữ liệu đã dịch ngày phải lưu thành file riêng, giữ nguyên file gốc ở vùng dữ liệu thô, và báo cáo phải ghi rõ ngày đã được dịch +11 năm so với nguồn, vì đó không còn là ngày giao dịch thật.

Nguồn số liệu: [OpenML 43368](https://api.openml.org/d/43368).

## Thiết kế PostgreSQL

Database `retail_dwh` có hai schema: `staging` giữ dữ liệu thô cùng nhật ký nạp, `dw` giữ các bảng phục vụ báo cáo. Viết các file SQL theo thứ tự `01` đến `03` để chạy lại từ đầu bất cứ lúc nào.

| Bảng | Cột chính | Khóa và ràng buộc |
| --- | --- | --- |
| `staging.etl_batch` | batch\_id, source\_file\_id, file\_name, sheet\_name, started\_at, finished\_at, rows\_read, rows\_valid, rows\_rejected, rows\_inserted, rows\_existing, status | Khóa chính `batch_id` |
| `staging.raw_online_retail` | source\_file\_id, source\_row\_id, batch\_id, các cột nguồn dạng văn bản | Duy nhất `(source_file_id, source_row_id)` |
| `staging.etl_error` | error\_id, batch\_id, source\_row\_id, reason, raw\_values | Khóa ngoại tới `etl_batch` |
| `dw.dim_date` | date\_key (dạng yyyymmdd), full\_date, day, month, quarter, year | Khóa chính `date_key` |
| `dw.dim_product` | product\_key, stock\_code, description | `stock_code` duy nhất |
| `dw.dim_customer` | customer\_key, customer\_id | `customer_id` duy nhất; dòng `customer_key = 0` là "Không xác định" |
| `dw.dim_country` | country\_key, country | `country` duy nhất |
| `dw.fact_sales` | 14 cột theo Bảng 2 của báo cáo | Khóa chính `sales_key`; 4 khóa ngoại; duy nhất `(source_file_id, source_row_id)` |

Bảng `dim_date` chỉ giữ ngày. Giờ phút giao dịch nằm ở cột `invoice_datetime` của `fact_sales`, khớp với ghi chú trong báo cáo rằng chưa tạo bảng thời gian riêng. Tạo đủ ngày từ 01/12/2009 đến 31/12/2011 (hoặc theo khoảng đã dịch nếu dùng cách ở mục dữ liệu nguồn).

Đoạn SQL cho bảng trung tâm, làm khuôn cho các bảng còn lại:

```sql
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dw;

CREATE TABLE staging.etl_batch (
  batch_id        serial PRIMARY KEY,
  source_file_id  char(64) NOT NULL,
  file_name       text NOT NULL,
  sheet_name      text,
  started_at      timestamp NOT NULL DEFAULT now(),
  finished_at     timestamp,
  rows_read       integer,
  rows_valid      integer,
  rows_rejected   integer,
  rows_inserted   integer,
  rows_existing   integer,
  status          text NOT NULL DEFAULT 'RUNNING'
);

CREATE TABLE dw.fact_sales (
  sales_key         bigserial PRIMARY KEY,
  source_file_id    char(64) NOT NULL,
  source_row_id     integer NOT NULL,
  batch_id          integer NOT NULL REFERENCES staging.etl_batch(batch_id),
  invoice_no        text NOT NULL,
  invoice_datetime  timestamp NOT NULL,
  date_key          integer NOT NULL REFERENCES dw.dim_date(date_key),
  product_key       integer NOT NULL REFERENCES dw.dim_product(product_key),
  customer_key      integer NOT NULL REFERENCES dw.dim_customer(customer_key),
  country_key       integer NOT NULL REFERENCES dw.dim_country(country_key),
  quantity          integer NOT NULL,
  unit_price        numeric(12,4) NOT NULL,
  line_amount       numeric(14,4) NOT NULL,
  transaction_type  text NOT NULL
    CHECK (transaction_type IN ('SALE','RETURN_CANCELLATION','ADJUSTMENT')),
  CONSTRAINT uq_fact_source UNIQUE (source_file_id, source_row_id)
);

CREATE INDEX ix_fact_date     ON dw.fact_sales (date_key);
CREATE INDEX ix_fact_product  ON dw.fact_sales (product_key);
CREATE INDEX ix_fact_customer ON dw.fact_sales (customer_key);
CREATE INDEX ix_fact_country  ON dw.fact_sales (country_key);
CREATE INDEX ix_fact_invoice  ON dw.fact_sales (invoice_no);
```

`source_row_id` đánh số liên tục từ 1 đến 1.067.371 trên cả hai sheet (không đánh lại từ 1 ở sheet thứ hai), để cặp với `source_file_id` vẫn duy nhất. Kiểu `numeric(12,4)` chỉ là mức an toàn: chốt lại số chữ số thập phân sau khi lập hồ sơ cột `Price`, và làm tròn 2 chữ số khi báo cáo tiền.

## Quy trình ETL bằng Python

`run_etl.py` gọi năm module theo đúng năm bước trong báo cáo. Mỗi sheet là một đợt nạp (`batch`), nên lần chạy đầu có hai dòng trong `staging.etl_batch`.

| Bước | Module | Việc cụ thể | Đầu ra |
| --- | --- | --- | --- |
| 1. Lấy và lưu | `extract.py` | Tính SHA-256 của file; đọc từng sheet; gán `source_row_id` liên tục trên cả hai sheet; tạo dòng `etl_batch`; ghi vào staging theo khối 50.000 dòng | `staging.raw_online_retail` |
| 2. Kiểm tra và làm sạch | `clean.py` | Đổi tên cột (Invoice thành invoice\_no, Price thành unit\_price, Customer ID thành customer\_id); cắt khoảng trắng; ép kiểu ngày, số nguyên, `Decimal`; chuẩn hóa mã khách hàng về chuỗi số nguyên không có đuôi `.0`; dòng không ép được kiểu ghi vào `etl_error` kèm lý do | Bảng dữ liệu hợp lệ và bảng lỗi |
| 3. Phân loại | `classify.py` | Gán `transaction_type` và tính `line_amount` theo quy tắc ở mục sau | Thêm hai cột vào dữ liệu hợp lệ |
| 4. Nạp kho | `load_dims.py`, `load_fact.py` | Nạp `dim_date`, `dim_country`, `dim_customer`, `dim_product` trước; lấy khóa; nối khóa vào dữ liệu; nạp `fact_sales` | Các bảng trong schema `dw` |
| 5. Đối chiếu | `reconcile.py` | Kiểm tra các đẳng thức số dòng, khóa liên kết, tổng tiền; ghi kết quả và thời gian chạy vào `etl_batch` | `status` là `SUCCESS` hoặc `FAILED` |

Quy tắc cho bốn bảng mô tả theo báo cáo: thiếu mã khách hàng thì gán `customer_key = 0`, không bỏ dòng; tên sản phẩm lấy giá trị không trống ở thời điểm gần nhất theo `InvoiceDate`, và ghi quy tắc này vào báo cáo.

Để chạy nhanh với hơn một triệu dòng, ghi dữ liệu hợp lệ vào bảng tạm bằng `COPY` (qua `psycopg2`), sau đó dùng một câu `INSERT ... SELECT` để nối khóa và nạp. Không nạp từng dòng một.

Tính idempotent (chạy lại không nhân đôi) dựa vào ràng buộc duy nhất đã đặt trên cặp mã file và số thứ tự dòng:

```sql
INSERT INTO dw.fact_sales (source_file_id, source_row_id, batch_id, invoice_no,
  invoice_datetime, date_key, product_key, customer_key, country_key,
  quantity, unit_price, line_amount, transaction_type)
SELECT t.source_file_id, t.source_row_id, t.batch_id, t.invoice_no,
  t.invoice_datetime, t.date_key, p.product_key, c.customer_key, k.country_key,
  t.quantity, t.unit_price, t.line_amount, t.transaction_type
FROM   staging.tmp_valid t
JOIN   dw.dim_product  p ON p.stock_code  = t.stock_code
JOIN   dw.dim_customer c ON c.customer_id IS NOT DISTINCT FROM t.customer_id
JOIN   dw.dim_country  k ON k.country     = t.country
ON CONFLICT (source_file_id, source_row_id) DO NOTHING;
```

Điều kiện đối chiếu của mỗi đợt nạp, lấy đúng từ báo cáo:

1. `rows_read` bằng `rows_valid` cộng `rows_rejected`.
2. `rows_valid` bằng `rows_inserted` cộng `rows_existing`.
3. Không có khóa ngoại rỗng trong `fact_sales`.
4. Tổng `line_amount` trong kho khớp tổng tính từ dữ liệu hợp lệ trong Python.

Câu `INSERT` ở trên nối bằng `JOIN`, nên một dòng thiếu khóa mô tả sẽ bị mất im lặng; điều kiện 3 và điều kiện 1–2 là lưới an toàn bắt trường hợp này.

## Quy tắc phân loại giao dịch

Mỗi dòng đi qua năm điều kiện theo đúng thứ tự dưới đây và chỉ rơi vào một kết quả. Thứ tự này bao phủ mọi tổ hợp của dấu số lượng, dấu đơn giá và chữ cái đầu mã hóa đơn.

| Thứ tự | Điều kiện (mã hóa đơn đã chuyển chữ hoa) | Kết quả |
| --- | --- | --- |
| 1 | `Quantity = 0` hoặc `unit_price <= 0` | Ghi vào `etl_error` với lý do tương ứng; không nạp vào `fact_sales` |
| 2 | Mã bắt đầu bằng `C` và `Quantity > 0` | Thông tin mâu thuẫn: ghi vào `etl_error` |
| 3 | Mã bắt đầu bằng `C`, `Quantity < 0`, `unit_price > 0` | `RETURN_CANCELLATION` |
| 4 | Mã không bắt đầu bằng `C`, `Quantity > 0`, `unit_price > 0` | `SALE` |
| 5 | Các dòng còn lại: mã không bắt đầu bằng `C`, `Quantity < 0`, `unit_price > 0` | `ADJUSTMENT` |

`line_amount` bằng `Quantity × unit_price`, tính bằng `Decimal`, giữ dấu âm của dòng hủy và điều chỉnh.

Việc cần làm thêm ở tuần 1 và 2:

- Liệt kê mã hóa đơn bắt đầu bằng chữ cái khác `C` trong hồ sơ dữ liệu, xem có rơi vào điều kiện 1 hay 5 và ghi vào báo cáo.
- Đếm số dòng của từng điều kiện và ghi vào `docs/data_profile.md`; con số này đi thẳng vào phần kết quả của báo cáo.
- Quyết định cách xử lý `StockCode` không phải mã sản phẩm thông thường (phí vận chuyển, phí ngân hàng và tương tự). Mặc định giữ trong `fact_sales` để tổng tiền khớp nguồn, và ghi chú rõ trong báo cáo.
- Viết quy tắc đúng một lần, trong `classify.py`. SQL và Power BI chỉ đọc cột `transaction_type` đã lưu, không tự phân loại lại, nhờ đó ba nơi tính ra cùng một số.

Phân loại này phục vụ phân tích, chưa xác nhận hoàn tiền hay đối chiếu từng đơn hủy với đơn gốc. Câu này cần giữ trong báo cáo.

## Truy vấn SQL và chỉ số

Viết năm truy vấn chính trong `sql/04_analysis_queries.sql`, rồi một truy vấn chỉ số tổng hợp. Mọi truy vấn đọc cột `transaction_type` đã lưu, không tự phân loại lại.

```sql
-- Q1. Doanh thu bán hàng theo tháng
SELECT d.year, d.month, SUM(f.line_amount) AS sales_revenue
FROM dw.fact_sales f
JOIN dw.dim_date d ON d.date_key = f.date_key
WHERE f.transaction_type = 'SALE'
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- Q2. Doanh thu bán hàng theo quốc gia
SELECT k.country, SUM(f.line_amount) AS sales_revenue
FROM dw.fact_sales f
JOIN dw.dim_country k ON k.country_key = f.country_key
WHERE f.transaction_type = 'SALE'
GROUP BY k.country
ORDER BY sales_revenue DESC;

-- Q3. 10 sản phẩm có doanh thu cao nhất
SELECT p.stock_code, p.description, SUM(f.line_amount) AS sales_revenue
FROM dw.fact_sales f
JOIN dw.dim_product p ON p.product_key = f.product_key
WHERE f.transaction_type = 'SALE'
GROUP BY p.stock_code, p.description
ORDER BY sales_revenue DESC
LIMIT 10;

-- Q4. 10 khách hàng có doanh thu cao nhất (bỏ dòng Không xác định)
SELECT c.customer_id, SUM(f.line_amount) AS sales_revenue
FROM dw.fact_sales f
JOIN dw.dim_customer c ON c.customer_key = f.customer_key
WHERE f.transaction_type = 'SALE' AND f.customer_key <> 0
GROUP BY c.customer_id
ORDER BY sales_revenue DESC
LIMIT 10;

-- Q5. Giá trị hủy và điều chỉnh âm theo tháng
SELECT d.year, d.month, ABS(SUM(f.line_amount)) AS cancel_adjust_amount
FROM dw.fact_sales f
JOIN dw.dim_date d ON d.date_key = f.date_key
WHERE f.transaction_type IN ('RETURN_CANCELLATION', 'ADJUSTMENT')
GROUP BY d.year, d.month
ORDER BY d.year, d.month;
```

Truy vấn chỉ số tổng hợp, đúng với Bảng 5 của báo cáo:

```sql
SELECT
  SUM(f.line_amount) FILTER (WHERE f.transaction_type = 'SALE') AS sales_revenue,
  ABS(SUM(f.line_amount) FILTER (
      WHERE f.transaction_type IN ('RETURN_CANCELLATION', 'ADJUSTMENT'))) AS cancel_adjust_amount,
  COUNT(DISTINCT f.invoice_no) FILTER (WHERE f.transaction_type = 'SALE') AS sale_invoices,
  COUNT(DISTINCT f.customer_key) FILTER (
      WHERE f.transaction_type = 'SALE' AND f.customer_key <> 0) AS known_customers
FROM dw.fact_sales f;
```

Từ kết quả trên tính thêm hai chỉ số: doanh thu sau điều chỉnh bằng `sales_revenue` trừ `cancel_adjust_amount`, và giá trị hóa đơn trung bình bằng `sales_revenue` chia `sale_invoices`.

Vì Online Retail II có tháng 12 của ba năm với độ dài khác nhau, thêm một truy vấn so sánh khoảng tương đương: lọc `d.month = 12 AND d.day <= 9` rồi nhóm theo `d.year`.

Cách đo thời gian chạy theo báo cáo:

1. Chạy mỗi truy vấn 5 lần bằng `EXPLAIN (ANALYZE, BUFFERS)` và lấy giá trị trung vị.
2. Ghi cấu hình máy (CPU, RAM, ổ đĩa), phiên bản PostgreSQL, số dòng của `fact_sales` và việc đã tạo chỉ mục hay chưa.
3. Đo hai lần: trước và sau khi tạo chỉ mục, nếu còn thời gian, để có thêm một so sánh cho báo cáo.

## Power BI: mô hình và dashboard

Dựng Power BI ở tuần 4, sau khi `fact_sales` đã nạp xong và 5 truy vấn SQL đã có kết quả để đối chiếu.

1. Kết nối: chọn nguồn PostgreSQL, server và database `retail_dwh`, chế độ **Import**. Nạp 5 bảng schema `dw` và bảng `staging.etl_batch` (cho trang 3). Nếu Power BI báo thiếu trình kết nối Npgsql, cài theo [hướng dẫn của Microsoft](https://learn.microsoft.com/en-us/power-query/connectors/postgresql).
2. Quan hệ: bốn quan hệ nhiều-một, một chiều, từ `fact_sales` tới `dim_date`, `dim_product`, `dim_customer`, `dim_country` theo các cột khóa. Đặt `dim_date` làm bảng ngày, dựa trên cột `full_date`. Theo mô hình hình sao, bảng mô tả lọc bảng giao dịch, không ngược lại ([Microsoft Learn](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema)).
3. Chỉ số: tạo thành các measure DAX, trùng với Bảng 5 của báo cáo.

```text
Sales Revenue = CALCULATE(SUM(fact_sales[line_amount]), fact_sales[transaction_type] = "SALE")

Cancel Adjust Amount = ABS(CALCULATE(SUM(fact_sales[line_amount]),
    fact_sales[transaction_type] IN {"RETURN_CANCELLATION", "ADJUSTMENT"}))

Adjusted Revenue = [Sales Revenue] - [Cancel Adjust Amount]

Sale Invoices = CALCULATE(DISTINCTCOUNT(fact_sales[invoice_no]), fact_sales[transaction_type] = "SALE")

Avg Invoice Value = DIVIDE([Sales Revenue], [Sale Invoices])

Known Customers = CALCULATE(DISTINCTCOUNT(fact_sales[customer_key]),
    fact_sales[transaction_type] = "SALE", fact_sales[customer_key] <> 0)

Rows Unknown Customer = CALCULATE(COUNTROWS(fact_sales), fact_sales[customer_key] = 0)
```

Ba trang dashboard theo Bảng 6 của báo cáo:

| Trang | Thành phần | Bộ lọc |
| --- | --- | --- |
| 1. Tổng quan bán hàng | 4 thẻ số: Sales Revenue, Adjusted Revenue, Sale Invoices, Avg Invoice Value; biểu đồ đường doanh thu theo tháng; biểu đồ cột doanh thu theo quốc gia; ô chữ ghi phạm vi ngày của dữ liệu | Năm, quý, quốc gia |
| 2. Sản phẩm và khách hàng | Biểu đồ cột 10 sản phẩm doanh thu cao nhất (lọc Top N); bảng khách hàng doanh thu cao nhất; thẻ Known Customers | Năm, quốc gia |
| 3. Dữ liệu và quá trình nạp | Thẻ rows\_read, rows\_valid, rows\_rejected, Rows Unknown Customer; bảng từng đợt nạp với thời gian chạy và trạng thái | Đợt nạp |

Lưu ý khi dựng:

- Ghi chú phạm vi ngày trên trang 1 và nêu rõ chỉ so sánh các khoảng thời gian tương đương, vì tháng 12 của ba năm không cùng độ dài.
- Khi so sánh theo tháng, dùng bộ lọc năm để người xem tự chọn khoảng, tránh vẽ cả ba năm trên một trục mà không giải thích.
- Mỗi thẻ số phải khớp kết quả SQL tương ứng sau khi làm tròn 2 chữ số; chụp ảnh từng trang kèm con số SQL để đưa vào báo cáo.
- Lưu `powerbi/retail.pbix` sau mỗi buổi làm, và xuất ảnh ba trang dự phòng cho buổi demo.

## Kiểm thử và nghiệm thu

Bảy tiêu chí ở Bảng 4 của báo cáo đều có cách kiểm tra cụ thể dưới đây. Ghi kết quả thật vào báo cáo cuối kỳ thay cho các "mức dự kiến" hiện có.

| Tiêu chí | Cách kiểm tra | Đạt khi |
| --- | --- | --- |
| Quy mô dữ liệu | `SELECT COUNT(*) FROM dw.fact_sales` | Lớn hơn 100.000 và bằng tổng `rows_inserted` của các đợt nạp |
| Mô hình kho | Đối chiếu danh sách bảng và ràng buộc trong `information_schema` | 1 bảng giao dịch, 4 bảng mô tả, 4 khóa ngoại hoạt động |
| Chạy lại chương trình | Chạy `run_etl.py` lần hai trên cùng file | Số dòng và `SUM(line_amount)` không đổi; `rows_inserted = 0`, `rows_existing = rows_valid` |
| Số dòng | Với mỗi đợt nạp, kiểm tra hai đẳng thức của `reconcile.py` | Cả hai đẳng thức đúng cho cả hai đợt (hai sheet) |
| Số tiền | So `SUM(line_amount)` theo từng `transaction_type` giữa Python, SQL và Power BI | Khớp nhau sau khi làm tròn 2 chữ số |
| Truy vấn phân tích | Chạy Q1 đến Q5 theo cách đo ở mục SQL | Đủ 5 truy vấn, mỗi truy vấn có thời gian và cấu hình máy ghi kèm |
| Dashboard | Đối chiếu từng thẻ số với SQL; thử từng bộ lọc | 3 trang, bộ lọc hoạt động, số liệu khớp SQL |

Ba kiểm tra bổ sung nên làm:

1. Nạp cả file thành một đợt duy nhất (thêm tùy chọn \`--single-batch\` cho \`run\_etl.py\`) vào một database trống khác, rồi so số dòng và tổng tiền với lần nạp hai đợt theo sheet; hai kết quả phải bằng nhau.
2. Tính tay khoảng 20 hóa đơn đã chọn ở tuần 1 (bán, hủy, thiếu mã khách) và so với `fact_sales`.
3. Cố ý làm hỏng một dòng trong bản sao dữ liệu (ví dụ `Quantity` là chữ) để xác nhận dòng đó vào `etl_error` kèm lý do và không làm dừng cả đợt nạp.

Một file `sql/05_checks.sql` gom các kiểm tra lặp lại được:

```sql
-- Số dòng và tổng tiền theo loại giao dịch
SELECT transaction_type, COUNT(*) AS rows_n, ROUND(SUM(line_amount), 2) AS total_amount
FROM dw.fact_sales
GROUP BY transaction_type
ORDER BY transaction_type;

-- Cặp nguồn bị trùng (phải trả về 0 dòng)
SELECT source_file_id, source_row_id, COUNT(*)
FROM dw.fact_sales
GROUP BY source_file_id, source_row_id
HAVING COUNT(*) > 1;

-- Số dòng thiếu mã khách hàng
SELECT COUNT(*) FROM dw.fact_sales WHERE customer_key = 0;

-- Đối chiếu nhật ký nạp
SELECT batch_id, sheet_name, rows_read, rows_valid, rows_rejected, rows_inserted, rows_existing,
       (rows_read = rows_valid + rows_rejected)      AS eq_read_ok,
       (rows_valid = rows_inserted + rows_existing)  AS eq_valid_ok
FROM staging.etl_batch
ORDER BY batch_id;
```

Đến hết tuần 4, mọi tiêu chí ở bảng trên phải có kết quả đo được; tuần 5 chỉ dành cho kiểm tra lần cuối và hoàn thiện báo cáo.

## Kế hoạch 5 tuần

Mỗi tuần kết thúc bằng một mốc kiểm tra; chưa đạt mốc thì chưa sang giai đoạn sau. Kế hoạch bám theo Bảng 7 của báo cáo, chi tiết hóa thành việc cụ thể.

&#91;embedded content: kế hoạch 5 tuần · 6 mảng việc, 4 mốc kiểm tra\]

Mỗi hình thoi là mốc kiểm tra cuối tuần; ETL là mảng mà SQL, Power BI và kiểm thử đều phải chờ.

### Tuần 1: Khảo sát và thiết kế

- [ ] Sửa 8 điểm trong báo cáo cho khớp Online Retail II.
- [ ] Cài môi trường, tạo repo Git, tạo database `retail_dwh`.
- [ ] Tải file, tính SHA-256, đọc thử hai sheet và xác nhận 1.067.371 dòng.
- [ ] Lập hồ sơ dữ liệu trong `docs/data_profile.md`.
- [ ] Chốt quy tắc phân loại, cách xử lý `StockCode` đặc biệt và cách xử lý năm trong dữ liệu.
- [ ] Viết bản nháp `01_schemas.sql`, `02_staging.sql`, `03_dw.sql`.
- [ ] Chọn khoảng 20 hóa đơn để tính tay.

Đầu ra: đề cương đã cập nhật, bản mô tả dữ liệu, thiết kế kho dữ liệu. Mốc kiểm tra: mọi thành viên đọc được file Excel và kết nối được PostgreSQL.

### Tuần 2: Dựng bảng và đọc nguồn

- [ ] Hoàn thiện và chạy ba file SQL tạo bảng; kiểm tra khóa và quan hệ.
- [ ] Sinh dữ liệu cho `dim_date` phủ toàn khoảng ngày của dữ liệu.
- [ ] Viết `extract.py`: SHA-256, đọc hai sheet, `source_row_id` liên tục, ghi `etl_batch`.
- [ ] Nạp dữ liệu thô vào `staging.raw_online_retail`.
- [ ] Viết bản đầu của `clean.py`: đổi tên cột, ép kiểu, ghi `etl_error`.

Đầu ra: file SQL tạo bảng, dữ liệu nguồn trong staging. Mốc kiểm tra: staging có đủ 1.067.371 dòng, schema `dw` tạo xong không lỗi.

### Tuần 3: Hoàn thiện ETL

- [ ] Hoàn thiện `clean.py` và viết `classify.py` theo 5 điều kiện phân loại.
- [ ] Viết `load_dims.py`, gồm dòng `customer_key = 0` và quy tắc chọn tên sản phẩm.
- [ ] Viết `load_fact.py`: `COPY` vào bảng tạm rồi `INSERT ... ON CONFLICT DO NOTHING`.
- [ ] Viết `reconcile.py` với các đẳng thức số dòng, khóa và tổng tiền.
- [ ] Chạy đủ hai đợt, rồi chạy lại để kiểm tra không nhân đôi dữ liệu.
- [ ] Bắt đầu viết 5 truy vấn phân tích.

Đầu ra: chương trình nạp được dữ liệu, kết quả kiểm tra chạy lại. Mốc kiểm tra: lần chạy thứ hai có `rows_inserted = 0` và tổng tiền không đổi.

### Tuần 4: Phân tích và dashboard

- [ ] Hoàn thiện Q1 đến Q5, truy vấn chỉ số, và đo thời gian chạy.
- [ ] Viết `05_checks.sql`.
- [ ] Kết nối Power BI, tạo quan hệ và các measure.
- [ ] Dựng 3 trang dashboard với bộ lọc.
- [ ] Đối chiếu từng thẻ số với SQL, chụp ảnh từng trang.
- [ ] Làm ba kiểm tra bổ sung: nạp một đợt, tính tay 20 hóa đơn, dòng lỗi cố ý.

Đầu ra: file `.pbix` và bảng đối chiếu với SQL. Mốc kiểm tra: mọi tiêu chí ở Bảng 4 đã có kết quả đo được.

### Tuần 5: Hoàn thiện và nộp

- [ ] Viết lại mục 3 và mục 4 của báo cáo bằng số liệu thật: số dòng, thời gian chạy, ảnh dashboard.
- [ ] Viết `README` hướng dẫn chạy từ đầu và hoàn thiện `requirements.txt`.
- [ ] Xuất PDF, kiểm tra lại tài liệu tham khảo và các đường dẫn.
- [ ] Chạy thử demo từ database trống; chuẩn bị ảnh dự phòng.
- [ ] Đóng gói SQL, Python, `.pbix`, README, PDF và nộp trên E-learning.

Đầu ra: bộ mã nguồn, dashboard, PDF, kịch bản demo. Mốc kiểm tra: một thành viên không viết mã làm theo `README` và chạy được toàn bộ trên máy sạch.

## Phân công và rủi ro

Báo cáo chia việc thành bốn mảng và để phân công cụ thể cho buổi họp đầu tuần 1. Bảng dưới gợi ý ranh giới giữa các mảng để mỗi người biết mình giao đầu ra cho ai; ghi tên người phụ trách vào bảng khi nhóm thống nhất.

| Mảng việc | Việc chính | Giao đầu ra cho | Cách tránh phải chờ nhau |
| --- | --- | --- | --- |
| Tìm hiểu dữ liệu | Hồ sơ dữ liệu, quy tắc phân loại, danh sách hóa đơn tính tay | Mảng PostgreSQL và Python | Chốt quy tắc trong tuần 1 |
| Thiết kế PostgreSQL | Schema, bảng, khóa, chỉ mục, `05_checks.sql` | Mảng Python và Power BI | Nạp một mẫu khoảng 50.000 dòng vào database dev riêng ở cuối tuần 2 |
| Lập trình Python | Năm module ETL, `reconcile.py`, `README` | Mảng Power BI | Báo ngay khi `fact_sales` nạp xong ở tuần 3 |
| Xây dựng Power BI | Quan hệ, measure, 3 trang, ảnh dự phòng | Báo cáo | Dựng bố cục trên mẫu 50.000 dòng từ tuần 3 |

Cả nhóm cùng kiểm tra số liệu, hoàn thiện báo cáo và chuẩn bị phần trình bày, đúng như báo cáo nêu.

Các rủi ro thường gặp và cách xử lý:

| Rủi ro | Cách xử lý |
| --- | --- |
| Đọc Excel hơn một triệu dòng chậm hoặc hết RAM | Dùng bản CSV tạm khi phát triển; đọc từng sheet; ghi staging theo khối 50.000 dòng |
| Mã khách hàng bị đọc thành số thực (có đuôi `.0`) | Đọc mã dạng chuỗi, chuẩn hóa về số nguyên, có một kiểm tra riêng |
| Số tiền lệch giữa Python, SQL và Power BI | Dùng `Decimal` và `numeric`, một quy tắc phân loại duy nhất, làm tròn 2 chữ số ở cùng một bước |
| Chạy lại làm nhân đôi dữ liệu | Ràng buộc duy nhất trên cặp mã file và số dòng; thử chạy lại ngay trong tuần 3 |
| Dòng bị mất khi nối khóa mô tả | Nạp mô tả trước; đẳng thức số dòng; dòng `customer_key = 0` cho khách thiếu mã |
| Power BI không chạy trên máy một thành viên | Xác định người dùng Windows ở tuần 1 và thử kết nối PostgreSQL ngay |
| So sánh sai mức tăng giảm do tháng 12 không cùng độ dài | Chỉ so khoảng tương đương và ghi chú phạm vi ngày trên dashboard |
| Hiểu dòng hủy là đã hoàn tiền | Gọi chỉ số là "hủy và điều chỉnh âm" và giữ câu giới hạn trong báo cáo |
| Lỗi kết nối ngày demo | Có sẵn ảnh dashboard và bản dữ liệu dự phòng, như báo cáo đã nêu |

## Bàn giao, nộp bài và demo

Bộ nộp gồm năm thành phần theo báo cáo, và được coi là xong khi mọi mục dưới đây đã tick.

- [ ] Các file SQL tạo bảng: `01_schemas.sql`, `02_staging.sql`, `03_dw.sql`, `04_analysis_queries.sql`, `05_checks.sql`.
- [ ] Mã Python trong thư mục `etl/`, kèm `requirements.txt` và `.env.example`.
- [ ] File Power BI `retail.pbix`.
- [ ] `README` hướng dẫn chạy từ database trống đến dashboard.
- [ ] Báo cáo kỹ thuật PDF, có mô hình bảng, quy tắc xử lý, ảnh dashboard và kết quả kiểm tra.

Checklist trước khi xuất PDF:

- [ ] Mọi số dòng, số tiền và thời gian trong báo cáo là số đo thật, không còn chữ "dự kiến" ở các bảng kết quả.
- [ ] Tên dataset, số dòng, khoảng ngày và DOI trong báo cáo khớp Online Retail II.
- [ ] Câu giới hạn về doanh thu (chưa kiểm toán, chưa xác nhận hoàn tiền) vẫn còn.
- [ ] Ghi nguồn dữ liệu theo giấy phép CC BY 4.0.
- [ ] Nếu có dịch năm trong dữ liệu, báo cáo nói rõ điều đó.
- [ ] Các đường dẫn tài liệu tham khảo mở được; cập nhật ngày truy cập.

Kịch bản demo, theo thứ tự nạp dữ liệu, kiểm tra PostgreSQL, làm mới Power BI như báo cáo đã nêu:

1. Trình bày ngắn mô hình hình sao: một bảng giao dịch, bốn bảng mô tả.
2. Chạy `run_etl.py` trên database trống và chỉ vào số dòng đọc, hợp lệ, lỗi, nạp mới trong log. Nếu cả file chạy quá lâu, nạp sẵn sheet đầu và chỉ chạy trực tiếp sheet thứ hai (thời gian chạy đã đo ở tuần 4).
3. Mở pgAdmin và chạy `05_checks.sql`: số dòng, tổng tiền theo loại, hai đẳng thức đối chiếu.
4. Chạy lại `run_etl.py` và cho thấy `rows_inserted = 0`.
5. Mở Power BI, làm mới dữ liệu, đi qua ba trang, thử một bộ lọc và đối chiếu một con số với SQL.
6. Nếu kết nối lỗi, chuyển sang ảnh dashboard và bản dữ liệu dự phòng.

### Nguồn

- [UCI, Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) và [Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail)
- [OpenML, Online-Retail-II-UCI](https://api.openml.org/d/43368)
- [Kaggle, mô tả hai sheet của Online Retail II](https://www.kaggle.com/datasets/lakshmi25npathi/online-retail-dataset)
- [pandas, read\_excel](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html)
- [PostgreSQL, Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [Microsoft Learn, star schema trong Power BI](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema) và [PostgreSQL connector](https://learn.microsoft.com/en-us/power-query/connectors/postgresql)
