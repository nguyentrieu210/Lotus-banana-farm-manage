# Implementation Plan: Làm lại chăm sóc vườn, chăm sóc buồng, thu hoạch, báo cáo và dự thu

**Branch**: `002-cham-soc-thu-hoach-du-thu` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-cham-soc-thu-hoach-du-thu/spec.md`

## Summary

Mọi việc trên lô được gom về một sổ. Các thay đổi chính:

- **Sổ lô:** `Lotus Work Entry` trở thành dòng sổ lô. Bỏ bắt buộc phiếu; thêm trạng thái, khóa nguồn, vụ, lý do hủy và kg.
- **Báo cáo ngày:** mỗi tổ mỗi ngày có một báo cáo (bảng mới `Lotus Daily Report`), nhập theo thẻ lô và hộp nhập. Tổ trưởng tự nhập hoặc người khác nhập hộ; có in phiếu giấy và cho máy đọc ảnh phiếu.
- **Giao việc theo vòng:** `Work Schedule Rule` thêm kiểu vòng tính từ lần xong gần nhất. Đội trưởng giao nhiều lô một lần, mỗi lô thành một `Lotus Work Assignment` loại Round.
- **Một nguồn số:** bảng màu dây, dự thu, báo cáo và tiền khoán đều tính từ sổ lô. Engine dự thu của spec 001 giữ nguyên, chỉ đổi nguồn đọc.
- **Bản chốt tuần:** tạo khi có người mở ứng dụng, dựng lại đúng số liệu trước 0 giờ thứ Hai.
- **Cách ly:** thu hoạch bị chặn khi lô đang cách ly thuốc.
- **Xưởng:** `Packhouse Shift` ghi nguồn buồng theo lô và đợt màu.
- **Giá thành:** bỏ chiều kế toán "Vụ"; nhập kho thành phẩm theo ca đóng gói.
- **Dọn sạch:** sổ buồng `Lotus Bunch Event` được chuyển sang sổ lô. 76 bảng đời cũ cùng màn hình, menu và mã bị xóa hẳn sau khi lưu trữ dữ liệu. Kho, tài chính, lương chuyển sang đọc sổ lô. Mảng vườn đi từ 99 bảng xuống 25 bảng ([cleanup.md](cleanup.md)).

## Technical Context

**Language/Version**: Python 3.14 (backend), JavaScript ES2022 với Vue 3 (frontend)

**Primary Dependencies**: Frappe/ERPNext v16 và HRMS (chấm công), app `lotus_farm`; Vue 3, Vant 4 (điện thoại), shadcn-vue trên reka-ui và `DataTable` AG Grid (máy tính); Groq để đọc ảnh (đang dùng cho chứng từ mua hàng)

**Storage**: MariaDB 11.8 qua DocType Frappe

**Testing**: `node --test` với happy-dom cho frontend; unit test Python cho module thuần; integration trong `tests/integration` chạy bằng bench

**Target Platform**: Web máy tính và PWA điện thoại (`/work`), Docker trên VPS

**Project Type**: Ứng dụng web

**Performance Goals**:
- Mở Hôm nay của một tổ dưới 2 giây.
- Lưu một lô dưới 1 giây.
- Ba màn báo cáo và dự thu toàn vườn dưới 3 giây, với 64 lô và khoảng 50.000 dòng sổ lô một năm.

**Constraints**:
- Máy chủ không có container chạy lịch và giữ nguyên như vậy; việc định kỳ chạy khi có người mở ứng dụng.
- Nhập liệu bằng thẻ và hộp nhập, không bảng phẳng.
- Số đang nhập được giữ trên máy khi mất sóng.
- Ảnh phiếu được gửi ra Groq.
- Không sửa thẳng sổ kế toán.

**Scale/Scope**:
- 64 lô, 530.373 cây, khoảng 10 tổ, 26 việc.
- Cao điểm 13.000 đến 25.000 buồng cắt bắp một tháng.
- Khoảng 150 dòng sổ lô một ngày.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá |
|---|---|
| I. Số thực, không suy diễn | Đạt. Số chồi tính từ diện tích và số máy đọc từ ảnh đều ghi rõ là ước tính hoặc máy đọc. Dòng máy đọc phải có người kiểm mới gửi được. Việc chưa có vòng thì không báo đến hạn |
| II. Một nguồn sự thật | Đạt, có hai ngoại lệ ghi ở Complexity Tracking. Sổ lô dựng trên bảng có sẵn. Sổ buồng của spec 001 được chuyển vào rồi bỏ. Mọi số đều đọc từ sổ lô. Bảng, màn hình và mã đời cũ bị xóa hẳn |
| III. Truy vết và kiểm soát | Đạt. Xác nhận theo tổ-ngày. Dòng đã xác nhận chỉ sửa bằng cách hủy có lý do rồi ghi dòng mới. Vòng và tham số có phiên bản, ngày hiệu lực, người duyệt. Bản chốt không sửa được |
| IV. Quy tắc tách riêng, có kiểm thử | Đạt. Quy tắc nằm trong module thuần có unit test. Các luồng gửi, xác nhận, sửa, giao vòng và xưởng có integration test. Component có mount test |
| V. Giao diện theo chuẩn chung | Đạt. Máy tính dùng `components/ui`, `DataTable`, `WorkspaceModal`. Điện thoại dùng Vant và `LotusMobile*`. Toàn bộ chữ tiếng Việt |
| Ràng buộc vận hành | Đạt. Sao lưu trước khi chuyển dữ liệu. Chuyển sổ buồng theo khóa nguồn, chạy lại không trùng. Đọc ảnh có xem trước và đánh dấu từng dòng. Xóa đồ cũ phải lưu trữ JSON từng bảng trước, và dừng nếu dữ liệu dính chứng từ đã ghi sổ. Nhập kho thành phẩm đi qua phiếu kho chuẩn, không ghi thẳng sổ |
| Quy trình phát triển | Đạt. Làm trên nhánh 002. Test và build phải qua trước khi lên VPS. Chỉ commit và triển khai khi chủ vườn yêu cầu |

Đánh giá lại sau Phase 1: không phát sinh vi phạm mới. Cách chia buổi công theo trọng số (research R3) không phạm nguyên tắc nào, nhưng là thay đổi cách chia tiền nên cần chủ vườn biết khi duyệt tasks.

## Project Structure

### Documentation (this feature)

```text
specs/002-cham-soc-thu-hoach-du-thu/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
├── cleanup.md           # kiểm kê đồ cũ: bảng xóa, bảng giữ, chỗ phải sửa, cách lưu trữ
├── checklists/requirements.md
└── tasks.md             # do /speckit-tasks tạo
```

### Source Code (repository root)

```text
lotus_farm/
├── lot_ledger_rules.py        # mới, thuần: trạng thái dòng, trần, màu dây, cách ly, trọng số buổi, tiền tạm tính
├── lot_report.py              # mới: Hôm nay, lưu, gửi, xác nhận, sửa, mở lại, trạng thái (thay bunch_posting và field_report.save_entry)
├── lot_paper_form.py          # mới: phiếu giấy, đọc ảnh qua document_ai
├── care_cycle_rules.py        # mới, thuần: đến hạn, quá hạn, xong vòng
├── care_cycle.py              # mới: danh sách đến hạn, giao nhiều lô, đổi tổ, hủy giao, sửa vòng
├── ribbon_board.py            # mới: bảng màu dây, danh sách cần thu
├── packout_rules.py           # mới, thuần: chia thùng theo kg, kg/buồng, thùng/buồng
├── field_reports.py           # mới: Sáng nay, Tuần, Tháng (thay work_report và bunch_report)
├── lot_ledger_migrate.py      # mới: chuyển sổ buồng, hủy dòng bản thử
├── legacy_purge.py            # mới: đếm, lưu trữ JSON, xóa đồ cũ (preview / commit)
├── finance/costing.py, rules.py, assets.py, planning.py, stock.py, setup.py  # sửa: bỏ chiều Vụ, nhập kho thành phẩm theo ca, dự thu chung
├── warehouse_issue.py, warehouse.py, warehouse_planning.py, stock_bridge.py  # sửa: bỏ xuất theo kế hoạch ngày và cầu nối cũ
├── farm_land.py, field.py, scoping.py, map_import.py, reporting.py          # sửa: bỏ thửa và bảng cũ, đọc sổ lô
├── push_notifications.py, user_admin.py                                      # sửa: bỏ phần kế hoạch và kết quả ngày cũ
├── (khoảng 35 module cũ bị xóa, xem cleanup.md mục 4)
├── field_report.py            # sửa: Round theo vòng, nghiệm thu, tiền khoán đọc sổ lô; bỏ save_entry
├── field_report_rules.py      # sửa: chia theo trọng số buổi
├── block_forecast.py          # sửa: nạp dữ liệu từ sổ lô
├── forecast_snapshot.py       # sửa: tạo khi mở ứng dụng, dựng theo mốc
├── bunch_opening_import.py    # sửa: ghi vào sổ lô
├── shift.py                   # sửa: nguồn buồng theo lô và đợt màu
├── document_ai.py             # sửa: thêm khuôn đọc phiếu ngày
├── hr_period.py               # sửa nhỏ: cộng trọng số buổi
├── finance/payroll.py         # sửa nhỏ: công theo lô từ trọng số
├── console.py                 # sửa: gọi tạo bản chốt tuần khi khởi động phiên
├── www/lotus_daily_form.html  # mới: phiếu giấy in
├── www/lotus_daily_form.py    # mới
└── lotus_farm/doctype/
    ├── lotus_daily_report/        # mới
    ├── packhouse_shift_source/    # mới, bảng con của Packhouse Shift
    ├── lotus_work_entry/          # sửa: thành dòng sổ lô
    ├── lotus_work_session/        # sửa: trọng số, khóa duy nhất mới
    ├── work_schedule_rule/        # sửa: rút gọn thành luật vòng chăm sóc, thêm khu
    ├── lotus_forecast_snapshot/   # sửa: mốc, khóa tuần
    ├── lotus_bunch_event/         # xóa sau khi chuyển và đối chiếu
    └── (75 thư mục DocType đời cũ khác: xóa, xem cleanup.md mục 1)

frontend/src/
├── field-report-navigation.js     # sửa: 7 mục
├── FieldReportApp.vue             # sửa
├── WorkMobile.vue                 # sửa: Hôm nay, Giao việc, Xác nhận, Tôi
├── lot-entry-model.js             # mới, thuần: gom dòng theo lô, nháp trên máy
├── components/field/
│   ├── LotCards.vue               # mới: thẻ lô của tổ trong ngày
│   ├── LotEntryModal.vue          # mới: hộp nhập mọi việc của một lô
│   ├── DayConfirm.vue             # mới: xác nhận tổ-ngày, sửa có lý do
│   ├── CareDueList.vue            # mới: lô đến hạn, giao nhiều lô
│   ├── RibbonBoard.vue            # mới: bảng màu dây, cần thu
│   └── PaperPhotoReview.vue       # mới: kiểm dòng máy đọc
│   (bỏ WorkTicket, WorkEntryForm, WorkBunch, WorkBunchSheet khi màn mới chạy)
├── components/report/
│   ├── MorningReport.vue          # mới
│   ├── WeekReport.vue             # mới, có bản đồ lô
│   └── MonthReport.vue            # mới
│   (bỏ GardenCareReport, BunchCareReport, PackhouseReport, ProtectionReport, PivotChart, PivotFilter)
└── tests/                         # mount test cho component mới, unit test lot-entry-model

tests/integration/
├── verify_lot_ledger.py           # mới
├── verify_care_cycle.py           # mới
└── verify_packout_sources.py      # mới
```

**Structure Decision**: Giữ một app Frappe và một frontend như hiện có. Dùng lại các bảng có sẵn; chỉ thêm một bảng chính và một bảng con.

## Thứ tự làm (gợi ý cho tasks)

1. **Nền:** sổ lô trên `Lotus Work Entry`, chuyển sổ buồng, trọng số buổi, chặn thu hoạch khi cách ly.
2. **US1:** báo cáo ngày (Hôm nay, gửi, xác nhận, sửa, nhập hộ), kiểm tra sâu bệnh, tiền tạm tính.
3. **US2:** bảng màu dây, danh sách cần thu, thu hoạch.
4. **US3:** vòng chăm sóc (rút gọn bảng luật lịch) và giao Round.
5. **US4:** dự thu đọc sổ lô. Tổng quan và kế hoạch tài chính dùng chung API dự thu. Bản chốt tạo khi mở ứng dụng.
6. **US6:** xưởng và nhập kho thành phẩm theo ca. Phải xong trước lứa thu đầu, khoảng cuối tháng 12/2026. Làm trước US7 để có cách nhập kho mới rồi mới xóa cách cũ.
7. **US7, dọn sạch:**
   - chuyển giá thành, tài sản, lương, kho sang nguồn mới (R15, R16);
   - chạy `legacy_purge.preview` trên bản sao dữ liệu thật;
   - xóa màn hình, mã, bảng, trường và chiều Vụ;
   - quét lại để chắc không còn tham chiếu.

Phần nào được thay trong phase nào thì xóa phần cũ ngay trong phase đó. Ví dụ: US1 xóa `bunch_posting.py`, US3 xóa định mức cũ, US4 xóa các engine dự thu cũ, US5 xóa báo cáo Pivot. US7 xóa phần đời cũ còn lại.
8. **US1 phần sau:** in phiếu giấy, đọc ảnh phiếu. Đo tỷ lệ đọc đúng trên phiếu thật trước khi bật cho các tổ.
9. **US5:** ba màn báo cáo, bản đồ lô, gọn menu còn 7 mục.

Bước 1 và 2 đủ để đưa lên chạy thử với Đội khu A + B. Lỗi cách ly ở bước 1 có thể tách ra sửa riêng trên bản đang chạy trước lứa thu đầu.

Khi lên VPS, `legacy_purge.commit` chạy cùng lần triển khai có xóa mã, sau khi đã sao lưu và xem kết quả `preview` trên bản thật. Bước này cần mật khẩu SSH do chủ vườn cung cấp lúc làm.

## Complexity Tracking

| Vi phạm | Vì sao cần | Phương án đơn giản hơn bị loại vì |
|---|---|---|
| Thêm bảng `Lotus Daily Report` | Cần chỗ giữ trạng thái đã gửi, người nhập hộ, ảnh phiếu, bản máy đọc và người xác nhận của một tổ trong một ngày | Gom theo khóa tổ-ngày như spec 001 thì không có chỗ cho ảnh, bản máy đọc và trạng thái gửi |
| Thêm bảng con `Packhouse Shift Source` | Ca đóng gói phải biết buồng đến từ lô và đợt màu nào | Chuỗi `Harvest Lot` / `Packout Run` cũ cần bật quản lý theo lô hàng và gắn thửa, trái quyết định chỉ quản lý đến lô. Chuỗi này cũng bị xóa trong spec này |
