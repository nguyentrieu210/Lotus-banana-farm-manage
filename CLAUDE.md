<!-- claude-setup:project:begin -->
## Bộ công cụ (claude-setup)

- Ponytail mặc định `lite` (kế toán, kho, lương, dữ liệu thật): giữ kiểm tra, xử lý lỗi, nhật ký. Chỉ dùng `/ponytail full` cho việc thuần giao diện.
- Context7: tra Frappe/ERPNext **v16**, Vue 3, AG Grid, Vite đúng phiên bản trước khi viết (nhiều bẫy v16).
- Modern Web: áp cho `frontend/`; không áp cho Python/DocType.
- Deploy, migrate, xóa dữ liệu: hook `hoi-lai` chặn; hỏi người dùng trong chat trước, theo quy trình deploy của dự án.
- Graphify: đồ thị mã ở `graphify-out/` (đã gitignore). Hỏi đồ thị trước khi lục tệp; sau thay đổi lớn chạy `graphify update .`.
- Quy trình: Spec Kit (`/speckit-specify` → `/speckit-implement`), `/code-review` trước khi gộp, `/security-review` trước khi deploy.
<!-- claude-setup:project:end -->
