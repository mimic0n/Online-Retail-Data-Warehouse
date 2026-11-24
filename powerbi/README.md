# Dựng dashboard Power BI

Mở [retail.pbix](retail.pbix) bằng Power BI Desktop trên Windows. Chọn **Home → Refresh** để đọc dữ liệu mới từ `retail_dwh`. Khi được hỏi thông tin đăng nhập, chọn **Database** và dùng tài khoản PostgreSQL có quyền đọc hai schema `dw` và `staging`.

| Trang đã lưu | Nội dung |
|---|---|
| Tổng Quan Bán Hàng | Mười thẻ KPI, doanh thu theo tháng và quốc gia. |
| Sản phẩm và khách hàng | Hai bảng xếp hạng và thẻ Known Customers. Bộ lọc Top N trên mã sản phẩm có thể hiển thị nhiều dòng mô tả cho một mã. |
| Dữ liệu và quá trình nạp | Bốn thẻ chất lượng dữ liệu, lịch sử lô và bộ lọc phân cấp theo batch_id, rows_read. |

Để đối chiếu sản phẩm ở đúng cấp chi tiết của kho, dùng `dim_product[product_key]` làm trường lọc Top N theo Sales Revenue và đưa khóa này vào bảng cùng mã và mô tả. Khóa số phân biệt các sản phẩm có mã chỉ khác chữ hoa/thường. [Kết quả SQL và ảnh ba trang](../docs/report/BAO_CAO_TRIEN_KHAI.md#đối-chiếu-power-bi).

## Cấu hình khi dựng lại báo cáo

1. Get Data → PostgreSQL, nhập server và database, chọn Import. Dùng tài khoản chỉ đọc cho báo cáo.
2. Chọn `dw.fact_sales`, bốn bảng `dw.dim_*`, `staging.etl_batch`. Có thể dùng mẫu `source.pq` cho từng bảng; không ghi mật khẩu vào M.
3. Tạo quan hệ 1:* từ mỗi dimension tới fact theo khóa; hướng lọc single từ dimension tới fact. Mark as date table cho `dim_date.full_date`. Không bật auto date/time.
4. Tạo cột Month Start = DATE(dim_date[year], dim_date[month], 1). Dùng trục tháng này, tránh gộp tháng của nhiều năm.
5. Nhập từng measure từ `measures.dax`; đặt unit_price và line_amount thành Fixed decimal number (4 số lẻ), ngày full_date là Date và invoice_datetime là Date/Time; tiền hiển thị GBP, 2 số lẻ. Không tự phân loại giao dịch trong DAX.
6. Trang Tổng quan: bốn card Sales Revenue, Adjusted Revenue, Sale Invoices, Avg Invoice Value; đường doanh thu theo tháng; cột theo quốc gia; slicer năm/quý/quốc gia. Chú thích phạm vi gốc 01/12/2009–09/12/2011, tháng 12/2011 chưa đủ tháng.
7. Trang Sản phẩm và khách hàng: Top N 10 sản phẩm theo Sales Revenue; bảng top khách với customer_key <> 0; card Known Customers; slicer năm/quốc gia.
8. Trang Dữ liệu và quá trình nạp: card Rows Read, Rows Valid, Rows Rejected và Rows Unknown Customer; bảng batch, trạng thái, thời gian, số dòng; slicer batch_id.

Tạo quan hệ `etl_batch[batch_id]` 1:* tới `fact_sales[batch_id]` chỉ khi muốn lọc các fact được nạp mới bởi batch đó. Lần chạy lại có số dòng fact mới bằng 0. Tổng Rows Read/Valid trong lịch sử bao gồm mọi lần chạy, không phải số dòng duy nhất trong kho. Khi đối chiếu hai sheet gốc, chọn đúng hai batch SUCCESS đầu tiên. Rows Unknown Customer theo batch phản ánh fact được batch đó nạp lần đầu; không phải mọi dòng được batch đọc lại.

Đối chiếu từng card với SQL Q1–Q5/KPI và `05_checks.sql`, cả khi có bộ lọc. Làm tròn 2 số lẻ ở bước hiển thị. Lưu `retail.pbix`, xuất ảnh 3 trang và ghi kết quả vào `docs/results/`. Chỉ so 01–09/12 giữa ba năm, hoặc tháng 12/2009 với 12/2010.

Phân loại hủy phục vụ phân tích; chưa xác nhận hoàn tiền hay đối chiếu đơn hủy với đơn gốc.
