# Kiểm kê 04 — Bảng dữ liệu dùng chung (AG Grid 36 Community) và phần bao quanh

- Nhánh `004-bo-giao-dien-agritech`, commit `40f8330`. Ngày kiểm: 10/11/2026.
- Chỉ đọc mã bằng Read/Grep/shell nhẹ. Không chạy test, build, dev server hay trình duyệt. Nhận định nào cần nhìn màn hình thật đều ghi **chưa kiểm**.
- Quy ước: `src/…` = `frontend/src/…`, `tests/…` = `frontend/tests/…`. Số đếm lấy bằng `grep`/`wc`/`perl` (cách đếm ở cuối tệp).
- Worktree này không có `frontend/node_modules`. Các ý về AG Grid (module, tham số theme, tuỳ chọn lưới) đối chiếu với types của `ag-grid-community` 36.2.0 cài ở một checkout khác trên cùng máy, đúng phiên bản ghi trong `frontend/package.json` (`ag-grid-community`, `ag-grid-vue3`, `@ag-grid-community/locale` đều `36.2.0`).
- Số dòng trích dẫn theo commit `40f8330`. Trong lúc kiểm, cây làm việc có thay đổi của bước khác ở `frontend/package.json` và `.gitignore`; không tệp nào trong `frontend/src` bị đổi.

## Hiện trạng

### 1. Tệp trong phạm vi

| Tệp | Dòng | Byte | Vai trò |
|---|---:|---:|---|
| `src/components/DataTable.vue` | 402 | 38.654 | Bảng dùng chung. Script 1–315, template 316–352, style 353–402. 31 `computed`, 8 `watch`, 34 `function`. Dòng dài nhất 1.419 ký tự (dòng 330, thẻ `<AgGridVue>`) |
| `src/components/ListPage.vue` | 37 | 3.207 | Trang danh sách chuẩn: thanh công cụ + dải tóm tắt + DataTable + phân trang server |
| `src/components/OpsList.vue` | 35 | 2.377 | Lớp bọc: nhận mảng tên trường, sinh colDef, gọi DataTable `interactive` |
| `src/components/ExcelHeader.vue` | 122 | 5.961 | Header cột: nút sắp xếp + nút lọc + popup lọc kiểu Excel. Không có `<style>` |
| `src/components/ColumnVisibilityMenu.vue` | 93 | 9.524 | Popover "Cột hiển thị": tìm, ẩn/hiện, ghim, đổi thứ tự, preset |
| `src/components/DataTableViews.vue` | 53 | 4.524 | Chip bộ lọc đang bật + chế độ xem đã lưu |
| `src/components/ui/pagination/Pagination.vue` (+ `index.js`) | 54 (+1) | 5.116 (+56) | Phân trang trên `reka-ui` |
| `src/components/LotusGridEditCell.vue` | 25 | 1.758 | cellRenderer cho 3 trường cố định của Nhân sự (`employee_select`, `map_action`, `select_log`) |
| `src/components/RosterGridCell.vue` | 29 | 1.945 | cellRenderer ô xếp ca |
| `src/components/TimekeepingGridCell.vue` | 41 | 3.722 | cellRenderer bảng công ngày |
| `src/components/WorkspaceListToolbar.vue` | 21 | 1.652 | Thanh công cụ danh sách (ListPage dùng) |
| `src/components/DesktopEmptyState.vue` | 13 | 676 | Trạng thái trống |
| `src/grid-theme.js` | 6 | 685 | Theme `themeQuartz.withParams` |
| `src/grid-modules.js` | 4 | 842 | Đăng ký module AG Grid |
| `src/grid-app-keys.js` | 4 | 525 | Danh sách cờ cột riêng của app |
| `src/grid-format.js` | 34 | 2.621 | Nhóm số, ngày ISO, ghép cột đơn vị, cột rỗng |
| `src/grid-totals.js` | 29 | 2.714 | Dòng tổng |
| `src/grid-visibility.js` | 83 | 4.397 | Ẩn/hiện, thứ tự, ghim; đọc ghi localStorage |
| `src/grid-state.js` | 19 | 1.367 | Bề rộng cột, chế độ xem; localStorage |
| `src/grid-row-id.js` | 13 | 663 | Định danh dòng |
| `src/table-pagination.js` | 20 | 995 | Đọc mọi trang server khi cỡ trang = 0 |
| `src/excel-export.js` | 65 | 5.964 | Dựng XLSX bằng `fflate` |
| `src/excel-filter-state.js` | 46 | 2.272 | Logic chọn giá trị lọc |
| `src/pivot-filter.js` | — | — | **Không tồn tại** trên nhánh này. Bị xoá ở commit `b81e758` (10/11/2026). Chuỗi "pivot" chỉ còn ở `src/system-translations.js` và `tests/field-navigation.test.js:31` |

Test trong phạm vi: 16 tệp nêu tên, 779 dòng, 55 lệnh `test(` (một lệnh trong `tests/pagination-size.mount.test.js` chạy vòng 5 màn). Ngoài ra `tests/excel-export.test.js` (3 ca). Tổng `frontend/tests` có 155 tệp `*.test.js`; 43 tệp có tham chiếu tới bảng (tên component, module `grid-*`/`excel-*`/`table-pagination`, class `lotus-*`/`.ag-*` của bảng).

### 2. Nơi dùng (đếm thẻ trong template)

| Component | Số tệp `.vue` | Số thẻ | Ghi chú |
|---|---:|---:|---|
| `<DataTable>` | 44 | 132 | Gồm 3 tệp không phải màn hình: `ListPage.vue`, `OpsList.vue`, `UiShowcase.vue` (mỗi tệp 1 thẻ). Nhiều nhất: `src/FinanceApp.vue` 35, `src/components/OneDriveProcessWorkspace.vue` 16, `src/components/finance/FinanceAssets.vue` 12, `src/components/land/LandBlockDetail.vue` 10 |
| `<ListPage>` | 13 | 18 | `src/FieldReportApp.vue` 6; mỗi tệp còn lại 1 |
| `<OpsList>` | 1 | 28 | Chỉ `src/App.vue` (nạp bằng `defineAsyncComponent`, `App.vue:40`) |
| Ít nhất một trong ba | 54 / 197 tệp `.vue` | 178 | |

- 4 PWA điện thoại (`WarehouseMobile.vue`, `BuyingMobile.vue`, `WorkMobile.vue`, `HrMobile.vue`) không dùng DataTable/ListPage/OpsList (0 tham chiếu). `tests/warehouse-mobile-standalone.test.js:15` cấm `DataTable|AGGrid|UiButton` trong `WarehouseMobile.vue`. Bộ `src/components/LotusMobile*.vue` (15 tệp) không có component danh sách/thẻ bản ghi dùng chung.
- AG Grid chỉ được import ở 3 tệp: `DataTable.vue`, `grid-modules.js`, `grid-theme.js`.
- Bảng nhập dòng chứng từ không dùng DataTable: `src/components/form/LineItemsEditor.vue` (CSS grid, 17 thẻ ở 10 tệp) có lược đồ cột riêng (`{field,label,type,width,…}`) và cũng dùng slot `#cell-<field>`.

Tần suất thuộc tính trên 132 thẻ `<DataTable>` (trực tiếp): `rows` 132, `columns` 132, `storage-key` 103, `row-key` 91, `empty` 62, `interactive` 22, `@open` 22, `loading` 21, `totals` 8 (đều `false`), `pinned-bottom-rows` 5, `paginate` 5, `export-title` 5, `selection-enabled` 4, `fill` 4, `selected-row-keys` 3, 3 sự kiện chọn mỗi loại 3, `exportable` 3, `columns-menu` 3, `@cell-open` 3, `tools-target` 2, `row-index-offset` 2; mỗi thứ sau 1 lần: `totals-label`, `show-empty-headers`, `server-filters`, `filter-values`, `@filter`, `row-detail`, `row-class`, `page-size`, `mobile-limit`, `keep-height`, `column-layout`, `auto-hide-empty`, `@visible-rows`, `@row-double-open`. Qua `<ListPage>` (18 thẻ): `storage-key` 16, `interactive` 12, `show-empty-headers` 9, `paged` 7, `server-sort` 5, `filter-values` 4, `export-rows` 2, `column-presets` 2, `summary` 2.

### 3. API công khai của `DataTable.vue`

**34 props** (`DataTable.vue:30`):

| Prop | Kiểu, mặc định | Tác dụng |
|---|---|---|
| `rows` | Array, `[]` | Dữ liệu |
| `columns` | Array, bắt buộc | colDef AG Grid + cờ riêng (mục 3.4) |
| `loading` | Boolean | Khung xương khi chưa có dòng; `loading` của AG Grid khi đã có dòng; `aria-busy` |
| `empty` | String, `'Chưa có dữ liệu.'` | Tiêu đề trạng thái trống và `noRowsToShow` |
| `emptyHint` | String, `''` | Mô tả dưới tiêu đề trống. 0 nơi dùng |
| `storageKey` | String | Khoá localStorage. Thiếu thì dùng chuỗi nối tên trường (`DataTable.vue:114`) |
| `rowKey` | String | Trường định danh dòng; thiếu thì `gridRowId` tự dò (`grid-row-id.js:8`) |
| `pinnedBottomRows` | Array, `[]` | Dòng ghim dưới do màn hình cấp; có thì tắt dòng tổng tự động |
| `totals` | Boolean, `true` | Dòng tổng tự động |
| `totalsLabel` | String, `'Tổng'` | Nhãn dòng tổng |
| `mobileLimit` | Number | Số cột tối đa trên thẻ điện thoại. Chỉ `OpsList.vue:34` dùng (4) |
| `interactive` | Boolean | Bấm dòng phát `open`; thẻ điện thoại thành `button` |
| `rowDetail` | Boolean, `true` | Bấm dòng mở modal chi tiết chỉ đọc khi màn hình không nghe `open`/`cell-open`/`row-double-open` |
| `rowClass` | Function | Class theo dòng. Thiếu thì áp `lotus-shortage-row` khi `shortage_qty>0` (`DataTable.vue:330`) |
| `serverSort` | Boolean | Phát `sort` thay vì chỉ sắp tại máy |
| `filterValues` | Object | Bật lọc phía server: danh sách giá trị từng cột do server cấp |
| `serverFilters` | Object, `{}` | Bộ lọc server đang áp |
| `showEmptyHeaders` | Boolean | Không có dòng vẫn vẽ lưới với header |
| `fill` | Number, `-1` | ≥0: lưới cao tới cách đáy cửa sổ `fill` px (`DataTable.vue:94`, tối thiểu 280) |
| `keepHeight` | Boolean | Giữ chiều cao cố định dù ít dòng |
| `paginate` | Boolean, `true` | Phân trang tại máy + thanh phân trang |
| `pageSize` | Number, `50` | Cỡ trang ban đầu; 0 = tất cả |
| `rowIndexOffset` | Number, `0` | Cộng vào STT (trang server) |
| `exportable` | Boolean, `true` | Nút "Xuất Excel" |
| `exportRows` | Function | Hàm async trả toàn bộ dòng để xuất |
| `exportTitle` | String | Tên tệp xuất |
| `columnsMenu` | Boolean, `true` | Nút "Cột hiển thị" |
| `hiddenColumns` | Array, `null` | Điều khiển cột ẩn từ ngoài. 0 nơi dùng |
| `columnLayout` | Object, `null` | Điều khiển `{hidden,order,pinned}` từ ngoài. 1 nơi (`FarmLandApp.vue`) |
| `columnPresets` | Array, `[]` | `[{id,label,visible}]`. 2 nơi (`StockInventory.vue:18`, `StockLedger.vue:16`) |
| `selectionEnabled` | Boolean, `true` | Chỉ ảnh hưởng nút chọn trên thẻ điện thoại (`DataTable.vue:333-334`) |
| `selectedRowKeys` | Array, `null` | Chọn dòng do màn hình giữ; `null` thì DataTable tự giữ |
| `toolsTarget` | bất kỳ, `null` | Phần tử để Teleport cụm công cụ (ListPage đưa lên thanh công cụ) |
| `autoHideEmpty` | Boolean | Tự ẩn cột rỗng ở mọi dòng |

**11 emits** (`DataTable.vue:31`): `open` (dòng), `cell-open` (máy tính: sự kiện ô của AG Grid; điện thoại: `{data,colDef}` — hai dạng payload khác nhau, `DataTable.vue:330` và `:338`), `row-double-open` (dòng), `filter` (`{field,values|null}`), `sort` (`[{colId,sort}]`, chỉ khi `serverSort`), `visible-rows` (dòng sau lọc và sắp), `update:hiddenColumns`, `update:columnLayout`, `row-selection-change` (`{id,row,selected}`), `page-selection-change` (`{rows,selected}`), `selection-clear`.

**Slots**: `cell-<field>` và `cell` (scope `{row,value,params,column}`; vẽ ở ô lưới, ở thẻ điện thoại khi không `interactive`, và ở modal chi tiết dòng), `empty-actions`. Thực dùng: 36 template `#cell-*` trên DataTable/ListPage ở 5 tệp màn hình; `#cell` chung 0; `#empty-actions` 0.

**Phương thức expose**: không có. `defineExpose` = 0 trong `DataTable.vue`, `ListPage.vue`, `OpsList.vue`, `ExcelHeader.vue`, `ColumnVisibilityMenu.vue`, `DataTableViews.vue`, `Pagination.vue`.

**3.4. Cờ cột riêng** — `GRID_APP_KEYS` (`grid-app-keys.js:4`), bị xoá khỏi colDef trước khi tới AG Grid (`DataTable.vue:71`):

| Cờ | Tác dụng | Nơi đọc | Nơi dùng ở màn hình |
|---|---|---|---|
| `sum` | `true/false` ép cộng / không cộng ở dòng tổng | `grid-totals.js:9-10` | 28 lần, 8 tệp |
| `defaultHidden` | Ẩn khi người dùng chưa từng chỉnh cột | `DataTable.vue:124` | 4 lần, `ProcurementWorkspace.vue:92-95` |
| `unitField` | Cột chứa đơn vị của cột số lượng | `grid-format.js:23` | 2 lần |
| `hideOnMobile` | Bỏ khỏi thẻ điện thoại | `DataTable.vue:56` | 2 lần |
| `mobileValue` | Hàm giá trị riêng cho thẻ | `DataTable.vue:77` | 1 lần (`stock-columns.js:13`) |
| `autoHide` | `false` = không tự ẩn khi rỗng | `grid-format.js:32` | 0 |
| `groupNumbers` | `false` = không nhóm chữ số | `grid-format.js:17` | 0 |
| `filterable` | `false` = bỏ khỏi ô chọn "Lọc theo cột…" trên điện thoại | `DataTable.vue:286` | 0 |
| `suppressExport` | Không xuất Excel | `DataTable.vue:138`, `excel-export.js:30` | 0 (chỉ DataTable tự gắn, `:271`) |
| `columnChooserLocked` | Không hiện trong "Cột hiển thị" | `grid-visibility.js:5` | 0 (chỉ DataTable tự gắn, `:271`) |

Key AG Grid mà DataTable tự xử lý hoặc ghi đè (`DataTable.vue:68-75`): `tooltipValueGetter`/`tooltipField`/`headerTooltipValueGetter` đổi sang `tooltip`/`headerTooltip`; `tooltip` mặc định `true` (ô nào cũng có tooltip là giá trị hiển thị); `flex` mặc định 1; `minWidth` mặc định 90; `sortable` mặc định `true`; **ghi đè cứng** `filter:false`, `resizable:true`, `headerComponent:ExcelHeader`, `pinned` (chỉ `'left'` hoặc `null` theo layout), `hide`, `headerName` (qua `uiFarmLabel`). Dòng ghim luôn vẽ chữ thường bằng `pinnedRenderer` (`:66-67`).

### 4. `ListPage.vue` và `OpsList.vue`

- `ListPage`: 14 props (`rows, columns, loading, title, search, searchable, searchPlaceholder, summary, error, paged, start, total, hasMore, pageSize`), 4 emits (`update:search`, `update:start`, `update:pageSize`, `refresh`), slots `filters`, `actions` (mặc định của thanh công cụ), `before`, mặc định, và mọi `cell-*` (chuyển tiếp, `ListPage.vue:14,28`). `inheritAttrs:false`; thuộc tính và listener còn lại đổ vào DataTable (`:28`). Tự đặt: `fill` 76 (trang server) hoặc 24, `tools-target`, `auto-hide-empty` khi không `paged`, `paginate` khi không `paged`, `row-index-offset`, `keep-height`, `totals-label` = "Tổng trang này" khi còn trang khác.
- `OpsList`: props `rows`, `columns` (mảng tên trường), `loading`, `filterValues`, `serverFilters`; emits `open`, `filter`. Sinh colDef (`OpsList.vue:23-30`): `minWidth` 160/128, `flex` 1.3/1, `cellClass` gồm `lotus-grid-cell`, `lotus-grid-number` cho 15 trường số (`:16`), `lotus-grid-status` cho `docstatus|status|approval_state`; `valueFormatter` dịch nhãn. `paginate` và `row-index-offset` từ `App.vue` rơi xuống DataTable qua fallthrough attrs.

### 5. Theme AG Grid được dựng thế nào

1. `grid-theme.js:2`: `compactGridTheme = themeQuartz.withParams({...})` với 12 tham số: `accentColor` (`--lotus-accent`), `backgroundColor` (`--lotus-surface`), `foregroundColor` (`--lotus-text`), `headerBackgroundColor` (`--lotus-table-header`), `headerTextColor` (`--lotus-table-heading`), `borderColor` (`--lotus-border`), `rowHoverColor` (`--lotus-soft`), `fontFamily` (`--lotus-font`), `fontSize`, `rowHeight`, `headerHeight`, `spacing`.
2. `grid-theme.js:3-6`: hai biến thể `desktopGridThemes.comfortable` / `.compact`.
3. `DataTable.vue:29`: lấy biến thể theo `inject('lotusDesktopDensity')` rồi `.withParams({fontSize,rowHeight,headerHeight,spacing:3})` — ghi đè cả 4 tham số khác nhau giữa các biến thể.
4. Truyền `:theme="theme"` (`DataTable.vue:330`). Không import tệp CSS nào của AG Grid (grep `ag-grid-community/styles|ag-theme-` = 0). Locale: `AG_GRID_LOCALE_VN` từ `@ag-grid-community/locale` 36.2.0.
5. Module đăng ký (`grid-modules.js:4-5`): `ClientSideRowModel`, `ClientSideRowModelApi`, `Locale`, `RowStyle`, `CellStyle`, `ColumnApi`, `RowAutoHeight`, `PinnedRow`, `Pagination`, `Tooltip`, `RenderApi`, và `Validation` khi DEV. Không đăng ký: `RowSelection`, `ColumnAutoSize`, `ColumnHover`, `CellSpan`, `HighlightChanges`, `CsvExport`, `GridState`, `QuickFilter`, các bộ lọc và editor.
6. CSS ghi đè nằm rải ở các nơi sau. Toàn `src` có 28 lần xuất hiện selector `.ag-*` trong 6 tệp, 13 class AG khác nhau.

| Nơi | Nội dung |
|---|---|
| `src/components/DataTable.vue:353-402` (44 rule, 36 `!important`, 50 giá trị px) | Padding ô 8px và header 7px bằng `!important`; viền cột ghim trái; dòng tổng `font-weight:650` + nền `--lotus-soft`; ô chọn, ô STT; input trong ô; nút liên kết trong ô; thẻ điện thoại; modal chi tiết |
| `src/attio.css:69-81` và `:99-114` | Khung `.lotus-ag-grid-shell` (viền, bo 8px, nền `#fff`), cao 520px, `.ag-header` 600, `.ag-header-cell-text` 11px, viền focus hàng; trong `@media(max-width:650px)`: ẩn lưới, hiện thẻ và ô lọc điện thoại |
| `src/compact.css:3,54-66,113-118,137,150-152,165,216,242-243,270-293` | Toàn bộ style của ExcelHeader và popup lọc (viết hai lần: `.excel-popup` và `.lotus-excel-popup`), `.lotus-shortage-row`, chiều cao khung cuộn, biến thể Kho, `@media(max-width:700px)` ẩn lưới của Kho |
| `src/stock-overview.css:12,22-41` | Kho: viền dọc ô và header, viền ngang dòng (đều `!important`), hover header, khung nút lọc |
| `src/warehouse-table-center.css:3-7` | Kho: căn giữa mọi ô và header (`!important`) |
| `src/desktop-system.css:53-59` (trong `@media (min-width:901px)`) | Bo 9px; màu, nền, `font-weight:650` cho `.ag-header-cell` |
| `src/desktop-shell.css:48` | `max-width:100%` cho khung lưới trong panel |
| `src/timekeeping.css:46-58` | Chấm công: cụm công cụ, bo góc `.ag-root-wrapper`, nền dòng đã sửa |
| `src/stock-attio.css:33-34,49`, `src/land.css:35`, `src/hr-workspace.css:72` | Padding trong panel Kho, vỏ bảng lô, `.lotus-grid-warn` |
| `src/workspace-experience.css:188-191` | Khung xương `.lotus-table-skeleton` |
| `src/components/stock/StockDocumentDetail.vue:117-118`, `src/finance.css:43-45`, `src/financial-planning.css:8` | Màu chữ ô theo trạng thái |

### 6. Mật độ và chiều cao dòng

| Nguồn | Cỡ chữ | Dòng | Header | spacing | Có hiệu lực |
|---|---:|---:|---:|---:|---|
| `grid-theme.js:2` (`compactGridTheme`) | 12 | 36 | 34 | 4 | Không — bị `DataTable.vue:29` ghi đè |
| `grid-theme.js:4` (`comfortable`) | 14 | 48 | 42 | 6 | Không |
| `grid-theme.js:5` (`compact`) | 13 | 38 | 38 | 4 | Không |
| `DataTable.vue:29`, mật độ khác `comfortable` | 12 | 34 | 33 | 3 | Có — mọi phân hệ không `provide` mật độ, và mọi màn < 901px |
| `DataTable.vue:29`, mật độ `comfortable` | 13 | 40 | 38 | 3 | Có — chỉ `StockApp.vue:30` và `FieldReportApp.vue:30`, khi ≥ 901px |
| `lotus-tokens.css:47` (`--lotus-row:36px`) | — | 36 | — | — | DataTable không đọc token này |

- `src/use-desktop-workspace.js:7-9`: mật độ mặc định `comfortable`, lưu ở localStorage `lotus-desktop-density`. Hàm `setDensity` (`:14`) không có nơi gọi nào trong `src` (grep). Không có nút chuyển mật độ; `AGENTS.md:3` cấm nhóm chọn mật độ phía trên bảng.
- Hệ quả: bảng dưới `StockApp.vue` (Kho) và `FieldReportApp.vue` (báo cáo, giao việc vườn) mặc định dòng 40px; bảng của `FinanceApp.vue`, `HrApp.vue`, `TimekeepingApp.vue`, `FarmLandApp.vue` và Mua hàng (`ProcurementWorkspace.vue`, nạp từ `App.vue`) dòng 34px.
- `domLayout`: `autoHeight` khi ≤ 10 dòng và không `keepHeight`; ngược lại `normal` với khung cao cố định (`DataTable.vue:102,330`).

### 7. Header cột và lọc kiểu Excel

- Mọi cột nghiệp vụ nhận `headerComponent: ExcelHeader` (`DataTable.vue:74`), không ngoại lệ. Cột Chọn có header dựng bằng DOM (`:258-259`); cột STT dùng header mặc định của AG Grid.
- `ExcelHeader.vue:94-97`: hai `<button>` gốc — `.excel-sort` (nhãn cột; bấm gọi `params.progressSort(shiftKey)`, Shift để sắp nhiều cột) và `.excel-trigger` (ký tự `▾`, `aria-expanded`, `aria-pressed`).
- Popup (`ExcelHeader.vue:98-120`): `<Teleport to="body">`, `role="dialog"`, ô tìm, "Chọn tất cả kết quả (n)" có trạng thái một phần, danh sách checkbox gốc, "Đã chọn x / y giá trị", nút "Xóa lọc" và "Áp dụng". Tự tính vị trí bằng `getBoundingClientRect` (`:24-37`), neo bên phải nút lọc (`excel-filter-state.js:44-46`), rộng tối đa 312px. Escape đóng và trả focus về nút lọc (`:67-69`).
- Logic chọn (`excel-filter-state.js`): tìm không dấu; gõ chữ thì tự chọn các giá trị khớp cho tới khi người dùng tự tick; chọn hết = bỏ lọc (`null`); bỏ hết = `[]` (0 dòng).
- Danh sách giá trị (`DataTable.vue:54`): từ `filterValues[field]` (server) hoặc giá trị duy nhất của `rows` sau khi áp bộ lọc của các cột khác; sắp bằng `sortExcelChoices`; nhãn lấy qua `valueFormatter` của cột.
- Lọc tại máy làm trong Vue: `visibleRows = rows.filter(passes)` (`DataTable.vue:49-50`). Bộ lọc gốc của AG Grid tắt hẳn (`filter:false`). Lọc server: phát `filter`.
- Kiểu dáng header: `.excel-sort` 11px/600, một dòng, cắt bằng `…` (`compact.css:55`); tooltip header = tên cột.
- Không có chỉ báo chiều sắp xếp: `ExcelHeader.vue` không đọc trạng thái sort; grep `sorted-asc|sorted-desc|getSort(|aria-sort` trong `src` = 0 kết quả.

### 8. Dòng tổng ghim dưới

- Tự động khi `totals` (mặc định bật), không có `pinnedBottomRows`, và có dòng hiển thị (`DataTable.vue:57-62`). Truyền vào `pinned-bottom-row-data`.
- Cột được cộng (`grid-totals.js:8-20`): `sum:true`; hoặc mọi giá trị là số, nhãn/tên trường không khớp danh sách loại trừ (đơn giá, tỷ lệ, %, số dư, mã, năm, tháng, tuổi… `:3-4`), không lẫn đơn vị (`:7`), và formatter không biến số thành chữ (`:17-18`).
- Nhãn "Tổng (N dòng)" đặt ở cột đầu tiên không cộng (`:26-27`). Giữ đơn vị duy nhất trên dòng tổng (`:25`).
- Cộng trên mọi dòng sau lọc của mọi trang tại máy. Với trang server chỉ cộng trang đang tải, nhãn "Tổng trang này" (`ListPage.vue:28`).
- Kiểu dáng: `font-weight:650`, nền `--lotus-soft` (`DataTable.vue:394`). Mọi cột vẽ chữ thường (`:66-67`).
- Điện thoại: `<dl class="lotus-mobile-total">` (`DataTable.vue:342`).
- 8 thẻ tắt (`:totals="false"`), 5 thẻ tự cấp `pinned-bottom-rows` (đều ở `FinanceApp.vue`).

### 9. Phân trang

- Tại máy: AG Grid phân trang (`pagination`, `pagination-page-size`), ẩn thanh của AG Grid (`suppress-pagination-panel`), dùng `Pagination` chung phía dưới (`DataTable.vue:343`). Cỡ trang 20/50/100 và "Hiện toàn bộ" (cỡ 0) (`Pagination.vue:14,19-20`). Cỡ trang không được lưu.
- `Pagination.vue:21-35`: luôn hiện khoảng dòng "a–b / tổng"; có `total` và nhiều hơn một trang thì hiện số trang (`PaginationRoot`, `sibling-count=1`, `show-edges`); không có `total` thì "Trước"/"Tiếp" theo `hasMore`. Một trang thì chỉ còn ô "Dòng/trang", nút "Hiện toàn bộ" và khoảng dòng.
- Server: `ListPage` đặt `paginate=false` cho DataTable và tự vẽ `Pagination` (`ListPage.vue:29`). `tablePage` (`table-pagination.js:3-20`) đọc lần lượt các trang 100 dòng khi cỡ trang = 0; 8 màn dùng.
- Chiều cao: `fill ≥ 0` thì lưới = `innerHeight − top − fill − 56` (khi có phân trang), tối thiểu 280 (`DataTable.vue:94`). Không `fill` thì lấy từ CSS `.lotus-ag-grid-shell--scroll`.
- `Pagination.vue:50-53`: khi có `.ai-chat` và ≥ 721px, thanh phân trang chừa 144px bên phải cho nút chat.

### 10. Cột Chọn và cột STT

- `gridDefs = [select, sttDef, ...body]` (`DataTable.vue:273-280`): hai cột tiện ích luôn đứng đầu, ghim trái, khoá vị trí, không đổi cỡ, không nằm trong "Cột hiển thị", không xuất Excel.
- Cột Chọn `__lotus_select` rộng 42 (`:260-263`): nút tự dựng bằng DOM (`utilityButton`, `:220-232`), `aria-pressed`, dấu `✓` là ký tự; header chọn/bỏ cả trang hiện tại, trạng thái một phần bằng class `is-partial`. Không dùng `RowSelectionModule` của AG Grid.
- Trạng thái chọn: nội bộ (`selectedLocal`) hoặc do màn hình giữ qua `selectedRowKeys` + 3 sự kiện. Cụm công cụ hiện "N dòng đã chọn" và nút "Bỏ chọn" (`:319`). Không có slot hay prop cho thao tác hàng loạt.
- Màn hình có sẵn cột chọn nghiệp vụ (`headerName:'Chọn'`, id thuộc `__pick|selected|select_log|choice`, `:270`) thì cột đó thay chỗ cột Chọn chung, giữ renderer riêng.
- Cột STT `__lotus_stt` rộng 52 (`:264-268`): `rowIndexOffset + rowIndex + 1`, theo thứ tự sau sắp/lọc, chạy liên tục qua các trang; canh giữa, `tabular-nums`, màu `--lotus-muted` (`:356,362`).
- Chỉ 3 thẻ nghe sự kiện chọn (`FarmLandApp.vue`, `TimekeepingApp.vue`, `HrTeamAssignments.vue`).

### 11. Cột hiển thị (`ColumnVisibilityMenu.vue`)

- Nút "Cột hiển thị" + số cột đang ẩn. Popover: ô tìm tên cột, preset (nếu có), "Hiện tất cả", "Mặc định", mỗi cột một hàng gồm nút bật/tắt (`aria-pressed`, không cho ẩn cột cuối cùng), nút ghim (tối đa 2, ghim trái), nút lên/xuống.
- Layout `{hidden,order,pinned}` chuẩn hoá ở `grid-visibility.js:27-34`. Cột có `pinned:'left'` trong colDef khởi đầu ở trạng thái ghim (`:44`).
- Tự ẩn cột rỗng (`autoHideEmpty`): cột không có giá trị ở mọi dòng bị ẩn cho tới khi người dùng bật lại; danh sách đã bật lưu ở `lotus-grid-shown-empty:<key>` (`DataTable.vue:116-118,134`).
- Áp vào lưới bằng `applyColumnState({…, applyOrder:true})` (`DataTable.vue:139-143`).

### 12. Chế độ xem đã lưu (`DataTableViews.vue`)

- Chỉ hiện khi có bộ lọc đang bật hoặc đã có chế độ xem (`:16`).
- Chip "Tên cột: N giá trị" có nút bỏ; "Xóa tất cả" khi > 1 chip; "Lưu chế độ xem" (tên ≤ 60 ký tự) khi có lọc hoặc sắp; menu "Chế độ xem" để áp hoặc xoá.
- Một chế độ xem chỉ gồm bộ lọc cột + sắp xếp (`grid-state.js:15`). Không gồm cột ẩn, thứ tự, ghim, bề rộng, cỡ trang. Tối đa 12 cho mỗi bảng (`:16`). Lưu theo trình duyệt.

### 13. Lưu trạng thái

Tất cả ở localStorage, theo trình duyệt, không theo tài khoản:

| Khoá | Nội dung | Nguồn |
|---|---|---|
| `lotus-grid-widths:<key>` | Bề rộng cột | `grid-state.js:2-8` |
| `lotus-grid-layout:<key>` | `{hidden,order,pinned}` | `grid-visibility.js:3,47-52` |
| `lotus-grid-hidden:<key>` | Cột ẩn kiểu cũ; vẫn được ghi song song mỗi lần lưu (`:50`) | `grid-visibility.js:2,23-26` |
| `lotus-grid-views:<key>` | Chế độ xem | `grid-state.js:11-19` |
| `lotus-grid-shown-empty:<key>` | Cột rỗng người dùng đã bật lại | `DataTable.vue:116-118` |
| `lotus-desktop-density` | Mật độ | `use-desktop-workspace.js:8,17` |

- `<key>` = `storageKey`, thiếu thì là chuỗi nối tên trường các cột (`DataTable.vue:114`).
- Không lưu: sắp xếp qua lần tải lại (chỉ giữ trong bộ nhớ, `grid-state.js:1`), bộ lọc tại máy (trừ khi lưu thành chế độ xem), cỡ trang, dòng đã chọn.

### 14. Hiển thị trên màn hẹp

- Lưới và danh sách thẻ luôn cùng có trong DOM (`DataTable.vue:330-342`). CSS quyết định cái nào hiện: `attio.css:81` ẩn thẻ; `attio.css:86-114` (`max-width:650px`) ẩn lưới, hiện thẻ; riêng Kho đổi ở 700px (`compact.css:223,242-243`).
- Ô lọc điện thoại `.lotus-mobile-filter` (`DataTable.vue:331`): `UiSelect` "Lọc theo cột…" + nút lọc của `ExcelHeader`; hiện khi > 5 dòng hoặc đang lọc.
- Thẻ (`:333-341`): nút chọn (khi `selectionEnabled`), STT, `<strong>` = giá trị cột đầu tiên không `hideOnMobile`, sau đó các cặp nhãn–giá trị của những cột còn lại (cắt theo `mobileLimit`). `interactive` thì thẻ là `UiButton` ghost có mũi tên và không vẽ slot; không `interactive` thì thẻ là `<article>`, vẽ slot `cell-*`, cột có `colId` thành nút liên kết phát `cell-open`.
- Thẻ lặp trên `pageRows` = lát cắt của `visibleRows` theo thứ tự dữ liệu gốc (`:103`).
- Cụm công cụ trong thanh ListPage: ≤ 640px chỉ còn icon (`:384`).
- Không có: nút chọn cả trang, điều khiển sắp xếp, slot thẻ tuỳ biến.

### 15. Trống, đang tải, lỗi

- Đang tải và chưa có dòng (không `showEmptyHeaders`): 5 thanh `UiSkeleton` (`DataTable.vue:325`); trong khối thẻ là 3 thanh (`:332`). Kiểu ở `workspace-experience.css:188-191`.
- Đang tải khi đã có dòng: `:loading` của AG Grid (`:330`). Hình thức lớp phủ: chưa kiểm.
- Trống: `DesktopEmptyState` với `empty`, mô tả `emptyHint` hoặc "Bộ lọc cột đang ẩn toàn bộ dòng." kèm nút "Xóa bộ lọc" (`:326-328`).
- `showEmptyHeaders`: vẽ lưới có header, chữ trống qua `noRowsToShow`.
- Lỗi: DataTable chỉ có dòng lỗi xuất Excel (`role="alert"`, `:323`). Lỗi tải dữ liệu nằm ở `ListPage` (`error`, `ListPage.vue:25`) hoặc từng màn hình.

### 16. Định dạng số, ngày và căn lề

- Cột không có `valueFormatter`/`cellRenderer`/slot được tự gắn formatter (`grid-format.js:14-19`, `DataTable.vue:48`): số → `toLocaleString('vi-VN',{maximumFractionDigits:3})`; chuỗi ISO → `dd/mm/yyyy [HH:mm]`. Bỏ qua khi tên trường hoặc nhãn là năm, mã, STT, điện thoại, MST (`:3-4`).
- Căn lề hiện có ba cơ chế: `type:'numericColumn'` (31 lần, 10 tệp); class `lotus-grid-number` (`attio.css:75`, chỉ OpsList gắn); Kho căn giữa mọi ô bằng `!important` (`warehouse-table-center.css:3-4`). Cột số được tự định dạng mà không khai `numericColumn` thì căn trái. `columnTypes` và `defaultColDef` không dùng (0).
- `font-variant-numeric:tabular-nums` chỉ có ở ô STT, `.lotus-grid-number`, `.fin .fin-num`; không áp chung cho ô số của lưới.
- Hàm định dạng dùng chung: `fmt` (`domain.js:19`), `formatDate`/`formatDateTime` (`format.js`), `groupNumber`/`isoDateText` (`grid-format.js:9,13`). Ngoài ra `toLocaleString('vi-VN'` xuất hiện 55 lần ở 45 tệp và `Intl.NumberFormat('vi-VN'` 9 lần ở 7 tệp.

### 17. Xuất Excel

- Nút "Xuất Excel" (`DataTable.vue:321`). Dòng lấy từ `exportRows()` nếu có, không thì từ lưới sau lọc và sắp (`forEachNodeAfterFilterAndSort`), không thì `visibleRows` (`:301-314`). Không xét dòng đã chọn.
- Cột = cột đang hiện theo thứ tự người dùng, trừ cột chọn nghiệp vụ (`:138`).
- `buildXlsx` (`excel-export.js:29-54`): một sheet "Dữ liệu", dòng tiêu đề đậm, đóng băng dòng 1, `autoFilter`, bề rộng cột = `minWidth/8` kẹp 14–50, số giữ kiểu số (giá trị thô), chuỗi qua `valueFormatter`, boolean thành "Có"/"Không", tối đa 20.000 dòng, font Arial 11. Chỉ có 2 style ô: không định dạng số, không kiểu ngày.
- Không có dòng tổng, không có dòng tiêu đề bảng/điều kiện lọc/ngày xuất.
- Tên tệp: `exportTitle`, không thì `storageKey`, không thì `Bang-du-lieu` (`:311`).
- Ngoài DataTable chỉ `FarmLandApp.vue:105` gọi `buildXlsx` trực tiếp.

### 18. Tuỳ biến mức cột đang dùng

Số thuộc tính `headerName:` trong `src`: 608 lần ở 48 tệp.

**`cellRenderer`** — 13 lần ở 7 tệp màn hình; `cellRendererParams` 10 lần ở 4 tệp:

| Renderer | Kiểu | Nơi dùng |
|---|---|---|
| `TimekeepingGridCell` | Component Vue: tên, nút có mặt sáng/chiều, phụ cấp, pill trạng thái + nút chi tiết | `TimekeepingApp.vue:95-100` (5 cột) |
| `RosterGridCell` | Component Vue: tên nhân viên, ô ca kéo-chọn | `components/timekeeping/TkRoster.vue:41,45` |
| `LotusGridEditCell` | Component Vue: `<select>`, `<button>`, `<input type=checkbox>` gốc | `components/hr/HrDevicePanel.vue:32-33`, `components/HrOperations.vue:32` |
| `itemCell` | Hàm dựng DOM: hai dòng tên + mã | `stock-columns.js:9,13` |
| `slipLink` | Hàm dựng DOM: thẻ `<a>` | `components/hr/HrPayrollPeriod.vue:118,120` |
| `plotActions` | Hàm dựng DOM: nút thao tác | `components/land/LandBlockDetail.vue:55,63` |

**Slot `#cell-*` trên DataTable/ListPage** — 36 template ở 5 tệp: `components/finance/FinanceAssets.vue` 20, `FinanceApp.vue` 12, `components/ProcurementCompare.vue` 2, `components/ProcurementWorkspace.vue` 1, `components/ForecastProfiles.vue` 1. Nội dung: nút `outline`/`link`, `DropdownMenu` "Thao tác", `Checkbox`, `Input`, `Combobox`, thẻ `<a>`, `<span>` trạng thái, chữ đã định dạng.

**`cellClass`** — 19 lần ở 7 tệp màn hình; `headerClass` 1 lần:

| Class | Ý nghĩa | Định nghĩa | Nơi gắn |
|---|---|---|---|
| `fin-cell-ok` / `fin-cell-bad` / `fin-cell-warn` / `fin-cell-total` | Màu chữ trạng thái; chữ đậm cho dòng tổng báo cáo | `finance.css:43-45,57` | `FinanceApp.vue` 11 lần |
| `lotus-grid-status` | Chữ đậm, màu `--lotus-info-500` | `attio.css:76` | `OpsList.vue:28`, `HrApp.vue:99` |
| `lotus-grid-warn` | Chữ cảnh báo | `hr-workspace.css:72` | `HrApp.vue:102` |
| `lotus-coverage-state is-covered/is-incoming/is-short` | Tình trạng nhu cầu | `compact.css:266` | `stock-columns.js:26` |
| `stock-diff-plus` / `stock-diff-minus` | Chênh lệch kiểm kê | `StockDocumentDetail.vue:117-118` | `StockDocumentDetail.vue:40` |
| `fp-negative` | Số âm | `financial-planning.css:8` | `FinancePlanning.vue:39` |
| `is-ok/is-half/is-off/is-leave/is-draft/is-warn`, `is-holiday` | Ô và header bảng công tháng | `timekeeping.css:121-128` | `TkMonthSheet.vue:29-30,34` |
| `lotus-grid-cell`, `lotus-grid-number` | Con trỏ, căn phải | `attio.css:74-75` | `OpsList.vue:28` |

**`valueFormatter`** — 231 lần ở 43 tệp (không tính `DataTable.vue` và các module `grid-*`); `valueGetter` 104 lần ở 23 tệp. Các mẫu lặp nhiều nhất: tiền `money/cash(p.value)` (≥ 27), số `fmt/num/kg/ton/qty` (≥ 36), ngày `dateFmt/formatDate/date/vnDate` (≥ 25), đơn vị `unitLabel/unit/withUnit` (≥ 16), dịch nhãn `stateLabel/statusLabel/warehouseLabel/hrCatalogLabel/accountLabel/typeLabel` (≥ 22), giá trị hai trạng thái viết tay thành chữ (13 cặp chữ khác nhau, 14 lần: "Có/Không", "Có/—", "Có/Chưa gắn", "Khớp/Lệch", "Đang dùng/Ngừng dùng", "Ngừng dùng/Đang dùng"…), phần trăm, số âm trong ngoặc (`FinanceApp.vue`), số có dấu `+` (`StockDocumentDetail.vue:40`).

**Khác**: `pinned:'left'` 6 nơi; `pinned:'right'` 2 nơi (`FinanceAssets.vue:55`, `FinanceMasterImport.vue:22`); `tooltip` trong cột 7 lần ở 5 tệp; `headerTooltip` 4 lần ở 2 tệp; `cellDataType:false` 1 lần (`UserPermissionAudit.vue:5`); thụt lề cấp bằng khoảng trắng trong `valueGetter`/formatter (`FinanceApp.vue:151`, `components/erp/ErpReport.vue:55`); `rowClass` 1 nơi (`TimekeepingApp.vue:89-93`).

### 19. Từng test khoá điều gì

Test mount chạy trên happy-dom, bỏ mọi import CSS (`tests/support/mount.mjs:31,39`): không có layout, không có media query, không kiểm màu hay kích thước thật. Chúng khoá cấu trúc DOM, class, thuộc tính ARIA, chữ hiển thị. Nhiều test khác khoá **nguyên văn chuỗi mã nguồn** bằng regex.

**`tests/data-table-lifecycle-26.mount.test.js`** (1 ca): đổi `rows` 4 lần rồi unmount; không được có lỗi/cảnh báo AG Grid #26 hay "grid has been destroyed". Không khoá kiểu dáng.

**`tests/data-table-mobile-slots.mount.test.js`** (2 ca):
- Slot `cell-actions` phải được vẽ trong `.lotus-mobile-record-detail` và nút trong slot bấm được.
- Với `interactive`: `.lotus-mobile-records` có đúng 2 `button` (1 nút chọn, 1 thẻ); `.lotus-mobile-record` có `tagName` `BUTTON`; trong thẻ không có `button` lồng; nút chọn có `aria-label="Chọn dòng"` và `aria-pressed` chuyển `true`; bấm chọn không phát `open`; bấm thẻ phát `open` với đúng object dòng.

**`tests/data-table-selection.mount.test.js`** (2 ca):
- Header chọn là `button` trong `.ag-header-cell[col-id="__lotus_select"]`; ô chọn là `button` trong `.ag-row[row-id="…"] [col-id="__lotus_select"]`; trạng thái bằng `aria-pressed`; chọn một phần thêm class `is-partial`; `.lotus-data-table__selected` có chữ "N dòng đã chọn" và một `button` bỏ chọn; nút `.lotus-pagination [aria-label="Trang sau"]`; chọn theo từng trang; không có `console.error`.
- Cột nghiệp vụ `{field:'choice',headerName:'Chọn'}`: đúng 1 header `[col-id="choice"]`, có `.lotus-grid-native-select-header` chữ "Chọn", không còn header `__lotus_select`, renderer của màn hình vẫn chạy.

**`tests/grid-app-keys.test.js`** (2 ca):
- Phân tích AST mọi `.vue`/`.js` trong `src`: object là cột (có `headerName`, hoặc `field` kèm `valueFormatter|minWidth|flex|cellRenderer`) chỉ được chứa key có trong `colDef.d.ts`/`iFilter.d.ts` của AG Grid đã cài, hoặc trong `GRID_APP_KEYS`, hoặc 3 key tooltip cũ.
- `DataTable.vue` phải chứa nguyên văn `import {GRID_APP_KEYS} from '../grid-app-keys'` và `for(const k of GRID_APP_KEYS)delete column[k]`; `GRID_APP_KEYS` phải có `sum`.

**`tests/grid-compact.test.js`** (6 ca):
- `numberFormatter`: nhóm số tối đa 3 số lẻ; không áp cho năm, mã, cột đã có formatter, `groupNumbers:false`.
- `unitColumn`/`summableColumn`/`totalsRow`: ghép `stock_qty` với `stock_uom`; không cộng khi lẫn đơn vị; dòng tổng mang đơn vị và nhãn "Tổng (2 dòng)".
- `emptyColumn`: rỗng khi không dòng nào có giá trị; 0 là giá trị; không có dòng thì giữ header; `autoHide:false` giữ cột.
- Mount: `autoHideEmpty` + `defaultHidden` → các header (trừ id bắt đầu `__lotus`) là `['name','qty']`; ô `.ag-row[row-id="Q1"] [col-id="qty"]` hiện số đã nhóm; bảng không bật `autoHideEmpty` giữ cột rỗng.
- ListPage: phải có `.workspace-list-row .workspace-list-tools .lotus-data-table__export` chứa chữ "Xuất Excel"; cả trang chỉ 1 `.lotus-data-table__export`.
- ListPage `paged`, trang cuối ngắn (`start:100,total:108`) phải có `.lotus-ag-grid-shell--scroll`; danh sách một trang 8 dòng thì không có class đó.

**`tests/grid-row-id.test.js`** (2 ca): `gridRowId` theo `name` hoặc trường chỉ định; dòng không khoá giữ id theo object. Không khoá kiểu dáng.

**`tests/grid-state.test.js`** (2 ca): khoá `lotus-grid-widths:<key>` lưu `{colId,width}` làm tròn, đọc ra thêm `flex:null`, chịu JSON hỏng và không có localStorage; `saveView` thay theo tên, `deleteView` trả phần còn lại.

**`tests/grid-totals.test.js`** (4 ca): cột nào được cộng (số lượng, thành tiền; không cộng đơn giá, mã, năm, số dư; `sum:true/false`); nhãn "Tổng (2 dòng)"; mã số hiển thị thành chữ không cộng; `sortExcelChoices` (số theo giá trị, chữ theo thứ tự tự nhiên, trống cuối).

**`tests/shared-grid-coverage.test.js`** (1 ca): không tệp `.vue` nào trong `src` được chứa `<table`; `DataTable.vue` phải chứa `AgGridVue`.

**`tests/table-pagination.test.js`** (5 ca): `tablePage` — cỡ 0 đọc các trang 100 từ `start` 0 và giữ bộ lọc; trang thường giữ offset và tên tham số (`length`/`page_length`); lỗi giữa chừng không trả dữ liệu thiếu; trang rỗng còn `has_more` báo "Không tải đủ"; `isCurrent` sai thì lỗi `stale`. Không khoá kiểu dáng.

**`tests/pagination-size.mount.test.js`** (1 ca + 5 ca theo màn):
- `select[aria-label="Số dòng mỗi trang"]` có các option 20/50/100; `[aria-label="Trang sau"]`; `.lotus-pagination__range` chứa "51–100", "1–20"…
- Số `.lotus-mobile-record-entry` trong DOM bằng cỡ trang (thẻ và lưới cùng tồn tại); `.ag-row[row-id="R001"]` sau khi đổi cỡ trang; chọn cả trang ra "N dòng đã chọn"; `.lotus-mobile-total dt` chứa "135 dòng".
- "Hiện toàn bộ" được tìm bằng `.lotus-pagination button:not([aria-label])` (nút đầu tiên không có `aria-label` trong thanh phân trang) và ở 5 màn bằng `textContent==='Hiện toàn bộ'`; sau đó không còn `[aria-label="Trang sau"]`.
- 5 màn (`StockInventory`, `StockDocumentList`, `StockLedger`, `WarehousePlanning`, `ProcurementMasters`): đúng 1 `.lotus-pagination`; đổi cỡ trang gọi lại server với `length`/`page_length` đúng và `start=0`.

**`tests/timekeeping-grid-layout-audit.test.js`** (4 ca), toàn regex nguồn:
- `TimekeepingApp.vue`: không có cột `field:'selected',headerName:'Chọn'`; có `:selected-row-keys="selected.map(rowKey)"`, `row-key="row_key"`, 3 listener chọn.
- `DataTable.vue` chứa nguyên văn `const selectDef={colId:'__lotus_select',headerName:'Chọn',width:42,minWidth:42,maxWidth:42` và `const sttDef={colId:'__lotus_stt',headerName:'STT',width:52,minWidth:52,maxWidth:52` (khoá bề rộng 42 và 52), `totalsRow(props.columns.filter(c=>columnId(c)!==nativeSelectId.value)`, `const gridDefs=computed`, `class="lotus-ag-grid-shell"`.
- `timekeeping.css` chứa `.tk-roster{overflow:visible;padding:0}`.
- `Pagination.vue` chứa nguyên văn hai điều kiện `v-if="pageSize>0 && total && total>pageSize"` và `v-else-if="pageSize>0&&!total&&(start>0||hasMore)"`.

**`tests/warehouse-ledger-alignment.test.js`** (2 ca):
- `stock-columns.js` (`movementColumns`) có đủ 15 trường của Sổ kho; vài chuỗi backend.
- `FarmLandApp.vue` có `<div class="land-filter-actions">`, chữ "Xuất bảng Excel" và "Xuất mẫu Excel", nguyên văn `:exportable="false" :columns-menu="false" :column-layout="normalizedLandLayout" :selected-row-keys=`; `land.css` chứa `.land-filter-actions{display:flex;flex-wrap:wrap;align-items:center`; `DataTable.vue` chứa nguyên văn `v-if="columnsMenu||exportable||selectedCount" class="lotus-data-table__export"`.

**`tests/excel-filter-ux.test.js`** (10 ca):
- 5 ca logic `excel-filter-state.js` (tìm không dấu, chọn mặc định theo chuỗi tìm, "chọn tất cả kết quả" giữ lựa chọn ngoài vùng tìm, giá trị áp dụng giữ kiểu gốc, chọn hết = `null`, bỏ hết = `[]`).
- `ExcelHeader.vue` chứa nguyên văn (kể cả khoảng trắng): `const manualSelection = ref(false)`, `watch(search, value =>`, `!manualSelection.value`, `manualSelection.value = true`, `excelDefaultSelection(choices.value, props.params.selection, value)`, `<Teleport to="body">`, `@change="selectVisible"`, `ref="searchInput"`, `@click="clear"`, `@click="apply"`, `onKeydown`.
- `WorkspaceListToolbar.vue`: `workspace-list-filters` đứng trước `workspace-list-search` trong nguồn; không có `type="submit"`. `stock-overview.css` phải chứa `.ag-header-cell`, `.ag-cell`, `border-right:1px solid`.
- `DataTable.vue` chứa `headerName:uiFarmLabel(c.headerName)`. Các ca còn lại về bộ lọc Công ty và nhãn "Vườn".

**`tests/fixed-select-stt.test.js`** (5 ca), regex nguồn trên `DataTable.vue`: `return [select,sttDef,...body]`; `:column-defs="gridDefs"`; `pinned:'left',lockPinned:true,lockPosition:'left',suppressMovable:true`; chuỗi `state:[{colId:nativeSelectId.value||'__lotus_select',pinned:'left',hide:false,width:42},{colId:'__lotus_stt',pinned:'left',width:52}`; `const getSelectionId=row=>gridRowId(row,props.rowKey)`; `setRowSelected(row,!selectedIds.value.has(getSelectionId(row)))`; `event.preventDefault();event.stopPropagation()`; `props.rowIndexOffset+params.node.rowIndex+1`; `isPaginated.value?(api.paginationGetCurrentPage?.()||0)*currentPageSize.value:0`; `const activeColumns=computed(()=>activeDisplayColumns.value.filter`; `const bytes=buildXlsx(activeColumns.value,records)`; không được có `props.columns.unshift(`. `ListPage.vue` chứa `:row-index-offset="paged?start:0"`. `FarmLandApp.vue` không có `field:'__picked'`, có `:selected-row-keys="[...picked]"` và 2 listener chọn.

**`tests/column-visibility.test.js`** (5 ca):
- 3 ca logic `grid-visibility.js`: di trú khoá cũ `lotus-grid-hidden:`; tách theo bảng; không ẩn hết; bỏ cột kỹ thuật; ghim tối đa 2; di chuyển/ghim không đổi mảng gốc.
- Excel theo cột đang hiện và thứ tự tuỳ chỉnh, không có cột khoá.
- `ColumnVisibilityMenu.vue` chứa nguyên văn `v-model="query" type="search"`, `lotus-column-picker__toggle`, CSS `grid-template-columns:minmax(0,1fr) 28px 28px 28px`, `@click="emit('pin',columnId(col))"`, `@click="emit('move',columnId(col),-1)"`; không được có `type="checkbox"`. `DataTable.vue` chứa `applyColumnState({state:[` và `applyOrder:true`. `StockLedger.vue` chứa `:column-presets="columnPresets"`.

**Test ngoài danh sách nhưng cũng khoá bảng**:
- `tests/excel-export.test.js`: XLSX có tiêu đề tiếng Việt, số không làm tròn (`<c r="B2"><v>250.75</v></c>`), không có công thức, `autoFilter ref="A1:D2"`; `DataTable.vue` chứa "Xuất Excel", `const records=[]`, `forEachNodeAfterFilterAndSort`.
- `tests/ui-stack.test.js:77-91`: `OpsList.vue` khớp `<DataTable [^>]*interactive[^>]*@open="emit('open',$event)"` và không chứa `ag-grid`; `DataTable.vue` chứa `from 'ag-grid-vue3'`, `import '../grid-modules.js'`, `@row-clicked="open"`, `emit('open',event.data)`, `lotus-mobile-records`; `grid-modules.js` có `ClientSideRowModelModule` và không import `AllCommunityModule`.
- `tests/warehouse-hr-link.test.js:32-36`: `warehouse-table-center.css` phải chứa `.stock-shell .lotus-ag-grid .ag-cell`, `text-align:center`, `.excel-sort` (tên test: "all StockApp table cells and headers are center-aligned").
- `tests/stock-filter-overhaul.test.js:33` và `tests/stock-actions-uom-columns.test.js:13-16`: `ExcelHeader.vue` chứa `excelAppliedValues(choices.value, selected.value)` và `excelPopupLeft(rect.right, width, window.innerWidth)`.
- `tests/hr-employee-table.mount.test.js:32-38,70-72`: lấy `querySelector('.lotus-ag-grid').__vueParentComponent.proxy`, đọc `$props.columnDefs`, gọi `headerComponentParams.apply([...])`, phát `row-clicked`; thẻ không `interactive` có `tagName` `ARTICLE`.
- `tests/forecast-source-form.mount.test.js:69-70`: lấy `.lotus-data-table` → `__vueParentComponent.proxy.$emit('open',row)`.
- Dùng selector lưới thật `.ag-row[row-id]`, `.ag-cell[col-id]`, `.ag-row:not(.ag-row-pinned)`, `.ag-header`, `.ag-header-cell[col-id="day_N"]`, `.lotus-grid-select-header button`, `.lotus-mobile-record > strong`: `farm-land`, `field-reports`, `finance`, `financial-planning`, `hr-audit-fixes`, `hr-payroll`, `onedrive-supply`, `packhouse-shifts`, `reports-workspace`, `ribbon-board`, `timekeeping-period`, `user-access`, `device-panel` (đều `.mount.test.js`).
- `tests/form-standard.mount.test.js:84-92`: `section.lotus-list-page[aria-label]`, `.workspace-list-toolbar input[type=search]`, `.lotus-pagination` chứa "1–1 / 120". `tests/form-standard.test.js:8-19`: template `ListPage.vue` không có `<input|select|textarea>` gốc.
- `tests/design-tokens.test.js:40-53`: không mã hex đục (trừ trắng/đen và hex 4/8 chữ số) trong `src/*.css`, `src/*.vue`, `src/components/*.vue`. Không quét thư mục con của `components/` và không quét `.js`.

## Ràng buộc phải giữ

1. **Quy ước chủ vườn trong `AGENTS.md`**: bảng gọn, không tiêu đề lớn, breadcrumb, mô tả, nhóm chọn mật độ phía trên bảng (`:3-6`); header cố định trên, dòng tổng cố định dưới, chỉ thân bảng cuộn, vỏ bọc không tạo vùng cuộn dọc thứ hai (`:7`); thanh lọc máy tính một hàng (`:8`); màu chỉ từ `lotus-tokens.css` (`:12`); dùng primitive `components/ui`, không tự viết popover/menu, nội dung nổi trong modal phải render trong `<dialog>` (`:16-17`); bảng dùng DataTable, OpsList là lớp bọc, icon dùng `LotusIcon` (`:18`); component có hành vi phải có test mount (`:20`).
2. **Hiến chương** (`.specify/memory/constitution.md`): I — không tạo số giả, thiếu dữ liệu thì cảnh báo: quy tắc dòng tổng (không cộng đơn giá, không cộng lẫn đơn vị, `grid-totals.js`) và ký hiệu trống `—` phải giữ nguyên nghĩa. IV — quy tắc tính nằm ở module thuần có unit test (`grid-*.js`, `excel-*.js`, `table-pagination.js`). V — toàn bộ chữ tiếng Việt.
3. **Không bật sửa ô của AG Grid** khi chưa có API kiểm quyền và đối soát (`docs/UI_STACK.md:31`). Nhập trong ô hiện đi qua slot/renderer do màn hình tự quản.
4. **Chỉ dùng bản Community** (`frontend/package.json` không có `ag-grid-enterprise`), đăng ký từng module (`grid-modules.js`), không import `AllCommunityModule` (`tests/ui-stack.test.js:87`). Row grouping, tree data, master-detail, pivot, cell selection, sparkline của AG Grid thuộc bản Enterprise.
5. **API công khai**: 34 props, 11 emits, slot `cell-<field>`/`cell`/`empty-actions`, cơ chế thuộc tính rơi từ `ListPage`/`OpsList` xuống DataTable. 178 thẻ ở 54 tệp phụ thuộc; đổi tên hay đổi mặc định là đổi 54 tệp.
6. **Hợp đồng DOM mà test dựa vào**: gốc `.lotus-data-table` là phần tử gốc của DataTable; `.lotus-ag-grid` là gốc của `AgGridVue`; `.lotus-ag-grid-shell` và `--scroll`; `.lotus-data-table__export`, `.lotus-data-table__selected` + `button`; cột `__lotus_select` và `__lotus_stt` với nút `aria-pressed`, class `is-partial`, `.lotus-grid-select-header`, `.lotus-grid-native-select-header`; `.lotus-mobile-records`, `.lotus-mobile-record-entry`, `.lotus-mobile-record` (BUTTON khi `interactive`, ARTICLE khi không, không nút lồng), `.lotus-mobile-record > strong`, `.lotus-mobile-record-detail`, `.lotus-mobile-total dt`; `.lotus-pagination`, `.lotus-pagination__range`, `select[aria-label="Số dòng mỗi trang"]`, `[aria-label="Trang sau"]`, nút "Hiện toàn bộ" không có `aria-label`; `.workspace-list-row .workspace-list-tools`; `section.lotus-list-page`. Chữ: "N dòng đã chọn", "Xuất Excel", "Chọn dòng", "Hiện toàn bộ", "Tổng (N dòng)".
7. **Thẻ và lưới phải cùng có trong DOM** chừng nào test mount còn đếm `.lotus-mobile-record-entry` và `.ag-row` trong cùng một lần mount (`tests/pagination-size.mount.test.js:23-25`).
8. **Chuỗi mã nguồn bị regex khoá** (mục 19): tên biến `selectDef`, `sttDef`, `gridDefs`, `activeColumns`, `getSelectionId`; bề rộng 42/52; `<Teleport to="body">` trong `ExcelHeader.vue`; `grid-template-columns:minmax(0,1fr) 28px 28px 28px` trong `ColumnVisibilityMenu.vue`; hai điều kiện `v-if` của `Pagination.vue`; `.tk-roster{overflow:visible;padding:0}`. Sửa các tệp này phải sửa test trong cùng thay đổi.
9. **Quy tắc riêng của Kho đã nghiệm thu**: ô và header căn giữa (`tests/warehouse-hr-link.test.js:32-36`); có viền dọc cột và viền ngang dòng (`docs/WAREHOUSE_EXCEL_FILTER_UX.md:7`, `tests/excel-filter-ux.test.js:71-73`); popup lọc neo bên phải nút lọc (`docs/WAREHOUSE_EXCEL_FILTER_UX.md:30`).
10. **Cột Chọn đứng đầu, STT thứ hai trên mọi bảng** (`tests/fixed-select-stt.test.js:10-17`); STT theo thứ tự lưới và cộng offset trang server; hai cột này không vào "Cột hiển thị" và không vào Excel. Một trang vẫn hiện khoảng dòng, không hiện nút Trước/Sau bị khoá (`tests/timekeeping-grid-layout-audit.test.js:32-35`).
11. **Cờ cột mới phải thêm vào `GRID_APP_KEYS`** (`tests/grid-app-keys.test.js`), nếu không test AST báo lỗi và AG Grid cảnh báo #307.
12. **Khoá localStorage và giá trị `storage-key`** (103 thẻ + 16 qua ListPage): đổi tiền tố hay đổi key là mất bề rộng, cột ẩn, chế độ xem người dùng đã lưu trên trình duyệt.
13. **PWA điện thoại tách riêng**: Vant 4 + `LotusMobile*`; `WarehouseMobile.vue` không được tham chiếu DataTable/UiButton (`tests/warehouse-mobile-standalone.test.js:15`). Chế độ thẻ của DataTable chỉ phục vụ app máy tính `/lotus` ở màn hẹp.
14. **Hướng dẫn của chủ vườn ngày 09/11/2026** (ghi nhớ phiên làm việc): trang chính gọn, bấm mới mở modal để nhập hoặc xem chi tiết, không trải phẳng cả bảng. Bảng nằm trong modal là trường hợp chính, không phải ngoại lệ.

## Điểm yếu

### A. Sai lệch chức năng đọc được từ mã

1. **`selectionEnabled=false` không bỏ cột Chọn trên lưới.** Prop chỉ được đọc ở `DataTable.vue:333-334` (thẻ điện thoại); `gridDefs` (`:273-280`) luôn chèn cột chọn. 4 nơi đang truyền `false`: `components/field/CareDueList.vue`, `PackhouseShifts.vue`, `RibbonBoard.vue`, `components/report/ReportCards.vue`.
2. **`pinned:'right'` bị bỏ.** `DataTable.vue:74` và `:142` chỉ đặt `'left'` hoặc `null`; `grid-visibility.js:44` chỉ nhận `'left'|true`. Hai nơi khai ghim phải không có tác dụng: `components/finance/FinanceAssets.vue:55` (cột thao tác), `components/finance/FinanceMasterImport.vue:22` (cột lỗi).
3. **`:pagination="false"` không phải prop** (`components/finance/FinanceAssets.vue:238`); prop đúng là `paginate`. Thuộc tính rơi xuống `div` gốc, phân trang vẫn bật.
4. **Bốn phần nổi của bảng đều teleport ra `body`**, trái `AGENTS.md:17`: popup lọc (`ExcelHeader.vue:98`), "Cột hiển thị" (`ColumnVisibilityMenu.vue:26`, không truyền `to`; `ui/popover/PopoverContent.vue:6` mặc định `'body'`), "Lưu chế độ xem" (`DataTableViews.vue:30`), menu "Chế độ xem" (`ui/dropdown-menu/DropdownMenuContent.vue:5`). `ui/portal-target.js:2-3` ghi rõ nội dung teleport ra `body` không bấm được khi modal `<dialog>` đang mở. 30 tệp có cả DataTable/ListPage lẫn `WorkspaceModal`/`ModalForm` (không phải bảng nào trong đó cũng nằm trong modal; có test xác nhận bảng trong `dialog` ở `tests/packhouse-shifts.mount.test.js:64`, `tests/ribbon-board.mount.test.js:65`, `tests/field-reports.mount.test.js:43`). Mức ảnh hưởng thực tế: chưa kiểm trên trình duyệt.
5. **Không có chỉ báo chiều sắp xếp** (`ExcelHeader.vue:94`; grep trạng thái sort = 0). Người dùng không thấy cột nào đang sắp, tăng hay giảm.
6. **Thẻ điện thoại không theo sắp xếp và không có nút sắp xếp.** Thẻ lặp theo thứ tự dữ liệu gốc (`DataTable.vue:103`); nút sắp bị ẩn ở ô lọc điện thoại (`attio.css:105`).
7. **Cột thao tác bị coi như cột dữ liệu.** `FinanceApp.vue:316-360` có 10 cột `headerName:''` (`__source`, `__view`, `__pay`…): vẫn nhận header có nút sắp và nút lọc (`aria-label="Lọc cột "`), hiện trong "Cột hiển thị" bằng id kỹ thuật (`ColumnVisibilityMenu.vue:46` dùng `col.headerName||columnId(col)`), và được xuất Excel thành cột rỗng tên `__pay`… (`excel-export.js:30,34`; không cột nào đặt `suppressExport`).
8. **Bảng công tháng mất màu trạng thái.** `TkMonthSheet.vue:29` gắn `is-ok/is-half/is-leave/is-draft/is-warn` vào ô AG Grid (`div.ag-cell`), nhưng CSS viết cho `td` (`timekeeping.css:123-128`: `.tk-sheet td.is-ok`…). Chỉ `.tk-sheet .is-off` và `.is-holiday` (`:121-122`) còn khớp. Chưa kiểm trên trình duyệt.
9. **Vỏ bọc tạo vùng cuộn thứ hai**, trái `AGENTS.md:7`: `.tk-sheet{overflow:auto;max-height:70vh}` bọc DataTable (`timekeeping.css:110`, `TkMonthSheet.vue:38-39`); `.lotus-chart-table{max-height:320px;overflow:auto}` bọc DataTable (`workspace-experience.css:271`, `components/LotusChart.vue:84`).
10. **Chế độ tối có nền trắng ghi cứng.** `attio.css:107` đặt thẻ `background:#fff;color:var(--lotus-text)`; ở `.dark` chữ là `#eceef2` trên trắng, tương phản khoảng 1,16:1. Tương tự: `attio.css:70` (khung lưới), `compact.css:287` (hover giá trị lọc `--lotus-neutral-50`), `compact.css:292` (nút chân popup `#fff`), `stock-overview.css:37` (nút lọc Kho `#fff`), `LotusGridEditCell.vue:23` (`select` nền `#fff`). Không có rule `.dark` nào cho `.lotus-mobile-record`, `.lotus-ag-grid-shell`, `.lotus-excel-popup` (grep). Chưa kiểm trên trình duyệt.
11. **Logic nghiệp vụ Kho nằm trong component chung**: thiếu `rowClass` thì mọi bảng có trường `shortage_qty>0` đều tô `lotus-shortage-row` (`DataTable.vue:330`).
12. **`DataTableViews` không theo dõi `storageKey`**: `views` chỉ đọc một lần lúc khởi tạo (`DataTableViews.vue:14`). Bảng đổi `storage-key` động mà không remount (`FinanceApp.vue` dùng `'fin-'+report`, `ReportCards.vue` dùng `storageKey+'-'+opened.key`) có thể hiện danh sách chế độ xem của bảng trước. Chưa kiểm.
13. **Hai cách định danh cột trái thứ tự nhau, viết ở 4 tệp**: `field||colId||headerName` (`DataTable.vue:44`, `excel-export.js:7`) và `colId||field||headerName` (`grid-visibility.js:4`, `grid-format.js:22`). Slot, bộ lọc, dòng tổng theo định nghĩa thứ nhất; ẩn/hiện, ghim, thứ tự theo định nghĩa thứ hai. Cột có cả hai key khác nhau (`LandBlockDetail.vue:63`: `field:'name',colId:'actions'`) bị lệch.
14. **Bảng thiếu `storage-key` dùng chung trạng thái**: 27 thẻ DataTable ở màn hình (16 ở `OneDriveProcessWorkspace.vue`), toàn bộ 28 bảng OpsList (`OpsList.vue:34` không truyền), 2 thẻ ListPage (`FinanceApp.vue`, `ProcurementCompare.vue`). Khoá khi đó là chuỗi nối tên trường (`DataTable.vue:114`), nên hai bảng cùng bộ cột dùng chung bề rộng, cột ẩn và chế độ xem. `LotusChart.vue:84` đặt cùng một khoá `chart-data-table` cho mọi biểu đồ dù cột khác nhau.
15. **Kéo đổi vị trí cột trên lưới không được lưu**: DataTable không nghe `column-moved` (danh sách listener ở `DataTable.vue:330`); thứ tự chỉ đổi qua nút lên/xuống trong "Cột hiển thị". Lần áp layout kế tiếp đặt lại thứ tự (`applyOrder:true`, `:142`). Kéo header có chạy được với header tuỳ biến hay không: chưa kiểm.
16. **`ListPage` chỉ chuyển tiếp slot `cell-*`** (`ListPage.vue:14`): `empty-actions` và `cell` không tới được DataTable.
17. **Payload `cell-open` khác nhau** giữa máy tính và thẻ (`DataTable.vue:330` và `:338`); trên thẻ, cột nào có `colId` cũng thành nút liên kết dù màn hình không nghe `cell-open` (ví dụ 31 cột ngày `colId:'day_N'` của `TkMonthSheet.vue:27`).

### B. Không nhất quán, trùng lặp

1. **CSS của bảng nằm ở 13 tệp `.css` toàn cục và 1 tệp `.vue` màn hình, ngoài style của chính các component bảng** (bảng ở mục 5). Tham số theme chỉ dùng 12; các thứ theme làm được lại ép bằng `!important`: padding ô và header (`DataTable.vue:357-358`), nền và độ đậm dòng ghim (`:394`), viền cột ghim (`:361`). Types 36.2.0 có sẵn `cellHorizontalPadding`, `pinnedRowBackgroundColor`, `pinnedRowFontWeight`, `pinnedColumnBorder`, `headerFontWeight`, `headerFontSize`, `wrapperBorderRadius`, `rowBorder`, `columnBorder`, `oddRowBackgroundColor`, `selectedRowBackgroundColor`, `headerCellHoverBackgroundColor`, `focusShadow`.
2. **Chiều cao khung cuộn khai 5 lần + 1 inline**: `attio.css:71` (520px), `compact.css:137` (`clamp(280px,100dvh−270px,680px)`), `:152` (Kho), `:165` (hộp thoại Kho), `:216` (Kho có thanh thao tác), và `style` inline khi `fill ≥ 0` (`DataTable.vue:330`).
3. **Header khai kiểu ở 6 nơi, độ đậm lệch nhau**: tham số theme; `DataTable.vue:358`; `attio.css:77-78` (600); `compact.css:3,54-58` (600); `desktop-system.css:54-57` (650, chỉ ≥ 901px); `stock-overview.css:22-33`.
4. **Bo góc khung bảng 5 giá trị**: 8px (`attio.css:70`), 9px (`desktop-system.css:53`, `attio.css:100`), `7px 7px 0 0` (`compact.css:151`), `0 0 9px 9px` (`timekeeping.css:49`), `--lotus-radius-md` (`timekeeping.css:57`). Token chỉ có 6/8/10/12/16 (`lotus-tokens.css:45`).
5. **Điểm gãy lệch nhau quanh bảng**: 640px (cụm công cụ, `DataTable.vue:384`), 650px (lưới → thẻ, `attio.css:86`), 700px (Kho lưới → thẻ, `compact.css:223`), 721px (phân trang chừa chat, `Pagination.vue:50`), 901px (mật độ, `use-desktop-workspace.js:5`; header, `desktop-system.css:4`).
6. **Căn lề số ba kiểu** (mục 16). Cột số tự định dạng nhưng không khai `numericColumn` thì căn trái; Kho căn giữa cả số.
7. **Trạng thái trong ô có 6 họ class đổi màu chữ và 1 pill riêng** (bảng ở mục 18). Không có chip dùng chung. `src/components/ui/badge` không được import ở đâu (grep).
8. **Định dạng viết tay lặp lại**: 231 `valueFormatter` ở 43 tệp; 13 cặp chữ khác nhau cho giá trị hai trạng thái; `toLocaleString('vi-VN'` 55 lần ở 45 tệp (mục 16).
9. **Popup lọc được style hai lần** cho cùng một phần tử mang hai class (`compact.css:59-66,115-118` cho `.excel-popup`; `:270-293` cho `.lotus-excel-popup`): `z-index` 100 và 2147483000, bề rộng 272px trong CSS và 312px inline.
10. **`.lotus-data-table__export` khai hai lần trong cùng tệp** với `gap` và `margin` khác nhau (`DataTable.vue:359` có `!important`, `:381` không).
11. **Trái quy ước primitive và icon** (`AGENTS.md:16-18`): `ExcelHeader.vue` dùng `<button>`, `<input type=checkbox>`, `<input type=search>` gốc và tự định vị popup; `LotusGridEditCell.vue:9,15,18` dùng `select`/`button`/`checkbox` gốc với kiểu riêng; ký tự làm icon: `▾` (`ExcelHeader.vue:97`), `✓` (`DataTable.vue:229,334`). Test "icons are icons" chỉ dò một tập ký tự cố định nên không bắt được (`tests/design-tokens.test.js:89`).
12. **Mật độ chỉ áp cho 2 phân hệ** (mục 6): cùng một bảng dùng chung nhưng Kho 40px, Tài chính 34px.
13. **Hai hệ bảng, hai lược đồ cột**: DataTable (colDef AG Grid, `headerName`) và `LineItemsEditor` (`label`, `type`, `width`), cùng tên slot `cell-<field>` nhưng scope khác (`{row,value,params,column}` so với `{row,index,column}`).
14. **Thanh công cụ ListPage xuống dòng** (`workspace-experience.css:121` `flex-wrap:wrap`; chú thích `WorkspaceListToolbar.vue:6`, `ListPage.vue:35`), trong khi `AGENTS.md:8` yêu cầu một hàng và cuộn trong thanh; chỉ Chấm công đặt `nowrap` + `overflow-x:auto` (`timekeeping.css:50-51`).

### C. Mã chết, tài liệu lệch

1. `import {themeQuartz}` không dùng (`DataTable.vue:8`).
2. Các giá trị cỡ chữ/dòng/header/spacing trong `grid-theme.js:2-6` luôn bị `DataTable.vue:29` ghi đè; sau khi ghi đè ba theme cho kết quả như nhau, hai biến thể trong `desktopGridThemes` là thừa.
3. Prop không có nơi dùng: `hiddenColumns`, `emptyHint`. Slot không có nơi dùng: `empty-actions`, `cell`. Cờ không có nơi dùng: `autoHide`, `groupNumbers`, `filterable`. `mobileLimit` chỉ OpsList dùng.
4. CSS chết: `.lotus-grid-footer` (`attio.css:80,114`; 0 nơi dùng); `.excel-popup[popover]` (`compact.css:117-118`; popup không còn dùng thuộc tính `popover`); rule `table/th/td` bên trong vỏ nay chỉ chứa DataTable: `timekeeping.css:111-120` (`.tk-sheet`, chỉ `TkMonthSheet.vue:38` dùng) và `workspace-experience.css:272-274` (`.lotus-chart-table`). Rule `th/td` chung ở `compact.css:3` và `desktop-system.css:58-59` nhiều khả năng cũng chết vì không tệp `.vue` nào còn `<table>` (bảng HTML chỉ còn sinh từ `ai-markdown.js`): chưa kiểm.
5. Ghi song song khoá cũ `lotus-grid-hidden:` mỗi lần lưu layout (`grid-visibility.js:50`).
6. `docs/COMPACT_WORKSPACE.md:4` ghi theme 36px; thực tế 34/40. `docs/LOTUS_DESKTOP_UI_STANDARD_20261017.md:5` ghi `grid-theme.js` giữ khoảng cách hàng; thực tế `DataTable.vue:29` quyết định.
7. `src/pivot-filter.js` được nêu trong phạm vi nhưng đã bị xoá.

### D. Truy cập, tương phản, vùng chạm

1. **Hover, nền header và dòng tổng cùng một màu gần trắng.** `rowHoverColor`, `--lotus-table-header`, nền dòng tổng đều là `--lotus-neutral-25` `#fcfbfa` trên nền `#fff` (`lotus-tokens.css:22,25`; `grid-theme.js:2`; `DataTable.vue:394`). Tỉ lệ tương phản tính theo công thức WCAG ≈ 1,03:1. Không có zebra. Dòng được chọn không đổi nền (chỉ ô tick đổi).
2. **Viền focus dưới 3:1 và hai màu focus.** Hàng: `box-shadow` `--lotus-info-300` `#8fb2e3` trên trắng ≈ 2,2:1 (`attio.css:79`). Thẻ: `outline` `--lotus-info-200` `#bdd2f0` ≈ 1,5:1 (`attio.css:109`). Ô đang focus của AG Grid dùng `accentColor` đỏ. Token `--lotus-focus` (`lotus-tokens.css:36`) không được bảng dùng.
3. **Vùng chạm nhỏ hơn `--lotus-touch:44px`** (`lotus-tokens.css:47`): nút chọn 20×20 kể cả trên thẻ điện thoại (`DataTable.vue:365,334`); nút lọc header 20×22 (`compact.css:57`), Kho 22×25 (`stock-overview.css:37`); nút bỏ chip 22×22 (`DataTableViews.vue:48`); nút ghim/di chuyển cột 27×29 (`ColumnVisibilityMenu.vue:85`); nút phân trang 32×32 và ô cỡ trang cao 32 (`Pagination.vue:41,44`) không có biến thể cho màn hẹp. Riêng nút lọc trên điện thoại 40×40 (`attio.css:106`).
4. **Chữ 10–11px**: header 11px (`compact.css:55`), nhãn–giá trị trên thẻ 11px (`attio.css:111`), mã vật tư 10px (`compact.css:159`), chân popup "Cột hiển thị" 11px. Trong các style của bảng có 33 khai báo `font-size` bằng px và 5 khai báo bằng token.
5. **Thẻ `<article>` bấm được nhưng không focus được**: `@click` mở chi tiết, không có `tabindex`, `role`, xử lý phím (`DataTable.vue:335`).
6. **Popup lọc** có `role="dialog"` nhưng không giữ focus bên trong, không `aria-modal`, danh sách giá trị không điều hướng bằng mũi tên (`ExcelHeader.vue:99-119`). Hành vi Tab thực tế: chưa kiểm.
7. **Không có CSS in** cho bảng: `@media print` = 0 trong toàn `src`.
8. Điều hướng bàn phím trong lưới (mũi tên, Tab, Enter) dựa vào lõi AG Grid; nút trong header tuỳ biến và nút chọn có tới được bằng bàn phím hay không: chưa kiểm.

### E. Giá trị ghi cứng

- `DataTable.vue` style: 50 giá trị px, 36 `!important`, 30 tham chiếu token. `ColumnVisibilityMenu.vue` style: 78 giá trị px, 72 `!important`, 22 tham chiếu token.
- Chiều cao dòng/header là số trong JS (`DataTable.vue:29`), không lấy từ `--lotus-row`.
- Bề rộng cột tiện ích 42 và 52, `minWidth` mặc định 90, ngưỡng "trên 10 dòng thì cuộn", 56px chừa cho phân trang, 280px tối thiểu: đều là hằng số rải trong `DataTable.vue:74,94,102,260,264`.
- Hex ngoài token không bị test bắt vì nằm trong template: `'#4b5563'` (`RosterGridCell.vue:17`).
- Bóng đổ viết tay thay vì `--lotus-shadow-*`: `0 12px 36px #0004` (`compact.css:59`), `0 18px 48px #15223b36` (`compact.css:272`).
- Popup lọc dùng bậc thang `--lotus-neutral-200/300/50/700` thay cho token ngữ nghĩa (`compact.css:270-293`).

### F. Hiệu năng

1. **Lưới bị huỷ và dựng lại mỗi khi tập dòng đổi**: `:key="rowIdentity"` (`DataTable.vue:330`), `rowIdentity` là chuỗi nối id mọi dòng (`:55`). Mất vị trí cuộn và ô đang focus sau mỗi lần lọc hay tải lại.
2. **Mỗi dòng được vẽ hai lần** (ô lưới + thẻ), thẻ không ảo hoá. "Hiện toàn bộ" vẽ thẻ cho mọi dòng dù đang ẩn bằng CSS (`:103,333`).
3. **Danh sách giá trị lọc tính sẵn cho mọi cột** mỗi lần `defs` tính lại (`:54,74`): duyệt toàn bộ `rows` và sắp xếp cho từng cột, dù chưa mở popup nào.
4. **Mỗi header đăng ký 4 listener toàn cục** lúc mount (`ExcelHeader.vue:78-83`), kể cả khi popup đóng; nhân với số cột đang vẽ và lặp lại sau mỗi lần dựng lại lưới.

## Thiếu so với một bộ giao diện đầy đủ

| Hạng mục | Đang có | Còn thiếu |
|---|---|---|
| Chip trạng thái trong ô | Đổi màu chữ bằng `cellClass` (6 họ class); 1 pill cục bộ `.tk-pill` (`TimekeepingGridCell.vue:28`, `timekeeping.css:84-88`) | Chip dùng chung theo tông (thành công, cảnh báo, nguy hiểm, thông tin, trung tính), bảng ánh xạ trạng thái → tông, dùng lại được trên thẻ và trong Excel |
| Ô tiến độ / thước đo | Không có. `resolved_percent` ("% xử lý", `OpsList.vue:15`) và `completed_qty`/`planned_qty` là chữ | Ô thanh tiến độ có số, ngưỡng màu |
| Avatar | Không có trong ô (chỉ ở chat và thanh trên) | Ô người: chữ cái đầu + tên + dòng phụ |
| Sparkline | Không có (grep = 0). Sparkline của AG Grid là Enterprise | Ô SVG nội tuyến cho xu hướng theo tuần |
| Nhóm dòng | Không có. Thụt lề bằng khoảng trắng (`FinanceApp.vue:151`, `ErpReport.vue:55`); cây dùng `MasterTree.vue` riêng | Dòng tiêu đề nhóm thu gọn được, tổng phụ theo nhóm |
| Cột đầu dính | Ghim trái qua menu (tối đa 2) hoặc `pinned:'left'` trong colDef (6 nơi); STT + Chọn luôn ghim (94px) | Ghim phải cho cột thao tác; quy ước tự ghim cột định danh |
| Zebra / hover / focus / chọn | Không zebra; hover 1,03:1; focus dưới 3:1; dòng chọn không tô | Token nền riêng cho hover, zebra, dòng chọn, dòng tổng; một kiểu focus |
| Chuyển mật độ | Composable 2 mức, không có nút, chỉ 2 phân hệ | Một nguồn mật độ cho mọi phân hệ; chỗ đặt nút không vi phạm `AGENTS.md:3` |
| Ghim cột | Trái, tối đa 2, lưu theo trình duyệt | Phải; kéo-thả có lưu |
| Bàn phím | Lõi AG Grid (chưa kiểm); Enter mở dòng (`DataTable.vue:330`); Escape đóng popup lọc | Phím tắt chọn dòng; thẻ focus được; popup giữ focus; `aria-sort` |
| Khung xương khi tải | 5 thanh ngang trước lần tải đầu; lớp phủ AG Grid khi tải lại | Khung xương theo cột, giữ header và bề rộng cột |
| Chế độ thẻ màn hẹp | Có: tiêu đề = cột đầu, cặp nhãn–giá trị, tổng, lọc theo cột | Vai trò cột (tiêu đề, phụ đề, chip, ẩn); sắp xếp; chọn cả trang; vùng chạm 44px; slot thẻ; ảo hoá |
| Chỉ báo sắp xếp | Không có | Icon + thứ tự khi sắp nhiều cột |
| Thao tác hàng loạt | Chỉ đếm "N dòng đã chọn" và "Bỏ chọn" | Thanh thao tác theo lựa chọn; xuất dòng đã chọn |
| Kiểu cột dựng sẵn | Không có (`columnTypes` = 0); mỗi màn tự viết formatter | Bộ dựng cột: chữ, số, tiền, số lượng + đơn vị, ngày, phần trăm, trạng thái, boolean, liên kết, thao tác |
| Cột thao tác | Slot nút hoặc renderer DOM, coi như cột dữ liệu | Kiểu cột riêng: không header lọc/sắp, không xuất, ghim phải, menu ⋯ |
| Tự co cột theo nội dung | Không (`ColumnAutoSizeModule` chưa đăng ký) | Bấm đúp mép cột để vừa nội dung |
| Lưu chế độ xem | Lọc + sắp, theo trình duyệt, 12 mục | Gồm cả cột/ghim/bề rộng/cỡ trang; theo tài khoản; chế độ xem mặc định |
| Xuất | XLSX thô: tiêu đề đậm, đóng băng, autoFilter | Định dạng số và ngày, dòng tổng, dòng tiêu đề + điều kiện lọc, chỉ dòng đã chọn; in |
| Trạng thái lỗi | Chỉ ở ListPage (`error`) | Lỗi tải trong DataTable kèm nút thử lại |
| Danh sách bản ghi cho PWA | Không có component chung trong `LotusMobile*` | Danh sách/thẻ bản ghi Vant dùng chung token và chip với máy tính |
| Trang mẫu | 1 bảng + 2 phân trang trong `UiShowcase.vue:56-60` | Trang mẫu đủ kiểu ô, 2 mật độ, sáng/tối, thẻ màn hẹp, bảng trong modal |

## Đề xuất cho bộ giao diện mới

Thứ tự: P0 thay da và sửa lỗi mà không đổi API; P1 thêm bộ ô và kiểu cột; P2 tính năng mới. Mục nào đổi hành vi đã nghiệm thu đều ghi "cần chủ vườn đồng ý".

### P0 — Nền tảng, giữ nguyên API và hợp đồng DOM

1. **Một nguồn kiểu dáng cho bảng.** Thêm nhóm token bảng vào `src/lotus-tokens.css` (cả `:root` và `:root.dark`): `--lotus-table-row`, `--lotus-table-row-comfortable`, `--lotus-table-header-height`, `--lotus-table-cell-padding`, `--lotus-table-hover`, `--lotus-table-zebra`, `--lotus-table-selected`, `--lotus-table-total`, `--lotus-table-border`, `--lotus-table-focus`. Hover, header, dòng tổng phải là ba mức nền phân biệt được.
2. **Viết lại `src/grid-theme.js` thành một hàm `lotusGridTheme(density)`** đọc token và đặt qua tham số theme: `rowHeight`, `headerHeight`, `fontSize`, `headerFontSize`, `headerFontWeight`, `cellHorizontalPadding`, `rowBorder`, `columnBorder`, `wrapperBorder`, `wrapperBorderRadius`, `oddRowBackgroundColor`, `rowHoverColor`, `selectedRowBackgroundColor`, `pinnedRowBackgroundColor`, `pinnedRowFontWeight`, `pinnedColumnBorder`, `headerCellHoverBackgroundColor`, `focusShadow` (đều có trong types 36.2.0). Bỏ `.withParams` ở `DataTable.vue:29` và các `!important` ở `:356-361,394`.
3. **Gom CSS của bảng về một chỗ** (style của các component bảng hoặc một tệp `src/data-table.css`): chuyển rule từ `attio.css:69-114`, `compact.css` (các dòng ở mục 5), `desktop-system.css:53-57`, `stock-attio.css:49`. Biến thể Kho (viền dọc, căn giữa) thành tuỳ chọn có tên của theme/bảng thay cho `stock-overview.css:22-41` và `warehouse-table-center.css`; cập nhật `tests/warehouse-hr-link.test.js` và `tests/excel-filter-ux.test.js:71-73` trong cùng thay đổi. Một quy tắc chiều cao khung, một điểm gãy lưới ↔ thẻ, bo góc theo token.
4. **Sửa các sai lệch ở mục A** kèm test mount: `selectionEnabled=false` bỏ cột Chọn trên lưới (A1); nhận `pinned:'right'` (A2); sửa `:pagination` ở `FinanceAssets.vue:238` (A3); phần nổi render trong `dialog[open]` bằng `useDialogPortal` (A4 — đổi chuỗi `<Teleport to="body">` nên phải sửa `tests/excel-filter-ux.test.js:55`); thêm chỉ báo sắp xếp và `aria-sort` (A5); CSS trạng thái của `TkMonthSheet` nhắm `.ag-cell` (A8); bỏ vỏ cuộn `.tk-sheet` và `.lotus-chart-table` (A9); nền theo token cho chế độ tối (A10); đưa quy tắc `shortage_qty` về `rowClass` của màn Kho (A11); `DataTableViews` theo dõi `storageKey` (A12); một hàm id cột dùng chung (A13).
5. **Thay ký tự bằng `LotusIcon`** (`▾`, `✓`) và thay điều khiển gốc trong `ExcelHeader.vue`, `LotusGridEditCell.vue` bằng primitive `components/ui` (Popover, Checkbox, Input, Button, Select).
6. **Dọn mã chết** (mục C): import thừa, biến thể theme, CSS chết, khoá localStorage cũ (giữ đọc để di trú, bỏ ghi). Với prop/slot/cờ 0 nơi dùng: quyết định giữ làm API chính thức hay bỏ, ghi vào hợp đồng.
7. **Viết hợp đồng** `specs/004-bo-giao-dien-agritech/contracts/data-table.md`: props, emits, slot, cờ cột, class DOM và chữ mà test dựa vào (mục "Ràng buộc" 5–8). Chuyển dần test regex nguồn sang test mount để lần sau đổi mã không phải sửa chuỗi.
8. **Mở rộng `tests/design-tokens.test.js`** quét cả thư mục con của `src/components/` và hex trong `:style` của template, trước khi thêm tệp mới vào thư mục con.

### P1 — Kiểu cột và bộ ô chuẩn

9. **Bộ dựng cột `src/grid-columns.js`** (module thuần, có unit test): `textCol`, `numberCol`, `moneyCol`, `qtyCol({unitField})`, `dateCol`, `dateTimeCol`, `percentCol`, `boolCol`, `statusCol(map)`, `linkCol`, `actionsCol`. Cột số tự căn phải và `tabular-nums`; `actionsCol` tự đặt `sortable:false`, không header lọc, `suppressExport`, `columnChooserLocked`, ghim phải. Chỉ sinh key AG Grid hoặc cờ trong `GRID_APP_KEYS`. Chuyển dần 231 `valueFormatter`, bắt đầu từ `FinanceApp.vue` (35 bảng), `stock-columns.js`, `OpsList.vue`. Căn lề số của Kho: cần chủ vườn đồng ý nếu đổi từ giữa sang phải.
10. **Bộ ô trong `src/components/table-cells/`**, mỗi ô có test mount và có dạng chữ cho dòng ghim, thẻ, Excel:
    - `StatusChipCell` — một bảng tông dùng `--lotus-success-soft`, `--lotus-warning-soft`, `--lotus-danger-soft`, `--lotus-info-soft`; thay `fin-cell-*`, `lotus-grid-status`, `lotus-grid-warn`, `lotus-coverage-state`, `fin-assets__status`, `tk-pill`.
    - `ProgressCell` — thanh + số; dùng cho % xử lý, hoàn thành/kế hoạch, đã thu/dự thu theo lô.
    - `DeltaCell` — tăng/giảm có dấu và màu; thay `stock-diff-*`, `fp-negative`.
    - `TwoLineCell` — tên + mã; thay `itemCell` (`stock-columns.js:9`).
    - `PersonCell` — chữ cái đầu + tên + tổ/chức danh; cho bảng nhân viên, chấm công, khoán.
    - `LotCell` — mã lô + chấm màu khu, dùng `--lotus-map-zone-a…f` (`lotus-tokens.css:34-35`).
    - `RibbonCell` — chấm màu dây buồng + tuần.
    - `SparklineCell` — SVG nội tuyến, không thêm thư viện.
    - `ActionsCell` — 1 nút chính + menu `DropdownMenu`.
11. **Thanh thao tác theo lựa chọn**: slot `#bulk-actions="{rows,ids,clear}"` cạnh "N dòng đã chọn"; tô nền dòng đã chọn; thêm "Xuất dòng đã chọn". Giữ vị trí cột Chọn/STT và class đã khoá.
12. **Mật độ một nguồn**: `provide('lotusDesktopDensity')` từ `App.vue` cho mọi phân hệ, giữ hai mức 34/40 bằng token. Chỗ đặt nút chuyển (menu tài khoản hoặc trong popover "Cột hiển thị", không phải phía trên bảng): cần chủ vườn đồng ý.
13. **Chế độ thẻ bản 2**: cờ `mobileRole` (`title|subtitle|badge|meta|hidden`) thêm vào `GRID_APP_KEYS`; slot `#mobile-card="{row}"`; ô "Sắp xếp theo…"; nút chọn cả trang; vùng chạm 44px; chip trạng thái ở góc thẻ; thẻ `<article>` focus được. Giữ nguyên các class `.lotus-mobile-*`, quy tắc BUTTON/ARTICLE, không nút lồng.
14. **Trạng thái tải, trống, lỗi**: khung xương theo cột dưới header thật; prop `error` + nút "Thử lại" trong DataTable; ẩn ô "Dòng/trang" và "Hiện toàn bộ" khi tổng số dòng ≤ 20 (khoảng dòng vẫn hiện theo test) — cần chủ vườn đồng ý.

### P2 — Tính năng mới

15. **Nhóm dòng trên bản Community**: prop `groupBy` + dòng tiêu đề nhóm dạng full-width (`isFullWidthRow` + `fullWidthCellRenderer` có trong lõi 36.2.0, không cần module), thu gọn/mở, tổng phụ dùng lại `grid-totals.js`. Ưu tiên nhóm theo Khu → Lô, Tổ, Nhà cung cấp, Tháng. Trên thẻ: tiêu đề nhóm dính.
16. **Không dựng lại lưới khi dữ liệu đổi**: thử bỏ `:key="rowIdentity"`, cập nhật `rowData` với `getRowId` để giữ vị trí cuộn và focus; tính danh sách giá trị lọc khi mở popup; gắn listener toàn cục của `ExcelHeader` chỉ khi popup mở. Phải chạy lại `tests/data-table-lifecycle-26.mount.test.js` và các test slot (chưa kiểm tác động).
17. **Lưu trạng thái theo tài khoản**: một bản ghi `{layout, widths, views, pageSize, density}` cho mỗi `storage-key`, có số phiên bản, di trú từ 5 khoá localStorage hiện tại; chế độ xem gồm cả cột, ghim, bề rộng. Bắt buộc `storage-key` (cảnh báo khi DEV); bổ sung cho 27 thẻ DataTable ở màn hình, 2 thẻ ListPage, `OpsList.vue:34`, và tách khoá ở `LotusChart.vue:84`.
18. **Xuất và in**: thêm style số (phân cách nghìn, số lẻ theo kiểu cột) và kiểu ngày vào `excel-export.js`; tuỳ chọn dòng tổng; dòng tiêu đề gồm tên bảng, điều kiện lọc, ngày xuất; bỏ cột thao tác; `@media print` cho bảng (ẩn công cụ, lặp header).
19. **Danh sách bản ghi cho PWA**: component Vant `LotusMobileRecordList` trong `src/components/`, dùng chung token, bảng tông trạng thái và `mobileRole` với DataTable; không import DataTable hay AG Grid.
20. **Trang mẫu và kiểm thử**: thêm mục "Bảng" trong `UiShowcase.vue` trình bày mọi kiểu ô, 2 mật độ, sáng/tối, thẻ màn hẹp, bảng trong `WorkspaceModal`; mỗi ô và mỗi sửa lỗi ở P0 có test mount qua `tests/support/mount.mjs`. Test chạy trên VPS hoặc GitHub Actions theo quy ước của máy này.

## Cách đếm

- Thẻ component: `grep -ro -E "<DataTable([[:space:]/>]|$)" --include=*.vue frontend/src | wc -l` (tương tự `ListPage`, `OpsList`, `LineItemsEditor`, `Pagination`).
- Thuộc tính trên thẻ: tách thẻ mở bằng `perl -0777` (178 thẻ) rồi đếm tên thuộc tính.
- Key cột: `grep -ro -E "(^|[{,[:space:]])<key>:" --include=*.vue --include=*.js frontend/src`; số ở "nơi dùng ở màn hình" đã trừ `DataTable.vue`, `grid-*.js`, `excel-export.js`.
- Slot `#cell-*`: quét bằng `perl`, gán mỗi slot cho thẻ `DataTable`/`ListPage`/`LineItemsEditor` bao ngoài gần nhất.
- Selector `.ag-*`: `grep -o -E '\.ag-[a-z-]+'` trên `*.css` và `*.vue`.
- Tương phản: công thức độ chói tương đối WCAG 2.x trên mã hex trong `frontend/src/lotus-tokens.css`.
- Tham số theme, module, tuỳ chọn lưới: đọc `dist/types/src` của `ag-grid-community` 36.2.0 (`theming/…`, `main.d.ts`, `entities/gridOptions.d.ts`, `entities/colDef.d.ts`).
