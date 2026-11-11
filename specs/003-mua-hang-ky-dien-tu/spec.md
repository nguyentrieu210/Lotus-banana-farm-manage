# Feature Specification: Hoàn thiện mua hàng: đề xuất, đơn mua, nhập kho, hóa đơn NCC, công nợ và ký điện tử trên điện thoại và máy tính

**Feature Branch**: `003-mua-hang-ky-dien-tu`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "chạy skill spec kit để làm lotus bảng đề xuất mua hàng đơn mua hàng và nhập kho công nợ hoá đơn NCC và Ký điện tử cho hoàn thiện cả giao diện điện thoại và máy tính"

## Ý tưởng chính

Một khoản mua đi đúng một đường: **đề xuất → đơn mua → nhập kho → hóa đơn NCC → công nợ → trả tiền**. Ở bước nào, người phụ trách cũng làm trọn việc của mình trên **điện thoại hoặc máy tính**, với cùng tên trạng thái và cùng quy tắc. Không bước nào phải mở ERPNext Desk.

Mọi chữ ký đi qua một chỗ là hộp **Chờ tôi ký**. Người ký bấm thông báo là tới đúng chứng từ, xem rồi ký hoặc trả lại. Khi đủ chữ ký, hệ thống lưu một bản PDF cố định có chữ ký, giờ ký và mã QR, để ai cầm bản in cũng đối chiếu được với bản gốc.

Phần lớn nghiệp vụ đã chạy thật từ đợt 07/11/2026: đề xuất ký 4 bước, đơn mua, nhận hàng từng phần, hóa đơn, phiếu chi ký 3 bước, công nợ tại ngày chốt. Spec này lấp chỗ thiếu, sửa chỗ hỏng và làm hai giao diện ngang nhau. Không làm lại từ đầu, không thay màn đang dùng.

## Hiện trạng (rà soát mã ngày 10/11/2026)

- **Ký**:
  - Chưa có hộp chờ ký chung.
  - Thông báo đề xuất mở về trang chủ app Mua hàng thay vì mở đề xuất.
  - Thông báo phiếu chi làm hỏng thao tác ký nếu người ký kế tiếp đã bật thông báo trên điện thoại.
  - Ký chỉ dựa vào việc đang đăng nhập.
  - Chỉ đơn mua có bản PDF đã ký được lưu lại.
  - Đơn mua duyệt theo chính sách không để lại chữ ký nào.
  - Xác nhận đơn mua qua đường khác chỉ cần có quyền duyệt, không cần đúng người được chỉ định đã ký.
  - Máy tính không có chỗ cài chữ ký, không trả lại hay chuyển người ký đơn mua.
  - Nút "ký bằng QR" và "ký nháy" của đơn mua không hoạt động.
- **Đề xuất**:
  - Máy tính thiếu "Chờ tôi ký", in PDF, chuyển người ký, xóa nháp.
  - Người được chỉ định ký mà không có quyền xem danh sách đề xuất thì không thấy gì.
  - Đề xuất kẹt ở "Đang mua" khi đơn đã đóng phần còn lại.
  - Hủy hoặc đóng đề xuất đã duyệt phải làm trên Desk.
  - App Kho dùng một biểu mẫu đề xuất rút gọn riêng.
- **Đơn mua**:
  - Máy tính không sửa được đơn nháp hoặc đơn bị trả lại, không trả lại, không hủy.
  - Nút "In đơn mua" báo lỗi.
  - Lập đơn từ đề xuất làm mất giá và NCC đã chọn.
  - Dòng nhập ngoài đề xuất lưu được nhưng bị chặn lúc duyệt.
  - App Kho chỉ lập nháp, không gửi duyệt được.
  - Danh sách không hiện "Đã gửi NCC" và "NCC đã xác nhận".
- **Nhập kho**:
  - Nhận theo đơn trên điện thoại không chụp ảnh được.
  - Phiếu trả hàng phải xác nhận trên Desk.
  - Phiếu nhận xem ở Mua hàng không in được và không đính kèm được.
  - Cùng một phiếu mang hai tên trạng thái khác nhau.
- **Hóa đơn NCC**:
  - Không lưu file gốc, không in, không hủy.
  - Phiếu Mua nhanh không lập được hóa đơn ở Mua hàng.
  - Hai đường lập hóa đơn kiểm tra trùng khác nhau.
- **Công nợ**:
  - Chỉ có số dư; không có tuổi nợ, không có sổ chi tiết từng NCC, không có biên bản đối chiếu.
  - Ở Mua hàng chưa trả được nhiều hóa đơn bằng một phiếu chi.
  - Nút mở phiếu chi trong phần tiến độ mở nhầm loại chứng từ.

## Clarifications

### Session 2026-11-10

- Q: Khi bấm Ký một chứng từ mua hàng, người ký phải xác thực thế nào? → A: Giữ như hiện tại: đang đăng nhập là ký được, chỉ bấm xác nhận. Không thêm mã ký, vân tay hay chữ ký số.
- Q: Đơn mua lập từ đề xuất đã ký đủ và chọn giá rẻ nhất đang được tự duyệt. Sau này đơn mua duyệt thế nào? → A: Giám đốc ký mọi đơn. Bỏ tự duyệt theo chính sách.
- Q: Khi nhận hàng theo đơn, ai ký phiếu nhập kho, có bắt buộc không? → A: Bấm xác nhận nhập kho là thủ kho ký luôn. Người giao hàng của NCC ký tay trên màn hình kèm họ tên, hoặc chụp phiếu giao có chữ ký; bắt buộc có một trong hai.
- Q: Hóa đơn NCC nên được điền sẵn từ đâu? → A: Nhập tay như hiện nay. File XML, PDF hoặc ảnh hóa đơn chỉ đính kèm làm bằng chứng; không đọc số tự động từ file.
- Q: Mọi đơn mua đã phải giám đốc ký, vậy Mua nhanh (nhập kho ngay, không qua đề xuất và đơn) kiểm soát thế nào? → A: Giữ như hiện tại: không giới hạn tiền, không cần ký. Danh sách chỉ ghi rõ đó là phiếu Mua nhanh.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ký điện tử: một hộp chờ ký, mở đúng chứng từ, bản đã ký được lưu (Priority: P1)

Những người ký gồm:
- trưởng bộ phận;
- mua hàng hoặc kế toán;
- kế toán trưởng;
- giám đốc;
- thủ kho.

Mỗi người mở **Chờ tôi ký** trên điện thoại hoặc máy tính và thấy mọi chứng từ đang đến lượt mình: đề xuất mua, đơn mua, phiếu chi và các phiếu kho đang chờ ký. Bấm một dòng thì chứng từ mở ngay trên thiết bị đang dùng, cùng các chữ ký trước đó. Từ đây người ký có ba thao tác:
- **Ký**: ký bằng phiên đăng nhập hiện tại, sau một bước xác nhận.
- **Trả lại**: ghi lý do.
- **Chuyển người ký**: giao bước của mình cho người khác đủ quyền.

Thông báo trên điện thoại và email mở thẳng đúng chứng từ. Khi đủ chữ ký, hệ thống lưu bản PDF cố định có chữ ký, giờ ký và QR xác minh. Mỗi người tự cài ảnh chữ ký và ký nháy ở mục **Chữ ký của tôi**, có trên cả hai giao diện.

**Why this priority**: Bước nào khác cũng phải chờ chữ ký. Hiện người ký không có chỗ xem việc đang chờ mình, thông báo mở sai chỗ, thông báo phiếu chi còn làm hỏng thao tác ký, và chỉ đơn mua có bản đã ký lưu lại.

**Independent Test**: Trên site thử, lập một đề xuất và một phiếu chi, gán người ký đã bật thông báo điện thoại. Mỗi người ký bấm thông báo và phải tới đúng chứng từ, rồi ký trên điện thoại hoặc máy tính. Khi người cuối ký xong, bản PDF lưu phải có đủ chữ ký, và quét QR phải ra trang xác minh báo "khớp bản lưu".

**Acceptance Scenarios**:

1. **Given** giám đốc có 3 đề xuất và 2 phiếu chi đến lượt ký, **When** mở Chờ tôi ký trên điện thoại, **Then** thấy đủ 5 dòng; mỗi dòng có loại chứng từ, số, người lập, số tiền, bước ký và ngày gửi; bấm dòng nào thì mở đúng chứng từ đó ngay trong app đang dùng.
2. **Given** thông báo "Đến lượt bạn ký: đề xuất X", **When** bấm thông báo trên điện thoại, **Then** mở chi tiết đề xuất X, không phải trang chủ.
3. **Given** kế toán trưởng đã bật thông báo trên app Mua hàng, **When** kế toán ký bước 1 của phiếu chi, **Then** thao tác thành công và kế toán trưởng nhận thông báo mở được phiếu chi.
4. **Given** người ký bấm Ký, **When** hộp xác nhận hiện loại chứng từ, số, số tiền và bước ký, **Then** chỉ khi bấm xác nhận thì chữ ký mới được ghi; bấm hủy thì chứng từ không đổi.
5. **Given** bước cuối của đơn mua vừa được ký, **When** hoàn tất, **Then** bản PDF lưu có, cho từng bước: ảnh chữ ký (hoặc tên nếu người ký chưa cài ảnh), chức danh và giờ ký, cùng QR xác minh. Quét QR thấy số chứng từ, trạng thái, giờ từng bước và "khớp bản lưu".
6. **Given** chứng từ đã ký đủ sau đó bị hủy, **When** quét QR trên bản in cũ, **Then** trang xác minh báo "Đã hủy".
7. **Given** trưởng bộ phận nghỉ phép, **When** người lập hoặc người đang đến lượt chọn Chuyển người ký sang người khác đủ quyền và ghi lý do, **Then** người mới nhận thông báo và lịch sử ký ghi lại việc chuyển.
8. **Given** giám đốc có 12 phiếu chi cùng chờ mình ký, **When** chọn cả 12 và ký một lần với một lần xác nhận, **Then** từng phiếu được kiểm tra và ký riêng; phiếu nào lỗi thì báo riêng, các phiếu khác vẫn được ký.
9. **Given** người dùng đổi ảnh chữ ký, **When** mở một bản PDF đã ký trước đó, **Then** bản đó vẫn mang ảnh cũ.
10. **Given** một chứng từ đã có chữ ký nhưng nội dung bị sửa bằng đường khác, **When** đến lượt người kế tiếp ký, **Then** hệ thống chặn và báo nội dung đã đổi sau khi ký.

---

### User Story 2 - Bảng đề xuất mua đầy đủ trên điện thoại và máy tính (Priority: P1)

Người đề xuất (tổ trưởng, thủ kho, đội trưởng, quản lý vườn) lập đề xuất trên điện thoại hoặc máy tính, kể cả từ màn Kho, bằng cùng một biểu mẫu. Biểu mẫu gồm: bộ phận, lý do, kho nhận, rồi từng dòng vật tư với số lượng, ngày cần và giá dự kiến (có thể để trống).

**Bảng đề xuất** chia theo giai đoạn, mỗi giai đoạn có số đếm: Nháp, Chờ tôi ký, Đang ký, Bị trả lại, Chờ mua, Đang mua, Đã nhận đủ, Đã xong, Đã hủy.

Bấm một đề xuất thì mở hộp chi tiết, gồm:
- các dòng hàng;
- tiến độ từng dòng: đã đặt, đã nhận, đã có hóa đơn, đã trả tiền;
- chuỗi chữ ký;
- file đính kèm;
- bản PDF.

Tùy quyền, người dùng có thể sửa, ký và gửi, trả lại, chuyển người ký, xóa nháp, in, hủy, hoặc đóng phần chưa mua.

**Why this priority**: Đề xuất là cửa vào của mọi khoản mua và đang được dùng thật từ 07/11. Nhưng máy tính còn thiếu nhiều thao tác, còn điện thoại không mở được đề xuất từ thông báo.

**Independent Test**: Lập một đề xuất 5 dòng từ app Kho trên điện thoại. Ký đủ 4 bước: 2 bước trên máy tính, 2 bước trên điện thoại. Đặt hàng 3 dòng, nhận đủ 3 dòng đó, rồi đóng 2 dòng còn lại; lúc này đề xuất ở "Đã nhận đủ". Lập hóa đơn cho phần đã nhận thì đề xuất chuyển "Đã xong". Ở mỗi lúc, bảng phải hiện đúng giai đoạn.

**Acceptance Scenarios**:

1. **Given** thủ kho đang ở app Kho, **When** lập đề xuất, **Then** dùng đúng biểu mẫu đầy đủ như app Mua hàng, và gửi xong thì mở ngay chi tiết đề xuất vừa lập.
2. **Given** đề xuất nhập từ Excel còn thiếu lý do, **When** người đề xuất mở để ký và gửi, **Then** được hỏi lý do ngay trong hộp ký, không phải sang màn khác.
3. **Given** trưởng bộ phận được chỉ định ký nhưng không có quyền xem danh sách đề xuất, **When** mở Chờ tôi ký, **Then** vẫn thấy và mở được đề xuất đó.
4. **Given** mua hàng bổ sung giá sau khi đề xuất đã có chữ ký, **When** lưu, **Then** đề xuất trở về người đề xuất để gửi vòng ký mới, và các chữ ký cũ vẫn xem được trong lịch sử.
5. **Given** đề xuất 5 dòng, 3 dòng đã nhận đủ và đã có hóa đơn, **When** mua hàng chọn Đóng phần chưa mua cho 2 dòng còn lại và ghi lý do, **Then** đề xuất chuyển sang "Đã xong", không kẹt ở "Đang mua".
6. **Given** đề xuất đã ký đủ, **When** bấm In, **Then** PDF có đủ chữ ký và QR; trên điện thoại chia sẻ được bằng nút chia sẻ của máy.
7. **Given** đề xuất chưa có dòng nào được đặt hàng, **When** người đề xuất hủy, **Then** phải ghi lý do và đề xuất chuyển "Đã hủy". Đề xuất đã có dòng được đặt thì chỉ đóng được phần chưa mua.

---

### User Story 3 - Đơn mua: chọn NCC và giá, duyệt có chữ ký, gửi cho NCC (Priority: P2)

Mua hàng lập đơn theo một trong hai cách:
- từ đề xuất đã duyệt, giữ nguyên NCC và giá đã chọn từ báo giá;
- từ bảng so sánh giá. Trên điện thoại, bảng này hiện theo từng mặt hàng, mỗi báo giá là một thẻ.

Đơn nháp hoặc đơn bị trả lại sửa được trên cả hai giao diện. Người lập gửi duyệt cho giám đốc. Giám đốc ký duyệt hoặc trả lại có lý do, trên điện thoại hay máy tính đều được.

Sau khi duyệt, đơn có bản PDF đã ký để tải hoặc chia sẻ cho NCC. Người dùng có thể đánh dấu đã gửi NCC hoặc NCC đã xác nhận, đổi hẹn giao, đóng phần chưa giao, và hủy đơn chưa nhận hàng.

**Why this priority**: Đơn mua là cam kết trả tiền cho NCC. Hiện máy tính không sửa, trả lại hay hủy được đơn và không in được đơn. Đơn tự duyệt theo chính sách không có chữ ký giám đốc.

**Independent Test**: Lấy một đề xuất đã duyệt có 2 báo giá. Chọn giá trên điện thoại rồi lập đơn. Giám đốc trả lại một lần trên máy tính; người lập sửa; giám đốc duyệt lại trên điện thoại. Tải PDF và đánh dấu đã gửi NCC. Danh sách đơn phải hiện đúng từng trạng thái.

**Acceptance Scenarios**:

1. **Given** đề xuất đã duyệt, đã chọn báo giá của NCC A giá 120.000 đ, **When** lập đơn từ đề xuất, **Then** đơn có sẵn NCC A và giá 120.000 đ.
2. **Given** đơn có một dòng không thuộc đề xuất đã duyệt, **When** lưu, **Then** hệ thống báo ngay dòng đó sẽ không duyệt được và vì sao, không đợi đến lúc duyệt.
3. **Given** đơn đang chờ duyệt, **When** giám đốc trả lại trên máy tính kèm lý do, **Then** người lập thấy lý do trên cả hai giao diện và sửa được đơn.
4. **Given** đơn lập từ đề xuất đã ký đủ và chọn đúng giá rẻ nhất, **When** lưu và gửi duyệt, **Then** đơn vẫn ở "Chờ duyệt" cho đến khi giám đốc ký; không đơn nào được tự duyệt.
5. **Given** một người có quyền duyệt mua nhưng không phải người được chỉ định, **When** cố xác nhận đơn bằng đường khác ngoài màn Lotus, **Then** bị chặn.
6. **Given** đơn đã duyệt, **When** bấm In đơn mua trên máy tính hoặc điện thoại, **Then** mở đúng bản PDF đã ký được lưu.
7. **Given** đơn chưa nhận hàng, **When** hủy kèm lý do, **Then** đơn chuyển "Đã hủy", và các dòng đề xuất liên quan trở về "Chờ mua".
8. **Given** thủ kho lập đơn nháp trên app Kho, **When** gửi duyệt, **Then** chọn được người duyệt và gửi ngay, không phải chuyển sang app khác.

---

### User Story 4 - Nhập kho theo đơn trên điện thoại, có ảnh và chữ ký (Priority: P2)

Thủ kho mở app Kho hoặc app Mua hàng trên điện thoại, chọn đơn đang chờ hàng, rồi:
1. nhập số thực nhận từng dòng (nhận một phần cũng được);
2. chụp ảnh hàng và phiếu giao hàng;
3. ghi chi phí phát sinh như vận chuyển, bốc xếp;
4. lấy xác nhận của người giao hàng: ký tay trên màn hình kèm họ tên, hoặc chụp phiếu giao có chữ ký (bắt buộc một trong hai);
5. xác nhận nhập kho. Bấm xác nhận là thủ kho ký luôn, không có bước ký riêng sau đó.

Phiếu nhập in được, có chữ ký và QR. Trả hàng, hủy phiếu (có lý do) và xóa phiếu nháp đều làm ngay trong app.

**Why this priority**: Lúc hàng về là lúc dễ sai số và thất lạc chứng từ nhất. Hiện nhận theo đơn trên điện thoại không chụp ảnh được, và phiếu trả hàng phải xác nhận trên Desk.

**Independent Test**: Làm toàn bộ trên điện thoại với một đơn 3 dòng:
1. Nhận lần 1 hai dòng, kèm 2 ảnh và chữ ký tay của người giao.
2. Nhận lần 2 dòng còn lại, thiếu 10%, kèm ảnh phiếu giao có chữ ký.
3. Trả lại 5 đơn vị của một dòng.

Phiếu in phải có danh sách ảnh, chữ ký và QR. Đơn phải hiện đúng số đã nhận và số còn chờ.

**Acceptance Scenarios**:

1. **Given** đơn còn chờ 100 bao, **When** nhận 60, **Then** có phiếu nhập 60 bao, đơn còn chờ 40, và đề xuất liên quan hiện "đã nhận 60".
2. **Given** thủ kho nhập số nhận vượt số còn chờ, **When** xác nhận, **Then** bị chặn và được báo số còn nhận được.
3. **Given** hai thủ kho cùng nhận một đơn cùng lúc, **When** cả hai xác nhận, **Then** tổng nhận không vượt số đặt, và người sau được báo số còn lại mới.
4. **Given** phiếu nhập đã xác nhận, **When** trả 5 bao hỏng, **Then** phiếu trả được lập và xác nhận ngay trong app, không cần Desk; nếu phiếu nhập đã có hóa đơn thì hệ thống nhắc lập hóa đơn điều chỉnh.
5. **Given** mất sóng đúng lúc bấm xác nhận, **When** có sóng lại và bấm lần nữa, **Then** chỉ có một phiếu nhập.
6. **Given** phiếu Mua nhanh (không qua đơn), **When** đã nhập kho, **Then** phiếu vẫn vào danh sách Hóa đơn chờ nhập và vào công nợ ở phần "hàng đã nhận, chưa có hóa đơn".
7. **Given** một phiếu nhận bất kỳ, **When** xem ở Kho hay Mua hàng, trên điện thoại hay máy tính, **Then** đều cùng một tên trạng thái.
8. **Given** chưa có chữ ký tay của người giao và chưa có ảnh phiếu giao, **When** thủ kho bấm xác nhận nhập kho, **Then** bị chặn và được nhắc lấy một trong hai.
9. **Given** thủ kho bấm xác nhận nhập kho, **When** hoàn tất, **Then** phiếu mang chữ ký của thủ kho với giờ xác nhận, và bản PDF phiếu nhập được lưu ngay.

---

### User Story 5 - Hóa đơn NCC: nhập tay có file gốc kèm theo, khớp với hàng đã nhận, tổng đúng đến từng đồng (Priority: P3)

Khi hàng về kèm hóa đơn, thủ kho hoặc mua hàng chụp ảnh hoặc tải file hóa đơn (ảnh, PDF hoặc XML) vào phiếu nhận. Phiếu đó vào danh sách **Hóa đơn chờ nhập**.

Kế toán mở phiếu trên máy tính hoặc điện thoại và chọn các phiếu nhận mà hóa đơn bao gồm. Các dòng có sẵn số lượng chưa lập hóa đơn và đơn giá theo đơn mua. Kế toán tự gõ đầu hóa đơn (ký hiệu, số, ngày, hạn trả), rồi sửa đơn giá, thuế GTGT và tổng thanh toán cho khớp bản in. Trong lúc gõ, file gốc hiện ngay cạnh biểu mẫu. Hệ thống không đọc số từ file.

Hệ thống so hóa đơn với phiếu nhận và đơn mua, rồi chỉ ra chênh lệch số lượng và đơn giá. Kế toán ghi lý do cho từng chênh lệch rồi ghi hóa đơn. Tổng trên hệ thống phải khớp tổng in trên hóa đơn đến từng đồng. Hóa đơn giữ file gốc đính kèm, in được, hủy hoặc điều chỉnh được nếu có lý do.

**Why this priority**: Hóa đơn quyết định công nợ và giá vốn. Lotus là hộ kinh doanh nên thuế GTGT đầu vào tính vào giá vốn. Hiện hóa đơn không lưu file gốc, và phiếu Mua nhanh không lập được hóa đơn ở Mua hàng.

**Independent Test**: Nhập ba hóa đơn:
- một hóa đơn gộp 2 phiếu nhận, có thuế suất 5% và 8% xen nhau và phí vận chuyển, kèm file PDF gốc;
- một hóa đơn có ảnh chụp, cho phiếu Mua nhanh;
- một hóa đơn dịch vụ không có phiếu nhận.

Tổng phải khớp đến từng đồng, giá vốn đã gồm thuế, công nợ NCC tăng đúng, và mỗi hóa đơn có file gốc.

**Acceptance Scenarios**:

1. **Given** hóa đơn bao gồm 2 phiếu nhận, **When** kế toán chọn 2 phiếu đó, **Then** các dòng có sẵn số lượng chưa lập hóa đơn và đơn giá theo đơn mua; kế toán chỉ gõ đầu hóa đơn và sửa giá hoặc thuế cho khớp bản in.
2. **Given** phiếu nhận đã có ảnh hoặc file hóa đơn, **When** kế toán mở để nhập, **Then** file hiện ngay cạnh biểu mẫu trên máy tính, hoặc mở được bằng một chạm trên điện thoại, và được lưu kèm hóa đơn sau khi ghi.
3. **Given** đơn giá trên hóa đơn 125.000 đ trong khi đơn mua là 120.000 đ, **When** ghép, **Then** hệ thống hiện chênh lệch 5.000 đ nhân số lượng và yêu cầu lý do; giá vốn lấy theo giá hóa đơn.
4. **Given** đã có hóa đơn cùng NCC, cùng ký hiệu và số, **When** nhập lại hóa đơn đó ở bất kỳ màn nào, **Then** bị chặn vì trùng.
5. **Given** tổng các dòng lệch tổng in trên hóa đơn 1 đồng do làm tròn, **When** ghi, **Then** hóa đơn ghi theo tổng in, phần lệch làm tròn vào giá vốn và hiện rõ trên chi tiết.
6. **Given** hóa đơn đã có phiếu chi trả một phần, **When** người dùng hủy hóa đơn, **Then** bị chặn, kèm hướng dẫn đảo phiếu chi trước hoặc lập hóa đơn điều chỉnh.
7. **Given** phiếu Mua nhanh chưa có hóa đơn, **When** mở Hóa đơn chờ nhập ở Mua hàng, **Then** thấy phiếu đó và lập được hóa đơn cho nó.

---

### User Story 6 - Công nợ NCC và trả tiền (Priority: P3)

Kế toán, kế toán trưởng và giám đốc xem công nợ từng NCC tại một ngày chốt, gồm:
- nợ theo hóa đơn;
- hàng đã nhận nhưng chưa có hóa đơn (tạm tính);
- tạm ứng;
- số còn phải trả;
- tuổi nợ: chưa đến hạn, quá hạn 1–30, 31–60, 61–90 và trên 90 ngày;
- danh sách đến hạn trong 7 ngày tới.

Mở một NCC là ra sổ chi tiết công nợ: số đầu kỳ, từng hóa đơn, phiếu chi, trả hàng, số cuối kỳ. Từ đây in hoặc xuất được biên bản đối chiếu công nợ.

Từ màn công nợ, người dùng chọn một hoặc nhiều hóa đơn của một NCC để lập phiếu chi, bằng chuyển khoản hoặc tiền mặt. Phiếu chi đi qua chuỗi ký: kế toán → kế toán trưởng → giám đốc. Ký đủ thì phiếu được ghi sổ và công nợ giảm. Phiếu chi in theo mẫu, có chữ ký và QR.

**Why this priority**: Công nợ là con số chủ vườn cần để xoay tiền. Hiện màn công nợ chỉ có số dư, không có tuổi nợ hay sổ chi tiết, và ở Mua hàng chưa trả được nhiều hóa đơn cùng lúc.

**Independent Test**: Lấy một NCC có:
- 3 hóa đơn, trong đó 1 hóa đơn quá hạn 40 ngày;
- 1 phiếu nhận chưa có hóa đơn;
- 1 khoản tạm ứng.

Xem công nợ của NCC này trên cả điện thoại và máy tính. Lập 1 phiếu chi trả 2 hóa đơn và ký đủ 3 bước. Công nợ và tuổi nợ phải cập nhật, và biên bản đối chiếu phải khớp sổ.

**Acceptance Scenarios**:

1. **Given** ngày chốt 30/11, **When** xem công nợ, **Then** số còn phải trả theo hóa đơn của mỗi NCC đúng bằng số dư phải trả trên sổ kế toán tại ngày đó, lệch 0 đồng.
2. **Given** hóa đơn hạn trả 05/10 và ngày chốt 15/11, **When** xem tuổi nợ, **Then** hóa đơn nằm trong nhóm quá hạn 31–60 ngày.
3. **Given** chọn 2 hóa đơn của NCC A, **When** lập phiếu chi, **Then** số tiền mặc định bằng tổng còn nợ của 2 hóa đơn trừ khoản tạm ứng cấn trừ được, và không chi vượt được trừ khi ghi rõ phần vượt là tạm ứng.
4. **Given** phiếu chi đã ký đủ, **When** hoàn tất, **Then** phiếu được ghi sổ, hóa đơn chuyển "Đã trả" hoặc "Trả một phần", công nợ giảm, và bản PDF phiếu chi được lưu kèm chữ ký.
5. **Given** giám đốc đang dùng điện thoại, **When** mở công nợ, **Then** xem được tổng, tuổi nợ, từng NCC và sổ chi tiết, và ký phiếu chi từ Chờ tôi ký.
6. **Given** người dùng in biên bản đối chiếu của NCC A từ 01/10 đến 30/11, **When** so với sổ chi tiết, **Then** số đầu kỳ, phát sinh và cuối kỳ khớp nhau.
7. **Given** một khoản cá nhân chi hộ trả NCC, **When** khoản này được duyệt theo luồng chi hộ hiện có, **Then** công nợ NCC giảm đúng số đã trả.

---

### Edge Cases

- **Người ký đã nghỉ việc hoặc bị khóa tài khoản** giữa vòng ký: bước đó không ký được. Người lập hoặc quản trị chuyển bước đó cho người khác. Danh sách người ký chỉ gồm người đang làm việc, cùng công ty với chứng từ, tài khoản đang hoạt động và đủ quyền.
- **Người ký chưa cài ảnh chữ ký**: đề xuất mua vẫn bắt buộc có ảnh, như hiện nay. Chứng từ khác ký bằng tên, và PDF ghi "Đã ký điện tử: <họ tên>, <giờ ký>".
- **Phiên đăng nhập hết hạn giữa lúc ký**: người ký đăng nhập lại rồi quay về đúng chứng từ đang mở; chữ ký chưa được ghi cho đến khi bấm xác nhận lại.
- **Chứng từ bị sửa sau khi đã có chữ ký**: vòng ký cũ hết hiệu lực và vòng mới bắt đầu lại từ người lập. Chữ ký cũ vẫn giữ trong lịch sử.
- **Một người ký cùng một bước trên hai thiết bị cùng lúc**: chỉ một chữ ký được ghi; thiết bị kia thấy "đã ký".
- **Mất mạng sau khi bấm Ký**: bấm lại không tạo chữ ký thứ hai.
- **Tạo PDF bị lỗi ở bước ký cuối**: bước ký đó không được ghi, hệ thống báo lỗi, và người ký ký lại được.
- **Đơn đã nhận một phần rồi bị hủy**: chỉ đóng phần chưa nhận; phần đã nhận giữ nguyên.
- **Trả hàng sau khi đã trả tiền**: công nợ đảo chiều, hiện thành khoản NCC phải hoàn hoặc cấn trừ lần mua sau.
- **Hóa đơn và phiếu nhận không một-một**: một hóa đơn gộp nhiều phiếu nhận hoặc nhiều đơn; một phiếu nhận có nhiều hóa đơn.
- **Hóa đơn của NCC có mã số thuế chưa có trong danh mục**: hệ thống không tự tạo NCC. Người nhập chọn NCC sẵn có (và bổ sung mã số thuế) hoặc tạo NCC mới qua biểu mẫu NCC.
- **Báo giá đã gồm thuế**: phải tách đúng thuế trước khi lập đơn, như hiện nay.
- **Tài sản mua theo từng chiếc**: giữ nguyên cách làm hiện có.
- **Ngày chứng từ khác ngày ký**: ngày chứng từ chọn được nếu có quyền; giờ ký luôn là giờ máy chủ, không sửa được.
- **Màn 320px**: không tràn ngang; popup không bị header hay thanh điều hướng dưới che.

## Requirements *(mandatory)*

### Functional Requirements

#### Chung

- **FR-001**: Mọi thao tác trong Ma trận thao tác (bên dưới) MUST làm được trên cả điện thoại và máy tính, trừ các ngoại lệ ghi rõ trong ma trận.
- **FR-002**: Không thao tác nào trong luồng mua hàng được dẫn người dùng sang ERPNext Desk.
- **FR-003**: Mỗi loại chứng từ MUST có một bộ tên trạng thái duy nhất (xem Key Entities). Bộ tên này dùng giống nhau ở Kho, Mua hàng, Tài chính, trên điện thoại, trên máy tính và trên bản in.
- **FR-004**: Liên kết từ thông báo, email, phần tiến độ và chứng từ liên quan MUST mở đúng chứng từ trên thiết bị đang dùng: trên điện thoại thì mở trong app điện thoại, trên máy tính thì mở trong màn máy tính.
- **FR-005**: Chứng từ mua hàng hiện có là nguồn số liệu duy nhất. Công nợ, tiến độ và tuổi nợ MUST tính từ chứng từ và sổ kế toán, không nhập tay, không lưu sổ song song.
- **FR-006**: Danh sách MUST lọc được theo NCC, kho, khoảng ngày và trạng thái, và tìm được theo số chứng từ hoặc tên hàng. Chi tiết và nhập liệu mở trong hộp thoại, không trải bảng nhập ra trang.
- **FR-007**: Mọi thao tác ghi MUST chống gửi trùng: bấm lại, hoặc thử lại sau khi mất mạng, không tạo bản ghi thứ hai. Thao tác ghi gồm lưu, gửi, ký, nhận hàng, ghi hóa đơn và lập phiếu chi.
- **FR-008**: Máy chủ MUST kiểm tra lại quyền, trạng thái và phiên bản chứng từ ở mọi thao tác. Ẩn nút trên giao diện không thay cho bước kiểm tra này.
- **FR-009**: Toàn bộ chữ hiển thị MUST là tiếng Việt và dùng thống nhất "Đề xuất mua", không lẫn với "Đề nghị".
- **FR-010**: Khi người dùng rời biểu mẫu chưa lưu, hệ thống MUST hỏi xác nhận.

#### Ký điện tử

- **FR-011**: Hộp **Chờ tôi ký** MUST có trên mọi app điện thoại Lotus mà người dùng được vào, và trên máy tính. Hộp liệt kê mọi chứng từ đang đến lượt người dùng ký. Mỗi dòng có loại, số, người lập, số tiền, bước ký và ngày gửi. Menu hoặc biểu tượng của hộp hiện số đếm.
- **FR-012**: Ký MUST dùng phiên đăng nhập hiện tại, không đòi mã, vân tay hay chứng thư. Trước khi ghi chữ ký, hệ thống MUST hiện hộp xác nhận nêu loại chứng từ, số, số tiền và bước ký. Ký nhiều chứng từ thì xác nhận một lần cho cả lượt.
- **FR-013**: Mỗi lần ký MUST ghi lại:
  - người ký, chức danh và vai trò lúc ký;
  - bước ký;
  - giờ máy chủ;
  - thiết bị và trình duyệt;
  - địa chỉ mạng;
  - phiên bản ảnh chữ ký;
  - dấu vân tay nội dung chứng từ.
- **FR-014**: Khi bước cuối được ký, hệ thống MUST lưu một bản PDF cố định, không tạo lại. Bản này có chữ ký từng bước, họ tên, chức danh, giờ ký và QR xác minh. QR xác minh so với dấu vân tay của chính bản lưu. Nếu tạo PDF lỗi, bước ký cuối không được ghi.
- **FR-015**: FR-011 đến FR-014 áp dụng cho đề xuất mua, đơn mua và phiếu chi (mọi phiếu chi đang đi chuỗi ký phiếu chi). Phiếu nhập kho theo đơn có chữ ký thủ kho ngay lúc xác nhận (FR-043), nên bản PDF của nó được lưu ngay khi xác nhận.
- **FR-016**: **Trả lại** (lý do ít nhất 3 ký tự) và **Chuyển người ký** (có lý do, người nhận phải đủ điều kiện) MUST có trên cả hai giao diện cho mọi loại chứng từ có ký.
- **FR-017**: **Ký nhiều**: người dùng chọn nhiều chứng từ đang đến lượt mình và xác nhận một lần. Hệ thống kiểm tra và ghi từng chứng từ riêng, rồi báo kết quả theo từng chứng từ.
- **FR-018**: Mục **Chữ ký của tôi** MUST có trên cả hai giao diện, gồm:
  - ảnh chữ ký: tải lên, cắt, tách nền, hoặc vẽ tay;
  - ký nháy;
  - định dạng ngày.
- **FR-019**: Mọi bước chốt (xác nhận, ghi sổ) MUST kiểm tra đủ chữ ký của đúng người được chỉ định, kể cả khi thao tác đi qua đường khác ngoài màn Lotus.
- **FR-020**: Mọi đơn mua MUST chờ người duyệt được chỉ định (giám đốc) ký mới được duyệt. Không còn tự duyệt theo chính sách, kể cả khi đơn đúng đề xuất đã ký đủ và chọn giá rẻ nhất.
- **FR-021**: Gửi thông báo đến lượt ký MUST NOT làm hỏng thao tác ký. Nếu gửi thông báo lỗi, hệ thống chỉ ghi nhật ký.
- **FR-022**: Các đường ký không hoạt động (ký bằng QR trên thiết bị khác, nút ký nháy riêng của đơn mua) MUST bị gỡ. QR trên chứng từ chỉ dùng để xác minh.
- **FR-023**: Bản PDF đã ký dài nhiều trang MUST có ký nháy ở chân mỗi trang, lấy của người ký bước kiểm tra (mua hàng hoặc kế toán) nếu người đó đã cài ký nháy.
- **FR-024**: Đổi hoặc xóa ảnh chữ ký MUST NOT làm thay đổi chữ ký trên các chứng từ đã ký.

#### Đề xuất mua

- **FR-025**: App Mua hàng, app Kho, màn Kho và màn Mua hàng trên máy tính MUST dùng chung một biểu mẫu đề xuất.
- **FR-026**: Bảng đề xuất MUST chia theo giai đoạn: Nháp, Chờ tôi ký, Đang ký, Bị trả lại, Chờ mua, Đang mua, Đã nhận đủ, Đã xong, Đã hủy, mỗi giai đoạn có số đếm. Giai đoạn tính từ chữ ký và tiến độ từng dòng, không nhập tay.
- **FR-027**: Người được chỉ định ký MUST luôn xem được chứng từ mình phải ký, kể cả khi không có quyền xem danh sách.
- **FR-028**: Chi tiết đề xuất MUST có:
  - các dòng hàng;
  - tiến độ từng dòng (đã đặt, đã nhận, đã có hóa đơn, đã trả tiền), bấm vào mở được chứng từ liên quan;
  - chuỗi chữ ký;
  - file đính kèm;
  - bản PDF.
- **FR-029**: Người có quyền MUST làm được các việc sau, mỗi việc có lý do:
  - đóng phần chưa mua của đề xuất đã duyệt;
  - hủy đề xuất chưa có dòng nào được đặt.

  Người lập MUST xóa được đề xuất còn ở dạng nháp.
- **FR-030**: Khi mọi dòng đã nhận đủ hoặc đã đóng, đề xuất MUST tự chuyển sang "Đã nhận đủ". Khi thêm điều kiện mọi phần đã nhận đều đã có hóa đơn, đề xuất MUST tự chuyển sang "Đã xong". Đơn mua bị đóng phần chưa giao được tính là đóng phần đó của đề xuất.
- **FR-031**: Đề xuất nhập từ Excel còn thiếu lý do MUST được hỏi lý do ngay lúc ký và gửi.

#### Báo giá và đơn mua

- **FR-032**: Lập đơn từ đề xuất MUST giữ NCC và giá của báo giá đã chọn, không đặt lại giá về 0.
- **FR-033**: Trên điện thoại, so sánh giá MUST hiện theo từng mặt hàng, mỗi báo giá là một thẻ. Người dùng chọn báo giá ngay trên thẻ, và phải ghi lý do nếu không chọn giá thấp nhất.
- **FR-034**: Báo giá đã lưu MUST sửa được; báo giá chưa dùng MUST hủy được.
- **FR-035**: Với đơn nháp hoặc đơn bị trả lại, người dùng MUST sửa, xóa nháp và gửi duyệt (chọn người duyệt) được trên cả hai giao diện, kể cả từ app Kho.
- **FR-036**: Ngay khi lưu, hệ thống MUST báo trước dòng nào sẽ bị chặn lúc duyệt và vì sao, ví dụ dòng không thuộc đề xuất đã duyệt hoặc vượt số còn lại.
- **FR-037**: Duyệt và Trả lại đơn MUST có trên cả hai giao diện. Lý do trả lại hiện ở chi tiết và ở danh sách.
- **FR-038**: Với đơn đã duyệt, các thao tác sau MUST có trên cả hai giao diện:
  - in, tải hoặc chia sẻ bản PDF đã lưu;
  - đánh dấu đã gửi NCC, NCC đã xác nhận;
  - đổi hẹn giao;
  - đóng phần chưa giao;
  - hủy (khi chưa nhận hàng, có lý do).
- **FR-039**: Danh sách đơn MUST hiện trạng thái theo bộ tên chung và cột tiến độ hóa đơn, trả tiền.
- **FR-040**: Người chỉ có vai trò mua hàng MUST lập đơn từ bảng so sánh giá và gửi duyệt được, không báo lỗi quyền.

#### Nhập kho

- **FR-041**: Nhận theo đơn trên cả điện thoại và máy tính MUST cho nhập số thực nhận từng dòng, nhận một phần, ghi chi phí phát sinh, chụp ảnh (hàng, phiếu giao, hóa đơn) và ghi chú.
- **FR-042**: Phiếu nhập theo đơn MUST có ít nhất một trong hai: chữ ký tay của người giao hàng trên màn hình kèm họ tên, hoặc ảnh phiếu giao hàng có chữ ký. Thiếu cả hai thì không xác nhận được. Chữ ký tay hoặc ảnh này in trên phiếu nhập.
- **FR-043**: Bấm xác nhận nhập kho theo đơn MUST đồng thời là chữ ký của thủ kho (người xác nhận), trên cả hai giao diện. Không còn bước ký riêng sau khi nhập kho. Bản in phiếu nhập có chữ ký và QR.
- **FR-044**: Trả hàng MUST lập và xác nhận được ngay trong Lotus. Nếu phiếu nhập gốc đã có hóa đơn, hệ thống nhắc lập hóa đơn điều chỉnh.
- **FR-045**: Từ cả Kho và Mua hàng, người dùng MUST:
  - hủy phiếu nhập, nếu có quyền quản lý kho và ghi lý do;
  - xóa phiếu nháp;
  - in phiếu;
  - xem và thêm đính kèm.
- **FR-046**: Hệ thống MUST chặn nhận vượt số còn chờ, kể cả khi hai người nhận cùng lúc.
- **FR-047**: Mọi phiếu nhập mua chưa có hóa đơn, dù theo đơn hay Mua nhanh, MUST hiện ở Hóa đơn chờ nhập và trong công nợ ở phần "hàng đã nhận, chưa có hóa đơn". Phiếu Mua nhanh không có giới hạn tiền và không cần ký, nhưng MUST mang nhãn "Mua nhanh" ở mọi danh sách: nhập kho, hóa đơn chờ nhập, công nợ, tiến độ.

#### Hóa đơn NCC

- **FR-048**: Danh sách **Hóa đơn chờ nhập** MUST gom file và ảnh hóa đơn đã đính kèm ở phiếu nhận, cùng các phiếu nhập chưa có hóa đơn.
- **FR-049**: Hóa đơn MUST được nhập tay. Hệ thống điền sẵn các dòng từ phiếu nhận và đơn mua đã chọn: số lượng chưa lập hóa đơn, đơn giá theo đơn. Hệ thống không đọc số từ file XML, PDF hay ảnh. File gốc đính kèm làm bằng chứng và MUST xem được ngay trong lúc nhập.
- **FR-050**: Hệ thống MUST ghép được:
  - một hóa đơn với một hoặc nhiều phiếu nhận, kể cả phiếu Mua nhanh;
  - một phiếu nhận với nhiều hóa đơn.

  Hóa đơn dịch vụ không cần phiếu nhận.
- **FR-051**: Hệ thống MUST hiện chênh lệch số lượng và đơn giá giữa hóa đơn, phiếu nhận và đơn mua. Mỗi chênh lệch phải có lý do. Giá vốn lấy theo hóa đơn.
- **FR-052**: Hóa đơn MUST giữ đủ các thông tin sau đúng như bản in:
  - ký hiệu, số, ngày, mã của cơ quan thuế (nếu có);
  - tiền hàng;
  - thuế GTGT từng dòng (nhiều thuế suất trong một hóa đơn);
  - chi phí;
  - tổng thanh toán.

  Thuế GTGT đầu vào tính vào giá vốn, theo cách đang áp dụng cho hộ kinh doanh.
- **FR-053**: Mọi đường lập hóa đơn MUST chặn trùng theo cặp NCC + ký hiệu + số.
- **FR-054**: Nếu tổng các dòng lệch tổng in không quá 1 đồng mỗi dòng hàng, hóa đơn MUST ghi theo tổng in, phần lệch đưa vào giá vốn và hiện rõ. Nếu lệch lớn hơn, hệ thống chặn và báo dòng nghi sai.
- **FR-055**: Người dùng MUST:
  - hủy được hóa đơn chưa có thanh toán, có lý do;
  - lập hóa đơn điều chỉnh khi trả hàng hoặc được giảm giá;
  - in hóa đơn đã nhập, kèm file gốc.
- **FR-056**: Kế toán MUST nhập và ghi được hóa đơn trên điện thoại, kể cả chụp hoặc tải file gốc. Người mua hàng và thủ kho chỉ đính kèm file và xem.

#### Công nợ và trả tiền NCC

- **FR-057**: Công nợ tại ngày chốt, theo từng NCC, MUST gồm:
  - nợ theo hóa đơn;
  - hàng đã nhận nhưng chưa có hóa đơn (tạm tính theo giá phiếu nhận, hiện riêng);
  - tạm ứng;
  - số còn phải trả.

  Phần nợ theo hóa đơn khớp sổ kế toán phải trả đến từng đồng.
- **FR-058**: Tuổi nợ MUST tính theo hạn trả, chia nhóm: chưa đến hạn, quá hạn 1–30, 31–60, 61–90, trên 90 ngày. Kèm danh sách khoản đến hạn trong 7 ngày tới.
- **FR-059**: Sổ chi tiết công nợ từng NCC theo khoảng ngày MUST có số đầu kỳ, hóa đơn, phiếu chi, trả hàng hoặc điều chỉnh, tạm ứng, số cuối kỳ. Từng chứng từ trong sổ mở được. Từ sổ in hoặc xuất được biên bản đối chiếu công nợ.
- **FR-060**: Lập phiếu chi từ màn công nợ MUST cho:
  - chọn một hoặc nhiều hóa đơn của một NCC, hoặc chi tạm ứng theo đơn;
  - chọn chuyển khoản hoặc tiền mặt;
  - ghi số tham chiếu ngân hàng;
  - đính kèm chứng từ ngân hàng.

  Không được chi vượt số còn nợ, trừ khi ghi rõ phần vượt là tạm ứng.
- **FR-061**: Phiếu chi MUST đi chuỗi ký: kế toán → kế toán trưởng → giám đốc. Ký đủ thì ghi sổ. Phiếu chi in theo mẫu, có chữ ký và QR.
- **FR-062**: Kế toán trưởng MUST đảo được phiếu chi đã ghi sổ, có lý do, từ cả màn Mua hàng và màn Tài chính.
- **FR-063**: Kế toán, kế toán trưởng và giám đốc MUST xem được công nợ, tuổi nợ và sổ chi tiết trên điện thoại.
- **FR-064**: Liên kết phiếu chi trong phần tiến độ của đề xuất và đơn mua MUST mở đúng phiếu chi.

### Ma trận thao tác (trạng thái cần đạt)

| Nhóm | Thao tác | Điện thoại | Máy tính |
|------|----------|------------|----------|
| Ký | Chờ tôi ký; ký; trả lại; chuyển người ký; ký nhiều | Có | Có |
| Ký | Chữ ký của tôi: ảnh chữ ký, ký nháy, định dạng ngày | Có | Có |
| Đề xuất | Lập, sửa, ký và gửi, xóa nháp, hủy, đóng phần chưa mua, in hoặc chia sẻ PDF, xem tiến độ | Có | Có |
| Đề xuất | Nhập từ Excel | Không | Có |
| Báo giá | Thêm và sửa (có máy đọc), xác nhận, so sánh và chọn, hủy | Có | Có |
| Báo giá | Nhập từ Excel | Không | Có |
| Đơn mua | Lập, sửa, xóa nháp, gửi duyệt, duyệt, trả lại, in hoặc chia sẻ PDF, đánh dấu đã gửi NCC, NCC xác nhận, đổi hẹn, đóng phần chưa giao, hủy | Có | Có |
| Nhập kho | Nhận theo đơn (một phần, chi phí, ảnh, chữ ký người giao), xác nhận, ký, in, trả hàng, hủy, xóa nháp, đính kèm | Có | Có |
| Hóa đơn NCC | Hóa đơn chờ nhập, nhập tay có file gốc bên cạnh, ghép phiếu nhận, xử lý chênh lệch, ghi, hủy, điều chỉnh, in, đính kèm | Có | Có |
| Công nợ | Công nợ tại ngày chốt, tuổi nợ, đến hạn, sổ chi tiết, biên bản đối chiếu (xem và in) | Có | Có |
| Công nợ | Xuất Excel | Không | Có |
| Trả tiền | Lập phiếu chi cho một hoặc nhiều hóa đơn, tạm ứng, chi hộ, ký, in phiếu chi, đảo phiếu | Có | Có |
| Trả tiền | Cấu hình tài khoản chi hộ | Không | Có |

### Key Entities *(include if feature involves data)*

- **Đề xuất mua**: nhu cầu mua của một bộ phận, gồm lý do, kho nhận và các dòng (vật tư, số lượng, ngày cần, giá dự kiến). Trạng thái: Nháp · Đang ký · Bị trả lại · Chờ mua · Đang mua · Đã nhận đủ · Đã xong · Đã hủy.
  - "Chờ tôi ký" là một cách lọc, không phải trạng thái.
  - "Đã nhận đủ": mọi dòng đã nhận hoặc đã đóng, nhưng còn hàng đã nhận chưa có hóa đơn.
  - "Đã xong": như trên, và mọi phần đã nhận đều đã có hóa đơn.
- **Báo giá**: giá của một NCC cho các dòng đề xuất, quy về đơn vị tính của kho, có thuế, phí vận chuyển và hạn giao. Trạng thái: Nháp · Đã xác nhận · Đã chọn · Đã hủy.
- **Đơn mua**: cam kết mua với một NCC, có người duyệt được chỉ định. Trạng thái: Nháp · Chờ duyệt · Bị trả lại · Đã duyệt · Đã gửi NCC · NCC đã xác nhận · Đang nhận · Đã nhận đủ · Đã đóng · Đã hủy.
- **Phiếu nhận hàng (nhập kho)**: số thực nhận theo đơn, hoặc nhập Mua nhanh, kèm chi phí và ảnh. Phiếu theo đơn có thêm xác nhận của người giao hàng (chữ ký tay kèm họ tên, hoặc ảnh phiếu giao có chữ ký) và chữ ký thủ kho lúc xác nhận.
  - Trạng thái phiếu: Nháp · Đã nhập kho · Đã hủy.
  - Tình trạng hóa đơn: Chưa có hóa đơn · Có hóa đơn một phần · Đã có hóa đơn · Đã trả hết hàng (không cần hóa đơn).
- **Phiếu trả hàng**: phần hàng trả lại NCC, gắn với phiếu nhận gốc.
- **Hóa đơn NCC**: hóa đơn của NCC đã ghi sổ, gồm ký hiệu, số, ngày, hạn trả, các dòng, thuế, tổng in, file gốc và liên kết tới phiếu nhận hoặc đơn mua. Trạng thái: Chưa trả · Trả một phần · Đã trả · Quá hạn · Đã hủy. Hóa đơn điều chỉnh gắn với hóa đơn gốc.
- **Hóa đơn chờ nhập**: file hoặc ảnh hóa đơn đã đính kèm, hoặc phiếu nhập chưa có hóa đơn, đang chờ kế toán ghi.
- **Phiếu chi**: khoản trả cho NCC (một hoặc nhiều hóa đơn, tạm ứng, hoặc hoàn chi hộ), qua chuỗi ký 3 bước. Trạng thái: Nháp · Đang ký · Bị trả lại · Đã chi · Đã đảo.
- **Công nợ NCC**: số tính ra từ hóa đơn, phiếu chi, trả hàng và tạm ứng tại một ngày chốt, kèm phần hàng đã nhận chưa có hóa đơn. Không nhập tay.
- **Vòng ký và bước ký**: thứ tự người ký của một chứng từ. Mỗi bước có người được chỉ định, trạng thái (Chưa đến lượt · Chờ ký · Đã ký · Trả lại), giờ ký và dấu vân tay nội dung. Sửa chứng từ thì mở vòng mới.
- **Nhật ký ký**: mọi lần ký, trả lại và chuyển người ký, kèm người làm, vai trò, giờ máy chủ, thiết bị và địa chỉ mạng.
- **Bản PDF đã ký**: bản cố định lưu khi đủ chữ ký, có dấu vân tay riêng, là thứ QR xác minh đối chiếu.
- **Hồ sơ chữ ký của người dùng**: ảnh chữ ký, ký nháy, định dạng ngày.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% thao tác trong Ma trận thao tác chạy được trên điện thoại (màn 320–390px) và máy tính, trừ 4 ngoại lệ ghi trong ma trận.
- **SC-002**: Với 100% loại chứng từ có ký, từ thông báo đến màn ký của đúng chứng từ chỉ mất 1 lần chạm.
- **SC-003**: Trên điện thoại, người ký hoàn tất một lần ký (xem, xác nhận, ký) trong không quá 30 giây, tính từ lúc bấm thông báo.
- **SC-004**: Sau khi phát hành, không có đề xuất, đơn mua hay phiếu chi nào được chốt mà thiếu chữ ký của đúng người được chỉ định. Kiểm bằng cách rà toàn bộ chứng từ phát sinh sau ngày phát hành.
- **SC-005**: 100% chứng từ ký đủ sau ngày phát hành có bản PDF được lưu, và quét QR của chúng đều báo "khớp bản lưu".
- **SC-006**: Không còn đường dẫn nào sang ERPNext Desk trong luồng đề xuất → trả tiền.
- **SC-007**: Thủ kho nhận xong một đơn 5 dòng, kèm 2 ảnh, trên điện thoại trong không quá 3 phút.
- **SC-008**: Với 100% hóa đơn ghi sổ sau ngày phát hành, tổng ghi sổ khớp tổng in trên hóa đơn (lệch 0 đồng) và có file gốc đính kèm. Kế toán nhập xong một hóa đơn 10 dòng đã có phiếu nhận trong không quá 5 phút.
- **SC-009**: Với 100% NCC, phần công nợ theo hóa đơn tại ngày chốt khớp số dư phải trả trên sổ kế toán, lệch 0 đồng.
- **SC-010**: Không thao tác ghi nào tạo bản ghi trùng khi bấm hai lần hoặc thử lại sau mất mạng. Kiểm bằng bài thử bấm hai lần cho từng thao tác ghi.
- **SC-011**: Giám đốc, kế toán, thủ kho và mua hàng mỗi người tự làm trọn một vòng thử từ đề xuất đến trả tiền, phần việc của mình trên thiết bị mình quen dùng, không cần người khác hỗ trợ.

## Assumptions

- **Loại chữ ký**: ký điện tử nội bộ, gồm ảnh chữ ký, phiên đăng nhập kèm bước xác nhận, nhật ký ký và bản PDF lưu cố định. Đây không phải chữ ký số có chứng thư.
- **Chuỗi ký giữ như đang chạy**:
  - Đề xuất mua: người đề xuất → trưởng bộ phận → mua hàng/kế toán → giám đốc. Đề xuất nhỏ chỉ 2 bước, ở nơi chính sách cho phép.
  - Đơn mua: người lập → giám đốc, cho mọi đơn.
  - Phiếu chi: kế toán → kế toán trưởng → giám đốc.
  - Phiếu nhập theo đơn: thủ kho ký ngay khi xác nhận; người giao hàng ký tay hoặc có ảnh phiếu giao có chữ ký. Các phiếu kho khác, kể cả Mua nhanh, giữ cách ký tùy chọn như hiện nay.
- **Mua nhanh** giữ như hiện nay, không qua đề xuất hay đơn. Spec chỉ bổ sung để phiếu Mua nhanh vào được hóa đơn và công nợ.
- **Hạn trả**: bằng ngày hóa đơn cộng điều khoản thanh toán của NCC. NCC chưa có điều khoản thì hạn trả là chính ngày hóa đơn.
- **Mẫu in phiếu chi**: chi tiền mặt in mẫu phiếu chi; chi chuyển khoản in giấy đề nghị chi có đủ chữ ký, kèm ảnh hoặc file chứng từ ngân hàng.
- **Đối tượng ngoài hệ thống**: người giao hàng và NCC không có tài khoản Lotus, và không có cổng cho NCC.
- **Quy mô**: một trang trại, vài chục chứng từ mua mỗi tuần, khoảng 10–20 người ký, dưới 200 NCC. Mạng ở vườn chập chờn.
- **Chứng từ cũ**: không chuyển hay nhập lại chứng từ lịch sử. Bản PDF cố định chỉ tạo cho chứng từ ký đủ sau ngày phát hành; chứng từ cũ vẫn in như hiện nay.
- **Nền tảng có sẵn**: ảnh chữ ký, chuỗi ký tuần tự, trang xác minh QR công khai, chống gửi trùng, máy đọc chứng từ và thông báo đẩy được dùng lại, không làm mới.
- **Ngoài phạm vi**:
  - chữ ký số có chứng thư (USB token, ký từ xa);
  - ủy quyền ký theo khoảng thời gian (dùng Chuyển người ký cho từng chứng từ);
  - đọc số tự động từ file XML, PDF hoặc ảnh hóa đơn NCC;
  - gửi tin tự động qua Zalo;
  - cổng NCC;
  - đề xuất cấp vật tư (xuất kho), kỳ công và lương. Nếu các chứng từ này có bước đang chờ người dùng ký thì vẫn hiện trong Chờ tôi ký và mở màn hiện có của chúng.
