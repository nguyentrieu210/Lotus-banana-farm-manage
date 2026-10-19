# Lotus — thiết kế chữ ký trên chứng từ (tham khảo Documenso, OpenSign, Dropbox Sign)

Ngày nghiên cứu: 19/10/2026.

## Nguồn và điểm rút ra

- [Documenso PDF placeholders](https://github.com/documenso/documenso/blob/main/apps/docs/content/docs/users/documents/advanced/pdf-placeholders.mdx): `signature`, `initials`, `date`, `name`, `text` và phân theo vai trò/người nhận.
- [Documenso Fields API](https://docs.documenso.com/docs/developers/api/fields): chữ ký, ký nháy, ngày đã ký, nhiều loại trường; ngày hoàn tất do máy chủ ghi.
- [Documenso Document API](https://docs.documenso.com/docs/developers/api/documents): vị trí trường ký tương đối theo trang; vai trò Signer/Approver/Viewer, ký tuần tự.
- [OpenSign](https://github.com/OpenSignLabs/OpenSign): vẽ/tải ảnh/lưu mẫu chữ ký và nhiều người ký.
- [Dropbox Sign Fields](https://help.dropbox.com/view-edit/signer-fields-dropbox-sign): chữ ký, initials, date signed; mẫu dùng lại.
- [Dropbox Sign Timestamp](https://help.dropbox.com/account-settings/signature-formats-dropbox-sign): tên và dấu thời gian hiển thị gần chữ ký.
- [Documenso QR Certificate](https://documenso.com/changelog): QR trên chứng nhận để đối chiếu bản gốc.
- [DocuSign Sign with Singpass](https://support.docusign.com/s/document-item?bundleId=yca1573855023892&language=en_US&topicId=xhc1615577299246.html): quét QR là phương thức xác thực một phiên ký; QR không tự đóng vai trò chữ ký.

## P1: Thiết lập chữ ký riêng trong mục Tôi

- Chọn ảnh PNG/JPG <=10 MB, crop cảm ứng (Cropper.js, MIT), xoay, zoom, tách nền giấy, xem trước, xác nhận rồi mới upload. V1 code trên nhánh này.
- Bổ sung **ký nháy** ở P2: ảnh hoặc ký vẽ riêng, lưu thành trường private `User.lotus_initials_image`, không tự dùng ảnh chữ ký chính làm ký nháy.
- Tài khoản chỉ chỉnh chữ ký của chính mình, giữ bản gốc riêng ở máy cục bộ cho đến khi bấm Lưu; chỉ gửi PNG đã cắt lên server và bỏ EXIF.
- Lưu phiên bản riêng mỗi lần thay ảnh; chứng từ đã duyệt không được tự thay ảnh đã đóng dấu trước đó.
- Vẽ tay bằng Canvas riêng để ký bằng ngón tay nếu không có ảnh; lưu tương tự ảnh chữ ký.
- Mục Tôi có thể cấu hình **định dạng ngày hiển thị** và **kiểu khung chữ ký**, không được sửa `approved_at`/timestamp thực.

## P2: Trường ký trên mẫu in/PDF

Các trường `SIGNATURE`, `INITIALS`, `SIGNED_DATE`, `NAME`, `TITLE`, `QR_VERIFY` với:
- `doctype`, `template_id`, `page`, `x_pct`, `y_pct`, `width_pct`, `height_pct`
- `role` hoặc `approver_user`, `required`, `signing_order`, `enabled`.
- Ví dụ phiếu đề nghị mua: Người lập (ngày lập) → kiểm tra/ký nháy ở góc từng trang → người có quyền duyệt (chữ ký chính + ngày máy chủ).
- Ký nháy chỉ xác nhận đã kiểm tra, **không thay** quyền duyệt; quyền ký gắn vai trò và người đăng nhập.
- Ký tuần tự: bước chưa đến lượt không được ký; mọi hành động phải kiểm soát backend, không chỉ ẩn nút.

## P3: Ngày ký

Phân biệt:
- `transaction_date` hoặc `effective_date`: ngày chứng từ/ngày hiệu lực, có thể chọn trước khi duyệt theo quyền.
- `approved_at` / `signed_at`: ngày-giờ thao tác thực từ server, chỉ đọc. Hiển thị tùy định dạng nhưng không cho giả ngày ký.
- Trong PDF, mỗi chữ ký có thể có tên người ký, chức danh tại thời điểm ký và timestamp riêng.

## P4: Hai QR khác nhau

**QR xác minh chứng từ in giấy**: đặt mã ở chân trang, dẫn tới `/verify/<opaque_token>`. Trang xác minh chỉ hiển thị thông tin công khai tối thiểu: số phiếu, loại phiếu, trạng thái, thời điểm duyệt, fingerprint (SHA-256) của *bản PDF cuối đã lưu*. Không nhúng ảnh chữ ký hoặc tài liệu riêng tư vào QR. Nếu muốn xem PDF, phải đăng nhập và có quyền. QR tự nó không làm file chống sửa; phải so bản lưu gốc và hash.

**QR xác nhận ký trên thiết bị khác**: QR là token dùng một lần, giới hạn ~60–120 giây, ràng buộc user/doctype/doc-id/hash/phiên duyệt, bắt buộc đăng nhập hoặc MFA trên điện thoại và người ký chủ động xác nhận. Không coi việc quét QR là chữ ký nếu thiếu xác thực.

## P5: Nhật ký và tính toàn vẹn

- Lưu `actor`, `role`, `document_id`, `document_version`, `signature_type`, `signed_at`, `ip`, `user_agent`, `file_hash`, `signature_image_revision`, `approval_step`.
- Mỗi bước chỉ phê duyệt khi render PDF và lưu bản bất biến hoàn tất, lỗi thì rollback.
- Ký nhiều cấp phải giữ mỗi bản/lần đóng dấu; không ghi đè PDF đã duyệt.
- Chỉ có ảnh chữ ký thì là ký điện tử nội bộ kèm audit, **không phải ký số chứng thư/PAdES**.
