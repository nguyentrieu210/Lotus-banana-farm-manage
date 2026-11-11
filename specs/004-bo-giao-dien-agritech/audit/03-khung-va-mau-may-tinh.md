# 03 — Khung ứng dụng máy tính và các mẫu ghép

Rà soát ngày 10/11/2026 trên nhánh `004-bo-giao-dien-agritech` (commit `40f8330`). Chỉ đọc mã bằng Read, Grep, wc, sed, awk. Không chạy npm, build, test hay trình duyệt. Kết luận nào suy ra từ mã mà chưa nhìn trên trình duyệt được ghi **chưa kiểm**.

Quy ước đường dẫn: tên tệp trần (`App.vue`, `compact.css`) nằm ở `frontend/src/`; `components/…` là `frontend/src/components/…`; `tests/…` là `frontend/tests/…`; `docs/…` ở gốc repo. Số sau dấu hai chấm là số dòng. Với CSS, một "rule" là một khối `bộ chọn {…}`, đếm bằng script tách theo dấu ngoặc trên 21 tệp CSS của điểm vào máy tính.

## Hiện trạng

### 1. Công nghệ và điểm vào

- `frontend/package.json` (mục dependencies): Vue 3.5.43, vue-router 4.6.4, pinia 3.0.4, reka-ui 2.11.0, Tailwind 3.4.19 với preset `frappe-ui` 1.0.0 (`frontend/tailwind.config.js:1-6`), AG Grid 36.2.0, ECharts ^6.1.0, Vite 8.3.3, happy-dom 21.0.1.
- Máy tính có một điểm vào: `frontend/index.html` → `main.js` → `App.vue`, phục vụ ở `/lotus/*`. Bốn PWA dùng khung Vant riêng, không thuộc tài liệu này.
- `main.js:22` gắn Pinia và router rồi mount. Không có `<router-view>` (0 kết quả grep). Router chỉ giữ trạng thái URL; mọi route dùng chung component giữ chỗ (`router.js:8`). `App.vue` chọn màn bằng chuỗi `v-if` theo `page` (`App.vue:76`, `App.vue:231-239`).
- Ba cách tạo kiểu cùng tồn tại trong khung: lớp tiện ích Tailwind qua `cva` (`components/ui/button/index.js:5-23`) và viết thẳng trong template (`components/ReleaseNotes.vue:30-36`, `components/WorkspaceBar.vue:45`); CSS toàn cục không layer; khối `<style>` không scoped trong SFC (81/197 SFC có `<style>`, 13 SFC dùng `scoped`; 12 tệp trong phạm vi có `<style>`, không tệp nào scoped).

### 2. Kích thước các tệp trong phạm vi

| Tệp | Dòng | Byte | Vai trò |
|---|---:|---:|---|
| `App.vue` | 250 | 72.650 | Khung, 14 nhánh màn, 4 hộp thoại, nghiệp vụ chứng từ. Dòng 246 dài 13.383 ký tự |
| `router.js` | 45 | 3.335 | Route, `permittedRoute`, guard phiên |
| `store.js` | 12 | 2.249 | Pinia `session` và `scope` |
| `workspace.js` | 15 | 1.240 | Sáng/tối, thu gọn sidebar |
| `use-desktop-workspace.js` | 22 | 1.202 | Cờ desktop và mật độ |
| `domain.js` | 20 | 3.280 | `pages`, `titles`, `navGroups`, `moduleKey` |
| `workspace-routes.js` | 22 | 1.278 | `workspaceModules`, `internalWorkspaceTarget` |
| `workspace-directory.js` | 25 | 1.647 | Danh bạ liên kết cho ô chuyển phân hệ và tìm nhanh |
| `module-navigation.js` | 16 | 2.010 | `sectionedModules` |
| `hr-navigation.js` / `stock-navigation.js` / `procurement-navigation.js` / `finance-navigation.js` / `field-report-navigation.js` | 21 / 24 / 34 / 22 / 30 | 2.298 / 1.949 / 2.694 / 1.835 / 2.463 | Mục con của 5 phân hệ |
| `components/WorkspaceBar.vue` | 78 | 8.663 | Thanh đầu trang và bảng tìm nhanh |
| `components/WorkspaceSidebar.vue` | 93 | 5.979 | Thanh bên |
| `components/WorkspaceModal.vue` | 34 | 3.082 | Hộp thoại duy nhất |
| `components/WorkspaceConfirm.vue` | 10 | 874 | Hộp xác nhận |
| `components/WorkspaceListToolbar.vue` | 21 | 1.652 | Thanh công cụ danh sách |
| `components/WorkspaceScopeBar.vue` | 12 | 2.998 | Thanh phạm vi công ty/vườn/khu/lô/vụ/ngày |
| `components/WorkspaceTabs.vue` | 8 | 999 | Tab |
| `components/WorkspaceSummaryStrip.vue` | 3 | 236 | Dải số tổng |
| `components/WorkspaceLoading.vue` | 1 | 187 | Khung chờ khi nạp phân hệ |
| `components/ListPage.vue` | 37 | 3.207 | Trang danh sách chuẩn |
| `components/form/LotusField.vue` | 75 | 7.496 | Trường nhập chuẩn |
| `components/form/ModalForm.vue` | 37 | 3.038 | Hộp nhập chuẩn |
| `components/form/ResponsiveForm.vue` | 32 | 2.558 | Hộp nhập dùng chung máy tính và điện thoại |
| `components/form/LineItemsEditor.vue` | 66 | 5.608 | Bảng dòng chi tiết sửa tại chỗ |
| `components/form/FormGrid.vue` / `FormSection.vue` / `ReasonDialog.vue` | 10 / 19 / 12 | 659 / 1.304 / 812 | Lưới, khối có tiêu đề, hộp hỏi lý do |
| `components/SchemaForm.vue` | 54 | 5.786 | Biểu mẫu sinh từ schema DocType Lotus |
| `components/SearchSelect.vue` / `LinkPicker.vue` / `MonthPicker.vue` | 7 / 8 / 16 | 659 / 980 / 1.246 | Lớp bọc Combobox, chọn tháng |
| `components/DesktopEmptyState.vue` / `DesktopMetricCard.vue` / `DesktopPageHeading.vue` | 13 / 10 / 13 | 676 / 576 / 553 | Trạng thái trống, thẻ số, khối tiêu đề |
| `components/OverviewBoard.vue` / `ReleaseNotes.vue` | 30 / 40 | 3.481 / 1.957 | Bảng tổng quan, "Có gì mới" |
| `components/erp/ErpSection.vue` / `ErpList.vue` / `ErpForm.vue` / `ErpFields.vue` / `ErpChildTable.vue` / `ErpReport.vue` | 58 / 53 / 192 / 106 / 54 / 91 | 4.599 / 3.651 / 17.157 / 9.876 / 3.934 / 7.185 | Chứng từ và báo cáo ERPNext trong khung Lotus |
| `docs/LOTUS_DESKTOP_UI_STANDARD_20261017.md` / `docs/COMPACT_WORKSPACE.md` / `docs/UI_STACK.md` | 35 / 46 / 42 | 3.359 / 2.944 / 4.314 | Tài liệu chuẩn |

### 3. CSS nạp cho khung máy tính

`main.js:6-29` import 20 tệp theo thứ tự: `lotus-fonts`, `lotus-tokens`, `style`, `stock`, `shadcn`, `attio`, `stock-attio`, `compact`, `farm-work`, `timekeeping`, `hr`, `hr-workspace`, `warehouse-table-center`, `stock-overview`, `warehouse-workspace-audit`, `desktop-system`, `desktop-components`, `desktop-shell`, `workspace-experience`, `care-map`. `App.vue:45` thêm `document-action.css`. Tổng 21 tệp, 170.735 byte, 1.654 rule (chưa tính CSS Tailwind sinh ra và `<style>` trong SFC).

| Tệp | Byte | Rule | Phần của khung nằm trong tệp |
|---|---:|---:|---|
| `workspace-experience.css` | 32.678 | 289 | Hộp thoại, tab, thanh công cụ danh sách, dải số tổng, sidebar nhóm, thông báo, skip link, ghi đè cuối |
| `compact.css` | 27.614 | 276 | Lưới thanh đầu trang, bảng tìm nhanh, sidebar 208px, mốc ≤700px |
| `style.css` | 11.019 | 139 | Khung gốc, nằm trong `@layer lotus-legacy` (`style.css:1-2`) |
| `attio.css` | 9.209 | 104 | Lớp phủ lần hai của khung gốc |
| `desktop-system.css` | 7.141 | 49 | Sidebar 224px, đệm `main`, ô nhập, panel (chỉ ≥901px) |
| `desktop-components.css` | 4.888 | 43 | `.lotus-page-heading`, `.lotus-metric-card`, `.lotus-empty-state` |
| `desktop-shell.css` | 4.652 | 21 | Thanh đầu trang đỏ 60px |
| `care-map.css` | 3.308 | 35 | Khung toàn màn cho trang bản đồ |
| `document-action.css` | 650 | 6 | Khối lý do hủy/sửa trong hộp chứng từ |
| 12 tệp còn lại (phân hệ, token, font) | 69.576 | 692 | Có 147 rule `.stock-shell` và các ghi đè lên lớp dùng chung |

Chỉ `style.css` nằm trong layer. 19 tệp còn lại không layer, thắng thua theo độ đặc hiệu và thứ tự import.

### 4. Bố cục khung

Cấu trúc DOM (`App.vue:230-248`): liên kết bỏ qua → `div.app-shell.lotus-ui.workspace-shell` → `WorkspaceSidebar` + `main#lotus-main` → (`WorkspaceBar`, `WorkspaceScopeBar`, dòng lỗi/thông báo, `div.workspace-module-host` có `KeepAlive`, hoặc `section` của trang) → `nav.mobile-bottom-nav` → 4 `WorkspaceModal`, `WorkspaceConfirm`, `Toaster`, `AiChatBubble`, `ReleaseNotes`.

| Vùng | ≥1161px | 901–1160px | 701–900px | ≤700px |
|---|---|---|---|---|
| Sidebar | 224px, đệm 18px 12px (`desktop-system.css:66`); cao 100dvh, chỉ `nav` cuộn (`workspace-experience.css:61-63`) | như trái | 208px (`compact.css:6`) | Thành dải ngang, `nav` ẩn (`compact.css:223-227`) |
| Sidebar thu gọn | 64px, ẩn nhãn, mũi tên, mục con (`workspace-experience.css:71-75`, `:257-259`) | như trái | 64px (`compact.css:208-218`) | Nút thu gọn bị ẩn |
| Thanh đầu trang | Dính trên, cao tối thiểu 60px, nền `--lotus-primary-600`, z-index 40, lưới `minmax(155px,1fr) minmax(165px,300px) minmax(150px,1fr)` (`desktop-shell.css:2-16`) | Lưới `minmax(125px,1fr) minmax(145px,210px) minmax(125px,1fr)` (`desktop-shell.css:54-62`) | Cao 50px, z-index 35, cột giữa 261px (`compact.css:11`) | Cột giữa 38px, ô tìm chỉ còn biểu tượng, nút 38px |
| Nội dung `main` | Là vùng cuộn duy nhất, `scrollbar-gutter:stable` (`workspace-experience.css:64-66`); đệm `0 22px 22px`, không giới hạn bề rộng (`desktop-system.css:78`) | Đệm ngang 14px | Đệm `0 10px 8px` (`compact.css:5`) | Đệm dưới `84px + safe-area` |
| Điều hướng dưới | Ẩn | Ẩn | Ẩn | Chỉ hiện từ ≤650px (`style.css:30-31`) |

- Thu gọn sidebar: `sidebarCollapsed` lưu `localStorage['lotus-sidebar']`, đồng bộ giữa các tab bằng sự kiện `storage` (`workspace.js:5`, `:10-11`). Lớp `sidebar-collapsed` đặt trên `.app-shell` (`App.vue:230`). Bấm nhóm có mục con khi đang thu gọn thì sidebar mở lại và mở nhóm đó (`components/WorkspaceSidebar.vue:42-47`).
- Nhóm sidebar: mỗi lần chỉ một nhóm mở (`openGroup`, `components/WorkspaceSidebar.vue:37-52`). Nút nhóm cao 40px chữ 13px, mục con cao 34px chữ 12px (`workspace-experience.css:240`, `:246`).
- Sáng/tối: `localStorage['lotus-theme']`, đặt lớp `.dark`, `data-theme` và `color-scheme` trên `<html>` (`workspace.js:4-9`).
- Thanh đầu trang gồm: nút thu gọn sidebar, liên kết trang chủ, ô chuyển phân hệ (DropdownMenu, nhãn là tên màn), ô chọn "Vườn làm việc", nút "Tìm nhanh… Ctrl K", nút sáng/tối, menu tài khoản (`components/WorkspaceBar.vue:43-72`).
- Thanh phạm vi (`components/WorkspaceScopeBar.vue:12`): Công ty (khi >1), Vườn, Khu, Lô chăm sóc, Vụ, Ngày, Từ ngày – đến ngày, nút "Cập nhật". Một hàng không xuống dòng, cuộn ngang; mỗi trường 170px, khoảng ngày 320px (`workspace-experience.css:219-234`). Chỉ hiện ở màn không nhúng và không phải bản đồ (`App.vue:230`).
- Mốc bề rộng dùng trong 21 tệp: 15 giá trị khác nhau (550, 600, 620, 650, 700, 701, 720, 900, 901, 1000, 1100, 1120, 1150, 1160, 1450px), 49 câu `@media`.

### 5. Điều hướng và cách đăng ký phân hệ

`domain.js:1-2` khai 24 trang. Trong đó 10 trang là phân hệ nhúng nạp trễ (`App.vue:52-63`: `mua-hang`, `nguoi-dung`, `nhan-su`, `cham-cong`, `kho`, `cong-viec`, `farms`, `tai-chinh`, `forecast`, `mau-day`), 4 trang có nhánh riêng trong `App.vue` (`reports`, `trace`, `map`, `admin/settings`), 10 trang dùng danh sách chung của `App.vue:239-244` (`alerts`, `work`, `materials`, `measurements`, `harvest`, `incoming-qc`, `packhouse`, `cycle-close`, `admin/masters`, `admin/imports`). Thêm `/plots/:plot`, `/cycles/:cycle`, `/mobile`, `/denied` và các chuyển hướng (`router.js:27-30`).

Muốn thêm một phân hệ phải sửa các nơi sau:

| Nơi | Nội dung khai |
|---|---|
| `domain.js:1-2` (`pages`) | Đường dẫn và tên màn; `pageRoutes` sinh route |
| `domain.js:5-15` (`navGroups`) | Nhóm sidebar, biểu tượng, nhãn ngắn; `kind` trỏ tới `sectionedModules` |
| `workspace-routes.js:2-13` | Đường dẫn → `capability` hoặc `module` để kiểm quyền |
| `App.vue:52-63` | Đường dẫn → component nạp trễ |
| `router.js:9-24` | Ngoại lệ quyền cho `nhan-su`, `mua-hang` |
| `module-navigation.js:9-15` + một tệp `*-navigation.js` | Mục con, hàm `normalize`, `query`, nhãn nhóm thiết lập |
| `App.vue:81` (`workspaceTitle`) và `App.vue:230-231` | Tên màn theo từng phân hệ; truyền `hr-view`, `buying-view`, `stock-view`, `finance-view`, `field-view` cho sidebar và phân hệ |
| `workspace-directory.js:3-10`, `App.vue:184`, `mobile-menu.js` | Liên kết cho ô chuyển phân hệ, tìm nhanh, điều hướng dưới |

- Tham số chọn màn con khác nhau theo phân hệ: `hr_view`, `buying_view`, `stock_view` (hoặc `tab`), `tab` (kế toán), `field_view`; mục ERP dùng thêm `erp_tab`, `name`, `new`, `erp_doctype` (`components/erp/ErpSection.vue:12-15`).
- Mục ERPNext/HRMS do máy chủ gửi kèm phiên, chèn vào sidebar bằng `withErpNav` (`erp-sections.js:13-23`).
- Hợp đồng của phân hệ nhúng (`App.vue:231`): nhận `embedded`, `navigation-key`, `buying-view`, `stock-view`, `company`, `warehouse`, `hr-view`, `field-view`; phát `navigation-consumed`; có thể lộ `hasChanges()`, `discardChanges()`, `scopeParams()` (`App.vue:104`, `:193-195`).
- Chặn rời màn khi chưa lưu: guard router (`App.vue:191-197`), hai trình nghe `beforeunload` (`App.vue:198-199`, `:216-217`), hỏi khi đóng hộp chứng từ (`App.vue:204-208`), bản nháp cục bộ cho chứng từ mới (`form-drafts.js:1-11`, `App.vue:209-215`).

### 6. Thành phần mẫu: API, lớp CSS, số nơi gọi

Số nơi gọi đếm thẻ trong phần `<template>` của 197 SFC, đã loại 10 SFC không chạy ở bản thật (xem mục Điểm yếu I). Dạng "tệp/thẻ".

- **WorkspaceBar** — props `farms`, `farm`, `user`, `title`, `actions`, `sidebar` (true), `branded` (false), `navigate`, `recordSearch`; emits `update:farm`, `whats-new`; không slot (`components/WorkspaceBar.vue:13-14`). Lớp: `.workspace-bar`, `.workspace-left|right`, `.workspace-sidebar-toggle`, `.workspace-home`, `.workspace-nav-trigger`, `.workspace-nav-title`, `.workspace-farm`, `.workspace-search`, `.workspace-avatar`, `.workspace-username`, `.workspace-user-trigger`, `.command-dialog`, `.command-input`, `.command-results`, `.lotus-menu__*`. Tạo kiểu ở `compact.css`, `desktop-shell.css`, `workspace-experience.css`, `desktop-system.css`, `care-map.css`. Nơi gọi: 1/1 (`App.vue:230`).
- **WorkspaceSidebar** — props `nav` (bắt buộc), `page`, `hrView`, `buyingView`, `stockView`, `financeView`, `fieldView`; emits `go(path, query)` (`components/WorkspaceSidebar.vue:11-12`). Lớp: `.sidebar`, `.brand`, `.lotus-brand-image`, `.nav-group`, `.nav-group-current`, `.nav-group-row`, `.nav-parent`, `.group-selected`, `.nav-toggle`, `.nav-chevron`, `.nav-submenu`, `.nav-subsection`, `.nav-child`, `.nav-sub-link`, `.nav-icon`, `.nav-label`, `.field-link`, `.active`. Tạo kiểu ở 7 tệp (93 rule `.sidebar`). Nơi gọi: 1/1.
- **WorkspaceScopeBar** — props `page`, `busy`, `land`, `farmVisible`, `options`, `companies`, `farms`; emits `change`, `refresh`; đọc ghi thẳng store `scope` (`components/WorkspaceScopeBar.vue:8-10`). Lớp `.scope-picker`, `.scope-date-range` (36 rule ở 6 tệp). Nơi gọi: 1/2 (`App.vue:230`, `:234`).
- **WorkspaceTabs** — props `items` [{id,label}], `modelValue`, `label`; emits `update:modelValue` (`components/WorkspaceTabs.vue:3-4`). Lớp `.workspace-tabs`, `button.selected` (`workspace-experience.css:109-112`, 1 rule ở `stock.css`). Nơi gọi: 9/9.
- **WorkspaceModal** — props `modelValue`, `title` (bắt buộc), `busy`, `width` ('960px'), `bare`, `expanded` (true); emits `update:modelValue`, `cancel`, `close`; slot mặc định; lộ `showModal()`, `close()`, `open`, `el` (`components/WorkspaceModal.vue:12-13`, `:26`). Lớp `.workspace-modal`, `--bare`, `--expanded`, `__header`, `__body` (24 rule ở `workspace-experience.css`, 7 rule ở `work-mobile.css`). Nơi gọi: 23/43.
- **WorkspaceConfirm** — props `open`, `title`, `message`, `alertOnly`, `confirmLabel` ('Đồng ý'), `cancelLabel` ('Hủy'); emits `answer` (`components/WorkspaceConfirm.vue:4-5`). Dùng với `useWorkspaceConfirm()` trả `ask(text, heading)`, `tell(text, heading)` (`use-workspace-confirm.js:4-11`). Lớp `.workspace-confirm__message|__actions` (`workspace-experience.css:172-173`). Nơi gọi: 11/11.
- **WorkspaceListToolbar** — props `modelValue`, `searchable`, `placeholder`, `busy`, `refreshable`, `refreshDisabled`; emits `update:modelValue`, `refresh`; slot mặc định (hàng 1), `filters`, `tools` (`components/WorkspaceListToolbar.vue:8-9`, `:12-20`). Lớp `.workspace-list-toolbar|-actions|-row|-filters|-search|-refresh|-tools` (`workspace-experience.css:118-131`; `timekeeping.css` ghi đè 4 rule). Nơi gọi: 6/6.
- **WorkspaceSummaryStrip** — props `items` [{label,value}] (`components/WorkspaceSummaryStrip.vue:2`). Lớp `.workspace-summary-strip` (`workspace-experience.css:113-116`). Nơi gọi: 5/9.
- **WorkspaceLoading** — không props. Lớp `.workspace-loading` (`workspace-experience.css:42-46`). Dùng làm `loadingComponent` 10 lần (`App.vue:53-62`).
- **ListPage** — props `rows`, `columns` (bắt buộc), `loading`, `title`, `search`, `searchable`, `searchPlaceholder`, `summary`, `error`, `paged`, `start`, `total`, `hasMore`, `pageSize` (50); emits `update:search`, `update:start`, `update:pageSize`, `refresh`; slot `filters`, `actions`, `before`, mặc định, `cell-<field>`; thuộc tính khác chuyển cho DataTable (`components/ListPage.vue:8-14`). Lớp `.lotus-list-page`, `__error`, `__tools` (trong chính SFC). Nơi gọi: 13/18.
- **LotusField** — props `modelValue`, `label`, `type`, `options`, `searchable`, `fetchOptions`, `displayValue`, `required`, `disabled`, `readonly`, `hint`, `error`, `placeholder`, `emptyOption`, `currency`, `wide`, `mobile`; emits `update:modelValue`, `select`, `change`; không slot (`components/form/LotusField.vue:22-28`). Loại điều khiển: text, number, money, date, month, select, combobox, textarea, checkbox, file (`:18`, `:31-36`). Lớp `.lotus-field*` (định nghĩa ở `components/ui/form-field/FormField.vue`). Nơi gọi: 53/413.
- **ModalForm** — props `modelValue`, `title`, `busy`, `width`, `error`, `description`, `submitLabel` ('Lưu'), `busyLabel`, `cancelLabel` ('Hủy'), `submitDisabled`, `readonly`; emits `update:modelValue`, `submit`, `cancel`; slot mặc định, `secondary`, `actions` (`components/form/ModalForm.vue:7-8`, `:17-22`). Lớp `.lotus-modal-form*`, `.lotus-delete-confirm*` (trong SFC). Nơi gọi: 30/58.
- **ResponsiveForm** — cùng props và slot với ModalForm, thêm `mobile` (`components/form/ResponsiveForm.vue:6-7`). Nơi gọi: 1/2.
- **LineItemsEditor** — props `modelValue`, `columns`, `newRow`, `title`, `addLabel`, `max` (100), `min` (1), `readonly`, `fixed`, `mobile`, `emptyText`; emits `update:modelValue`, `select`, `remove`; slot `cell-<field>`, `footer` (`components/form/LineItemsEditor.vue:10-15`, `:34`, `:42`). Lớp `.lotus-lines*` (trong SFC). Nơi gọi: 10/17.
- **FormGrid** — props `columns` (2); lớp `.lotus-form-grid`, `__wide` (`components/form/FormGrid.vue:3`, `:7-9`). Nơi gọi: 19/54.
- **FormSection** — props `title`, `description`; slot mặc định, `actions` (`components/form/FormSection.vue:3`, `:7`). Nơi gọi: 9/62.
- **ReasonDialog** — props `dialog` (từ `useReasonDialog()`), `submitLabel` (`components/form/ReasonDialog.vue:5`). Nơi gọi: 3/3.
- **SchemaForm** — props `schema`, `model`, `readonly`, `scope`, `child`, `linkTitles`, `linkOptions` (`components/SchemaForm.vue:14`). Lớp `.schema-grid`, `.child-table`, `.child-row`, `.section-title`, `.field-value`, `.wide` (13 rule ở `style.css`, `attio.css`, `farm-work.css`, `workspace-experience.css`). Nơi gọi: 5/7.
- **SearchSelect** 2/3, **LinkPicker** 1/1 (`components/SchemaForm.vue:48`), **MonthPicker** 3/3.
- **DesktopEmptyState** — props `title`, `description`, `icon`; slot `actions`. Nơi gọi sống: 1/1 (`components/DataTable.vue:326`). **DesktopMetricCard** và **DesktopPageHeading**: 0 nơi gọi sống.
- **OverviewBoard** 1/1 (`components/ReportsWorkspace.vue`), **ReleaseNotes** 2/2 (`App.vue:248`, `WorkMobile.vue`).
- **ErpSection** 4/4 (`StockApp.vue`, `HrApp.vue`, `FinanceApp.vue`, `components/ProcurementWorkspace.vue`), **ErpReport** 4/4, **ErpList** 1/1, **ErpForm** 1/1, **ErpFields** 2/2, **ErpChildTable** 1/1.

### 7. Trang danh sách chuẩn

`components/ListPage.vue:19-31`, từ trên xuống:

1. `section.lotus-list-page`; `title` chỉ thành `aria-label`, không hiện chữ.
2. Hàng 1 `.workspace-list-actions`: slot `actions`, canh trái (`workspace-experience.css:119`).
3. Hàng 2 `.workspace-list-row`: slot `filters` (mỗi ô 150–240px), ô tìm `type=search` (200–380px), nút "Làm mới", vùng `tools` ở mép phải. Hai nút "Cột hiển thị" và "Xuất Excel" của DataTable được chuyển lên vùng `tools` qua `tools-target` (`components/ListPage.vue:16`, `:23`, `:28`). Mọi điều khiển cao 36px (`workspace-experience.css:130`).
4. Dòng lỗi `p.lotus-list-page__error[role=alert]`.
5. `WorkspaceSummaryStrip` khi có `summary`.
6. Slot `before`.
7. `DataTable`, ô tùy biến qua slot `cell-<field>`.
8. `Pagination` khi `paged`: chọn 20/50/100 dòng, nút "Hiện toàn bộ", khoảng "1–50 / 1.234", số trang hoặc Trước/Tiếp, canh phải (`components/ui/pagination/Pagination.vue:18-36`).
9. Slot mặc định cho hộp thoại đi kèm.

`components/erp/ErpList.vue:47-52` là ví dụ đủ: tìm chờ 250ms, sắp xếp và phân trang trên máy chủ, nút "Tạo mới" ở slot `actions`.

### 8. Hệ hộp thoại

- Một thành phần `WorkspaceModal` trên `<dialog>` gốc, ba cách dùng: `v-model` + `title` (38 thẻ sống), `bare` + ref (2: bảng tìm nhanh `components/WorkspaceBar.vue:73`, quét mã `components/CccdQrScanner.vue`), ref không `bare` (3: `components/WorkMaterialSettings.vue` ×2, `FarmWorkApp.vue` ×1).
- Dạng chuẩn: teleport ra `body`, đầu hộp dính trên gồm `h2` và nút "Đóng", thân bọc trong `fieldset` bị khóa khi `busy`, cao tối đa `100dvh - 32px`, đệm thân `18px 20px` (`components/WorkspaceModal.vue:30-33`, `workspace-experience.css:47-54`).
- Kích thước: prop `width` thành `min(width, 100vw - 24px)`. Ở ≥901px, hộp có `expanded` (mặc định true) bị ép `width: calc(100vw - 24px) !important` (`workspace-experience.css:290-293`, commit `5859e30` ngày 02/11/2026).
- Đóng: Esc và bấm nền đều bị chặn khi `busy` (`components/WorkspaceModal.vue:18-19`, `dialogs.js:3-8`); hộp tự đóng khi màn trong `KeepAlive` bị ẩn (`:23`).
- Chân hộp chuẩn chỉ có ở `ModalForm`: slot `secondary` bên trái, rồi "Hủy", slot `actions`, "Lưu" ở mép phải; dính dưới (`components/form/ModalForm.vue:18-23`, `:31-32`). `readonly` chỉ còn nút "Đóng".
- Xác nhận: `useWorkspaceConfirm` + `WorkspaceConfirm` (480px, không giãn). Hỏi lý do: `useReasonDialog` + `ReasonDialog` (`use-reason-dialog.js:3-13`).
- Nội dung nổi trong hộp: `useDialogPortal()` trả về `dialog[open]` gần nhất hoặc `body` (`components/ui/portal-target.js:4-11`). Chỉ `Combobox`, `DatePicker`, `DateRangePicker` dùng hàm này.
- Thứ tự lớp: thanh đầu trang 35/40, lớp phủ cũ 80, Sheet 2147481000, Popover và danh sách chọn 2147482000, Tooltip 2147482500, Toast 2147483000, skip link 2147483001. `<dialog>` mở bằng `showModal()` nằm ở top layer, trên mọi z-index.

### 9. Quy tắc bố cục biểu mẫu đang có

| Hệ | Nơi định nghĩa | Cột và mốc | Nơi dùng |
|---|---|---|---|
| `FormGrid` | `components/form/FormGrid.vue:7-9` | N cột đều (mặc định 2), khoảng cách 14px 16px, 1 cột ở ≤720px | 54 thẻ; giá trị `columns` gặp: 1, 2, 3, 4 |
| `.schema-grid` | `style.css:4` | 3 cột, 2 cột ở ≤1000px, 1 cột ở ≤650px, khoảng cách 15px; trong `.farm-editor` là 2 cột (`farm-work.css`) | `SchemaForm`, `App.vue`, 2 SFC khác |
| `.erp-section__columns` | `components/erp/ErpFields.vue:94-105` | Số cột theo DocType; phần một cột chảy `minmax(260px,1fr)`; 1 cột ở ≤900px | Chứng từ ERP |
| `.erp-report__filters` | `components/erp/ErpReport.vue:90` | `repeat(auto-fill,minmax(190px,1fr))`, khoảng cách 10px | Bộ lọc báo cáo ERP |

- Trường: nhãn trên, dấu `*` màu nguy, gợi ý hoặc lỗi dưới ô, chữ 12px (`components/ui/form-field/FormField.vue`).
- `FormSection`: tiêu đề `h3`, hành động nằm dưới tiêu đề và canh trái (`components/form/FormSection.vue:14-18`).
- `LineItemsEditor`: đầu khối có tên và số dòng, một hàng tiêu đề cột, nút xóa 36px cuối mỗi dòng, nút "Thêm dòng" ở dưới bên trái.

### 10. Trạng thái trống, đang tải, lỗi

- Đang tải: `WorkspaceLoading` (3 thanh nhấp nháy, "Đang mở màn hình…"); chữ "Đang đọc số liệu…" (`App.vue:230`); khung dòng `.lotus-table-skeleton` trong DataTable; prop `loading` của nút; đổi chữ nút ("Đang lưu…", "Đang tải…", "Đang chạy…"); `aria-busy` và `fieldset disabled` của hộp thoại; "Đang mở chứng từ…" (`components/erp/ErpForm.vue:158`).
- Trống: `DesktopEmptyState` trong DataTable; `p.empty` (`App.vue:233`, `:247`); `p.muted` "Chưa có dòng." (`components/SchemaForm.vue:36`); `.lotus-lines__empty`; `.lotus-chart-empty`; `.erp-child__missing`; dấu "—" cho số thiếu (`domain.js:19`).
- Lỗi: dòng `role=alert` cạnh nội dung. Thành công: toast qua `useNoticeToast` (`App.vue:186`, `use-toast.js:20-22`); toast tối đa 4, 5 giây, 8 giây khi có hành động hoặc là lỗi. Mất mạng: dòng `.notice` "Đang dùng dữ liệu đã lưu…" (`App.vue:230`). Không quyền: `section.panel` "Không có quyền mở màn hình này" (`App.vue:231`).
- `workspace-experience.css:174-180` gom 12 lớp thông báo cũ về bốn tông (lỗi, thành công, thông tin, cảnh báo).

### 11. Phím tắt

| Phím | Tác dụng | Nơi |
|---|---|---|
| Ctrl/Cmd + K | Mở hoặc đóng bảng tìm nhanh; không mở khi đang có hộp thoại | `components/WorkspaceBar.vue:34-36` |
| ↑ ↓, Enter, Esc | Chọn, mở, đóng trong bảng tìm nhanh | `components/WorkspaceBar.vue:37`, `:76` |
| ← →, Home, End | Chuyển và kích hoạt tab | `components/WorkspaceTabs.vue:6` |
| Esc | Đóng hộp thoại (bị chặn khi `busy`) | `components/WorkspaceModal.vue:19` |
| Enter | Lọc ở danh sách chung và truy xuất | `App.vue:239`, `:233` |
| Tab đầu tiên | Hiện liên kết "Bỏ qua tới nội dung" | `App.vue:230`, `workspace-experience.css:193-194` |

Không có phím tắt cho lưu, tạo mới, đưa con trỏ vào ô tìm, và không có bảng liệt kê phím tắt.

### 12. Trang mẫu và tài liệu

- `components/UiShowcase.vue` (75 dòng) trưng: nút và thông báo, biểu mẫu, menu/tooltip/popover/sheet, bảng, tab/phân trang/tải/trống. `showcase-main.js:3-12` nạp 10 tệp CSS, điểm vào thật nạp 20.
- `docs/WORKSPACE_UI_STANDARD.md:5` ghi đúng ba số của khung: thanh đầu trang 60px, sidebar 224px, thu gọn 64px.

## Ràng buộc phải giữ

### Quy ước đã chốt với chủ vườn

1. Nút tạo đứng đầu, bên trái. Đang thực hiện ở `components/WorkspaceListToolbar.vue:5`, `:13` và `workspace-experience.css:119` (commit `69ae952`).
2. Hàng 1 là thao tác, hàng 2 là tìm và lọc (`components/WorkspaceListToolbar.vue:13-19`).
3. Không tiêu đề, breadcrumb, mô tả trang trí trên bảng (`AGENTS.md:3-6`). `ListPage` chỉ đưa `title` vào `aria-label` (`components/ListPage.vue:19`).
4. Nhập liệu và số tổng hợp dùng thẻ cộng hộp thoại, không trải bảng phẳng trên trang. Mẫu đang có: `components/report/ReportCards.vue:21-33`, `components/field/LotCards.vue`, `ModalForm`.
5. Nút lưu ở bên phải (`components/form/ModalForm.vue:18-23`). `tests/form-standard.mount.test.js:58-59` khóa thứ tự chân hộp là `['Hủy','Lưu']`.
6. Thanh lọc máy tính nằm trên một hàng, màn hẹp cuộn trong chính thanh lọc (`AGENTS.md:8`).
7. Màu chính Đỏ Lotus `#c43224`; màu, chữ, khoảng cách, bo góc, bóng lấy từ `lotus-tokens.css` (`AGENTS.md:12`).
8. Hộp thoại máy tính chỉ dùng `WorkspaceModal`; nội dung nổi trong hộp phải render trong chính `<dialog>`; xác nhận dùng `useWorkspaceConfirm`; biểu tượng dùng `LotusIcon` (`AGENTS.md:17-19`).
9. Component có hành vi phải có test mount; trang mẫu không vào bản thật (`AGENTS.md:20-21`).
10. Toàn bộ chữ hiển thị bằng tiếng Việt (`.specify/memory/constitution.md:20`).
11. Phạm vi chỉ tới lô: `store.js:9` xóa `plot` mỗi lần đọc phạm vi; thanh phạm vi không có ô chọn thửa.
12. Biểu mẫu nhập mở hết bề ngang trên máy tính (commit `5859e30`; `tests/workspace-modal.mount.test.js:14`, `:45` khóa lớp `workspace-modal--expanded`).

### Test khóa hành vi và tên lớp

- `tests/workspace-sidebar.mount.test.js`: lớp `.nav-parent`, `.nav-label`, `.nav-group`, `.nav-group-current`, `.nav-submenu`, `.nav-child`, `.nav-toggle`, `.nav-subsection` (thẻ `SPAN`), `.nav-sub-link`, `svg.lotus-icon`, `nav button.active`, `aria-current=page`; thứ tự nhóm; `emit('go', path, query)`; mỗi trang thuộc đúng một nhóm và có biểu tượng thật.
- `tests/workspace-modal.mount.test.js`: `bare` render tại chỗ và giữ lớp người gọi; `aria-label` bằng `title`; `showModal()` đồng bộ; chuyển tiếp `@cancel`, `@close`; Esc bị chặn khi `busy` hoặc khi người gọi `preventDefault`; dạng `v-model` có `.workspace-modal__header` và nút đóng cập nhật model.
- `tests/form-standard.mount.test.js`: `label.lotus-field__label[for]`, `.lotus-field__required`, `aria-describedby` trỏ `-hint`; số và tiền là `input[inputmode=decimal][type=text]` nhận cả dấu phẩy và dấu chấm; `[role=checkbox]`; lựa chọn rỗng "Chọn…"; `.lotus-lines__head > span`, `.lotus-lines__remove`, `input[aria-label="Vật tư dòng 1"]`; `section.lotus-list-page[aria-label]`, `.workspace-list-toolbar input[type=search]`, `.lotus-pagination` hiện "1–1 / 120".
- `tests/form-standard.test.js:8-28`: danh sách tệp "chuẩn" không được có `<input|select|textarea>` trong template, không `window.prompt/confirm/alert`, không `<WorkspaceModal bare>`, `<form>` chỉ nằm trong `ModalForm` và `ResponsiveForm`.
- `tests/grid-compact.test.js:64-87`: `.workspace-list-row .workspace-list-tools .lotus-data-table__export`; trang cuối ngắn vẫn giữ chiều cao bảng.
- `tests/excel-filter-ux.test.js:68-70`, `:83`: trong `WorkspaceListToolbar.vue`, chuỗi `workspace-list-filters` đứng trước `workspace-list-search` và không có `type="submit"`; `WorkspaceScopeBar.vue` có `v-if="companies.length>1" label="Công ty"`.
- `tests/scope-filterbar-layout.test.js:8-19`: khớp nguyên văn chuỗi CSS trong `workspace-experience.css` (170px, 320px, `flex-wrap:nowrap`, `overflow-x:auto`).
- `tests/desktop-design-system.test.js:11-30`: `main.js` import ba tệp `desktop-*.css`; `App.vue` chứa `lotus-ui`; `desktop-system.css` chứa `@media (min-width:901px)`, `.lotus-ui.app-shell`, `.lotus-ui.stock-shell`, `prefers-reduced-motion:reduce`, `focus-visible`.
- `tests/component-library.test.js:14-33`: `SearchSelect`, `LinkPicker` chỉ bọc `<Combobox`; `WorkspaceBar` dùng `<DropdownMenuContent`, `<Tooltip`, không `<details`; `showcase.html` tồn tại và không có trong `vite.config.js`.
- `tests/ui-stack.test.js:43-66`: `App.vue` và `SchemaForm.vue` import `{Button as UiButton}`; nút biểu tượng `ghost` trên `WorkspaceBar` có `hover:bg-white/15 hover:text-white`.
- `tests/design-tokens.test.js`: mọi điểm vào import `lotus-tokens.css` trước; không mã hex đục ngoài tệp token; không `window.alert/confirm`; không ký tự thay biểu tượng.
- `tests/document-actions-simplified.test.js`, `tests/stock-filter-overhaul.test.js:18`: khớp chuỗi trong `App.vue` (nhãn "Lưu thiết lập"/"Lưu nháp", `pendingDocumentAction`, `<WorkspaceBar … :actions="workspaceActions"`).
- `tests/field-navigation.test.js`, `tests/procurement-menu.test.js`, `tests/hr-navigation.test.js`, `tests/hr-navigation.mount.test.js`, `tests/domain.test.js`: nhãn, thứ tự, id của menu; liên kết cũ vẫn mở đúng màn.
- `tests/use-confirm-core.test.js`, `tests/use-toast.test.js`, `tests/dialogs.test.js`, `tests/release-notes.test.js`, `tests/erp-form.mount.test.js`.

### API và hành vi đang được nơi khác dùng

- Tên component và props/slot/emit ở mục 6: 413 thẻ `LotusField`, 58 `ModalForm`, 43 `WorkspaceModal`, 54 `FormGrid`, 62 `FormSection`, 18 `ListPage`, 17 `LineItemsEditor`. Đổi tên prop là sửa từng ấy nơi.
- URL và tham số: `/lotus/<trang>` cùng `hr_view`, `buying_view`, `stock_view`, `tab`, `field_view`, `erp_tab`, `name`, `new`, `action`; các chuyển hướng cũ ở `router.js:27-28` và `workspace-routes.js:20`.
- Khóa `localStorage`: `lotus-theme`, `lotus-sidebar`, `lotus-desktop-density`, `lotus-safe-scope|<user>` (`store.js:9-11`), `lotus-release-notes-seen:<user>` (`components/ReleaseNotes.vue:9`), `lotus-draft:<doctype>` (`form-drafts.js:2`). FR-047 của `spec.md` yêu cầu giữ.
- Hợp đồng phân hệ nhúng ở mục 5; `KeepAlive` giữ biểu mẫu chưa lưu khi chuyển màn (`App.vue:231`, `docs/WORKSPACE_UI_STANDARD.md:8`).
- Quyền: menu không cấp quyền; `permittedRoute` và guard ở `router.js:9-24`, `:32-43` phải chạy như cũ.
- CSS máy tính không được ảnh hưởng PWA Vant (`tests/desktop-design-system.test.js:18-21`).

### Quy tắc đang mâu thuẫn, cần chốt trước khi thiết kế

1. Thứ tự hàng 2. `AGENTS.md:8`: kho, từ ngày, đến ngày, làm mới, tìm kiếm. Chú thích `components/WorkspaceListToolbar.vue:5`: lọc · tìm · làm mới. Chú thích `workspace-experience.css:117`: tìm · lọc · làm mới. Thực tế: DOM là lọc → tìm → làm mới, CSS `order:-1` đưa ô tìm lên đầu (`workspace-experience.css:126`). Test `tests/excel-filter-ux.test.js:69` khóa thứ tự DOM.
2. Một hàng cuộn ngang hay xuống dòng. `AGENTS.md:8` yêu cầu một hàng; `components/WorkspaceListToolbar.vue:6` và `workspace-experience.css:121` cho xuống dòng; `timekeeping.css` tự ép `flex-wrap:nowrap` cho riêng chấm công; thanh phạm vi thì một hàng.
3. Hộp nhỏ có giãn hết màn không. Quy tắc "mở hết bề ngang" hiện áp cả cho hộp hỏi lý do và bảng tìm nhanh (xem Điểm yếu E1).
4. Khối tiêu đề lớn. `AGENTS.md:3` cấm; `docs/LOTUS_DESKTOP_UI_STANDARD_20261017.md:17` và `tests/desktop-design-system.test.js:31-35` lại yêu cầu `DesktopPageHeading`.
5. Trang thửa. `store.js:9` bỏ thửa, nhưng `App.vue:237` còn trang `/plots/:plot` và `App.vue:233` còn lựa chọn truy xuất "Thửa".

## Điểm yếu

### A. Kiến trúc CSS của khung

- A1. Cùng một vùng bị tạo kiểu ở nhiều tệp chồng nhau: `.sidebar` 93 rule ở 7 tệp, `.app-shell` 136 rule ở 7 tệp, `.workspace-bar` 36 rule ở 5 tệp, các lớp con của thanh đầu trang 57 rule ở 3 tệp, `.scope-picker` 36 rule ở 6 tệp. Bề rộng sidebar khai 5 lần: 235px (`style.css:4`), 244px (`attio.css:11`), 208px (`compact.css:6`), 224px (`desktop-system.css:66`), 64px (`workspace-experience.css:71` và `compact.css:208-218`). Đệm của `main` khai 10 lần ở 5 tệp.
- A2. Thắng thua dựa vào mẹo: 35 rule mở đầu bằng `:root:root` (đều ở `workspace-experience.css`) và 42 lần `!important` trong 29 rule (17 lần ở `workspace-experience.css`). Chú thích `workspace-experience.css:165-166` ghi rõ làm vậy để không phụ thuộc thứ tự chunk của Vite.
- A3. 231 rule nhắm thẳng thẻ `button`, `input`, `select`, `textarea` (49 ở `compact.css`, 39 ở `workspace-experience.css`, 30 ở `timekeeping.css`). Primitive bị sửa từ bên ngoài: sidebar dùng `UiButton variant="outline"` (`components/WorkspaceSidebar.vue:66`, `:70`, `:77`) rồi `desktop-system.css:70-73` xóa viền và nền; `compact.css:15` ép mọi nút trong thanh đầu trang cao 30px; `workspace-experience.css:130` ép mọi nút trong thanh công cụ cao 36px.
- A4. Giá trị ghi cứng trong 7 tệp CSS của khung: 195 lần `font-size:…px` với 20 cỡ từ 8 đến 30px (dùng token 13 lần); 85 lần `border-radius:…px` với 15 giá trị (token 10 lần); 18 bóng ghi cứng (token 2 lần); 22 mã màu trong suốt khác nhau. Test token chỉ chặn màu đục và font.
- A5. z-index có 14 giá trị trong CSS khung và thêm 7 giá trị trong `components/ui` (tới 2147483001), không có thang. 15 mốc bề rộng (mục 4).
- A6. Từ 651 đến 700px không có điều hướng chính: `compact.css:223-227` ẩn `nav` của sidebar và nút thu gọn ở ≤700px, còn `style.css:31` chỉ hiện điều hướng dưới ở ≤650px. Còn lại ô chuyển phân hệ và Ctrl K. (chưa kiểm)
- A7. Token ngữ nghĩa bị định nghĩa lại ngay trong thanh đầu trang (`--lotus-text:#fff`, `--lotus-muted`, `--lotus-border`, `--lotus-soft` ở `compact.css:81` và `desktop-shell.css:6`). `tests/design-tokens.test.js:30-38` chỉ kiểm `:root`, `.dark`, `.lotus-ui` nên không bắt.
- A8. Lớp dùng chung lại định nghĩa trong SFC nghiệp vụ, không scoped: `.lotus-form-note` chỉ có ở `components/stock/StockDocumentForm.vue:224` nhưng dùng 106 lần ở 33 tệp; `.lotus-list-page__error` (`components/ListPage.vue:36`) dùng 17 lần ở 16 tệp; `.lotus-delete-confirm` (`components/form/ModalForm.vue:34`) dùng ở 5 tệp khác; `components/erp/ErpReport.vue:77-78` dùng `.erp-form__error`, `.erp-form__loading` của `ErpForm.vue:188-191`. Màn nào mở trước khi chunk chứa định nghĩa được nạp sẽ thiếu kiểu. (chưa kiểm bản build)
- A9. CSS không còn template nào dùng: `.workspace-menu` 10 rule, `.document-dialog` 16 rule, `.small-dialog` 13 rule, `.pn-*` 36 rule, `.stock-dialog` 54 rule, `.farm-assignment` 26 rule, `.assignment-*` 26 rule, `.workspace-status` 3 rule; biến `--lotus-line` (`workspace-experience.css:2`) không ai đọc. Ngược lại, các lớp `.nav-child`, `.nav-group-current`, `.workspace-brand`, `.overview-board`, `.workspace-modal--bare` có trong template nhưng không có rule nào.
- A10. Biến dùng kèm giá trị dự phòng vì chưa có trong tệp token: `--lotus-bg` (`components/erp/ErpForm.vue:176`), `--lotus-surface-muted` (`workspace-experience.css:136`), `--lotus-text-lg` có nhưng vẫn kèm `1.1rem` (`components/erp/ErpReport.vue:87`).

### B. Khung

- B1. `App.vue` vừa là khung vừa là 14 màn và 4 hộp thoại: 72.650 byte, 49 `ref`, 19 `computed`, 47 hàm, 49 dòng import, 64 nút (63 `outline`, 1 `link`). `docs/UI_AUDIT_FULL_20261019.md:54` đã ghi việc tách là "GĐ4, cần duyệt riêng"; chưa làm.
- B2. Không có trạng thái khởi động. Trước khi phiên tải xong, route còn ở `/` nên `page` là `'today'` (`App.vue:76`) và nhánh `App.vue:231` hiện 10 ô KPI cũ cùng 3 bảng rỗng, sau đó mới đổi sang màn thật. (chưa kiểm)
- B3. Nhánh không tới được nhưng còn nằm trong khung: màn `today` sau khi phiên tải (`router.js:27` chuyển hướng `/today`); màn `farms` và lô (`App.vue:236`, vì `farms` là phân hệ nhúng và `router.js:28` chuyển hướng các đường con); `page.value==='process'` (`App.vue:140`) và `OneDriveProcessWorkspace` (`App.vue:41`, không có thẻ nào trong template); `key.value==='labor'` lồng trong nhánh `work` (`App.vue:145`).
- B4. Trình xử lý không tồn tại: `@closed="forecastClosed"` (`App.vue:246`) nhưng không có hàm `forecastClosed` (1 lần xuất hiện trong cả `frontend/src`). Import và biến thừa: `normalizeHrView` (`App.vue:25`), `getMobileActions` (`App.vue:64`), `breadcrumb` (`App.vue:85`).
- B5. Tên tab trình duyệt không đổi theo màn: không nơi nào gán `document.title`; `frontend/index.html` và `lotus_farm/www/lotus.html:1` cùng một tiêu đề. Không có vùng thông báo đổi màn cho trình đọc màn hình.
- B6. `consoleAPI('bootstrap')` gọi hai lần mỗi lần mở: `store.js:7` và `components/WorkspaceBar.vue:39`; `api.js` không gộp yêu cầu trùng.
- B7. Thanh đầu trang: phần tử gốc là `div` có `aria-label` nhưng không có vai trò (`components/WorkspaceBar.vue:43`); nút cao 30px (`compact.css:15`), thấp hơn `--lotus-control-height` 36px; nhãn "Ctrl K" ghi cứng 3 chỗ; prop `branded` và nhánh `.workspace-brand` không ai dùng (`:46`); import `dismissOnBackdrop` thừa (`:10`). Liên kết trang chủ rộng 28px theo `flex-basis` ở `compact.css:258` nhưng `workspace-experience.css:201` khai 32px.
- B8. Sidebar: khi thu gọn không có menu bật ra, chú thích dựa vào `title` của trình duyệt; nút mở nhóm rộng 27px (`workspace-experience.css:241`); ghi `localStorage` trực tiếp không bọc lỗi (`components/WorkspaceSidebar.vue:44`) trong khi `workspace.js:3` đã có hàm an toàn; biến `scope` khai rồi bỏ (`:13`); `watch` thiếu `fieldView` (`:38`); thẻ `<small>` tên người dùng luôn bị ẩn (`compact.css:10`); nhánh `group.links` không có dữ liệu nào (`domain.js:5-15` không khai `links`).
- B9. `use-desktop-workspace.js` không còn tác dụng: hai nơi gọi (`StockApp.vue:29`, `FieldReportApp.vue:29`) đều chạy với `embedded:true`, nên `desktop` luôn false, `gridDensity` luôn null, lớp `lotus-desktop-page` không bao giờ được đặt; `setDensity` không ai gọi. Mật độ gọn/thoáng (FR-003, FR-013) hiện chưa có đường vào.
- B10. Nền trắng ghi cứng có thể sai ở chế độ tối: `.mobile-bottom-nav{background:#fff}` (`style.css:31`), `.workspace-bar .workspace-search{background:#fff}` (`compact.css:83`), 22 lần `background:#fff` trong `style.css`, `attio.css`, `compact.css`, `desktop-shell.css`. (chưa kiểm)
- B11. Liên kết "Mở ERP ↗" trong hộp chứng từ đưa người dùng sang Desk `/app/…` tiếng Anh (`App.vue:246`); sidebar có hai liên kết chân dùng ký tự "↗" thay biểu tượng (`components/WorkspaceSidebar.vue:89-90`).

### C. Đăng ký điều hướng

- C1. Một phân hệ khai ở 8 nơi (mục 5). Nhãn lệch nhau: `/nhan-su` là "Hồ sơ nhân sự" ở `domain.js:1` và `mobile-menu.js`, là "Hồ sơ nhân viên" ở `domain.js:13`, `workspace-routes.js:5`, `hr-navigation.js:4`. Trường `label` của `workspaceModules` không nơi nào đọc.
- C2. Mỗi phân hệ một tên tham số, nên sidebar cần 5 prop riêng (`components/WorkspaceSidebar.vue:11`) và `workspaceTitle` là chuỗi 5 phép chọn lồng nhau (`App.vue:81`). Chú thích `module-navigation.js:6` nói tiêu đề đọc từ registry, mã thì không.
- C3. `toggleOnly` (5 chỗ) và `moduleForPath` trong `module-navigation.js:10-16` không nơi nào dùng.
- C4. Route không có meta (tên, biểu tượng, quyền); kiểm quyền nằm trong một hàm `if` nối tiếp (`router.js:9-24`).

### D. Trang danh sách và thanh công cụ

- D1. 10 trang danh sách chung trong `App.vue:239-244` không dùng `ListPage`: một hàng `.view-controls` trộn chọn loại phiếu, tìm, trạng thái, sắp xếp; nút "Thêm phiếu" đứng thứ sáu; tìm phải bấm Enter; nút nào cũng `outline`. Trái quy ước 1, 2 và nguyên tắc 2 của `docs/LOTUS_DESKTOP_UI_STANDARD_20261017.md:21`.
- D2. Tiêu đề và mô tả phía trên bảng còn nhiều trong `App.vue`: 17 thẻ `h2`, 10 thẻ `h3`, 18 đoạn `p.muted` (ví dụ "Nhu cầu còn lại và tồn khả dụng ERP", "Ma trận lỗi đầu vào · kg" ở `App.vue:241`, `:243`). `components/erp/ErpReport.vue:63-68` cũng đặt `h2` tên báo cáo trên bảng và đẩy nút "Chạy báo cáo" sang phải (`:87` `flex:1`).
- D3. Biểu mẫu trải thẳng trên trang: "Nhận số cân" (`App.vue:242`), "Đề xuất hiệu chuẩn từ thực tế" (`App.vue:232`). Trái quy ước 4.
- D4. `order:-1` làm thứ tự Tab khác thứ tự nhìn thấy (`workspace-experience.css:126`).
- D5. `ListPage` luôn truyền slot mặc định cho thanh công cụ (`components/ListPage.vue:22`), nên `div.workspace-list-actions` luôn được dựng (`components/WorkspaceListToolbar.vue:13`); danh sách không có nút hành động vẫn có một hàng rỗng cộng 10px khoảng cách. (chưa kiểm)
- D6. Số trong tài liệu khác mã: `docs/WORKSPACE_UI_STANDARD.md:17` ghi ô tìm 360/280/420px, CSS là 260/200/380px (`workspace-experience.css:126`).
- D7. Không có chỗ chuẩn cho: nhãn bộ lọc đang bật, nút "Xóa bộ lọc" ở cấp thanh công cụ, thanh hành động hàng loạt khi chọn nhiều dòng. `components/DataTableViews.vue` tự làm phần của bảng.
- D8. Trang "Tổng quan" tự dựng thanh lọc bằng `<label>` cộng `UiSelect` trong `.scope-picker` (`components/ReportsWorkspace.vue`, đầu template), không qua `LotusField` hay thanh công cụ chung.

### E. Hộp thoại

- E1. Ở ≥901px, prop `width` không còn tác dụng với hộp `expanded` (`workspace-experience.css:292`). Có ít nhất 18 giá trị `width` ghi cứng từ 480 đến 1180px ở các nơi gọi, thêm 1040px và 1280px tính ở `components/erp/ErpSection.vue:21`; phần tính này và emit `size` của `ErpForm` thành thừa trên máy tính. Hộp hỏi lý do một ô (`components/form/ReasonDialog.vue:9`, 520px) và bảng tìm nhanh (`components/WorkspaceBar.vue:73`; `compact.css:32` khai 560px) cũng giãn hết bề ngang. (chưa kiểm)
- E2. Kích thước gắn vào cờ `readonly`: `components/form/ModalForm.vue:13` truyền `:expanded="!readonly"`. 27 trong 58 thẻ `ModalForm` có `readonly`; hộp có `readonly` động (ví dụ `components/field/LotEntryModal.vue:108`) đổi bề rộng theo trạng thái.
- E3. `WorkspaceModal` không có vùng chân. Có bốn kiểu chân tự dựng: `.lotus-modal-form__footer` với lề âm `-20px/-18px` khớp cứng với đệm thân (`components/form/ModalForm.vue:31`, `workspace-experience.css:53`); `.erp-form__actions--footer` (`components/erp/ErpForm.vue:186`); `.attendance-toolbar:last-child` (`workspace-experience.css:55`); `.user-form-footer` (`workspace-experience.css:139`). 39 thẻ `WorkspaceModal` trong màn nghiệp vụ không đi qua `ModalForm`.
- E4. Nút lưu không ở mép phải trong hai nơi: hộp chứng từ của `App.vue:246` đặt 14 nút và 1 liên kết trên một hàng ở đầu hộp, canh trái, tất cả `outline`; chân `ErpForm` canh phải nhưng thứ tự là Lưu, Ghi sổ, …, In, Hủy chứng từ (`components/erp/ErpForm.vue:162-169`), nút mép phải là nút nguy hiểm. `ErpForm` lặp nguyên 8 nút hai lần (`:146-153`, `:162-169`).
- E5. Nội dung nổi chưa đồng bộ với top layer. Đưa thẳng ra `body`: `components/ui/dropdown-menu/DropdownMenuContent.vue:5`, `components/ui/tooltip/Tooltip.vue:7`, `components/ColumnVisibilityMenu.vue:26`, `components/DataTableViews.vue:30`, `:34`, `components/ExcelHeader.vue:98`. Bảng nằm trong hộp thoại (ví dụ `components/report/ReportCards.vue:26-30`) sẽ có "Cột hiển thị" và lọc cột mở ra phía dưới hộp, không bấm được. `inject('searchSelectTarget')` ở `components/ui/portal-target.js:5` không có nơi nào `provide`. (chưa kiểm)
- E6. `Toaster` đặt ngoài hộp thoại (`App.vue:248`). Toast "Đã lưu phiếu nháp." (`App.vue:151`) và toast "Có bản nháp chưa lưu" kèm nút "Khôi phục" (`App.vue:212`) xuất hiện lúc hộp chứng từ đang mở, tức nằm dưới lớp phủ mờ và không bấm được. (chưa kiểm)
- E7. Con trỏ khi mở hộp rơi vào nút "Đóng" vì nút này đứng đầu DOM (`components/WorkspaceModal.vue:31`); chỉ `ReasonDialog` (`:10`) và `WorkspaceConfirm` (`:9`) đặt `autofocus`.
- E8. `WorkspaceConfirm` không có tông nguy hiểm và `ask(text, heading)` không truyền được nhãn nút. Hộp "Hủy chứng từ …?" (`components/erp/ErpForm.vue:70`) hiện hai nút "Hủy" và "Đồng ý"; "Hủy" ở đây nghĩa là không làm.
- E9. Còn một `window.prompt` (`App.vue:166`); test chỉ chặn `alert` và `confirm` trên toàn bộ mã.
- E10. Cách dùng thứ ba (ref, không `bare`) ở `components/WorkMaterialSettings.vue` và `FarmWorkApp.vue` không có trong `AGENTS.md:19`.

### F. Biểu mẫu

- F1. Bốn hệ lưới với bốn bộ khoảng cách và ba bộ mốc (mục 9).
- F2. Ba cách sửa bảng con: thẻ xếp chồng "Dòng n" của `SchemaForm` (`components/SchemaForm.vue:29-37`), lưới `LineItemsEditor`, và `ErpChildTable` (lưới cộng hộp "Chi tiết"). Trong `SchemaForm`, "Thêm dòng" và "Xóa dòng" là nút chính màu đỏ (`:30`, `:34`, không khai `variant`), trong khi nút lưu của hộp là `outline` (`App.vue:246`).
- F3. Lỗi theo từng ô không được dùng qua `LotusField`: 0 trong 388 dòng có `<LotusField` truyền `:error`. `FormField :error` có 10 chỗ. Lỗi dồn về một dòng đầu hộp, ví dụ "Cần nhập: A, B, C…" (`components/erp/ErpForm.vue:68`). FR-018 yêu cầu lỗi ngay dưới ô.
- F4. `LotusField`: prop `currency` khai mà không dùng (`components/form/LotusField.vue:26`); nhánh `numeric` ở dòng 64 không bao giờ chạy vì dòng 63 đã bắt; không có slot đầu/cuối ô hay đơn vị; không có loại ngày-giờ và giờ, nên `components/erp/ErpFields.vue:68-69` rơi về `input` gốc.
- F5. `MonthPicker` chỉ liệt kê 24 tháng lùi từ `max` (`components/MonthPicker.vue:8-12`); không chọn được tháng tới nếu nơi gọi không đẩy `max`.
- F6. Ba cách hiện giá trị chỉ đọc: `.field-value` (`components/SchemaForm.vue:39`), `.erp-readonly` (`components/erp/ErpFields.vue:55-59`), prop `readonly` của `LotusField`.
- F7. `App.vue` còn 5 ô `type="date"` gốc và 1 ô `datetime-local` (`App.vue:232`, `:242`, `:246`), 26 thẻ `FormField` tự ghép so với 4 thẻ `LotusField`. `App.vue` không nằm trong danh sách "chuẩn" của `tests/form-standard.test.js:8`.

### G. Trạng thái và phản hồi

- G1. Bảy lớp dòng lỗi cùng tồn tại: `.error` (13 lần), `.stock-error` (25), `.hr-ops-error` (14), `.lotus-list-page__error` (17), `.lotus-modal-form__error` (5), `.erp-form__error` (4), `.lotus-field__error`. Ba khối CSS giống hệt nhau ở `components/ListPage.vue:36`, `components/form/ModalForm.vue:30`, `components/erp/ErpForm.vue:188-189`. Không có component thông báo trong trang.
- G2. Bảy kiểu đang tải, sáu kiểu trống (mục 10). `DesktopEmptyState` chỉ có kiểu trong `@media(min-width:901px)` và dưới `.lotus-ui` (`desktop-components.css:2`, `:15-19`); ở ≤900px không có rule nào. (chưa kiểm)
- G3. Một biến `error` dùng chung cho trang và hai hộp thoại (`App.vue:230`, `:246`, `:247`): lỗi hiện hai nơi cùng lúc, hai nút `role=alert`.
- G4. Năm mẫu số tổng hợp: `.kpi` (`App.vue`, 27 rule ở 4 tệp), `.lotus-stat` (`components/OverviewBoard.vue:18`, 14 lần ở `components/ReportsWorkspace.vue`), `DesktopMetricCard`, `WorkspaceSummaryStrip`, `.report-card`. Ô `.lotus-stat` của trang Tổng quan không bấm được, trái quy ước 4.
- G5. Nhãn trạng thái tự làm ở từng nơi: `.pill` (`App.vue:240`), `.erp-form__status--0|1|2` (`components/erp/ErpForm.vue:180-182`), `.fin-ok`, `.land-bad`, `.land-warn`. Primitive `Badge` chỉ có 1 nơi gọi (màn điện thoại).

### H. Tiếp cận

- H1. `WorkspaceTabs` có `role=tab` nhưng không có `aria-controls` và không có `tabpanel` (`components/WorkspaceTabs.vue:8`). Tab kiểu cũ `.tabs` không có vai trò nào (`App.vue:237`, `:246`).
- H2. 10 rule `focus-visible` ở 9 tệp, 7 giá trị `outline-offset`. Nút vừa có vòng `ring` của Tailwind (`components/ui/button/index.js:6`) vừa có `outline` toàn cục (`workspace-experience.css:4`). Token `--lotus-focus` chỉ dùng ở 3 tệp. (chưa kiểm)
- H3. Không có rule nào cho `prefers-contrast`, `forced-colors`, `@media print` trong `frontend/src`. Không dùng container query, nên nội dung không biết sidebar đang 224 hay 64px.
- H4. Kích thước chữ của điều hướng: mục con sidebar 12px, nhãn nhóm thiết lập 11px (`workspace-experience.css:279`), chân bảng tìm nhanh 10px (`compact.css:41`).

### I. Mã chết, kiểm thử, tài liệu

- I1. SFC không được import ở đâu trong `frontend/src`: `components/ForecastPlanner.vue`, `components/ForecastWorkspace.vue`, `components/Vip126RollingForecast.vue`, `components/PlotMap.vue`, `components/LotusImportPreview.vue`. SFC chỉ tới được qua tệp mồ côi hoặc nhánh chết: `components/DesktopForecastChart.vue`, `components/ZonePlantingSchedule.vue`, `components/OneDriveProcessWorkspace.vue`, `components/OneDriveSupplyDialog.vue`. `components/UiShowcase.vue` chỉ chạy khi dev. `DesktopPageHeading` và `DesktopMetricCard` chỉ có `ForecastPlanner.vue` dùng.
- I2. `tests/desktop-design-system.test.js:31-40` khóa mã chết (bắt `ForecastPlanner.vue` phải dùng ba khối `Desktop*`).
- I3. 155 tệp test, 54 tệp mount, 64 tệp đọc mã nguồn bằng `readFileSync`, 8 tệp khớp chuỗi trong các tệp CSS của khung. `tests/support/mount.mjs` bỏ mọi CSS khi biên dịch, nên không test nào thấy bố cục, màu hay thứ tự lớp. Không có Playwright (`docs/UI_AUDIT_FULL_20261019.md:55` đã ghi).
- I4. Trang mẫu nạp 10/20 tệp CSS của bản thật và không có `ListPage`, `WorkspaceListToolbar`, `ModalForm`, `LineItemsEditor`, `LotusField`, `FormGrid`, `FormSection`, sidebar, thanh đầu trang, `WorkspaceConfirm`, `ReasonDialog`, `WorkspaceSummaryStrip`.
- I5. Ba tài liệu lệch mã. `docs/COMPACT_WORKSPACE.md:10` ghi thanh đầu màu than cao 50px (nay đỏ, 60px); `:14-15` ghi dùng popover gốc của trình duyệt (mã dùng Teleport và portal reka); dòng 17–46 là nghiệp vụ kho. `docs/UI_STACK.md:10-12` liệt kê 7 primitive (nay 19 thư mục), nhắc `AssignApp.vue` (không còn), nói còn dùng Frappe UI (`tests/ui-stack.test.js:51` nói chỉ còn preset); `:42` là ghi chú trạng thái ngày 13/10. `docs/LOTUS_DESKTOP_UI_STANDARD_20261017.md:13` ghi "màu đất nung"; `:25` yêu cầu CSS máy tính chỉ ở ≥901px trong khi phần lớn `workspace-experience.css` nằm ngoài `@media`; `docs/LOTUS_SIDEBAR_NGHIEP_VU.md:16-27` mô tả menu đã đổi.

## Thiếu so với một bộ giao diện đầy đủ

1. Component khung tách khỏi nghiệp vụ (khung, sidebar, thanh đầu trang, vùng trang) và token bố cục: bề rộng sidebar, chiều cao thanh đầu trang, đệm trang, thang z-index, bộ mốc bề rộng.
2. Một registry điều hướng: mỗi phân hệ khai một lần đường dẫn, nhãn, biểu tượng, nhóm, quyền, component, tham số màn con. Kèm tên tab trình duyệt theo màn.
3. Hệ lớp nổi thống nhất: cỡ hộp thoại theo tên, vùng chân, ngăn kéo cạnh dùng thật (`Sheet` mới có 1 nơi gọi: `components/timekeeping/TkDailyDetails.vue`), mọi nội dung nổi và toast tự vào hộp đang mở, trả con trỏ về nút đã mở (FR-019, FR-020).
4. Dải thông báo trong trang bốn mức có hành động; khối trạng thái chung cho trống, đang tải, lỗi kèm "Thử lại", không quyền, mất mạng; màn chờ khi khởi động; khung chờ cho biểu mẫu.
5. Nhãn trạng thái dùng chung với bảng từ vựng (FR-005); chữ cái đại diện cho người; nhãn đếm trên mục menu.
6. Ô số liệu và lưới thẻ có bấm mở hộp chi tiết (quy ước 4), thay năm mẫu hiện có.
7. Thanh lọc chuẩn: nhãn bộ lọc đang bật, "Xóa bộ lọc", khoảng ngày nhanh, thanh hành động hàng loạt.
8. Mẫu trang chi tiết chứng từ: đầu hộp có trạng thái, danh sách cặp tên–giá trị, các bước duyệt/ký, dòng thời gian lịch sử, chứng từ liên quan. Hiện có `.audit-drawer` (`App.vue:246`), `.erp-readonly`, `components/LotusSignatureTimeline.vue` rời nhau.
9. Biểu mẫu: lỗi theo ô và tóm tắt lỗi có nhảy tới ô; chọn ngày-giờ và giờ; ô số kèm đơn vị; công tắc, chọn theo đoạn, chọn nhiều; các bước của một quy trình nhập nhiều bước; chỉ báo "chưa lưu" và "đã lưu nháp" dùng chung.
10. Phím tắt: nơi đăng ký chung, bảng liệt kê, lưu bằng bàn phím trong hộp nhập, phím vào ô tìm.
11. Sidebar: menu bật ra khi thu gọn, đi bằng phím mũi tên, nhớ nhóm đã mở, số việc chờ trên mục.
12. Chỉ báo đồng bộ/mất mạng và hàng chờ ở thanh đầu trang (nay là hai dòng chữ trong nội dung, `App.vue:230`).
13. Mật độ gọn/thoáng có nút chọn (FR-003); kiểu in; `prefers-contrast`; container query cho vùng nội dung.
14. Mẫu bố cục nông nghiệp ở cấp khung: bản đồ cạnh danh sách, lưới thẻ lô, thanh ngữ cảnh vườn–vụ–tuần. Trang bản đồ hiện là ngoại lệ viết tay (`care-map.css`, 3 lần `!important`).
15. Trang mẫu cho khung và các mẫu ghép, dùng đúng bộ CSS của bản thật; kiểm tra hình ảnh tự động chạy trên GitHub Actions.

## Đề xuất cho bộ giao diện mới

Giữ tên và API công khai của các component ở mục 6; thay phần ruột và CSS. Việc nào đụng test khớp chuỗi thì sửa test trong cùng thay đổi. Test và build chạy trên máy chủ thử hoặc GitHub Actions.

### P0 — nền của khung (làm trước, các phần khác dựa vào)

1. **Layer và một tệp cho khung.** Khai thứ tự layer một lần (reset → token → nền → primitive → mẫu ghép → khung → phân hệ → tiện ích). Viết lại CSS khung vào một tệp trong layer "khung", dùng token mới: sidebar 224px, thu gọn 64px, thanh đầu trang 60px, đệm trang 22px (14px ở 901–1160px), thang z-index có tên. Gỡ phần khung khỏi `style.css`, `attio.css`, `compact.css`, `desktop-system.css`, `desktop-shell.css`, `workspace-experience.css`. Mục tiêu đo được: 0 rule `:root:root`, 0 `!important` trong CSS khung; `.sidebar` và `.app-shell` chỉ còn ở một tệp. Giữ mốc 901px và ba số 60/224/64.
2. **Bộ mốc bề rộng cố định.** Chọn 4 mốc (đề xuất 700, 900, 1160, 1440px) thay 15 mốc; sửa khoảng trống 651–700px bằng cách cho điều hướng dưới hiện từ ≤700px.
3. **Tách khung khỏi `App.vue`.** Tạo component khung nhận `nav`, `title`, slot nội dung; `App.vue` chỉ còn phiên, phạm vi, chọn màn. Chuyển 4 nhánh trang riêng và danh sách chung thành SFC nạp trễ như 10 phân hệ. Xóa các nhánh chết ở B3, sửa `forecastClosed` ở B4. Thêm màn chờ khởi động thay cho nhánh `today`.
4. **Registry điều hướng.** Một tệp khai mỗi phân hệ một lần; `router.js`, sidebar, tên màn, bảng tìm nhanh, ô chuyển phân hệ, điều hướng dưới cùng đọc từ đó. Giữ nguyên tên tham số URL hiện có (liên kết cũ). Sidebar nhận một prop `view` thay 5 prop. Đặt `document.title` theo tên màn.
5. **Hộp thoại có cỡ và có chân.** Thêm prop `size` cho `WorkspaceModal` (đề xuất `sm` 480, `md` 720, `lg` 960, `xl` 1200, `full`) và slot `footer`; `ModalForm` và `ErpForm` dùng slot này, bỏ lề âm. Biểu mẫu nhập giữ `full` theo commit `5859e30`; hộp xác nhận, hộp lý do, bảng tìm nhanh, hộp chỉ xem dùng cỡ cố định. Tách `readonly` khỏi kích thước. `width` cũ ánh xạ sang cỡ gần nhất để không sửa 100 nơi gọi cùng lúc. Đặt con trỏ vào ô đầu tiên của biểu mẫu.
6. **Lớp nổi vào đúng hộp.** Cho `DropdownMenuContent`, `Tooltip`, `PopoverContent` mặc định dùng `useDialogPortal()`; sửa `ColumnVisibilityMenu`, `DataTableViews`, `ExcelHeader`; cho vùng toast chuyển vào hộp thoại trên cùng khi có hộp mở. Thêm test mount cho từng loại nằm trong `WorkspaceModal`.
7. **Chốt 5 điểm mâu thuẫn** ở mục Ràng buộc trước khi vẽ thanh công cụ và hộp thoại; ghi kết quả vào `AGENTS.md`.

### P1 — mẫu ghép

8. **Trang danh sách.** Chuyển 10 trang danh sách chung của `App.vue` sang `ListPage`. Thêm vào thanh công cụ: nhãn bộ lọc đang bật, "Xóa bộ lọc", thanh hành động hàng loạt. Bỏ `order:-1`, để DOM đúng thứ tự đã chốt. Không dựng hàng 1 khi không có nút. Bỏ `h2` trong `ErpReport`, đưa "Chạy báo cáo" về hàng 1 bên trái.
9. **Thông báo và trạng thái.** Một component dải thông báo bốn mức thay 7 lớp lỗi; một component trạng thái (trống, đang tải, lỗi kèm "Thử lại", không quyền, mất mạng) có kiểu ở mọi bề rộng; `DesktopEmptyState` thành lớp bọc. Lỗi trong hộp thoại dùng biến riêng của hộp.
10. **Biểu mẫu.** Một hệ lưới (`FormGrid`) cho cả `SchemaForm` và `ErpFields`; bảng con đều đi qua `LineItemsEditor`; `LotusField` thêm loại ngày-giờ, giờ, slot đơn vị, bỏ `currency` và nhánh chết; nối lỗi theo ô từ máy chủ vào prop `error`, kèm tóm tắt lỗi đầu hộp có nhảy tới ô. `ErpForm` khai danh sách nút một lần, thứ tự chân: nút nguy hiểm bên trái (slot `secondary`), Lưu/Ghi sổ ở mép phải.
11. **Xác nhận.** `ask()` nhận nhãn nút và tông; hành động hủy/xóa dùng tông nguy hiểm, nhãn nút là động từ ("Hủy chứng từ" / "Không hủy"), con trỏ mặc định ở nút an toàn. Thay `window.prompt` ở `App.vue:166` bằng `ReasonDialog` và mở rộng test chặn `prompt`.
12. **Số tổng hợp.** Một ô số liệu và lưới thẻ bấm mở hộp chi tiết, gom `.kpi`, `.lotus-stat`, `DesktopMetricCard`, `.report-card`; `WorkspaceSummaryStrip` giữ cho dải số trên bảng. Ô thiếu số hiện "—" kèm lý do (FR-034).
13. **Tab và sidebar.** `WorkspaceTabs` thêm `aria-controls` và vùng `tabpanel`; thay `.tabs` cũ. Sidebar: menu bật ra khi thu gọn, phím mũi tên, nút mở nhóm tối thiểu 32px, chữ mục con 13px, bỏ `variant="outline"` rồi xóa kiểu, thêm biến thể nút điều hướng trong primitive.
14. **Thanh đầu trang.** Thẻ `header` có vai trò; nút 36px; token "trên nền chính" thay việc định nghĩa lại `--lotus-text` tại chỗ; chỉ báo hàng chờ và mất mạng thành một nhãn trên thanh; bỏ `branded`; bảng tìm nhanh chia nhóm (màn, thao tác, bản ghi) và nhớ mục vừa mở.
15. **Phím tắt và mật độ.** Một composable đăng ký phím tắt kèm bảng liệt kê; thêm lưu trong hộp nhập và phím vào ô tìm. Nối nút chọn mật độ vào khung, đọc khóa `lotus-desktop-density` đang có, cấp cho `DataTable` qua `provide` ở cấp khung thay cho `use-desktop-workspace.js`.

### P2 — dọn và giữ chuẩn

16. Xóa CSS chết ở A9, SFC mồ côi ở I1 (sau khi sửa `tests/desktop-design-system.test.js`), `use-desktop-workspace.js`, các trường không dùng ở C1 và C3.
17. Đưa các lớp dùng chung đang nằm trong SFC nghiệp vụ (A8) về CSS của bộ.
18. Trang mẫu thêm mục "Khung và mẫu ghép": khung đủ ba bề rộng, trang danh sách, hộp nhập, hộp xác nhận, trang tổng hợp theo thẻ; nạp đúng bộ CSS của bản thật.
19. Thay test khớp chuỗi CSS (`tests/scope-filterbar-layout.test.js`, phần CSS của `tests/desktop-design-system.test.js`) bằng test mount cộng một bộ kiểm tra hình ảnh trên GitHub Actions cho khung ở 1440, 1024, 768px, sáng và tối.
20. Gộp ba tài liệu trong phạm vi và `docs/WORKSPACE_UI_STANDARD.md` thành một hướng dẫn tiếng Việt của bộ giao diện (FR-042); chuyển phần nghiệp vụ kho của `docs/COMPACT_WORKSPACE.md` sang tài liệu kho.
