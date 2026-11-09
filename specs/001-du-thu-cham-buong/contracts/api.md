# API Contracts

Tất cả là whitelisted method của Frappe. Kiểm quyền theo vai trò hiện có của báo cáo ngày.

## Nhập liệu

| Method | Tham số | Kết quả |
|---|---|---|
| `bunch_posting.day_sheet` | `farm`, `crew`, `date` | Các lô của đội, màu dây trong ngày, số đã nhập, danh mục lý do |
| `bunch_posting.save_day` | `farm`, `crew`, `date`, `team`, `rows[]` (`block`, `event_type`, `qty`, `bunch_tag`, `reason`, `reject_stage`, `weight_kg`) | Số dòng đã lưu và đã bỏ, lỗi từng dòng. Có dòng lỗi thì không lưu gì |
| `bunch_posting.day_status` | `farm`, `crew`, `date` | Số chờ xác nhận, lô chưa báo, số bất thường |
| `bunch_posting.confirm_day` | `farm`, `crew`, `date` | Số dòng đã xác nhận, lỗi từng dòng |
| `bunch_posting.amend` | `event`, `values`, `reason` | Dòng sổ buồng mới |

`save_day` cho tổ trưởng và đội trưởng của đội. `confirm_day` chỉ cho đội trưởng hoặc quản lý vườn, và không xác nhận được dòng do chính mình nhập.

## Số đầu kỳ

| Method | Tham số | Kết quả |
|---|---|---|
| `bunch_opening_import.preview` | `farm`, `content` (base64 file .xlsx), `filename` | Dòng hợp lệ theo lô, tuần, lần, màu, số buồng; lỗi từng dòng; `token` |
| `bunch_opening_import.commit` | `farm`, `token` | Số dòng đã ghi, số dòng bỏ qua do đã có |

## Dự thu

| Method | Tham số | Kết quả |
|---|---|---|
| `block_forecast.board` (mở rộng) | `farm`, `zone`, `block` | Thêm khóa `bunch`: `weeks[]`, `rows[]` có `week`, `block`, `layer`, `confidence`, `bunches`, `kg`, `cartons`, `ribbon`; `months`, `blocks`, `zones`, `totals`, `warnings`. Các khóa cũ giữ nguyên tới khi gỡ engine cũ (T040) |
| `block_forecast.trace` | `farm`, `block`, `week`, `layer` | Các dòng sổ buồng gốc và bộ tham số |

Mức tin cậy: `high` (đã cắt bắp), `medium` (đã chích bắp), `low` (số cây, chọn chồi, tuổi cây).

## Đối chiếu

| Method | Tham số | Kết quả |
|---|---|---|
| `forecast_snapshot.create` | `farm` | Bản chốt; lịch tự động mỗi thứ 2 |
| `forecast_snapshot.variance` | `farm`, `from_week`, `to_week`, `group_by` | Dự thu, thực tế, sai số |
| `forecast_snapshot.suggest_parameters` | `farm`, `block` | Tham số đề xuất kèm số mẫu; không tự áp dụng |
