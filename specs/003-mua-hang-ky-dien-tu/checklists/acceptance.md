# Nghiệm thu với người dùng thật (SC-011)

Mục tiêu: mỗi người tự làm phần việc của mình trong một vòng mua hàng trọn vẹn, từ đề xuất đến trả tiền, trên thiết bị mình quen dùng, không cần người khác làm hộ (spec.md, SC-011).

## Chuẩn bị

- **Khi nào:** làm sau khi spec 003 đã lên site thật. Thông báo đẩy chỉ chạy trên site thật; bản sao dùng để thử không gửi thông báo.
- **Chọn món hàng:** một lần mua nhỏ có thật, ví dụ 1–2 bao phân của một nhà cung cấp quen. Như vậy không phải hủy chứng từ nào sau khi thử.
- **Mỗi người cần sẵn:**
  - đăng nhập trên điện thoại, hoặc máy tính, hoặc cả hai;
  - đã cho phép thông báo trên app;
  - đã có ảnh chữ ký trong hồ sơ.
- **Người ghi chép:** một người đứng cạnh, chỉ ghi lại chỗ ai phải hỏi, chỗ màn hình khó hiểu, chỗ bị báo lỗi. Người này không làm hộ.

## Vòng thử

Làm theo thứ tự. Mỗi bước có cột "Đạt" và "Ghi chú" (người, thiết bị, chỗ vướng).

| # | Ai | Làm gì, trên đâu | Thấy gì là đạt | Đạt | Ghi chú |
|---|---|---|---|---|---|
| 1 | Người đề xuất (tổ trưởng hoặc thủ kho) | Lập đề xuất mua trên điện thoại, rồi ký gửi. | Đề xuất ở giai đoạn "Đang ký". Người ký tiếp theo nhận thông báo. | ☐ | |
| 2 | Những người ký đề xuất (trưởng bộ phận, …) | Bấm vào thông báo trên điện thoại, xem rồi ký. | Thông báo mở đúng tấm ký. Ký xong, đề xuất sang người kế tiếp, cuối cùng ở "Chờ mua". | ☐ | |
| 3 | Mua hàng | Nhập báo giá, chọn nhà cung cấp, bấm "Lập đơn từ đề xuất", gửi giám đốc duyệt. | Đơn có sẵn nhà cung cấp và giá đã chọn. Dòng nào sẽ bị chặn khi duyệt thì được báo ngay lúc lưu. | ☐ | |
| 4 | Giám đốc | Duyệt đơn trên điện thoại (bấm thông báo) hoặc ở `/lotus/cho-ky` trên máy tính. | Đơn "Đã duyệt". "In đơn mua" mở bản PDF đã ký. | ☐ | |
| 5 | Mua hàng | Đánh dấu "Đã gửi NCC", rồi "NCC đã xác nhận". | Danh sách đơn hiện đúng trạng thái. | ☐ | |
| 6 | Thủ kho | Khi hàng về: nhận trên điện thoại. Ghi số thực nhận, chụp ảnh hàng. Người giao ký bằng ngón tay trên màn hình và ghi tên, hoặc chụp phiếu giao hàng có chữ ký. Bấm "Xác nhận nhập kho". | Phiếu "Đã nhập kho", có chữ ký thủ kho và bản PDF lưu. Thiếu chữ ký hoặc ảnh thì bị chặn kèm lời nhắc. | ☐ | |
| 7 | Kế toán | Ở "Hóa đơn chờ nhập", nhập hóa đơn của nhà cung cấp theo đúng bản giấy. Đính kèm ảnh hoặc PDF hóa đơn, gõ tổng in. | File gốc hiện cạnh biểu mẫu. Tổng khớp từng đồng. Giá khác đơn thì phải ghi lý do. | ☐ | |
| 8 | Kế toán | Ở Công nợ: xem nhà cung cấp tại ngày hôm nay, rồi lập phiếu chi cho hóa đơn, ký bước 1. | Công nợ đúng số. Dòng đối chiếu báo "khớp sổ cái". | ☐ | |
| 9 | Kế toán trưởng | Bấm thông báo, ký phiếu chi. | Phiếu chuyển sang giám đốc. | ☐ | |
| 10 | Giám đốc | Bấm thông báo trên điện thoại, ký phiếu chi. | Phiếu được ghi sổ. Người lập nhận "Đã ký đủ". Hóa đơn chuyển "Đã trả". | ☐ | |
| 11 | Kế toán | In giấy đề nghị chi và biên bản đối chiếu với nhà cung cấp. | Bản in có chữ ký và mã QR. Số đầu kỳ, phát sinh, cuối kỳ khớp sổ chi tiết. | ☐ | |

## Kiểm tra chỉ làm được bằng thiết bị thật

| Kiểm tra | Cách làm | Đạt khi | Đạt | Ghi chú |
|---|---|---|---|---|
| Thông báo đẩy | Ở bước 2, 4, 9, 10: khóa màn hình điện thoại, chờ thông báo, bấm vào. Thử cả Android và iPhone nếu có. | Thông báo đến trong vài giây và mở đúng tấm ký. | ☐ | |
| Mã QR trên giấy | In đơn mua (bước 4) và giấy đề nghị chi (bước 11) ra giấy A4. Dùng camera của một điện thoại khác quét QR. | Trang `/verify/lotus` báo bản in khớp bản lưu. | ☐ | |
| Bản in | Xem bằng mắt các bản in trên. | Chữ ký và tên đúng người, không tràn trang, chữ đọc được. | ☐ | |
| Mất sóng | Ở bước 6, bật chế độ máy bay đúng lúc bấm "Xác nhận nhập kho". Tắt chế độ máy bay rồi bấm lại. | Chỉ có một phiếu nhập. Số lượng không bị nhân đôi. | ☐ | |

## Kết luận

- **Đạt SC-011** khi mỗi người tự làm xong phần của mình ở bảng "Vòng thử", không cần ai làm hộ, và bốn kiểm tra thiết bị đều đạt.
- **Chỗ vướng** (phải hỏi người khác, màn hình khó hiểu, bị báo lỗi): ghi vào cột "Ghi chú", gửi lại để sửa trước khi dùng rộng.

| Người | Vai trò | Thiết bị | Ngày | Ký xác nhận |
|---|---|---|---|---|
| | Người đề xuất | | | |
| | Trưởng bộ phận | | | |
| | Mua hàng | | | |
| | Kế toán | | | |
| | Kế toán trưởng | | | |
| | Giám đốc | | | |
| | Thủ kho | | | |
