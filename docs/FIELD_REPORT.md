# Báo cáo ngày của đội và giao lô (Vườn 222)

Thay cho Nhật ký công việc (chép Zalo), Giao việc theo ngày và duyệt kết quả 3 cấp (đã xóa 29/10/2026).
Mẫu theo file vườn đang dùng "222 BÁO CÁO CÔNG VIỆC HẰNG NGÀY.xlsx".

## Ai làm gì

- **Lô thuộc đội theo khu.** Đội là `Work Team` có `lotus_team_level = Crew` và `lotus_zones` (ví dụ "A, B");
  đội trưởng là `lotus_leader`. Tổ là `Work Team` cấp `Team`, `lotus_parent_team` = đội, tổ trưởng = `lotus_leader`.
- **Tổ trưởng** (vai trò Lotus Team Leader) nhập và sửa dòng của tổ mình.
- **Đội trưởng** (Lotus Field Supervisor, là leader của đội) sửa mọi dòng, ghi thời tiết, thêm công nhật cả khu,
  **xác nhận** hoặc **trả lại** báo cáo; quá 10 giờ sáng hôm sau chưa xác nhận thì báo quá hạn (không tự duyệt).
  Sửa báo cáo đã xác nhận: mở lại, ghi lý do.
- **Quản lý vườn** (Lotus Farm Manager) xem tất cả, tạo đội, sửa bảng giá, mở lại được.
- Màn hình: máy tính `/lotus/cong-viec` (Báo cáo ngày, Danh sách, Chăm sóc buồng, Tiền khoán tháng, Đội-tổ-lô,
  Bảng giá khoán, Danh mục công việc); điện thoại `/work`.

## Dòng báo cáo

- Mỗi dòng: tổ, việc, CN (công nhật) / CK (công khoán), lô (hoặc nhiều lô / cả khu cho công nhật), công sáng/chiều,
  khối lượng, tối đa 4 vật tư (danh mục kho, chỉ ghi nhận, không trừ kho), nhận xét / đề xuất / ghi chú.
- **Công khoán**: một lô một dòng. Giá theo `Lotus Piece Rate` đang hiệu lực ngày đó. Việc tính theo ha hoặc số cây:
  để trống khối lượng là cả lô (diện tích, số cây hiện có `lotus_tree_count` chốt vào dòng); làm dở thì ghi phần đã làm.
  Một ngày, cùng việc trên cùng lô không vượt cả lô (nhiều tổ thì chia). Việc đếm (buồng, cây, bao) nhập số thật.
- **Công nhật**: không ra tiền trong báo cáo (lương theo chấm công); chỉ ghi công để chia chi phí lô.
- **Chưa đạt ngày công**: khối lượng/công dưới năng suất tối thiểu của giá → bắt ghi lý do.
- **Chăm sóc buồng** (công đoạn có `Work Type.lotus_bunch_stage`): ghi số buồng theo lô; **cắt bắp** tự gắn màu dây
  đang hiệu lực (lịch 12 màu theo tuần, xem LOTUS_RIBBON_2026W43.md).

## Tiền

Dòng CK của báo cáo **đã xác nhận** cộng theo tổ × việc × đơn giá vào "Phải trả đội khoán"
(`hr_period`, cùng chỗ với chấm công đội khoán) và trang Tiền khoán tháng. Tháng công đã khóa thì không sửa báo cáo.

## Mã

- `lotus_farm/field_report.py` (API, quyền), `field_report_rules.py` (quy tắc thuần, `tests/test_field_report_rules.py`),
  `field_report_seed.py` (nạp F222: 26 việc, 23 giá từ file khoán 21/10, Đội khu A + B).
- DocType: Lotus Field Report (+ Line, Material), Lotus Piece Rate; trường thêm trên Work Team, Work Type.
- Giao diện: `FieldReportApp.vue`, `components/field/FieldReportDay.vue`, `WorkMobile.vue`, `field-report-model.js`.
- Kiểm thử tích hợp (site thử, tự rollback): `tests/integration/verify_field_report.py`.
