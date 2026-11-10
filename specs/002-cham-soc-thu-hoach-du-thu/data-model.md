# Data Model

## Lotus Work Entry → dòng sổ lô

Các trường có sẵn giữ nguyên: `farm`, `company`, `crew`, `work_team`, `farm_block`, `work_type`, `posting_date`, `qty`, `bunch_tag`, `done`, `under_norm`, `notes`, `entered_by`, `confirmed_by`, `confirmed_at`, `people` (Lotus Work Entry Person: người, sáng, chiều), `materials` (Lotus Work Entry Material: vật tư, số lượng, liều, phiếu xuất kho, `phi_days`).

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `assignment` | Link Lotus Work Assignment | Bỏ bắt buộc. Có giá trị khi dòng thuộc một Round hoặc một giao cố định chăm buồng |
| `daily_report` | Link Lotus Daily Report | Mới. Bắt buộc, trừ dòng nhập đầu kỳ |
| `farm_block`, `work_team`, `work_type` | Link | Chuyển thành bắt buộc |
| `stage` | Select | Mới. Lấy từ `Work Type.lotus_bunch_stage` lúc lưu: Sucker Select, Bud Injection, Cut Bud, Bag, Care, Prop, Reject, Harvest. Để trống với việc vườn và phun bón |
| `cycle_no` | Int | Mới. Vụ của lô lúc ghi; chọn chồi thuộc vụ kế tiếp (FR-026 spec 001) |
| `uom` | Link UOM | Mới. Đơn vị của `qty` |
| `area_ha` | Float | Mới. Dùng cho chọn chồi và việc tính theo ha |
| `reason` | Link Cancellation Reason | Mới. Chỉ dùng với Reject |
| `reject_stage` | Select: Before Cut, After Cut | Mới. Chỉ dùng với Reject |
| `weight_kg` | Float | Mới. Bắt buộc với Harvest |
| `disease` | Link Disease | Mới. Chỉ dòng kiểm tra sâu bệnh; khi đó `qty` là số cây bị |
| `severity` | Select: Nhẹ, Vừa, Nặng | Mới. Chỉ dòng kiểm tra sâu bệnh |
| `state` | Select: Draft, Sent, Confirmed, Voided | Mới |
| `source_type` | Select: Daily, Photo, Opening Import, Manual | Mới |
| `source_key` | Data, duy nhất | Mới. Chống ghi trùng |
| `machine_read` | Check | Mới. Dòng do máy đọc từ ảnh |
| `review_flags` | Small Text | Mới. Lý do dòng máy đọc bị đánh dấu cần kiểm |
| `rate`, `amount` | Currency | Mới. Chụp lúc xác nhận, với việc khoán số lượng |
| `voided_at`, `void_reason` | Datetime, Small Text | Mới. Thông tin hủy dòng |
| `replaces` | Link Lotus Work Entry | Mới. Dòng mới thay cho dòng đã hủy |
| `posted_event`, `over_cut` | | Bỏ: không còn sổ buồng riêng; vượt trần chuyển thành chặn |

**Quy tắc kiểm** (module thuần `lot_ledger_rules`):

- **Việc buồng:** số lượng phải là số nguyên lớn hơn 0.
- **Cut Bud:** màu dây tự gán theo ngày làm (tuần và nửa tuần của `Bunch Tag`); người nhập không chọn.
- **Bag, Harvest, Reject sau cắt:** chỉ chọn trong các đợt màu còn buồng của lô. Bao, hủy sau cắt và thu cộng dồn không vượt số cắt bắp của lô và đợt màu đó.
- **Bud Injection, Care, Prop:** không có màu dây. Cộng dồn trong vụ không vượt số cây của lô.
- **Harvest:**
  - kg phải lớn hơn 0;
  - bị chặn khi ngày thu không sau `Farm Block.lotus_quarantine_until`;
  - kiểm khi lưu, gửi, xác nhận và sửa.
- **Phun, bón (việc có cờ bắt buộc vật tư):** bắt buộc vật tư, số lượng và liều.
- **Kiểm tra sâu bệnh:** bắt buộc bệnh, số cây bị và mức độ; không có vật tư.
- **Ngày ghi:** không báo cho ngày tương lai; không ghi vào tháng đã khóa sổ.
- **Dòng đã xác nhận:** không sửa trường số liệu. Muốn sửa thì hủy dòng có lý do rồi tạo dòng mới trỏ `replaces`.
- **Xác nhận:** người xác nhận phải khác người nhập.

## Lotus Work Session

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `entry` | Link Lotus Work Entry | Bắt buộc như cũ |
| `assignment` | Link Lotus Work Assignment | Bỏ bắt buộc |
| `weight` | Float | Mới. Lớn hơn 0 và không quá 1; tổng theo người × ngày × buổi bằng 1 |

Khóa duy nhất đổi từ người × ngày × buổi (`lotus_work_session_once`) sang người × ngày × buổi × dòng. Buổi của dòng đã hủy không được tính.

## Lotus Daily Report (mới)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `farm`, `crew`, `work_team` | Link | Vườn, đội, tổ |
| `report_date` | Date | |
| `state` | Select: Draft, Sent, Confirmed, Reopened | |
| `entered_by` | Link User | Người nhập gần nhất |
| `on_behalf` | Check | Nhập hộ từ phiếu giấy |
| `source` | Select: Phone, Paper, Photo | |
| `sent_at` | Datetime | |
| `confirmed_by`, `confirmed_at` | Link User, Datetime | |
| `reopen_reason` | Small Text | Bắt buộc khi mở lại |
| `machine_draft` | Long Text | Kết quả máy đọc (JSON), giữ để đối chiếu |
| `present_morning`, `present_afternoon` | Int | Số người của tổ có lượt máy chấm công |
| `notes` | Small Text | |

Khóa duy nhất: vườn × tổ × ngày. Ảnh phiếu lưu dạng tệp đính kèm của báo cáo.

## Lotus Work Assignment

- `kind` = Round: một lô, một việc, một vòng. Thêm `cycle_rule` (Link Work Schedule Rule).
- `done_report` đổi đích thành Lotus Daily Report (hiện đang trỏ tới một bảng đã bỏ).
- Các trạng thái và trường chụp cách trả, đơn giá giữ nguyên.

## Work Schedule Rule → luật vòng chăm sóc

- **Giữ:** `farm`, `rule_name`, `work_type`, `repeat_days` (độ dài vòng), `valid_from`, `valid_to`, `version`, `approval_state`.
- **Thêm:** `farm_zone` (khu, tùy chọn).
- **Bỏ** (thuộc định mức cũ): `anchor`, `offset_days`, `offset_months`, `repeat_months`, `quantity_basis`, `norm_profile`.
- Tại một ngày, mỗi việc chỉ có một luật đang hiệu lực cho một phạm vi (cả vườn hoặc một khu). Luật theo khu được ưu tiên hơn luật cả vườn.

## Work Type

- `lotus_bunch_stage` thêm hai giá trị Reject và Harvest.
- Thêm việc "Hủy buồng" (Reject, không trả tiền) và "Thu hoạch" (Harvest, công nhật) nếu danh mục chưa có.

## Packhouse Shift Source (bảng con mới của Packhouse Shift)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `farm_block`, `bunch_tag` | Link | Lô, đợt màu |
| `bunches`, `kg` | Int, Float | Số nhận vào ca |
| `harvest_entry` | Link Lotus Work Entry | Dòng thu hoạch |

**Quy tắc:**
- Tổng kg các nguồn bằng `input_kg` của ca.
- Số buồng nhận của một đợt không vượt số đã thu mà chưa vào xưởng.
- Thùng và thành phẩm được chia theo kg, tính khi đọc (module thuần `packout_rules`).

## Lotus Forecast Snapshot

- Thêm `week_start` (Date), `as_of` (Datetime) và `limits` (Small Text: giới hạn của bản dựng lại).
- Với bản Weekly, khóa duy nhất là vườn × `week_start` × `kind`.

## Lotus Bunch Event

Ngừng ghi. Dữ liệu chuyển sang sổ lô; bỏ bảng sau khi đối chiếu tổng số.

## Trạng thái

- **Dòng sổ lô:** Draft → Sent → Confirmed → Voided (kèm dòng thay). Dòng Draft xóa được. Mở lại báo cáo thì dòng Sent về Draft.
- **Báo cáo ngày:** Draft → Sent → Confirmed. Từ Confirmed có thể mở lại (Reopened, phải có lý do), rồi Sent → Confirmed.
- **Round:**
  - Khoán cả lô: Open → Reported → Approved → nghiệm thu Passed (rồi Locked) hoặc Failed (quay về Open).
  - Khoán số lượng và công nhật: từ Approved sang thẳng Passed (giữ `next_state`).
  - Hủy (Cancelled) phải có lý do.

## Khóa nguồn

| Nguồn | `source_key` |
|---|---|
| Báo cáo ngày, kể cả dòng máy đọc đã kiểm | `day:<báo cáo>:<lô>:<việc>:<màu>:<lý do>` |
| Sổ cắt bắp đầu kỳ | `opening:<lô>:<tuần>:<lần>` (giữ từ spec 001) |
| Chuyển từ sổ buồng | Giữ nguyên khóa cũ |

## Chuyển dữ liệu

| Từ | Sang |
|---|---|
| `Lotus Bunch Event` đã xác nhận | Dòng sổ lô Confirmed. `stage` theo `event_type`, việc tương ứng; giữ ngày, lô, tổ, màu, lý do, kg và khóa nguồn |
| `Lotus Bunch Event` nháp | Bỏ (bản thử) |
| `Lotus Work Entry` cũ | Voided, lý do "Bản thử trước sổ lô" |
| `Lotus Work Assignment` loại Round đang mở | Cancelled với cùng lý do. Giao cố định chăm buồng giữ nguyên |
| `Lotus Work Session` cũ | Giữ nguyên; không được tính vì dòng của nó đã hủy |

## Bảng giữ có trường bị gỡ

| Bảng | Trường bỏ |
|---|---|
| Bunch Tag | Trường trỏ `Bunch Operation`; `process_adoption` |
| Work Type | Trường trỏ `Work Category` |
| Packhouse Preprocessing | Trường trỏ `Harvest Lot` |
| Lotus Costing Row | Trường trỏ `Crop Cycle`, thay bằng `cycle_no` (Int) |
| Lotus Asset Allocation Row | Trường trỏ `Crop Cycle` |
| Stock Entry (trường tùy chỉnh) | `lotus_work_plan`, `lotus_harvest_lot`, trường trỏ `Packout Run` |
| Material Request Item (trường tùy chỉnh) | Trường trỏ `Material Requirement` |
| Các chứng từ kế toán | Chiều kế toán "Vụ" (`lotus_crop_cycle`) |

## Bảng xóa

76 bảng, trong đó 18 bảng con. Danh sách đủ ở [cleanup.md](cleanup.md). Trước khi xóa, mỗi bảng được xuất ra một tệp JSON lưu trữ.
