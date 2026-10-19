# Đánh giá độ hiện đại, trải nghiệm người dùng và bộ component dùng chung — Lotus (19/10/2026)

Phạm vi: khung máy tính `/lotus/*` và bốn PWA (`/warehouse`, `/buying`, `/work`, `/hr-mobile`) sau đợt đồng bộ giao diện (`UI_AUDIT_FULL_20261019.md`). Đợt trước giải quyết **nhất quán**; báo cáo này đánh giá **mức hiện đại và trải nghiệm**, so với chuẩn của các ứng dụng nghiệp vụ hiện nay (Linear, Stripe Dashboard, Notion, ERPNext v16 Desk).

Hướng chuẩn hóa đã chọn: **shadcn-vue trên reka-ui** cho máy tính (đã cài, không thêm phụ thuộc), **Vant 4** cho PWA.

## Chấm điểm (1 = lạc hậu, 5 = ngang chuẩn hiện đại)

| Mảng | Điểm | Nhận định ngắn |
|---|---|---|
| Hệ thị giác (màu, chữ, token) | 4 | Sau đợt đồng bộ: một nguồn token, Đỏ Lotus, Inter, sáng/tối. Còn icon PWA tông cam, `/login` Frappe gốc. |
| Bộ component dùng chung | 2 | Chỉ Button đạt chuẩn; thiếu Toast, Menu, Popover, Tooltip, DatePicker, Sheet, Pagination; 4 bản combobox tự viết. |
| Phản hồi & trạng thái tải | 2 | Chỉ chữ “Đang tải…”, không skeleton; thông báo là đoạn văn đứng yên, không toast, không hoàn tác. |
| Biểu mẫu | 2,5 | Mobile tốt (label/hint/lỗi). Desktop chỉ có `required` native, lỗi gom một dòng, không chặn rời form, 48 ô ngày native. |
| Bảng dữ liệu | 3 | AG Grid + lọc kiểu Excel tốt; không nhớ cột/lọc, phân trang tự viết, không thao tác hàng loạt, xuất dữ liệu rời rạc. |
| Điều hướng & tìm kiếm | 3 | Ctrl‑K có ARIA tốt nhưng chỉ tìm màn hình; phạm vi lọc giữ trong URL; không breadcrumb, không saved views. |
| PWA điện thoại | 4 | Shell chung, onboarding cài đặt, push, vuốt tab, safe‑area, vùng chạm 44px. Thiếu dark mode, kéo để làm mới. |
| Hiệu năng | 2 | JS chính 1,47 MB (AG Grid nạp toàn bộ module), CSS 881 KB (kéo cả `frappe-ui/style.css` dù không dùng component). |
| Khả năng tiếp cận | 3 | `lang=vi`, focus-visible, reduced-motion, role alert/status. Thiếu skip link, tab chưa đúng `tablist`, tooltip chỉ `title`. |
| Khả năng bảo trì | 1,5 | Không TypeScript, không tài liệu component, 0 test mount; template một dòng tới 6.661 ký tự; `App.vue` 73 KB. |
| **Trung bình** | **2,7** | Nền móng thống nhất đã có; khoảng cách lớn nhất ở bộ component, phản hồi, hiệu năng, bảo trì. |

## Phát hiện chính

### 1. Bộ component dùng chung
- `components/ui/`: Button (reka `Primitive`, loading + `aria-busy`) dùng 283 lần — tốt. Input/Textarea không có label/lỗi; Select là `<select>` native; Card, Badge mỗi thứ 1 nơi dùng; Skeleton, Separator 0 nơi dùng.
- reka-ui 2.11 chỉ dùng `Primitive`; frappe-ui chỉ dùng `FrappeUIProvider` nhưng kéo 881 KB CSS.
- Trùng lặp: 4 combobox (`SearchSelect`, `LinkPicker`, `MobileLinkField`, `MobileLiveSearch`), 5 popover tự định vị, `DataTable` ≈ `OpsList`, `use-mobile-confirm` ≈ `use-workspace-confirm`, 20 `<dialog>` thô ngoài `WorkspaceModal`, 9 menu bằng `<details>`.
- `WorkspaceTabs` dùng `nav`+`aria-current` thay vì `tablist/tab`. `SchemaForm` sửa trực tiếp `props.model`.
- Thành phần tốt nên giữ làm chuẩn: `LotusMobileInput/Select` (label/hint/lỗi, `useId`), palette Ctrl‑K trong `WorkspaceBar`, `WorkspaceModal` (dialog native, KeepAlive), `DesktopEmptyState` (slot actions).

### 2. Trải nghiệm
- **Tải**: `WorkspaceLoading.vue` là khối tĩnh; bảng chỉ hiện “Đang tải…”. Không skeleton, không cập nhật lạc quan.
- **Phản hồi**: `<p class="notice">` đứng yên tới lần thao tác sau; không toast tự đóng, không “Hoàn tác”.
- **Biểu mẫu desktop**: lỗi server hiện một dòng đầu form, người dùng phải tự tìm trường sai; đóng/chuyển màn khi đang nhập không cảnh báo (PWA thì có).
- **Bảng**: chỉnh độ rộng/sắp xếp mất khi tải lại; lọc cột không nằm trong URL nên không chia sẻ được; phân trang “Trước/Tiếp” 50 dòng.
- **Trạng thái trống**: “Chưa có dữ liệu.” không gợi ý bước tiếp theo.
- **Ngày**: hiển thị bằng cắt chuỗi ISO (`month.slice(5)`), ô ngày theo locale trình duyệt (`mm/dd/yyyy` trên máy tiếng Anh).

### 3. Hiệu năng (bản build hiện tại)
| Tệp | Kích thước | Nguyên nhân |
|---|---|---|
| `index-*.js` | 1.472 KB | `AllCommunityModule` của AG Grid đăng ký ở 3 component; `DataTable` nạp thẳng trong `App.vue` |
| `index-*.css` | 881 KB | `@import 'frappe-ui/style.css'` + preset Tailwind quét mã frappe-ui |
| `DesktopForecastChart-*.js` | 572 KB | Lõi ECharts (đã tải trễ, chấp nhận được) |

## Lộ trình nâng cấp

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| B — Quick wins | AG Grid chỉ nạp module cần (`grid-modules.js`) + tải trễ bảng; bỏ CSS frappe-ui; Toast + Hoàn tác (`use-toast.js`, reka Toast, F8 để tới thông báo); Skeleton cho bảng và màn đang mở; trạng thái trống có hành động + nút “Xóa bộ lọc” khi lọc cột ẩn hết dòng; `FormField` desktop, SchemaForm viết lại nhiều dòng; bảng nhớ độ rộng cột; skip link, `WorkspaceTabs` đúng tablist; `format.js` thay 3 bản định dạng ngày | Xong |
| C — Component v2 | DropdownMenu (menu phân hệ, tài khoản), Tooltip, Popover, Combobox gộp (SearchSelect + LinkPicker thành lớp bọc), DatePicker/DateRangePicker `vi-VN` có khoảng nhanh (thanh lọc khung `/lotus`), Sheet, Pagination (2 nơi trong App), OpsList thành lớp bọc DataTable, lõi confirm chung, danh mục component `showcase.html` | Xong (xem ghi chú) |
| D — UX nâng cao | Ctrl‑K tìm bản ghi, saved views, thao tác hàng loạt, chặn rời form desktop, PWA dark mode, kéo để làm mới, tự lưu nháp | Đề xuất |
| E — Dài hạn | Tách `App.vue` theo route, TypeScript cho `components/ui`, test mount, theme `/login` & Desk | Cần duyệt riêng |

## Kết quả giai đoạn B

| Chỉ số | Trước | Sau |
|---|---|---|
| JS chính desktop (`index-*.js`) | 1.472 KB | 193 KB |
| CSS desktop (`index-*.css`) | 881 KB | 211 KB |
| AG Grid | trong JS chính | chunk riêng 725 KB, chỉ tải khi mở bảng |

- Ảnh so sánh pixel bản build (Hôm nay, Nhân sự, Cấu hình kế hoạch, Vườn @1440/1024 sáng/tối, Công việc PWA): 0,000% khác biệt sau khi bỏ CSS frappe-ui. Không có lỗi AG Grid thiếu module.
- Luồng Chức danh → xác nhận → toast chạy đúng; F8 đưa focus tới vùng thông báo.
- Phát hiện kèm: khi lọc cột ẩn toàn bộ dòng, bảng biến mất cùng tiêu đề lọc nên người dùng không bỏ lọc được — nay có nút “Xóa bộ lọc”.
- `npm test` 249/249; DOM 24/24.
- Chưa làm: đưa bộ lọc cột Kho vào URL (để giai đoạn D cùng saved views).

## Kết quả giai đoạn C

- Primitive mới trong `components/ui/`: dropdown-menu, tooltip, popover, combobox, date-picker (DatePicker, DateRangePicker), sheet, pagination, form-field, toast. Không thêm thư viện: chỉ khai báo trực tiếp `@internationalized/date` (đã có sẵn qua reka-ui, cùng phiên bản 3.12.4).
- Combobox: tìm không dấu, bỏ qua khoảng trắng/gạch (`option-search.js`), nhóm + mô tả, tải từ máy chủ, giữ chữ gõ cho trường Link; danh sách render trong hộp thoại đang mở nên chọn được trong form Kho.
- DatePicker gõ được từng phần dd/mm/yyyy hoặc chọn lịch (thứ Hai đầu tuần, “Hôm nay”, “Xóa”); DateRangePicker 2 tháng + khoảng nhanh thay hai ô “Từ ngày/Đến ngày”. Khoảng ngày chỉ áp dụng khi chọn đủ hai đầu (trước đây có thể để trống một đầu).
- Thanh trên: menu phân hệ và tài khoản bằng DropdownMenu (phím mũi tên, Esc trả focus), tooltip cho nút icon, icon thay ký tự ☰ ⌂ ⌄. Sửa kèm: quy tắc CSS `button[aria-expanded]` cũ làm co nút menu và sẽ ẩn menu phân hệ trên điện thoại.
- Kiểm tra: `npm test` 251/251 (thêm test toast, định dạng ngày, độ rộng cột, tìm không dấu, lõi confirm, vuốt tab); DOM 24/24; luồng thật trên showcase: tìm “binh duong”, tải “bao”, chọn trong hộp thoại, khoảng “Tháng này”, không lỗi console.

- Kích thước sau GĐ C: JS chính 384 KB (DatePicker/Combobox nằm trên thanh lọc nên nạp ngay; vẫn giảm 74% so với 1.472 KB ban đầu), CSS 223 KB.

Ghi chú lệch kế hoạch:
- Trang tài liệu là `frontend/showcase.html` chạy bằng `npm run dev` thay cho route `/lotus/admin/ui`: không thêm mục vào menu/phân quyền, không phát hành ra production.
- 20 `<dialog>` thô chưa chuyển cấu trúc sang WorkspaceModal (giao diện đã thống nhất bằng CSS ở đợt trước); chuyển dần khi sửa từng màn vì các form này gọi `showModal()` trực tiếp và nằm trong tệp lớn.
- MobileLinkField (PWA) giữ cách lọc hiện tại; `option-search.js` mới áp dụng cho desktop.

## Phát hiện thêm (chưa xử lý)
- Ở bề rộng ≤ 900px, khung `/lotus` dùng thanh trên màu xám đậm thay vì Đỏ Lotus và nhãn thanh điều hướng dưới bị cắt (“Trang…”, “Xem…”).
- Ở 1024px, tên phân hệ trên thanh trên bị ẩn và thanh lọc phải cuộn ngang.
