# Lotus Banana Farm Manage

Custom Frappe/ERPNext app for Lotus banana farm operations.

## Mô hình vườn

Company → Farm (vườn) → Farm Block (lô). Lô là đơn vị nhỏ nhất; khu là trường `farm_zone` của lô, không có thửa.

Mọi việc ngoài vườn đi vào **sổ lô** (`Lotus Work Entry`): tổ gửi báo cáo ngày (`Lotus Daily Report`) gồm các dòng của từng lô (cắt bắp, bao buồng, thu hoạch, hủy buồng, chăm sóc, phun thuốc…), theo phiếu giao việc theo lô (`Lotus Work Assignment`), buổi công từng người (`Lotus Work Session`) và nghiệm thu khoán cả lô (`Lotus Work Inspection`). Chỉ dòng đội trưởng đã xác nhận mới được tính: dự thu, bảng màu dây, vòng chăm sóc, tiền khoán và báo cáo. Ca đóng gói (`Packhouse Shift`) lấy buồng từ dòng thu hoạch đã xác nhận. Dự thu tính theo lô từ sổ lô, mỗi thứ Hai có một bản chốt (`Lotus Forecast Snapshot`).

Hướng dẫn: [báo cáo ngày theo lô](docs/FIELD_REPORT.md), [màu dây, thu hoạch, xưởng và dự thu](docs/CHAM_BUONG_DU_THU.md). Thiết kế: `specs/002-cham-soc-thu-hoach-du-thu/`. Bảng đời cũ (chuỗi Farm Plot / vụ / kế hoạch ngày, thu hoạch – QC – packout cũ, dự thu cũ, nhập OneDrive) đã gỡ hẳn: danh sách và lý do ở `specs/002-cham-soc-thu-hoach-du-thu/cleanup.md`, công cụ lưu trữ rồi xóa là `lotus_farm/legacy_purge.py`.

## Màn hình

Trên máy tính, mọi phân hệ nằm trong một ứng dụng `/lotus` (Vue 3, Vue Router, Pinia; shadcn-vue, token Lotus và AG Grid, xem [UI stack](docs/UI_STACK.md)). Menu chỉ hiện phần tài khoản được phép:

- **Tổng quan** `/lotus/reports`: biểu đồ đất, công việc, thu hoạch, đóng gói, hủy buồng, dự thu, kho, nhân sự, mua bán (`lotus_farm.reporting.charts`).
- **Việc hằng ngày** `/lotus/cong-viec`: Hôm nay, Giao việc, Màu dây & thu hoạch, Xưởng, Dự thu (`/lotus/forecast`), Báo cáo, Thiết lập; danh mục màu dây `/lotus/mau-day`.
- **Vườn & lô** `/lotus/farms`, bản đồ lô `/lotus/map`.
- **Kho** `/lotus/kho`, **Mua hàng** `/lotus/mua-hang`, **Tài chính – Kế toán** `/lotus/tai-chinh`, **Nhân sự** `/lotus/nhan-su` và `/lotus/cham-cong`.
- **Thiết lập**: danh mục `/lotus/admin/masters`, người dùng & phân quyền `/lotus/nguoi-dung`.

Trên điện thoại: `/lotus/mobile` là trang chủ theo quyền; tổ trưởng và đội trưởng dùng `/work` (Hôm nay, Giao việc, Xác nhận, Tôi); kho `/warehouse`, mua hàng `/buying`, nhân sự `/hr-mobile`.

Build giao diện: `npm ci --prefix frontend && npm run --prefix frontend build`, rồi migrate site.

## Kế hoạch tài chính

**Tài chính – Kế toán → Kế hoạch tài chính** (`/lotus/tai-chinh?tab=planning`): lập ngân sách theo tháng, lấy sản lượng từ dự thu hiện tại của vườn (cùng số với màn Dự thu), dự phóng doanh thu / lợi nhuận / dòng tiền, so sánh kịch bản và duyệt khóa kế hoạch. [Quy tắc và cách triển khai](docs/KE_HOACH_TAI_CHINH.md).

## ERPNext boundary

ERPNext remains responsible for standard commercial and inventory objects such as Item, Customer, Sales Order, Warehouse, Stock, Delivery and Finance. Lotus Farm adds the farm-specific records above: the lot ledger, packhouse shifts and the lot forecast. A closed packhouse shift is received into stock through a draft ERPNext Stock Entry that the accountant reviews.

## Install

```bash
bench get-app https://github.com/nguyentrieu210/Lotus-banana-farm-manage.git
bench --site <site> install-app lotus_farm
bench --site <site> migrate
```

ERPNext is required. Runtime installation on a real Frappe site is still required before calling this production-ready. Deployment of a release image: [deployment/README.md](deployment/README.md).

## Tests

Pure checks without a Frappe installation:

```bash
python -m pip install "openpyxl>=3.1.5,<4"
python -m unittest discover -s tests -v
```

On a **disposable** ERPNext v16 site:

```bash
bench --site lotus.test run-tests --module lotus_farm.tests.test_brd
```

The site suite includes a concurrency test with committed test fixtures. Never run it on production. The GitHub `Lotus BRD checks` workflow provisions that disposable site and migrates twice.
