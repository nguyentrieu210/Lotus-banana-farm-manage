# Giao việc và nghiệm thu tiền khoán

Mở `/lotus/giao-viec`, chọn ngày, tổ, lô **hoặc** thửa, loại việc và số lượng.
Chọn cách trả công trên từng việc. Work Type chỉ cung cấp lựa chọn mặc định.

## Ví dụ

- Tổ 1 bao 800 buồng, giá niêm yết 2.000đ/buồng: tiền dự tính 1.600.000đ.
- Ghi tiêu chuẩn đạt để tổ thực hiện và người nghiệm thu đối chiếu.
- Đơn giá giao có thể thấp hơn hoặc bằng niêm yết, không cần duyệt vượt giá.
- Nếu giao 2.200đ/buồng: ghi lý do; hệ thống lưu kế hoạch nháp **chờ duyệt**, chưa giao việc.
- Quản lý khác người lập/người sửa gần nhất mở kế hoạch, xem giá và bấm **Duyệt giá và giao việc**.
- Người nghiệm thu chỉ nhận 750 buồng đạt ở mức giá 2.000đ: tiền khoán là **1.500.000đ**; phải ghi lý do giảm so với số tổ báo.
- Số công theo dõi năng suất không được cộng thêm vào tiền khoán.

## Giá và bằng chứng

`Work Piece Rate` lưu bảng giá theo nông trường, loại việc, đơn vị và ngày hiệu lực.
Giá chỉ dùng sau khi Submit; không cho hai giá đã duyệt chồng ngày.
Kế hoạch lưu bảng giá nguồn, giá niêm yết, giá giao, tiền dự tính, tiêu chuẩn đạt,
lý do vượt và người/thời điểm duyệt. Bảng giá thay đổi không tính lại giá đã lưu.
Khi đã giao, muốn đổi giá phải hủy và lập bản sửa có lý do theo quy trình chứng từ.

`Work Piece Settlement` lấy giá từ dòng kế hoạch đã giao, không chọn giá mới lúc
nghiệm thu. Một kết quả đã nộp chỉ có một phiếu nghiệm thu đang hiệu lực. Không
nghiệm thu vượt số tổ báo; giảm số lượng phải có lý do. Phải hủy nghiệm thu trước
khi hủy báo cáo gốc. Giá có kế hoạch đang dùng không được hủy.

Kế hoạch cũ chưa có giá chốt không được tự tính khoán theo giá hiện tại. Cần xử lý
hủy/lập lại có kiểm tra và lý do; không tự sửa lịch sử.

## Nhân công và vật tư trên màn hình xem trước

Hiển thị số công dự tính từ định mức năng suất và lượng vật tư cần từ định mức đã
duyệt, còn hiệu lực. Không hiển thị tồn kho. Khi chưa có định mức vật tư, báo rõ
chưa tính được thay vì coi nhu cầu bằng 0. Chọn lô thì chia khối lượng xuống các
thửa theo diện tích như chức năng hiện có; người giao cần kiểm tra phần phân bổ.

## Giới hạn và triển khai

- Công nhật giữ cách ghi nhận hiện có. Phần này chưa bổ sung bảng thanh toán công nhật.
- Phiếu nghiệm thu tiền khoán chưa tạo bút toán, Payment Entry hay xác nhận đã trả tiền.
- Duyệt **vượt giá giao việc** có hai tài khoản; nghiệm thu sản lượng hiện vẫn do Farm Manager Submit, chưa có ký nhận hai bên.
- Build frontend và chạy `bench --site <site> migrate` trước khi dùng.
- Kiểm tra trên site ERPNext v16 riêng: cả giá trong mức, vượt mức, từ chối tự duyệt,
  báo kết quả, nghiệm thu một phần và hủy/lập lại. Chưa nghiệm thu trên dữ liệu thật.
