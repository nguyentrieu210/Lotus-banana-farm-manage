# Kiểm kê bộ giao diện điện thoại (PWA Vue 3 + Vant 4)

Nhánh `004-bo-giao-dien-agritech`, commit `40f8330`, kiểm ngày 10/11/2026.

Cách kiểm: đọc mã nguồn và đếm bằng grep/wc. Không chạy test, build hay trình duyệt. Số đo bundle lấy từ bản build đã commit ở `lotus_farm/public/frontend` (chưa build lại). Tương phản tính theo công thức WCAG 2.x từ mã màu trong `frontend/src/lotus-tokens.css`. Nhận định nào chỉ suy ra từ mã mà chưa nhìn trên máy thật thì ghi "chưa kiểm".

Đường dẫn không có tiền tố là tính từ `frontend/src/`.

## Hiện trạng

### 1. Phạm vi và số liệu

| Nhóm | Số file | Dòng | Byte |
|---|---|---|---|
| `components/LotusMobile*.vue` | 15 | 765 | 50.099 |
| `components/Mobile*.vue` | 7 | 528 | 45.254 |
| Gốc PWA: `WarehouseMobile.vue`, `BuyingMobile.vue`, `WorkMobile.vue`, `HrMobile.vue` | 4 | 1.662 | 123.043 |
| CSS điện thoại: `mobile-ui.css`, `mobile-work-legacy.css`, `warehouse-mobile.css`, `buying-mobile.css`, `work-mobile.css`, `hr-mobile.css`, `hr-mobile-attendance.css`, `purchase-proposal-mobile.css` | 8 | 893 | 97.714 |
| `mobile-*.js` (gồm `mobile-ui-theme.js`) | 7 | 209 | 15.805 |
| `use-mobile-*.js` | 3 | 108 | 5.723 |
| `*-mobile-main.js` | 4 | 46 | 1.620 |
| `components/field/*` chạy trên `/work` (11 trong 13 file) | 11 | 1.210 | 89.572 |

Tám file CSS điện thoại có 952 khối `{}`, 276 khai báo `font-size` bằng px (23 giá trị khác nhau, từ 11px đến 54px) và 9 khai báo dùng token chữ.

### 2. Năm bề mặt điện thoại

| App | Đường dẫn | Entry | Gốc | Class gốc và khung nội dung | Tab dưới | CSS riêng |
|---|---|---|---|---|---|---|
| Kho | `/warehouse` | `warehouse.html` → `warehouse-mobile-main.js` | `WarehouseMobile.vue` (766 dòng) | `.lotus-mobile` > `main.mobile-container#lotus-content` | 4: Trang chủ, Lịch sử, Xuất nhập tồn, Tôi (dòng 58-63) | `warehouse-mobile.css` |
| Mua hàng | `/buying` | `buying.html` → `buying-mobile-main.js` | `BuyingMobile.vue` (441 dòng) | `.buy-app` > `main.buy-main` | 4: Trang chủ, Đơn mua, Nhà cung cấp, Tôi (dòng 61-66) | `buying-mobile.css` (import ở `BuyingMobile.vue:29`), `purchase-proposal-mobile.css`, `procurement.css`, `signer-picker.css` |
| Công việc | `/work` | `work-mobile.html` → `work-mobile-main.js` | `WorkMobile.vue` (127 dòng) | `.lotus-mobile.lotus-work` > `main.mobile-container#lotus-content` | tối đa 4, lọc theo quyền: Hôm nay, Xác nhận, Giao việc, Tôi (dòng 26, 37) | `mobile-work-legacy.css`, `work-mobile.css` |
| Nhân sự | `/hr-mobile` | `hr-mobile.html` → `hr-mobile-main.js` | `HrMobile.vue` (328 dòng) | gốc không có class riêng > `main.hr-mobile-main` | 5: Trang chủ, Chấm công, Nhân viên, Tiếp nhận, Tôi (dòng 31) | `hr-mobile.css`, `hr-mobile-attendance.css` |

Bề mặt thứ năm là `/lotus/mobile` trong app máy tính: `components/MobileHome.vue` + `mobile-menu.js`. Nó không dùng Vant, dùng `ui/button`, `ui/input`, `ui/card` và `LotusIcon` (`MobileHome.vue:2-6`). Ở màn hẹp, `DataTable` của app máy tính đổi sang danh sách thẻ `.lotus-mobile-records`, CSS nằm ở `attio.css:81-113`.

Mỗi PWA có manifest, service worker và trang offline riêng trong `lotus_farm/public/` (`*.webmanifest`, `*-worker.js`, `*-offline.html`), phục vụ qua `lotus_farm/web.py`. Trang thật là `lotus_farm/www/{warehouse,buying,work,hr_mobile}.html`: `viewport-fit=cover`, `theme-color #c43224`. Các file `frontend/*.html` chỉ là entry cho Vite; `frontend/buying.html` còn ghi `theme-color #f3653c`, `frontend/work-mobile.html` ghi `#ed5932`.

### 3. Thứ tự nạp CSS

Trong nguồn (`*-mobile-main.js`): `vant/lib/index.css` → `lotus-fonts.css` → `lotus-tokens.css` → CSS của app và `<style>` của component → `shadcn.css` (Tailwind components + utilities, không có preflight) → `mobile-ui.css`.

Trong bản build, Vite tách CSS theo chunk. `mobile-ui.css` nằm chung một chunk với toàn bộ CSS Vant (`assets/mobile-ui-BBCYLE71.css`, 232.013 byte). CSS riêng của app nằm ở chunk entry: `work-mobile-DRvDeh0i.css` 28.038 byte, `warehouse-aAFuAqJN.css` 28.419 byte, `buying-Df07eCaK.css` 10.809 byte, `hr-mobile-EqNzDq2l.css` 4.896 byte. `lotus_farm/www/work.py:19-29` và `lotus_farm/www/warehouse.py:22-32` xếp CSS của các chunk phụ thuộc trước, CSS của entry sau cùng. Vì vậy trên máy chủ, CSS legacy của app đứng sau `mobile-ui.css`, ngược với thứ tự trong nguồn.

### 4. Token và ánh xạ theme Vant

- `lotus-tokens.css` có: ramp primary, neutral, success, warning, info (50 đến 900); token ngữ nghĩa cho sáng và `.dark`; cỡ chữ 11/12/13/14/16/20/24px; khoảng cách 4/8/12/16/24/32px; bo góc 6/8/10/12/16px; ba mức bóng; `--lotus-control-height:36px`; `--lotus-touch:44px`; `--lotus-motion:160ms`.
- Không có thang chữ riêng cho điện thoại. Cỡ nền 15px của shell viết tay ở `mobile-ui.css:8`; 15, 17, 18, 19, 21px không có trong token.
- `mobile-ui-theme.js:3` đưa 26 biến vào `ConfigProvider` (`theme-vars-scope="global"`, `LotusMobileShell.vue:23`): `primaryColor`, 3 biến nút chính, `successColor`, `dangerColor`, `warningColor`, `textColor`, `textColor2`, `textColor3`, `borderColor`, `background`, `background2`, 5 biến NavBar (cao 54px), 3 biến Tabbar (cao 60px), `buttonDefaultHeight:'48px'`, `buttonDefaultFontSize:'16px'`, `buttonBorderRadius:'12px'`, `dialogBorderRadius:'20px'`, `popupRoundBorderRadius:'20px'`.
- Chưa ánh xạ: font, thang chữ Vant (10/12/14/16px), bo góc, padding, cell (chữ 14px), nút small (cao 32px, chữ 12px), hộp kiểm (20px), notice bar (cao 40px), overlay, thời lượng chuyển động. Các giá trị này đang là mặc định của Vant (đọc từ CSS đã build).
- `mobile-ui.css:7,172` khai 13 alias `--lotus-pwa-*`. Sáu alias không được dùng lần nào: `--lotus-pwa-space-1/2/3/4/6` và `--lotus-pwa-touch`.
- Giao diện tối: `LotusMobileShell.vue:16-20` theo `prefers-color-scheme` của máy, gắn `.dark` lên `<html>` và bật theme tối của Vant. Không có nút chọn sáng/tối.

### 5. Giải phẫu shell, header, điều hướng dưới

```
ConfigProvider.lotus-pwa-shell[.lotus-pwa-keyboard]        LotusMobileShell.vue:23-29
 ├ header.lotus-pwa-header   sticky, z-index 60, nền --lotus-primary-600, chữ trắng
 │   NavBar #left : nút back 44×44 · khung logo trắng 106×38 · <strong> tiêu đề
 │   NavBar #right: chuông thông báo 44×44 + slot header-right
 ├ PullRefresh.lotus-pwa-pull → slot mặc định (main của app, hộp thoại của app)
 ├ LotusMobileOnboarding     Popup đáy, teleport ra body
 ├ nav.lotus-pwa-bottom      Tabbar fixed, z-index 55
 └ LotusMobileAiChat         nút nổi fixed z-index 75 + Popup đáy
```

- Shell: `min-height:100dvh`, `padding-bottom:calc(76px + safe-area)`, chữ 15px/1.5, rộng tối đa 600px và căn giữa từ 740px (`mobile-ui.css:8,113`).
- Header: cao 54px cộng safe-area trên. Logo là ảnh PNG `lotus-agritech-header-v2.png` (103.091 byte) trong khung nền `--lotus-surface`, 106×38px, còn 94×36px ở màn ≤360px (`mobile-ui.css:17,188`). Tiêu đề là `<strong>` 16px/700, 14px ở ≤360px, tối đa 2 dòng (`mobile-ui.css:16,189`). Vùng phải rộng 60px, 54px ở ≤360px.
- Điều hướng dưới: Tabbar 60px cộng safe-area dưới, icon 23px, chữ nhãn bị ẩn bằng `font-size:0` (`mobile-ui.css:23`). Tên tab nằm trong `aria-label`, `title` và `span.lotus-sr-only` (`LotusMobileBottomNav.vue:9`). Tab đang chọn: nền `--lotus-page`, icon màu `--lotus-primary`. Tabbar bị gỡ khỏi DOM khi bàn phím mở và `inert` khi `disabled`.
- Khung nội dung: `.mobile-container` và `.buy-main` rộng tối đa 600px, lề 16px (12px ở ≤360px) có cộng safe-area trái phải (`mobile-ui.css:27,114`). `.hr-mobile-main` tự đặt lề 14px, không cộng safe-area (`hr-mobile.css:2`).

### 6. Từng wrapper

| Component | Bọc Vant | Props (mặc định) | Emits | Slot | Class | Số thẻ / số file |
|---|---|---|---|---|---|---|
| `LotusMobileShell` | ConfigProvider, PullRefresh | `app` ('warehouse'), `user`, `title` ('Lotus'), `tabs`*, `activeTab`*, `back`, `keyboardOpen`, `disabled`, `notifications` (true), `onboarding` (true), `refresh` (Function), `refreshable` | `navigate`, `back` | mặc định, `header-right` | `lotus-pwa-shell`, `lotus-pwa-keyboard`, `lotus-pwa-pull` | 4 / 4 |
| `LotusMobileHeader` | NavBar, Icon | `title`*, `back`, `disabled`, `logo` (true) | `back` | `right` | `lotus-pwa-header`, `-header-title`, `-back`, `-logo-frame`, `-logo` | 1 / 1 |
| `LotusMobileBottomNav` | Tabbar, TabbarItem | `items`* (mỗi mục có `name` hoặc `id`, `label`, `icon`), `active`*, `hidden`, `disabled`, `label` | `navigate` | không | `lotus-pwa-bottom`, `lotus-sr-only` | 1 / 1 |
| `LotusMobileAction` | Button, Icon | `title`*, `icon` ('apps-o'), `symbol`, `primary`, `disabled` | `select`, `click` | không | `lotus-pwa-action`, `is-primary`, `is-disabled`, `-action-icon`, `-action-name`, `-action-arrow` | 12 / 2 |
| `LotusMobileButton` | Button | `type` ('button', thành `native-type`), `variant` ('default', thành `type` của Vant), `disabled`, `loading`; còn lại rơi thẳng xuống Button | không khai | mặc định | không có class riêng | 129 / 14 |
| `LotusMobileInput` | Field (nhãn trên, slot `#input` chứa `<input>`/`<textarea>` native) | `modelValue`, `label`, `type` (text, textarea, money hoặc kiểu native), `placeholder`, `required`, `disabled`, `rows` (2), `inputmode`, `min`, `max`, `step`, `maxlength`, `name`, `hint`, `error` | `update:modelValue` | không | `lotus-pwa-field`, `lotus-pwa-money`, `lotus-pwa-field-hint` | 65 / 7 |
| `LotusMobileSelect` | Field, Icon + `<select>` native | `modelValue`, `label`, `options`, `placeholder`, `disabled`, `required`, `hint`, `error` | `update:modelValue` | mặc định (các `<option>`) | `lotus-pwa-field`, `lotus-pwa-select`, `lotus-pwa-select-arrow` | 26 / 7 |
| `LotusMobileCheck` | Checkbox | `modelValue`, `disabled` | `update:modelValue` | mặc định (nhãn) | `mobile-check` | 3 / 2 |
| `LotusMobileFile` | Field + `<input type=file>` | chỉ `$attrs` | sự kiện native | không | `lotus-pwa-field`, `lotus-pwa-file` | 1 / 1 |
| `LotusMobileDialog` | Dialog | không; expose `showModal()`, `close()`, `open` | `cancel` (phím Esc) | mặc định | `lotus-pwa-dialog-body`; nơi gọi thêm `mobile-leave-dialog` | 11 / 8 |
| `LotusMobileFeedback` | NoticeBar, Loading | `kind`: info, error, warning, success, loading | không | mặc định | `lotus-pwa-feedback`, `mobile-message`, `danger`, `success` | 26 / 8 |
| `LotusMobileNotifications` | Icon, Badge, Popup, Button, Cell, Empty | `app`* | không | không | `lotus-notification*` | 1 / 1 |
| `LotusMobileOnboarding` | Popup, Button, Icon | `app`*, `title`* | không | không | `lotus-pwa-setup*` | 1 / 1 |
| `LotusMobileAiChat` | Button, Field, Icon, Popup | `user`, `pushApp`, `disabled`, `keyboardOpen` | không | không | `lotus-mobile-ai__*` | 1 / 1 |
| `LotusMobileSignatureSettings` | Icon | `user` | không | không | `lotus-signature-*` | 4 / 4 |
| `MobileLinkField` | Field, Icon, CellGroup | `modelValue`, `options`, `placeholder`, `disabled`, `required`, `label`, `ariaLabel`, `searchable` ('auto'; `false` thì dùng select native) | `update:modelValue` | không | `mobile-link-field`, `mobile-link-box`, `mobile-link-native-box`, `mobile-link-options`, `mobile-floating-options`, `mobile-link-up`, `is-highlighted` | 23 / 5 |
| `MobileLiveSearch` | Field, Icon, CellGroup, Loading | `modelValue`, `options`, `placeholder`, `loading`, `disabled` | `update:modelValue`, `select` | không | `mobile-live-search`, `mobile-live-box`, `mobile-live-clear`, `mobile-live-wait`, `mobile-live-results` | 3 / 1 |

Dấu * là bắt buộc. `MobilePurchaseOrderForm`, `MobilePurchaseOrderDetail` (Cell, CellGroup), `MobilePurchaseProposal`, `MobileSupplierForm` là màn nghiệp vụ ghép từ các wrapper trên; mỗi cái được Kho và Mua hàng dùng chung.

Cách các nơi gọi tạo kiểu cho `LotusMobileButton` (đếm trên 127 thẻ một dòng): 16 `class="buy-outline"`, 10 `mobile-submit`, 8 `buy-primary`, 6 `mobile-add`, 4 `buy-danger`, 4 `danger`, 9 `variant="primary"`, 12 `plain`, 15 `block`, 43 thẻ không có class lẫn variant.

`form/LotusField.vue:41-50` là cầu nối cho màn dùng chung: có `mobile` thì chọn `LotusMobileInput`, `LotusMobileSelect`, `MobileLinkField`, `LotusMobileCheck` hoặc `LotusMobileFile`. Nếu có `fetchOptions` thì vẫn dùng Combobox của máy tính (điều kiện `mobile&&!fetchOptions` ở dòng 50).

### 7. Hệ popup và hộp thoại

1. `LotusMobileDialog`: Vant Dialog giữa màn hình, tắt nút sẵn có, không đóng khi bấm nền hoặc popstate (`LotusMobileDialog.vue:16`), tự gắn `aria-labelledby` theo tiêu đề h1–h3 đầu tiên (dòng 8). `useMobileConfirm()` + `use-confirm-core.js` điều khiển: mỗi lúc một câu hỏi, `ask()` trả Promise. Nội dung xác nhận là markup `.mobile-leave-content` viết tay, lặp 7 lần ở 5 file.
2. Vant `Popup position="bottom" round`, mỗi nơi tự dựng header, nút đóng và lề safe-area: hộp thông báo (`LotusMobileNotifications.vue:101`, cao `min(82dvh,660px)`), thiết lập lần đầu (`LotusMobileOnboarding.vue:100-101`), AI chat (`LotusMobileAiChat.vue:114`, cao theo `visualViewport`), vẽ chữ ký (`LotusSignatureDraw.vue`), cắt ảnh chữ ký (`LotusSignatureImageEditor.vue`).
3. `WorkspaceModal` của máy tính (`<dialog>` native, teleport ra body, `WorkspaceModal.vue:30`) qua `form/ModalForm.vue`: mọi hộp thoại của `components/field/*` trên `/work`, `ReleaseNotes.vue`, và `CccdQrScanner.vue` (`<WorkspaceModal bare>`). CSS cho nó trên `/work` nằm ở `work-mobile.css:65-71`.
4. Danh sách gợi ý nổi `.mobile-floating-options` của `MobileLinkField` (tối đa 60 dòng) và `MobileLiveSearch` (tối đa 12 dòng): teleport ra body, z-index 200, vị trí do `use-mobile-popup.js` và `mobile-popup-layout.js` tính theo `visualViewport`, đáy header và đỉnh tabbar.
5. Khối xác nhận nằm trong trang `.lotus-delete-confirm` (`components/field/LotToday.vue:120-124`, `LotEntryModal.vue:193-196`).
6. Popover reka-ui của Combobox máy tính khi `LotusField` có `fetchOptions`, ví dụ ô vật tư ở `components/field/LotEntryModal.vue:85,160`.

Không có action sheet, bottom sheet dùng chung, toast hay xem ảnh phóng to dùng chung.

### 8. Safe-area và bàn phím

- `env(safe-area-inset-*)` xuất hiện 36 lần trong CSS và component điện thoại: đỉnh header (`mobile-ui.css:11`), đáy shell (dòng 8), lề trái phải khung nội dung (dòng 27), đáy Tabbar (`LotusMobileBottomNav.vue:8`), đáy hộp thông báo và hộp thiết lập (`mobile-ui.css:118,148`), nút AI (`LotusMobileAiChat.vue:158`). `hr-mobile.css` và `hr-mobile-attendance.css` không dùng lần nào.
- `use-mobile-viewport.js:6-15`: coi bàn phím đang mở khi có ô nhập được focus và `visualViewport.height` hụt hơn 140px so với mốc; ghi biến `--warehouse-visible-height` lên `<html>`.
- Khi bàn phím mở: shell thêm `.lotus-pwa-keyboard` (đệm đáy 16px), Tabbar bị gỡ, nút AI ẩn, kéo để tải lại bị tắt (`LotusMobileShell.vue:23,25,27`; `LotusMobileAiChat.vue:112`). Kho và Công việc còn thêm `.mobile-keyboard-open` (20px), Mua hàng thêm `.buy-keyboard` (10px), Nhân sự không thêm gì.
- Popup gợi ý tính lại vị trí khi `visualViewport` đổi và mở lên trên khi bên dưới còn dưới 180px (`mobile-popup-layout.js:8`).
- `html{scroll-padding-top:calc(80px + safe-area);scroll-padding-bottom:90px}` chỉ có ở Kho và Công việc (`warehouse-mobile.css:241`, `mobile-work-legacy.css:176`).
- Hộp thoại rời form giới hạn cao theo `--warehouse-visible-height` (`mobile-ui.css:87`). Tấm sửa công của Nhân sự dùng `80vh` (`hr-mobile-attendance.css:23`).

### 9. Vant dùng trực tiếp

26 file import từ `vant`, tổng 18 component. Không có thẻ `<van-*>` và không gọi `showToast`, `showDialog`, `showNotify` (0 lần).

| File | Component |
|---|---|
| `LotusMobileShell.vue` | ConfigProvider, PullRefresh |
| `LotusMobileHeader.vue` | NavBar, Icon |
| `LotusMobileBottomNav.vue` | Tabbar, TabbarItem |
| `LotusMobileAction.vue` | Button, Icon |
| `LotusMobileButton.vue` | Button |
| `LotusMobileInput.vue`, `LotusMobileFile.vue` | Field |
| `LotusMobileSelect.vue` | Field, Icon |
| `LotusMobileCheck.vue` | Checkbox |
| `LotusMobileDialog.vue` | Dialog |
| `LotusMobileFeedback.vue` | NoticeBar, Loading |
| `LotusMobileNotifications.vue` | Icon, Badge, Popup, Button, Cell, Empty |
| `LotusMobileOnboarding.vue` | Popup, Button, Icon |
| `LotusMobileAiChat.vue` | Button, Field, Icon, Popup |
| `LotusMobileSignatureSettings.vue` | Icon |
| `LotusSignatureDraw.vue` | Popup, Icon |
| `LotusSignatureImageEditor.vue` | Popup, Slider, Icon |
| `MobileLinkField.vue` | Field, Icon, CellGroup |
| `MobileLiveSearch.vue` | Field, Icon, CellGroup, Loading |
| `MobilePurchaseOrderDetail.vue` | Cell, CellGroup |
| `MobilePurchaseOrderForm.vue` | Icon, NoticeBar |
| `ProcurementMasters.vue`, `ProcurementWorkspace.vue` | Cell, CellGroup |
| `WarehouseMobile.vue`, `BuyingMobile.vue`, `HrMobile.vue` | Icon |
| `WorkMobile.vue`, `components/field/*`, `components/hr/HrMobileAttendance.vue` | không import Vant |

Số file theo component: Icon 15, Field 6, Popup 5, CellGroup 5, Button 5, Cell 4, NoticeBar 2, Loading 2; mỗi cái 1 file: Tabbar, TabbarItem, NavBar, PullRefresh, ConfigProvider, Dialog, Checkbox, Badge, Empty, Slider.

Chưa dùng: Toast, ActionSheet, Stepper, Switch, Tabs, Picker, Calendar, Search, Tag, Skeleton, SwipeCell, List, Collapse, Steps, Progress, Uploader, FloatingBubble, Sticky, Radio.

CSS của dự án ghi đè 28 class `.van-*`, tổng 97 lần. 49 lần trong đó là `.van-button`, `.van-button__content`, `.van-button__text`, vì Button được dùng làm thẻ, dòng danh sách và ô thao tác. Khoảng 35 tên icon Vant được dùng; CSS Vant mang theo 259 glyph.

### 10. Vùng chạm

| Thành phần | Kích thước khai báo | Nguồn |
|---|---|---|
| Token | `--lotus-touch:44px`; cả `src` dùng 13 lần, `mobile-ui.css` dùng 5 lần | `lotus-tokens.css` |
| Nút Vant mặc định | cao 48px, chữ 16px, bo 12px | `mobile-ui-theme.js:3` |
| Nút chính `.mobile-submit`, `.buy-primary` | tối thiểu 50px | `mobile-ui.css:51` |
| Nút viền `.mobile-add`, `.buy-outline` | tối thiểu 46px | `mobile-ui.css:52` |
| Ô thao tác trang chủ | tối thiểu 112px; hàng chính 82px; icon 46×46 | `mobile-ui.css:59,62,68` |
| Tab dưới | tối thiểu 60px | `mobile-ui.css:21` |
| Nút back, chuông, nút mở danh sách, nút xoá tìm | 44×44 | `mobile-ui.css:117,136,174` |
| Dòng gợi ý | tối thiểu 56px | `mobile-ui.css:138` |
| Nút hộp thoại, nút thiết lập | tối thiểu 48px | `mobile-ui.css:144,161` |
| Nhân sự | nút 46px; dòng nhân viên 66px; dòng công 56px; ô số liệu 64px; nút chế độ 44px | `hr-mobile.css:11,21`; `hr-mobile-attendance.css:6,14,26` |
| Nút AI nổi | 88×52 | `LotusMobileAiChat.vue:158` |
| Dưới 44px | `.pp-scopes button` 36px; `.pp-remove` 32px; `.lotus-signature-editor button` 42px; hộp kiểm Vant 20px, cả dòng nhãn cao khoảng 24px; `UiButton` 36px và 32px với `size="sm"`; nút xoá dòng 36×36; Combobox, Input, Select máy tính 36px | `purchase-proposal-mobile.css:4,17`; `components/lotus-signature-editor.css:5`; `components/ui/button/index.js:17-20`; `components/form/LineItemsEditor.vue:58` |

Không file nào có quy tắc `@media (pointer:coarse)`.

### 11. Cỡ chữ

- Nền shell 15px; ô nhập 16px (`mobile-ui.css:33`); nhãn ô nhập và gợi ý 13px; nút 16px, nút viền 15px; tiêu đề header 16px (14px ở ≤360px); tên ô thao tác 15px (17px cho ô chính).
- Thẻ kiểu cũ: `.mobile-list-card strong` 19px, `small` 14px, số bên phải 19px. Thẻ Mua hàng: tên 16px, mã 12px, mô tả 12px, số tiền 16px/800. Nhãn trạng thái 12px (11px ở ≤360px).
- Chữ nhỏ nhất: 10px (dòng phụ của AI chat ở ≤360px, `LotusMobileAiChat.vue:190`), 11px (ngày của thông báo, nhãn `pp-state`, nút công cụ cắt ảnh chữ ký), 12px ở 35 khai báo.
- 11 component `components/field/*` chạy trên `/work` khai 31 cỡ chữ, 28 cái là `--lotus-text-sm` (12px), dùng cho mọi dòng phụ trên thẻ lô, thẻ việc, thẻ màu dây.

### 12. CSS từng app

| File | Dòng / byte | Sở hữu | Phần thừa |
|---|---|---|---|
| `mobile-ui.css` | 198 / 23.097 | shell, header, tabbar, ô nhập, nút, ô thao tác, popup gợi ý, hộp thoại rời form, form và chi tiết đơn mua, feedback, hộp thông báo, thiết lập lần đầu, link in, trạng thái trống | 7 class không template nào dùng: `lotus-pwa-sr-only`, `mobile-field`, `mobile-inline-input`, `mobile-loading`, `mobile-screen-bar`, `work-list-row`, `work-primary`; 11 `!important`; chứa selector riêng của app (`.buy-*`, `.work-*`, `.lotus-purchase-*`) |
| `warehouse-mobile.css` | 268 / 29.875 | reset toàn cục (`:root`, `*`, `button`, `h1`, `h2`), thẻ, dòng hàng, tóm tắt, chuyển tab, tài khoản của Kho; 5 lớp lịch sử chồng nhau (bản xanh lá, "ứng dụng mua sắm", v3, v4, lớp tương tác chung) | 21/73 tên class app Kho không dùng; `.lotus-mobile` khai 6 lần, `.mobile-action strong` 8 lần; 37 `!important`; 12 `@media` |
| `mobile-work-legacy.css` | 197 / 20.919 | bản sao cho Công việc | 190/192 quy tắc trùng nguyên văn với `warehouse-mobile.css`; 25/49 tên class app Công việc không dùng; 14 `!important` |
| `work-mobile.css` | 71 / 7.487 | `.lotus-work …` và CSS của `.workspace-modal` trên `/work` | 26/40 tên class không dùng (cả nhóm `work-status`, `work-list-row`, `work-chips`, `work-info`, `work-queue-actions`, `work-preview-*`) |
| `buying-mobile.css` | 78 / 8.001 | reset, `.buy-*`: thẻ, tóm tắt, toolbar, nút, thẻ đơn mua | 9/41 không dùng: `buy-alert`, `buy-edit-line`, `buy-empty`, `buy-head-back`, `buy-inline-action`, `buy-quick`, `buy-search`, `buy-total`, `buy-two` |
| `hr-mobile.css` | 23 / 2.532 | `.hr-mobile-*` | 1: `hr-mobile-loading` |
| `hr-mobile-attendance.css` | 28 / 2.589 | `.hr-att__*` (BEM) | 0 |
| `purchase-proposal-mobile.css` | 30 / 3.214 | `.pp-*`, chỉ dùng token | 3: `pp-steps`, `pp-steps__mark`, `pp-steps__sign` |
| `field-todo.css` | 15 / 1.348 | `.field-todo-*` | không file nào import |
| `components/lotus-mobile-signature.css`, `components/lotus-signature-editor.css`, `signer-picker.css` | 30 / 3.949; 25 / 3.298; 24 / 2.781 | chữ ký, người ký | `signing-panel__steps` không dùng |

Cộng lại, 81 tên class được khai báo mà app tương ứng không dùng (21 + 25 + 26 + 9).

Tám file CSS điện thoại cùng `components/lotus-mobile-signature.css` tham chiếu ramp cố định 241 lần và token ngữ nghĩa 425 lần. `--lotus-primary-600` được gọi thẳng 94 lần, `--lotus-success-900` 14 lần. Có 131 khai báo `border-radius` với 18 giá trị viết tay; 8 khai báo dùng token.

### 13. `components/field/*` trên điện thoại

`WorkMobile.vue` dùng `LotToday` (kéo theo `LotCards`, `LotEntryModal`, `CrewStatus`, `PaperPhotoReview`), `RibbonBoard`, `CareDueList`, `MyPay`, `WorkAssign` và `WorkInspect` (kéo theo `WorkTicket`). `PackhouseShifts` và `CareCycleSettings` chỉ chạy trên máy tính.

11 file này không import wrapper `LotusMobile*` nào và không import Vant. Chúng nhận prop `mobile` (45 chỗ truyền) để: xếp `FormGrid` một cột, đổi `LotusField` sang control điện thoại, đổi lưới thẻ thành một cột. Phần còn lại là primitive máy tính: `UiButton` (38 thẻ trong 10 file, 16 thẻ `size="sm"`), `ModalForm` → `WorkspaceModal`, `LineItemsEditor`, `ReasonDialog`, `DataTable` (AG Grid, trong `RibbonBoard.vue:87` và `CareDueList.vue:121`), `WorkspaceSummaryStrip`, `ListPage`, `FilePickerButton`.

Mẫu thẻ hiện có: thẻ lô `.lot-card` (viền trái 4px theo trạng thái, đệm 10×12px, `LotCards.vue:40-52`), thẻ việc `.care-due__card`, thẻ màu dây `.ribbon-card` và `.ribbon-due`, thẻ tổ `.crew-status__team` (đệm 6×10px), thẻ phiếu `.field-assign__card` (mượn `.mobile-list-card`), dòng tiền khoán `.my-pay__head`. Không thẻ nào khai `min-height`.

### 14. Offline, cập nhật, thông báo đẩy

- Service worker của bốn app chỉ cache tài nguyên build và trang offline tĩnh, không cache API (`lotus_farm/public/*-worker.js`). Khi mất mạng lúc mở app, người dùng thấy `*-offline.html`.
- Băng báo mất mạng: Kho (`WarehouseMobile.vue:561`) và Mua hàng (`BuyingMobile.vue:311`) qua `LotusMobileFeedback kind="warning"`; AI chat có dòng riêng (`LotusMobileAiChat.vue:149`). `WorkMobile.vue` và `HrMobile.vue` không theo dõi `online`/`offline`.
- Hàng chờ ghi `offline.js` (IndexedDB) chỉ `App.vue` của máy tính dùng. Cache đọc `offline-cache.js:4` chỉ cho 8 method `console.*`, `daily_api.daily_overview`, `field.bootstrap`, `field.available_labor`; không có method nào của `/work` (`field_report.*`, `lot_report.*`, `ribbon_board.board`, `care_cycle.due`).
- `/work` giữ số đang nhập của từng lô trong `localStorage`, ghi sau 400ms (`lot-entry-model.js:116-126`, `LotEntryModal.vue:47-52`), và báo "Đã khôi phục số đang nhập dở" khi mở lại (`LotEntryModal.vue:115`).
- Nhắc có bản mới: chỉ Kho (`WarehouseMobile.vue:162-163,564`).
- Thông báo đẩy: chuông trên header với Badge, mở Popup đáy có nút bật, tắt, gửi thử và danh sách thông báo, tự tải lại mỗi 60 giây (`LotusMobileNotifications.vue:91`). Thiết lập lần đầu 3 bước cài app → bật thông báo → hướng dẫn (`LotusMobileOnboarding.vue`), mở lại bằng sự kiện `lotus:open-setup`. Đăng xuất gỡ endpoint đẩy của máy (`mobile-push-session.js`). Worker đẩy dùng icon `lotus-agritech.jpg`, không có badge icon và không có nút hành động (`lotus_farm/public/lotus-push-worker.js`).

### 15. Trọng lượng (bản build đã commit, byte chưa nén, tính theo chuỗi import tĩnh)

| Entry | JS | CSS | Chunk đáng chú ý |
|---|---|---|---|
| `work-mobile.html` | 2.127.677 | 343.711 | `DataTable-BqIzjUwq.js` 959.028 (AG Grid); `hr-catalog-labels-CSAYCmjS.js` 491.048 (chứa từ điển `system-translations.js`, nguồn 524.405 byte) |
| `buying.html` | 2.406.918 | 330.638 | hai chunk trên, `ProcurementWorkspace` 103.605, `StockDocumentDetail` 52.618, `ErpSection` 40.637 |
| `warehouse.html` | 676.730 | 322.319 | không có AG Grid |
| `hr-mobile.html` | 965.390 | 286.575 | `hr-catalog-labels-CSAYCmjS.js` 491.048 |

Mọi app tải `mobile-ui-BBCYLE71.css` 232.013 byte, trong đó có 397 gốc class `.van-*` (1.054 class), dù chỉ 18 component Vant được dùng. Font Inter biến thiên 264.236 byte. Service worker tải trước toàn bộ danh sách này khi cài (`cache.addAll(ASSETS)`).

### 16. Test đang ghim gì

| Test | Ghim |
|---|---|
| `tests/lotus-mobile-shared.test.js` | Ba gốc Kho, Mua hàng, Công việc có `<LotusMobileShell`, `:tabs="mobileTabs"`, `@navigate=`; entry import `vant/lib/index.css` và `mobile-ui.css`; header có `NavBar`, `class="lotus-pwa-logo"`, `@click="emit('back')"`; bottom có `TabbarItem`, `v-if="!hidden"`, `safe-area-inset-bottom`, `:aria-label="item.label"`, `class="lotus-sr-only"`; theme có `navBarHeight:'54px'`, `tabbarHeight:'60px'`; ô thao tác có `import {Button,Icon} from 'vant'`, `class="lotus-pwa-action-icon"`, `@click="choose"`; "Tạo đơn mua" đứng trước "Nhập theo đơn" |
| `tests/warehouse-mobile-standalone.test.js` | `WarehouseMobile.vue` không chứa `DataTable`, `AGGrid`, `UiButton`, `frappe-ui`; có `class="mobile-switcher"`, `class="mobile-line"`, `class="mobile-actions"` đứng trước `class="mobile-install"`; `warehouse-mobile.css` khớp `mobile-actions{grid-template-columns:repeat(2` và `mobile-submit{…min-height:64px`; `MobileLinkField` có `@focus="reveal"`, `@input="changed"`, `role="listbox"`; có `popstate`, `pushState`, `confirmLeave`, `flush:'sync'` |
| `tests/warehouse-mobile-ux-v4.test.js` | `MobileLinkField` có `ArrowDown`, `aria-activedescendant`, `mobile-link-up`; `warehouse-mobile.css` có `.mobile-link-options.mobile-link-up`; `mobile-ui.css` có `.lotus-pwa-back{width:44px;min-width:44px`; `MobileLiveSearch` có `@focus="open"`, `@input="typed"`, `role="listbox"`; nhãn 4 tab của Kho; chặn kết quả đến muộn bằng `pendingRequest`, `historyRequest`, `inventoryRequest` |
| `tests/mobile-shared-plan.test.js` | `LotusMobileInput`, `LotusMobileSelect` có nguyên văn `hint:String,error:String`, `:aria-invalid="!!error"`, `:error-message="error||undefined"`, `lotus-pwa-field-hint`; `mobile-ui.css` có `@media(max-width:360px)`, `.lotus-pwa-logo-frame{width:94px;flex-basis:94px;height:36px}`, `--lotus-pwa-touch:var(--lotus-touch)`; token `--lotus-touch:44px`; entry Công việc import `mobile-work-legacy.css` và không import `warehouse-mobile.css`; file legacy phải có `.mobile-container`, `.mobile-field`, `.mobile-inline`, `.mobile-list-card`, `.mobile-line`; ba gốc có `function openSetup()`, `lotus:open-setup`; manifest có id riêng và icon maskable 512 |
| `tests/lotus-pwa-setup.test.js` | Header có `#left`, `lotus-agritech-header-v2.png`; `mobile-ui.css` có `.lotus-pwa-header .van-nav-bar__left` và nguyên văn `.lotus-pwa-logo{display:block;max-width:100%;max-height:100%;width:100%;height:100%;object-fit:contain`; ba gốc chứa "Cài ứng dụng và thông báo" và "Rời đi"; tên app "Công việc ngoài vườn" |
| `tests/two-lotus-pwas.test.js`, `tests/buying-mobile-pwa.test.js`, `tests/warehouse-mobile-pwa.test.js`, `tests/hr-mobile-qr.test.js` | id, scope, start_url của manifest; mỗi app một worker và một tên cache; worker không cache `/api/`; trang `www` trỏ đúng manifest và icon; Mua hàng và Nhân sự giữ trang đăng nhập trong scope |
| `tests/buying-order-cards.test.js` | `LotusMobileButton class="buy-order-card"`; các class `buy-order-supplier`, `-status`, `-code`, `-bottom`, `-amount`; `buying-mobile.css` có `.buy-order-card .van-button__text{`, `white-space:nowrap` cho trạng thái và số tiền, `text-overflow:ellipsis` cho tên NCC |
| `tests/mobile-ai-chat.mount.test.js` | Mount thật: `.lotus-mobile-ai__popup`, `.lotus-mobile-ai__fab`, `.lotus-mobile-ai__suggestion`, `.lotus-mobile-ai__message`, `aria-label` "Hỏi trợ lý Lotus AI" và "Cuộc hỏi mới"; shell có `<LotusMobileAiChat :user="user"`; bốn gốc có `<LotusMobileShell app="…" :user="session?.user` |
| `tests/mobile-signature-settings.test.js` | Bốn gốc có `<LotusMobileSignatureSettings :user="session?.user\|\|''"/>`; input file native có class `lotus-signature-visible-input`; CSS chữ ký có `opacity:1;appearance:auto`, `pointer-events:auto`; editor có `max-height:96dvh` |
| `tests/lotus-push-pwa.test.js`, `tests/hr-setup-notifications.test.js` | Shell có `<LotusMobileNotifications v-if="notifications"`, `<LotusMobileOnboarding v-if="onboarding"`, `:app="app"`; bốn gốc gọi `logoutPwa('<app>'`; không có `href="/logout"` |
| `tests/design-tokens.test.js` | Theme có `primaryColor:'var(--lotus-primary)'` và không có hex 6 số; mỗi entry import `lotus-tokens.css` trước CSS khác; không hex đục trong `src/*.css`, `src/*.vue`, `src/components/*.vue`; chỉ một font; bốn gốc không gọi `window.alert/confirm`; mọi `var(--lotus-*)` phải được định nghĩa; template không chứa các ký tự `↻⟳◌☀☼☾⚙◷♧▦▣` |
| `tests/form-standard.test.js:38-44` | `WarehouseMobile.vue`, `WorkMobile.vue`, `MobilePurchaseOrderForm.vue` không bọc nhãn tay quanh control điện thoại |
| `tests/ui-stack.test.js:56-60` | Bốn entry điện thoại import `./shadcn.css` |
| `tests/mobile-popup-layout.test.js`, `tests/mobile-swipe.test.js`, `tests/mobile-menu.test.js`, `tests/mobile-purchase.test.js` | Hợp đồng hàm thuần `popupLayout`, `swipeStep`, `createTabSwipe`, `mobileActions`, `mobileTabs`, `purchasePayload` |
| Test mount của màn hiện trường và mua hàng | `lot-entry`: `.lot-card__main`, `.lot-today__ask`, `.lot-entry__line`, `dialog.lot-entry-modal[open]`; `care-due-list`: `.care-due__card`, `.care-due__lots`, `.care-due__zone`; `ribbon-board`: `.ribbon-card`, `.ribbon-due`, `.ribbon-board__totals`; `paper-photo-review`: `.paper-review__lot`, `.paper-review__photo`; `hr-mobile-attendance`: `.hr-att__row`, `.hr-att__sheet`, `.hr-att__stats`; `purchase-proposal`: `a.pp-print`, `.pp-line`, `.van-field`; `purchase-flow`: `.van-cell`, `[role=tab]` |
| `tools/verify_mobile_purchase_dom.mjs`, `tools/verify_warehouse_mobile_dom.mjs` | `.lotus-purchase-form`, `.lotus-supplier-form`, `.van-dialog`, `.van-field__label`, `input[type=number]`, `input[role=combobox]`, `[role=option]`, `[role=listbox]`, `.mobile-keyboard-open`, `.mobile-summary`, `.mobile-line`, `.mobile-actions`, `.mobile-account`, `.lotus-mobile`, `.mobile-link-native-box select` |

Phần lớn test trên là so chuỗi trong mã nguồn. Chưa có test mount cho `LotusMobileShell`, `LotusMobileHeader`, `LotusMobileBottomNav`, `LotusMobileButton`, `LotusMobileInput`, `LotusMobileSelect`, `LotusMobileCheck`, `LotusMobileDialog`, `LotusMobileFeedback`, `MobileLinkField`, `MobileLiveSearch`.

## Ràng buộc phải giữ

### Quy ước của chủ vườn

- `AGENTS.md:25`: mọi PWA dùng Vue 3 và Vant 4, chung `LotusMobileShell`, `LotusMobileHeader`, `LotusMobileBottomNav`; không tạo header, bottom hay bộ component riêng cho từng app.
- `AGENTS.md:12,26`: màu chính duy nhất là Đỏ Lotus `#c43224`; màu, chữ, khoảng cách, bo góc, bóng lấy từ `lotus-tokens.css`; không ghi hex trong CSS khác (trừ trắng, đen, bóng trong suốt); safe-area và bố cục PWA ở `mobile-ui.css`; `mobile-ui-theme.js` chỉ trỏ tới token.
- `AGENTS.md:27`: nút, ô nhập, lựa chọn, hộp thoại, thao tác trang chủ dùng wrapper Vant chung; input native cho ngày, số, file, bàn phím và validation HTML nằm bên trong component chung.
- `AGENTS.md:28`: header một hàng; điều hướng dưới dùng biểu tượng gọn, có tên truy cập đầy đủ, ẩn khi bàn phím mở; không lặp tiêu đề lớn hay mô tả trang trí; không tràn ngang ở 320px; popup và nội dung không bị header, bottom che.
- `AGENTS.md:29`: đổi giao diện không được đổi API, phân quyền, trạng thái chứng từ, chống gửi trùng, xác nhận rời form, cách tách service worker.
- `AGENTS.md:31`: manifest và service worker của từng PWA độc lập; tìm và chọn dữ liệu phải gợi ý khi gõ, không bắt Enter; giữ IME và cuộn popup.
- `AGENTS.md:32`: mỗi lần sửa UI điện thoại phải chạy unit test frontend, build và kiểm các PWA ở màn hẹp.
- `AGENTS.md:34`: header màu đỏ Lotus, logo đủ lớn, rõ chữ, một hàng ở 320px; không thu logo về biểu tượng 30px.
- `AGENTS.md:35`: tạo, sửa, xem đơn mua và tạo nhà cung cấp của Kho và Mua hàng dùng chung `MobilePurchaseOrderForm`, `MobileSupplierForm`, `MobilePurchaseOrderDetail`, `mobile-purchase.js`.
- `AGENTS.md:36`: named link luôn tìm và chọn một cách; select native chỉ khi khai `searchable=false`; lỗi, cảnh báo, xác nhận dùng component và composable chung.
- `AGENTS.md:18`: xác nhận trên PWA dùng `useMobileConfirm`; icon không dùng ký tự.
- `.specify/memory/constitution.md` mục V: điện thoại dùng Vue 3, Vant 4, wrapper `LotusMobile*`; chữ hiển thị tiếng Việt. Mục IV: component có hành vi phải có test mount.
- `docs/UI_STACK.md:13`: AG Grid cho bảng trên máy tính; điện thoại dùng danh sách nút theo dòng.
- `docs/FIELD_REPORT.md:7,12`: `/work` có 4 tab Hôm nay, Giao việc, Xác nhận, Tôi; mỗi lô là một thẻ, bấm thẻ để mở hộp nhập của lô.
- `docs/MOBILE_UI_STANDARD.md:19`: header 54px, bottom 60px cộng safe-area, nội dung tối đa 600px, lề 12px ở 320px và 16px bình thường, ô nhập 16px để iOS không tự zoom.

### Hợp đồng kỹ thuật

- Mọi chuỗi ở mục "Test đang ghim gì". Đổi tên class, đổi prop hay bỏ file thì phải sửa test trong cùng thay đổi.
- `use-mobile-popup.js:12-13` tìm header bằng `.lotus-pwa-header,.mobile-head` và tabbar bằng `.lotus-pwa-bottom .van-tabbar`. `WarehouseMobile.vue:101,126,165` dựa vào `.mobile-message.danger`, `.mobile-link-field`, `.mobile-live-search`, `.lotus-pwa-bottom`, `.mobile-leave-dialog`, `.mobile-floating-options`.
- `LotusMobileButton` nhận `class`, `icon`, `plain`, `block`, `size`, `role`, `id`, `aria-*`, `autofocus` và sự kiện qua attribute rơi xuống Vant Button; 129 thẻ ở 14 file dựa vào điều này.
- `LotusMobileDialog` giữ API `showModal()`, `close()`, `open` và sự kiện `cancel`; `useMobileConfirm()` trả `{dialog,message,pending,ask,finish}`.
- `LotusMobileInput` giữ `type="money"` (gõ tự do khi focus, nhóm số khi blur), thuộc tính native `required/min/max/step/maxlength/inputmode`, và `aria-label` lấy từ `label`.
- Nút lưu phải là `type="submit"` trong DOM (`docs/MOBILE_UI_STANDARD.md:31`).
- Khoá lưu trữ: `lotus-pwa-setup-v1:<app>`, `lotus-pwa-installed:<app>` (localStorage), `lotus-ai-chat|<user>` (sessionStorage), bản nháp lô trong `lot-entry-model.js`. Sự kiện `lotus:open-setup`. Đổi tên thì người dùng mất trạng thái đã lưu.
- Manifest: `id`, `scope`, `start_url` của bốn app; tên cache `lotus-warehouse-shell-`, `lotus-buying-shell-`, `lotus-work-shell-`, `lotus-hr-mobile-`.
- `design-tokens.test.js:21-28`: `lotus-tokens.css` là CSS đầu tiên sau `lotus-fonts.css` ở mọi entry.
- Kéo để tải lại chỉ bật ở màn gốc để không tải lại form đang nhập (`LotusMobileShell.vue:12`).
- Chống gửi trùng bằng `client_event_id`, chặn kết quả đến muộn, xử lý nút back của hệ thống trong `WarehouseMobile.vue:169-203` và `BuyingMobile.vue` là hành vi nghiệp vụ, không thuộc phần đúc lại giao diện.

## Điểm yếu

### A. Màn hiện trường không dùng bộ điện thoại

1. 11 component của `/work` import 0 wrapper `LotusMobile*` và 0 component Vant; chúng dựng bằng `UiButton`, `ModalForm`, `LineItemsEditor`, `DataTable`. Bằng chứng: phần import của `components/field/LotToday.vue:4-12`, `LotEntryModal.vue:4-8`, `CareDueList.vue:4-8`, `WorkAssign.vue:4-9`, `WorkTicket.vue:4-9`.
2. Danh sách gợi ý của `MobileLinkField` luôn teleport ra `body` (`MobileLinkField.vue:66`, `MobileLiveSearch.vue:67`). Hai chỗ đặt nó trong `<dialog>` modal: ô "+ Việc khác…" (`components/field/LotEntryModal.vue:122`) và ô bắt buộc "Công việc" (`components/field/WorkAssign.vue:95`). `components/ui/portal-target.js:2-3` ghi rõ danh sách teleport ra body trong lúc dialog modal mở thì không bấm được. Combobox máy tính dùng `useDialogPortal`, `MobileLinkField` thì không. Chưa kiểm trên trình duyệt thật.
3. Class dùng trên `/work` mà không có CSS được nạp: `.lotus-form-note` (27 chỗ; chỉ định nghĩa ở `components/stock/StockDocumentForm.vue:224`, file không nằm trong chuỗi import của `/work`), `.field-report__notice` và `.field-report__warning` (không định nghĩa ở đâu; dùng ở `LotToday.vue:103`, `WorkAssign.vue:72-73`, `WorkTicket.vue:68`), `.work-today__cards`, `.work-today__card`, `.work-today__main` (không định nghĩa ở đâu; `WorkInspect.vue:26-27`), `.stock-success` (`CareDueList.vue:81`; chỉ có trong CSS máy tính), `.workspace-summary-strip` (`WorkTicket.vue:77`; chỉ có ở `workspace-experience.css`). Đã đối chiếu với các chunk CSS của `work-mobile.html` trong bản build: không chunk nào chứa các class này.
4. `DataTable` trên `/work` thiếu CSS chuyển chế độ: `.lotus-mobile-records{display:none}` và `@media` đổi sang thẻ nằm ở `attio.css:81-113`, file chỉ `main.js` nạp. `RibbonBoard.vue:87` mở `DataTable` 9 cột trong hộp thoại trên điện thoại. Điều này cũng trái `docs/UI_STACK.md:13`. Chưa kiểm hiển thị.
5. Quy tắc nền của bộ điện thoại bị khoá trong `.lotus-pwa-shell` nên không tới nội dung teleport. Ví dụ `mobile-ui.css:33` đặt chữ ô nhập 16px chỉ cho `.lotus-pwa-shell .lotus-pwa-field …`; hộp nhập lô nằm trong `dialog.workspace-modal` ngoài shell nên ô nhập thừa hưởng 14px của `.van-cell`, dưới ngưỡng tránh iOS tự zoom mà `docs/MOBILE_UI_STANDARD.md:19` đặt ra. `MobileLinkField` trong hộp thoại nhận kiểu legacy (viền 1.5px, cao 56px, chữ 17px ở `mobile-work-legacy.css:100-103`), còn `LotusMobileInput` cạnh nó nhận kiểu mới. Chưa kiểm trên iPhone.
6. `LotusField` có `mobile` và `fetchOptions` vẫn dựng Combobox máy tính cao 36px (`form/LotusField.vue:50,57`); ô chọn vật tư trong hộp nhập lô đi đường này (`LotEntryModal.vue:85,160`).

### B. CSS: thứ tự, trùng lặp, mã chết

7. Thứ tự CSS trên máy chủ ngược với nguồn và với `docs/MOBILE_UI_STANDARD.md:19` ("CSS cuối cùng: mobile-ui.css"): `lotus_farm/www/work.py:19-29` nạp CSS chunk entry (legacy) sau chunk chứa `mobile-ui.css`. Các cặp cùng độ ưu tiên sẽ cho kết quả khác giữa dev và production: `.lotus-pwa-shell{padding-bottom:calc(76px + …)}` với `.lotus-mobile{padding-bottom:calc(80px + …)}` và `.buy-app{…82px…}`; `.lotus-pwa-keyboard` 16px với `.mobile-keyboard-open` 20px và `.buy-keyboard` 10px. Chưa kiểm trên máy.
8. `mobile-work-legacy.css` lặp nguyên văn 190/192 quy tắc của `warehouse-mobile.css`.
9. 81 tên class khai báo mà app tương ứng không dùng; `field-todo.css` không được import. `warehouse-mobile.css` còn nguyên header cũ (`.mobile-head-home`, `.mobile-logo`, `.mobile-brand-text`, `.mobile-back`) với 37 `!important`.
10. `warehouse-mobile.css:214-215`: chú thích mở ở dòng 214 nuốt một đoạn quy tắc (`header gon{justify-content:center!important;flex:1}`).
11. `mobile-ui.css` là file "bộ" nhưng chứa selector của từng app: `.buy-main`, `.buy-field`, `.buy-toolbar`, `.buy-primary`, `.work-primary`, `.work-list-row`, `.lotus-purchase-*` (dòng 27-31, 47-53, 90-112).
12. File legacy đặt quy tắc lên thẻ trần cho cả trang: `h1{font-size:26px}`, `h2{font-size:21px;margin:25px 0 12px}`, `button:disabled{opacity:.48}` (`warehouse-mobile.css:4,13-14`, `mobile-work-legacy.css:7-13`, `buying-mobile.css:1-3`). `work-mobile.css:68` phải viết lại `h2` cho hộp thoại vì thế.
13. Test ghim giá trị không còn hiệu lực: `warehouse-mobile-standalone.test.js:31` đòi `mobile-submit{…min-height:64px` trong khi `mobile-ui.css:51` đặt 50px với độ ưu tiên cao hơn; `mobile-shared-plan.test.js:51` đòi `.mobile-field` có trong file legacy dù không template nào dùng class này.
14. `design-tokens.test.js:7-8` chỉ quét `src/*.css`, `src/*.vue` và `src/components/*.vue`. `components/lotus-signature-editor.css` có hai màu hex đục `#212936` và `#eaeaea` mà test không bắt. `components/field/*`, `components/hr/*`, `components/form/*` cũng không được quét.

### C. Không nhất quán

15. Bảy cách tạo nút chính: `class="mobile-submit"` (Kho, form chung), `class="buy-primary"` (Mua hàng), `variant="primary" block` (Nhân sự), `UiButton` mặc định (màn hiện trường), `<Button type="primary">` của Vant gọi thẳng (`LotusMobileNotifications.vue:107`, `LotusMobileOnboarding.vue:118`), `.signing-panel__primary` (`SigningPanel.vue`), `.lotus-signature-editor-primary`.
16. 14 họ class thẻ: `mobile-list-card`, `mobile-line`, `buy-card`, `buy-order-card`, `pp-card`, `hr-mobile-card`, `hr-mobile-row`, `hr-att__row`, `lot-card`, `ribbon-card`, `care-due__card`, `crew-status__team`, `field-assign__card`, `my-pay__team`. Bo góc từ 8px đến 16px, viền 1px hoặc 1.5px, có nơi có bóng.
17. 4 họ nhãn trạng thái (`mobile-status`, `buy-pill`, `buy-order-status--*`, `pp-state`), 6 kiểu ô số liệu (`buy-summary`, `hr-mobile-stats`, `hr-att__stats`, `ribbon-board__totals`, `mobile-summary`, `workspace-summary-strip`), 4 kiểu chuyển chế độ (`mobile-switcher`, `pp-scopes`, `hr-att__modes`, `lotus-chat-tabs`).
18. Ba tên khung nội dung và ba kiểu lề: `.mobile-container`, `.buy-main` (16px, 12px ở ≤360px, có safe-area), `.hr-mobile-main` (14px, không safe-area).
19. Nhân sự có 5 tab, ba app kia 4; `docs/MOBILE_UI_STANDARD.md:8` ghi "bốn tab".
20. Trạng thái trống: Kho, Mua hàng, Nhân sự dùng `p.mobile-empty` (12 chỗ); `/work` dùng `.lotus-form-note` không có CSS; hộp thông báo dùng `Empty` của Vant. `docs/MOBILE_UI_STANDARD.md:14` ghi cả bốn PWA dùng `mobile-empty`.
21. Màu icon ô thao tác đặt theo vị trí `nth-child(2…5)` (`mobile-ui.css:63-66`) trong khi các ô có `v-if` theo quyền (`WarehouseMobile.vue:572-577`), nên cùng một thao tác đổi màu tuỳ tài khoản.
22. Tên của Kho nằm trong mã dùng chung: biến `--warehouse-visible-height` (`use-mobile-viewport.js:14`), sự kiện `warehouse-picker-open` và `warehouse-dismiss-picker` (`use-mobile-popup.js:36,42-43`), hàm `foldVietnamese` trong `warehouse-mobile-helpers.js`, prop `app` mặc định `'warehouse'` (`LotusMobileShell.vue:10`).
23. Hai luật so khớp khi tìm: `MobileLinkField.vue:25` bỏ dấu, khoảng trắng và gạch nối (`option-search.js`); `MobileLiveSearch.vue:20-21` chỉ bỏ dấu.
24. Lặp logic: theo dõi `online` viết 3 lần (`WarehouseMobile.vue:214,534`, `BuyingMobile.vue:119,296`, `LotusMobileAiChat.vue:44,53`); đăng ký push viết 2 lần (`LotusMobileNotifications.vue:13-59` và `mobile-push-subscription.js:3-33`); markup hộp xác nhận lặp 7 lần.
25. Tài liệu lệch mã: `docs/MOBILE_UI_AUDIT_20261017.md:19` ghi Công việc giữ "hàng chờ offline, đồng bộ" nhưng `WorkMobile.vue` không import `offline.js`.

### D. Đọc ngoài nắng

26. Tương phản chữ dưới 4.5:1: `--lotus-subtle` (neutral-500) trên nền trắng 3.96:1, dùng cho placeholder và icon tab chưa chọn (`mobile-ui-theme.js:3`), dòng phụ của thẻ Mua hàng (`buying-mobile.css:19,68,70`), dòng phụ của gợi ý (`mobile-ui.css:141`); `.mobile-status` (primary-500 trên primary-50) 3.84:1 và `.mobile-status.posted` (success-600 trên neutral-100) 4.13:1 ở cỡ 12px (`warehouse-mobile.css:154-155`); `.buy-order-status--closed` 4.42:1 (`buying-mobile.css:67`); `--lotus-warning` làm màu chữ 4.40:1 (`LotEntryModal.vue:205,214`, `RibbonBoard.vue:103`, `CrewStatus.vue:51`); icon ô thao tác thứ 5 (warning-500 trên warning-50) 2.90:1 (`mobile-ui.css:66`).
27. Chữ phụ đạt AA nhưng thấp cho ngoài trời: `--lotus-muted` 5.36:1 trên trắng, 5.01:1 trên nền trang; chữ trắng trên header đỏ 5.48:1. Phần lớn chữ phụ trên thẻ lô, thẻ việc là 12px.
28. Viền và ranh giới gần như không thấy: `--lotus-border` trên trắng 1.26:1, `--lotus-border-strong` 1.49:1, `--lotus-primary-200` 1.48:1, thẻ trắng trên nền trang 1.07:1. Ngưỡng cho ranh giới control là 3:1.
29. Vòng focus `--lotus-pwa-focus` (primary-300) trên trắng 2.01:1 (`mobile-ui.css:172,177`).
30. Tab đang chọn chỉ khác ở màu icon và nền 1.07:1 (`mobile-ui.css:24`); không có nhãn chữ.
31. Giao diện tối bật theo máy, không tắt được, và CSS dùng ramp cố định 241 lần nên không đổi theo `.dark`: `.mobile-summary b` (success-900) trên nền tối 1.02:1 (`warehouse-mobile.css:54`, dùng ở `WarehouseMobile.vue:608,623,632,682`); chữ `--lotus-primary-600` trên nền tối 2.78:1; `LotusMobileFeedback.vue:5` dùng `warning-700`, `success-700`, `info-700` trên nền soft tối cho 2.13:1, 2.03:1, 1.66:1. Khung logo trên header lấy nền `--lotus-surface` nên thành tối (`mobile-ui.css:17`). Chưa kiểm trên máy.

### E. Găng tay, ngón cái, một tay

32. Vùng chạm dưới 44px ở màn hiện trường: 38 `UiButton` cao 36px, 16 cái cao 32px với chữ 12px, gồm nút bật Sáng/Chiều cho từng người (`LotEntryModal.vue:178-180`), nút thêm việc nhanh (dòng 121), "Bỏ việc này" (dòng 129), "Chọn cả khu" (`CareDueList.vue:106-107`, `WorkAssign.vue:101`), "Kiểm lô này" (`PaperPhotoReview.vue:63`), "Gửi báo cáo", "Xác nhận", "Mở lại" (`LotToday.vue:115-117`), "Hủy" và "Lưu" ở chân hộp thoại (`form/ModalForm.vue:20-22`). Khoảng cách giữa các nút 6px (`LotEntryModal.vue:206,217,219`).
33. Hộp kiểm chọn lô: icon 20px, dòng nhãn cao khoảng 24px, không có đệm chạm (`LotusMobileCheck.vue:6`, `mobile-work-legacy.css:57-58`); dùng ở `CareDueList.vue:110`, `WorkAssign.vue:104`, `WarehouseMobile.vue:611,634`.
34. Vùng chạm dưới 44px khác: bộ lọc `.pp-scopes button` 36px và "Bỏ dòng" 32px (`purchase-proposal-mobile.css:4,17`), nút trong trình cắt ảnh chữ ký 42px (`components/lotus-signature-editor.css:5`), nút xoá tệp `size="sm"` (`components/stock/StockEvidence.vue`).
35. Nút lưu nằm cuối nội dung cuộn, không dính đáy, ở Kho, Mua hàng, Nhân sự (`WarehouseMobile.vue:602`, `MobilePurchaseOrderForm.vue:62`, `HrMobile.vue:270`). Nội dung nằm trong `.van-pull-refresh{overflow:hidden}` nên `position:sticky` bên trong không bám theo màn hình.
36. Nút AI nổi 88×52px đặt ở `bottom:calc(76px + safe-area)` (`LotusMobileAiChat.vue:158`), đúng bằng đệm đáy của shell (`mobile-ui.css:8`), nên che góc phải của phần tử cuối trang ở mọi màn.
37. Nút back ở góc trên trái. Chỉ Kho và Mua hàng xử lý nút back của hệ thống (`popstate`); `WorkMobile.vue` và `HrMobile.vue` không có `popstate`, `pushState` hay `beforeunload`. `HrMobile.vue:54` chuyển màn mà không hỏi khi form hồ sơ đang nhập dở.
38. Vuốt đổi tab chỉ có ở Kho (`WarehouseMobile.vue:126`).
39. Trên "Hôm nay" của `/work`, trước thẻ lô đầu tiên là các ô Vườn, Đội, Ngày, Tổ xếp dọc, thanh trạng thái và khối phiếu giấy (`WorkMobile.vue:83-89`, `LotToday.vue:97-126`). Ước tính từ CSS: 380px đến 640px tính từ đỉnh màn hình. Chưa đo trên máy.

### F. Tốc độ nhập liệu

40. Ô số trên điện thoại là `<input type="number">` native (`form/LotusField.vue:42`, `LotusMobileInput.vue:20`). Chính `LotusField.vue:38` ghi input number từ chối dấu phẩy ở nhiều trình duyệt; máy tính đã đổi sang `MoneyInput`, điện thoại chưa.
41. 6 trong 14 ô số tìm thấy không có `inputmode`: `MobilePurchaseProposal.vue:144`, `LotToday.vue:133-135`, `WorkTicket.vue:91-92`.
42. Không có stepper cộng trừ; số buồng, số cây, số lượng đều gõ bằng bàn phím.
43. Lựa chọn hai giá trị dùng select native: "Sáng" và "Chiều" có mặt hay vắng, phụ cấp có hay không (`components/hr/HrMobileAttendance.vue:101-103`).
44. Chuyển ngày bằng nút trước, sau chỉ có ở chấm công Nhân sự (`HrMobileAttendance.vue:71`); "Hôm nay" của `/work` chỉ có ô ngày native.
45. Danh sách dài phân trang bằng nút "← Trước", "Sau →", 50 dòng mỗi trang (`WarehouseMobile.vue:619,675,715,727`); không có cuộn tải thêm.
46. `MobileLinkField` thiếu `hint`, `error`, nút xoá, tìm trên máy chủ và trạng thái đang tải; `LotusField` vẫn truyền `hint`, `error` vào nó (`form/LotusField.vue:50`).

### G. Màn 320px

47. `warehouse-mobile.css:261` đổi `.mobile-qty-grid` thành một cột ở ≤360px, nhưng `mobile-ui.css:57,98` ép lại hai cột với độ ưu tiên cao hơn; mỗi cột còn khoảng 128px cho ô số lượng và ô đơn vị.
48. Ô lọc trạng thái đơn mua rộng 98px ở ≤360px (`mobile-ui.css:190`, `BuyingMobile.vue:340`); trừ đệm và mũi tên còn khoảng 48px cho chữ như "Về một phần".
49. `.pp-pair{grid-template-columns:1fr 1fr}` không có `minmax(0,1fr)` (`purchase-proposal-mobile.css:15`); nhãn "Đơn giá dự kiến (đồng)" xuống hai dòng làm hai ô lệch hàng.
50. Tràn ngang ở 320px của bốn app chưa kiểm trên máy; `body{overflow-x:hidden}` (`warehouse-mobile.css:3`, `mobile-work-legacy.css:6`) che lỗi tràn nếu có.

### H. Offline, cập nhật, phản hồi

51. `/work` và `/hr-mobile` không có băng báo mất mạng (xem mục 14).
52. `/work` không có hàng chờ ghi và không có cache đọc. Khi ghi lỗi, `api.js:13` trả câu "Chưa gửi được. Giữ bản ghi trong hàng chờ rồi thử lại khi có mạng." và `lotus_farm/public/work-offline.html` cũng nhắc "hàng chờ trên máy", trong khi app không có hàng chờ.
53. Trang offline tĩnh dùng màu ngoài token và mỗi trang một kiểu: nút `#173e2e` (`warehouse-offline.html`), link `#14663b` (`work-offline.html`), nút `#e65338` (`hr-mobile-offline.html`), không kiểu (`buying-offline.html`).
54. Ba app không báo khi có bản mới; worker gọi `skipWaiting()` nên trang đang mở vẫn chạy mã cũ cho tới khi tải lại.
55. Không có toast. Thông báo thành công là `NoticeBar` ở đầu trang; người dùng đang cuộn ở dưới không thấy. Kho chỉ cuộn tới lỗi (`WarehouseMobile.vue:101`). `WorkMobile.vue:70` tìm `.lotus-mobile-feedback`, class không tồn tại (class thật là `lotus-pwa-feedback`), nên lỗi ở `/work` không được cuộn tới.
56. `LotusMobileFeedback` không có icon, nút đóng hay nút hành động; không có skeleton; đang tải chỉ là một vòng xoay 18px kèm chữ.

### I. Icon và ngữ nghĩa

57. Ký tự làm icon: `→` 8 lần và `←` 5 lần trong nhãn nút của `WarehouseMobile.vue`, `＋` 3 lần, `✓` làm biểu tượng hoàn tất (dòng 751), emoji `👤` làm avatar (`WarehouseMobile.vue:734`, `WorkMobile.vue:106`), `×` (`MobileLiveSearch.vue:64`), `‹ ›` (`HrMobileAttendance.vue:71`), `▲ ▼ ✓` (`LotEntryModal.vue:165,167`), `content:'⌄'` (`warehouse-mobile.css:238`). `design-tokens.test.js:89` chỉ cấm một nhóm ký tự khác.
58. Hai hệ icon trong cùng app: font icon Vant ở wrapper và `LotusIcon` SVG ở primitive máy tính (42 thẻ `LotusIcon` trong chuỗi import của `/work`).
59. Thẻ bấm được là Vant Button bọc `<strong>`, `<small>`, `<div>` (`WarehouseMobile.vue:617,669`, `BuyingOrderCard.vue:13-23`, `MobilePurchaseProposal.vue:118-123`); `<div>` nằm trong `<button>`.
60. Trang không có `h1`: tiêu đề header là `<strong>` (`LotusMobileHeader.vue:13`) và `mobile-ui.css:28` đặt `display:none` cho `h1` trong khung nội dung, kể cả `h1` ở `WorkMobile.vue:105`.
61. Điều hướng dưới không hiện nhãn và không có badge; `LotusMobileBottomNav` không mở prop `badge` hay `dot` của `TabbarItem`.
62. `role="tablist"` viết tay không xử lý phím mũi tên (`MobilePurchaseProposal.vue:114`, `HrMobileAttendance.vue:96`).
63. Style inline cho ảnh QR (`BuyingMobile.vue:426`). Class không có định nghĩa: `buy-request-print`, `buy-order-actions` (`BuyingMobile.vue:362,395`), `mobile-evidence` (`WarehouseMobile.vue:610`), `lotus-mobile-check-field` (`form/LotusField.vue:48`).

### J. Trọng lượng

64. `/work` tải 2,13 MB JS chưa nén, trong đó 959 KB là AG Grid và 491 KB là từ điển dịch của ERPNext; `/buying` tải 2,41 MB vì nhúng `ProcurementWorkspace` của máy tính (`BuyingMobile.vue:3,419`).
65. Cả bốn app tải toàn bộ CSS Vant (232 KB cùng `mobile-ui.css`) cho 18 component.
66. Logo header là PNG 103 KB cho khung 106×38px.

### K. Thiếu nơi xem và thử

67. `components/UiShowcase.vue` không có component điện thoại nào (0 tham chiếu tới `LotusMobile`, `Mobile`, `vant`).

## Thiếu so với một bộ giao diện đầy đủ

| Thành phần | Đang có | Còn thiếu |
|---|---|---|
| Ô danh sách (list cell) | `Cell` của Vant ở 4 file; còn lại tự viết (`hr-mobile-row`, `hr-att__row`, `mobile-profile-row`, `buy-request-line`) | Một cell chung: tiêu đề, dòng phụ, giá trị, phần đuôi, mũi tên, badge, viền trạng thái, nhóm có tiêu đề |
| Thẻ | 14 họ class | Một thẻ chung (đầu, thân, chân, tông màu, bấm được với ngữ nghĩa đúng) và hai biến thể chuẩn: thẻ lô, thẻ việc |
| Ô số liệu | 6 kiểu | Một ô chung: số lớn, nhãn, đơn vị, tông màu, bấm để lọc |
| Chip, nhãn trạng thái | 4 họ class | Chip trạng thái theo token, chip lọc chọn nhiều, chấm màu dây chuẩn |
| Stepper | không có | Ô số lượng có nút cộng trừ, hậu tố đơn vị, bàn phím số, nhận dấu phẩy |
| Segmented control | 4 kiểu viết tay | Một component có `role="tablist"` và điều khiển bàn phím |
| Công tắc | không có | Switch cho lựa chọn hai giá trị |
| Action sheet, bottom sheet | Popup đáy tự dựng ở 5 chỗ; Dialog giữa màn dùng làm "sheet" ở chấm công | Sheet chung: tay nắm, tiêu đề, nút đóng, vùng cuộn, chân dính, safe-area; action sheet cho menu thao tác |
| Kéo để tải lại | có trong `LotusMobileShell` | Chỉ báo "cập nhật lúc…" |
| Danh sách tải thêm | nút Trước, Sau | Cuộn tải thêm hoặc nút "Tải thêm" |
| Skeleton | không có trên điện thoại | Skeleton cho thẻ, cell, ô số liệu |
| Trạng thái trống | `p.mobile-empty` chỉ có chữ | Icon, câu ngắn, nút hành động |
| Nút nổi | chỉ nút AI | FAB cho hành động chính và quy tắc xếp với tabbar, nút AI |
| Tab trong trang | không có | Tabs cuộn ngang có badge |
| Toast | không có | Toast thành công, lỗi, có nút hoàn tác |
| Banner | `LotusMobileFeedback` trong trang | Banner cố định dưới header cho mất mạng, đang đồng bộ, có bản mới; có icon, nút đóng, nút hành động |
| Thanh hành động dính đáy | không có | Thanh chứa nút lưu, tổng tiền, nằm trên tabbar và trên bàn phím |
| Ô tìm | `MobileLiveSearch` | Trạng thái tải, nút xoá bằng icon, nút quét mã |
| Chọn liên kết | `MobileLinkField` | Chạy được trong dialog, tìm trên máy chủ, `hint`, `error`, xoá, tạo mới |
| Chọn ngày | input native | Thanh chuyển ngày (trước, hôm nay, sau), chọn tuần ISO |
| Ảnh, tệp | `LotusMobileFile` trần; `FilePickerButton` của máy tính | Uploader có chụp ảnh, xem trước, nén, tiến độ, thử lại |
| Avatar | emoji | Avatar chữ cái hoặc ảnh |
| Tiến độ, các bước | `LotusSignatureTimeline`, `PurchaseProgress` riêng lẻ | Thanh tiến độ và danh sách bước chung |
| Tiêu đề nhóm, đường kẻ, nhóm gập | `h2` trần | Section header, divider, collapse |
| Hộp xác nhận | markup lặp 7 lần | Một component xác nhận nhận tiêu đề, nội dung, nhãn nút, tông màu |
| Icon | font Vant + `LotusIcon` + ký tự | Một bộ icon cho cả điện thoại |
| Token điện thoại | `--lotus-touch`, alias `--lotus-pwa-*` | Thang chữ, cỡ control, khoảng cách chạm, z-index, màu "ngoài nắng" |
| Phản hồi rung | không có | Rung ngắn khi lưu xong hoặc lỗi (tuỳ chọn) |
| Nơi xem trước | không có | Trang showcase điện thoại ở khung 320px và 390px |
| Test mount | 3 file (`mobile-ai-chat`, `hr-mobile-attendance`, `purchase-proposal`) | Test mount cho từng wrapper: hành vi, `aria`, vùng chạm |

## Đề xuất cho bộ giao diện mới

### P0. Nền móng

1. Thêm tầng token điện thoại vào `lotus-tokens.css`: thang chữ (phụ tối thiểu 13px, nội dung 15–16px, control 16px, số liệu 20–32px), cỡ chạm 48px và 56px cho hành động chính, khoảng cách giữa hai vùng chạm tối thiểu 8px, ba bậc bo góc, thang z-index (header, tabbar, nút nổi, popup, toast). Xoá alias `--lotus-pwa-*`.
2. Thêm nhóm màu cho ngoài nắng, vẫn lấy từ ramp hiện có: chữ phụ dùng neutral-700 (8.11:1 trên trắng) thay neutral-600 và neutral-500; chữ trạng thái dùng bậc 700 hoặc 800 trên nền 50 (5.96:1 đến 8.63:1); viền control dùng neutral-500 (3.96:1); vòng focus dùng primary-600. Header giữ `#c43224` theo `AGENTS.md:34`, tiêu đề tối thiểu 16px/700.
3. Mọi màu trong CSS điện thoại đi qua token ngữ nghĩa, bỏ 241 lần gọi ramp trực tiếp. Mặc định giao diện sáng; chế độ tối là lựa chọn trong tab Tôi (cần chủ vườn duyệt vì hiện đang tự theo máy).
4. Ánh xạ đầy đủ Vant trong `mobile-ui-theme.js`: thang chữ, bo góc, padding, cell, nút small, hộp kiểm 24px, field, notice bar, overlay, thời lượng. Không để cỡ mặc định 12px và 14px của Vant lọt ra màn hình.
5. Viết lại `mobile-ui.css` thành file bộ thuần: không chứa selector của app, không khoá trong `.lotus-pwa-shell` với các bề mặt teleport (đặt class gốc lên `<html>`). Dùng `@layer vant, tokens, kit, app` để thứ tự không phụ thuộc cách Vite tách chunk, đồng thời sửa `lotus_farm/www/*.py` cho khớp. Thêm test đọc `manifest.json` để kiểm thứ tự.
6. Xoá legacy trong cùng đợt: bỏ `mobile-work-legacy.css` và `field-todo.css`; rút `warehouse-mobile.css`, `work-mobile.css`, `buying-mobile.css` về phần riêng của app; bỏ quy tắc trên thẻ trần. Sửa các test đang ghim chuỗi cũ (`warehouse-mobile-standalone.test.js:30-31`, `mobile-shared-plan.test.js:46-55`).

### P1. Component

7. `LotusMobileButton` có prop rõ ràng: `variant` (primary, secondary, outline, danger, ghost), `size` (48px, 56px), `block`, `icon`, `loading`. Thay các class `mobile-submit`, `mobile-add`, `buy-primary`, `buy-outline`, `buy-danger` và 43 thẻ không kiểu.
8. Bộ wrapper mới, mỗi cái một file `components/LotusMobile*.vue`, có test mount và có mặt trong showcase: `Card`, `Cell` và `CellGroup`, `Stat`, `Chip`, `Segmented`, `Stepper` (ô số lượng có đơn vị, nhận dấu phẩy), `Switch`, `Sheet` (bottom sheet và action sheet), `Toast`, `Banner`, `Empty`, `Skeleton`, `Fab`, `Tabs`, `ActionBar`, `DateBar`, `Uploader`, `Avatar`, `Confirm`.
9. `MobileLinkField`: dùng `useDialogPortal` của `components/ui/portal-target.js`, hoặc mở danh sách bằng `Sheet` toàn màn hình có ô tìm; thêm `fetchOptions`, `hint`, `error`, nút xoá; gộp luật so khớp với `MobileLiveSearch`. Sau đó `form/LotusField.vue:50` bỏ nhánh rơi về Combobox máy tính.
10. `LotusMobileInput`: ô số dùng `type="text"` với `inputmode="decimal"` hoặc `numeric` và bộ đọc số như `type="money"`; thêm hậu tố đơn vị, nút xoá, `readonly`.
11. `/work`: thẻ lô và thẻ việc theo `Card` chung (tên lô 17–18px, trạng thái bằng chip có chữ, màu dây bằng chấm 16px kèm tên màu, số còn lại 20px trở lên, cao tối thiểu 72px). Hộp nhập lô thành `Sheet` toàn màn hình với `ActionBar` 56px dính đáy; nút Sáng/Chiều theo `Segmented` 48px; chọn lô bằng cell có hộp kiểm 24px và vùng chạm cả dòng. Giữ luồng "mỗi lô một thẻ, bấm để mở hộp nhập" (`docs/FIELD_REPORT.md:12`) và các class mà test mount đang dùng, hoặc sửa test cùng lúc.
12. Bỏ `DataTable` khỏi chuỗi import của `/work` (`RibbonBoard.vue:83-89`, `CareDueList.vue:120-123`, `WorkAssign.vue:74`) bằng import động chỉ khi không phải `mobile`, và thay bằng danh sách cell. Tách `system-translations.js` khỏi chunk dùng chung của điện thoại.
13. Shell: băng mất mạng và băng có bản mới đặt trong `LotusMobileShell` cho cả bốn app, dùng một composable `useOnline`; một composable lịch sử màn hình (popstate, xác nhận rời form) dùng chung, áp cho Nhân sự và Công việc; thêm `badge` cho tab; dời nút AI lên header hoặc đặt nó phía trên `ActionBar` để không che nội dung.
14. Nhãn chữ dưới icon tab (11–12px, đậm khi chọn) và vạch chỉ tab đang chọn. Việc này đổi `AGENTS.md:28` ("biểu tượng gọn"), cần chủ vườn duyệt; nếu không duyệt thì giữ icon và tăng tương phản tab đang chọn bằng vạch màu `--lotus-primary`.
15. Một bộ icon cho điện thoại (ưu tiên `LotusIcon` SVG để bỏ font icon Vant 259 glyph); thay toàn bộ ký tự và emoji ở mục I.57; mở rộng `design-tokens.test.js:85-92` để cấm `→ ← ＋ ✓ × ▲ ▼ ‹ ›` làm icon.

### P2. Bảo vệ và tài liệu

16. Trang showcase điện thoại trong `showcase.html` (khung 320px và 390px, sáng và tối) liệt kê mọi wrapper và các mẫu thẻ lô, thẻ việc.
17. Test tĩnh mới: chuỗi import của bốn entry điện thoại không chứa `ui/button`, `DataTable`, `ui/combobox`; không có `font-size` dưới 13px trong CSS điện thoại; mọi class dùng trong template điện thoại phải có định nghĩa trong CSS mà entry đó nạp; quét hex ở mọi thư mục con của `src`.
18. Giảm trọng lượng: import CSS Vant theo component; logo header dạng SVG hoặc PNG đúng cỡ; thêm ngưỡng kích thước chunk cho bốn entry trong CI.
19. Offline cho `/work` là quyết định nghiệp vụ cần chủ vườn chốt (hàng chờ ghi, cache đọc). Bộ giao diện chỉ chuẩn bị phần hiển thị: `Banner` trạng thái, số bản ghi chờ gửi, nút thử lại. Trước mắt sửa câu ở `api.js:13` và `work-offline.html` cho đúng thực tế, và viết lại bốn trang offline theo token.
20. Cập nhật `docs/MOBILE_UI_STANDARD.md` theo bộ mới: thứ tự CSS thật, số tab, trạng thái trống, quy tắc vùng chạm và cỡ chữ tối thiểu.
