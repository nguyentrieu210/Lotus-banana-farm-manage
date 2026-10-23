# Tài sản cố định và khấu hao Lotus

Mở **Tài chính – Kế toán → Tài sản cố định**. Nền dữ liệu là Asset, lịch khấu hao và sổ cái ERPNext; Lotus lưu bước xem trước, duyệt và phân bổ. Phạm vi: Lotus Agritech, VND, sổ mặc định, điều chuyển nội bộ công ty. Công cụ dụng cụ, chi phí trả trước, tài sản sinh học và giao dịch giữa pháp nhân có quy trình riêng.

## Quyền và kích hoạt

- Kế toán lập hồ sơ, nhập Excel, lập nghiệp vụ và tỷ lệ phân bổ. Kế toán trưởng xem trước, duyệt, hủy/đảo. Kiểm soát chỉ xem/xuất.
- Migration chỉ thêm schema, trường và quyền. Tính năng mặc định tắt, không sinh tài sản/bút toán.
- Trên môi trường thử, cấu hình nhóm tài sản, chạy hết một vòng nhập → duyệt → khấu hao → phân bổ → kết chuyển → đảo trước khi bật trên hệ thống làm việc.
- Khi kế toán trưởng bật tính năng, Lotus tắt `Accounts Settings.book_asset_depreciation_entry_automatically`. Bật lại tự động trong khi đang dùng quy trình duyệt bị chặn. Tắt tính năng không tự bật lại tự động khấu hao.
- Một nghiệp vụ có thể phát sinh nhiều chứng từ nhưng được duyệt trong một giao dịch. Lỗi khiến toàn bộ lần duyệt rollback; xem trước lại sau khi sửa lỗi.

## Thiết lập và nhập đầu kỳ

Màn TSCĐ có các mục **Tài sản, Nhóm tài sản, Vị trí, Tài khoản, Khấu hao, Biến động, Báo cáo**. Số trên mỗi mục là số hồ sơ/danh mục đang có; mục đã chọn nằm trong URL `asset_view` để tải lại hoặc quay lại đúng màn. Bảng Nhóm hiển thị tài khoản đã gắn, số tài sản và số hồ sơ chờ duyệt; có thể mở danh sách tài sản theo nhóm hoặc vị trí. Tài khoản mặc định hiện các TK có mã đang dùng, gồm cả tổng hợp và chi tiết; chọn “Tất cả tài khoản” để xem thêm các TK không mã/ngừng dùng.

Hồ sơ vừa thêm hoặc nhập Excel hiện ngay trong bảng **Tài sản** với trạng thái **Chờ duyệt**, có thể sửa/xem trước/hủy qua menu thao tác. Chỉ khi kế toán trưởng duyệt mới trở thành tài sản chính thức; dòng chờ duyệt được thay thế, không lặp. Tổng giá trị sổ sách không cộng các hồ sơ chờ duyệt. Khi chưa có hồ sơ, màn hình giữ bảng và các nút tạo/nhập, đồng thời hiển thị số nhóm/vị trí đã sẵn sàng. Tìm/lọc không có kết quả có nút xóa bộ lọc riêng.

Chi tiết tài sản có **Hồ sơ – Lịch khấu hao – Lịch sử biến động – Chứng từ**. Nhóm chưa có tài sản được duyệt có thể sửa cấu hình bởi kế toán trưởng; nhóm đã dùng giữ chính sách tài khoản. Vị trí giữ nguyên mã khi sửa tên hiển thị: bản cập nhật chỉ thêm trường nhãn `Location.lotus_display_name` vì ERPNext tự đồng bộ `location_name` theo mã. Trường mới để trống cho dữ liệu cũ và lấy tên gốc để hiển thị; không đổi liên kết hay tạo dữ liệu tài sản khi migrate.

Kế toán trưởng có thể nhập hai danh mục bằng Excel trước khi bật quản lý tài sản:

- **Thiết lập → Hệ thống tài khoản → Nhập tài khoản Excel**: tải mẫu, điền số tài khoản, tên, tài khoản cha, là nhóm (0/1), loại tài khoản. Tài khoản cha nhận số TK hoặc mã đầy đủ trong sheet `Tai khoan hien co`; có thể là một nhóm mới trong cùng file, không cần xếp cha trước con. Loại tài khoản lấy đúng giá trị trong sheet `Loai tai khoan`; để trống khi không cần phân loại riêng. Không tạo thêm tài khoản gốc.
- **Tài sản cố định → Nhập nhóm Excel**: tải mẫu, điền tên nhóm, không khấu hao (0/1) và bốn TK nguyên giá, hao mòn, chi phí khấu hao, mua sắm chờ ghi tăng. Nhận số TK hoặc mã đầy đủ của tài khoản chi tiết đang dùng đúng công ty và loại. Nhập tài khoản còn thiếu trước, sau đó tải lại mẫu nhóm.
- Chọn file `.xlsx` tối đa 5 MB / 2.000 dòng, **Xem trước**, sửa hết lỗi rồi **Xác nhận nhập**. Sheet đầu tiên chứa dữ liệu nhập; các sheet còn lại chỉ để tham chiếu. Giữ số TK ở dạng văn bản để giữ số 0 đầu; không dùng công thức Excel.
- Chỉ thêm mới. Dòng đã tồn tại và khớp hoàn toàn được bỏ qua; khác thông tin sẽ báo lỗi, không đổi tên, loại, cấu trúc hay tài khoản của danh mục đang có. Không ghi số dư, không chuyển số dư và không tạo bút toán. Thay đổi hệ thống tài khoản chuẩn vẫn theo luồng áp dụng Thông tư 99 hiện có.
- Lần xác nhận kiểm tra lại dữ liệu và quyền kế toán trưởng trong một giao dịch. Nếu danh mục thay đổi sau khi xem trước, phải xem trước lại; lỗi ở bất kỳ dòng nào hoàn tác toàn bộ lần nhập. Lịch sử thêm tài khoản/nhóm và ghi chú xác nhận được giữ trong hệ thống.

1. Kế toán trưởng tạo nhóm với tài khoản nguyên giá, hao mòn, chi phí khấu hao và mua sắm chờ ghi tăng. Chọn tài khoản chi tiết đúng công ty. Nhóm đã có tài sản được duyệt không được đổi chính sách tài khoản.
2. Tạo vị trí quản lý tài sản. Hồ sơ có mã riêng, serial, người quản lý và farm/lô.
3. Tài sản đầu kỳ: nhập ngày mua/ngày sử dụng thực tế, nguyên giá, hao mòn đầu kỳ, tổng số tháng và số kỳ đã trích; không điền dữ liệu giả. Tải mẫu Excel ở Nhập Excel, xem lỗi từng dòng rồi tạo hồ sơ chờ duyệt.
4. Duyệt từng hồ sơ. Hồ sơ đầu kỳ **không ghi thêm số dư**. Nhập số dư qua chức năng Số dư đầu kỳ hiện có; nguyên giá và hao mòn phải khớp trước khi được duyệt khấu hao. Tài khoản đối ứng đầu kỳ do kế toán xác định trong bảng cân đối đầu kỳ.
5. Mua mới: chọn đúng dòng hóa đơn mua đã duyệt (số lượng 1), hoặc chọn nhà cung cấp để lập Purchase Invoice chuẩn khi duyệt. Không tạo hai hồ sơ từ cùng một dòng mua. Mỗi tài sản là một đơn vị để có lịch bàn giao/thanh lý độc lập.

Phương pháp mặc định đường thẳng, hàng tháng; thời gian, giá trị thu hồi và phương pháp do kế toán trưởng quyết định theo hồ sơ. Nhóm không khấu hao được cấu hình rõ ràng. Hệ thống không tự áp thời gian pháp lý cho mọi loại tài sản.

## Khấu hao và phân bổ tháng

1. Chọn tháng; mở Phân bổ trên từng tài sản. Nhập tỷ lệ %, tài khoản chi phí và trung tâm chi phí, farm/lô/vụ/công việc nếu có. Chi phí sản xuất cần farm; chi phí chung farm có thể để trống lô.
2. Tổng tỷ lệ đúng 100%. Tháng mới kế thừa tỷ lệ gần nhất. Duyệt lưu snapshot; sửa tháng sau không đổi tháng trước.
3. Lập bảng khấu hao, xem tài sản đến hạn, tiền khấu hao và từng đích phân bổ. Tháng còn khấu hao trước đó chưa duyệt phải được xử lý theo thứ tự. Có thể xem trước tháng hiện tại nhưng chỉ ghi sổ khi đến ngày kết thúc tháng.
4. Kế toán có thể lưu bảng chờ duyệt; kế toán trưởng mở bảng, xem trước lại rồi duyệt. Lịch, hồ sơ, nhóm và phân bổ được kiểm tra lại; dữ liệu đã thay đổi cần xem trước mới. Mỗi kỳ chỉ ghi một lần.
5. Bút toán khấu hao ERPNext giữ nguyên để cập nhật lịch và giá trị còn lại. Một Journal Entry liên kết riêng chuyển chi phí sang các đích phân bổ; không khấu hao tài sản lần thứ hai. Tổng phân bổ sau làm tròn khớp số tiền nguồn. Nếu ERPNext sinh khấu hao lẻ, phân bổ giữ chính xác số lẻ đó; không làm tròn mất tiền nguồn.
6. Hoàn tất khấu hao/nghiệp vụ chờ duyệt trước kết chuyển chi phí, tính giá thành và khóa tháng. Khấu hao phục vụ sản xuất tham gia các báo cáo/kết chuyển hiện có; chi phí quản lý/bán hàng theo tài khoản cấu hình.

## Biến động và sửa sai

- Điều chuyển/bàn giao tạo Asset Movement; kiểm tra lại tỷ lệ phân bổ tháng, không suy diễn tỷ lệ từ vị trí.
- Sửa chữa dùng chi phí hóa đơn và Asset Repair. Nâng cấp được vốn hóa qua chứng từ chuẩn, có thời gian tăng thêm nếu được duyệt; không tính chi phí hai lần.
- Tạm ngừng/sử dụng lại lưu ngày và lý do. Trạng thái sử dụng không tự dừng khấu hao.
- Sửa phương pháp/thời gian phải qua nghiệp vụ cập nhật hồ sơ và duyệt; nguyên giá/nhóm/ngày gốc không sửa trực tiếp sau duyệt. Dùng nâng cấp/chứng từ phù hợp để thay đổi giá trị.
- Bán tạo Sales Invoice tham chiếu đúng Asset, không xuất tồn kho vật tư. Thu tiền sử dụng quy trình công nợ hiện có; số hóa đơn điện tử nhập từ hệ thống phát hành hóa đơn. Bảng xem trước thể hiện giá bán, VAT, giá trị còn lại, khấu hao bổ sung và lãi/lỗ.
- Thanh lý tính khấu hao đến ngày xử lý và ghi giảm qua ERPNext. Phục hồi dùng nghiệp vụ chuẩn để đảo đúng chứng từ liên quan.
- Hủy/đảo cần lý do, đúng quyền, kỳ mở. Đảo các nghiệp vụ/kỳ sau trước; nếu tháng đã tính giá thành thì đảo giá thành và kết chuyển trước. Đảo phân bổ trước khấu hao gốc; không xóa sổ cái hay lịch sử chứng từ.

## Đối chiếu và phục hồi

Sổ tài sản lọc theo ngày/farm, xuất Excel. Đối chiếu nguyên giá, hao mòn, giá trị còn lại với tài khoản nhóm và các Journal Entry được liên kết. Các chứng từ mua/bán còn đối chiếu công nợ như nghiệp vụ chuẩn.

Trước triển khai sao lưu DB và cấu hình, ghi nhận image đang chạy. Migrate, kiểm thử trên dữ liệu riêng, triển khai với tính năng tắt rồi kế toán trưởng kích hoạt. Nếu quay lại bản cũ, giữ tự động khấu hao tắt và giữ toàn bộ hồ sơ/lịch sử; không xóa DocType, bảng dữ liệu hay bút toán đã ghi. Phục hồi DB chỉ theo bản sao lưu phù hợp và quy trình vận hành.

## Kết quả kiểm chứng

Phát triển riêng ở nhánh `codex/fixed-assets`, tích hợp nền kế toán P5 (`807d3c1`). Bộ kiểm thử chạy ERPNext/HRMS/Lotus trên site `assets-test.localhost`, MariaDB và Redis riêng, không gắn dữ liệu production.

- Ghi tăng, đầu kỳ, tháng lẻ, khấu hao hết, nhiều farm, VAT mua/bán, nâng cấp, điều chuyển, tạm ngừng, thay đổi chính sách, bán/thanh lý và phục hồi được đối chiếu chứng từ thật.
- Duyệt đồng thời chạy hai kết nối DB: một lần ghi tăng và một lần khấu hao thành công; yêu cầu trùng bị từ chối. Đảo và ghi lại không làm tăng khấu hao hai lần.
- Nhập Excel tài khoản/nhóm được kiểm chứng trên ERPNext thật: cây cha/con đảo thứ tự, gắn theo số TK, bỏ qua bản ghi khớp, lỗi theo trường, dữ liệu thay đổi sau xem trước, quyền, hoàn tác khi lỗi giữa file và xác nhận đồng thời chỉ ghi một lần. Kiểm thử giao diện và Chromium đi qua xem trước → xác nhận cho cả hai danh mục.
- Phiên bản ERPNext hiện dùng ghi giảm theo `net_purchase_amount`, trong khi sửa chữa vốn hóa tăng `total_asset_cost`. Lotus đối chiếu GL của chứng từ giảm gốc và tạo JE liên kết để ghi giảm phần vốn hóa còn thiếu, không sửa chứng từ gốc.
- Phục hồi bán/thanh lý giữa tháng giữ bút toán đảo chuẩn ERPNext vào ngày phục hồi; cả kỳ gốc và ngày phục hồi phải mở. Bút toán phân bổ được đảo trước. Chứng từ gốc và lịch sử vẫn còn để đối chiếu.
- ERPNext không vốn hóa Asset Repair khi tài sản đã khấu hao hết; xem trước chặn trường hợp này và yêu cầu hồ sơ ghi tăng phần đầu tư mới. Không âm thầm coi nâng cấp là chi phí sửa chữa.
- Giao diện được kiểm tra trên Chromium thật: ô chỉnh tỷ lệ của AG Grid cập nhật dữ liệu nguồn; tổng khác 100% bị chặn, biểu mẫu và bảng xem trước hiển thị ngày dd/MM/yyyy.

Kiểm thử độc lập: `tests/test_asset_rules.py`, `frontend/tests/fixed-assets.mount.test.js`, `tests/integration/verify_fixed_assets.py`, `tests/integration/verify_asset_concurrency.py`. Kiểm thử tích hợp từ chối site production và yêu cầu `LOTUS_ASSET_TEST_ONLY=1` trong container test.

Kết quả bàn giao: 409 kiểm thử frontend qua; 227 kiểm thử Python hoàn tất (226 qua, 1 bỏ qua theo điều kiện có sẵn); 20 kịch bản ERPNext và hai cuộc đua duyệt đồng thời qua; build frontend thành công. Tính năng chưa bật và chưa triển khai lên production.
