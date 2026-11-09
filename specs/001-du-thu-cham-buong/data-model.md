# Data Model

## Thay đổi trên bảng có sẵn

### Lotus Work Entry

| Trường mới | Kiểu | Ghi chú |
|---|---|---|
| `confirmed_by`, `confirmed_at` | Link User, Datetime | Đội trưởng xác nhận theo ngày |
| `posted_event` | Link Lotus Bunch Event | Dòng sổ buồng đã sinh |

**Quy tắc**: Số buồng phải nguyên. Sửa sau xác nhận phải có lý do, chuyển dòng sổ buồng cũ sang Voided rồi ghi lại.

### Work Type.lotus_bunch_stage

Thêm giá trị `Sucker Select`, `Harvest`.

### Lotus Block Forecast Profile

Thêm `cut_to_harvest_min_days`, `cut_to_harvest_max_days` nếu chưa có.

## Bảng mới

### Farm Block (thêm trường)

`lotus_current_cycle_no` (Int): vụ hiện tại của lô, quản lý vườn chốt khi chuyển vụ. Đổi số này không làm thay đổi các dòng sổ buồng đã ghi.

### Lotus Bunch Event (sổ buồng theo lô)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `farm`, `farm_block`, `work_team` | Link | Lô bắt buộc; không có thửa; tổ nhập |
| `cycle_no` | Int | Vụ của lô tại thời điểm ghi; chọn chồi thuộc vụ kế tiếp |
| `event_type` | Select | Sucker Select, Bud Injection, Cut Bud, Reject, Harvest |
| `event_date` | Date | Ngày làm việc |
| `qty` | Int | Số buồng; với Sucker Select là số chồi ước tính |
| `area_ha` | Float | Chỉ Sucker Select |
| `bunch_tag` | Link Bunch Tag | Bắt buộc với Cut Bud, Harvest và Reject sau cắt bắp |
| `reject_stage`, `reason` | Select, Link Cancellation Reason | Chỉ Reject |
| `weight_kg` | Float | Chỉ Harvest |
| `source_type`, `source_name` | Select, Data | Work Entry, Opening Import, Manual |
| `source_key` | Data, duy nhất | Chống ghi trùng: `work-entry:<name>`, `opening:<lô>:<tuần>:<lần>`, `daily:<lô>:<ngày>:<việc>:<màu>:<lý do>:<tổ>` |
| `state` | Select | Draft, Confirmed, Voided |
| `entered_by`, `confirmed_by`, `confirmed_at`, `void_reason`, `notes` | | `entered_by` là người lưu số gần nhất |

**Quy tắc**: Dòng nháp bỏ được trên bảng nhập. Dòng đã xác nhận không xóa; sửa là chuyển dòng cũ sang Voided có lý do rồi tạo dòng mới. Lần cắt lấy từ `week_half` của `Bunch Tag`. Tổng thu cộng loại sau cắt của một lô và màu không vượt số cắt của màu đó.

### Lotus Forecast Snapshot

`farm`, `snapshot_date`, `week_label`, `profile_refs`, `kind` (Weekly / Manual), `rows_json` (lô, tuần thu, tầng, buồng, kg), `total_bunches`, `total_kg`, `created_by`. Không sửa sau khi tạo.

## Ánh xạ khi xác nhận

| Công đoạn trên báo cáo | Dòng sổ buồng |
|---|---|
| Chọn F trên phiếu | Sucker Select khi đội trưởng xác nhận; `qty` = số cây × ha đã làm ÷ diện tích lô; vụ theo FR-026 |
| Bảng nhập nhanh: chích, cắt, loại, thu | Dòng tương ứng ở trạng thái Draft, xác nhận theo ngày |
| Bag trên phiếu | Không ghi; trần theo màu tính từ sổ buồng |
| Care, Prop trên phiếu | Không ghi; không màu dây, trần theo số cây của lô |
| Sổ cắt bắp đầu kỳ | Cut Bud, `source_type` = Opening Import, Confirmed |

## Dữ liệu chuẩn bị

Tạo danh mục lý do loại buồng. Danh mục lô thêm `lotus_current_cycle_no` và ngày chọn chồi vào phần sửa được và file Excel. Đánh dấu các lô khu A có `forecast_count_source` là `Census Confirmed` theo xác nhận của chủ vườn.

## Trạng thái ghi nhận

Nháp (tổ đã lưu) → Đã xác nhận (đã ghi vào sổ buồng) → Sửa có lý do (hủy và ghi lại).
