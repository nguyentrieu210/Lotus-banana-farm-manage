# Giao việc theo lô và báo cáo ngày của đội (Vườn 222)

Thay cho Nhật ký công việc (chép Zalo), Giao việc theo ngày và duyệt kết quả 3 cấp (đã xóa 29/10/2026).
Mẫu dòng theo file vườn đang dùng "222 BÁO CÁO CÔNG VIỆC HẰNG NGÀY.xlsx". Từ 30/10/2026 báo cáo đi từ
**bảng giao việc theo lô**: đội trưởng giao trước, tổ báo trên chính các phiếu đã giao.

## Ai làm gì

- **Lô thuộc đội theo khu.** Đội là `Work Team` có `lotus_team_level = Crew` và `lotus_zones` (ví dụ "A, B");
  đội trưởng là `lotus_leader`. Tổ là `Work Team` cấp `Team`, `lotus_parent_team` = đội, tổ trưởng = `lotus_leader`.
- **Đội trưởng** (Lotus Field Supervisor, là leader của đội) giao việc theo lô, giao chăm buồng, sửa mọi dòng, ghi thời
  tiết, **xác nhận** hoặc **trả lại** báo cáo; quá 10 giờ sáng hôm sau chưa xác nhận thì báo quá hạn (không tự duyệt).
  Sửa báo cáo đã xác nhận: mở lại, ghi lý do.
- **Tổ trưởng** (Lotus Team Leader) xem phiếu của tổ mình và báo cáo trên đó.
- **Quản lý vườn** (Lotus Farm Manager) xem tất cả, làm được mọi việc của đội trưởng, tạo đội, sửa bảng giá.
- Màn hình: máy tính `/lotus/cong-viec` (Báo cáo ngày, Giao việc theo lô, Bảng lô × việc, Danh sách, Chăm sóc buồng,
  Tiền khoán tháng, Đội-tổ-lô, Bảng giá khoán, Danh mục công việc); điện thoại `/work` (tab Giao việc chỉ hiện với
  đội trưởng).

## Phiếu giao (`Lotus Work Assignment`)

- **Việc vườn** (`kind = Round`): một phiếu = một lô × một việc × một tổ, có ngày giao và hạn. Giao nhiều lô một lần
  ra nhiều phiếu. Mỗi lô + việc chỉ có một phiếu đang giao; xong rồi mới giao lượt sau (không giới hạn số lượt).
  Đổi tổ hoặc huỷ phải ghi lý do; tổ đã báo Xong chờ xác nhận thì không đổi / huỷ được.
- Trạng thái hiển thị tính từ dữ liệu: Đã giao → Đang làm (đã có dòng báo cáo) → Tổ báo xong (dòng Xong chưa xác nhận)
  → Xong (đội trưởng xác nhận ngày đó); Quá hạn khi qua hạn mà chưa xong; Đã huỷ.
- **Chăm buồng** (`kind = Bunch`): mỗi lô giao cố định cho một tổ từ một ngày đến khi đổi. Đổi tổ thì phiếu cũ kết
  thúc hôm trước ngày đổi (`Ended`, `ended_on`), phiếu mới mở từ ngày đổi; đổi phải ghi lý do.
- Bảng lô × việc: mỗi tháng, dòng là lô của đội, cột là việc đã giao, ô là phiếu (tổ, trạng thái, ngày xong).

## Báo cáo ngày

- **Việc được giao**: các phiếu đang giao của tổ hiện sẵn. Tổ trưởng ghi CN/CK, công sáng/chiều, khối lượng làm được
  hôm nay, vật tư (tối đa 4, chỉ ghi nhận, không trừ kho), nhận xét / đề xuất / ghi chú; làm hết lô thì tích
  **Xong lô**. Dòng để trống không lưu. Việc, lô, tổ lấy từ phiếu, không sửa trên dòng.
- **Công nhật khác**: việc công nhật ngoài phiếu (một lô, nhiều lô hoặc cả khu). Công khoán việc vườn bắt buộc có phiếu.
- **Chăm sóc buồng** (công đoạn có `Work Type.lotus_bunch_stage`): ghi số buồng theo lô.
  - Cắt bắp tự gắn màu dây đang hiệu lực (lịch 12 màu theo tuần, xem LOTUS_RIBBON_2026W43.md).
  - Bao buồng, vặt râu / tỉa trái, chống đổ chọn màu của lứa đang làm (màu cắt bắp 16 tuần gần nhất). Cộng dồn
    mọi báo cáo, số của một công đoạn trên một lô và một màu không vượt số đã cắt bắp màu đó ở lô đó: trước
    01/12/2026 chỉ cảnh báo (`over_cut`, đội trưởng vẫn xác nhận được, có ghi chú), từ 01/12/2026 chặn khi lưu.
  - Chích bắp không có màu.
  - Công khoán buồng chỉ trên lô đang giao chăm buồng cho tổ đó vào ngày báo cáo.
- **Chưa đạt ngày công**: khối lượng/công dưới năng suất tối thiểu của giá → bắt ghi lý do.
- **Xác nhận**: đội trưởng xác nhận ngày một lần; lần xác nhận đó đóng các phiếu được tích Xong trong ngày
  (`state = Done`, `done_report`). Mở lại báo cáo thì các phiếu đó mở lại.

## Tiền

- Giá theo `Lotus Piece Rate` đang hiệu lực ngày báo (với Xong là ngày Xong), chốt vào dòng.
- Việc tính theo ha hoặc số cây: trả **một lần, cả lô** (diện tích / số cây hiện có `lotus_tree_count` chốt vào dòng)
  vào ngày tích Xong; các ngày trước chỉ ghi tiến độ, tiền 0. Việc đếm (buồng, cây, bao) trả theo số báo mỗi ngày.
- Công nhật không ra tiền trong báo cáo (lương theo chấm công); chỉ ghi công để chia chi phí lô.
- Dòng CK của báo cáo **đã xác nhận** cộng theo tổ × việc × đơn giá (khối lượng = `paid_qty`) vào "Phải trả đội
  khoán" (`hr_period`) và trang Tiền khoán tháng. Tháng công đã khóa thì không sửa báo cáo.

## Mã

- `lotus_farm/field_report.py` (API, quyền), `field_report_rules.py` (quy tắc thuần, `tests/test_field_report_rules.py`),
  `field_report_seed.py` (nạp F222: 26 việc, 23 giá từ file khoán 21/10, Đội khu A + B).
- DocType: Lotus Work Assignment, Lotus Field Report (+ Line, Material), Lotus Piece Rate; trường thêm trên Work Team,
  Work Type.
- Giao diện: `FieldReportApp.vue`, `components/field/FieldReportDay.vue`, `FieldAssignments.vue`, `FieldBoard.vue`,
  `WorkMobile.vue`, `field-report-model.js`.
- Kiểm thử tích hợp (site thử, tự rollback): `tests/integration/verify_field_report.py`.
- Giai đoạn sau: thu hoạch theo màu, dự thu 12 tuần từ cắt bắp, hao hụt; nối vào Bunch Operation; 622 theo lô.
