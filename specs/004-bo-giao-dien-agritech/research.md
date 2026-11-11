# Research: Đúc lại bộ giao diện Lotus

Hiện trạng kiểm ngày 10/11/2026 trên nhánh tách từ `40f8330` (bằng `main` và bản đang chạy sau khi 002 lên máy chủ thật). Rà soát chi tiết bảng dữ liệu ở [audit/04-bang-du-lieu.md](audit/04-bang-du-lieu.md); các phần khác tra trực tiếp trong mã khi cần.

## R1. Hướng thiết kế "Đất và lá"

- **Decision**:
  - Nền trung tính ấm (màu đá, cát) thay cho xám lạnh pha xanh. Đỏ Lotus là màu hành động duy nhất và là dải thương hiệu (thanh trên).
  - Xanh lá của chữ "Agritech" mang nghĩa đạt, đã xong, khỏe. Vàng chuối là đến hạn, đang chờ. Xanh nước là thông tin, dự thu. Đỏ thẫm ngả hồng là nguy, quá hạn, cách ly. Nâu đất cho dữ liệu phụ.
  - Chất "agritech" đến từ dữ liệu nghề vườn: lưới 64 lô theo khu, màu dây, dải tuần ISO, nhãn cách ly đếm ngày, ô số liệu có đơn vị, biểu đồ dự thu. Không dùng ảnh, họa tiết hay hiệu ứng trang trí.
  - Bảng như sổ cái: chữ số đều cột, kẻ mảnh, năm mức nền phân biệt (tiêu đề, xen kẽ, rê chuột, đang chọn, dòng tổng).
- **Rationale**: Đỏ đất nung đi với trung tính ấm hài hòa hơn với xám lạnh. Màu dữ liệu lấy từ cây, quả, nước, đất nên người vườn đọc ra nghĩa mà không cần chú giải dài. Phần mềm nông nghiệp hàng đầu tạo nhận diện bằng bản đồ ô ruộng, thang trạng thái và số liệu có đơn vị, không bằng trang trí.
- **Alternatives**:
  - Thanh bên xanh lá đậm: cạnh thanh trên đỏ thành cặp đỏ và xanh lớn, trông như trang trí Giáng sinh. Bỏ.
  - Giữ xám lạnh hiện tại: an toàn nhưng vẫn là trang quản trị chung chung.
  - Thử 4 hướng song song bằng nhiều tác tử rồi chấm điểm: đã chạy nhưng hết hạn mức sử dụng giữa chừng, không ra kết quả. Một hướng được thiết kế và kiểm bằng ảnh chụp thật.

## R2. Đỏ thương hiệu và màu nguy

- **Decision**:
  - Nút đỏ đặc chỉ dành cho một hành động chính.
  - Hành động phá hủy (`variant="destructive"`) là nền đỏ thẫm nhạt có viền và biểu tượng (thùng rác, cấm), khác hẳn nút chính về sắc, độ đậm và hình.
  - Đỏ thẫm đặc (`variant="danger"`) chỉ dùng cho bước xác nhận cuối trong hộp xác nhận.
  - Màu nguy (`--lotus-danger-600` #b3243f) ngả hồng, khác sắc đỏ cam của thương hiệu (#c43224). Mọi chip nguy có biểu tượng.
- **Rationale**: FR-007 yêu cầu phân biệt không chỉ bằng màu. 16 chỗ đang dùng `variant="destructive"` đổi diện mạo mà không phải sửa mã.

## R3. Ba chế độ hiển thị

- **Decision**: Sáng (mặc định), `.dark`, `.lotus-outdoor` trên `<html>`, do `ui-mode.js` đặt.
  - Ngoài trời là chế độ sáng tương phản cao: chữ chính từ 7:1, chữ to hơn một bậc và đậm hơn, viền đậm, vùng bấm 48px, nút chính đỏ đậm hơn (#a3291d) để chữ trắng đạt 7,26:1.
  - Ngoài trời không bao giờ đi cùng tối.
  - Điện thoại theo chế độ sáng/tối của máy như trước; nút mặt trời trên thanh trên bật hoặc tắt ngoài trời và nhớ trên máy.
  - Máy tính giữ lựa chọn sáng/tối cũ (khóa `lotus-theme`), không có ngoài trời.
- **Alternatives**: Tự bật theo cảm biến ánh sáng: trình duyệt không cho đọc cảm biến ổn định. Bỏ.

## R4. Mật độ một nguồn

- **Decision**: Hai mức gọn (mặc định) và thoáng, chọn ở menu tài khoản (FR-013, `AGENTS.md` cấm nút phía trên bảng). Lưu ở khóa cũ `lotus-desktop-density`. `DataTable` lấy mật độ từ `ui-mode.js` khi phân hệ không tự cấp.

  | Mức | Dòng | Tiêu đề | Chữ | Lề ô |
  |---|---|---|---|---|
  | Gọn | 36px | 36px | 13px | 10px |
  | Thoáng | 44px | 40px | 14px | 12px |

- **Rationale**: Trước đây Kho và Báo cáo ngày mặc định 40px, các phân hệ khác 34px, và không có nút chuyển (`setDensity` không ai gọi). 36px là điểm giữa, đúng quy ước bảng gọn.

## R5. Token ba tầng, chỉ mã hex

- **Decision**: `lotus-tokens.css` là nguồn duy nhất.
  - Tầng 1: dải màu gốc 50–900 (đỏ, đá, lá, chuối, đỏ thẫm, nước, đất), màu dây, màu khu.
  - Tầng 2: bề mặt, chữ, viền, tông (`--lotus-tone-<tông>-solid|on|soft|text|border`), trạng thái lô, biểu đồ.
  - Tầng 3: kích thước điều khiển, bảng, chip, thẻ theo mật độ.
  - Giữ mọi tên cũ. Mọi màu ghi hex hoặc `rgb()` vì WebView Android cũ không hiểu `oklch()`.
  - Viền ô nhập riêng (`--lotus-border-control`) đạt 3:1; viền phân cách vẫn nhạt.
- **Kiểm chứng**: `tests/design-tokens-contrast.test.js` đo 60 cặp ở ba chế độ.

## R6. Bảng dữ liệu

- **Decision**:
  - `grid-theme.js` dựng theme từ token qua tham số `themeQuartz.withParams` có thật trong AG Grid 36.2 (đã đối chiếu kiểu `BorderValue`, `LengthValue`, `ColorValue` trong `ag-stack`).
  - Màu là biến CSS nên đổi chế độ không phải dựng lại lưới. Kích thước là số vì lưới tính dòng bằng JS; `tests/grid-theme.test.js` buộc số khớp token.
  - Bảng Kho là biến thể có tên `stock` (có viền dọc), Kho cấp qua `provide('lotusTableVariant','stock')`.
  - Tô nền dòng đang chọn trên cả phần ghim và phần cuộn; dòng tổng có nền và viền riêng.
  - Bỏ nền trắng ghi cứng làm bảng và thẻ chói ở chế độ tối.
  - Kiểu cột dựng sẵn ở `grid-columns.js`: số, tiền, số lượng có đơn vị, phần trăm, ngày, hạn (kèm chip quá hạn), trạng thái, tiến độ, màu dây, người, lệch. Ô vẽ bằng DOM với đúng lớp kiểu của component Vue. `valueFormatter` luôn trả chữ thuần cho bộ lọc, thẻ điện thoại, dòng tổng và Excel.
  - Số lượng mang `unitField` nên dòng tổng không cộng lẫn đơn vị.
- **Để đợt sau** (báo cáo bảng, P2): nhóm dòng, lưu trạng thái theo tài khoản, bỏ dựng lại lưới khi đổi dữ liệu, in bảng.

## R7. Từ vựng trạng thái

- **Decision**: `ui-status.js` gom khoảng 80 mã trạng thái gốc (ERPNext, HRMS, Lotus) về 23 loại, mỗi loại có nhãn, tông và biểu tượng.
  - Nhãn của mã gốc vẫn lấy từ `labels.js` (`stateLabel`) để giữ chữ đang dùng.
  - Mã lạ hiện chip trung tính có chữ, không đoán tông.
  - Đã hủy có gạch ngang chữ, không chỉ xám.

## R8. Màu dây

- **Decision**: `ribbon-colors.js` đọc mã danh mục (`DO`, `XANH_LA_DO`…) và cả tên tiếng Việt gõ tay. Màu lấy từ token `--lotus-ribbon-*`, giống dây thật nên giữ nguyên ở mọi chế độ. Viền `--lotus-ribbon-outline` giữ Trắng và Đen thấy được trên mọi nền. Dây hai màu hiện nửa mỗi màu.

## R9. Biểu đồ trong bộ nông nghiệp

- **Decision**: Biểu đồ dự thu theo tuần và biểu đồ tuổi buồng là SVG viết tay, không dùng ECharts.
  - Lý do: chạy được trên điện thoại mà không tải gói ECharts khoảng 570 KB.
  - Chỉ vẽ số được đưa vào: tuần chưa có thực tế thì không có cột, không vẽ cột 0.
  - Có nhãn tóm tắt và nhãn từng cột cho trình đọc màn hình, đi được bằng bàn phím.
  - Biểu đồ ECharts có sẵn sẽ lấy màu từ token ở đợt sau (User Story 8).

## R10. Bộ điện thoại

- **Decision**:
  - Vant giữ nguyên; theme Vant trỏ vào token nên tự đổi theo chế độ.
  - Thanh dưới có chữ dưới biểu tượng (đổi so với chuẩn 17/10; chờ chủ vườn duyệt ở trang mẫu).
  - Dải "Đang ngoại tuyến" dính dưới thanh trên, kèm số việc chờ gửi.
  - Ô số có nút cộng trừ lớn (52px, ngoài trời 56px), giữ nút để tăng nhanh.
  - Bộ chọn màu dây là nhóm nút chọn một, đi bằng phím mũi tên.
  - Các thành phần nông nghiệp viết bằng CSS thuần nên dùng chung cho máy tính và điện thoại.

## R11. Trang mẫu

- **Decision**: `showcase.html` dựng bằng `vite.showcase.config.js`, không nằm trong bản chạy thật.
  - Sáu phần: Nền, Thành phần, Bảng, Điện thoại, Nông nghiệp, Mẫu màn hình.
  - Tham số `?section=&mode=&density=` mở riêng một phần ở một chế độ để chụp ảnh.
  - Dữ liệu mẫu cố định, không đọc hay ghi dữ liệu thật; tên người và nhà cung cấp là tên chung chung, không trùng dữ liệu của vườn.

## R12. Kiểm tra và nơi chạy

- **Decision**: Mọi test, bản dựng và ảnh chụp chạy ở `/opt/lotus-004-test` trên VPS (theo quy định không chạy nặng trên máy làm việc). Chromium 156 không giao diện chụp trang mẫu do một máy chủ tĩnh nội bộ ở `127.0.0.1:8704` phục vụ.
- **Bẫy đã gặp**:
  - Lệnh SSH treo khi tiến trình nền còn giữ đầu vào/đầu ra của phiên; dùng `setsid … </dev/null >/dev/null 2>&1 &`.
  - Vite biến `src` tĩnh bắt đầu bằng `/assets/` thành import tệp; logo phải gắn động (`:src="'/assets/…'"`).
  - Lớp `.lotus-chip` cũ trong `DataTableViews.vue` (không scoped) đè chip mới; đã chuyển sang `lotus-chip--filter`.
  - Quy tắc `label{flex-direction:column;font-size:12px}` trong `style.css` (lớp legacy) ảnh hưởng mọi `<label>`; nhãn trong bộ mới tự đặt lại.

## R13. Kiểu của thành phần nằm trong thành phần (đợt 2, 11/11)

- **Bối cảnh**: sau khi gộp `main` 737f686 (đã xóa nhiều CSS cũ), mốc dung lượng của bản máy tính giảm từ 58.526 xuống 55.274 byte sau nén. Cùng phần thêm của 004, mức tăng thành +15,6%, vượt SC-008. `lotus-kit.css` (46 KB) nạp ở mọi ứng dụng, kể cả kiểu của thẻ lô, lưới lô, biểu đồ… mà màn mở đầu không dùng.
- **Decision**: `lotus-kit.css` chỉ giữ lớp nhiều nơi dùng và lớp mà `grid-columns.js` vẽ (11 KB). Kiểu chỉ một thành phần dùng chuyển vào khối `<style>` không `scoped` của thành phần đó; hai biểu đồ dùng chung `lotus-kit-chart.css`. Màn nhập thẳng tệp thành phần, không qua tệp gộp. Kết quả: máy tính +9,1% so với mốc mới.
- **Phát hiện kèm theo**: `.lotus-stat` là lớp cũ của màn Tổng quan và Báo cáo (`workspace-experience.css`), trùng tên ô số liệu mới. Hai bên đè nhau, ví dụ `.lotus-stat span` cũ làm mất màu tốt/xấu của mũi tên lệch. Trang mẫu cũng bị vì nó nạp cả CSS cũ. Đã chuyển hai màn sang `StatTile` và xóa kiểu cũ; quy tắc mới: tên lớp mới không dùng tiền tố của bộ.
- **Alternatives**: lớp CSS (`@layer`) cho cả khung là đề xuất P0 của báo cáo khung; lớn và rủi ro, để đợt riêng.

## R14. Xem thử ứng dụng thật trên VPS (đợt 2)

- **Decision**: mount test và trang mẫu không thay được việc nhìn ứng dụng thật: lỗi trùng `.lotus-stat`, thanh bên nền đen ở 701–900px, ô tìm trắng chói ở chế độ tối chỉ lộ ra trên khung thật. Dựng bộ máy chủ thử riêng `lotus-004-test` (`/srv/lotus-test/004/stack.sh`, bản sao của kịch bản 002, image đang chạy thật b71a0b5, site `ui.test` nạp từ bản sao lưu 01:05 ngày 11/11 của lần triển khai b71a0b5, không sao lưu thêm từ máy chủ thật). Proxy `/opt/lotus-004-test/preview/server.mjs` phục vụ bản dựng 004 theo đúng cách trang www chọn tệp, các lệnh `/api` gửi sang site thử bằng khóa API của Administrator trên site thử; `shot.mjs` chụp bằng Playwright (bản của khu 003, chỉ đọc).
- **Bẫy**: mở đường dẫn sâu trong tab mới thì `App.vue` về trang đầu menu (lỗi đang có trên bản thật; bản sửa nằm ở nhánh 003), nên ảnh chụp đi bằng menu chuyển phân hệ. Điện thoại theo chế độ của hệ thống, muốn chụp chế độ tối phải giả lập hệ thống tối.
- **Dọn**: bộ thử giữ một bản sao dữ liệu thật; gỡ cả volume (`stack.sh down`) khi xong đợt.
