# Implementation Plan: Đúc lại bộ giao diện Lotus đạt chuẩn phần mềm nông nghiệp

**Branch**: `004-bo-giao-dien-agritech` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-bo-giao-dien-agritech/spec.md`

## Summary

Một bộ giao diện duy nhất, hướng "Đất và lá" ([research.md](research.md) R1), dựng trên bốn lớp:

- **Nền**: `lotus-tokens.css` ba tầng, ba chế độ (sáng, tối, ngoài trời), hai mật độ; `ui-mode.js` đặt chế độ và mật độ cho cả máy tính và điện thoại.
- **Bộ thành phần**: `lotus-kit.css` cùng 12 component mới trong `components/ui/` (chip trạng thái, thông báo trong trang, ô số liệu, tiến độ, công tắc, chọn theo đoạn, ô số cộng trừ, chữ cái đại diện, các bước duyệt, dòng thời gian, danh sách chi tiết) và nút có biến thể nguy hiểm tách khỏi nút chính.
- **Bảng**: theme từ token, biến thể Kho, các kiểu cột dựng sẵn trong `grid-columns.js`.
- **Bộ nông nghiệp**: 17 component trong `components/agri/` (thẻ lô, lưới lô, màu dây, tuần, đến hạn, cách ly, biểu đồ dự thu, tuổi buồng, bản đồ, ca xưởng, tổ…).

Kèm trang mẫu sáu phần và các kiểm tra tự động giữ chuẩn. Không đổi nghiệp vụ, số liệu, quyền hay trạng thái chứng từ.

## Technical Context

**Language/Version**: JavaScript ES2022, Vue 3.5 (SFC, `<script setup>`), CSS (custom properties, không preprocessor)

**Primary Dependencies**:
- Máy tính: shadcn-vue trên reka-ui 2.11, Tailwind 3.4.
- Điện thoại: Vant 4.10.
- Bảng: AG Grid Community 36.2.
- ECharts 6 cho các biểu đồ có sẵn.
- Không thêm thư viện.

**Storage**: `localStorage` cho lựa chọn hiển thị (`lotus-theme`, `lotus-desktop-density`, `lotus-outdoor`); không đổi cơ sở dữ liệu

**Testing**: `node --test` với happy-dom (`tests/support/mount.mjs`). Kiểm tra tương phản đọc thẳng `lotus-tokens.css` (`tests/support/css-tokens.mjs`). Chạy trên VPS ở `/opt/lotus-004-test`.

**Target Platform**:
- Máy tính `/lotus`.
- Bốn ứng dụng điện thoại `/warehouse`, `/buying`, `/work`, `/hr-mobile`.
- Trình duyệt Chromium và WebView Android.

**Project Type**: Ứng dụng web (frontend của app Frappe `lotus_farm`)

**Performance Goals**: Dung lượng kiểu sau nén của mỗi ứng dụng không tăng quá 15% (SC-008). Biểu đồ nông nghiệp không kéo thêm ECharts.

**Constraints**:
- Mọi chữ tiếng Việt.
- Màu chỉ trong `lotus-tokens.css`.
- Không nút mật độ phía trên bảng.
- Hộp chọn và menu mở trong hộp thoại phải nổi trên hộp thoại.
- Màn chưa chuyển vẫn chạy đúng.

**Scale/Scope**:
- Khoảng 200 tệp `.vue` và 178 thẻ bảng ở 54 tệp.
- 64 lô mỗi vườn, 12 màu dây, tuần ISO (2026 có 53 tuần).

## Constitution Check

| Nguyên tắc | Đánh giá |
|---|---|
| I. Số thực, không suy diễn | Đạt. Thành phần chỉ hiển thị số được đưa vào. Thiếu số thì hiện "—" và lý do, không hiện 0. Biểu đồ không vẽ cột cho tuần chưa có thực tế. Trang mẫu ghi rõ "Dữ liệu mẫu" và không gọi máy chủ (có test). |
| II. Một nguồn sự thật | Đạt. Một nguồn token, một từ vựng trạng thái (`ui-status.js`), một nguồn màu dây (`ribbon-colors.js`), một nguồn chế độ và mật độ (`ui-mode.js`), một bảng biểu tượng (`icon-paths.js`). |
| III. Truy vết và kiểm soát | Không áp dụng (không đổi dữ liệu nghiệp vụ). Lựa chọn hiển thị cũ của người dùng được giữ (FR-047). |
| IV. Quy tắc tách riêng, có kiểm thử | Đạt. Module thuần có unit test: `ui-status`, `ribbon-colors`, `agri-format`, `ui-mode`, `grid-columns`, `chart-scale`, `grid-theme`. Component có hành vi có test mount. |
| V. Giao diện theo chuẩn chung | Đạt, kèm hai thay đổi cần chủ vườn duyệt ở trang mẫu: thanh dưới điện thoại có chữ (chuẩn 17/10 chỉ có biểu tượng), và nút phá hủy không còn là đỏ đặc. Màu vẫn chỉ ở `lotus-tokens.css`, Đỏ Lotus vẫn là màu chính. |

Không có vi phạm cần giải trình.

## Project Structure

### Documentation (this feature)

```text
specs/004-bo-giao-dien-agritech/
├── spec.md              # Đặc tả
├── baseline.md          # Mốc trước khi làm (test, dung lượng, tương phản)
├── research.md          # Quyết định R1–R12
├── plan.md              # Tệp này
├── data-model.md        # Token, chế độ, trạng thái, màu dây, trạng thái lô
├── contracts/
│   ├── ui-kit.md        # API component của bộ (props, slots, emits, lớp kiểu)
│   └── data-table.md    # Hợp đồng bảng dùng chung: giữ gì, thêm gì
├── quickstart.md        # Cách kiểm chứng trên VPS
├── audit/04-bang-du-lieu.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
frontend/
├── src/
│   ├── lotus-tokens.css         # Token ba tầng, ba chế độ, hai mật độ (viết lại, giữ tên cũ)
│   ├── lotus-kit.css            # Lớp kiểu dùng chung của bộ (mới)
│   ├── ui-mode.js               # Chế độ và mật độ (mới)
│   ├── ui-status.js             # Từ vựng trạng thái (mới)
│   ├── ribbon-colors.js         # Màu dây (mới)
│   ├── lot-states.js            # Trạng thái lô, nhóm theo khu (mới)
│   ├── agri-format.js           # Tuần ISO, số có đơn vị (mới)
│   ├── chart-scale.js           # Thang trục cho biểu đồ SVG (mới)
│   ├── color-contrast.js        # Tỉ lệ tương phản cho trang mẫu (mới)
│   ├── icon-paths.js            # Bảng biểu tượng dùng chung (tách từ LotusIcon.vue)
│   ├── grid-theme.js            # Theme bảng từ token (viết lại)
│   ├── grid-columns.js          # Kiểu cột dựng sẵn (mới)
│   ├── workspace.js, use-desktop-workspace.js   # Dùng ui-mode
│   └── components/
│       ├── ui/{status-chip,banner,stat-tile,progress,switch,segmented,number-stepper,avatar,steps,timeline,description-list}/
│       ├── agri/                # 17 thành phần nông nghiệp
│       ├── showcase/            # Sáu phần của trang mẫu + dữ liệu mẫu
│       ├── UiShowcase.vue       # Khung trang mẫu
│       ├── LotusMobileNetBar.vue, LotusMobileShell.vue, LotusMobileBottomNav.vue
│       ├── DataTable.vue, DataTableViews.vue, WorkspaceBar.vue, LotusIcon.vue
│       └── field/               # Màn vườn chuyển sang bộ nông nghiệp
├── vite.showcase.config.js      # Dựng trang mẫu riêng (mới)
└── tests/                       # Test mới: tương phản, theme bảng, ui-mode, trạng thái, cột, mount bộ, trang mẫu
```

**Structure Decision**: Giữ cấu trúc frontend hiện có. Bộ mới nằm ở `components/ui/<tên>/` (giống shadcn-vue) và `components/agri/`. Kiểu dùng chung ở một tệp `lotus-kit.css` nạp ngay sau token ở mọi điểm vào, để máy tính và điện thoại cùng dùng.

## Rollout

1. **Đợt này**: nền, bộ thành phần, bảng, bộ nông nghiệp, trang mẫu, khung chung (thanh trên, mật độ, nút ngoài trời, thanh dưới, dải ngoại tuyến) và các màn vườn, buồng, thu hoạch, dự thu.
2. **Duyệt**: chủ vườn xem trang mẫu (SC-010), đặc biệt hai thay đổi chuẩn ở Constitution Check.
3. **Gộp**: gộp lại `main` (002 đã lên) và nhánh 003 trước khi lên máy chủ. Nhánh 003 sửa `lotus-tokens.css` (thêm `--lotus-signature-ink`) và `tests/design-tokens.test.js`: giữ cả hai phần.
4. **Đợt sau** (User Story 7, 8): chuyển hẳn Kho, Mua hàng, Tài chính, Nhân sự sang chip và kiểu cột chung, dọn kiểu cũ, biểu đồ ECharts và bản in theo token.

## Complexity Tracking

Không có.
