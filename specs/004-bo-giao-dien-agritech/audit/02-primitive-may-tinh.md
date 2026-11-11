# 02 — Primitive máy tính: `frontend/src/components/ui/**` và helper

Phạm vi: `frontend/src/components/ui/**`, `frontend/src/lib/**`, `components/ui/portal-target.js`, `src/use-toast.js`, `src/use-confirm-core.js`, `src/use-workspace-confirm.js`, `src/dialogs.js`, `components/LotusIcon.vue`, `components/UiShowcase.vue`, `src/showcase-main.js`, `frontend/showcase.html`.

Cách kiểm: chỉ đọc mã ở nhánh `004-bo-giao-dien-agritech`, commit `40f8330`, ngày 10/11/2026. Đếm bằng `grep`/`wc` và một script Perl đọc thẻ có tính dấu nháy. Không chạy `npm`, test, build hay trình duyệt.

Giới hạn cần biết khi đọc:

- Thư mục `frontend/node_modules` không có trên máy này. Hành vi bàn phím và ARIA do reka-ui cấp được ghi theo tài liệu reka-ui 2.x và theo các test mount trong repo; phần nào không có test xác nhận thì ghi "chưa kiểm".
- Giá trị CSS sau biên dịch lấy từ bản build đã commit: `lotus_farm/public/frontend/assets/shadcn-8_U6msli.css` và `index-BYaQUi6F.css`.
- Các kết luận về "rule nào thắng" suy ra từ độ ưu tiên (specificity) của selector. Chưa kiểm trên trình duyệt. Những chỗ này có ghi "suy ra từ CSS".
- Số đếm thẻ có tính cả `components/UiShowcase.vue` và ba component không còn tệp nào import (`ForecastPlanner.vue`, `ForecastWorkspace.vue`, `Vip126RollingForecast.vue`).
- Trong lúc kiểm, cây làm việc có thêm tệp chưa commit do bước khác tạo: `frontend/vite.showcase.config.js`, script `showcase:build` trong `frontend/package.json`, `frontend/tests/support/css-tokens.mjs`. Bản kiểm này không tạo và không sửa các tệp đó.

## Hiện trạng

### 1. Tổng quan

| Mục | Số liệu | Nguồn |
|---|---|---|
| Thư mục primitive | 19 thư mục + `portal-target.js` | `frontend/src/components/ui/` |
| Tệp, dòng, dung lượng | 53 tệp, 796 dòng, 58.401 byte | `wc -lc` |
| Thư viện | reka-ui 2.11.0, class-variance-authority 0.7.1, clsx 2.1.1, tailwind-merge 2.6.0, @internationalized/date 3.12.4 | `frontend/package.json:12-31` |
| Tailwind | tailwindcss 3.4.19, preset `frappe-ui/tailwind` (frappe-ui 1.0.0), plugin tailwindcss-animate 1.0.7 | `frontend/tailwind.config.js:1-30` |
| Cấu hình shadcn-vue | style `new-york`, `typescript:false`, css `src/shadcn.css` | `frontend/components.json` |
| Tệp import reka-ui | 12 tệp, tất cả nằm trong `components/ui`; ngoài `ui` là 0 | `grep "from 'reka-ui'"` |
| Tệp dùng `cva` | 2 (`badge/index.js`, `button/index.js`) | `grep class-variance-authority` |
| Tệp dùng `cn()` | 14 lần import `@/lib/utils`, tất cả trong `components/ui` | `grep "@/lib/utils"` |
| CSS Tailwind sau build | 37.189 byte, 313 rule | `lotus_farm/public/frontend/assets/shadcn-8_U6msli.css` |
| Lịch sử | thêm ngày 13/10/2026 (`c59f6da`), bản v2 trên reka-ui ngày 19/10/2026 (`081bb6e`), 45 commit chạm `components/ui`, gần nhất 05/11/2026 (`0ee18de`) | `git log` |

Bộ primitive đang dùng hai cách viết kiểu:

| Cách | Thư mục | Token |
|---|---|---|
| Class Tailwind trong template, ghép bằng `cn()` | `badge`, `button`, `card`, `input`, `select`, `separator`, `skeleton`, `textarea` (8) | Biến HSL kiểu shadcn: `--primary`, `--input`, `--ring`, `--destructive`… (`lotus-tokens.css`, khối cuối `:root`) |
| Class BEM `.lotus-*` trong `<style>` không `scoped` hoặc tệp `.css` riêng | `checkbox`, `combobox`, `date-picker`, `dropdown-menu`, `file-input`, `form-field`, `pagination`, `popover`, `sheet`, `toast`, `tooltip` (11) | `--lotus-*` |

Ngoài `components/ui`, utility Tailwind chỉ xuất hiện trong 3 tệp: `components/ReleaseNotes.vue:30-33`, `components/WorkspaceBar.vue:45,52,56`, `components/WorkspaceListToolbar.vue` (`sr-only`).

Giá trị thật của các class Tailwind chính (đọc từ `shadcn-8_U6msli.css`):

- `.text-sm{letter-spacing:.02em;font-size:13px;font-weight:420;line-height:1.35}`, `.text-xs` = 12px, `.text-lg` = 16px. Đây là thang của preset frappe-ui, không phải thang Tailwind gốc.
- `.rounded-md{border-radius:calc(var(--radius) - 2px)}` = 8px, `.rounded-lg` = 10px (`--radius:.625rem`).
- `.h-9`, `.min-h-9` = 36px; `.min-h-8` = 32px; `.min-h-10` = 40px.
- `.shadow-sm{--tw-shadow:var(--elevation-sm)…}`. Biến `--elevation-sm` là của frappe-ui, chỉ được định nghĩa trong `index-BYaQUi6F.css` (gói máy tính).
- Các class `hover:*` nằm trong `@media (hover:hover) and (pointer:fine)`.

Thứ tự nạp CSS của máy tính: `frontend/src/main.js:6-29`. `style.css` và `stock.css` nằm trong `@layer lotus-legacy`. Các tệp còn lại (`attio.css`, `compact.css`, `desktop-system.css`, `workspace-experience.css`, CSS phân hệ, `shadcn.css`, `<style>` của primitive) không nằm trong layer nào.

### 2. Từng primitive

Số "tệp import" là số tệp `.vue`/`.js` trong `frontend/src` có `from '…ui/<thư mục>…'`, không tính chính thư mục đó và không tính import nội bộ trong `ui`.

#### `badge/` — Badge

- Tệp: `Badge.vue` (7 dòng), `index.js` (10 dòng).
- Export: `Badge`, `badgeVariants`.
- Props: `variant` (String, mặc định `'default'`). Không emit. Slot mặc định. `inheritAttrs:false`, `$attrs` gắn vào `<span>`.
- Biến thể (`badge/index.js:3-10`):

```js
export const badgeVariants=cva('inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',{
  variants:{variant:{
    default:'border-transparent bg-primary text-primary-foreground',
    secondary:'border-transparent bg-secondary text-secondary-foreground',
    destructive:'border-transparent bg-destructive text-destructive-foreground',
    outline:'text-foreground',
  }},defaultVariants:{variant:'default'}
})
```

- Không có cỡ. Không có tông đạt/cảnh báo/thông tin. Không có chỗ cho icon hay chấm màu.
- A11y: là `<span>`, không có role. Có class focus ring nhưng phần tử không nhận focus.
- Dùng: 0 tệp import. `tests/ui-stack.test.js:38` yêu cầu `badge/index.js` tồn tại.

#### `button/` — Button

- Tệp: `Button.vue` (30 dòng), `index.js` (24 dòng).
- Export: `Button`, `buttonVariants`.
- Props (`Button.vue:7-15`): `variant` (`'default'`), `size` (`'default'`), `as` (`'button'`), `asChild` (false), `type` (`'button'`), `loading` (false), `disabled` (false). Không khai emit; `click` đi qua `$attrs`. Slot mặc định.
- `loading`: thêm `<span class="lotus-button-spinner" aria-hidden="true">`, đặt `disabled` và `aria-busy` (`Button.vue:23-27`). CSS của spinner nằm ở `attio.css` (`.lotus-button-spinner`, `@keyframes lotus-spin`), không nằm trong `ui`.
- Biến thể và cỡ (`button/index.js:5-24`):

```js
export const buttonVariants=cva(
  'inline-flex min-w-0 max-w-full items-center justify-center gap-2 whitespace-normal break-words rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {variants:{
    variant:{
      default:'bg-primary text-primary-foreground hover:bg-primary/90',
      destructive:'bg-destructive text-destructive-foreground hover:bg-destructive/90',
      outline:'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
      secondary:'bg-secondary text-secondary-foreground hover:bg-secondary/80',
      ghost:'hover:bg-accent hover:text-accent-foreground',
      link:'text-primary underline-offset-4 hover:underline',
    },
    size:{
      default:'min-h-9 h-auto px-4 py-2',
      sm:'min-h-8 h-auto rounded-md px-3 py-1 text-xs',
      lg:'min-h-10 h-auto px-8 py-2',
      icon:'h-9 w-9',
    },
  },
  defaultVariants:{variant:'default',size:'default'}}
)
```

- Giá trị hiển thị: chữ 13px đậm 500, bo 8px, cao tối thiểu 36/32/40px, nút icon 36×36px. Chữ được xuống dòng (`whitespace-normal break-words`).
- A11y: `<button type="button">` gốc. Focus: ring 2px màu `--ring` cách 2px. Vô hiệu: `opacity:.5` và `pointer-events:none`. Nút chỉ có icon phải tự thêm `aria-label`; component không ép.
- Dùng: 87 tệp import, 591 thẻ (448 `<UiButton>` ở 71 tệp, 87 `<Button>` ở 9 tệp, 56 `<component :is="button">` ở 7 tệp).

| Thuộc tính | Số thẻ |
|---|---|
| `variant="outline"` | 340 |
| không ghi `variant` (mặc định) | 165 |
| `variant="ghost"` | 53 |
| `variant="destructive"` | 16 |
| `variant="link"` | 10 |
| `:variant` động (`'default'`/`'outline'`) | 7 |
| `variant="secondary"` | 0 |
| `size="sm"` | 119 |
| `size="icon"` | 6 |
| `size="lg"` | 0 |
| có `loading` | 11 |
| có `class` riêng | 40 |
| có `title` | 22 |

- Ví dụ: `src/App.vue:230`, `src/ColorTagCatalogApp.vue:91`, `src/components/AiChatBubble.vue:52`.
- Dùng chung khuôn với điện thoại: 7 tệp chọn `LotusMobileButton` hoặc `Button` bằng `computed` rồi render `<component :is="button">` (`components/ProcurementWorkspace.vue` 45 thẻ, `ProcurementMasters.vue:70-76`, `ProcurementDocumentForm.vue:102-103`, `ProcurementMasterForm.vue:60`, `MobileSupplierForm.vue:39`, `PurchaseProgress.vue:10`, `StockReceiptReason.vue:12`).

#### `card/` — Card

- Tệp: `Card.vue`, `CardHeader.vue`, `CardTitle.vue`, `CardDescription.vue`, `CardContent.vue`, `CardFooter.vue` (mỗi tệp 5 dòng), `index.js`.
- Không có props. Slot mặc định. `$attrs` đi thẳng vào phần tử gốc.
- Class: Card `rounded-lg border border-border bg-card text-card-foreground shadow-sm`; Header `flex flex-col space-y-1.5 p-6`; Title là `<h3>` `text-lg font-semibold leading-none tracking-tight`; Description `text-sm text-muted-foreground`; Content `p-6 pt-0`; Footer `flex items-center p-6 pt-0`.
- Dùng: 1 tệp (`components/MobileHome.vue:5,19`, `<UiCard class="mobile-welcome">`). Năm phần con: 0 nơi dùng.

#### `checkbox/` — Checkbox

- Tệp: `Checkbox.vue` (20 dòng), `index.js`.
- Props: `modelValue` (Boolean), `disabled`, `required`, `id`. Emit `update:modelValue` (luôn là boolean). Không có slot.
- Dựng trên `CheckboxRoot` + `CheckboxIndicator` của reka-ui, dấu tích là `<LotusIcon name="tick"/>`.
- Kiểu (`Checkbox.vue:15-19`): ô 18×18px, viền `--lotus-border-strong`, bo 4px ghi cứng, đã chọn nền `--lotus-primary`, vô hiệu `opacity:.5`.
- A11y: render `button[role=checkbox]` (xác nhận ở `tests/form-standard.mount.test.js:40`, `tests/user-access.mount.test.js:18`). Focus: `outline:2px solid var(--lotus-primary)` cách 2px. Không có nhãn kèm; nơi dùng tự gắn `<label for>` hoặc `aria-label`. Không có trạng thái "chọn một phần".
- Dùng: 6 tệp, 8 thẻ. Ví dụ: `components/form/LotusField.vue:52`, `components/SchemaForm.vue:45`, `components/UserRolePicker.vue:24`.

#### `combobox/` — Combobox

- Tệp: `Combobox.vue` (89 dòng), `index.js`.
- Props (`Combobox.vue:11`): `modelValue` (String|Number), `options` (mảng `{value,label,subtitle?,group?}`), `fetchOptions(search)`, `displayValue`, `label`, `placeholder` (`'Chọn hoặc gõ để tìm…'`), `hideValues`, `disabled`, `readonly`, `required`, `allowCustom`.
- Emit: `update:modelValue`, `change`, `select` (trả cả dòng). Không có slot.
- Hành vi: lọc tại chỗ không phân biệt dấu (`src/option-search.js`); tải từ máy chủ có trễ 150ms và bỏ kết quả cũ (`Combobox.vue:24-36`); ba trạng thái "Đang tải…", lỗi, "Không tìm thấy lựa chọn."; tiêu đề nhóm; dấu tích ở mục đang chọn; tự render danh sách vào `<dialog>` đang mở (`Combobox.vue:15-16`).
- Kiểu (`Combobox.vue:69-88`): ô cao `--lotus-control-height`, viền `--lotus-border-strong`, bo `--lotus-radius-md`, chữ `--lotus-text-base` (14px); nút mở 28×28px; danh sách rộng tối thiểu 280px, cao tối đa 320px, mục cao tối thiểu 36px; `z-index:2147482000`.
- A11y: ô nhập có `role=combobox`, mục có `role=option` (xác nhận ở `tests/components.mount.test.js:10,16`). `aria-label` lấy từ thuộc tính hoặc prop `label`. Nút mở có `aria-label="Mở danh sách lựa chọn"` và `tabindex="-1"`. Trạng thái dùng `role=status`/`role=alert`. Tiêu đề nhóm là `<div role="presentation">`. Phím mũi tên, Enter, Esc do reka-ui cấp (chưa kiểm).
- Dùng: 6 tệp, 43 thẻ. Ví dụ: `components/finance/FinanceAssets.vue:142`, `components/finance/FinancePlanning.vue:92`, `components/form/LotusField.vue:57`. Hai lớp bọc cũ: `components/SearchSelect.vue` (3 tệp import), `components/LinkPicker.vue` (2 tệp import).

#### `date-picker/` — DatePicker, DateRangePicker

- Tệp: `DatePicker.vue` (67 dòng), `DateRangePicker.vue` (63), `date-picker.css` (43), `date-value.js` (19), `range-presets.js` (11), `index.js` (4).
- Export: `DatePicker`, `DateRangePicker`, `rangePresets`.
- `DatePicker` — props (`DatePicker.vue:9`): `modelValue` (chuỗi `YYYY-MM-DD`), `min`, `max`, `disabled`, `readonly`, `required`, `label`, `clearable` (true). Emit `update:modelValue`, `change`. Không slot. Là một ô chữ gõ `dd/mm/yyyy` (`inputmode="numeric"`), tự kiểm ngày sai và ngoài khoảng bằng `setCustomValidity` (`DatePicker.vue:15-23`), chuẩn hoá khi rời ô, có lịch bật ra với nút "Hôm nay" và "Xóa".
- `DateRangePicker` — props (`DateRangePicker.vue:11`): `from`, `to`, `disabled`, `label` (`'Khoảng ngày'`), `presets` (true). Emit `update:from`, `update:to`, `change({from,to})`. Ô nhập chia đoạn ngày/tháng/năm của reka-ui, lịch hai tháng, 6 khoảng nhanh (`range-presets.js:4-11`) và nút "Bỏ chọn".
- Cả hai: `locale="vi-VN"`, tuần bắt đầu thứ Hai, tự render lịch vào `<dialog>` đang mở.
- `date-value.js`: `toCalendarDate`, `fromCalendarDate`, `formatDateInput`, `parseDateInput`, `todayValue`.
- Kiểu (`date-picker.css`): ô cao `--lotus-control-height`, viền `--lotus-border-strong`, chữ `--lotus-text-md` (13px); nút lịch 28×28px; nút chuyển tháng 30×30px; ô ngày 36×34px; nút khoảng nhanh cao 32px; nút chân lịch cao 30px; `z-index:2147482000`; dưới 640px lịch khoảng xếp dọc.
- A11y: nhãn tiếng Việt cho nút ("Mở lịch", "Tháng trước", "Tháng sau", "Mở lịch chọn khoảng ngày", "Ngày từ"…). `aria-invalid` đặt trên khung và ô nhập. Ô ngày có focus `box-shadow:var(--lotus-focus)`. Điều hướng lịch bằng phím do reka-ui cấp (chưa kiểm).
- Dùng: 15 tệp. `DatePicker` 22 thẻ ở 9 tệp, `DateRangePicker` 10 thẻ ở 9 tệp. Ví dụ: `components/finance/FinanceAssets.vue:190`, `components/OneDriveSupplyDialog.vue:61`, `components/ProcurementWorkspace.vue:327`.

#### `dropdown-menu/` — DropdownMenu

- Tệp: `DropdownMenuContent.vue` (5 dòng), `DropdownMenuItem.vue` (6), `dropdown-menu.css` (9), `index.js` (5).
- Export: `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuLabel`, `DropdownMenuSeparator` (xuất thẳng từ reka-ui); `DropdownMenuContent` (props `align='start'`, `sideOffset=6`); `DropdownMenuItem` (prop `disabled`, emit `select`).
- Kiểu: `.lotus-menu` rộng 200–320px, bo `--lotus-radius-lg`, bóng `--lotus-shadow-lg`; mục cao tối thiểu 34px; mục đang trỏ nền `--lotus-hover`; `z-index:2147482000`.
- A11y: phím mũi tên, gõ chữ để nhảy, Esc, trả focus do reka-ui cấp (ghi ở `index.js:1`; chưa kiểm).
- Không có mục dạng hộp kiểm, chọn một, menu con, menu chuột phải.
- Dùng: 5 tệp, 8 menu, 25 mục. Ví dụ: `components/WorkspaceBar.vue:48,57`, `components/DataTableViews.vue:32`, `src/TimekeepingApp.vue:279`.

#### `file-input/` — FileInput, FilePickerButton

- Tệp: `FileInput.vue` (13 dòng), `FilePickerButton.vue` (14), `index.js`.
- `FileInput` — props: `accept`, `multiple`, `disabled`, `required`. Emit `update:modelValue` (File, File[] hoặc null) và `change` (sự kiện gốc). Là `<input type="file">` viền nét đứt.
- `FilePickerButton` — props (`FilePickerButton.vue:6`): `accept`, `multiple`, `capture`, `disabled`, `label` (bắt buộc), `variant='outline'`, `size`, `as` (mặc định `Button`), `buttonClass`. Emit `files(File[])`. Slot mặc định là nội dung nút. Ô file ẩn mang `aria-label`.
- Không có vùng kéo thả, danh sách tệp, xem trước, tiến độ, giới hạn dung lượng.
- Dùng: 7 tệp; `FileInput` 3 thẻ, `FilePickerButton` 6 thẻ. Ví dụ: `components/finance/FinanceAssets.vue:274`, `components/stock/StockEvidence.vue:37`, `components/InternalChat.vue:230`.

#### `form-field/` — FormField

- Tệp: `FormField.vue` (25 dòng), `index.js`.
- Props: `label`, `hint`, `error`, `required`, `id`. Slot mặc định nhận `{id, required, 'aria-invalid', 'aria-describedby'}` (`FormField.vue:8`). Nơi dùng phải viết `v-slot="f"` và `v-bind="f"` lên ô nhập.
- Hiển thị: nhãn, dấu `*`, rồi lỗi hoặc gợi ý (có lỗi thì không hiện gợi ý).
- Kiểu: nhãn 12px đậm 550; lỗi màu `--lotus-danger`; gợi ý màu `--lotus-muted`. Nhãn dùng `:root:root .lotus-field__label` để thắng rule `label{…}` toàn cục.
- Dùng: 24 tệp, 198 thẻ. Ví dụ: `src/App.vue:232`, `components/DataTableViews.vue:30`, `components/finance/FinanceAssets.vue:185`.

#### `input/` — Input, MoneyInput

- Tệp: `Input.vue` (29 dòng), `MoneyInput.vue` (29), `model.js` (6), `index.js`.
- `Input` — props: `modelValue` (String|Number), `modelModifiers`, `type='text'`, `disabled`. Emit `update:modelValue`. Giữ hành vi `v-model.number` qua `normalizeInputValue` (`model.js`). Class (`Input.vue:26`): `flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring aria-[invalid=true]:border-destructive aria-[invalid=true]:focus-visible:ring-destructive disabled:cursor-not-allowed disabled:opacity-50`.
- `MoneyInput` — props: `modelValue`, `disabled`. Emit `update:modelValue`, `blur`, `focus`. Là ô chữ `inputmode="decimal"`, canh phải, `tabular-nums`. Nhận cả "," và "." (`src/money-format.js`), khi rời ô hiện dạng `26.571.428,571`.
- Không có tiền tố, hậu tố đơn vị, nút xoá, nút cộng trừ, chặn min/max.
- Dùng: 24 tệp, 110 thẻ `Input` (85 `<UiInput>`, 25 `<Input>`) và 6 thẻ `MoneyInput`. Ví dụ: `src/App.vue:232`, `components/ForecastPlanner.vue:69`, `components/SchemaForm.vue:46`.

| `type` trên thẻ Input | Số thẻ |
|---|---|
| `number` | 25 |
| `search` | 11 |
| `date` | 10 |
| `email` | 3 |
| `datetime-local` | 3 |
| `time` | 2 |
| `tel` | 2 |
| `month` | 1 |
| `file` | 1 |

#### `pagination/` — Pagination

- Tệp: `Pagination.vue` (54 dòng), `index.js`.
- Props (`Pagination.vue:9`): `start`, `count`, `pageSize=50`, `total`, `hasMore`, `disabled`, `sizeSelectable=true`. Emit `update:start`, `update:pageSize`.
- Hai chế độ: có `total` thì hiện số trang (reka `PaginationRoot`); không có `total` thì hiện "Trước"/"Tiếp" theo `hasMore`. Cỡ trang 20/50/100 và nút "Hiện toàn bộ" (`pageSize=0`).
- Kiểu: nút cao 32px, rộng tối thiểu 32px; trang đang chọn nền `--lotus-primary`. Có rule riêng cho nút trò chuyện: `body:has(.ai-chat) .app-shell .lotus-pagination{padding-inline-end:…}` (`Pagination.vue:50-53`).
- A11y: `<nav aria-label="Phân trang">`; dải số có `aria-live="polite"`; nút có `aria-label` "Trang trước", "Trang sau", "Trang N".
- Dùng: 5 tệp, 7 thẻ. Ví dụ: `src/App.vue:236`, `components/DataTable.vue:343`, `components/ListPage.vue:29`.

#### `popover/` — Popover

- Tệp: `PopoverContent.vue` (13 dòng), `index.js`.
- Export: `Popover`, `PopoverTrigger`, `PopoverClose` (từ reka-ui); `PopoverContent` (props `align='start'`, `side='bottom'`, `sideOffset=6`, `to='body'`).
- Kiểu: `.lotus-popover` đệm 12px, bo `--lotus-radius-lg`, `z-index:2147482000`. Không có mũi tên.
- A11y do reka-ui cấp (chưa kiểm).
- Dùng: 3 tệp. `components/ColumnVisibilityMenu.vue:22`, `components/DataTableViews.vue:28`, `components/UiShowcase.vue:52`. `PopoverClose`: 0 nơi dùng. Prop `to`: 0 nơi truyền.

#### `select/` — Select

- Tệp: `Select.vue` (10 dòng), `index.js`.
- Props: `modelValue` (String|Number). Emit `update:modelValue`; gọi tiếp `onChange` của nơi dùng. Là `<select>` gốc, slot nhận các `<option>`.
- Class: `h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:… aria-[invalid=true]:… disabled:opacity-50`. Không có `shadow-sm` như `Input`.
- Dùng: 21 tệp, 75 thẻ (63 `<UiSelect>`, 12 `<Select>`), thêm 1 lần trong `Pagination.vue:19`. Ví dụ: `src/App.vue:233`, `components/MonthPicker.vue:16`, `components/WorkspaceBar.vue:52`.

#### `separator/` — Separator

- Tệp: `Separator.vue` (12 dòng), `index.js`. Props `orientation='horizontal'`, `decorative=true`. Dựng trên `Separator` của reka-ui.
- Dùng: 0 tệp import. `tests/ui-stack.test.js:38` yêu cầu thư mục tồn tại.

#### `sheet/` — Sheet

- Tệp: `Sheet.vue` (40 dòng), `index.js`.
- Props: `open`, `title` (bắt buộc), `description`, `side='right'`, `width='420px'`. Emit `update:open`. Slot mặc định và `footer`.
- Dựng trên `Dialog*` của reka-ui, render ra `<body>`.
- Kiểu: lớp phủ `z-index:2147481000`, ngăn `2147481001`; hoạt ảnh 220ms ghi cứng; tiêu đề 18px đậm 650; nút đóng 32×32px.
- A11y: giữ focus, Esc, trả focus do reka-ui cấp (ghi ở `Sheet.vue:4`; chưa kiểm). Nút đóng có `aria-label="Đóng " + title`.
- Dùng: 2 tệp (`components/timekeeping/TkDailyDetails.vue:14`, `components/UiShowcase.vue:65`).

#### `skeleton/` — Skeleton

- Tệp: `Skeleton.vue` (5 dòng), `index.js`. Không props. Class `animate-pulse rounded-md bg-muted`.
- Dùng: 2 tệp, 5 thẻ (`components/DataTable.vue:325,332`, `components/UiShowcase.vue:61`).

#### `textarea/` — Textarea

- Tệp: `Textarea.vue` (15 dòng), `index.js`. Props `modelValue` (String), `disabled`. Emit `update:modelValue`. Class giống `Input`, thêm `min-h-[80px]`. Không tự giãn, không đếm ký tự.
- Dùng: 10 tệp, 14 thẻ. Ví dụ: `src/App.vue:247`, `components/ForecastCloseAction.vue:33`, `components/hr/HrPayrollPeriod.vue:227`.

#### `toast/` — Toaster

- Tệp: `Toaster.vue` (40 dòng), `index.js` (xuất lại `toast`, `dismissToast`, `useNoticeToast` từ `src/use-toast.js`).
- `Toaster`: không props. Dựng trên `Toast*` của reka-ui. Mỗi thông báo có tiêu đề, mô tả tuỳ chọn, một nút hành động tuỳ chọn, nút đóng "Đóng thông báo".
- Ba tông: `info`, `success`, `error`. Tông chỉ khác nhau ở màu viền trái 4px (`Toaster.vue:24-26`).
- Vị trí: góc phải dưới, rộng tối đa 380px, `z-index:2147483000`.
- A11y: lỗi dùng `type="foreground"`, còn lại `background` (`Toaster.vue:10`); vuốt phải để đóng; phím tắt vào vùng thông báo do reka-ui cấp (chưa kiểm).
- Dùng: `ui/toast` được 2 tệp import (`src/App.vue:18`, `components/UiShowcase.vue:15`). `<Toaster/>` chỉ gắn ở `src/App.vue:248`.

#### `tooltip/` — Tooltip

- Tệp: `Tooltip.vue` (13 dòng), `index.js`.
- Props: `content` (String, bắt buộc), `side='bottom'`. Slot mặc định là phần tử kích hoạt (`as-child`). Trễ 400ms.
- Mỗi `Tooltip` tự tạo một `TooltipProvider` (`Tooltip.vue:7`).
- Kiểu: nền `--lotus-neutral-900`, chữ `#fff`, 12px; chế độ tối đảo màu; `z-index:2147482500`.
- Dùng: 4 tệp, 12 thẻ. Ví dụ: `components/AiChatBubble.vue:52`, `components/InternalChat.vue:188`, `components/WorkspaceBar.vue:45`.

### 3. Helper

| Tệp | Nội dung | Nơi dùng |
|---|---|---|
| `src/lib/utils.js` (5 dòng) | `cn(...inputs)` = `twMerge(clsx(inputs))` | 14 lần import, chỉ trong `components/ui` |
| `components/ui/portal-target.js` (11 dòng) | `useDialogPortal()` trả hàm `target(element)`: lấy giá trị `inject('searchSelectTarget')` nếu có, không thì `element.closest('dialog[open]')`, không thì `'body'` | `Combobox.vue`, `DatePicker.vue`, `DateRangePicker.vue` |
| `src/use-toast.js` (22 dòng) | `toast(input)`, `toast.success/error/info`, `dismissToast(id)`, `useToastState()`, `useNoticeToast(ref)`. Trạng thái là một `reactive` dùng chung. Giữ tối đa 4 thông báo. Thời lượng 5.000ms; lỗi và thông báo có hành động 8.000ms | `toast` gọi trực tiếp ở `src/App.vue:212` và `components/ProcurementWorkspace.vue:137`; `useNoticeToast` ở 6 tệp (`App.vue:186`, `FarmLandApp.vue:121`, `FinanceApp.vue:422`, `HrApp.vue:212`, `TimekeepingApp.vue:244`, `UserAdminApp.vue:48`); `toast.error` chỉ có trong `UiShowcase.vue` |
| `src/use-confirm-core.js` (16 dòng) | `useConfirmCore({onShow,onHide})` trả `{message,pending,ask,finish}`. Mỗi lúc một câu hỏi; `ask()` thứ hai trả `false` | `use-workspace-confirm.js`, `use-mobile-confirm.js` |
| `src/use-workspace-confirm.js` (11 dòng) | `useWorkspaceConfirm()` trả `{open,title,alertOnly,message,ask,tell,finish}`. `ask(text,heading='Xác nhận')`, `tell(text,heading='Thông báo')` | 11 màn; 27 lời gọi `ask(` trong template và script |
| `src/dialogs.js` (8 dòng) | `dismissOnBackdrop(event,busy)`: đóng `<dialog>` khi bấm ngoài khung chữ nhật của nó | Dùng thật ở `components/WorkspaceModal.vue:29-30` |

### 4. LotusIcon

- Tệp: `components/LotusIcon.vue` (71 dòng, 7.327 byte). Một prop: `name` (mặc định `'boxes'`).
- Nguồn icon: dữ liệu đường vẽ ghi thẳng trong đối tượng `paths` (`LotusIcon.vue:3-69`). Dòng 4-41 là đường vẽ viết tay theo kiểu lucide. Dòng 43-68 chép từ lucide-static 1.52 và đổi `rect/circle/ellipse/polyline` thành `path` (ghi chú ở `LotusIcon.vue:42`). `lucide-static` 1.52.0 có trong `package-lock.json` vì frappe-ui kéo theo; `package.json` không khai trực tiếp.
- 64 khoá, 63 icon khác nhau (`send` khai hai lần). Danh sách: `boxes`, `cart`, `receive`, `issue`, `transfer`, `check`, `list`, `document`, `settings`, `leaf`, `people`, `warehouse`, `chevron`, `x`, `calendar`, `chevron-left`, `tick`, `check-circle`, `clock`, `send`, `alert`, `target`, `map`, `chart`, `menu`, `home`, `chevron-down`, `logout`, `search`, `chat`, `sparkle`, `scan`, `sun`, `moon`, `switch-camera`, `flashlight`, `flashlight-off`, `sprout`, `clipboard`, `sliders`, `trending`, `ruler`, `trash`, `basket`, `shield`, `package`, `lock`, `flag`, `route`, `id-card`, `user-cog`, `database`, `upload`, `plus`, `arrow-left`, `paperclip`, `users`, `download`, `printer`, `more`, `refresh`, `edit`, `wallet`.
- Thẻ xuất ra (`LotusIcon.vue:71`): `<svg class="lotus-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">`.
- Cỡ: mặc định 20px qua thuộc tính. Không có prop cỡ. Nơi dùng đổi cỡ bằng CSS: 26 rule `.lotus-icon` và 15 rule `… svg` rải trong các tệp CSS và `<style>`, với 9 cỡ khác nhau (12, 13, 14, 15, 16, 17, 18, 19, 22px), thêm 29px ở `.lotus-work .mobile-action-icon svg`.
- Nét: `stroke-width` cố định 1,7 trên khung 24. Nét co theo cỡ: khoảng 1,42px ở 20px, 1,13px ở 16px, 0,92px ở 13px.
- Màu: `currentColor`.
- Tên không có trong `paths` thì vẽ icon `boxes`, không cảnh báo (`paths[name]||paths.boxes`).
- Dùng: 46 tệp import, 169 thẻ (15 thẻ trong 7 tệp `ui`, 154 thẻ ở 39 tệp ngoài `ui`). 149 thẻ ghi tên tĩnh, 20 thẻ ghi tên động. Tên dùng nhiều nhất: `plus` 20, `download` 12, `x` 10, `chevron-down` 10, `chevron` 8, `tick` 6, `refresh` 6, `printer` 5.
- Tên icon còn đi qua cấu hình: `src/domain.js` (bộ ba `[đường dẫn, icon, nhãn]`), `src/finance-navigation.js`, `src/mobile-menu.js` và các tệp `*-navigation.js`.
- Điện thoại dùng thêm bộ icon thứ hai là phông icon của Vant: 31 thẻ `<Icon>` ở 14 tệp.

### 5. UiShowcase, `showcase-main.js`, `showcase.html`

- `frontend/showcase.html` (1 dòng) nạp `/src/showcase-main.js`. `showcase-main.js:3-14` nạp 10 tệp CSS rồi gắn `UiShowcase`. `vite.config.js` không liệt kê trang này trong `rollupOptions.input`.
- `components/UiShowcase.vue` (75 dòng) có 5 khối:
  1. "Nút & thông báo": Button mặc định, `outline`, `ghost`, `destructive`, `loading`; ba kiểu toast.
  2. "Biểu mẫu": FormField với Input (có lỗi), Combobox tĩnh, Combobox tải từ máy chủ, DatePicker, DateRangePicker, Select.
  3. "Menu, tooltip, popover, sheet": DropdownMenu, Tooltip trên nút icon, Popover, nút mở Sheet, nút mở WorkspaceModal chứa Combobox và DatePicker.
  4. "Bảng": một `DataTable` 6 dòng.
  5. "Tab, phân trang, tải, trống": `WorkspaceTabs`, hai `Pagination`, ba `Skeleton`, `DesktopEmptyState`.
- Có nút đổi sáng/tối (`UiShowcase.vue:33`).
- Có mặt 13/19 thư mục primitive. Vắng: `badge`, `card`, `checkbox`, `file-input`, `separator`, `textarea`; vắng cả `MoneyInput` và `FilePickerButton`.
- Button: có 4/6 biến thể (thiếu `secondary`, `link`), không có cỡ `lg`, không có trạng thái vô hiệu.
- Không có: bảng màu và tỉ lệ tương phản, chữ, khoảng cách, bo góc, bóng; danh mục icon; ma trận trạng thái (rê chuột, đang bấm, đang đứng, vô hiệu, lỗi, chỉ đọc); `WorkspaceConfirm`, `ModalForm`, `LotusField`, `LineItemsEditor`, `MonthPicker`, `WorkspaceSummaryStrip`, `WorkspaceListToolbar`, `ListPage`; biểu đồ; bộ điện thoại `LotusMobile*`; thành phần nông nghiệp; mục lục; nút đổi mật độ; ghi chú "dữ liệu mẫu".
- `showcase-main.js` không nạp `stock.css`, `stock-attio.css`, `farm-work.css`, `timekeeping.css`, `hr.css`, `hr-workspace.css`, `warehouse-table-center.css`, `stock-overview.css`, `warehouse-workspace-audit.css`, `care-map.css` như `main.js:9-29`. `stock.css` có 16 rule theo tên thẻ (ví dụ `select{min-width:210px}`), nên trang mẫu không tái hiện đúng thứ tự ghi đè của bản chạy thật.
- Kiểu của trang mẫu ghi cứng cỡ chữ 22px, 15px, 12px và dùng `style="…"` trực tiếp (`UiShowcase.vue:52,61,71-74`).

### 6. Lớp bọc ngoài `ui` dựng trên primitive

| Component | Vai trò | Tệp import | Thẻ |
|---|---|---|---|
| `components/form/LotusField.vue` | Một trường nhập cho mọi màn: chọn ô theo `type` (text, number, money, date, month, select, combobox, textarea, checkbox, file); `mobile` thì dùng `LotusMobile*` | 56 | 420 |
| `components/DataTable.vue` | Bảng AG Grid dùng chung | 43 | 132 |
| `components/form/ModalForm.vue` | Hộp nhập chuẩn: `WorkspaceModal` + dải lỗi + chân "Hủy · Lưu" | 30 | 59 |
| `components/WorkspaceModal.vue` | Hộp thoại máy tính trên `<dialog>` gốc; hai chế độ `v-model`+`title` và `bare`+ref | 26 | 49 |
| `components/form/FormGrid.vue`, `FormSection.vue` | Lưới và khối trong biểu mẫu | 20, 9 | 55, 62 |
| `components/ListPage.vue` | Trang danh sách | 13 | 18 |
| `components/WorkspaceTabs.vue` | Tab theo WAI-ARIA, tự viết | 12 | 12 |
| `components/WorkspaceConfirm.vue` | Hộp xác nhận | 11 | 11 |
| `components/form/LineItemsEditor.vue` | Dòng chi tiết chứng từ | 10 | 17 |
| `components/WorkspaceListToolbar.vue` | Thanh công cụ danh sách | 6 | 6 |
| `components/WorkspaceSummaryStrip.vue` | Dải số tổng hợp | 5 | 9 |
| `components/MonthPicker.vue` | Chọn tháng bằng `<select>` | 4 | 3 |
| `components/DesktopEmptyState.vue` | Trạng thái trống | 3 | 3 |
| `components/form/ReasonDialog.vue` + `src/use-reason-dialog.js` | Hỏi lý do | 3 | 4 |
| `components/DesktopMetricCard.vue`, `DesktopPageHeading.vue` | Ô số liệu, tiêu đề trang | 1, 1 (chỉ `ForecastPlanner.vue`, tệp này không còn ai import) | 4, 1 |

## Ràng buộc phải giữ

### Quy ước đã chốt với chủ vườn

- `AGENTS.md:12`: một màu chính Đỏ Lotus `#c43224`; mọi màu, chữ, khoảng cách, bo góc, bóng lấy từ `frontend/src/lotus-tokens.css`; không ghi mã hex ở CSS khác.
- `AGENTS.md:16`: màn máy tính dùng primitive trong `components/ui`; ô nhập bọc trong `FormField`; mọi ô chọn có tìm dùng `Combobox`; `DatePicker`/`DateRangePicker` gõ được `dd/mm/yyyy` hoặc chọn lịch; nút chỉ có icon có `Tooltip`; toast cho thành công, lỗi chặn hiện cạnh biểu mẫu.
- `AGENTS.md:17`: không tự viết lại popover, combobox, menu, date picker; nội dung nổi trong hộp thoại phải render trong chính `<dialog>`.
- `AGENTS.md:18-19`: xác nhận dùng `useWorkspaceConfirm`; icon dùng `LotusIcon`; hộp thoại máy tính chỉ dùng `WorkspaceModal`.
- `AGENTS.md:20`: component có hành vi phải có test mount qua `tests/support/mount.mjs`.
- `AGENTS.md:21`: xem trước bằng `npm run dev` rồi mở `showcase.html`; không build ra production.
- `.specify/memory/constitution.md` nguyên tắc V: máy tính dùng `components/ui`, `DataTable`, `WorkspaceModal`; toàn bộ chữ hiển thị bằng tiếng Việt.
- `specs/004-bo-giao-dien-agritech/spec.md` mục Assumptions: không thêm thư viện giao diện mới; thư viện đang dùng giữ nguyên phiên bản.

### Test đang khoá cấu trúc

| Test | Điều bị khoá |
|---|---|
| `tests/component-library.test.js:6-12` | 14 thư mục phải có `index.js`; 7 tệp (`Combobox`, `DatePicker`, `DateRangePicker`, `Toaster`, `Sheet`, `Pagination`, `Tooltip`) phải có `from 'reka-ui'` |
| `tests/component-library.test.js:14-20` | `SearchSelect.vue`, `LinkPicker.vue` phải chứa `<Combobox ` và không tự định vị popup |
| `tests/component-library.test.js:22-28` | `WorkspaceBar.vue` dùng `<DropdownMenuContent`, `<Tooltip `, không dùng `<details` |
| `tests/component-library.test.js:30-33` | `showcase.html` tồn tại; `vite.config.js` không chứa chữ `showcase` |
| `tests/ui-stack.test.js:19-42` | `components.json` (`new-york`, `typescript:false`, css `src/shadcn.css`), script `ui:add` dùng `shadcn-vue@1.0.3`, phiên bản khoá của `class-variance-authority`, `clsx`, `tailwind-merge`, `reka-ui`, `tailwindcss-animate` trong `tailwind.config.js`, `@tailwind utilities` trong `shadcn.css`, 7 thư mục (`button`, `input`, `textarea`, `card`, `badge`, `skeleton`, `separator`) có `index.js`, không có `components/ui/Button.vue` |
| `tests/ui-stack.test.js:43-55` | `App.vue`, `FieldReportApp.vue`, `SchemaForm.vue` có `import {Button as UiButton}` và số thẻ mở bằng số thẻ đóng |
| `tests/ui-stack.test.js:56-60` | 6 entry (`main`, `showcase-main`, `work-mobile-main`, `buying-mobile-main`, `hr-mobile-main`, `warehouse-mobile-main`) phải `import './shadcn.css'` |
| `tests/ui-stack.test.js:61-66` | Nút `ghost` cỡ `icon` trong `WorkspaceBar.vue` phải có class `hover:bg-white/15 hover:text-white` |
| `tests/ui-stack.test.js:67-75` | `normalizeInputValue`; chuỗi import trong `SchemaForm.vue` và `MobileHome.vue` (`import {Card as UiCard}`) |
| `tests/design-tokens.test.js:11-19` | `lotus-tokens.css` có `--lotus-primary-600:#c43224`, `--primary:5 69% 45%`, `:root.dark{` |
| `tests/design-tokens.test.js:40-62` | Không mã hex và chỉ phông `var(--lotus-font)` trong `src/*.css`, `src/*.vue`, `src/components/*.vue` |
| `tests/design-tokens.test.js:79-83` | Không `window.alert/confirm`; `use-workspace-confirm.js` xuất `useWorkspaceConfirm` |
| `tests/components.mount.test.js` | Combobox: `input[role=combobox]`, `aria-label`, `.lotus-combobox__trigger`, `[role=option]`, mở ra hiện đủ mục, gõ không dấu vẫn lọc. Toaster: `.lotus-toast`, nút hành động chạy một lần rồi đóng |
| `tests/date-picker-input.mount.test.js` | Placeholder `dd/mm/yyyy`; `id` rơi vào ô nhập; ngày sai hoặc ngoài khoảng phát `''` và chặn form; lịch nằm trong `dialog[open]`; class `.lotus-date__trigger`, `.lotus-date__content`, `.lotus-calendar__day`, thuộc tính `data-outside-view` |
| `tests/use-toast.test.js` | Thời lượng 5000/8000, tối đa 4, `useNoticeToast` xoá ref sau khi hiện |
| `tests/use-confirm-core.test.js` | Mỗi lúc một hộp; thứ tự `show`/`hide` |
| `tests/dialogs.test.js` | `dismissOnBackdrop` chỉ đóng khi bấm ngoài khung và không bận |
| `tests/timekeeping-grid-layout-audit.test.js:32-35` | Hai chuỗi nguyên văn trong template `Pagination.vue` (`v-if="pageSize>0 && total && total>pageSize"`, `v-else-if="pageSize>0&&!total&&(start>0||hasMore)"`) |
| `tests/warehouse-hr-link.test.js:23-30` | Hai chuỗi nguyên văn trong `Combobox.vue` (`chosen.value=row`, `const shown=()=>props.displayValue||current.value?.label`) |
| `tests/workspace-sidebar.mount.test.js:16-22,30` | Mỗi icon của `navGroups` phải khớp mẫu `tên:[` trong mã `LotusIcon.vue`; DOM có `svg.lotus-icon` |
| `tests/pagination-size.mount.test.js`, `tests/data-table-selection.mount.test.js:30`, `tests/form-standard.mount.test.js:90` | `.lotus-pagination`, `.lotus-pagination__range`, `[aria-label="Trang sau"]`, và nút "Hiện toàn bộ" là nút duy nhất trong `.lotus-pagination` không có `aria-label` |
| `tests/form-standard.mount.test.js:11-23` và 4 test khác | `.lotus-field`, `label.lotus-field__label`, `.lotus-field__required` |
| `tests/hr-audit-fixes.mount.test.js:109-120`, `tests/timekeeping-period.mount.test.js:64-67` | `.lotus-sheet` chứa nội dung và nút; đóng thì biến mất |
| `tests/workspace-modal.mount.test.js` và 22 chỗ `querySelector('dialog[open]')` | `WorkspaceModal` là `<dialog>` gốc, có `showModal()`, `close()`, `.open`, class `workspace-modal`, `workspace-modal__header` |
| `tests/scope-filterbar-layout.test.js:10,12` | Selector `>.scope-picker>.lotus-field` và `.scope-date-range .lotus-date__field` trong CSS |
| `tests/form-standard.test.js:12-28` | Các màn "standard" không dùng thẻ `input/select/textarea` gốc, không `<UiInput type="date|month">`, không `WorkspaceModal bare` |

Tổng số tệp test: 155, trong đó 54 tệp mount.

### API đang được nơi dùng dựa vào

- Button: tên biến thể `default`, `outline`, `ghost`, `destructive`, `link`; cỡ `sm`, `icon`; props `loading`, `disabled`, `type`, `as`, `asChild`. `LotusMobileButton.vue:3` nhận cùng bộ `type`, `variant`, `disabled`, `loading` để 7 tệp đổi qua lại bằng `<component :is>`.
- Input: `v-model` và `v-model.number` (24 thẻ), mọi thuộc tính gốc đi qua `$attrs`.
- Select: `v-model`, `@change` gốc (14 thẻ), slot `<option>`.
- FormField: tên bốn slot prop `id`, `required`, `aria-invalid`, `aria-describedby` (149 thẻ dùng `v-slot`).
- Combobox: dạng `options`, chữ ký `fetchOptions(search)`, `displayValue`, `allowCustom`, `hideValues`, emit `change`, `select`.
- DatePicker: `v-model` là `YYYY-MM-DD` hoặc `''`; `min`, `max`, `clearable`. DateRangePicker: `v-model:from`, `v-model:to`, `@change({from,to})`, `presets`.
- Pagination: `start`, `count`, `total`, `hasMore`, `pageSize` (0 nghĩa là tất cả), emit `update:start`, `update:pageSize`.
- Sheet: `v-model:open`, `title`, `description`, slot `footer`. Tooltip: `content`. DropdownMenuItem: `@select`. FilePickerButton: `@files`, `as`, `capture`. FileInput: `@change` trả sự kiện gốc.
- `toast`, `toast.success/error/info`, `action:{label,run}`; `useWorkspaceConfirm()` trả đủ bảy khoá; `dismissOnBackdrop(event,busy)`.
- LotusIcon: prop `name`, class `lotus-icon`, tên sai rơi về `boxes`.
- CSS ngoài `ui` nhắm vào class của primitive: `finance.css` (`.lotus-date--range`), `financial-planning.css` (`.fp-toolbar>.lotus-combobox`), `hr-workspace.css` và `timekeeping.css` (`.lotus-date`), `procurement.css` (`.procurement-toolbar .lotus-field`), `workspace-experience.css` (`.workspace-list-filters>.lotus-date--range`, `.scope-picker>.lotus-field`, `.lotus-menu__user`, `.lotus-menu__kbd`), `components/ColumnVisibilityMenu.vue:60` (`.lotus-column-picker.lotus-popover`), `components/finance/FinanceAssets.vue:288`, `components/form/LotusField.vue:69-72`, `components/erp/ErpFields.vue:99`.
- Lựa chọn lưu trên máy người dùng: `lotus-theme`, `lotus-sidebar` (`src/workspace.js:4-5`), `lotus-desktop-density` (`src/use-desktop-workspace.js:8`).

## Điểm yếu

Xếp theo mức ảnh hưởng tới việc đúc lại bộ.

1. **Hai hệ kiểu và hai bộ token trong cùng một bộ primitive.** 8 thư mục dùng Tailwind với biến HSL, 11 thư mục dùng BEM với `--lotus-*`. Hai bộ lệch giá trị: `--primary:5 69% 45%` ra `#c23124` trong khi `--lotus-primary` là `#c43224`; `--destructive:4 77% 40%` ra `#b52217` trong khi `--lotus-danger` là `#b42318`. Tên cỡ chữ cũng lệch: `text-sm` của Tailwind là 13px, `--lotus-text-sm` là 12px; `text-xs` là 12px, `--lotus-text-xs` là 11px. `text-sm` còn kéo theo `font-weight:420` và `letter-spacing:.02em` của preset frappe-ui; `shadow-sm` phụ thuộc `--elevation-sm` của frappe-ui. Bằng chứng: `lotus-tokens.css`, `tailwind.config.js:1,12-26`, `shadcn-8_U6msli.css`.

2. **CSS toàn cục theo tên thẻ đè lên primitive.** `desktop-system.css` có `.lotus-ui :is(input,select,textarea):not([type="checkbox"]):not([type="radio"]){border-radius:8px;min-height:…;border-color:var(--lotus-border);background:var(--lotus-surface)…}` với độ ưu tiên (0,3,1). Rule này thắng `.border-input`, `.bg-background`, `.rounded-md` (0,1,0), thắng cả `.aria-\[invalid\=true\]\:border-destructive[aria-invalid=true]` và `.lotus-combobox__input[aria-invalid=true]` (0,2,0). Hệ quả suy ra từ CSS: ở bề rộng từ 901px, bên trong `.lotus-ui`, viền của Input, Select, Textarea, Combobox không đổi sang màu lỗi. Không có rule nào khác cho trạng thái lỗi của các ô này. Rule trên cũng khớp ô `input` bên trong DatePicker (`.lotus-date__input`) vì nó nhắm theo tên thẻ.

3. **171 rule trong 27 tệp `.css` và 38 rule trong `<style>` của `.vue` đặt nền, viền, màu, chiều cao hoặc đệm cho `button` theo ngữ cảnh.** Ví dụ `compact.css`: `.workspace-bar button{background:transparent;color:#fff}`, `.workspace-bar button{min-height:30px;height:30px;padding:4px 9px;font-size:12px}`; `attio.css`: `.actions button{background:…;color:…;border:…}`; `workspace-experience.css`: `.workspace-list-toolbar :is(input,select,button,…){height:36px;min-height:36px}`. Các rule này có độ ưu tiên (0,1,1) trở lên nên thắng class biến thể của Button. `tests/ui-stack.test.js:61-66` phải ép thêm class `hover:bg-white/15 hover:text-white` để vá một trường hợp.

4. **Viền chỉ vị trí đang đứng không có một nguồn.** Có sáu nguồn với ba màu: `style.css` (`button:focus-visible{outline:3px solid var(--lotus-success-400)}`, xanh lá), `attio.css` (`input:focus{outline:2px solid var(--lotus-info-200);border-color:var(--lotus-info-400)}`, xanh dương), `desktop-system.css` (viền ngoài 2px `--lotus-accent` kèm quầng 2px `--lotus-accent-soft`, chỉ từ 901px), `workspace-experience.css` (viền ngoài 2px cách 3px), ring của Tailwind trong primitive, và `--lotus-focus` trong Combobox, DatePicker. Suy ra từ CSS: Input trong `.lotus-ui` từ 901px nhận cùng lúc viền, quầng và viền ngoài; dưới 901px hoặc bên ngoài `.lotus-ui` thì viền chuyển xanh dương. Các nút gốc bên trong nội dung nổi (`.lotus-calendar__nav`, `.lotus-calendar__footer button`, `.lotus-date__presets button`, `.lotus-sheet__close`, `.lotus-toast__close`, `.lotus-pagination__button`) không tự định nghĩa `:focus-visible`.

5. **Phạm vi `.lotus-ui` không phủ nội dung nổi.** Class `lotus-ui` gắn ở gốc từng màn và ở `<dialog>` của `WorkspaceModal` (`App.vue:230`, `WorkspaceModal.vue:29-30` và 10 màn khác), không gắn ở `<body>`. 193 rule trong `src/*.css` dùng phạm vi này. Sheet, Popover, DropdownMenu, danh sách Combobox, lịch, Tooltip, Toast render ra `<body>` nên đứng ngoài phạm vi. Vì vậy 7 khối CSS trong `ui` phải tự đặt lại `font-family:var(--lotus-font)`, và ô nhập đặt trong Sheet (`TkDailyDetails.vue:25`) nhận bộ rule khác với cùng ô đó trong trang.

6. **Hai cơ chế lớp nổi không tương thích.** `WorkspaceModal` dùng `<dialog>` gốc. Sheet, DropdownMenu, Popover, Tooltip, Toast dùng cổng của reka-ui ra `<body>`. Chỉ Combobox, DatePicker, DateRangePicker tự chuyển vào `<dialog>` qua `useDialogPortal`. `PopoverContent` có prop `to` nhưng 0 nơi truyền. `DropdownMenuContent.vue`, `Tooltip.vue`, `Sheet.vue` không có đường nào để render vào `<dialog>`. 26 hộp thoại đang chứa `DataTable` hoặc `OpsList` (ví dụ `App.vue:248`, `FinanceApp.vue` 5 hộp, `finance/FinanceAssets.vue` 5 hộp), mà công cụ của bảng dùng Popover và DropdownMenu ra `<body>` (`ColumnVisibilityMenu.vue:26`, `DataTableViews.vue:30,34`). Chưa kiểm hiển thị thực tế. Khoá `inject('searchSelectTarget')` trong `portal-target.js:5` không có nơi nào `provide`.

7. **Nhãn và lỗi của FormField dễ bị đứt.** 49/198 thẻ `<FormField>` không lấy slot props (40 thẻ ở `finance/FinanceAssets.vue`, ví dụ dòng 187-190), nên `<label for>` không trỏ tới ô nào và ô không nhận `aria-invalid`, `aria-describedby`. `DateRangePicker.vue:29-31` chỉ dùng `class` và `aria-label` từ `$attrs`, bỏ `id`. Lỗi theo trường hầu như không được dùng: 9/198 thẻ `FormField` và 2/420 thẻ `LotusField` có `:error`. Class `lotus-field--invalid` (`FormField.vue:11`) không có rule CSS nào. Dòng lỗi không có `role="alert"`, `aria-live` hay icon.

8. **Tương phản dưới mức yêu cầu của `spec.md` FR-004.** Tính theo công thức WCAG:

| Cặp | Tỉ lệ |
|---|---|
| Viền ô nhập `--lotus-border` `#e8e5e1` trên nền trắng | 1,26:1 |
| Viền `--lotus-border-strong` `#d6d3cf` (Checkbox, DatePicker) trên nền trắng | 1,49:1 |
| Chế độ tối: viền `#3b414b` và `#4b525d` trên `#20262f` | 1,48:1 và 1,93:1 |
| Chữ gợi ý và ngày ngoài tháng `--lotus-neutral-400` `#a7abb2` trên nền trắng (`date-picker.css` dòng 7, 10, 11, 32) | 2,30:1 |
| Quầng focus `--lotus-focus` (28% đỏ trên trắng, `#eec6c2`) | 1,56:1 |
| Quầng focus `--lotus-accent-soft` `#fef3f1` | 1,09:1 |
| Mục menu/option đang trỏ: nền `--lotus-hover` `#f1f0ef` so với nền trắng (`.lotus-menu__item[data-highlighted]`, `.lotus-combobox__item[data-highlighted]`) | 1,14:1 (tối: 1,19:1) |
| Chữ trắng trên nút chính khi vô hiệu (`opacity:.5`) | 2,28:1 |

9. **Nút chính và nút nguy hiểm gần như cùng màu.** `bg-primary` là `#c23124`, `bg-destructive` là `#b52217`; tỉ lệ giữa hai màu là 1,17:1. `WorkspaceConfirm.vue:9` luôn dùng nút mặc định và đặt `autofocus` lên nút đồng ý, kể cả với câu hỏi huỷ phiếu hay bỏ thay đổi (ví dụ các lời gọi `ask('Huỷ phiếu …')`, `ask('Đóng biểu mẫu và bỏ phần chưa lưu?')`). `ask(text,heading)` không nhận tông nguy hiểm hay nhãn nút; `HrApp.vue:353` phải so chuỗi tiêu đề để đổi nhãn.

10. **Vùng bấm nhỏ và không dùng token.** Checkbox 18×18px; nút mở Combobox và nút lịch 28×28px; nút đóng toast 28×28px; nút chuyển tháng 30×30px; ô ngày 36×34px; nút phân trang 32px; Button `sm` 32px. `--lotus-touch:44px` có trong `lotus-tokens.css` nhưng không tệp nào trong `ui` dùng. Một số primitive vẫn chạy trên điện thoại: `FilePickerButton` với `capture` (`stock/StockEvidence.vue:37`, `field/PaperPhotoReview.vue:53`), `DateRangePicker` có rule riêng cho dưới 640px.

11. **Giá trị ghi cứng trong primitive.** CSS trong `ui` có 175 chỗ ghi `px` so với 188 chỗ dùng `var(--lotus-*)`; token khoảng cách `--lotus-space-*` chỉ được dùng 4 lần. `z-index` ghi tay sáu giá trị sát 2^31 (`2147481000`, `2147481001`, `2147482000`, `2147482500`, `2147483000`), không có token; cả frontend có 24 giá trị `z-index` khác nhau trong 55 khai báo. Độ mờ khi vô hiệu có 4 mức (`.5`, `.55`, `.45`, `.35`). Độ đậm chữ có 6 mức (400, 500, 550, 600, 650, 700). `Sheet.vue:28-29` ghi `220ms` thay cho `--lotus-motion`. Có 7 `@keyframes` gần giống nhau cho hiệu ứng hiện ra.

12. **Các ô nhập cùng một biểu mẫu không đồng nhất** (suy ra từ CSS). Cỡ chữ: Combobox 14px (`--lotus-text-base`), Input/Select/DatePicker 13px. Viền lúc thường trong `.lotus-ui`: Input, Select, Textarea, Combobox, FileInput bị ép về `--lotus-border`; DatePicker, DateRangePicker, Checkbox giữ `--lotus-border-strong`. Đệm trái: Input và Combobox 12px, DatePicker 10px. `Input` có `shadow-sm`, `Select` không có. Chiều cao 36px được ghi bằng `h-9` ở nhóm Tailwind và bằng `--lotus-control-height` ở nhóm BEM.

13. **API không theo một khuôn.** Tên import: `Button as UiButton` 73 tệp, `Button` 14 tệp; `UiSelect` import thẳng `ui/select/Select.vue` 18 tệp. Ngày đơn là ô chữ tự do, khoảng ngày là ô chia đoạn. Prop `label` có ở Combobox, DatePicker, DateRangePicker, FilePickerButton; không có ở Input, Select, Textarea. Emit `change` có ở Combobox, DatePicker, DateRangePicker; `FileInput` trả sự kiện gốc; Input, Textarea, Checkbox không có. Chỉ Button có `size`. Không prop nào có kiểm giá trị: `variant` sai tên chỉ làm mất class, không báo.

14. **LotusIcon.** Toàn bộ 63 icon nằm trong một SFC, mọi nơi dùng đều tải đủ. Không có prop cỡ, nét, tiêu đề. Cỡ nằm rải ở 41 rule CSS. Khoá `send` khai hai lần với hai đường vẽ khác nhau (`LotusIcon.vue:23,34`). Tên sai không báo: `src/finance-navigation.js:12` dùng `icon:'landmark'`, tên này không có trong `paths`, nên mục "Ngân hàng – Đối chiếu" vẽ icon `boxes` khi đi qua `WorkspaceSidebar.vue:78`. `tests/workspace-sidebar.mount.test.js:16-22` chỉ kiểm icon của `navGroups` trong `domain.js`, không kiểm các tệp `*-navigation.js`.

15. **Button bị dùng làm khung cho thứ không phải nút hành động.** 40/591 thẻ mang class riêng như `kpi`, `nav-parent`, `nav-child`, `mobile-action`, `fin-todo__item`, `workspace-search`, rồi CSS phân hệ đè lại toàn bộ diện mạo. `loading` chỉ dùng ở 11/591 thẻ; nhiều nơi đổi chữ thành "Đang lưu…" thay vào. Có 16 nút chỉ chứa một icon; cả 16 có `aria-label`, nhưng chỉ 6 dùng `size="icon"` và ít nhất 10 nút ở 9 tệp không có `Tooltip` (`stock/StockEvidence.vue`, `timekeeping/TkSetup.vue`, `form/LineItemsEditor.vue:39`, `erp/ErpReport.vue`, `erp/ErpForm.vue`, `erp/ErpChildTable.vue`, `WorkspaceSidebar.vue`, `TimekeepingGridCell.vue`, `TimekeepingApp.vue`).

16. **Vẫn còn ô ngày, giờ, số gốc của trình duyệt.** `type="date"` 10 thẻ (`App.vue` 5, `ColorTagCatalogApp.vue` 4, `timekeeping/TkRoster.vue` 1), `datetime-local` 3, `time` 2, `month` 1, `number` 25. `tests/form-standard.test.js:17` chỉ chặn trong danh sách màn "standard". Bộ primitive chưa có ô giờ và ô ngày-giờ.

17. **Toast.** Tông chỉ phân biệt bằng màu viền trái, không có icon. Thiếu tông cảnh báo. Vùng toast (`right:16px;bottom:16px`) trùng góc với nút trò chuyện `.ai-chat` (`right` và `bottom` 24px), trong khi `Pagination.vue:50-53` phải thêm rule để né góc này. `Toaster.vue:11` xoá mục khỏi danh sách ngay khi đóng, nên rule `.lotus-toast[data-state=closed]` nhiều khả năng không chạy (suy ra từ mã).

18. **Mã và phụ thuộc không dùng.** `badge` và `separator`: 0 tệp import. Năm phần con của Card: 0 nơi dùng. Biến thể `secondary` và cỡ `lg` của Button: 0 thẻ. Các export `PopoverClose`, `TooltipProvider`, `rangePresets`, `dismissToast`, `buttonVariants`, `badgeVariants` không ai dùng ngoài `ui`. `tailwindcss-animate` được cài và test yêu cầu, nhưng không class nào của nó xuất hiện trong `src`. `dismissOnBackdrop` được import mà không dùng ở `components/WorkspaceBar.vue:10` và `src/FarmWorkApp.vue:16`. `compact.css` còn 11 rule `.link-picker-input`/`.link-picker-options` và 14 rule `.workspace-menu` không còn markup nào dùng. `components.json` khai alias `@/composables` nhưng không có thư mục `src/composables`.

19. **Tailwind sinh utility trùng từ thường.** `tailwind.config.js:9` quét `./src/**/*.{vue,js,ts}`, gồm cả `system-translations.js` 524KB. Kết quả là `shadcn-8_U6msli.css` có `.grid`, `.table`, `.hidden`, `.block`, `.fixed`, `.absolute`, `.relative`, `.visible`, `.filter`, `.blur`, `.transform`, `.transition`, `.shadow`, `.ring`, `.outline`, `.resize`, `.border`, `.prose`, dù không primitive nào dùng phần lớn các class này. Đây là class toàn cục; `UiShowcase.vue:40,61,64` đã có `class="grid"` trùng tên.

20. **Lỗ hổng kiểm thử.** Chưa có test mount cho Button, Input, Select, Textarea, MoneyInput (chỉ có test hàm định dạng ở `tests/money-format.test.js`), DateRangePicker, DropdownMenu, Popover, Tooltip, FileInput, FilePickerButton, `WorkspaceConfirm`, phím mũi tên của `WorkspaceTabs`, và trường hợp menu hoặc popover mở trong hộp thoại. `tests/design-tokens.test.js:8` chỉ quét `src/*.css`, `src/*.vue`, `src/components/*.vue`; các tệp trong `components/ui/**`, `components/form/**` và thư mục con khác nằm ngoài kiểm tra màu và phông. Không có test nào bảo đảm mọi primitive có mặt trên trang mẫu.

## Thiếu so với một bộ giao diện đầy đủ

| Thành phần | Trong `components/ui` | Ad-hoc ngoài `ui` | Kết luận |
|---|---|---|---|
| Alert / Banner | Không | Class `.stock-error` (25 chỗ, 14 tệp), `.notice` (30 chỗ, 9 tệp), `.stock-success` (9), `.tk-banner` (8), `.lotus-modal-form__error` (`form/ModalForm.vue:16`); kiểu gom ở `workspace-experience.css` (`:root:root :is(.stock-error,.error,…)`); template có 109 `role="alert"` và 93 `role="status"` viết tay | Thiếu component |
| Avatar | Không | `<span class="workspace-avatar">` (`WorkspaceBar.vue:58`), `.lotus-chat__avatar` (`InternalChat.vue:181,195`), `.mobile-avatar` (`WarehouseMobile.vue:734`, `WorkMobile.vue:106`) | Thiếu component |
| Accordion | Không | 16 thẻ `<details>` gốc ở 11 tệp (`FinanceApp.vue` 6) | Thiếu |
| Breadcrumb | Không | Chuỗi nối bằng `›` (`App.vue:85`, `App.vue:238`) | Thiếu; `AGENTS.md:3` cấm đặt breadcrumb phía trên bảng |
| Calendar | Chỉ có bên trong `date-picker` (`.lotus-calendar*`) | Lịch nghiệp vụ tự viết (`forecast-calendar.css`, `ZonePlantingSchedule.vue`, `timekeeping/TkMonthSheet.vue`) | Thiếu lịch đứng riêng |
| Chip / Tag | `badge/` (4 biến thể, 0 nơi dùng) | `.tk-pill` (6 chỗ, 5 tệp), `.lotus-chip` (`DataTableViews.vue:24`), `.pill` (`App.vue:240`), `.alert-chip` (`App.vue:231`), chữ màu `.lotus-grid-status` trong ô bảng (`OpsList.vue:28`, `attio.css`) | Có nhưng không dùng; thiếu nhãn trạng thái theo bảng từ vựng |
| Command palette | Không | Tự viết trong `WorkspaceBar.vue:73-77` (Ctrl K, `role=combobox`/`listbox`, `WorkspaceModal bare`) | Chỉ có bản ad-hoc |
| Dialog / Drawer | `sheet/` (ngăn kéo cạnh, 1 nơi dùng thật) | Hộp thoại: `WorkspaceModal.vue` (49 thẻ), `form/ModalForm.vue` (59), `WorkspaceConfirm.vue` (11), `form/ReasonDialog.vue` (4) | Hộp thoại nằm ngoài `ui`; hai cơ chế khác nhau |
| Empty state | Không | `DesktopEmptyState.vue` (3 tệp import; kiểu chỉ có từ 901px trong `desktop-components.css`), class `.empty`, `.stock-empty` | Chỉ có bản ad-hoc; thiếu trạng thái lỗi kèm thử lại |
| Kbd | Không | 2 thẻ `<kbd>` gốc (`WorkspaceBar.vue:54,64`), kiểu ở `desktop-shell.css` và `workspace-experience.css` | Thiếu |
| Menu | `dropdown-menu/` | — | Có; thiếu mục hộp kiểm, chọn một, menu con, menu chuột phải |
| NumberInput | `input/MoneyInput.vue` (ô chữ định dạng số Việt) | `<UiInput type="number">` 25 thẻ | Có một phần; thiếu đơn vị, min/max, bước, nút cộng trừ |
| Progress / Meter | Không | Thanh tự vẽ `.calendar-track` (`ForecastPlanner.vue:79`); 0 thẻ `<progress>`, `<meter>`, `role=progressbar` | Thiếu |
| Radio | Không | `role="radiogroup"` tự viết cho ô màu (`timekeeping/TkShiftForm.vue:41`); 0 thẻ `input type="radio"` | Thiếu |
| Switch | Không | Không có; giá trị bật/tắt dùng Checkbox hoặc nút `aria-pressed` | Thiếu |
| Segmented control | Không | Cặp `UiButton` đổi `:variant` (7 thẻ, ví dụ `LotusChart.vue`), `.land-views` (`FarmLandApp.vue:136`, `finance/FinancePlanning.vue:104`), `.tk-subnav` (`hr/HrPayrollPeriod.vue:188`, `timekeeping/TkSetup.vue:70`), `.forecast-tabs`; 32 thuộc tính `aria-pressed` ở 18 tệp | Thiếu |
| Slider | Không | `Slider` của Vant trong `LotusSignatureImageEditor.vue:99` (điện thoại) | Thiếu cho máy tính |
| Stat / KPI tile | Không | `DesktopMetricCard.vue` (chỉ `ForecastPlanner.vue` import, tệp này không còn ai import), `WorkspaceSummaryStrip.vue` (5 tệp), `.lotus-stat` (19 chỗ, 2 tệp; kiểu ở `workspace-experience.css`), `<UiButton class="kpi">` (`App.vue:231`) | Bốn bản ad-hoc khác nhau |
| Stepper | Không | `<ol class="hr-steps">` (`hr/HrPayrollPeriod.vue:143`), `PurchaseProgress.vue`, các bước ở `timekeeping/TkSetup.vue:70` | Thiếu |
| Table | Không | `DataTable.vue` (AG Grid, 132 thẻ, 43 tệp), `OpsList.vue`, `ListPage.vue`; 0 thẻ `<table>` trong mọi `.vue` | Bảng dữ liệu nằm ngoài `ui`; thiếu danh sách cặp tên–giá trị cho chi tiết |
| Tabs | Không | `WorkspaceTabs.vue` (12 tệp; `role=tablist/tab`, mũi tên, Home, End; không có `aria-controls`, không có `tabpanel`), `.tabs` (`App.vue:237,246`), nút `aria-current` (`ProcurementWorkspace.vue:304`) | Chỉ có bản ad-hoc |
| Timeline | Không | `LotusSignatureTimeline.vue` (5 tệp import, riêng cho chữ ký), class `.timeline` cũ (`App.vue:237`) | Chỉ có bản chuyên dụng |
| Toggle | Không | `timekeeping/TkPresenceToggle.vue` (riêng cho chấm công), các `UiButton` có `aria-pressed` | Thiếu bản chung |
| Tree | Không | `stock/MasterTree.vue` (`role=tree/treeitem`, 1 tệp import), cây menu trong `WorkspaceSidebar.vue` | Chỉ có bản ad-hoc |
| Upload | `file-input/` (ô file gốc và nút chọn tệp) | `stock/StockEvidence.vue`, `finance/FinanceMasterImport.vue`, `BunchOpeningImport.vue`, `DocumentReader.vue`, `field/PaperPhotoReview.vue`, kéo thả trong `InternalChat.vue` | Có một phần; thiếu vùng kéo thả, danh sách tệp, xem trước, tiến độ |

Ngoài danh sách trên, bộ hiện tại còn thiếu: nhóm nút, nút icon có nhãn bắt buộc, ô chọn nhiều, ô giờ và ngày-giờ, vòng tiến độ, trạng thái lỗi kèm nút thử lại, token cho thứ tự lớp nổi, và mật độ gọn/thoáng ở mức primitive (hiện chỉ `use-desktop-workspace.js` giữ lựa chọn cho bảng).

## Đề xuất cho bộ giao diện mới

Mọi đề xuất dùng thư viện đang có. reka-ui 2.11.0 đã cài sẵn các khối Accordion, Collapsible, RadioGroup, Switch, ToggleGroup, Tabs, Progress, Stepper, Tree, NumberField, TagsInput, Avatar, AlertDialog, ContextMenu và danh sách ảo hoá cho Combobox (dựa trên `@tanstack/vue-virtual` có trong `package-lock.json`). Chưa kiểm từng API vì không có `node_modules`.

### Ưu tiên 0 — nền của primitive, làm trước khi thêm component

1. **Chọn một hệ kiểu cho toàn bộ primitive.** Đề xuất: class `.lotus-*` cộng token `--lotus-*`, vì 11/19 thư mục đã theo cách này và Tailwind ngoài `ui` chỉ có ở 3 tệp. Chuyển 8 thư mục còn lại (`badge`, `button`, `card`, `input`, `select`, `separator`, `skeleton`, `textarea`). Giữ `shadcn.css` trong build cho tới khi sửa có chủ đích các test `tests/ui-stack.test.js:19-42,56-66`. Phương án tối thiểu nếu chưa chuyển: trỏ màu Tailwind trong `tailwind.config.js:13-26` thẳng vào `var(--lotus-*)` và bỏ khối HSL trùng trong `lotus-tokens.css` (phải sửa `tests/design-tokens.test.js:14`).
2. **Chặn CSS theo tên thẻ đè primitive.** Đưa các rule `input,select,textarea{…}`, `label{…}`, `.lotus-ui :is(input,select,textarea)…`, `.lotus-ui :is(button,…)` của `attio.css`, `desktop-system.css`, `workspace-experience.css` vào `@layer lotus-legacy` như đã làm với `style.css` và `stock.css`, hoặc xoá khi primitive đã tự mang kiểu đó. Sau bước này bỏ được các mẹo `:root:root` trong `ui` (`FormField.vue:20`, `date-picker.css:42-43`).
3. **Một kiểu cho mỗi trạng thái, đặt trong primitive.** Một token viền focus đạt 3:1 dùng cho mọi phần tử bấm được, kể cả nút bên trong lịch, Sheet, Toast, Pagination. Một kiểu lỗi hiện trên chính ô nhập (viền, icon, chữ). Một mức mờ khi vô hiệu. Viền ô nhập và Checkbox đạt 3:1. Mục menu và option đang trỏ có dấu hiệu ngoài màu nền.
4. **Một cơ chế lớp nổi.** Giữ `<dialog>` gốc của `WorkspaceModal` vì test và 108 nơi dùng dựa vào nó. Mở rộng `portal-target.js` cho `PopoverContent` (tự động, không cần truyền `to`), `DropdownMenuContent`, `Tooltip`; bỏ khoá `searchSelectTarget`. Thêm token `z-index` cho ngăn kéo, hộp nổi, chú thích, toast. Gắn phạm vi kiểu chữ lên `<body>` để nội dung nổi không phải tự đặt lại phông. Thêm test mount: menu, popover, tooltip mở trong `WorkspaceModal`.
5. **FormField cấp ngữ cảnh cho ô nhập.** `FormField` `provide` `id`, trạng thái lỗi, `aria-describedby`, bắt buộc, vô hiệu; các ô nhập `inject`. Giữ slot props để 149 nơi đang dùng không phải sửa. `DateRangePicker` nhận `id`. Dòng lỗi có icon và `role="alert"`.

### Ưu tiên 1 — bổ sung và hợp nhất

6. **Button.** Biến thể: chính, phụ (viền), mờ, nguy hiểm (kiểu khác hẳn nút chính và có icon, theo `spec.md` FR-007), liên kết. Ba cỡ. Giữ tên `outline`, `ghost`, `destructive`, `link`, `sm`, `icon` làm tên tương thích cho 591 thẻ. Thêm `IconButton` với prop `label` bắt buộc, tự đặt `aria-label` và `Tooltip`. Thêm `ButtonGroup`. Đưa spinner từ `attio.css` vào primitive. Giữ bộ props chung với `LotusMobileButton.vue`.
7. **Nhãn trạng thái và dải thông báo.** Thay `badge/` bằng `StatusBadge` theo bảng từ vựng (`spec.md` FR-005): tông, icon, chấm màu, hai cỡ. Thêm `Alert` bốn mức có icon và chỗ cho hành động, thay các class `.stock-error`, `.notice`, `.stock-success`, `.tk-banner`, `.lotus-modal-form__error`.
8. **Đưa hộp thoại vào `ui`.** Chuyển `WorkspaceModal`, `ModalForm`, `WorkspaceConfirm` vào `components/ui/dialog`, giữ tên cũ làm lớp xuất lại. Thêm `ConfirmDialog` có tông nguy hiểm, nhãn nút truyền qua `ask(text,{title,tone,confirmLabel,cancelLabel})`, không `autofocus` lên nút nguy hiểm. Thêm một `ConfirmHost` gắn một lần ở `App.vue` như `Toaster`, để 11 màn không phải tự gắn bốn ref.
9. **Bộ chọn và bật tắt.** `Tabs` (đưa `WorkspaceTabs` vào `ui`, thêm liên kết `tabpanel`, giữ `role=tab` cho test), `SegmentedControl` (thay 32 nút `aria-pressed` và `.land-views`, `.tk-subnav`, `.forecast-tabs`), `Switch`, `RadioGroup`, Checkbox có trạng thái chọn một phần, `Accordion` thay 16 thẻ `<details>`.
10. **Nhập số, ngày, tệp.** `NumberInput` mở rộng từ `MoneyInput`: đơn vị, min/max, bước, số lẻ; giữ `money-format.js` và test của nó. Thêm `TimeInput`, `DateTimePicker`; đưa `MonthPicker` vào `ui`; thay 16 ô ngày giờ gốc. Combobox thêm nút xoá, chọn nhiều, ảo hoá danh sách dài, nhóm có nhãn đọc được. `Upload` có vùng kéo thả, danh sách tệp, xem trước, dựng trên `FileInput` và `FilePickerButton`.
11. **Hiển thị.** `StatTile` gộp `DesktopMetricCard`, `WorkspaceSummaryStrip`, `.lotus-stat`, `.kpi` (hiện dấu gạch khi thiếu số, theo FR-034). `EmptyState` và `ErrorState` có kiểu ở mọi bề rộng. `Progress`, `Stepper`, `Timeline` (tổng quát hoá `LotusSignatureTimeline`, `.hr-steps`, `PurchaseProgress`). `Avatar`, `Kbd`, `Tree` (từ `MasterTree`), `DescriptionList` cho chi tiết chứng từ, `CommandPalette` tách khỏi `WorkspaceBar.vue`. Menu thêm mục hộp kiểm, chọn một, menu con.
12. **LotusIcon.** Tách dữ liệu đường vẽ ra một tệp đăng ký; thêm prop `size` theo token (16, 18, 20, 24), prop `stroke` giữ nét đều theo cỡ, prop `title` cho icon mang nghĩa. Bản dev cảnh báo khi tên không tồn tại. Thêm test quét mọi `icon:'…'` trong `src/*-navigation.js`, `src/mobile-menu.js`, `src/domain.js`. Sửa `landmark` ở `finance-navigation.js:12` và khoá `send` trùng. Gom 41 rule cỡ icon về prop. Bổ sung icon nghề vườn (buồng, dây màu, cân, tưới, phun, xe). Cập nhật `tests/workspace-sidebar.mount.test.js:20-21` nếu đổi dạng lưu.
13. **Toast.** Thêm icon theo tông và tông cảnh báo; đặt vị trí theo một token dùng chung với nút trò chuyện và phân trang; giữ API `toast()` và các con số trong `tests/use-toast.test.js`.

### Ưu tiên 2 — trang mẫu, kiểm thử, dọn dẹp

14. **Trang mẫu.** Dựng lại `UiShowcase.vue` theo sáu phần của `spec.md` User Story 6; mỗi primitive hiện đủ biến thể, cỡ, trạng thái; nạp cùng bộ CSS với `main.js`; ghi "dữ liệu mẫu". Thêm test: mọi thư mục trong `components/ui` phải có mặt trong trang mẫu. Giữ `vite.config.js` không chứa `showcase` (`tests/component-library.test.js:30-33`).
15. **Kiểm thử.** Thêm test mount cho Button, Input, Select, Textarea trong FormField (gắn `id`, `aria-*`, kiểu lỗi), DateRangePicker (gõ, khoảng nhanh, nhãn), DropdownMenu, Popover, Tooltip, FileInput, ConfirmDialog, phím của Tabs. Mở rộng phạm vi quét của `tests/design-tokens.test.js:8` sang `components/**`. Thêm test tương phản cho các cặp ở Điểm yếu 8.
16. **Dọn dẹp.** Quyết định giữ hay bỏ `badge`, `separator`, phần con của Card, biến thể `secondary`, cỡ `lg`, `tailwindcss-animate` (sửa `tests/ui-stack.test.js:34-40` cho khớp). Xoá import thừa ở `WorkspaceBar.vue:10`, `FarmWorkApp.vue:16`; xoá rule `.link-picker-*` và `.workspace-menu` trong `compact.css`. Thu hẹp `content` của Tailwind để không sinh `.grid`, `.table`, `.hidden`… ngoài ý muốn. Thống nhất một cách import (một tệp `components/ui/index.js`, một tên cho mỗi component).
