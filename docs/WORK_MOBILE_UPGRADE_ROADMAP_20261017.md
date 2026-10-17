# Lotus — Công việc ngoài vườn: triển khai nâng cấp toàn bộ
Ngày chốt phạm vi: 2026-10-17. Quy ước: PWA Vue 3/Vant 4, backend Frappe/ERPNext, theo **Vườn -> Lô lớn -> Tổ**. Không quay lại làm việc theo Thửa nhỏ. Chấm công theo tổng công của Tổ (không tự chia lương cho cá nhân).

## Phạm vi đã phê duyệt
1. Giao công việc -> chuẩn bị tổng công/vật tư -> tổ báo thực hiện -> đội trưởng kiểm tra -> quản lý duyệt -> mới ghi vào sổ sản xuất.
2. Vai trò quản lý vườn, giám sát/đội trưởng, tổ trưởng. Quyền theo Vườn và Tổ; người lập khác người kiểm tra khác người duyệt.
3. Nghiệp vụ công nhật/khoán, định mức, nhu cầu vật tư, cấp phát qua app Kho, ghi dùng và hoàn trả, đối chiếu số liệu.
4. PWA offline an toàn, ảnh hiện trường, cảnh báo xung đột/đồng bộ; thông báo đúng người; giao diện Vant dùng chung.
5. Test backend/API, trên Android/iPhone thật, pilot một Tổ trước khi triển khai các Vườn.

## Trạng thái code ở nhánh feat/work-review-20261017
- Đã tạo nhánh worktree riêng ở C:\\code\\Lotus-work-review để không ghi đè công việc đang dở trên sync/lotus-mobile-20261017.
- Đã tạo quy trình báo cáo dự thảo -> Pending -> Verified -> Approved/Changes Requested với 3 vai trò tách biệt. Chỉ Approved mới submit Daily Work Result vào sổ thực tế.
- Đã có trả lại/sửa/gửi lại và lịch sử Frappe Comment; giữ Field Capture ID chống gửi trùng, kế thừa IndexedDB hàng chờ và cảnh báo tài khoản khác.
- Đã có hiển thị công dự kiến đã phân, phiếu vật tư cần tạo; quản lý có thể tạo phân bổ công tổng hợp + Material Requirement theo lô lớn. Đây KHÔNG phải phiếu xuất kho, KHÔNG phải chấm công thực tế.
- Đã thêm thông báo inbox theo người nhận và Web Push tùy chọn, cần kiểm tra thực tế recipient.
- Đã điều chỉnh DocType liên quan để Farm Plot/Crop Cycle chỉ là dữ liệu lịch sử, không bắt buộc với Lô lớn.
- Không tự động chỉnh sửa dữ liệu cũ. Chưa chạy migrate, chưa chạy E2E với DB thật, chưa được coi là nghiệm thu.

## Công việc còn lại (toàn bộ kế hoạch, không phải đã xong)
| Thứ tự | Công việc | Đầu ra nghiệm thu |
|---|---|---|
| P0 | Test Frappe với dữ liệu kiểm thử độc lập sau migrate | Ba tài khoản khác quyền; submit/draft/verify/approve/reject/revision và không trùng số |
| P0 | Kiểm thử mô hình chốt công: kế hoạch và dự thu, công thực tế, định mức kho | Sổ chính thức không cộng báo cáo Pending/Rejected; khóa ngày đúng; ERP ledger đối chiếu |
| P0 | Tăng độ bền offline (version conflict, delta-sync, file upload) | Máy A/B không ghi đè; đổi tài khoản không lẫn dữ liệu; retry không nhân đôi |
| P0 | Hoàn thiện vật tư: app Kho xuất theo yêu cầu, thực dùng, trả về, chênh lệch | 20 kg yêu cầu, 18 xuất, 16 sử dụng, 2 hoàn trả được đối chiếu |
| P0 | Test thông báo phân công Tổ + báo cáo chờ duyệt, cấp quyền và giới hạn farm/team | Thông báo tới đúng người; inbox lưu dù push không đến |
| P0 | Test điện thoại Android cấu hình thấp + iPhone đã cài PWA | Chụp ảnh, offline 1 buổi, kill/reopen, back/swipe, màn hình 320/390 |
| P1 | Mẫu tác nghiệp ngắn theo vai trò; đội trưởng xem hàng chờ; màn hình xử lý lỗi sync | Tổ trưởng nộp vài thao tác; đội trưởng duyệt nhiều công việc; dễ hiểu |
| P1 | Tối ưu ảnh riêng tư/nén ảnh và cơ chế lưu tạm trước khi đồng bộ | Không rò ảnh, không mất ảnh sau reload nếu còn dung lượng |
| P1 | Khóa sửa sau duyệt, audit truy vết nguồn, quy trình mở lại có lý do | Luôn biết ai báo, kiểm tra, duyệt, sửa, lúc nào |
| P2 | Dashboard tiến độ và định mức theo Lô lớn/Tổ | Số liệu từ Approved và stock/công đúng, có đối chiếu nguồn |

## Điều kiện trước khi đưa lên production
- Backup cơ sở dữ liệu, file riêng tư và asset PWA. Triển khai trên staging, chạy `bench migrate` ở staging và kiểm tra Frappe DocType/Role/User Permission.
- Kiểm tra kết quả nộp online/offline bằng người dùng thử, không ghi nhầm vào sổ sản xuất thật.
- 0 lỗi ghi trùng, 0 mất báo cáo, 0 truy cập ngoài Vườn/Tổ, không duyệt do cùng người nộp; role API chặn cả khi gọi trực tiếp.
- Kiểm tra app Kho và Mua hàng sau migrate vì có thay đổi schema chung; tuyệt đối không chạy migration trên production khi test chưa xong.
- Chỉ mở pilot một Tổ thuộc Vườn 222 Thuận Phú. UAT với quản lý/tổ trưởng/đội trưởng; chạy song song sổ đối chiếu cho đến khi nghiệm thu.
- Có cơ chế tắt tính năng mới, giữ bản cũ, và hướng dẫn phục hồi data/file + assets; rollback schema sau migrate yêu cầu backup/restore, không chỉ git reset.

## Những quyết định nghiệp vụ phải giữ nguyên
- Đơn vị giao việc: Lô lớn, Tổ; không bắt buộc giao tới từng công nhân.
- Tổ trưởng báo số lượng + tổng công tổ + lý do thiếu + ảnh/GPS nếu có.
- Đội trưởng kiểm tra, quản lý vườn duyệt cuối. Giá khoán vượt chuẩn tiếp tục có luồng duyệt đơn giá riêng.
- Vật tư có bốn số riêng: yêu cầu, xuất, thực dùng, hoàn trả. App Công việc không có quyền tự xuất tồn.
- Công việc đã duyệt muốn sửa phải mở lại theo quyền, không ghi đè lên sổ mà không có lịch sử.
