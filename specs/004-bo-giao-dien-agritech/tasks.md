---

description: "Danh sách việc: đúc lại bộ giao diện Lotus đạt chuẩn phần mềm nông nghiệp"
---

# Tasks: Đúc lại bộ giao diện Lotus đạt chuẩn phần mềm nông nghiệp

**Input**: `specs/004-bo-giao-dien-agritech/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-kit.md, contracts/data-table.md, quickstart.md

**Tests**: Có, theo nguyên tắc IV của constitution: unit test cho module thuần, mount test cho component có hành vi. Mọi test chạy trên VPS (`/opt/lotus-004-test`), không chạy trên máy làm việc.

**Quy ước đường dẫn**: frontend ở `frontend/src/`, test ở `frontend/tests/`.

## Phase 1: Setup

- [x] T001 Tạo nhánh `004-bo-giao-dien-agritech` trong worktree `C:\code\lotus-004-giao-dien` từ `40f8330` (bằng `main`, bản đang chạy)
- [x] T002 Lập chỗ thử trên VPS `/opt/lotus-004-test`: bản sao mã, `node_modules` liên kết cứng từ 003, máy chủ tĩnh nội bộ cổng 8704, Chromium chụp ảnh; mốc test 611/611 ghi ở `specs/004-bo-giao-dien-agritech/baseline.md`
- [x] T003 [P] Đo mốc dung lượng kiểu từng ứng dụng và tương phản bộ màu cũ vào `specs/004-bo-giao-dien-agritech/baseline.md`
- [x] T004 [P] Cấu hình dựng trang mẫu riêng `frontend/vite.showcase.config.js`, lệnh `showcase:build` trong `frontend/package.json`, bỏ qua `frontend/dist-showcase/` trong `.gitignore`

## Phase 2: Foundational (nền)

**⚠️ CRITICAL**: mọi phần sau dựa vào phase này.

- [x] T005 Viết lại `frontend/src/lotus-tokens.css` thành ba tầng, chế độ `.dark` và `.lotus-outdoor`, mật độ `[data-density="comfortable"]`; giữ mọi tên cũ, `--lotus-primary-600:#c43224`, `--primary:5 69% 45%`, `:root.dark{`
- [x] T006 [P] Bộ đọc token và tính tương phản `frontend/tests/support/css-tokens.mjs`; kiểm tra `frontend/tests/design-tokens-contrast.test.js` (chữ ≥ 4,5, viền và biểu đồ ≥ 3, ngoài trời ≥ 7, chỉ hex)
- [x] T007 [P] `frontend/src/ui-mode.js` (chế độ, mật độ, giữ khóa `lotus-theme`, `lotus-desktop-density`; thêm `lotus-outdoor`) và `frontend/tests/ui-mode.test.js`
- [x] T008 [P] `frontend/src/ui-status.js` (23 loại, khoảng 80 mã gốc, `dueState`) và `frontend/src/ribbon-colors.js`; test `frontend/tests/ui-status.test.js`
- [x] T009 [P] `frontend/src/agri-format.js` (tuần ISO, số có đơn vị) và `frontend/tests/agri-format.test.js`
- [x] T010 Tách bảng biểu tượng ra `frontend/src/icon-paths.js`, thêm 25 biểu tượng (trạng thái, nông nghiệp, bảng); `LotusIcon.vue` dùng bảng này; `tests/ui-status.test.js` và `tests/workspace-sidebar.mount.test.js` đọc bảng mới
- [x] T011 `frontend/src/lotus-kit.css` (lớp kiểu dùng chung) và `frontend/src/lotus-kit-mobile.css` (chỉ điện thoại: dải ngoại tuyến, ngoài trời); nạp ngay sau token ở mọi điểm vào `frontend/src/*main.js`
- [x] T012 Nối `ui-mode.js` vào `frontend/src/workspace.js` và `frontend/src/use-desktop-workspace.js` (một nguồn mật độ)

**Checkpoint**: nền xong; đổi chế độ và mật độ trên `<html>` là cả giao diện đổi theo.

## Phase 3: User Story 1 – Diện mạo thống nhất (P1) 🎯

**Independent Test**: trang mẫu phần Nền ở sáng, tối, ngoài trời; kiểm tra tương phản tự động.

- [x] T013 [US1] Nút: `destructive` tô nhạt có viền, `danger` đặc chỉ trong hộp xác nhận, thêm `soft`; cỡ theo token mật độ trong `frontend/src/components/ui/button/index.js`
- [x] T014 [US1] Chip trạng thái `frontend/src/components/ui/status-chip/` theo `ui-status.js`; chip bộ lọc đang bật trong `frontend/src/components/DataTableViews.vue` chuyển sang `lotus-chip--filter`
- [x] T015 [US1] Thay nền trắng ghi cứng bằng `--lotus-surface` trong `attio.css`, `style.css`, `stock*.css`, `warehouse-mobile.css`, `buying-mobile.css`, `mobile-work-legacy.css`, `LotusGridEditCell.vue`
- [x] T016 [US1] Menu tài khoản có "Bảng gọn hơn / thoáng hơn" trong `frontend/src/components/WorkspaceBar.vue`
- [x] T017 [US1] Thanh trên và thanh bên máy tính theo token (dải đỏ đậm dần, menu thả xuống theo chế độ tối) trong `frontend/src/desktop-shell.css`, `frontend/src/compact.css`. Nhóm token thanh trên mới (`--lotus-on-topbar-muted`, `--lotus-topbar-soft/-line/-sunken`, `--lotus-topbar-field*`, `--lotus-topbar-kbd*`), ô tìm và ô chọn vườn theo chế độ, bỏ `.workspace-menu` không còn dùng; thanh bên 701–900px hết nền đen ghi cứng, giống ≥901px. Đã chụp trên ứng dụng thật ở 1440, 1024, 800px, sáng và tối.

## Phase 4: User Story 2 – Bảng dữ liệu (P1)

**Independent Test**: trang mẫu phần Bảng; toàn bộ test bảng cũ vẫn qua.

- [x] T018 [US2] `frontend/src/grid-theme.js`: `lotusGridTheme(density, variant)` từ token; `frontend/tests/grid-theme.test.js` buộc cỡ khớp token
- [x] T019 [US2] `frontend/src/components/DataTable.vue`: theme theo mật độ chung và biến thể Kho (`provide('lotusTableVariant','stock')` ở `StockApp.vue`), lề ô theo token, tô dòng đang chọn, dòng tổng riêng; bỏ quy tắc tiêu đề trùng ở `attio.css`, `desktop-system.css`
- [x] T020 [US2] `frontend/src/grid-columns.js` (số, tiền, số lượng có `unitField`, %, ngày, hạn, trạng thái, tiến độ, màu dây, người, lệch) và `frontend/tests/grid-columns.test.js`
- [x] T021 [US2] Chuyển dần các màn sang kiểu cột chung, bắt đầu `FinanceApp.vue` (35 bảng), `stock-columns.js`, `OpsList.vue`. Đợt 2: cột trạng thái của ba tệp này (và Nhân sự, Mua hàng) dùng `statusCol`/`chipNode`. Hàm tiền, số lượng, ngày của Tài chính và Kho giữ có chủ đích (sổ kế toán để trống số 0, không gắn "đ"); xem `contracts/data-table.md`.

## Phase 5: User Story 3 – Bộ thành phần máy tính (P1)

- [x] T022 [P] [US3] `Banner`, `StatTile`, `Progress`, `ProgressRing`, `Switch`, `Segmented`, `NumberStepper`, `Avatar`, `Steps`, `Timeline`, `DescriptionList` trong `frontend/src/components/ui/*/`
- [x] T023 [US3] Mount test `frontend/tests/ui-kit.mount.test.js`

## Phase 6: User Story 4 – Điện thoại ngoài vườn (P2)

- [x] T024 [US4] `frontend/src/components/LotusMobileShell.vue`: chế độ theo `ui-mode.js`, nút ngoài trời, dải ngoại tuyến `LotusMobileNetBar.vue`
- [x] T025 [US4] Thanh dưới có chữ dưới biểu tượng: `frontend/src/components/LotusMobileBottomNav.vue`, `frontend/src/mobile-ui.css` (chờ chủ vườn duyệt)
- [x] T026 [US4] Dùng `NumberStepper size="lg"` và `RibbonPicker` trong hộp nhập lô `frontend/src/components/field/LotEntryModal.vue` (trên điện thoại). Số buồng của cắt bắp, bao, thu, hủy và màu dây của bao, thu, hủy sau cắt bắp; máy tính giữ ô cũ. Mount test mới trong `tests/lot-entry.mount.test.js`.
- [x] T027 [US4] Kiểm tra ba ứng dụng điện thoại thật ở 320 và 390px trên bản dựng thử (chụp ảnh trên VPS). Đã chụp Công việc, Kho, Mua hàng, Nhân sự ở 390px; Công việc và Kho ở 320px; Công việc ở chế độ ngoài trời và tối; hộp nhập lô thật (lô A1) ở 390px sáng và ngoài trời. Không tràn ngang; thanh dưới đủ chữ ở 320px.

## Phase 7: User Story 5 – Bộ nông nghiệp (P2)

- [x] T028 [P] [US5] `frontend/src/lot-states.js`, `frontend/src/chart-scale.js`
- [x] T029 [P] [US5] 17 thành phần trong `frontend/src/components/agri/` (thẻ lô, lưới lô, màu dây, bộ chọn màu dây, thẻ đợt màu, tuần, đến hạn, cách ly, biểu đồ dự thu, tuổi buồng, khu, chú giải bản đồ, ca xưởng, tổ)
- [x] T030 [US5] Mount test `frontend/tests/agri-kit.mount.test.js`
- [x] T031 [US5] Màn Hôm nay dùng `LotCard`: `frontend/src/components/field/LotCards.vue`
- [x] T032 [US5] Màn Màu dây và thu hoạch dùng `StatTile`, `RibbonDot`, `RibbonBatchCard`: `frontend/src/components/field/RibbonBoard.vue`; cập nhật một câu kiểm tra trong `frontend/tests/ribbon-board.mount.test.js`
- [x] T033 [US5] Vòng chăm sóc theo token của bộ: `frontend/src/components/field/CareDueList.vue`
- [x] T034 [US5] `swatch()` trong `frontend/src/lot-entry-model.js` dùng `ribbon-colors.js` (bỏ bảng hex ghi cứng); cập nhật `frontend/tests/lot-entry-model.test.js`
- [x] T035 [US5] Báo cáo Sáng nay / Tuần / Tháng dùng `StatTile`, `LotGrid` thay ô số và bản đồ màu riêng: `frontend/src/components/report/FieldReports.vue`. Thẻ số (`ReportCards.vue`) là `StatTile` dạng nút, tông theo mức tốt/cần chú ý/xấu, "Xem N dòng" ở chân thẻ. Bản đồ tuần giữ `CareMap` (bản đồ địa lý của lô, nhiều thông tin hơn lưới); `LotGrid` dành cho nơi cần cả vườn trong một khung nhỏ.
- [x] T036 [US5] Xưởng dùng `ShiftCard`: `frontend/src/components/field/PackhouseShifts.vue`. `ShiftCard` thêm `interactive` và `lines`; chip trạng thái nhập kho.

## Phase 8: User Story 6 – Trang mẫu (P2)

- [x] T037 [US6] `frontend/src/components/UiShowcase.vue` và sáu phần trong `frontend/src/components/showcase/`, dữ liệu mẫu cố định `sample-data.js`, tham số `?section=&mode=&density=`
- [x] T038 [US6] `frontend/tests/showcase-coverage.test.js` (đủ thành phần, ghi rõ dữ liệu mẫu, không gọi máy chủ, không vào bản chạy thật)
- [ ] T039 [US6] Chủ vườn xem và duyệt trang mẫu (SC-010), nhất là thanh dưới có chữ và nút phá hủy mới

## Phase 9: User Story 7, 8 – Chuyển phân hệ, biểu đồ, bản in (P3)

- [x] T040 [US7] Kho, Mua hàng, Tài chính, Nhân sự: thay nhãn trạng thái tự viết (`fin-cell-*`, `lotus-grid-status`, `tk-pill`…) bằng chip chung; xóa kiểu cũ. Xem bảng "Cột trạng thái" trong `contracts/data-table.md`. `fin-cell-ok/bad` còn cho cột số (chênh lệch, lỗi) vì đó là tô số, không phải trạng thái.
- [x] T041 [US8] Biểu đồ ECharts (`LotusChart.vue`) lấy màu từ token theo chế độ: trục `--lotus-chart-axis`, lưới `--lotus-chart-grid`, đủ 8 màu; vẽ lại khi đổi sáng, tối, ngoài trời. `DesktopForecastChart.vue` đã bị `main` xóa.
- [x] T042 [US8] Bản in luôn nền trắng chữ đen (`@media print` trong `lotus-tokens.css`). Khối token tối và ngoài trời nằm trong `@media screen`; khi in, mọi token về bộ sáng, trang trắng, `color-scheme: light`. Test trong `design-tokens-contrast.test.js`.

## Phase 10: Polish

- [x] T043 Toàn bộ test frontend trên VPS: xem kết quả mới nhất trong `baseline.md`
- [x] T044 Dung lượng kiểu sau nén ≤ +15% mỗi ứng dụng (SC-008): máy tính +14,8%, Kho +11,8%, Mua hàng +11,3%, Công việc +11,3%, Nhân sự +13,1%
- [ ] T045 Gộp lại `main` và nhánh 003 (`lotus-tokens.css` thêm `--lotus-signature-ink`; `tests/design-tokens.test.js` quét thêm thư mục con), chạy lại toàn bộ test. Đợt 2: đã gộp `main` 737f686 (commit 9e1646f, 599/599). Nhánh 003 còn ~49 tệp chưa commit nên chưa gộp được. Hai nhánh cùng sửa `lotus-tokens.css` (004 viết lại cả tệp; 003 thêm `--lotus-signature-ink`: thêm token đó vào bộ mới), `LotusMobileShell.vue`, `WorkspaceBar.vue`, `buying-mobile.css`, `tests/design-tokens.test.js`.
- [ ] T046 Dựng bản phát hành và đưa lên VPS khi chủ vườn yêu cầu

## Đợt 2: việc phát sinh

- [x] T047 Tách `lotus-kit.css`: lớp một thành phần dùng chuyển vào khối `<style>` của thành phần; biểu đồ dùng `lotus-kit-chart.css`; màn nhập thẳng tệp thành phần. Máy tính từ +15,6% xuống +9,1% so với mốc mới (R13).
- [x] T048 Sửa trùng lớp `.lotus-stat`: màn Tổng quan (`OverviewBoard.vue`) và Báo cáo (`ReportsWorkspace.vue`) dùng `StatTile`; xóa 4 quy tắc cũ trong `workspace-experience.css`; sửa `tests/reports-workspace.mount.test.js` theo cấu trúc mới.
- [x] T049 Màu dây trong hộp nhập lô có "lần": `field_report._ribbon_tags` đọc `week_half`, `lot_report._colours` trả `lan`; nhãn "Tím · tuần 45 lần 2 · còn 31". Trước đây hai đợt cùng màu cùng tuần hiện giống hệt nhau. Test Python `test_lot_paper_form`, `test_care_stage_rules`, `test_ribbon_board` đạt trên site thử; test JS trong `tests/lot-entry-model.test.js`.
- [x] T050 `NumberStepper`: từ ô rỗng, "+" cho một bước (trước là 0).
- [x] T051 Bộ xem thử ứng dụng thật trên VPS (R14) và ảnh chụp các màn đã đổi.
- [ ] T052 Gỡ bộ thử `lotus-004-test` cùng volume khi chủ vườn duyệt xong; gỡ khóa API Administrator đã tạo trên site thử `mua.test` của bộ 003 (bộ đó đang dừng).

## Dependencies & Execution Order

- Phase 2 trước mọi phần khác.
- US1, US2, US3 làm song song được sau Phase 2. US5 dùng chip, ô số liệu, tiến độ của US3.
- US6 (trang mẫu) cần các thành phần đã có.
- T039 (chủ vườn duyệt) trước T046 (lên máy chủ).

## Implementation Strategy

1. **MVP** (đã xong): nền, bảng, bộ thành phần, bộ nông nghiệp, trang mẫu, ba màn vườn chính, khung điện thoại.
2. **Duyệt**: chủ vườn xem trang mẫu.
3. **Đợt 2** (đã xong 11/11): T017, T021, T026, T027, T035, T036, T040–T042, T047–T051; gộp `main`.
4. **Còn lại**: chủ vườn duyệt (T039), gộp 003 khi nhánh đó commit (T045), phát hành khi được yêu cầu (T046), dọn bộ thử (T052).
