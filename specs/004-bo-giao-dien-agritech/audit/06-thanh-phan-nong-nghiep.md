# Rà soát 06 — Thành phần nông nghiệp: lô, màu dây, tuần, trạng thái, bản đồ, biểu đồ, xưởng

Ngày rà soát: 10/11/2026. Nhánh `004-bo-giao-dien-agritech`, commit `40f8330`.

Cách làm: đọc mã bằng Read, Grep, wc. Không chạy test, build hay trình duyệt. Nhận xét về hiển thị dựa trên mã và phân tích import tĩnh; chỗ chưa xác minh được ghi "chưa kiểm". Tương phản tính theo công thức WCAG 2.x từ mã màu trong `frontend/src/lotus-tokens.css`. Đường dẫn dạng `components/...` là viết tắt của `frontend/src/components/...`; tệp gốc khác ghi từ `frontend/src/`.

## Hiện trạng

### 1. Bảng kê tệp

**A. Công việc ngoài vườn** (`/lotus/cong-viec` trên máy tính, `/work` trên điện thoại). API đều có tiền tố `lotus_farm.`.

| Tệp | Dòng / byte | Vai trò | API | Nơi dùng |
|---|---|---|---|---|
| `frontend/src/FieldReportApp.vue` | 280 / 21.141 | Khung máy tính, 11 `field_view` | `field_report.{bootstrap,setup,payable,user_options,save_crew,save_team,save_work_mode,save_rate}` | `App.vue:58`, nạp trễ |
| `frontend/src/WorkMobile.vue` | 127 / 9.207 | Khung điện thoại, 4 tab | `field_report.{bootstrap,setup}` | `work-mobile-main.js:5` |
| `components/field/LotToday.vue` | 156 / 10.858 | Báo cáo ngày của tổ | `lot_report.{today,open_report,send,confirm,reopen,amend}` | máy tính và điện thoại |
| `components/field/LotCards.vue` | 53 / 4.164 | Thẻ lô của ngày | nhận `lots` | LotToday |
| `components/field/LotEntryModal.vue` | 229 / 18.651 | Hộp nhập một lô | `lot_report.save_lot`, `field_report.item_options` | LotToday |
| `components/field/CrewStatus.vue` | 53 / 3.407 | Tình hình các tổ của đội | `lot_report.status` | LotToday (máy tính), tab Xác nhận (điện thoại) |
| `components/field/PaperPhotoReview.vue` | 92 / 6.389 | Phiếu giấy, đọc ảnh, kiểm lô | `lot_paper_form.{form_url,read_photo}` | LotToday |
| `components/field/RibbonBoard.vue` | 123 / 9.664 | Bảng màu dây, danh sách cần thu | `ribbon_board.board`, `ribbon_board.export_cut_book` | máy tính; điện thoại (`compact`) |
| `components/field/CareDueList.vue` | 149 / 10.883 | Việc đến hạn theo vòng, giao nhiều lô | `care_cycle.{due,assign}` | cả hai |
| `components/field/CareCycleSettings.vue` | 135 / 9.505 | Đặt vòng chăm sóc, phiên bản | `care_cycle.{rule_list,save_rule,approve_rule,delete_rule}` | máy tính |
| `components/field/WorkAssign.vue` | 133 / 10.840 | Phiếu giao việc | `field_report.{assignments,assign}` | cả hai |
| `components/field/WorkTicket.vue` | 136 / 9.675 | Một phiếu, nghiệm thu | `field_report.{ticket,approve,return_ticket,cancel_assignment,reassign,inspection_plan,inspect}` | WorkAssign, WorkInspect |
| `components/field/WorkInspect.vue` | 41 / 2.383 | Phiếu chờ nghiệm thu | `field_report.inspections_due` | cả hai |
| `components/field/PackhouseShifts.vue` | 211 / 15.731 | Ca xưởng, nguồn buồng, truy vết | `shift.{shifts,shift,harvest_sources,save_shift,close_shift,trace}`, `finance.costing.receive_shift` | máy tính |
| `components/field/MyPay.vue` | 45 / 2.658 | Tiền khoán tạm tính | `lot_report.my_pay` | điện thoại |
| `components/report/FieldReports.vue`, `ReportCards.vue` | 76 / 5.286 và 49 / 3.397 | Báo cáo Sáng nay, Tuần, Tháng. Ngoài danh sách giao nhưng là nơi dùng bản đồ tô theo tình trạng | `field_reports.{morning,week,month}`, `field.map_block_data` | máy tính |
| `frontend/src/lot-entry-model.js` | 145 / 8.924 | Hàm thuần của báo cáo ngày, có `swatch()` đổi mã màu dây | — | 8 component |
| `frontend/src/field-work-model.js` | 37 / 2.648 | Nhãn phiếu, tiền tạm tính | — | WorkAssign, WorkTicket, WorkInspect, FieldReportApp |
| `frontend/src/field-report-navigation.js` | 30 / 2.463 | Menu 7 mục | — | thanh bên |
| `frontend/src/FarmWorkApp.vue` | 142 / 16.338 | Danh mục công việc, tổ, vụ, định mức | `farm_workspace.{load,norm_options}`, console `schema/detail/save` | nhúng ở `FieldReportApp.vue:236` |
| `frontend/src/farm-work.css` | 24 / 7.934 | Kiểu của FarmWorkApp | — | `main.js:15` |
| `frontend/src/work-mobile.css` | 71 / 7.487 | Kiểu riêng `/work` | — | `work-mobile-main.js:7` |
| `frontend/src/field-todo.css` | 15 / 1.348 | — | — | không tệp nào import |

**B. Vườn & lô, bản đồ**

| Tệp | Dòng / byte | Vai trò | API | Nơi dùng |
|---|---|---|---|---|
| `frontend/src/FarmLandApp.vue` | 204 / 17.806 | `/lotus/farms`: danh sách lô, thẻ khu, bản đồ, nhập xuất Excel | `farm_land.{overview,save_block,export_blocks,preview_blocks,commit_blocks}`, `field.map_block_data` | `App.vue:59` |
| `components/land/LandBlockDetail.vue` | 181 / 17.973 | Trang một lô, 5 tab | `farm_land.{block_detail,save_block,save_plot}` | FarmLandApp |
| `components/CareMap.vue` | 114 / 13.484 | Bản đồ Leaflet | nhận `collection` | 4 nơi: `App.vue:234`, `FarmLandApp.vue:179`, `LandBlockDetail.vue:105`, `FieldReports.vue:58` |
| `components/PlotMap.vue` | 41 / 2.169 | Bản đồ thửa bằng SVG | — | không tệp nào import |
| `frontend/src/map-land.js` | 40 / 3.265 | Màu tô lô và chú giải theo chế độ | — | CareMap, FarmLandApp, FieldReports |
| `frontend/src/map-zones.js` | 30 / 1.892 | Màu khu, điểm đặt nhãn khu | — | CareMap |
| `frontend/src/map-measure.js` | 26 / 1.813 | Đo khoảng cách, diện tích | — | CareMap |
| `frontend/src/map-imagery.js`, `map-imagery-config.js` | 20 / 1.287 và 59 / 1.549 | Căn ảnh flycam theo ảnh vệ tinh | — | CareMap |
| `frontend/src/care-map.css` | 18 / 3.308 | Kiểu bản đồ | — | `main.js:29` |
| `frontend/src/land.css` | 100 / 7.805 | Kiểu Vườn & lô; dùng lại ở Dự thu và Tài chính | — | FarmLandApp, BlockForecastApp, FinanceApp |

**C. Dự thu, biểu đồ, màu dây**

| Tệp | Dòng / byte | Vai trò | API | Nơi dùng |
|---|---|---|---|---|
| `frontend/src/BlockForecastApp.vue` | 128 / 9.420 | `/lotus/forecast`, 5 tab | `block_forecast.board` | `App.vue:61` |
| `components/BunchWeeklyForecast.vue` | 195 / 16.142 | 13 tuần, 12 tháng, nhịp cắt bắp, theo khu | `block_forecast.trace` | BlockForecastApp |
| `components/BunchChart.vue` | 108 / 8.318 | Cột chồng dựng bằng HTML và CSS, không dùng ECharts | — | BunchWeeklyForecast |
| `components/LotusChart.vue` | 86 / 7.422 | Biểu đồ ECharts dùng chung | — | 23 chỗ: OverviewBoard 8, ReportsWorkspace 14, FinanceApp 1 |
| `components/OverviewBoard.vue` | 30 / 3.481 | Tổng quan: 8 ô số, 8 biểu đồ | nhận `charts` (`reporting.charts`) | ReportsWorkspace |
| `frontend/src/ColorTagCatalogApp.vue` | 157 / 9.969 | `/lotus/mau-day`: lịch màu dây | `bunch_tag_catalog.{catalog,add_manual_period}`, `onedrive_workspace.generate_tags` | `App.vue:62` |
| `frontend/src/forecast-planning.js` | 7 / 1.626 | Nhãn và hàm lọc dự thu | — | `ForecastForm.vue`, ForecastWorkspace |
| `components/ForecastWorkspace.vue` + `forecast-workspace.css` | 126 / 11.005 và 65 / 6.776 | Dự thu kiểu phiếu | — | không màn nào import; `tests/forecast-source-form.mount.test.js` còn mount |
| `components/ForecastPlanner.vue` + `forecast-calendar.css` + `forecast-sample.js` | 101 / 8.674, 55 / 6.200, 45 / 2.938 | Dự thu 36 tháng, có chế độ dữ liệu mẫu | — | không màn nào import; 3 tệp test đọc mã |
| `components/Vip126RollingForecast.vue`, `ZonePlantingSchedule.vue` | 225 / 19.854 và 53 / 3.881 | Dự phóng VIP 126 | `vip126_trial.calendar`, `vip126_timeline.calendar`, `vip126_zone_plan.status` | không màn nào import; 5 tệp test đọc mã |
| `components/DesktopForecastChart.vue` | 47 / 3.253 | Cấu hình ECharts thứ hai | — | chỉ ForecastPlanner và Vip126RollingForecast |

Tài liệu đã đọc: `docs/CHAM_BUONG_DU_THU.md` (61 dòng), `docs/BUNCH_TAG_CATALOG.md` (28), `docs/FARM_WORKSPACE.md` (99), `docs/FIELD_REPORT.md` (78), `docs/LOTUS_RIBBON_2026W43.md`, `specs/002-cham-soc-thu-hoach-du-thu/spec.md` (311).

### 2. Mẫu hiển thị theo nghề

#### 2.1 Thẻ lô và dòng lô

Có 10 kiểu markup cho "một lô", mỗi kiểu một khối CSS riêng. Không có component thẻ lô dùng chung.

| Kiểu | Tệp:dòng | Markup và class | Màu | Điện thoại |
|---|---|---|---|---|
| Thẻ lô báo cáo ngày | `LotCards.vue:19-30`, CSS 37-52 | `article.lot-card.is-{success,info,warning,neutral,idle}` > `button.lot-card__main`: mã lô và khu, số việc và trạng thái báo cáo, việc được giao, tối đa 4 chấm màu dây kèm số buồng, dòng cách ly | viền trái 4px: `--lotus-success`, `--lotus-primary`, `--lotus-warning` | `.lot-cards--mobile` 1 cột |
| Lô đến hạn trong hộp giao việc | `CareDueList.vue:109-113`, CSS 143-148 | `ul.care-due__lots li.is-late/.is-given` + ô tick | viền trái 3px warning, danger, success | 1 cột |
| Ô chọn lô khi giao phiếu riêng | `WorkAssign.vue:103-106`, CSS 129-132 | `.field-assign__lot` + ô tick, ha và số cây | viền thường | 2 cột |
| Dòng cần thu (lô × màu) | `RibbonBoard.vue:64-69`, CSS 108-113 | `article.ribbon-due.is-held/.is-late` + `.ribbon-swatch` | viền trái warning, danger; đang cách ly thì `opacity:.85` | 1 cột |
| Nguồn buồng của ca | `PackhouseShifts.vue:141-148`, CSS 201-206 | `ul.packhouse__sources li.is-on` + ô tick + 2 ô số | viền `--lotus-primary` khi chọn | — |
| Lô cần kiểm của phiếu giấy | `PaperPhotoReview.vue:62-65`, CSS 86-89 | `article.paper-review__lot` | viền trái warning | 1 cột |
| Truy vết về lô | `PackhouseShifts.vue:177-182`, CSS 208-210 | `.packhouse__trace article` | không | — |
| Dòng dự thu theo lô | `BunchWeeklyForecast.vue:113-117`, `137-139`, CSS 176-182 | `ul.bunch-lines` | không | — |
| Thẻ phiếu giao | `WorkAssign.vue:85-89` | `button.mobile-list-card.field-assign__card` | kiểu PWA | chỉ điện thoại |
| Thẻ chờ nghiệm thu | `WorkInspect.vue:26-31` | `.work-today__card` | không có CSS | — |

Cách ghi tên lô và khu không thống nhất. "Lô A5" ở LotCards, RibbonBoard, CareDueList, PackhouseShifts. "A5" trần ở `WorkAssign.vue:86,104`, `WorkTicket.vue:71`, `WorkInspect.vue:28`, `BunchWeeklyForecast.vue:115,138`. Khu ghi "khu A" (`LotCards.vue:21`), "Khu A" (đa số), "A" (`BunchWeeklyForecast.vue:71`).

#### 2.2 Màu dây

- Nguồn mã màu: `lotus_farm/ribbon_cycle.py:8-21`. Chu kỳ 12 tuần: `DO`, `TRANG`, `TIM`, `CAM`, `DEN`, `XANH_DUONG`, `DO_XANH_LA`, `TRANG_XANH_LA`, `TIM_XANH_LA`, `CAM_XANH_LA`, `DEN_XANH_LA`, `XANH_LA_XANH_DUONG`. Mỗi tuần hai nửa (thứ Hai–Năm, thứ Sáu–Chủ nhật) cùng màu.
- Đổi mã thành màu CSS: `swatch()` ở `frontend/src/lot-entry-model.js:130-142`. Bảng `RIBBON` có 7 màu gốc ghi cứng: `XANH_DUONG #1976d2`, `XANH_LA #2e7d32`, `TRANG #ffffff`, `CAM #f57c00`, `DEN #212121`, `TIM #7b1fa2`, `DO #d32f2f`. Mã hai màu trả `linear-gradient(90deg,A 50%,B 50%)`. Mã lạ trả `transparent`. Chuỗi bắt đầu bằng `#`, `rgb`, `hsl` được trả nguyên.
- Bốn chỗ vẽ chấm màu, bốn khối CSS, ba cỡ:

| Tệp:dòng | Class | Cỡ | Viền |
|---|---|---|---|
| `LotCards.vue:26`, CSS 51 | `.lot-card__colours b` | 10px | `--lotus-border` |
| `LotEntryModal.vue:112`, CSS 203 | `.lot-entry__ribbon i` | 12px | `--lotus-border` |
| `PackhouseShifts.vue:143`, CSS 206 | `.packhouse__swatch` | 12px | `--lotus-border` |
| `RibbonBoard.vue:65,76`, CSS 122 | `.ribbon-swatch` | 14px | `--lotus-border` |

- Cả bốn chỗ đều có tên màu bằng chữ đi kèm và chấm có `aria-hidden`.
- Tên trường khác nhau giữa các API. Mã màu: `code` (`LotCards.vue:26`, `RibbonBoard.vue:76`, `LotEntryModal.vue:112`), `code_colour` (`RibbonBoard.vue:65`), `colour_code` (`PackhouseShifts.vue:143`). Nhãn: `label`, `colour`, `ribbon`, `color_label`, `color_name`.
- Chỗ chỉ có chữ, không có chấm: `ColorTagCatalogApp.vue:31-41` (màn danh mục màu dây), `BunchWeeklyForecast.vue:115,121`, `WorkTicket.vue:105`, `PackhouseShifts.vue:105,178`, `components/ForecastVariance.vue:75`. Phiếu giấy in cũng chỉ ghi chữ, có chủ ý vì in đen trắng (`lotus_farm/templates/print/body/daily_form.html:7`).
- Không có chú giải 12 màu và không có dải chu kỳ màu ở màn nào.

#### 2.3 Nhãn tuần

Không có hàm định dạng tuần dùng chung. `frontend/src/format.js` chỉ có `formatDate`, `formatDateTime`, `formatMonthShort`. Tính tuần ISO phía trình duyệt chỉ có ở `components/ForecastVariance.vue:12`.

| Dạng hiển thị | Tệp:dòng |
|---|---|
| "Đỏ tuần 43 lần 1" | `RibbonBoard.vue:66,76` |
| "Đỏ · tuần 43 · còn 12" | `lot-entry-model.js:88` |
| "Tuần 52 (21/12 – 27/12)", nhãn cột "52" | `BunchWeeklyForecast.vue:36` |
| "Tuần 52 · 21/12 – 27/12" | `BunchWeeklyForecast.vue:53` |
| "Tuần 43/2026" | `ColorTagCatalogApp.vue:23` |
| "Tuần 46: 09/11/2026 – 15/11/2026" | `FieldReports.vue:39` |
| "Cần thu tuần này", "tuần từ dd/mm/yyyy" | `RibbonBoard.vue:61` |
| "11-02" (cắt chuỗi ISO) | `OverviewBoard.vue:23` |
| "02/11" | `components/ReportsWorkspace.vue:100` |

Dữ liệu tuần đến dưới ba dạng: số tuần (`week`, `week_number` + `week_year`), chuỗi `2026-W52` (dự thu, báo cáo), ngày bắt đầu tuần (`w.week`, `operations.week`). Chọn tuần bằng hộp chọn ba mục (`RibbonBoard.vue:26`, `CareDueList.vue:19`) hoặc ô ngày "Tuần có ngày" (`FieldReports.vue:48`).

#### 2.4 Trạng thái

Vùng này không dùng nhãn trạng thái chung. `components/ui/badge` có 4 biến thể (default, secondary, destructive, outline) nhưng không tệp nào trong `frontend/src` import. Nhãn dạng viên duy nhất đang dùng là `.land-gap` (`land.css:48`, `LandBlockDetail.vue:81`).

| Nghĩa | Giá trị → nhãn | Cách thể hiện | Tệp:dòng |
|---|---|---|---|
| Báo cáo ngày | Draft "Chưa gửi", Sent "Đã gửi, chờ xác nhận", Confirmed "Đã xác nhận", Reopened "Mở lại để sửa" | chữ + viền trái theo `stateTone` | `lot-entry-model.js:7-8`, `LotCards.vue:19`, `LotToday.vue:107`, `CrewStatus.vue:20,29` |
| Vòng chăm sóc | overdue "Quá hạn N ngày", due "Đến hạn dd/mm", later "Hạn dd/mm", đã giao | chữ + viền trái | `CareDueList.vue:30,85-89,109-113` |
| Tuổi buồng theo màu | waiting "Đang nuôi", due "Đến tuổi thu", overdue "Quá tuổi thu", done "Đã thu hết" | chữ + viền trái; done thêm `opacity:.8` | `RibbonBoard.vue:27,75-80`, CSS 114-118 |
| Phiếu giao | 12 trạng thái | chữ trong cột bảng và trong thẻ | `field-work-model.js:8-9`, `WorkAssign.vue:37,87` |
| Ca xưởng | đang mở, đã đóng; 4 câu về phiếu nhập kho | viền trái warning hoặc success + chữ | `PackhouseShifts.vue:30,123` |
| Vòng chăm sóc (phiên bản) | đang áp dụng, đã duyệt, chờ duyệt | viền + chữ | `CareCycleSettings.vue:75-80,87-89` |
| Thẻ báo cáo | tone good, warn, bad | viền trên 4px | `ReportCards.vue:20`, CSS 39-42 |
| Độ tin cậy dự thu | "Tin cậy cao", "khá", "thấp"; "quá hạn" | chữ | `BunchWeeklyForecast.vue:23,115` |
| Tình trạng lô trên bản đồ | held, late, harvest, ok | màu tô | `map-land.js:15` |

Cách ly thuốc có 7 chỗ hiển thị, 4 câu chữ khác nhau, không chỗ nào ghi số ngày còn lại:

- `LotCards.vue:28`: "Cách ly thuốc đến {ngày}".
- `LotEntryModal.vue:113`: "Đang cách ly thuốc đến {ngày}: chưa được thu hoạch".
- `RibbonBoard.vue:68`: "Đang cách ly đến {ngày}: chưa được thu"; cột bảng "Cách ly đến" (dòng 42).
- `WorkTicket.vue:74`: "Lô đang cách ly thu hoạch đến {ngày}".
- `WorkAssign.vue:105`: " · cách ly", không có ngày.
- `FieldReportApp.vue:138`: cột "Cách ly thu hoạch đến".
- `map-land.js:15`: "Đang cách ly thuốc", tô `--lotus-danger`.

#### 2.5 Bản đồ

- Thư viện: `leaflet` 1.9.4, `polygon-clipping` 0.15.7 (hợp các lô thành ranh khu), `polylabel` 2.1.0 (điểm đặt nhãn khu) (`frontend/package.json:23-26`). Màu truyền vào Leaflet là chuỗi `var(--lotus-…)` (`CareMap.vue:33,40,41,56,57,62,69`), nên bản đồ phụ thuộc renderer SVG.
- Khởi tạo: `L.map(el,{minZoom:12,maxZoom:22,zoomControl:false}).setView([11.602,106.79],15)` (`CareMap.vue:82`). Nút phóng to, thu nhỏ ở góc dưới phải, tiêu đề tiếng Việt (dòng 83).
- Nền: Esri World Imagery, `maxNativeZoom:19`, ghi công "Ảnh vệ tinh © Esri" (dòng 87). Ảnh flycam `https://map.gpcds.site/v2/tiles/farm222/{z}/{x}/{y}.webp?v=20261016-116292` cho vườn `LOTUS-222` và `LOTUS-180` (dòng 79), căn bằng ma trận affine ở `map-imagery-config.js:21-57` qua `alignedTiles` (`map-imagery.js:2-20`).
- Lớp vẽ:

| Lớp | Kiểu | Dòng |
|---|---|---|
| Ranh ngoài vườn | `--lotus-neutral-0`, nét 5 | 62 |
| Lô, chế độ khu | viền và nền màu khu, nét 1,5, `fillOpacity:.12` | 56 |
| Lô, chế độ khác | viền `--lotus-neutral-950` nét 1, nền theo `fillFor`, `fillOpacity:.72` | 57 |
| Quầng khu | `--lotus-neutral-950`, nét 7, mờ .65 | 69 |
| Ranh khu | màu khu, nét 4; có ở mọi chế độ | 70 |
| Ranh chưa khép kín | nét đứt `6 5`, điểm tròn bán kính 6 | 64 |
| Nét đo vẽ | `--lotus-primary`, nét 3, `fillOpacity:.16` | 33, 40 |

- Bảng màu (`map-land.js:9-15`, `lotus-tokens.css:34-35`):
  - Khu: `--lotus-map-zone-a…f` = `#f46963`, `#43d99a`, `#ffd166`, `#65baff`, `#c89cff`, `#ff9d57`. Không đổi theo chế độ tối.
  - Giống: dùng lại 6 màu khu theo thứ tự danh sách giống.
  - Mật độ: 5 bậc `--lotus-success-100/300/500/700/900`, ngưỡng 1.500, 1.800, 2.100, 2.400 cây/ha.
  - Tháng trổ: 4 bậc `--lotus-info-200/400/600/800`.
  - Tình trạng: held `--lotus-danger`, late `--lotus-warning`, harvest `--lotus-success-500`, ok `--lotus-info-200`.
  - Thiếu dữ liệu: `--lotus-neutral-300`.
- Nhãn: tooltip `.care-map-label` "A5 · 1,2 ha", thêm mật độ, giống hoặc tháng trổ theo chế độ; cố định khi zoom từ 16,5 (`CareMap.vue:54,63,89`). Nhãn khu `.care-map-zone` "Khu A": nền trắng, viền 3px màu khu, chữ 14px (`care-map.css:14`).
- Chú giải: nằm trong khung `.care-map-status` góc dưới trái. Chế độ khu liệt kê khu đang hiện; chế độ khác lấy từ `legendFor` (`CareMap.vue:111`). Báo cáo Tuần vẽ chú giải riêng bên ngoài bản đồ (`FieldReports.vue:57`).
- Popup: không có (`bindPopup` 0 lần). Bấm lô phát sự kiện `open(block)`.
- Công cụ: Toàn vườn, Đo đường, Đo vùng, Xoá nét chọn, GeoJSON, Xoá tất cả (dòng 101-108). Nét vẽ lưu `localStorage` khóa `lotus-map-sketch|user|farm`, tối đa 500 nét (dòng 26-28).
- Biến thể: `compact` ẩn công cụ và khung trạng thái. Màn bản đồ toàn trang dùng `.app-shell.map-workspace>main` cao `100dvh` (`care-map.css:4`). Từ 900px trở xuống thanh công cụ nằm ngang và cuộn.
- Không có: thước tỉ lệ, đổi lớp nền, định vị người dùng, tìm lô, popup, danh sách lô thay thế cho bàn phím.

#### 2.6 Biểu đồ

**`LotusChart.vue` (ECharts `^6.1.0`)**

- Nạp theo mô-đun: `BarChart`, `LineChart`, `PieChart`, `GridComponent`, `TooltipComponent`, `LegendComponent`, `CanvasRenderer` (dòng 3-10).
- Không đăng ký theme. Mỗi lần vẽ đọc token bằng `getComputedStyle` (dòng 46-48): chữ trục `--lotus-muted`, đường trục và lưới `--lotus-border` (lưới nét đứt `[3,3]`), nền tooltip và viền cột `--lotus-surface`, màu chuỗi `--lotus-chart-1…5` và `--lotus-chart-other`. Vẽ lại khi đổi sáng tối (dòng 74).
- Màu gán theo thứ tự chuỗi (dòng 51). Tối đa 3 chuỗi (`maxSeries`), chuỗi thừa bị bỏ (dòng 30).
- Cỡ chữ ghi số: trục 11, chú giải 12, tooltip 12, nhãn giá trị 11. Không đặt `fontFamily`.
- Tooltip: `trigger:'axis'`; con trỏ `line` cho đường, `shadow` cho cột; giá trị kèm đơn vị (dòng 64).
- Cột: rộng tối đa 28 (ngang 18), bo 4, viền 1px màu nền. Đường: nét 2, điểm tròn 8, hiện điểm khi không quá 14 điểm. `animationDuration:200`.
- Nút "Xem bảng số liệu" đổi sang `DataTable`; không có canvas thì chỉ hiện bảng (dòng 41, 79, 84). Có `role="img"` và `aria-label` gồm tiêu đề và tổng từng chuỗi (dòng 83).
- Kiểu đang dùng trong 23 chỗ gọi: cột đứng 17, cột ngang 4, đường 2. Số chuỗi: 15 chỗ 1 chuỗi, 6 chỗ 2 chuỗi, 2 chỗ 3 chuỗi.
- Không nơi nào gọi: `kind="area"`, `kind="donut"`, `stacked`, `clickable`, `showValues`, `pointColors`, `maxSeries`, slot `controls`.

**`BunchChart.vue` (tự dựng)**

- Cột chồng 3 phần theo độ chắc: `cut`, `inject`, `est`. Thang một tông xanh dương khai cục bộ: `--bunch-cut:var(--lotus-info-800)`, `--bunch-inject:var(--lotus-info-500)`, `--bunch-est:var(--lotus-info-300)`; chế độ tối đổi sang 200, 400, 500 (dòng 78-79).
- Cao cố định 220px (dòng 8). 3 vạch trục (0, 50%, 100%) theo `niceMax` (dòng 10-16). Chỉ ghi số trên cột cao nhất và cột cao nhất toàn số thật (dòng 19-25).
- Mỗi cột là vùng bấm, có `aria-label` đọc đủ các phần; rê chuột hoặc focus hiện `.bunch-chart__tip`; bảng số nằm trong `<details>` (dòng 52, 60, 70).

**`DesktopForecastChart.vue`**: cột "Dự thu buồng" + đường "Thành phẩm" + đường đứt "Đã thu thực tế"; màu `--lotus-primary`, `--lotus-success`, `--lotus-info` kèm 5 mã hex dự phòng (dòng 20-25); đăng ký `DataZoomComponent` nhưng không dùng. Chỉ được gọi từ hai component không còn màn nào dùng.

**Thanh vẽ bằng CSS**: `.bunch-zones__bar` theo khu (`BunchWeeklyForecast.vue:104`), `.calendar-track` theo tháng (`ForecastPlanner.vue:79`).

#### 2.7 Lịch, lịch trình, dòng thời gian

Không có component lịch tuần, dải tuần hay dòng thời gian trong vùng này. Các chỗ mang nghĩa thời gian đều là danh sách chữ:

- Lịch màu dây: bảng `DataTable` 11 cột (`ColorTagCatalogApp.vue:30-42,109`).
- Phiên bản vòng chăm sóc: `ul.care-cycles__versions` (`CareCycleSettings.vue:86-96`).
- Báo cáo theo ngày của phiếu: `ul.work-ticket__entries` (`WorkTicket.vue:102-110`).
- Truy vết ca: thu hoạch và các lần phun trong 90 ngày, dạng dòng chữ (`PackhouseShifts.vue:177-182`).
- Lịch sử thay đổi của lô: `ol.land-history` (`LandBlockDetail.vue:158`).
- Nhịp cắt bắp theo tuần: `ul.bunch-lines` trong hộp (`BunchWeeklyForecast.vue:144-146`).
- Thẻ tuần so dự thu với thực tế: `button.bunch-week` (`components/ForecastVariance.vue:60-68`; CSS nằm ở `BunchWeeklyForecast.vue:183-188`).
- Trong mã không còn màn nào dùng: lưới 12 tháng `.calendar-months` (`ForecastPlanner.vue:76-83`), dải 20% – 60% – 20% (`Vip126RollingForecast.vue:101-105`).

Ngoài vùng này, `components/LotusSignatureTimeline.vue` là dòng thời gian duy nhất của ứng dụng.

#### 2.8 Ô số liệu và dải tổng hợp

Năm cách đang dùng, năm cỡ số:

| Cách | Định nghĩa | Cỡ số | Nơi dùng |
|---|---|---|---|
| `.land-stats` | `land.css:10-16` | 1.45rem | `FarmLandApp.vue:142-147`, `LandBlockDetail.vue:85-90`, `BunchWeeklyForecast.vue:78-82`, `BlockForecastApp.vue:100-105` |
| `.lotus-stat-row` / `.lotus-stat` | `workspace-experience.css:259-262` | 24px | `OverviewBoard.vue:18`, `components/ReportsWorkspace.vue` |
| `.ribbon-board__totals` | `RibbonBoard.vue:99-104` | 16px | `RibbonBoard.vue:56-60` |
| `.report-card` | `ReportCards.vue:39-48` | 20px | báo cáo Sáng nay, Tuần, Tháng |
| `WorkspaceSummaryStrip` (`dl`) | `workspace-experience.css:113-116` | 18px | `WorkTicket.vue:77` |

Thêm bốn cách trong mã không còn màn nào dùng: `DesktopMetricCard` (24px, 19px), `.forecast-metric` (22px, `forecast-workspace.css:8-13`), `.vip126-timeline__metrics` (21px), `.farm-kpis` (28px, `farm-work.css:5`). Các khối chữ số khác: `dl.land-dl`, `dl.bunch-trace__facts`, `.lot-entry__facts`, `.bunch-pace`.

Không ô nào có xu hướng hay so với kỳ trước. Đơn vị nằm trong chuỗi số (`land-stats`) hoặc ở dòng nhỏ bên dưới (`lotus-stat`).

#### 2.9 Thanh tiến độ

Không có `<progress>`, `<meter>`, `role="progressbar"` hay `role="meter"` trong `frontend/src` (grep 0 kết quả). Tiến độ ghi bằng chữ: "Cắt 100 · bao 80 · thu 16 / Còn 80" (`RibbonBoard.vue:78-79`), "3 lô quá hạn · 5 lô đến hạn / 2 lô đã giao · 6 lô chưa giao" (`CareDueList.vue:87-88`), tỷ lệ đóng gói (`PackhouseShifts.vue:125`), "N ngày · khối lượng" (`WorkAssign.vue:40`). Class `.forecast-meter*` có CSS (`forecast-workspace.css:34-37`) nhưng không template nào dùng.

#### 2.10 Ảnh và phiếu giấy

- `PaperPhotoReview.vue`: thanh trạng thái bằng chữ (chưa in, đã in lúc, đã đọc ảnh lúc, còn N lô chưa kiểm) và hai nút (dòng 46-56). Thân hai cột: ảnh phiếu trong nút `cursor:zoom-in`, cao tối đa 420px; danh sách lô cần kiểm kèm cờ của máy đọc (dòng 59-68). Bấm ảnh mở hộp 1.100px chỉ có một thẻ `<img>`, không phóng, kéo hay xoay (dòng 69-71). Trên điện thoại nút chụp dùng `capture="environment"` (dòng 53).
- Dòng do máy đọc trong hộp nhập lô: câu "Máy đọc từ ảnh, cần kiểm: …" màu `--lotus-warning` (`LotEntryModal.vue:131`).
- Ảnh nghiệm thu: ô chọn tệp (`WorkTicket.vue:94`) và liên kết chữ "Xem ảnh" mở tab mới (dòng 115), không có ảnh thu nhỏ.

#### 2.11 Bản in và xuất tệp

- `frontend/src` không có `@media print` và không gọi `window.print` (grep 0 kết quả).
- Phiếu báo cáo ngày in từ máy chủ: `PaperPhotoReview.vue:19-28` mở URL do `lot_paper_form.form_url` trả về; trang dựng bằng `lotus_farm/templates/print/body/daily_form.html` và `lotus_farm/templates/print/lotus_print.css` (giấy ngang, mỗi lô một hàng, mỗi việc một cột có mã C1, C2…, ô tô đậm là việc đã giao, màu dây ghi chữ). Bộ in dùng giá trị màu ghi thẳng vì wkhtmltopdf không có biến CSS.
- Xuất tệp: sổ cắt bắp Excel (`RibbonBoard.vue:32,52`), mẫu Excel lô (`FarmLandApp.vue:100`), bảng đang hiện (`FarmLandApp.vue:101-106` và `export-title` của `DataTable`), nét đo GeoJSON (`CareMap.vue:52`).

#### 2.12 Điện thoại và máy tính

- Cùng component cho hai nơi, khác nhau bằng prop `mobile` (15 component có prop này). Prop làm ba việc: `LotusField` đổi sang ô nhập Vant; `FormGrid` còn 1 cột; lưới thẻ còn 1 cột qua class `--mobile` (11 class).
- Nút vẫn là `UiButton` của máy tính: 42 thẻ trong `components/field`, 17 thẻ `size="sm"`. Không component nào trong `components/field` và `components/report` dùng `LotusMobile*`.
- Hộp nhập trên điện thoại vẫn là `ModalForm` → `WorkspaceModal` (`<dialog>`); `work-mobile.css:64-71` khai lại kiểu hộp vì CSS máy tính không được nạp ở `/work`.
- Trên điện thoại có: LotToday, CrewStatus, RibbonBoard (`compact`), CareDueList, WorkAssign, WorkInspect, MyPay (`WorkMobile.vue:89-108`). Không có: Báo cáo, Xưởng, Vòng chăm sóc, bản đồ, dự thu.
- Số đang nhập dở được giữ ở `localStorage` khóa `lotus-lot-draft:{báo cáo}:{lô}` (`lot-entry-model.js:115-127`).

## Ràng buộc phải giữ

### Quy tắc đã chốt với chủ vườn

- Lô là đơn vị nhỏ nhất, thửa không tham gia (`specs/002-cham-soc-thu-hoach-du-thu/spec.md:187`, FR-002).
- Nhập liệu và xem số bằng thẻ và hộp, không trải bảng phẳng (spec 002 dòng 193 FR-005 và dòng 303).
- Lịch 12 màu dây theo tuần, hai lần cắt mỗi tuần. Cùng một màu ở hai chu kỳ là hai đợt riêng (FR-016), nên nhãn màu dây luôn phải kèm tuần.
- Số thật và số ước tính của dự thu đứng riêng, không có một tổng gộp phía trên (`frontend/tests/bunch-weekly.mount.test.js:31-37`). Toàn hệ thống chỉ có một con số dự thu (FR-025).
- Lô đang cách ly không ghi được thu hoạch (FR-019). Số thu không vượt số còn trên cây (FR-020).
- Không tạo số liệu giả, không tự suy số; thiếu dữ liệu thì cảnh báo (`.specify/memory/constitution.md:8`).
- Màu chính duy nhất là Đỏ Lotus `#c43224`; mọi màu, chữ, khoảng cách, bo góc, bóng lấy từ `frontend/src/lotus-tokens.css` (`AGENTS.md:12`).
- Không thêm tiêu đề lớn, mô tả trang trí phía trên bảng (`AGENTS.md:3-6`). Icon dùng `LotusIcon`, không dùng ký tự (`AGENTS.md:18`).
- Điện thoại dùng Vue 3, Vant 4 và các wrapper `LotusMobile*`; không tràn ngang ở 320px (`AGENTS.md:25-28`).
- Chuẩn hóa giao diện không đổi API, phân quyền, trạng thái chứng từ, chống gửi trùng (`AGENTS.md:29`).
- Không thêm thư viện giao diện mới (`specs/004-bo-giao-dien-agritech/spec.md`, mục Clarifications).

### Test đang khóa class, chữ và hành vi

Các test mount dùng `frontend/tests/support/mount.mjs` (happy-dom).

| Test (`frontend/tests/`) | Phụ thuộc vào |
|---|---|
| `care-map.mount.test.js` | `.leaflet-container`, `.leaflet-interactive`, `.care-map-filters`, `.care-map-status`; chữ "1 lô chăm sóc", "chưa duyệt", "Ảnh flycam Lotus Farm 222", "N điểm", "N nét vẽ"; tên nút "Đo đường", "Hoàn tất", "Lùi điểm", "Xoá nét chọn"; khóa `lotus-map-sketch\|user\|farm`; không được có chữ "thửa", "tưới" |
| `ribbon-board.mount.test.js` | `.ribbon-board__totals`, `.ribbon-due`, `.ribbon-due.is-held`, `.ribbon-card` (thẻ `strong` đầu là tên màu), `.ribbon-board__tools`; chuỗi "Lô A5 · Đỏ tuần 43 lần 1", "Đang cách ly đến dd/mm/yyyy: chưa được thu", "Xem từng màu dây" |
| `lot-entry.mount.test.js` | `.lot-card`, `.lot-card__main`, `dialog.lot-entry-modal[open]`, `.lot-entry__line`, `.lot-entry__line.is-error`, `.lot-today__ask`; tên nút "Gửi báo cáo", "Đã kiểm, lưu lô này" |
| `care-due-list.mount.test.js` | `.care-due__card`, `.care-due__lots li` (class `is-late`), `.care-due__zone header`, `.care-due__tools select` |
| `care-cycle-settings.mount.test.js` | `.care-cycles__card`, `.care-cycles__versions li` |
| `packhouse-shifts.mount.test.js` | `.packhouse__card`, `.packhouse__sources`, `input[placeholder="VD: S1"]` |
| `paper-photo-review.mount.test.js` | `.paper-review__lot`, `.paper-review__photo img`, `.paper-review__notes` |
| `farm-land.mount.test.js` | `.land-zone`, `.land-gaps`, `.land-table`, `.land-form`; chuỗi "3 lô · 6 thửa", "Thửa trong lô" |
| `bunch-weekly.mount.test.js` | `.land-stats>div` (đúng 3 ô), `.bunch-col`, `button.bunch-col`, `.bunch-col__cap` (chỉ 1), `.bunch-col__name`, `.bunch-chart__tip`, `details.bunch-chart__table`, `.bunch-pace`, `.bunch-zones`, `.bunch-lines button`, `[aria-label="Lọc theo khu"]` |
| `reports-workspace.mount.test.js` | `.lotus-stat`, `.lotus-chart-head h3`, `.lotus-chart-head button` ("Xem bảng số liệu"), `.lotus-chart-canvas`, `.lotus-chart-table`, `.lotus-chart-empty`, `.report-filters label` |
| `lot-entry-model.test.js:84-89` | `swatch('CAM')==='#f57c00'`, `swatch('DO_XANH_LA')==='linear-gradient(90deg,#d32f2f 50%,#2e7d32 50%)'`, mã lạ trả `transparent` |
| `map-land.test.js` | tên token trong kết quả `fillFor`: `success-100…900`, `info-200…800`, `neutral-300`; `legendFor('zone')===null` |
| `map-zones.test.js` | `zoneColor('B')==='var(--lotus-map-zone-b)'`, 6 màu khác nhau |
| `design-tokens.test.js` | không mã hex đục trong CSS và `<style>` của `src/*.vue`, `src/components/*.vue`; mọi `var(--lotus-*)` không có dự phòng phải được khai báo; `font-family` chỉ từ token |
| `warehouse-ledger-alignment.test.js` | chuỗi `.land-filter-actions{display:flex;flex-wrap:wrap;align-items:center` trong `land.css` và 4 chuỗi trong `FarmLandApp.vue` |
| `fixed-select-stt.test.js`, `column-visibility.test.js` | các chuỗi chọn dòng và cột trong `FarmLandApp.vue` |
| `ui-stack.test.js:43-50` | `FieldReportApp.vue` import `{Button as UiButton}` và đóng mở thẻ cân bằng |
| `desktop-design-system.test.js:31-41`, `forecast-calendar.test.js`, `forecast-sample.test.js`, 5 tệp `vip126-*.test.js` | chuỗi chữ trong `ForecastPlanner.vue`, `DesktopForecastChart.vue`, `Vip126RollingForecast.vue`; đồng thời khẳng định `App.vue` không dùng hai màn này |

### Giao diện công khai của component

- `CareMap`: props `collection`, `farm`, `user`, `colorBy` (`zone`, `variety`, `density`, `flowering`, `status`), `varieties`, `compact`; emit `open(block)`, `reset`; slot `filters`.
- `LotusChart`: props `title`, `kind`, `categories`, `series`, `unit`, `decimals`, `empty`, `height`; emit `select`. Được gọi ngoài vùng này ở `FinanceApp.vue:605`.
- `BunchChart`: props `items`, `format`, `unit`, `clickable`, `label`, `series`; emit `select`.
- `RibbonBoard` (`farm`, `zones`, `mobile`, `compact`), `LotToday` (`farm`, `crew`, `setup`, `mobile`, `initialTeam`, `v-model:date`), `CareDueList` (emit `assigned`), `CrewStatus` (emit `pick`), `PaperPhotoReview` (emit `changed`, `open-lot`), `WorkTicket` (expose `reload`), `LandBlockDetail` (emit `back`, `changed`, `notice`, `error`).
- Class `land-*` được dùng ngoài Vườn & lô: `FinanceApp.vue` 23 lần, `BlockForecastApp.vue` 16, `components/finance/FinanceGuide.vue` 14, `components/finance/FinancePlanning.vue` 8, `BunchWeeklyForecast.vue` 5, `components/ForecastProfiles.vue` 4, `components/ForecastVariance.vue` 3. `frontend/src/finance.css:1` ghi "builds on land.css".
- Khóa lưu bố cục cột của `DataTable` (đổi tên sẽ mất bố cục người dùng đã lưu): `ribbon-board-lots`, `care-due-matrix`, `packhouse-split`, `field-work-tickets`, `field-work-payable`, `field-crews`, `field-teams`, `field-blocks`, `field-rates`, `field-work-modes`, `lotus-farm-land`, `lot-*` (10 khóa), `bunch-chart-table`, `chart-data-table`, `block-forecast-months`, `block-forecast-rows`, `forecast-observed-milestones`, `bunch-color-periods`, `field-report-{tab}-{thẻ}`.
- Khóa `localStorage`: `lotus-lot-draft:{báo cáo}:{lô}` (FR-011 yêu cầu không mất số nhập dở), `lotus-map-sketch|{user}|{farm}`.
- Bố cục phiếu giấy do `lot_paper_form.form_url` cố định để ảnh đọc lại khớp cột (`lotus_farm/www/lotus_daily_form.py:1-2`). Bộ giao diện mới không đổi cột và mã việc trên phiếu.

## Điểm yếu

### A. Lỗi và kiểu bị thiếu

1. `FarmLandApp.vue:198` truyền `:columns="landPreviewColumns"` nhưng không có khai báo `landPreviewColumns` nào trong `frontend/src` (grep chỉ ra đúng 1 lần xuất hiện). Bảng xem trước nhập Excel nhận `columns=undefined`; chưa kiểm khi chạy. Cùng tệp có `changeText` (dòng 116), `sortBy` (55), `togglePick` (56), `columnId` (17) khai báo mà không dùng.
2. `WorkInspect.vue:26-27` dùng `work-today__cards`, `work-today__card`, `work-today__main`, `work-today--mobile`; không có CSS nào cho các class này trong `frontend/src`. Thẻ chờ nghiệm thu là nút trần.
3. Class không có CSS: `.field-report__notice` (`LotToday.vue:103`, `WorkAssign.vue:72`, `WorkTicket.vue:68`), `.field-report__warning` (`WorkAssign.vue:73`), `.land-text-link` (`LandBlockDetail.vue:58`).
4. `.lotus-form-note` chỉ có một luật CSS, đặt ở `components/stock/StockDocumentForm.vue:224`, trong khi `components/field` dùng class này ở 36 dòng. StockDocumentForm chỉ được import bởi `StockApp.vue:20` và `components/ProcurementWorkspace.vue:14`, cả hai nạp trễ (`App.vue:53,57`), và không nằm trong đồ thị import của `/work`. Kiểu của ghi chú vì vậy phụ thuộc người dùng đã mở Kho hoặc Mua hàng trước đó; trên điện thoại không có. Phân tích import tĩnh, chưa kiểm trên bản build.
5. `/work` chỉ nạp `vant`, `lotus-fonts.css`, `lotus-tokens.css`, `mobile-work-legacy.css`, `work-mobile.css`, `shadcn.css`, `mobile-ui.css` (`work-mobile-main.js:1-13`). `.stock-success` (`CareDueList.vue:81`) và `.workspace-summary-strip` (`WorkTicket.vue:77`) không có luật nào trong các tệp này.
6. Bản đồ thu gọn ở báo cáo Tuần: luật `.care-map--compact .care-map-filters{display:none}` và `.land-card--map .care-map-canvas{height:100%}` nằm ở `land.css:99-100`, nhưng FieldReportApp không import `land.css`. Dải lọc rỗng và chiều cao `calc(100dvh - 105px)` (`care-map.css:1`) có hay không tùy màn đã mở trước; chưa kiểm.
7. `FieldReports.vue:58` không nghe sự kiện `open` của CareMap. Bấm lô trên bản đồ Tuần không mở gì. Spec 002, User Story 5, kịch bản 3 yêu cầu mở hộp sổ lô; chưa có component sổ lô.
8. "Hôm nay" lấy từ ba nguồn. Máy chủ: `session.today` (`FieldReportApp.vue:35`). Đồng hồ máy, giờ địa phương: `RibbonBoard.vue:25`, `CareDueList.vue:17-18`, `PackhouseShifts.vue:16-17`, `FieldReports.vue:16-17`, `CareCycleSettings.vue:38`. Đồng hồ máy, giờ UTC: `MyPay.vue:9`, `LandBlockDetail.vue:24-25`, `ColorTagCatalogApp.vue:19`, `map-land.js:30`. Trước 7 giờ sáng giờ Việt Nam ngày UTC là hôm trước. `CareMap.vue:56-57` không truyền `today` cho `fillFor` nên chế độ tô theo tháng trổ dùng ngày UTC.

### B. Màu và nghĩa

9. Tông "info" là đỏ thương hiệu ở ba chỗ (`LotCards.vue:42`, `LotToday.vue:151`, `CrewStatus.vue:48`) và là xanh `--lotus-info` ở chỗ khác (`RibbonBoard.vue:117`, `CareDueList.vue:133`, `ReportCards.vue:39`). Trong CrewStatus, "Đã gửi, chờ xác nhận" (`#c43224`) đứng cạnh "Chưa có báo cáo" (`--lotus-danger` `#b42318`): tương phản 1,20:1, cùng sắc đỏ.
10. "Chưa gửi" (neutral) và "Mở lại để sửa" (warning) dùng chung một màu viền (`LotCards.vue:43`, `LotToday.vue:152`, `CrewStatus.vue:49`).
11. Màu dây ghi cứng trong JS (`lot-entry-model.js:130`), ngoài `lotus-tokens.css`. `frontend/tests/design-tokens.test.js:8-9,40-53` chỉ quét CSS và khối `<style>` của `src/*.vue` và `src/components/*.vue`; không quét JS và không quét `components/field`, `components/land`, `components/report`.
12. Chấm Trắng trên nền sáng: 1,00:1; viền chấm `--lotus-border` trên nền trắng: 1,26:1. Chấm Đen trên nền tối `#20262f`: 1,06:1; viền chấm ở chế độ tối: 1,48:1. Chấm Tím trên nền tối: 1,86:1. Ngưỡng WCAG 1.4.11 cho đối tượng đồ họa là 3:1.
13. Hai nửa của dây hai màu gần bằng nhau về độ sáng: Đỏ – Xanh lá 1,03:1; Xanh lá – Xanh dương 1,11:1; Tím – Xanh lá 1,60:1. Chấm 10–14px không có vạch ngăn giữa hai nửa. Người mù màu đỏ–lục khó tách "Đỏ" với "Đỏ – Xanh lá" nếu không đọc chữ.
14. Thang tình trạng lô trên bản đồ (`map-land.js:15`) có ba màu gần nhau về độ sáng: late `#a86b0d` với harvest `#2a9862` 1,21:1; held `#b42318` với late 1,49:1; held với harvest 1,81:1. Chúng chỉ khác sắc đỏ, hổ phách, lục và được tô 72% trên ảnh vệ tinh. Nhãn lô ở chế độ này không ghi tình trạng (`CareMap.vue:54`), nên tình trạng chỉ thể hiện bằng màu.
15. Màu khu dùng lại cho giống (`map-land.js:13`) trong khi ranh khu vẫn vẽ ở mọi chế độ (`CareMap.vue:15,70`): một màu mang hai nghĩa trên cùng bản đồ. Quá 6 giống thì lặp màu (`map-land.js:28`). Khu ngoài A–F: `zoneColor` trả màu khu A (`map-zones.js:3`, `map-land.js:6`), còn `FarmLandApp.vue:150` tự ghép tên biến. `zoneColor` và danh sách khu được viết hai lần.
16. Màu khu đặt trên nền trắng (thẻ khu `FarmLandApp.vue:150` + `land.css:18`; viền nhãn khu `care-map.css:14`): khu C `#ffd166` 1,44:1; khu B 1,81:1; khu F 2,06:1; khu D 2,10:1; khu E 2,17:1; khu A 2,98:1.
17. Chữ cảnh báo 12px dùng `--lotus-warning` (`#a86b0d`): 4,40:1 trên nền trắng, dưới mức 4,5:1 (`LotEntryModal.vue:205,214`, `CareCycleSettings.vue:128`, `PaperPhotoReview.vue:89`, `CrewStatus.vue:51`, `BunchWeeklyForecast.vue:167`). `land.css:16,48,75` dùng `--lotus-warning-700` (6,30:1) cho cùng mục đích.
18. Trạng thái thể hiện bằng độ mờ: `.ribbon-due.is-held{opacity:.85}` (`RibbonBoard.vue:110`), `.ribbon-card.is-done{opacity:.8}` (dòng 118), `.care-due__lots li.is-given{opacity:.85}` (`CareDueList.vue:147`). Chữ phụ 12px còn 3,91:1 và 3,52:1. Dòng lô đang cách ly, là dòng cần chú ý, lại bị làm mờ.
19. `forecast-calendar.css` và `forecast-workspace.css`: 11 chỗ `background:white` hoặc `#fff`, 69 lần gọi thẳng `--lotus-neutral-N`, 0 luật `.dark`. Hai tệp này không theo chế độ tối.

### C. Trùng lặp

20. Thẻ viền màu trạng thái: 12 selector ở 10 tệp (`.care-cycles__card`, `.care-due__card`, `.care-due__lots li`, `.crew-status__team`, `.lot-card`, `.lot-today__bar`, `.packhouse__card`, `.paper-review__lot`, `.ribbon-due`, `.ribbon-card`, `.report-card`, `.land-zone`). Lưới thẻ `repeat(auto-fill,minmax(Npx,1fr))` viết 8 lần với N = 150, 220, 220, 240, 240, 250, 260, 280.
21. Ô số liệu: 5 cách đang dùng và 4 cách trong mã không còn dùng; cỡ số 16, 18, 20, 23,2 (1.45rem), 24px (mục 2.8).
22. Tab và nút phân đoạn: 6 cách đang dùng. `WorkspaceTabs`; `nav.workspace-tabs` với nút trần (`BlockForecastApp.vue:90-96`, `LandBlockDetail.vue:91`); `.field-reports__tabs` (`FieldReports.vue:44-46`); `.land-farms` và `.land-views` (`FarmLandApp.vue:131-136`); `.bunch-chips` (`BunchWeeklyForecast.vue:69-75`); `.farm-config-tabs` (`FarmWorkApp.vue:126`). Chỉ `WorkspaceTabs` có điều hướng bằng phím mũi tên.
23. Hàm định dạng viết lại tại chỗ. Ngày: `vnDate` (`FarmLandApp.vue:34`, `LandBlockDetail.vue:29`), `dateFmt` (`BlockForecastApp.vue:21`), `dm` và `dmy` (`BunchWeeklyForecast.vue:13-14`), `dm` (`Vip126RollingForecast.vue:43`), `date` (`ZonePlantingSchedule.vue:22`). `iso()` viết 3 lần (`CareDueList.vue:17`, `PackhouseShifts.vue:16`, `FieldReports.vue:16`). Số: `num` (3 chỗ), `fmt`, `n`, `number` (2 chỗ), `ton` (2 chỗ), `integer`, `bunches`. `amountText` và `money` giống hệt nhau ở `lot-entry-model.js:144-145` và `field-work-model.js:13-14`.
24. Nhãn công đoạn có 4 bảng khác chữ: `lot-entry-model.js:4` (`Care` là "Tỉa"), `LandBlockDetail.vue:31` (`Care` là "Chăm sóc buồng"), `BunchWeeklyForecast.vue:21`, `Vip126RollingForecast.vue:44`. Nhóm `Protection` là "Phun bón, sâu bệnh" (`lot-entry-model.js:6`) và "BVTV / phân bón" (`field-work-model.js:4`). Nửa tuần cắt bắp gọi là "lần" (`RibbonBoard.vue:66`) và "Đợt 1 / 2" (`ColorTagCatalogApp.vue:33`), trong khi spec 002 dùng "đợt màu" cho màu + tuần.
25. Ô màu chú giải: 3 cách (`.care-map-legend i` ở `care-map.css:17`, `.field-reports__legend i` ở `FieldReports.vue:74`, `.bunch-chart__key` ở `BunchChart.vue:85`) cộng 4 chấm màu dây.
26. Hai cấu hình ECharts và một biểu đồ tự dựng. Màu gán theo thứ tự chuỗi nên cùng một đại lượng có màu khác nhau: "Thành phẩm" là `--lotus-chart-2` (xanh dương) ở `components/ReportsWorkspace.vue:102` và là xanh lục ở `DesktopForecastChart.vue:25,33`. Nhãn trục cùng dữ liệu tuần là `MM-DD` ở `OverviewBoard.vue:22-23` và `dd/mm` ở `components/ReportsWorkspace.vue:84,100`.

### D. Mã không còn dùng

27. Không màn nào import: `components/PlotMap.vue` (CSS `.plot-map` ở `frontend/src/style.css:8`), `frontend/src/field-todo.css`, `ForecastWorkspace.vue`, `ForecastPlanner.vue`, `Vip126RollingForecast.vue`, `ZonePlantingSchedule.vue`, `DesktopForecastChart.vue`, `forecast-sample.js`, `forecast-calendar.css`, `forecast-workspace.css`. Tám tệp sau chỉ còn test đọc mã; gỡ chúng phải sửa 9 tệp test (bảng ở mục Ràng buộc).
28. Class có CSS nhưng không template hay JS nào tham chiếu: `farm-work.css` 17 trên 52 class (`farm-kpis`, `farm-status`, `farm-assignment`, `farm-heading`…), `work-mobile.css` 17 trên 41 (`work-list-row`, `work-chips`, `work-status`, `work-photo-preview`…), `land.css` 6 (`land-mini`, `land-check`, `land-row-actions`, `land-form--grid`, `land-form__full`, `land-file`), `forecast-workspace.css` 8 (`forecast-meter*`, `forecast-week-table`…), `forecast-calendar.css` 5.
29. Mã thừa trong tệp đang dùng: `field-work-model.js:10` `stateTone` không nơi nào import; `field-work-model.js:28` `boardRows` chỉ test gọi; `lotSummary` trả `works`, `due`, `held` không hiển thị (`lot-entry-model.js:108-110`) và bị gọi 4 lần cho mỗi thẻ (`LotCards.vue:19,22`); `BlockForecastApp.vue:73-76` có header rỗng, import `UiButton` không dùng; `FarmWorkApp.vue` có `taskState`, `team`, `teamName`, `dismissOnBackdrop` không dùng và `tab` luôn là `setup`.
30. Tài liệu lệch mã: `docs/BUNCH_TAG_CATALOG.md:12-16` còn ghi 17 màu, kỳ 5 ngày, trái với `docs/LOTUS_RIBBON_2026W43.md:27`. `docs/FARM_WORKSPACE.md:8-15` mô tả các tab Tổng quan, Kế hoạch, Tiến độ và "thửa" không còn trong `FarmWorkApp.vue`.

### E. Trợ năng và vùng bấm

31. `UiButton size="sm"` cao tối thiểu 32px (`components/ui/button/index.js`). Nút này dùng cho ô "Sáng", "Chiều" theo từng người (`LotEntryModal.vue:178-180`) và nút thêm việc nhanh (dòng 121) trên điện thoại. `--lotus-touch` (44px) được dùng 0 lần trong vùng này. `.bunch-chips button` cao tối thiểu 32px (`BunchWeeklyForecast.vue:162`).
32. Có 9 loại thẻ bấm được và 1 nhóm tab (10 khai báo `cursor:pointer`) nhưng `<style>` của `components/field` và `components/report` có 0 luật `:hover`, 0 luật `:active`, 0 `transition`.
33. Trạng thái tải: 11 trên 13 component trong `components/field` đặt `aria-busy`, chỉ 2 có chữ báo tải (`PaperPhotoReview.vue:57`, `WorkTicket.vue:122`). Không component nào dùng `components/ui/skeleton`. Màn trống cho đến khi có dữ liệu (ví dụ `RibbonBoard.vue:55`).
34. Ký tự thay icon: `LotEntryModal.vue:165` (▲▼), dòng 167 (✓); `LandBlockDetail.vue:79` (‹), dòng 102 và 139 (↗, 4 lần); `BunchWeeklyForecast.vue:96` (⚠), dòng 120 (‹); `FarmWorkApp.vue:127,134` (＋); `WorkMobile.vue:106` (👤). Test ở `design-tokens.test.js:85-91` chỉ bắt một nhóm ký tự khác. 13 component field và 2 component report không dùng `LotusIcon` lần nào.
35. `LotCards.vue:26` cắt còn 4 màu dây đầu (`slice(0,4)`), không có "+N". Số buồng theo tuần nằm trong thuộc tính `title`, không đọc được trên màn cảm ứng.
36. Lô trên bản đồ là path SVG của Leaflet, không vào được bằng bàn phím. Màn bản đồ toàn trang (`App.vue:234`) không có danh sách lô thay thế.
37. `.field-reports__tabs` và `.land-farms` có `role="tab"` nhưng không có `tabindex` luân chuyển, phím mũi tên và `role="tabpanel"` (`FieldReports.vue:44-46`, `FarmLandApp.vue:131-134`).

### F. Giá trị ghi cứng

38. `components/field`: 121 khai báo `gap`, `padding`, `margin` bằng px; 0 lần dùng `var(--lotus-space-*)`. Cỡ chữ và bo góc bằng px: `farm-work.css` 27 và 11; `work-mobile.css` 23 và 9; `forecast-calendar.css` 25 và 12; `forecast-workspace.css` 23 và 12; `Vip126RollingForecast.vue` 23 và 11; `ColorTagCatalogApp.vue` 5 và 1.
39. Ngưỡng nghiệp vụ nằm trong mã giao diện: mật độ `DENSITY_EDGES=[1500,1800,2100,2400]` (`map-land.js:10`); ngưỡng lệch dự thu 10% và 15% (`components/ForecastVariance.vue:29`); tâm bản đồ `[11.602,106.79]` (`CareMap.vue:82`); danh sách vườn có ảnh flycam và ghi công "Ảnh flycam Lotus Farm 222" cho cả `LOTUS-180` (`CareMap.vue:79`; chưa kiểm vườn 180 có nằm trong vùng ảnh).
40. Biểu đồ không đặt `fontFamily` (0 lần ở `LotusChart.vue` và `DesktopForecastChart.vue`), nên chữ trong biểu đồ dùng phông mặc định của ECharts thay vì `--lotus-font`. `animationDuration` 200 và 240 không theo `--lotus-motion` và `prefers-reduced-motion`. Mã màu trong JS: `LotusChart.vue:50` (`#fff`, `rgba(0,0,0,.6)`), `DesktopForecastChart.vue:20-25` (5 mã hex). Bảng số của cả 23 biểu đồ dùng chung `storage-key="chart-data-table"` (`LotusChart.vue:84`).
41. Mọi biểu đồ một chuỗi (15 trên 23) tô `--lotus-chart-1`, tức đỏ thương hiệu (`lotus-tokens.css:32`). Màu này cách `--lotus-danger` 1,20:1 nên số liệu thường như diện tích, số cây trông như cảnh báo.

### G. Điện thoại

42. Hộp nhập trên điện thoại là `WorkspaceModal`, teleport ra `<body>` (`components/WorkspaceModal.vue:30`), nằm ngoài `.lotus-pwa-shell` (`components/LotusMobileShell.vue:23`). 8 trên 16 luật `.lotus-pwa-field` trong `mobile-ui.css` có tiền tố `.lotus-pwa-shell` nên không áp vào ô nhập trong hộp; các luật `.lotus-work …` và `.lotus-mobile button:active` cũng vậy. `LotEntryModal.vue:228` có một luật vá. Chưa kiểm trên thiết bị.
43. Hai kiểu thẻ trong cùng ứng dụng điện thoại: `.mobile-list-card` cho phiếu giao (bo 14–15px, đệm 16px, tiêu đề 19px: `mobile-work-legacy.css:36-39`, `mobile-ui.css:53`); thẻ lô, màu dây, việc đến hạn bo 8px, đệm 10×12px, chữ phụ 12px. `--lotus-text-sm` (12px) dùng 40 lần trong `<style>` của `components/field` và `components/report`, không có ghi đè cho điện thoại; cỡ chữ gốc của khung điện thoại là 15px (`mobile-ui.css:8`).
44. Phản hồi không theo chuẩn chung: lỗi là `<p class="lotus-list-page__error">` (12 chỗ), thông báo xong là `<p>` nội tuyến (6 chỗ). Không dùng `LotusMobileFeedback` và không dùng `use-toast` (0 lần trong `components/field`, `components/report`).
45. Gói `/work` nạp tĩnh `components/DataTable.vue` (ag-grid-vue3, ag-grid-community) qua `RibbonBoard.vue:6`, `CareDueList.vue:7` và `WorkAssign.vue:4` → `components/ListPage.vue:5`, dù trên điện thoại ListPage và bảng lô × việc bị ẩn bằng `v-if="!mobile"`. Chưa đo dung lượng.
46. `App.vue:48` import tĩnh `CareMap.vue`, kéo Leaflet, polygon-clipping, polylabel vào gói chính; `defineAsyncComponent` ở `FarmLandApp.vue:26` và `LandBlockDetail.vue:20` không còn tác dụng tách gói. Ba tệp đặt tên biến `PlotMap` cho CareMap trong khi `components/PlotMap.vue` là tệp khác.

### H. Quy ước bố cục

47. Tiêu đề và mô tả phía trên nội dung: `FarmLandApp.vue:130` (`<h2>Vườn & lô</h2>`), `ColorTagCatalogApp.vue:90` (tiêu đề và đoạn mô tả), 10 đoạn chú thích nghiệp vụ phía trên danh sách (`FieldReportApp.vue:211,215,219,222,229,234`, `WorkAssign.vue:77`, `WorkInspect.vue:24`, `MyPay.vue:23`, `CareCycleSettings.vue:68`). `AGENTS.md:3-6` cấm mô tả trang trí nhưng cho giữ hướng dẫn bắt buộc; cần chủ vườn quyết từng đoạn.
48. `ColorTagCatalogApp.vue:94-102,117-121` bọc ô nhập bằng `<label>` tự viết và dòng 107 dùng `<input type="checkbox">` trần, thay vì `FormField` hoặc `LotusField`.
49. Vườn & lô còn lớp thửa (`FarmLandApp.vue:35,143`, `LandBlockDetail.vue:109-113,172-179`) trong khi FR-002 bỏ thửa; việc gỡ là T071, chưa làm (`specs/002-cham-soc-thu-hoach-du-thu/tasks.md:324`). Bộ giao diện mới không nên vẽ thành phần cho thửa.

### I. Chưa kiểm

- Hiển thị thật trên trình duyệt và thiết bị của mọi điểm suy ra từ import tĩnh (điểm 4, 5, 6, 42).
- Lỗi `landPreviewColumns` khi chạy (điểm 1).
- Vườn `LOTUS-180` có nằm trong vùng ảnh flycam của vườn 222 hay không (điểm 39).
- Dung lượng gói `/work` và gói chính (điểm 45, 46).
- Các đường dẫn `go('work')` và `go('measurements')` ở `LandBlockDetail.vue:102,139` còn màn đích hay không.
- API phía máy chủ có trả số kỳ trước cho ô số liệu hay không.

## Thiếu so với một bộ giao diện đầy đủ

1. **Token nghề.** `lotus-tokens.css` có màu khu và màu chuỗi biểu đồ, chưa có: màu dây, thang tình trạng lô, thang độ chắc của dự thu, viền bảo đảm thấy chấm Trắng và Đen, cỡ chữ và vùng bấm cho ngoài trời.
2. **Thẻ lô dùng chung** và **lưới lô theo khu** (64 lô nhìn một lần mà không cần ranh bản đồ). Hiện chỉ có bảng và bản đồ.
3. **Nhãn màu dây** dùng chung, **chú giải 12 màu**, **dải chu kỳ màu theo tuần**. Màn danh mục màu dây không có một ô màu nào.
4. **Nhãn tuần ISO** và **dải tuần** (13 tuần, đánh dấu tuần này, tuần đến tuổi thu, tuần đã chốt). Chưa có hàm định dạng tuần và hàm tính tuần ISO dùng chung có test cho tuần 53.
5. **Nhãn trạng thái theo nghề** có icon và chữ: báo cáo ngày, vòng chăm sóc, tuổi buồng, phiếu giao, ca xưởng, phiên bản tham số.
6. **Nhãn cách ly có số ngày còn lại**, một câu chữ cho mọi màn.
7. **Thước đến hạn** của vòng chăm sóc và **thanh tiến độ** cắt → bao → thu → còn, tỷ lệ đóng gói, số lô đã giao.
8. **Ô số liệu** một kiểu, có đơn vị tách riêng, trạng thái trống, đang tải, không có quyền; chỗ cho xu hướng khi API có số kỳ trước.
9. **Dòng thời gian của lô** (cắt bắp, bao, thu; phun và khoảng cách ly) và hộp sổ lô mở từ bản đồ.
10. **Thẻ ca xưởng** có thanh tỷ lệ đóng gói và nhãn tình trạng nhập kho; **nhãn tổ và đội**.
11. **Biểu đồ**: theme ECharts chung; màu chuỗi theo nghĩa; biểu đồ tuổi buồng; dự thu và thực tế trên cùng trục (hiện là thẻ số ở `components/ForecastVariance.vue`); thang hai chiều cho độ lệch; mốc "tuần này" và "bản chốt"; đường nhỏ trong ô số liệu.
12. **Bản đồ**: chú giải dùng chung; thẻ lô khi bấm; mã hóa tình trạng bằng nhãn hoặc hoa văn; thước tỉ lệ cho công cụ đo; đổi lớp nền; định vị người dùng ngoài vườn; tìm lô; trạng thái tải và lỗi ô ảnh; danh sách thay thế cho bàn phím.
13. **Điện thoại**: hộp nhập mở từ dưới theo chuẩn PWA; nút cộng trừ số buồng; nút phân đoạn "Sáng / Chiều" đủ 44px; dấu hiệu "đã lưu trên máy, chờ gửi" ngay trên thẻ lô (hiện chỉ có câu trong hộp, `LotEntryModal.vue:115`); khung chờ và trạng thái trống cho thẻ.
14. **Xem ảnh**: phóng, kéo, xoay ảnh phiếu; ảnh thu nhỏ cho ảnh nghiệm thu; tiến độ "đã kiểm N trên M lô".
15. **Bản in từ trình duyệt**: không có `@media print` cho bảng màu dây, danh sách cần thu, báo cáo tuần, bản đồ.
16. **Trang mẫu**: `components/UiShowcase.vue` (75 dòng) không có thành phần nông nghiệp nào.
17. **Kiểm tra tự động**: chưa có test tương phản cho màu dây và thang tình trạng; chưa quét mã màu trong JS và trong `components/field`, `components/land`, `components/report`.
18. **Bảng từ vựng hiển thị**: lô, khu, tuần, lần, đợt màu, tên trạng thái, tên công đoạn.
19. **Dải thời tiết: không làm.** Không có nguồn dữ liệu thời tiết trong mã: grep `weather|thời tiết|lượng mưa|nhiệt độ` trong `lotus_farm/` và `frontend/src/` chỉ ra một tên nhóm lý do hủy trong `lotus_farm/tests/test_brd.py:1116`. Hiến pháp cấm số bịa.

## Đề xuất cho bộ giao diện mới

Thứ tự ưu tiên từ trên xuống. Không thêm thư viện. Tên tệp là đề xuất.

### P0. Sửa trước khi đúc (không đổi diện mạo)

1. Khai báo lại `landPreviewColumns` ở `FarmLandApp.vue` và thêm test mount cho hộp nhập Excel.
2. Đưa `.lotus-form-note` và kiểu thông báo xong về lớp dùng chung nạp ở cả `main.js` và `work-mobile-main.js`; bỏ phụ thuộc vào `StockDocumentForm.vue:224`.
3. Viết kiểu cho thẻ chờ nghiệm thu (`WorkInspect.vue`) bằng thẻ lô mới; xóa các class `work-today__*`, `field-report__notice`, `field-report__warning`, `land-text-link` không có CSS.
4. Chuyển hai luật `care-map--compact` từ `land.css:99-100` về `care-map.css`.
5. Một nguồn "hôm nay": lấy `today` của máy chủ qua một hàm chung; bỏ `new Date().toISOString()` ở `MyPay.vue:9`, `LandBlockDetail.vue:24-25`, `ColorTagCatalogApp.vue:19`, `map-land.js:30`; truyền `today` vào `fillFor` ở `CareMap.vue:56`.

### P1. Nền của bộ nông nghiệp

**Token mới trong `frontend/src/lotus-tokens.css`:**

| Nhóm | Token | Ghi chú |
|---|---|---|
| Màu dây | `--lotus-ribbon-do`, `-trang`, `-tim`, `-cam`, `-den`, `-xanh-duong`, `-xanh-la` | 7 màu gốc đang ở `lot-entry-model.js:130`. Là màu vật thật nên không đổi theo sáng tối |
| Viền chấm màu | `--lotus-ribbon-edge`, `--lotus-ribbon-split` | Viền đạt 3:1 trên `--lotus-surface` sáng và tối; vạch ngăn hai nửa |
| Tình trạng lô | `--lotus-lot-held`, `-late`, `-due`, `-harvest`, `-ok`, `-none`, mỗi màu có `-soft` | Thay `STATUS` ở `map-land.js:15` và 12 viền trái. Các bậc phải khác nhau cả về độ sáng |
| Độ chắc dự thu | `--lotus-certain-cut`, `-inject`, `-est` | Thay biến cục bộ ở `BunchChart.vue:78-79` |
| Tông trạng thái | bảng tone → viền, nền nhạt, chữ cho `success`, `warning`, `danger`, `info`, `neutral` | "info" không còn là đỏ thương hiệu; chữ cảnh báo dùng bậc 700 |
| Chuỗi biểu đồ theo nghĩa | `--lotus-series-harvest`, `-saleable`, `-packed`, `-forecast`, `-actual`, `-plan` | Một đại lượng một màu ở mọi biểu đồ |

**Mô-đun thuần có unit test** (nguyên tắc IV của hiến pháp):

| Tệp đề xuất | Nội dung | Thay cho |
|---|---|---|
| `frontend/src/agri/ribbon.js` | tách mã màu thành các phần, tên đọc, token màu; giữ `swatch()` cho mã cũ | `lot-entry-model.js:130-142` |
| `frontend/src/agri/week.js` | tuần ISO từ ngày, có năm của tuần; `weekLabel` dài và ngắn; khoảng ngày của tuần; nhận `today` của máy chủ | 9 dạng ở mục 2.3; `ForecastVariance.vue:12` |
| `frontend/src/agri/lot-status.js` | từ dữ liệu lô ra `{status,tone,label,icon}`; số ngày cách ly còn lại; số ngày quá hạn | `stateTone` ở hai model; `statusText` ở `CareDueList.vue:30`; `statusLabels` ở `RibbonBoard.vue:27` |
| `frontend/src/agri/labels.js` | một bảng nhãn công đoạn, nhóm việc, trạng thái phiếu; `lotLabel`, `zoneLabel` | 4 bảng ở điểm yếu 24 |
| mở rộng `frontend/src/format.js` | số có đơn vị, ngày ngắn, khoảng ngày | 20 hàm tại chỗ ở điểm yếu 23 |

Mở rộng `frontend/tests/design-tokens.test.js` để quét thư mục con của `components/` và các tệp `agri/*.js`; thêm test tương phản cho chấm màu dây trên nền sáng, tối và cho thang tình trạng lô.

### P2. Thành phần nhỏ (đề xuất đặt ở `frontend/src/components/agri/`)

| Tên | Mục đích | Dữ liệu vào (đã có) | Trạng thái |
|---|---|---|---|
| `RibbonChip` | Chấm màu dây kèm tên, tuần, lần, số buồng. Thay 4 chấm ở mục 2.2 | `{code,label,week,year,lan,count}` từ `lot_report.today`, `ribbon_board.board`, `shift.harvest_sources` | một màu; hai màu (chia đôi có vạch ngăn); Trắng và Đen (có viền); mã lạ (ô gạch chéo, ghi mã); đang chọn; hết buồng; cỡ nhỏ, vừa, lớn |
| `RibbonLegend`, `RibbonCycleStrip` | Chú giải 12 màu và dải tuần – màu | các dòng của `bunch_tag_catalog.catalog` | tuần này; đã qua; sắp tới; chưa có lịch |
| `WeekChip` | Nhãn tuần ISO: "T46 · 09/11–15/11", thêm năm khi khác năm hiện tại | ngày hoặc `YYYY-Www` + `today` máy chủ | tuần này; quá khứ; tương lai; đã chốt |
| `WeekStrip` | Dải 13 tuần để chọn tuần. Thay hộp chọn ba mục và ô "Tuần có ngày" | danh sách tuần của `block_forecast.board`, `ribbon_board.board` | đang chọn; tuần này; có số; đến tuổi thu; khóa |
| `StatusPill` | Nhãn trạng thái có icon và chữ theo bảng tone | khóa trạng thái + nhóm (báo cáo, vòng, tuổi buồng, phiếu, ca, tham số) | 5 tone; cỡ nhỏ, vừa; chỉ icon kèm `aria-label` |
| `QuarantineBadge` | "Cách ly còn 4 ngày, đến 14/11". Thay 7 chỗ ở mục 2.4 | `quarantine_until` + `today` máy chủ | đang cách ly; hết hôm nay; đã hết (ẩn); dạng gọn |
| `LotChip`, `ZoneChip` | "Lô A5" và "Khu A" một cách ghi; ô màu khu có viền đậm | `block_code`, `zone` | thường; đang chọn; vô hiệu; khu ngoài A–F (xám, không mượn màu khu A) |
| `CrewChip` | Tên tổ kèm trạng thái báo cáo và số việc. Thay `.crew-status__team` | `lot_report.status.teams[]` | chưa có báo cáo; chưa gửi; đã gửi; đã xác nhận; mở lại; đang xem |
| `KpiTile`, `KpiStrip` | Ô số liệu: tên, số lớn, đơn vị, dòng phụ. Thay 5 cách ở mục 2.8 | các số của `farm_land.overview.summary`, `ribbon_board.board`, `field_reports.*.cards`, `reporting.charts` | có số; chưa có số (gạch ngang và lý do, không hiện 0); đang tải; không có quyền; bấm được; tone cảnh báo. Xu hướng chỉ hiện khi API trả cả số kỳ trước |
| `Meter` | Thanh tiến độ có `role="meter"`, một đoạn hoặc nhiều đoạn | xem ba dòng dưới | thường; đầy; vượt; không có mẫu số |
| `DueMeter` | Thước đến hạn của vòng chăm sóc: còn n ngày, đến hạn, quá n ngày | `care_cycle.due.rows[]`: `last_done`, `due_date`, `overdue_days`, `status` | chưa đến hạn; đến hạn; quá hạn; chưa làm lần nào; đã giao |
| `BatchMeter` | Cắt → bao → thu → còn của một đợt màu | `ribbon_board.board.cards[]`: `cut`, `bag`, `harvested`, `rejected`, `left` | đang nuôi; đến tuổi; quá tuổi; đã thu hết |
| `PackoutMeter` | Tỷ lệ đóng gói của ca | `shift.shifts[]`: `input_kg`, `finished_kg`, `packout_percent` | ca mở (chưa có kết quả); ca đóng |

### P3. Thẻ và khối

| Tên | Mục đích | Dữ liệu vào (đã có) | Trạng thái |
|---|---|---|---|
| `LotCard` | Một thẻ lô cho mọi màn. Thay 10 kiểu ở mục 2.1 | `lot_report.today.lots[]`, `care_cycle.due.rows[]`, `field_report.setup.blocks[]` | biến thể: nhập ngày, chọn (có ô tick), đến hạn, truy vết. Trạng thái: chưa nhập; chưa gửi; đã gửi; đã xác nhận; mở lại; cách ly; quá hạn; đang chọn; đã có phiếu (khóa); máy đọc chưa kiểm; có nháp trên máy; đang tải. Màu dây hiện đủ hoặc có "+N" |
| `LotGrid` | Lưới lô theo khu, tô theo một chỉ tiêu, bấm mở lô | `field_report.setup.blocks[]` cộng một trong: `lot_report.status`, `care_cycle.due`, `ribbon_board.board`, `field_reports.week.lots[]` | chỉ tiêu: báo cáo ngày, đến hạn chăm sóc, đến tuổi thu, cách ly. Mỗi mức có icon hoặc hoa văn; có chú giải; lô thiếu dữ liệu |
| `RibbonBatchCard` | Thẻ một đợt màu: `RibbonChip`, tuổi tuần, khoảng ngày thu, `BatchMeter`, `StatusPill` | `ribbon_board.board.cards[]` | đang nuôi; đến tuổi; quá tuổi; đã thu hết; có lô cách ly |
| `HarvestDueRow` | Dòng cần thu lô × màu | `ribbon_board.board.due_rows[]` | đến tuổi; quá tuổi; cách ly (nhãn rõ, không làm mờ) |
| `CareWorkCard` | Thẻ một việc của vòng: thanh 4 đoạn quá hạn, đến hạn, đã giao, chưa giao | `care_cycle.due.summary[]` | có quá hạn; chỉ đến hạn; chưa lô nào đến hạn; chưa có vòng |
| `ShiftCard` | Thẻ ca xưởng: mã ca, ngày giờ, kg vào → thành phẩm, thùng, số lô, `PackoutMeter`, nhãn nhập kho | `shift.shifts[]` | đang mở; đã đóng; phiếu nhập nháp; đã nhập kho |
| `LotTimeline` | Dòng thời gian của lô: cắt bắp, bao, thu, phun (kèm khoảng cách ly), nghiệm thu, đổi thông tin | `shift.trace.sources[]` (`harvests`, `sprays` có `phi_days`), `field_report.ticket.entries[]`, `farm_land.block_detail.history` | theo loại sự kiện (icon); khoảng cách ly; trống; đang tải; gom theo ngày |
| `LotLedgerDialog` | Hộp sổ lô mở từ bản đồ, lưới lô, thẻ lô (spec 002, User Story 5, kịch bản 3) | `farm_land.block_detail` + màu còn trên cây của `ribbon_board.board` | đang tải; không có quyền từng phần; lô chưa có số |
| `PaperFormReview` | Xem ảnh phiếu có phóng, kéo; danh sách lô cần kiểm; tiến độ đã kiểm | `lot_report.today.paper`, `lots[].lines[]` (`machine_read`, `review_flags`) | chưa in; đã in; đang đọc; còn lô chưa kiểm; đã kiểm hết; đọc lỗi |
| `PhotoThumb`, `PhotoViewer` | Ảnh thu nhỏ và hộp xem ảnh nghiệm thu | `inspection_doc.photo` | có ảnh; không có; lỗi tải |
| `WeekVarianceCard` | Thẻ tuần so dự thu với thực tế. Thay `.bunch-week` | các dòng của `components/ForecastVariance.vue` | trong mục tiêu; sát mục tiêu; ngoài mục tiêu; chưa có bản chốt |

### P4. Biểu đồ và bản đồ

1. **Một theme ECharts** trong `frontend/src/chart-theme.js`, dựng từ token: phông `--lotus-font`, cỡ chữ theo token, thời lượng theo `--lotus-motion`, tooltip, trục, lưới. `LotusChart.vue` dùng theme này; nhận tên nghĩa của chuỗi để lấy màu `--lotus-series-*`; mỗi biểu đồ một `storage-key` bảng số riêng. Biểu đồ một chuỗi dùng màu trung tính của dữ liệu, không dùng đỏ thương hiệu.
2. **`HarvestForecastChart`**: cột chồng theo độ chắc, thêm đường thực tế đã thu, mốc "tuần này", mốc bản chốt. Dữ liệu: `block_forecast.board.bunch.weeks[]` và các dòng so sánh của `forecast_snapshot`. Giữ hai luật đang có test: số thật và ước tính đứng riêng; chỉ ghi số trên cột cao nhất. Có thể giữ lõi HTML của `BunchChart.vue` vì đã có `aria-label` từng cột.
3. **`BunchAgeChart`**: số buồng còn trên cây theo tuổi (tuần), mỗi cột kèm `RibbonChip`, dải nền là khoảng tuổi thu. Dữ liệu: `ribbon_board.board.cards[]` (`age_weeks`, `left`, `start`, `end`, `status`).
4. **`YieldMeter`**: kg/buồng, thùng/buồng, tỷ lệ đóng gói thật so với tham số đã duyệt. Dữ liệu: `shift.shift.split[]` và `block_forecast.trace.params`. Chỉ vẽ mốc so sánh khi có bộ tham số đã duyệt.
5. **Bộ bản đồ**: tách kiểu vẽ ra `frontend/src/map-theme.js` (nét, độ mờ, quầng, nhãn đang nằm rải trong `CareMap.vue:33-72`). Thêm `MapLegend` dùng cho cả 5 chế độ (thay 3 chỗ vẽ chú giải), `MapModeSwitch`, thẻ lô khi bấm (dùng `LotCard`), nhãn hoặc hoa văn cho tình trạng, thước tỉ lệ, nút đổi nền flycam và vệ tinh, danh sách lô cạnh bản đồ cho bàn phím. Giữ renderer SVG. Màu giống dùng bảng phân loại riêng, không mượn màu khu.
6. Xóa `DesktopForecastChart.vue` cùng các màn dự thu không còn dùng sau khi chủ vườn đồng ý, sửa 9 tệp test liên quan trong cùng lần đổi.

### P5. Điện thoại

1. Biến thể điện thoại của `LotCard`, `RibbonBatchCard`, `CareWorkCard`, `CrewChip` theo kiểu thẻ PWA (`.mobile-list-card`): chữ phụ từ 14px, vùng bấm từ `--lotus-touch`.
2. Hộp nhập lô mở từ dưới bằng wrapper Vant (`LotusMobileDialog` hoặc một wrapper sheet mới), nằm trong `.lotus-pwa-shell`. Giữ nguyên logic nháp, `save_lot`, kiểm số còn lại của màu.
3. Nút phân đoạn "Sáng / Chiều" và nút cộng trừ số buồng cao từ 44px. Nút hành động dùng `LotusMobileButton`.
4. Thông báo dùng `LotusMobileFeedback`; nhãn "đã lưu trên máy, chờ gửi" trên `LotCard` đọc từ `loadDraft`.
5. Nạp trễ `DataTable` ở `RibbonBoard.vue`, `CareDueList.vue`, `WorkAssign.vue` để gói `/work` không mang AG Grid khi chưa mở bảng.

### P6. In, trang mẫu, dọn dẹp

1. `@media print` cho bảng màu dây, danh sách cần thu và báo cáo Tuần: nền trắng, chữ đen, màu dây ghi chữ kèm ô màu. Phiếu ngày giữ nguyên ở bộ in của máy chủ.
2. Thêm mục Nông nghiệp vào `components/UiShowcase.vue` với dữ liệu mẫu 64 lô và 12 màu dây, ghi rõ "dữ liệu mẫu" trên trang. `showcase.html` không nằm trong `rollupOptions.input` của `frontend/vite.config.js` nên không vào bản phát hành.
3. Xóa mã không còn dùng ở điểm yếu 27–29 sau khi chủ vườn đồng ý; cập nhật `docs/BUNCH_TAG_CATALOG.md` và `docs/FARM_WORKSPACE.md`.
4. Trình chủ vườn quyết từng đoạn chú thích ở điểm yếu 47.

### Thứ tự thay thế đề xuất

1. Token và mô-đun thuần (không đổi diện mạo, có test).
2. `RibbonChip` thay 4 chấm màu; `StatusPill` và `QuarantineBadge` thay chữ và viền trái.
3. `LotCard` lần lượt ở `LotCards.vue`, `CareDueList.vue`, `WorkAssign.vue`, `PackhouseShifts.vue`, `WorkInspect.vue`.
4. `KpiTile` thay `.land-stats`, `.lotus-stat`, `.ribbon-board__totals`, `.report-card`. Giữ class cũ làm tên phụ cho đến khi sửa xong test và các màn Tài chính đang dùng `land-*`.
5. Theme biểu đồ, `HarvestForecastChart`, `BunchAgeChart`.
6. Bộ bản đồ và `LotLedgerDialog`.
7. Điện thoại, bản in, trang mẫu, dọn mã cũ.

Mỗi bước giữ nguyên các class và chuỗi mà test ở mục Ràng buộc đang kiểm, hoặc sửa test trong cùng lần đổi.
