# Lotus Kho — Bàn giao Mua hàng Lite, nhận theo đơn và PWA

## Kết quả đã hiện thực trong source code

- Tab **Mua hàng** tách khỏi Nhu cầu, giữ bảng Excel và tìm tức thì.
- Đơn mua: NCC chọn hoặc tạo nhanh; loại mua chủ đầu tư chỉ định hoặc kho tự mua; kho nhận; ngày giao; các dòng vật tư, ĐVT, số lượng, đơn giá; lưu nháp; liên kết đề nghị mua đã duyệt; file báo giá riêng tư.
- Xác nhận đặt hàng qua **ERPNext Purchase Order** bởi người có quyền submit; không dùng giá 0 khi xác nhận.
- Trên điện thoại, **Nhập theo đơn** mở danh sách Purchase Order đang chờ hàng. Chọn đơn rồi nhập lượng thực nhận theo ĐVT đơn (Bao, Can, Kg…), hệ thống quy đổi thành Stock UOM tại API. Form nhập không kèm bảng và chức năng nâng cao.
- Lập Purchase Receipt nháp, kiểm tra lại, ghi sổ; **không tạo Stock Entry thứ hai**. ERPNext cập nhật Bin/Stock Ledger, số đã nhận và số còn chờ. Nhận nhiều đợt, cảnh báo quá hạn, hạn chế ghi trùng bằng request ID, chặn số vượt.
- Xem danh sách phiếu nhận thuộc một đơn; người có quyền cancel được hủy phiếu hợp lệ, ERPNext đảo tồn và cập nhật lại đơn.
- Roles riêng: Warehouse Operator, Purchase Requester, Warehouse Receiver, Warehouse Manager, Purchase Approver. Tài khoản vận hành không tự được cấp Approver, quyền User/System Manager hoặc quyền xóa/chỉnh chứng từ hệ thống.
- URL PWA riêng: `http://localhost:8080/warehouse`, có giao diện điện thoại độc lập theo phong cách mua sắm, chỉ gồm 5 form thao tác: **Nhập theo đơn, Nhập kho khác, Xuất kho, Chuyển kho, Tạo đơn mua**. Phần nhập liệu có 5 form đơn giản; thanh dưới có 4 tab: Trang chủ, Lịch sử phiếu, Xuất nhập tồn, Tôi. Tab xem dữ liệu dùng thẻ dọc; không có bảng quản trị hay phần thiết lập trên PWA. Logo hiển thị lớn không cắt hình, nút chạm lớn; biểu mẫu tự nhập theo chiều dọc, dùng chung API ERPNext, đăng nhập Frappe, biểu tượng và manifest riêng. Service worker cache **chỉ static shell**, không cache API, báo giá, dữ liệu đã đăng nhập. Mất mạng không ghi sổ.
- Tạo manifest trả đúng MIME `application/manifest+json`.

## Nghiệp vụ ERPNext là nguồn dữ liệu gốc

1. Purchase Order đã submit mới được xem là hàng chờ về.
2. Purchase Receipt nháp không cộng tồn, PR đã submit cộng tồn và tăng lượng đã nhận trong PO.
3. Hủy PR qua ERPNext `cancel()`, không tự điều chỉnh `Bin` hoặc ghi thêm Stock Entry để tránh tăng/giảm tồn hai lần.
4. Tồn còn nhận và số lượng nhập tối đa được xác minh server-side khi tạo/submit PR, cộng thêm row lock và idempotency theo sự kiện từ điện thoại.
5. Chuyển kho, xuất dùng và kiểm kê vẫn là Stock Entry / Stock Reconciliation theo nghiệp vụ hiện hữu.
6. ĐVT Can/Bao quy đổi theo **từng Item**, không gán một hệ số chung.

## Nghiệm thu

- `npm test` + `npm run build`.
- `tests/integration/verify_buying_lite.py`: tạo NCC, PO, submit, idempotent receipt, nhận 5/12, Stock Ledger tăng đúng, cancel PR và xác nhận tồn quay về, PO còn 12/12. **Rollback toàn bộ dữ liệu UAT**.
- `tests/integration/verify_stock_overhaul.py`: kho và vật tư thật còn nguyên.
- `tests/integration/verify_warehouse_pwa.py`: route, manifest, SW và quyền roles.
- Backup DB + public/private files trước triển khai. Hai container frontend/backend phải cùng image tag. `deployment/Dockerfile.warehouse-pwa-purchase` dùng base image thực tế của runtime nên khi tái triển khai sang máy khác cần rebuild từ Docker ERPNext/Frappe tương ứng.

## Điều kiện còn thiếu để dùng PWA trên điện thoại thật

- `localhost:8080` là **localhost trên máy Windows đang chạy Docker**, không phải URL Internet của điện thoại. Trên LAN có thể mở qua IP nội bộ nếu kết nối cùng mạng và firewall cho phép.
- Cài PWA tin cậy qua Android/iOS cần **HTTPS ở hostname truy cập từ điện thoại**, hoặc localhost ngay trên máy chạy browser. Phải cấu hình host HTTPS/tunnel chính thức, rồi kiểm tra `manifest`, `service-worker`, `beforeinstallprompt`, đăng nhập và cập nhật cache trên điện thoại.
- Email của site chưa cấu hình outbound SMTP. Để tài khoản mới đăng nhập qua thư kích hoạt, quản trị viên phải cấu hình outgoing Email Account hoặc đặt mật khẩu qua quy trình quản trị bảo mật, không ghi mật khẩu vào Git/BRD.
- Mọi thao tác hủy PR chỉ dành cho Warehouse Manager được cấp quyền. Người tạo đơn không đồng thời tự phê duyệt PO.

## Hướng dẫn thao tác

Mở Kho → **Mua hàng** → **Tạo đơn mua** → chọn NCC, kho, vật tư, ngày về, báo giá → **Lưu nháp**. Người duyệt trong ERPNext xác nhận PO. Tại **Nhập kho** hoặc tab **Mua hàng → Hàng chờ về**, chọn PO, điền lượng thực nhận theo ĐVT đơn → **Tạo phiếu nhận nháp** → kiểm tra → **Ghi sổ nhận hàng**. Hàng còn chờ được cập nhật tự động. Lịch sử và sổ kho dùng chung bảng lọc Excel như Tồn kho.

Không chạy script xóa/reset hoặc nhập dữ liệu UAT trực tiếp mà không rollback. Không hứa đã nghiệm thu giao diện bằng thao tác tay khi mới có unit/integration/API test.

## Bản PWA Kho điện thoại v3 (15/10/2026)

- Header cam thấp 66px, logo Lotus bản gốc được thu lại; bỏ mô tả phụ bên dưới biểu tượng công việc.
- 4 tab cố định: **Trang chủ** (Tạo đơn mua đầu tiên, Nhập theo đơn, Xuất kho, Chuyển kho, Nhập không theo đơn), **Lịch sử**, **Xuất nhập tồn**, **Tôi** (tài khoản, chọn kho, đăng xuất).
- Trường chọn NCC, kho, nhân viên, vật tư dùng danh sách xổ xuống ngay khi chạm; gõ tiếng Việt có hoặc không dấu đều lọc tại chỗ. Không có AG Grid trên điện thoại.
- Nút Back và cử chỉ quay lại Android được giữ trong lịch sử màn hình của PWA; đang nhập thông tin chưa lưu sẽ yêu cầu xác nhận rời form.
- Biểu tượng PWA mới được cắt từ chính logo hiện có, tách hoa sen + chữ Lotus trên nền trắng, dùng file versioned `warehouse-icon-v3-192.png`, `warehouse-icon-v3-512.png` để tránh cache icon cũ.
- **Nhập không theo đơn** chỉ dành cho hàng không có đơn đặt mua. Đã có PO thì dùng **Nhập theo đơn** để ghi nhận hàng về, tránh tăng tồn hai lần.
- Backend có quyền đọc Stock Ledger Entry cho vai trò Lotus Warehouse Operator để sử dụng tab Xuất nhập tồn; kiểm tra quyền và doanh nghiệp/kho ở API vẫn áp dụng.
- Build/test: `npm test` (77/77), `npm run build`. Đã đưa image `lotus-warehouse-mobile-v3:20261015` vào cả backend/frontend và kiểm tra route, manifest, worker tại localhost:8080. Chưa có nghiệm thu trực tiếp bằng thao tác ngón tay trên điện thoại thật.
