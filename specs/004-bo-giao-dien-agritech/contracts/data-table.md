# Hợp đồng: bảng dùng chung (DataTable, ListPage, OpsList)

Chi tiết hiện trạng ở [audit/04-bang-du-lieu.md](../audit/04-bang-du-lieu.md). 178 thẻ ở 54 tệp dựa vào hợp đồng này.

## Giữ nguyên

- **API**: 34 props, 11 sự kiện, slot `cell-<field>`, `cell`, `empty-actions`. `ListPage` và `OpsList` chuyển thuộc tính xuống `DataTable`.
- **Cờ cột riêng** trong `GRID_APP_KEYS` (`sum`, `unitField`, `defaultHidden`, `hideOnMobile`, `mobileValue`, `autoHide`, `groupNumbers`, `filterable`, `suppressExport`, `columnChooserLocked`). Cờ mới phải thêm vào danh sách này.
- **DOM và chữ mà test dựa vào**:
  - lớp: `.lotus-data-table`, `.lotus-ag-grid`, `.lotus-ag-grid-shell(--scroll)`, `.lotus-data-table__export`, `.lotus-data-table__selected`;
  - cột `__lotus_select` (đứng đầu) và `__lotus_stt` (thứ hai);
  - thẻ điện thoại: `.lotus-mobile-records`, `.lotus-mobile-record`;
  - phân trang: `.lotus-pagination`;
  - chữ: "N dòng đã chọn", "Xuất Excel", "Chọn dòng", "Hiện toàn bộ", "Tổng (N dòng)".
- **Khóa lưu**: khóa `localStorage` và giá trị `storage-key`. Đổi là mất bề rộng cột, cột ẩn, chế độ xem người dùng đã lưu.
- **Kho**: căn giữa ô và tiêu đề, có viền dọc giữa các cột.
- Chỉ dùng AG Grid Community, đăng ký từng module, không sửa trong ô.

## Thay đổi trong spec 004

| Mục | Trước | Sau |
|---|---|---|
| Theme | `grid-theme.js` có 3 biến thể không dùng; `DataTable` ghi đè 4 tham số, cỡ dòng 34/40 | `lotusGridTheme(density, variant)` dựng từ token: màu là biến CSS, cỡ theo `GRID_DENSITY` (36/44) khớp token. Mỗi tổ hợp một đối tượng theme. |
| Mật độ | Chỉ Kho và Báo cáo ngày có, không có nút | Một nguồn (`ui-mode.js`), chọn ở menu tài khoản; phân hệ vẫn `provide('lotusDesktopDensity')` được. |
| Biến thể Kho | CSS `!important` ở `stock-overview.css`, `warehouse-table-center.css` | Thêm `provide('lotusTableVariant','stock')` ở `StockApp.vue` → viền dọc qua theme. CSS căn giữa vẫn giữ. |
| Nền | Tiêu đề, rê chuột, dòng tổng cùng một màu (1,03:1); dòng chọn không đổi nền | Năm nền token riêng: `--lotus-table-header`, `-zebra`, `-hover`, `-selected`, `-total`. Dòng chọn tô nền cả phần ghim và phần cuộn, có vạch đỏ bên trái. |
| Lề ô | 8px/7px ghi cứng | `--lotus-table-cell-x` theo mật độ |
| Chế độ tối | Nền trắng ghi cứng ở thẻ điện thoại, vỏ lưới, popup lọc, ô nhập trong ô | Theo `--lotus-surface` |
| Chip bộ lọc đang bật | Lớp `.lotus-chip` riêng, không scoped | Chip chung `lotus-chip lotus-chip--primary lotus-chip--filter` |
| Kiểu cột | Mỗi màn tự viết `valueFormatter` (231 chỗ ở 43 tệp) | `grid-columns.js`; chuyển dần màn cũ sang. |

## Chưa làm trong đợt này

Nhóm dòng, ghim phải, chỉ báo chiều sắp xếp, lưu trạng thái theo tài khoản, bỏ dựng lại lưới khi đổi dữ liệu, CSS in bảng, thay ký tự `▾`/`✓` bằng `LotusIcon` trong tiêu đề cột và cột chọn.

`selection-enabled="false"` vẫn không bỏ cột Chọn trên lưới (lỗi A1 trong báo cáo bảng). Sửa lỗi này là đổi quy tắc đã nghiệm thu "cột Chọn đứng đầu mọi bảng" (`tests/fixed-select-stt.test.js`), nên cần chủ vườn đồng ý.
