# Hồ sơ dữ liệu thực tế

Nguồn cục bộ: `data/raw/online-retail-ii.xlsx`
SHA-256: `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`
Thời điểm lập hồ sơ UTC: 2026-11-15T14:28:20.645084+00:00

Đếm trực tiếp workbook bằng bộ đọc streaming. Giữ ngày gốc và toàn bộ dòng trùng; giữ mã phí đặc biệt. File CSV có sẵn không được dùng làm nguồn chuẩn.

| Sheet | Số dòng |
|---|---:|
| Year 2009-2010 | 525,461 |
| Year 2010-2011 | 541,910 |

| Kiểm tra | Kết quả |
|---|---:|
| read | 1,067,371 |
| missing_customer | 243,007 |
| missing_description | 4,382 |
| c_prefix | 19,494 |
| duplicate_rows | 34,335 |
| valid | 1,061,163 |
| rejected | 6,208 |
| Số lẻ Price tối đa | 3 |

Phạm vi ngày hợp lệ: 2009-12-01 07:45:00 → 2011-12-09 12:50:00.

| Loại | Dòng hợp lệ | Tổng tiền GBP |
|---|---:|---:|
| SALE | 1,041,670 | 20972594.5680 |
| RETURN_CANCELLATION | 19,493 | -1527041.4300 |

| Lỗi | Số dòng |
|---|---:|
| NON_POSITIVE_PRICE | 6,207 |
| CANCELLATION_POSITIVE_QUANTITY | 1 |

Chi tiết quốc gia, mã đặc biệt, dấu số lượng/giá và mẫu hóa đơn ở file JSON cạnh tài liệu này.
Các mẫu hóa đơn là tổng được tính tự động để đối chiếu, chưa phải xác minh thủ công.
Số liệu trên là kết quả Python trên nguồn, chưa phải bằng chứng kho PostgreSQL đã nạp thành công.

Quy tắc: khách thiếu mã dùng khóa 0; tên sản phẩm lấy mô tả không trống tại ngày giao dịch gần nhất, hòa ngày chọn mã file rồi số dòng lớn hơn. Thiếu mô tả hoàn toàn dùng Unknown product.
Phân loại hủy phục vụ phân tích, chưa xác nhận hoàn tiền hay đối chiếu từng đơn hủy với đơn gốc.

Ghi nguồn theo kế hoạch: D. Chen (2012), UCI Online Retail II, DOI 10.24432/C5CG6D, CC BY 4.0. Ngày tải file chưa được cung cấp; không suy ra từ thời gian sửa file.
