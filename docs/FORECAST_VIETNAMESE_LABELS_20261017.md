# Quy ước tên tiếng Việt — Dự thu và Kế hoạch (17/10/2026)

- Toàn bộ tên trường, tên lựa chọn, tiêu đề bảng và trạng thái người dùng nhìn thấy phải dùng tiếng Việt ngắn, dễ hiểu.
- Các mã dữ liệu trong ERPNext/Frappe như `forecast_basis`, `Manual`, `Released` được GIỮ NGUYÊN để không ảnh hưởng dữ liệu, quyền và công thức.
- Tên hiển thị chung tra tại `frontend/src/vn-domain-labels.js`, áp dụng qua `label()` và `stateLabel()` trong `frontend/src/labels.js`.
- Tên có ý nghĩa riêng ở phiếu Dự thu (như `item` = `Sản phẩm dự kiến`) đặt trong `ForecastForm.vue`; không dịch kiểu chung thành tên sai nghiệp vụ.
- `Harvest Forecast` = `Dự thu`, `Gross Bunch Forecast` = `Dự thu ngoài vườn (kg buồng)`, `Packed Forecast` = `Thành phẩm dự kiến (kg)`. Không nhầm kg buồng với kg thành phẩm.
- Lựa chọn: `Manual` = `Nhập tay`, `Sucker Selection` = `Theo đợt chọn chồi`, `Shooting Operations` = `Theo số buồng đã trổ`, `Cut Bud Operations` = `Theo số buồng đã cắt bắp`.
- Trạng thái: `Draft` = `Nháp`, `Released` = `Đã phát hành`, `Superseded` = `Đã thay thế`, `Closed` trong Dự thu = `Đã kết thúc`.
- Khi thêm trường mới, cập nhật tên tiếng Việt kèm kiểm thử. Không dịch lại mã hệ thống hoặc thay `options` trong DocType JSON.

Kiểm tra: `npm test` (167/167) và `npm run build` đạt; Docker image `lotus-forecast-vietnamese:v1-20261017`, giữ nguyên backend từ bản dự thu trước. Các trang `/lotus/forecast` và `/lotus/plans` trả HTTP 200 khi chạy tại localhost:8080.
