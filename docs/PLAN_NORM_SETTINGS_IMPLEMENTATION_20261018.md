# Lotus – Cấu hình kế hoạch & định mức (18/10/2026)

## Đã thực hiện trên nhánh
`feat/lotus-plan-norm-settings-20261018` dựa trên `feat/lotus-a-complete-cycle-20261018` (có mô hình dự thu 36 tháng và 20–60–20). Không sửa worktree `C:\\code\\Lotus-banana-farm-manage` đang có nhiều thay đổi chưa commit.

Trang quản lý `/lotus/plan-norm?farm=LOTUS-222`, nằm trong menu **Cấu hình kế hoạch & định mức** và có lối vào từ Công việc vườn/Dự thu. Tài khoản cần có quyền đọc `Daily Work Plan` để mở phần giao diện và quyền tương ứng cho mỗi DocType để tạo/sửa.

Bốn tab:
- **Chu kỳ cây:** bộ `Harvest Profile` và đợt dự kiến `Plan Cohort`, nhiều đợt cùng `Farm Block`.
- **Lịch công việc:** `Work Schedule Rule`, ngày lệch trước/sau mốc, chu kỳ lặp, basis số lượng, hiệu lực và phiên bản.
- **Định mức:** `Work Type` (năng suất/công, giá khoán), `Material Norm Profile` (vật tư/đơn vị công việc).
- **Thử tính 36 tháng:** từ một tháng được chọn, 20/60/20 có thể thay đổi nhưng chưa lưu, bảng theo tháng, lịch công việc, vật tư, khối lượng ước tính.

## Luồng dữ liệu và an toàn
- `Plan Cohort` là hồ sơ **dự kiến**, không phải sự kiện trồng/chọn chồi/trổ/thu thực tế.
- `plan_norm.board` kiểm tra vườn/lô qua `land_scope`, đọc dữ liệu qua `frappe.get_list` và quyền từng DocType; không ghi chứng từ.
- Người có quyền ghi tạo bản nháp, quản lý có quyền tương ứng mới có thể duyệt. Bản duyệt không cho sửa/xóa; để điều chỉnh phải tạo phiên bản mới, liên kết bản cũ. Khi tính chỉ lấy phiên bản cao nhất trong cùng mã đợt/lô.
- Không dùng `Draft` khi tính thử, trừ khi bật rõ "Bao gồm bản nháp để thử". Các bộ hệ số và định mức phải Approved.
- Không tự coi 1 cây = 1 buồng, không quy đổi những đơn vị chưa khai báo, không nhân toàn diện tích lô cho nhiều đợt cùng một lúc.
- Các mốc tính theo ngày: `Planting/Selection/Shooting/Cut Bud` đến thu từ `Harvest Profile`; không tự thêm số ngày thiếu. Trổ 20/60/20 chỉ tách 3 tháng khi nguồn là số buồng dự kiến và chưa có mốc trổ quan sát. Vụ chồi tương lai chỉ hiện mốc, **không** tự ước lượng sản lượng không có căn cứ.
- Bản tính không tạo `Daily Work Plan`, `Material Requirement`, `Purchase Order`, `Stock Entry`, `Harvest Forecast`; không giữ nguồn hàng hay phê duyệt giao việc.
- Không thay đổi dữ liệu hoạt động, kho hoặc kết quả đã xác nhận.

## Kiểm thử
- `node --test frontend/tests/plan-norm*.test.js` kiểm tra chia đợt, chống trùng phiên bản, bản nháp, quy đổi đơn vị, Area, mốc âm, phê duyệt, sai thứ tự.
- `cd frontend && npm test` toàn bộ bộ frontend.
- `cd frontend && npm run build` build Vite.
- Python: kiểm tra cú pháp `plan_norm.py` bằng AST trong container (không ghi DB).
- Trước khi bật live phải chạy `bench --site frontend migrate` trên bản thử nghiệm/sao lưu trước để tạo DocType `Plan Cohort`, rồi kiểm tra quyền/CSRF/nhập liệu với tài khoản thật. Không dùng `reload-doc` trực tiếp trên production khi chưa có bản sao lưu.

## Việc còn phải nối trước khi cho hệ thống tự tạo kế hoạch thật
1. Đối chiếu `Plan Cohort` với nhật ký hiện trường theo *mã đợt*, đặc biệt khi một đợt chỉ cắt bắp một phần. Mô phỏng mới **chưa tự thay thế mốc thủ công bằng ghi nhận thực tế**; phần dự thu hiện có vẫn giữ luồng ưu tiên ghi nhận thật của nó.
2. Xác định vườn/kho nhận vật tư và mức tồn hiện hành; chưa đưa ra "thiếu vật tư" từ số tồn chưa biết thuộc kho nào.
3. Thiết kế bước duyệt kế hoạch tuần/ngày, giới hạn đội/người/giờ và tránh tạo trùng bản giao việc, không tự động xuất vật tư hoặc tạo đơn mua.
4. Kiểm thử nghiệp vụ Frappe cùng dữ liệu mẫu, sau đó mới tạo PR tích hợp/triển khai host Docker.

## Ghi chú
Vite có cảnh báo chung về bundle lớn và một số class Tailwind, không phải lỗi từ Plan Norm. Nên lazy-load PlanNormSettings sau khi tích hợp để giảm tải bundle ban đầu.
