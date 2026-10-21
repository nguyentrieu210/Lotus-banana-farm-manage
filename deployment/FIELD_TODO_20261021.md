# Bảng giao việc ngoài vườn – 21/10/2026

- App PWA: `/work`, tab **Công việc**, Home → **Bảng giao việc theo lô**.
- Đúng 5 nhóm từ danh mục OneDrive (91 công việc):
  Trồng mới 33, Chăm sóc vườn 24, BVTV 16, Chăm sóc buồng 12, Thu hoạch 6.
- Nhóm → Hạng mục → Công việc; giao theo **lô lớn**, **tổ**, **ngày bắt đầu**, **hạn**.
- Hai kiểu theo dõi: **theo số lượng** (người giao tự chọn đơn vị, chưa có định mức)
  và **báo hoàn thành** (không ép nhập khối lượng).
- Luồng: chưa làm → đang làm → báo hoàn thành → nghiệm thu; có thể trả làm lại.
  Cho phép chuyển tổ khi chưa báo xong; có chống gửi trùng, kiểm tra phiên bản và quyền vườn/tổ.
- Độc lập với Daily Work Plan/Result, Nhật ký công việc, công nhật, lương, thưởng, kho
  và vật tư. KHÔNG tự ghi công hay trả lương.
- Danh mục OD- đang chưa kích hoạt trong Work Type cũ; app mới dùng dữ liệu đã nhập
  riêng, không bật lên trong kế hoạch cũ vì chưa có đơn vị/định mức được xác nhận.
- Migration bổ sung duy nhất `Field Todo`: 
  `bench --site frontend reload-doc lotus_farm doctype field_todo`.
- Kiểm tra: frontend `npm test`, `npm run build`;
  `tests/integration/verify_field_todo.py` chạy trên site và rollback.
- Backup trước triển khai: `sites/frontend/private/backups/20261021_201748-frontend-database.sql.gz`.
- Bản triển khai 8080: `lotus-field-todo:v1-20261021`; nền `lotus-release:276884f`.
  Khi cần rollback giao diện/API, chuyển lại image nền; schema mới có thể để nguyên
  không dùng, không xóa dữ liệu Field Todo nếu đã phát sinh việc thật.
- Chưa nghiệm thu thực tế với các tài khoản tổ trưởng/giám sát và kết nối mạng yếu;
  cần UAT trước khi coi là quy trình vận hành chính thức.
