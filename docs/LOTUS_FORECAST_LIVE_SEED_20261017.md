# Dự thu 36 tháng: dữ liệu minh họa và đưa lên máy chạy Lotus

## Đã xác minh dữ liệu vận hành
- Farm LOTUS-222 và LOTUS-180 đang tồn tại.
- Vườn 222 có 64 Lô đã lập danh mục từ nguồn bản đồ, **không phải dữ liệu trồng**.
- Chưa có bộ hệ số dự thu đã duyệt; các lô hiện chưa có ngày trồng hay mật độ cây.
- Không được gán bừa ngày trồng hoặc 2.400 cây/ha đồng loạt: con số có thể chỉ là giả định.
- Không sử dụng `lotus_farm.mobile_demo_seed.seed` trên site frontend: seed đó bị khóa riêng cho site `allow_tests`.

## Đã hoàn thiện
- Màn Dự thu 3 năm có nút **Xem dữ liệu mẫu**: tạo 4 lô MẪU, 36 tháng, sản lượng ước tính minh họa (chỉ trong bộ nhớ trình duyệt); đổi lại bằng **Xem dữ liệu thật**.
- Trong chế độ mẫu, tất cả số liệu đều dán nhãn MẪU và ẩn phần phiếu dự thu thật, tuyệt đối không ghi/đổi database, không phê duyệt hay giữ hàng.
- Có nút **Tải bảng nhập ngày trồng**: tạo CSV UTF-8 từ danh sách lô người dùng được phép đọc, gồm mã lô, diện tích, ngày trồng và mật độ cây (ô nào không có số giữ trống). Không tự sửa bản ghi.
- Dữ liệu thật chỉ được dự tính khi có ngày trồng hoặc công đoạn được ghi nhận và bộ hệ số dự thu được duyệt.

## Đưa lên live
- Dùng Docker image `lotus-live-readiness:v1-20261017` kế thừa `lotus-desktop-ui:v1-20261017`, chỉ thay frontend và thêm `lotus_farm.forecast_setup`.
- Không chạy test seed hoặc tự nhập ngày trồng trên hệ thống vận hành.
- Kiểm tra `/lotus/forecast`, `/lotus/kho`, `/lotus/giao-viec`, `/lotus/cham-cong`, `/lotus/mobile`; giữ các service Docker khác nguyên trạng.
- Trường hợp lỗi khôi phục lại ảnh `lotus-desktop-ui:v1-20261017`.
- **Mẫu không thể trở thành kế hoạch sản lượng thật nếu chưa có số liệu hiện trường và bộ hệ số được quản lý duyệt.**
