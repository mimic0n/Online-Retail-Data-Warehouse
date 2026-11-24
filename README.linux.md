# Chạy Online Retail II trên Linux — CachyOS

Hướng dẫn này dùng PostgreSQL cài trực tiếp trên CachyOS/Arch Linux. Python ETL và SQL chạy trên Linux; phần Power BI Desktop cần Windows. Thực hiện các lệnh trong terminal bằng tài khoản người dùng thông thường, chỉ dùng `sudo` ở những lệnh ghi rõ.

## 1. Cài công cụ

```bash
sudo pacman -Syu
sudo pacman -S python python-pip postgresql

python --version
psql --version
```

Dự án cần Python từ 3.11. CachyOS là bản phân phối rolling release; phiên bản PostgreSQL trong kho có thể mới hơn 15/16 trong kế hoạch. Bộ SQL đã được kiểm tra thêm trên PostgreSQL 18. Sau khi nâng phiên bản major PostgreSQL, cần thực hiện quy trình nâng cấp cluster tương ứng trước khi khởi động lại dịch vụ.

## 2. Khởi tạo PostgreSQL

Kiểm tra máy đã có cluster chưa:

```bash
sudo test -f /var/lib/postgres/data/PG_VERSION && echo 'Đã có cluster PostgreSQL'
```

**Chỉ chạy lệnh sau khi chưa có cluster tại đường dẫn này.** Nếu đã có dữ liệu, giữ nguyên cluster và chuyển sang khởi động dịch vụ.

```bash
sudo -iu postgres initdb \
  --locale=C.UTF-8 --encoding=UTF8 \
  -D /var/lib/postgres/data
```

Khởi động dịch vụ và bật tự khởi động cùng máy:

```bash
sudo systemctl enable --now postgresql
systemctl status postgresql --no-pager
```

Nếu `initdb` báo locale không hợp lệ, xem các locale đã có bằng `locale -a` và chọn locale UTF-8 tương ứng. Nếu dịch vụ không khởi động, đọc lỗi bằng:

```bash
sudo journalctl -u postgresql -n 80 --no-pager
```

## 3. Tạo tài khoản và database

```bash
sudo -iu postgres createuser --pwprompt retail
sudo -iu postgres createdb --owner=retail retail_dwh
```

Nhập mật khẩu cho tài khoản `retail` khi được hỏi. Nếu role/database đã tồn tại, không cần tạo lại. Kiểm tra kết nối TCP giống cách runner sẽ dùng:

```bash
psql -h localhost -U retail -d retail_dwh -W \
  -c 'SELECT current_user, current_database(), version();'
```

`-W` yêu cầu nhập mật khẩu; lệnh này không tự bật xác thực mật khẩu trên server. Nếu cluster mới dùng `trust` cho localhost và bạn muốn xác thực bằng mật khẩu, xem mục xử lý xác thực bên dưới.

## 4. Chuẩn bị dự án

```bash
cd "/home/grey/Projects/DataWarehouse/Online Retail Data Warehouse"

python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Trên máy khác, thay đường dẫn `cd` bằng thư mục đã tải dự án. Các lần mở terminal sau chỉ cần `cd` vào dự án và kích hoạt lại `.venv`.

Đảm bảo có file nguồn:

```bash
ls -lh data/raw/online-retail-ii.xlsx
```

Dữ liệu không được đưa lên Git. Nếu vừa clone dự án, cần đặt workbook Online Retail II vào đường dẫn này. File CSV có sẵn không thay thế nguồn Excel trong runner.

Tạo cấu hình nếu chưa có `.env`:

```bash
if [ ! -f .env ]; then cp .env.example .env; fi
chmod 600 .env
nano .env
```

Nội dung ví dụ:

```dotenv
DATABASE_URL=postgresql://retail:MAT_KHAU@localhost:5432/retail_dwh
SOURCE_FILE=data/raw/online-retail-ii.xlsx
CHUNK_SIZE=50000
```

Thay `MAT_KHAU` bằng mật khẩu đã đặt. Nếu mật khẩu chứa ký tự đặc biệt như `@`, `:`, `/`, `#`, `%`, cần percent-encode phần mật khẩu trong URL. Không đưa `.env` lên Git.

## 5. Khởi tạo bảng và chạy ETL

```bash
python -m etl.run_etl --init
```

Lệnh này tạo schema/bảng nếu còn thiếu và nạp hai sheet thành hai batch. DDL không tự nâng cấp cấu trúc bảng cũ.

Nếu chỉ muốn tạo bảng trước:

```bash
python -m etl.run_etl --init-only
python -m etl.run_etl
```

Chạy lại cùng workbook để kiểm tra chống trùng:

```bash
python -m etl.run_etl
```

Kết quả mong đợi cho từng sheet: `status=SUCCESS`, `rows_inserted=0`, `rows_existing` bằng số dòng hợp lệ của sheet. Các dòng trùng nghiệp vụ ở vị trí nguồn khác nhau vẫn được giữ.

Một số tùy chọn:

```bash
python -m etl.run_etl --sheet 'Year 2010-2011'
python -m etl.run_etl --chunk-size 10000
python -m etl.run_etl --source /duong/dan/online-retail-ii.xlsx
```

Dùng chunk nhỏ hơn có thể giảm bộ nhớ Python, nhưng mỗi sheet vẫn là một transaction. Chỉ thử `--single-batch` trên database trống khác nếu muốn đối chiếu hai cách nạp; tùy chọn này không tạo database mới.

## 6. Kiểm tra dữ liệu và phân tích

```bash
psql -h localhost -U retail -d retail_dwh -W \
  -v ON_ERROR_STOP=1 -f sql/05_checks.sql

psql -h localhost -U retail -d retail_dwh -W \
  -v ON_ERROR_STOP=1 -f sql/04_analysis_queries.sql
```

Với đúng workbook có SHA-256 trong `docs/data_profile.md`, kết quả kiểm tra nguồn trước đây là:

| Chỉ số | Giá trị |
|---|---:|
| Tổng dòng nguồn | 1.067.371 |
| Dòng hợp lệ | 1.061.163 |
| Dòng bị loại | 6.208 |
| Doanh thu SALE, GBP | 20.972.594,5680 |
| Tổng RETURN_CANCELLATION, GBP | -1.527.041,4300 |

Đây là mốc đối chiếu từ kiểm tra trên cluster tạm, không phải xác nhận database dịch vụ của bạn đã được nạp. Nếu workbook khác nội dung, SHA thay đổi và hệ thống xem đó là nguồn mới.

Lập hồ sơ và đo thời gian truy vấn:

```bash
python -m etl.profile
python -m etl.benchmark
```

Profile ghi vào `docs/data_profile.md` và JSON cùng tên. Benchmark ghi CSV và `benchmark.json` vào `docs/results/`, chạy mỗi truy vấn năm lần và lấy trung vị. Các lệnh này có thể ghi đè kết quả đã có trong dự án.

## 7. Chạy kiểm thử

```bash
python -m unittest discover -s tests -v
python -m tests.check_postgres
python -m tests.check_full_postgres
```

Hai lệnh cuối cần `initdb` và `postgres` trên PATH. Chạy bằng tài khoản thường, không dùng root. Chúng tạo cluster tạm, không mở cổng và không thay đổi database dịch vụ. Kiểm tra full đọc cả workbook và cần dung lượng trống cho CSV, database tạm và WAL; thời gian chạy tùy máy. Log/JSON kết quả được ghi vào `docs/results/`.

Các kiểm tra này xác minh quy tắc Python và SQL nạp thực tế. Để kiểm tra runner qua `psycopg2`, vẫn cần chạy các bước 5–6 trên PostgreSQL dịch vụ.

## 8. Xử lý lỗi thường gặp

### `externally-managed-environment` hoặc thiếu module

Cài thư viện vào venv, không dùng `sudo pip` hoặc sửa Python hệ thống:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Nếu nâng cấp Python của CachyOS khiến venv cũ không còn hoạt động, đổi tên venv cũ rồi tạo lại `.venv` bằng Python mới và cài requirements.

### `connection refused`

Kiểm tra PostgreSQL đang chạy và cấu hình đúng host/port:

```bash
systemctl status postgresql --no-pager
pg_isready -h localhost -p 5432
```

Nếu dùng port khác, sửa cả `.env` và các lệnh `psql`. `pg_isready` chỉ kiểm tra trạng thái server, không xác nhận mật khẩu đúng.

### `password authentication failed`, `peer authentication failed` hoặc localhost dùng `trust`

Dùng `-h localhost` để kiểm tra kết nối TCP, tránh nhầm với xác thực peer qua Unix socket. Kiểm tra role và đặt lại mật khẩu bằng lệnh tương tác nếu cần:

```bash
sudo -iu postgres psql -c '\password retail'
```

Xác định đúng file cấu hình xác thực của cluster:

```bash
sudo -iu postgres psql -Atc 'SHOW hba_file;'
```

Nếu muốn bắt buộc mật khẩu cho role/database dự án, sửa file vừa tìm được và đặt hai dòng sau **trước các dòng localhost rộng hơn**:

```text
host    retail_dwh    retail    127.0.0.1/32    scram-sha-256
host    retail_dwh    retail    ::1/128         scram-sha-256
```

PostgreSQL dùng dòng khớp đầu tiên. Giữ kết nối quản trị cục bộ bằng tài khoản `postgres`, rồi tải lại cấu hình và thử lại `psql`:

```bash
sudo systemctl reload postgresql
```

### `permission denied for schema` hoặc database thuộc tài khoản khác

Database mới nên được tạo với `--owner=retail` như bước 3. Nếu đang tái sử dụng database có bảng cũ thuộc role khác, cần kiểm tra owner/quyền của các schema và bảng; không xóa database để xử lý lỗi quyền.

### Không tìm thấy file nguồn

Chạy lệnh từ thư mục gốc dự án, kiểm tra `SOURCE_FILE` trong `.env`, hoặc truyền đường dẫn tuyệt đối bằng `--source`. Nếu tên file có khoảng trắng, đặt đường dẫn trong dấu ngoặc kép.

## 9. Dashboard trên Linux

Mở [retail.pbix](powerbi/retail.pbix) bằng Power BI Desktop trên Windows hoặc máy ảo Windows. Dùng **Home → Refresh** sau khi nạp dữ liệu mới.

Nếu Power BI ở máy ảo, `localhost` trong máy ảo trỏ tới Windows, không phải máy CachyOS. Cần cấu hình địa chỉ host phù hợp với mạng máy ảo, `listen_addresses`, quy tắc `pg_hba.conf` và firewall để cho phép đúng máy đó truy cập PostgreSQL.

Có thể xem ảnh ba trang và kết quả đối chiếu ngay trên Linux qua [báo cáo triển khai](docs/report/BAO_CAO_TRIEN_KHAI.md#đối-chiếu-power-bi).

## Tài liệu liên quan

- [README tổng quan](README.md)
- [Hướng dẫn Power BI](powerbi/README.md)
- [Hồ sơ dữ liệu](docs/data_profile.md)
- [Báo cáo triển khai](docs/report/BAO_CAO_TRIEN_KHAI.md)
- [ArchWiki: PostgreSQL](https://wiki.archlinux.org/title/PostgreSQL) — tham khảo cấu hình PostgreSQL trên hệ Arch.
