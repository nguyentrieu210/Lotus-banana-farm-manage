# Hợp đồng: bộ thành phần Lotus (spec 004)

Ai làm màn mới dùng các thành phần này, không viết kiểu riêng. Mọi thành phần lấy màu, chữ, khoảng cách từ `lotus-tokens.css`. Lớp kiểu (`lotus-*`) là một phần của hợp đồng: ô bảng vẽ bằng DOM (`grid-columns.js`) dùng đúng các lớp này.

**Kiểu nằm ở đâu (đợt 2, để màn nào chỉ nạp kiểu nó hiện, SC-008):**

- `lotus-kit.css` (mọi ứng dụng nạp ngay sau token): lớp nhiều nơi dùng hoặc ô bảng vẽ: số và đơn vị, thẻ `lotus-card`, chip, mũi tên lệch `lotus-stat__delta`, thanh tiến độ, avatar và tổ, chấm và chip màu dây, dấu màu dây dưới tuần, ô bảng, khối in.
- `lotus-kit-mobile.css` (điện thoại và trang mẫu): dải ngoại tuyến, chỉnh cỡ ở chế độ ngoài trời.
- `lotus-kit-chart.css`: biểu đồ SVG, do `ForecastWeekChart` và `AgeHistogram` nạp.
- Còn lại nằm trong khối `<style>` (không `scoped`, tên lớp là hợp đồng) của đúng thành phần: `Banner`, `StatTile` (kèm `lotus-stat-row`), `ProgressRing`, `Switch`, `Segmented`, `NumberStepper`, `Steps`, `Timeline`, `DescriptionList`, `RibbonLegend`, `WeekChip`, `WeekStrip`, `DueMeter`, `QuarantineBadge`, `LotCard` (kèm `lotus-lotcards`), `LotGrid`, `ZoneChip`, `MapLegend`, `ShiftCard`, `RibbonBatchCard` (kèm `lotus-batches`), `RibbonPicker`.
- Muốn dùng một lớp của thành phần thì dùng thành phần đó. Màn nhập thẳng tệp thành phần (`../agri/LotCard.vue`), không qua tệp gộp `agri/index.js`, để gói chỉ kéo đúng kiểu cần.
- Không đặt tên lớp mới trùng tiền tố của bộ (`lotus-stat`, `lotus-chip`…). Màn Tổng quan và Báo cáo từng có `.lotus-stat` riêng đè lên ô số liệu; đợt 2 đã chuyển chúng sang `StatTile` và xóa kiểu cũ.

## Máy tính và điện thoại: `components/ui/`

| Thành phần | Import | Props chính | Sự kiện, slot | Ghi chú |
|---|---|---|---|---|
| `StatusChip` | `ui/status-chip` | `status` (mã gốc), `label`, `tone`, `icon`, `solid`, `size: sm\|md\|lg` | – | Nhãn, tông, biểu tượng từ `ui-status.js`. Mã lạ: trung tính. Lớp `lotus-chip lotus-chip--<tông>`, `data-kind`. |
| `Banner` | `ui/banner` | `tone: info\|success\|warning\|danger\|neutral`, `title`, `icon`, `dismissible` | `@dismiss`; slot mặc định, `#actions` | `role="alert"` khi nguy, `status` khi khác. |
| `StatTile` | `ui/stat-tile` | `label`, `value` (số, hoặc `null` khi chưa có), `unit`, `digits`, `icon`, `tone`, `delta`, `deltaDigits`, `deltaUnit`, `deltaLabel`, `goodWhen: up\|down`, `missing`, `hint`, `as` | `#foot` (thêm vào cuối dòng dưới, ví dụ "Xem 3 dòng") | Thiếu số: "—" kèm `missing`, không hiện 0. Nhãn xuống tối đa hai dòng. `as="button"` khi thẻ mở chi tiết (Báo cáo). |
| `Progress`, `ProgressRing` | `ui/progress` | `value`, `max`, `label`, `valueText`, `tone`, `inline`; vòng thêm `size`, `stroke` | – | `role="progressbar"`, giá trị kẹp 0–100. |
| `Switch` | `ui/switch` | `v-model` (bool), `label`, `disabled` | slot nhãn | reka-ui `SwitchRoot`; nhãn gắn `for`. |
| `Segmented` | `ui/segmented` | `v-model`, `options: [{value,label,count?,icon?}]`, `label` (bắt buộc), `block` | – | reka-ui `ToggleGroup` một lựa chọn; không bỏ chọn được. |
| `NumberStepper` | `ui/number-stepper` | `v-model` (số hoặc `null`), `label` (bắt buộc), `min`, `max`, `step`, `decimals`, `unit`, `size: md\|lg`, `block` | – | Rỗng là `null`, không phải 0. Từ ô rỗng, "+" cho một bước (1 buồng, 0,5 kg) hoặc `min` nếu lớn hơn; "−" cho `min`. Nhận dấu phẩy thập phân. Giữ nút để tăng nhanh. Mũi tên lên xuống. |
| `Avatar` | `ui/avatar` | `name`, `size` | – | Hai chữ cái cuối của tên; tông theo tên. |
| `Steps` | `ui/steps` | `steps: [{label, meta?, state: done\|current\|waiting\|returned}]`, `label`, `vertical` | – | `aria-current="step"`; trạng thái đọc được bằng chữ. |
| `Timeline` | `ui/timeline` | `items: [{title, time?, text?, tone?, icon?}]`, `label` | `#item` | – |
| `DescriptionList` | `ui/description-list` | `items: [{label, value, key?, wide?}]`, `columns` | `#value-<key>` | Giá trị rỗng: "—". |
| `Button` | `ui/button` | `variant: default\|outline\|secondary\|soft\|ghost\|link\|destructive\|danger`, `size: default\|sm\|lg\|icon`, `loading` | – | `default`: hành động chính duy nhất, đỏ đặc. `destructive`: nền đỏ thẫm nhạt có viền. `danger`: đỏ thẫm đặc, chỉ trong hộp xác nhận. |

## Nông nghiệp: `components/agri/`

| Thành phần | Props chính | Sự kiện | Ghi chú |
|---|---|---|---|
| `LotCard` | `lot: {code, zone, state, stateLabel?, status?, line?, todo?, ribbons:[{code,label?,week?,count?}], quarantineUntil?, facts:[]}`, `today`, `interactive`, `maxRibbons` | `@open(lot)` | Thẻ lô dùng chung cho Hôm nay, Màu dây, Vòng chăm sóc; là nút khi `interactive`. |
| `LotGrid` | `lots: [{code, zone?, state, title?}]`, `states` (thứ tự chú giải), `label`, `zoneLabel`, `v-model` (mã lô) | `@select(lot)` | Nhóm theo khu, sắp mã tự nhiên; ô là nút có `aria-label`; chú giải có số đếm. |
| `RibbonDot` | `code`, `label`, `size: sm\|md\|lg`, `band`, `decorative` | – | Luôn có viền. |
| `RibbonChip` | `code`, `label`, `week`, `count`, `unit` | – | – |
| `RibbonLegend` | `items: [{code,label?,count?}]` | – | – |
| `RibbonPicker` | `options: [{code, value?, label?, week?, hint?}]`, `label`, `v-model` (`value`, không có thì `code`) | – | `role="radiogroup"`, phím mũi tên. `value` tách giá trị chọn (mã đợt, ví dụ `bunch_tag`) khỏi mã màu, để hai đợt cùng màu không lẫn. Hộp nhập lô trên điện thoại dùng nó, gợi ý "lần N · còn X". |
| `RibbonBatchCard` | `batch: {code, week, year?, age, cut, bagged, harvested, left, ripe?}`, `today`, `interactive` | `@open(batch)` | – |
| `WeekChip` | `year`+`week` hoặc `date`, `today`, `harvest`, `long` | – | – |
| `WeekStrip` | `today`, `before`, `after`, `harvest: ['YYYY-Www']`, `ribbons: {key:[codes]}`, `values: {key:number}`, `unit`, `label`, `v-model` (khóa tuần) | – | Tuần này `aria-current="date"`. |
| `DueMeter` | `due`, `today`, `cycle`, `soon`, `label` | – | `data-state`: `upcoming`, `due`, `overdue`. |
| `QuarantineBadge` | `until`, `today` | – | Hết cách ly thì không hiện gì. |
| `ForecastWeekChart` | `weeks: [{year, week, forecast?, actual?, low?, high?}]`, `today`, `unit`, `label`, `height` | – | SVG; chỉ vẽ số có; mỗi tuần một nhóm đi được bằng bàn phím, có nhãn. |
| `AgeHistogram` | `bins: [{age, count, ripe?, ribbon?}]`, `unit`, `label`, `height` | – | – |
| `ZoneChip` | `zone`, `label` | – | Màu khu cố định A–F. |
| `MapLegend` | `title`, `items: [{label, colour, count?}]`, hoặc `scale: [colour]` + `ends: [thấp, cao]` | – | – |
| `ShiftCard` | `shift: {date, name, team?, bunches?, kg?, boxes?, status?, statusLabel?, lines?:[chữ], sources:[{lot, ribbon, count}]}`, `interactive` | `@open` | Là nút khi `interactive` (danh sách ca ở màn Xưởng). |
| `CrewChip` | `name`, `team`, `size` | – | – |

## Điện thoại

| Thành phần | Props | Ghi chú |
|---|---|---|
| `LotusMobileNetBar` | `queued`, `online` (bỏ trống thì theo `navigator.onLine`) | Đã có trong `LotusMobileShell`. Dải dính dưới thanh trên. |
| `LotusMobileShell` | như trước | Thêm nút ngoài trời (`aria-pressed`) ở thanh trên. Theo chế độ của máy qua `ui-mode.js`. |
| `LotusMobileBottomNav` | `items: [{name, label, icon, short?}]` | Có chữ dưới biểu tượng (`short` nếu nhãn dài). Giữ `aria-label` đầy đủ. |

## Module thuần

| Module | Xuất | Dùng cho |
|---|---|---|
| `ui-mode.js` | `useUiMode({followSystem, allowOutdoor})`, `readUiPrefs`, `resolveUiMode`, `applyUiMode`, `uiMode`, `uiDensity`, `UI_KEYS` | Chế độ, mật độ |
| `ui-status.js` | `STATUS_KINDS`, `TONES`, `statusKind`, `statusMeta`, `daysBetween`, `dueState` | Chip, ô bảng, hạn |
| `ribbon-colors.js` | `RIBBON_COLOURS`, `ribbonParts`, `ribbonLabel`, `ribbonBackground` | Màu dây |
| `lot-states.js` | `LOT_STATES`, `LOT_METRICS`, `zoneOf`, `zoneColour`, `compareLotCodes`, `groupLots` | Thẻ và lưới lô |
| `agri-format.js` | `isoWeek`, `isoWeekMonday`, `addWeeks`, `weekKey`, `weekLabel`, `weekRange`, `weeksInYear`, `formatNumber`, `formatDelta`, `shortDate`, `initials` | Định dạng nghề vườn |
| `grid-columns.js` | `numberCol`, `moneyCol`, `qtyCol`, `percentCol`, `dateCol`, `dueCol`, `statusCol`, `progressCol`, `ribbonCol`, `personCol`, `deltaCol`, `chipNode`, `iconNode` | Bảng |
| `grid-theme.js` | `lotusGridTheme(density, variant)`, `GRID_DENSITY`, `GRID_VARIANTS` | Bảng |
| `icon-paths.js` | `ICON_PATHS` | `LotusIcon`, ô bảng |
