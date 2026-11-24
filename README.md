# Online Retail II — Kho dữ liệu bán lẻ trực tuyến

Hệ thống PostgreSQL theo mô hình sao, ETL Python theo từng sheet Excel và bộ truy vấn/measure cho Power BI. Nguồn chuẩn là `data/raw/online-retail-ii.xlsx`; giữ ngày gốc 2009–2011, giữ mã phí và dòng trùng nghiệp vụ. Mỗi dòng được nhận diện bằng SHA-256 của file và số dòng liên tục trên tất cả sheet.

Hướng dẫn riêng cho CachyOS/Arch Linux: [README.linux.md](README.linux.md).

## Khởi chạy

Cần Python >=3.11, PostgreSQL 15/16 (kiểm thử cục bộ bổ sung trên PostgreSQL 18) và Power BI Desktop trên Windows để dựng `.pbix`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Sửa `DATABASE_URL` trong `.env`. Khi dùng PostgreSQL đã cài, tạo database `retail_dwh` thuộc tài khoản riêng của dự án. Khi dùng Docker Compose, thêm `POSTGRES_PASSWORD` vào `.env`, đặt cùng mật khẩu trong `DATABASE_URL`, rồi chạy:

```bash
docker compose up -d
python -m etl.run_etl --init
```

Lần đầu tạo schema và nạp hai sheet thành hai batch. Có thể chạy SQL `01`–`03` bằng `psql` thay `--init`. DDL chỉ tạo các đối tượng còn thiếu; không tự sửa schema cũ.

```bash
python -m etl.run_etl --init-only
python -m etl.run_etl
python -m etl.run_etl                 # kiểm tra chạy lại: inserted=0
python -m etl.run_etl --sheet 'Year 2010-2011'
python -m etl.run_etl --single-batch   # dùng database trống khác để so sánh
python -m etl.profile                # lập hồ sơ trực tiếp Excel, không cần database
python -m etl.benchmark              # Q1–Q5 và KPI, 5 lần EXPLAIN mỗi truy vấn
```

Nguồn mặc định có thể thay bằng `--source path.xlsx`. `--chunk-size` mặc định 50.000; `--sheet` vẫn giữ số dòng toàn cục bằng cách duyệt sheet trước. `--single-batch` và `--sheet` không dùng chung. Bộ đọc XLSX streaming dùng thư viện chuẩn để không giữ cả triệu dòng trong RAM; không cần bản CSV trung gian. Workbook yêu cầu đúng tám tên cột trong kế hoạch. Không dịch năm tự động.

## Thiết kế và tính đúng

- `staging.etl_batch`: lịch sử từng lần chạy, SUCCESS/FAILED và kết quả đối chiếu JSON.
- `staging.raw_online_retail`: các giá trị nguồn sau đọc Excel, khóa duy nhất file/dòng. Đọc số Excel theo ngữ nghĩa số thực như openpyxl trước khi chuyển sang Decimal; tránh giữ nhiễu XML như `0.84999999999999998`. Ngày được chuyển từ serial Excel về timestamp, làm tròn tới giây.
- `staging.etl_error`: mỗi dòng không hợp lệ có lý do và JSON nguồn. Không xóa dòng trùng nghiệp vụ.
- `dw.fact_sales`: 14 cột, bốn khóa dimension và khóa batch; `numeric(12,4)`/`numeric(14,4)` và ràng buộc số tiền.
- `dw.dim_date`, `dim_product`, `dim_customer`, `dim_country`: khách thiếu mã dùng khóa 0; sản phẩm dùng mô tả không trống mới nhất theo ngày giao dịch. Hòa ngày chọn SHA file, rồi số dòng lớn hơn. Có metadata thời điểm mô tả để sheet nạp sau không ghi đè bằng tên cũ.

Quy tắc phân loại chỉ nằm trong `etl/classify.py`: số lượng 0/giá <=0 bị loại; mã C với lượng dương bị loại; C với lượng âm là RETURN_CANCELLATION; lượng dương là SALE; lượng âm còn lại là ADJUSTMENT. Lỗi kiểu, mã bắt buộc thiếu, số vượt miền hoặc giá quá bốn số lẻ đều ghi lỗi. Mã khách có `.0` được chuẩn hóa; thiếu khách vẫn giữ dòng.

Mỗi sheet dùng một transaction cho staging, lỗi, dimension, fact và đối chiếu; lỗi hệ thống rollback cả sheet và đánh dấu FAILED riêng. Sheet đã thành công trước đó được giữ. Nhật ký RUNNING được commit trước khi xử lý; nếu tiến trình bị kill/mất điện có thể còn RUNNING và phải kiểm tra trước khi ghi nhận thất bại. Không giữ staging của sheet rollback. Một advisory lock cấp session ngăn các ETL chạy đồng thời trong cùng database.

COPY theo khối vào bảng tạm, rồi JOIN dimension và INSERT ON CONFLICT. Đối chiếu số dòng, giá trị/khóa dimension, tổng tiền từng loại với Decimal tích lũy độc lập trong Python. Chạy lại vẫn kiểm tra các fact có sẵn. Thay đổi nội dung workbook làm đổi SHA và được xem là nguồn mới; không dùng file đã chỉnh sửa để thay thế âm thầm dữ liệu cũ.

## SQL và Power BI

`sql/04_analysis_queries.sql` có Q1–Q5, KPI và so sánh ngày 01–09/12. `sql/05_checks.sql` kiểm tra số dòng, khóa, lịch sử và tổng tiền. Chạy bằng `psql` với cấu hình kết nối của bạn; không đưa mật khẩu lên dòng lệnh.

`python -m etl.benchmark` xuất CSV kết quả cùng thời gian trung vị, execution plans, phiên bản PostgreSQL và chỉ mục vào `docs/results/`. Bổ sung RAM, ổ đĩa và model CPU thực tế khi đưa vào báo cáo; công cụ chưa tự thu thập đủ phần cứng.

Xem [hướng dẫn Power BI](powerbi/README.md), [measures DAX](powerbi/measures.dax) và [nguồn Power Query](powerbi/source.pq). Chưa có file `retail.pbix` hay ảnh dashboard đã kiểm chứng. Cần dựng và đối chiếu trên Windows. Tổng lịch sử batch bao gồm các lần đọc lại, khác số dòng fact duy nhất.

## Kiểm tra

```bash
python -m unittest discover -s tests -v
python -m tests.check_postgres
python -m tests.check_full_postgres
```

Hai lệnh cuối cần binary `initdb` và `postgres`, tạo cluster tạm, không mở cổng và không đụng database của người dùng. Bộ full kiểm tra toàn bộ workbook, nạp hai sheet, chạy lại không chèn mới, đối chiếu Decimal/SQL và tương đương nạp một batch. Đây là kiểm tra cleaning/SQL thực, chưa thay thế kiểm thử tích hợp runner qua psycopg2 và Power BI. Các file log/JSON trong `docs/results/` ghi bằng chứng, không phải số dự kiến.

Báo cáo triển khai và phạm vi nghiệm thu tại [docs/report/BAO_CAO_TRIEN_KHAI.md](docs/report/BAO_CAO_TRIEN_KHAI.md).

Hồ sơ dữ liệu tại [docs/data_profile.md](docs/data_profile.md), chi tiết ở JSON cùng tên. Mẫu hóa đơn trong JSON được tính tự động; vẫn cần kiểm tra tay khoảng 20 hóa đơn. CSV có sẵn trong `data/raw/` chưa được xác nhận cùng phạm vi Excel và không được dùng để nạp.

## Nguồn và giới hạn

Theo kế hoạch dự án: D. Chen (2012), UCI Online Retail II, DOI `10.24432/C5CG6D`, CC BY 4.0. File dữ liệu và thông tin kết nối bị loại khỏi Git. Chưa có ngày tải được xác nhận.

Phân loại hủy phục vụ phân tích, chưa xác nhận hoàn tiền hay đối chiếu từng đơn hủy với đơn gốc. Chỉ so tháng 12 với khoảng ngày tương đương. Không có báo cáo gốc khác trong repo để sửa tám vị trí được kế hoạch nhắc tới; chưa có PDF báo cáo cuối kỳ.
