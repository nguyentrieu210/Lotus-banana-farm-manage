# API Contracts

Tất cả là whitelisted method của Frappe. Quyền theo các vai trò hiện có của công việc ngoài vườn: tổ trưởng, đội trưởng, quản lý vườn, kỹ thuật vườn.

## Báo cáo ngày (`lot_report`)

| Method | Tham số | Kết quả |
|---|---|---|
| `today` | `farm`, `team`, `date` | Báo cáo của tổ trong ngày (tạo nháp nếu chưa có), gồm: thẻ lô (lô giao cố định và Round đang mở của tổ), việc đến hạn của mỗi lô, đợt màu còn buồng, cách ly, các dòng đã nhập, người có lượt máy theo buổi |
| `save_lot` | `report`, `block`, `lines[]` (`work_type`, `qty`, `bunch_tag`, `reason`, `reject_stage`, `weight_kg`, `area_ha`, `done`, `people[]`, `materials[]`), `expected_modified` | Các dòng đã lưu của lô và lỗi từng dòng. Có lỗi thì không lưu dòng nào |
| `send` | `report` | Trạng thái Sent; báo các dòng máy đọc chưa được kiểm |
| `confirm` | `report` | Confirmed, số dòng, lỗi từng dòng. Chặn khi người xác nhận là người nhập |
| `amend` | `entry`, `values`, `reason` | Dòng mới; dòng cũ chuyển Voided |
| `reopen` | `report`, `reason` | Reopened |
| `status` | `farm`, `crew`, `date` | Tổ chưa gửi, tổ chưa được xác nhận, số bất thường, lô quá hạn |
| `my_pay` | `farm`, `month` | Tiền khoán tạm tính của tổ và của từng người, theo quyền xem |

`save_lot` và `send` dành cho tổ trưởng của tổ, đội trưởng của đội và quản lý vườn. `confirm` dành cho đội trưởng hoặc quản lý vườn.

## Phiếu giấy và ảnh (`lot_paper_form`)

| Method | Tham số | Kết quả |
|---|---|---|
| `form_url` | `report` | Đường dẫn trang in phiếu của tổ trong ngày |
| `read_photo` | `report`, `file_url` | Các dòng nháp do máy đọc, kèm `review_flags`; bản máy đọc được lưu vào báo cáo |

Giới hạn số lượt dùng chung với `document_ai.read`.

## Vòng chăm sóc (`care_cycle`)

| Method | Tham số | Kết quả |
|---|---|---|
| `due` | `farm`, `crew`, `from`, `to` | Mỗi lô × việc: lần xong gần nhất, ngày đến hạn, số ngày quá hạn, đã giao cho tổ nào |
| `assign` | `farm`, `work_type`, `blocks[]`, `team`, `due_date` | Các Round đã tạo. Lô đã có Round đang mở cho việc đó thì được báo ra |
| `reassign` | `assignment`, `team`, `reason` | Round đã đổi tổ |
| `cancel` | `assignment`, `reason` | Round đã hủy |
| `rules` | `farm` | Các luật vòng và phiên bản |
| `save_rule` | luật vòng | Phiên bản mới, chờ duyệt |

`assign` dành cho đội trưởng và quản lý vườn. `save_rule` chỉ dành cho quản lý vườn.

## Màu dây và thu hoạch (`ribbon_board`)

| Method | Tham số | Kết quả |
|---|---|---|
| `board` | `farm`, `zone`, `block` | Lô × đợt màu: cắt, bao, hủy, thu, còn trên cây, tuổi tuần, tuần thu dự kiến |
| `harvest_due` | `farm`, `week` | Các đợt đến tuổi thu trong tuần theo lô; lô đang cách ly được đánh dấu |

## Xưởng (`shift`)

| Method | Tham số | Kết quả |
|---|---|---|
| Lưu ca (mở rộng API hiện có) | Thêm `sources[]` (`block`, `bunch_tag`, `bunches`, `kg`, `harvest_entry`) | Ca đã lưu, thùng và thành phẩm chia theo từng nguồn |
| `trace` | `shift` | Nguồn → dòng thu hoạch → các dòng phun ở lô đó trước ngày thu |
| `finance.costing.receive_shift` | `shift` | Phiếu nhập kho thành phẩm nháp của ca: thành phẩm và phụ phẩm theo kg, giá trị chia theo kg nguồn từ chi phí dở dang của từng lô. Thay cho `receive_harvest` theo `Harvest Lot`. Chỉ kế toán dùng |

## Dự thu

| Method | Tham số | Kết quả |
|---|---|---|
| `block_forecast.board` | Giữ như spec 001 | Nạp số từ sổ lô; bỏ các khóa của engine cũ |
| `block_forecast.trace` | Giữ như spec 001 | Trỏ về dòng sổ lô gốc |
| `forecast_snapshot.ensure_weeks` | `farm` | Tạo các bản chốt còn thiếu theo mốc 0 giờ thứ Hai; được gọi khi khởi động phiên |
| `forecast_snapshot.variance`, `forecast_snapshot.suggest_parameters` | Giữ như spec 001 | Thêm kg/buồng và thùng/buồng lấy từ xưởng |

## Báo cáo (`field_reports`)

| Method | Tham số | Kết quả |
|---|---|---|
| `morning` | `farm`, `crew`, `date` | Thẻ và chi tiết: tổ chưa gửi, chưa xác nhận, số bất thường, việc quá hạn, lô cách ly, đợt đến tuổi thu |
| `week` | `farm`, `week`, `zone`, `block`, `team` | Thẻ và chi tiết: việc theo lô, bảng màu dây, thu hoạch và đóng gói, dự thu so với thực tế; tình trạng từng lô để tô bản đồ |
| `month` | `farm`, `month`, `zone`, `block`, `team` | Sản lượng và các tỷ lệ; công và tiền khoán theo lô; vật tư xuất kho so với vật tư báo dùng |

Xuất Excel làm trên trình duyệt từ các dòng chi tiết.

## Chuyển dữ liệu (`lot_ledger_migrate`, chạy bằng bench)

| Method | Tham số | Kết quả |
|---|---|---|
| `preview` | `farm` | Số dòng sẽ chuyển và sẽ hủy; lỗi từng dòng |
| `commit` | `farm` | Như `preview` nhưng ghi thật; chạy lại không ghi trùng |

## Dọn đồ cũ (`legacy_purge`, chạy bằng bench, chỉ System Manager)

| Method | Tham số | Kết quả |
|---|---|---|
| `preview` | không có | Chỉ đọc. Trả về: số dòng từng bảng sẽ xóa; số giá trị khác rỗng của các trường sẽ gỡ trên chứng từ (chiều Vụ, `lotus_work_plan`, `lotus_harvest_lot`, trường trỏ `Material Requirement`); các kỳ lương đã hạch toán có dùng `Labor Allocation`; danh sách chặn (nếu có) |
| `commit` | `archive_dir` | Sao lưu, xuất từng bảng ra JSON (kèm số dòng và mã kiểm), rồi xóa: dữ liệu → trường tùy chỉnh và chiều kế toán → DocType. Dừng nếu `preview` có danh sách chặn. Chạy lại không lỗi |
