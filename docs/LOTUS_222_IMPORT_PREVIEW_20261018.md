# Nạp dữ liệu mẫu Vườn 222 và dự kiến trổ khu A (18/10/2026)

## Nguồn và phân loại
- File người dùng: `Lo_lon_lo_nho_va_so_cay_222.xlsx`, SHA256 `1e71054ce186babac7be6b19432557b7a912b29ea4043ba3fda20f70b7128435`.
- Tab **Lô lớn**: 64 lô lớn, 215,16 ha; 30 lô có số cây, tổng số đếm đã có là 227.004 cây; 34 lô chưa có số.
- Tab **Lô nhỏ**: 210 dòng, kiểm tra tổng diện tích khớp 64 lô lớn. Không đưa lô nhỏ vào hệ thống hoạt động.
- Khu A: 13 lô lớn, 8 có số cây (63.283 cây), 5 thiếu số (A1, A2, A3, A4, A12).
- Ngày dự kiến **trổ hoa 01/11/2026**, theo người dùng nói khu A còn khoảng hai tuần từ 18/10/2026. Chưa có bằng chứng đã trổ.
- Khung thu tham khảo **10/01–07/02/2027**, lấy 10–14 tuần sau trổ theo FAO Việt Nam (https://www.fao.org/4/ad523e/ad523e05.htm). Khoảng này không phải đơn thu đã duyệt hoặc đúng cho mọi giống và thời tiết.

## Cơ chế nhập (an toàn)
- Dữ liệu Excel được chuyển thành CSV 64 dòng và lưu **ngoài repo**, tại site Frappe `sites/frontend/private/files/lotus_222_import_preview_20261018.csv` với quyền hệ thống.
- API chỉ đọc `lotus_farm.forecast_import_preview.preview`, kiểm tra quyền `Farm Block` và `Harvest Forecast`, đọc và lọc theo quyền của người dùng và vườn/lô.
- Biểu mẫu nằm trong trang `/lotus/forecast`, sau màn dự thu, cho người vận hành xem số cây đã đếm, phần thiếu và dự kiến khu A. Không ảnh hưởng PWA điện thoại.
- Không dùng **số cây được đếm qua ảnh** làm `planting_density` (mật độ trồng ban đầu).
- Không tạo bản ghi `Shooting` đã thực hiện từ một ngày còn dự kiến.
- Không seed hệ số, sản lượng, phiếu thu, kho, mua hàng hoặc cam kết bán.
- CSV nhập riêng cần được bảo quản và đối chiếu thực địa trước khi tạo bản ghi vận hành.

## Kiểm tra
- 64 mã lô duy nhất; so diện tích với Farm Block đang có (dung sai 0,03 ha). Hiển thị cảnh báo nếu lệch.
- Trong Excel, các mã lô nhỏ cộng đúng lô lớn, tổng 215,16 ha.
- Gọi API với quyền hạn chế để kiểm tra không lộ lô trái quyền. Dữ liệu không được xuất bản trong bundle JS, ảnh hoặc Git công khai.
- Site `frontend` chưa có bộ Harvest Profile Approved, vì vậy không thể suy ra tấn thành phẩm chính thức từ ngày trổ mẫu.
