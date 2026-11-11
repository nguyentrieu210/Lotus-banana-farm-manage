# Spec 005 — lên live

## 11/11/2026 09:15–09:18: `lotus-release:c510b71` (gốc `5f3ceac` = spec 004 + 003)

- Chủ vườn bảo lên live ("lên live và gộp chưa", "làm đi").
- Image dựng trên VPS từ `git archive c510b71`, `BASE_IMAGE=lotus-release:5f3ceac`; hồ sơ ở `/srv/lotus-build/c510b71`.
- Diễn tập trước đó (`rehearsal5.sh c510b71 5f3ceac`, bản sao site thật 09:10): migrate 142 s, 26 bảng sổ sách không đổi (thêm 10 Custom Field, 8 Custom DocPerm); 33/37 API giống hệt code cũ, 4 khác chỉ ở khóa cũ của spec 002 đã bỏ có chủ đích; `verify_issue_request` ALL PASSED; `verify_kho_e2e` 61/61, `verify_warehouse_audit`, `verify_costing`, `verify_lot_ledger`, `verify_care_cycle`, `verify_packout_sources`, `verify_field_reports`, `verify_vat_in_cost` 24/24, `verify_sign_notify` qua. `audit_warehouse_edge_cases`, `verify_warehouse_regressions` lỗi "Đề xuất mua phải ký đủ 4 bước" giống hệt trên `5f3ceac` (có sẵn, không do 005); `verify_issue_uom` cần `--site`, `verify_purchase_flow` cần stack mua hàng riêng.
- Lên live bằng `rollout3.sh c510b71 5f3ceac`: bảo trì → dừng hàng đợi → sao lưu `20261111_091524` (có file) → đổi `LOTUS_IMAGE` → migrate → so sổ sách (không đổi) → bật lại. Ngưng khoảng 3 phút. Ping 200; Error Log chỉ có một "Session Stopped" lúc bảo trì.
- Trên live sau khi lên: 9 Custom Field `lotus_issue*`, 4 quyền đọc vật tư/đơn vị/kho/nhóm vật tư cho đội trưởng, 0 yêu cầu cấp vật tư.
- Quay lại: `bash /srv/lotus-build/c510b71/rollback.sh c510b71 --restore-db` (về `5f3ceac` và bản sao lưu trên).

## Chưa làm

- T059: chưa kiểm tay trên trình duyệt ở 320px/390px; chỉ có mount test frontend (691/691).
- Chưa có người thật lập/duyệt/cấp một yêu cầu trên live.
