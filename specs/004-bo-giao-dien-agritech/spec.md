# Feature Specification: Đúc lại bộ giao diện Lotus đạt chuẩn phần mềm nông nghiệp

**Feature Branch**: `004-bo-giao-dien-agritech`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "Đúc lại bộ giao diện cho Lotus gồm bảng, bộ component, CSS, đầy đủ và mở rộng; gợi ý thêm; mở nhánh làm tự do nâng cấp; gọi Spec Kit để làm; phải đạt đẳng cấp agritech."

## Ý tưởng chính

Lotus đang có một bộ giao diện dùng chung nhưng mỏng: khoảng 20 thành phần cơ bản cho máy tính, một bảng dùng chung, bộ bọc cho điện thoại và hơn 40 tệp kiểu viết riêng cho từng phân hệ. Mỗi phân hệ tự làm thẻ, nhãn trạng thái, ô số liệu theo cách của mình. Các màn trông như một trang quản trị thông thường, chưa nói lên đây là phần mềm của một nông trại chuối.

Bản này đúc lại thành **một bộ giao diện duy nhất**, gồm bốn lớp chồng lên nhau:

1. **Nền**: màu, chữ, khoảng cách, bo góc, bóng, chuyển động. Có thêm màu mang nghĩa nghề vườn: màu dây, trạng thái lô, màu khu trên bản đồ, bảng màu cho biểu đồ. Có ba chế độ: sáng, tối và ngoài trời.
2. **Bộ thành phần chung** cho máy tính và điện thoại: đủ các khối thường dùng, mỗi khối đủ trạng thái.
3. **Bảng dữ liệu**: nơi văn phòng làm việc nhiều nhất.
4. **Bộ thành phần nông nghiệp**: thẻ lô, lưới lô, nhãn màu dây, dải tuần, nhãn cách ly, ô số liệu có đơn vị, biểu đồ dự thu.

Đi kèm là một **trang mẫu** để chủ vườn xem và duyệt diện mạo, và bộ **kiểm tra tự động** để các lần sửa sau không làm lệch chuẩn.

Ba điều không đổi:

- Không đổi nghiệp vụ, số liệu, quyền hạn, trạng thái chứng từ hay cách ký.
- Đỏ Lotus vẫn là màu chính duy nhất.
- Các quy ước bố cục chủ vườn đã chốt vẫn giữ: nút tạo mới đứng đầu bên trái, không thêm tiêu đề hay mô tả trang trí phía trên bảng, nhập liệu và số tổng hợp dùng thẻ và hộp nhập thay vì trải cả bảng trên trang.

## Clarifications

### Session 2026-11-10

Chủ vườn giao "làm tự do", nên các điểm dưới đây do người làm tự quyết. Chủ vườn có thể đổi bất kỳ điểm nào khi xem trang mẫu.

- Q: Màu chính có đổi không? → A (tự quyết): Không. Giữ Đỏ Lotus theo quy ước ngày 19/10/2026. Xanh lá, vàng, xanh dương, nâu đất chỉ dùng khi mang nghĩa (đạt, cảnh báo, thông tin, đất vườn) và cho dữ liệu.
- Q: Làm đến đâu trong đợt này? → A (tự quyết): Làm đủ nền, bộ thành phần máy tính và điện thoại, bảng, bộ nông nghiệp và trang mẫu. Áp vào khung chung và các màn vườn, buồng, thu hoạch, dự thu. Các phân hệ khác đổi diện mạo qua lớp dùng chung; việc chuyển hẳn từng màn làm theo thứ tự ở User Story 7.
- Q: Nhánh này tách từ đâu? → A (tự quyết): Từ nhánh `002-cham-soc-thu-hoach-du-thu`, vì các màn vườn, buồng, thu hoạch mới nằm ở đó và các màn cũ đã bị xóa ở đó. Bản này vì vậy ra sau bản 002.
- Q: Có thêm thư viện giao diện mới không? → A (tự quyết): Không. Dùng tiếp các thư viện đang có cho máy tính, điện thoại, bảng, biểu đồ và bản đồ.
- Q: Chế độ ngoài trời bật thế nào? → A (tự quyết): Người dùng tự bật bằng một nút trên điện thoại, máy nhớ lựa chọn. Không tự bật theo cảm biến ánh sáng.
- Q: Số liệu trong trang mẫu lấy ở đâu? → A (tự quyết): Là số mẫu, có ghi rõ "dữ liệu mẫu" trên trang. Trang mẫu không đọc và không ghi dữ liệu thật.
- Q: Đặt nút chọn mật độ bảng ở đâu? → A (tự quyết, theo `AGENTS.md`): Ở menu tài khoản trên thanh trên, áp cho mọi bảng. Không đặt phía trên bảng.
- Q: Thanh dưới của điện thoại có chữ dưới biểu tượng không? → A (tự quyết, đổi so với chuẩn 17/10/2026 vốn chỉ có biểu tượng): Có. Người vườn đọc chữ nhanh hơn đoán biểu tượng, nhất là ngoài nắng. Chủ vườn duyệt điểm này ở trang mẫu; nếu không đồng ý thì giữ chỉ biểu tượng.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Một diện mạo thống nhất trên mọi màn hình (Priority: P1)

Người dùng mở bất kỳ màn nào trên máy tính hay điện thoại đều thấy cùng một hệ màu, chữ, khoảng cách và cùng một cách thể hiện trạng thái. Chứng từ đang "Chờ duyệt" thì ở Kho, Mua hàng hay Tài chính đều có cùng nhãn, cùng màu, cùng biểu tượng. Chuyển giữa sáng và tối không còn mảng nào sai màu. Nút nguy hiểm (xóa, hủy chứng từ) nhìn khác hẳn nút chính, dù màu chính của Lotus là đỏ.

**Why this priority**: Đây là lớp nền. Bảng, thành phần và mọi màn hình đều dựng trên lớp này. Áp xong lớp này thì toàn bộ màn hiện có đã đổi diện mạo mà chưa phải sửa từng màn.

**Independent Test**: Mở trang mẫu và hai màn tiêu biểu của mỗi phân hệ ở chế độ sáng rồi tối. So nhãn của cùng một trạng thái ở ba phân hệ. Chạy kiểm tra tương phản tự động trên toàn bộ cặp chữ và nền.

**Acceptance Scenarios**:

1. **Given** một chứng từ đang "Chờ duyệt", **When** xem nó ở Kho, Mua hàng và Tài chính, **Then** nhãn trạng thái có cùng chữ, cùng màu và cùng biểu tượng.
2. **Given** một màn đang ở chế độ sáng, **When** người dùng chuyển sang tối, **Then** không còn vùng nền trắng chói, chữ chìm vào nền hay đường viền biến mất.
3. **Given** người dùng chỉ dùng bàn phím, **When** chuyển qua các nút và ô nhập, **Then** luôn thấy viền chỉ vị trí đang đứng.
4. **Given** nút "Xóa" hoặc "Hủy chứng từ" đứng cạnh nút chính "Lưu", **When** người dùng nhìn lướt, **Then** phân biệt được hai nút nhờ kiểu nút và biểu tượng, không phải chỉ nhờ màu.
5. **Given** một màn chưa được chuyển sang bộ mới, **When** mở nó sau khi áp nền mới, **Then** bố cục không vỡ và mọi thao tác chạy như trước.
6. **Given** người dùng đã bật "giảm chuyển động" trên máy, **When** mở hộp thoại hoặc menu, **Then** không có hiệu ứng trượt hay mờ dần.
7. **Given** một trạng thái được thể hiện bằng màu (đạt, cảnh báo, nguy, thông tin), **When** người mù màu đỏ và lục nhìn, **Then** vẫn hiểu đúng nhờ chữ hoặc biểu tượng đi kèm.

---

### User Story 2 - Bảng dữ liệu gọn, đọc số nhanh (Priority: P1)

Kế toán, thủ kho, nhân sự và thống kê làm việc chủ yếu trên bảng. Trong bảng mới, số canh phải với chữ số thẳng cột và có đơn vị. Trạng thái là nhãn màu. Ngày quá hạn nổi bật. Tiêu đề cột và dòng tổng luôn đứng yên khi cuộn. Người dùng chọn mật độ gọn hoặc thoáng. Bảng trống và bảng đang tải có hình dạng rõ ràng. Trên điện thoại, mỗi dòng thành một thẻ. Cách lọc kiểu Excel, ẩn hiện cột, chế độ xem đã lưu, phân trang và xuất Excel giữ nguyên.

**Why this priority**: Phần lớn màn máy tính là bảng. Bảng đẹp và dễ đọc thì cả phần văn phòng của Lotus đổi khác.

**Independent Test**: Mở phần Bảng của trang mẫu với ba bộ dữ liệu mẫu (0 dòng, 20 dòng, 5.000 dòng), đổi mật độ, lọc, cuộn, thu hẹp về bề rộng điện thoại. Chạy lại toàn bộ kiểm tra tự động của bảng hiện có.

**Acceptance Scenarios**:

1. **Given** bảng có cột tiền và cột số lượng, **When** hiển thị, **Then** số canh phải, chữ số thẳng cột, có dấu tách nghìn và đơn vị theo cột. Riêng bảng Kho giữ kiểu căn giữa đã nghiệm thu, chữ số vẫn thẳng cột.
2. **Given** bảng có cột trạng thái, **When** hiển thị, **Then** mỗi ô là một nhãn trạng thái theo bảng từ vựng chung của User Story 1.
3. **Given** bảng dài hơn màn hình, **When** cuộn, **Then** tiêu đề cột và dòng tổng đứng yên.
4. **Given** người dùng đổi mật độ từ thoáng sang gọn ở menu tài khoản, **When** mở bất kỳ bảng nào, kể cả lần sau, **Then** bảng ở mật độ gọn và số dòng thấy được nhiều hơn. Phía trên bảng không có nút chọn mật độ.
5. **Given** bảng không còn dòng nào sau khi lọc, **When** hiển thị, **Then** có trạng thái trống kèm nút "Xóa bộ lọc". **Given** chưa có dữ liệu và người dùng có quyền tạo, **Then** trạng thái trống kèm nút tạo mới.
6. **Given** bảng đang tải, **When** chờ, **Then** hiện khung chờ có dạng dòng, và bố cục không nhảy khi dữ liệu về.
7. **Given** mở bảng trên điện thoại, **When** hiển thị, **Then** mỗi dòng là một thẻ có tiêu đề, hai đến bốn thông tin chính và nhãn trạng thái; không phải cuộn ngang.
8. **Given** cột tiến độ, màu dây, người hoặc hạn, **When** hiển thị, **Then** ô có thanh tiến độ, chấm màu dây, tên kèm chữ cái đầu, hoặc ngày kèm "quá n ngày".
9. **Given** các bảng hiện có, **When** chuyển sang diện mạo mới, **Then** lọc, sắp xếp, ẩn hiện cột, chế độ xem đã lưu, chọn dòng, phân trang và xuất Excel cho cùng kết quả như trước.

---

### User Story 3 - Bộ thành phần máy tính đầy đủ (Priority: P1)

Người làm màn hình mới có sẵn mọi khối cần dùng, không phải viết kiểu riêng. Người dùng thấy cùng một loại việc thì cùng một cách làm ở mọi phân hệ. Bộ này gồm:

- **Hành động**: nút (chính, phụ, viền, mờ, nguy hiểm; ba cỡ; có biểu tượng; đang tải), nhóm nút, nút chỉ có biểu tượng kèm chú thích, menu thao tác.
- **Nhập liệu**: ô chữ, số, tiền, ngày, tháng, khoảng ngày, vùng chữ dài, ô tìm chọn, chọn nhiều, tệp và ảnh, hộp kiểm, chọn một, công tắc, chọn theo đoạn, kèm nhãn, gợi ý và lỗi theo từng ô.
- **Hiển thị**: nhãn trạng thái, thẻ, ô số liệu, danh sách cặp tên và giá trị cho chi tiết chứng từ, chữ cái đại diện cho người, thanh và vòng tiến độ, dòng thời gian, các bước của một quy trình, cây thư mục.
- **Phản hồi**: dải thông báo trong trang (thông tin, đạt, cảnh báo, nguy), thông báo nổi, khung chờ, trạng thái trống, trạng thái lỗi kèm nút thử lại.
- **Lớp nổi**: hộp thoại, ngăn kéo cạnh, menu, chú thích, hộp nổi, hộp xác nhận.
- **Điều hướng và bố cục**: thẻ chuyển mục (tab), phân trang, thanh công cụ danh sách, thanh lọc, phần gập mở, bảng tìm nhanh.

**Why this priority**: Không có đủ khối thì người làm lại viết riêng, và sự lệch chuẩn quay lại.

**Independent Test**: Trong trang mẫu, dựng một trang danh sách có nút tạo, thanh lọc, bảng và hộp nhập, chỉ bằng thành phần của bộ. Đi hết bằng bàn phím.

**Acceptance Scenarios**:

1. **Given** người làm cần một trang danh sách có nút tạo, lọc, bảng và hộp nhập, **When** dựng bằng bộ thành phần, **Then** không phải viết thêm kiểu riêng nào.
2. **Given** một thành phần bấm được, **When** xem trong trang mẫu, **Then** có đủ trạng thái thường, rê chuột, đang bấm, đang đứng, vô hiệu, và đang tải nếu có nghĩa.
3. **Given** hộp thoại đang mở, **When** bấm Esc hoặc Tab, **Then** Esc đóng hộp, Tab không thoát ra ngoài hộp, và đóng xong con trỏ về lại nút đã mở.
4. **Given** một ô nhập sai, **When** người dùng rời ô hoặc bấm lưu, **Then** lỗi hiện ngay dưới ô kèm biểu tượng và trình đọc màn hình đọc được.
5. **Given** cần báo một điều trong trang (đã khóa sổ, thiếu dữ liệu, mất mạng), **When** hiển thị, **Then** dùng dải thông báo một trong bốn mức, kèm hành động nếu có.
6. **Given** một chứng từ có nhiều bước ký, **When** xem chi tiết, **Then** các bước hiện bằng thành phần "các bước" với người, giờ và trạng thái từng bước.

---

### User Story 4 - Điện thoại dùng được ngoài vườn (Priority: P2)

Tổ trưởng, đội trưởng và thủ kho dùng điện thoại ngoài nắng, tay bẩn hoặc đeo găng, mạng yếu. Bộ điện thoại có chế độ ngoài trời: tương phản cao, chữ to và đậm hơn, vùng bấm lớn. Nhập số có nút cộng trừ lớn. Mất mạng thì có dải báo, việc đã nhập hiện "chờ gửi". Thanh dưới có chữ dưới biểu tượng. Có sẵn thẻ, dòng danh sách, ô số liệu, nhãn, khung chờ, trạng thái trống.

**Why this priority**: Số liệu vườn vào hệ thống từ điện thoại. Màn khó nhìn ngoài nắng thì tổ trưởng nhập sai hoặc không nhập.

**Independent Test**: Mở phần Điện thoại của trang mẫu ở bề rộng 320px và 390px, bật chế độ ngoài trời, đo tương phản và kích thước vùng bấm. Mở ứng dụng Công việc ở bề rộng 320px và nhập thử một lô.

**Acceptance Scenarios**:

1. **Given** tổ trưởng đang đứng ngoài nắng, **When** bật chế độ ngoài trời, **Then** chữ chính đạt tương phản từ 7:1, chữ to và đậm hơn, vùng bấm từ 48px, và máy nhớ lựa chọn này.
2. **Given** ô nhập số buồng, **When** bấm vào, **Then** có nút trừ và cộng lớn hai bên và bàn phím số; giữ nút thì số tăng nhanh.
3. **Given** điện thoại mất mạng, **When** người dùng đang ở bất kỳ màn nào, **Then** có dải báo "Đang ngoại tuyến" cố định; có mạng lại thì dải báo đổi thành "Đã có mạng" rồi tự ẩn.
4. **Given** màn rộng 320px, **When** mở bất kỳ màn mẫu nào, **Then** không tràn ngang và thanh dưới có chữ dưới mỗi biểu tượng.
5. **Given** một danh sách đang tải hoặc không có gì, **When** hiển thị, **Then** có khung chờ hoặc trạng thái trống theo cùng kiểu với máy tính.
6. **Given** hộp nhập mở từ dưới lên, **When** bàn phím hiện ra, **Then** ô đang nhập và nút lưu không bị che.

---

### User Story 5 - Bộ thành phần nông nghiệp (Priority: P2)

Đây là phần làm Lotus khác một trang quản trị thông thường. Người vườn nhìn là nhận ra việc của mình:

- **Thẻ lô**: mã lô, khu, trạng thái hôm nay, việc được giao, các màu dây còn trên cây, cách ly.
- **Lưới lô**: mọi lô của vườn xếp theo khu thành các ô, tô màu theo một chỉ tiêu (trạng thái báo cáo, đến hạn chăm sóc, đến tuổi thu, cách ly). Nhìn một lần thấy cả vườn.
- **Nhãn màu dây** và **chú giải màu dây**: chấm một màu hoặc hai màu, có viền để màu Trắng và Đen luôn thấy.
- **Nhãn tuần** và **dải tuần**: tuần theo lịch ISO, đánh dấu tuần này và các tuần đến tuổi thu.
- **Thước đến hạn**: còn n ngày, đến hạn, quá n ngày.
- **Nhãn cách ly**: còn n ngày, đến ngày nào.
- **Ô số liệu**: tên, số lớn, đơn vị, so với kỳ trước hoặc kế hoạch.
- **Biểu đồ dự thu theo tuần** (dự thu, thực tế, khoảng lệch) và **biểu đồ tuổi buồng**.
- **Chú giải bản đồ** và **nhãn khu**.
- **Thẻ ca xưởng**, **dòng thời gian của lô**, **nhãn tổ và đội**.

**Why this priority**: Các màn vườn, buồng, thu hoạch, dự thu là phần riêng của Lotus. Hiện mỗi màn tự vẽ thẻ lô và chấm màu theo cách của mình.

**Independent Test**: Mở phần Nông nghiệp của trang mẫu với dữ liệu mẫu 64 lô và 12 màu dây. Mở ba màn Hôm nay, Màu dây và thu hoạch, Vòng chăm sóc và so thẻ của cùng một lô.

**Acceptance Scenarios**:

1. **Given** đợt màu "Trắng" trên nền sáng hoặc "Đen" trên nền tối, **When** hiển thị, **Then** chấm màu vẫn thấy rõ nhờ viền.
2. **Given** đợt hai màu, ví dụ Xanh lá và Đỏ, **When** hiển thị, **Then** chấm chia đôi hai màu và nhãn đọc đủ tên.
3. **Given** lô đang cách ly thuốc đến 14/11 và hôm nay là 10/11, **When** hiển thị, **Then** nhãn ghi "Cách ly còn 4 ngày, đến 14/11" theo tông nguy.
4. **Given** lưới lô của vườn 64 lô, **When** chọn chỉ tiêu "đến hạn chăm sóc", **Then** mỗi ô tô theo ba mức (chưa đến hạn, đến hạn, quá hạn), có chú giải, và bấm một ô thì mở chi tiết lô.
5. **Given** ô số liệu chưa có số, **When** hiển thị, **Then** hiện dấu gạch và ghi "chưa có số", không hiện 0.
6. **Given** cùng một lô hiện ở màn Hôm nay, Màu dây và Vòng chăm sóc, **When** so sánh, **Then** thẻ lô có cùng bố cục và cùng màu trạng thái.
7. **Given** người mù màu đỏ và lục, **When** xem lưới lô, **Then** các mức vẫn phân biệt được nhờ biểu tượng hoặc hoa văn trong ô.
8. **Given** biểu đồ dự thu theo tuần, **When** rê chuột vào một tuần, **Then** thấy dự thu, thực tế và độ lệch của tuần đó, có đơn vị.

---

### User Story 6 - Trang mẫu để xem và duyệt (Priority: P2)

Chủ vườn và người làm có một trang liệt kê toàn bộ bộ giao diện: màu kèm tỉ lệ tương phản, chữ, khoảng cách, từng thành phần với mọi trạng thái, bảng, bộ điện thoại trong khung điện thoại, bộ nông nghiệp, và vài mẫu màn hình hoàn chỉnh. Trang có nút đổi sáng, tối, ngoài trời và gọn, thoáng. Chủ vườn duyệt diện mạo ở đây trước khi áp rộng.

**Why this priority**: Không có chỗ xem tổng thể thì không duyệt được, và người làm sau không biết đã có gì.

**Independent Test**: Mở trang mẫu, đi hết mục lục, đổi qua lại các chế độ. Đếm số thành phần trong bộ và số thành phần có mặt trên trang.

**Acceptance Scenarios**:

1. **Given** người xem mở trang mẫu, **When** nhìn mục lục, **Then** thấy sáu phần: Nền, Thành phần, Bảng, Điện thoại, Nông nghiệp, Mẫu màn hình.
2. **Given** trang mẫu đang mở, **When** bấm đổi sáng, tối, ngoài trời hoặc gọn, thoáng, **Then** toàn trang đổi theo ngay.
3. **Given** phần màu, **When** xem một cặp chữ và nền, **Then** thấy tỉ lệ tương phản và kết quả đạt hay không đạt.
4. **Given** phần Điện thoại, **When** xem, **Then** thành phần hiện trong khung rộng 390px và 320px.
5. **Given** bất kỳ số liệu nào trên trang mẫu, **When** xem, **Then** có ghi rõ đó là dữ liệu mẫu.
6. **Given** bản chạy thật, **When** người dùng thường đăng nhập, **Then** không có đường nào dẫn tới trang mẫu.

---

### User Story 7 - Chuyển các màn hiện có và dọn kiểu cũ (Priority: P3)

Từng phân hệ được chuyển hẳn sang bộ mới: thẻ, nhãn, ô số liệu, thanh công cụ viết riêng được thay bằng thành phần chung. Kiểu cũ không còn màn nào dùng thì xóa. Thứ tự: khung chung (thanh bên, thanh trên, tab, hộp thoại), rồi vườn, buồng, thu hoạch, dự thu, rồi Kho, Mua hàng, Tài chính, Nhân sự và chấm công, cuối cùng là các ứng dụng điện thoại.

**Why this priority**: Lớp nền đã đổi diện mạo chung. Việc chuyển hẳn từng màn làm bộ giao diện gọn lại và dễ sửa về sau, nhưng không chặn các phần trên.

**Independent Test**: Với mỗi phân hệ đã chuyển: chạy toàn bộ kiểm tra tự động, mở từng màn ở máy tính và điện thoại, đếm số kiểu viết riêng còn lại.

**Acceptance Scenarios**:

1. **Given** một phân hệ đã chuyển, **When** rà mã của nó, **Then** thẻ, nhãn trạng thái, ô số liệu và thanh công cụ đều là thành phần chung; tệp kiểu riêng chỉ còn phần đặc thù của phân hệ.
2. **Given** một kiểu cũ không còn màn nào dùng, **When** hoàn tất chuyển phân hệ đó, **Then** kiểu ấy đã bị xóa.
3. **Given** một phân hệ vừa chuyển xong, **When** chạy toàn bộ kiểm tra tự động, **Then** tất cả vẫn qua và thao tác trên màn cho cùng kết quả như trước.
4. **Given** hai nhánh khác đang sửa cùng tệp, **When** gộp, **Then** phần sửa của hai nhánh đó được giữ nguyên.

---

### User Story 8 - Biểu đồ, bản đồ và bản in cùng một hệ (Priority: P3)

Biểu đồ dùng một bảng màu chung, phân biệt được với người mù màu. Bản đồ có chú giải, nhãn khu và nút điều khiển cùng kiểu với phần còn lại. Bản in (phiếu giao việc, phiếu ngày, đơn mua, phiếu chi) có cùng kiểu chữ, khung và vị trí chữ ký, luôn in nền trắng chữ đen.

**Why this priority**: Đây là phần hoàn thiện. Thiếu nó thì biểu đồ, bản đồ và giấy in vẫn dùng được như hiện nay.

**Independent Test**: Mở các biểu đồ và bản đồ hiện có ở sáng và tối. Xem trước bản in của bốn loại phiếu khi đang ở chế độ tối.

**Acceptance Scenarios**:

1. **Given** biểu đồ có nhiều chuỗi, **When** hiển thị, **Then** dùng tối đa tám màu phân loại theo thứ tự cố định, kèm chú giải.
2. **Given** biểu đồ thể hiện mức độ, **When** hiển thị, **Then** dùng thang màu liên tục một tông; lệch so với kế hoạch dùng thang hai chiều.
3. **Given** bản đồ vườn, **When** hiển thị, **Then** chú giải, nhãn khu và nút phóng to thu nhỏ theo cùng kiểu chữ, bo góc và bóng với các thành phần khác.
4. **Given** người dùng đang ở chế độ tối, **When** in một phiếu, **Then** bản in nền trắng chữ đen.

---

### Edge Cases

- Màn chưa chuyển vẫn nạp kiểu cũ cùng lúc với nền mới: không được vỡ bố cục, không được đổi chức năng.
- Tên tiếng Việt dài có dấu, số rất lớn (hàng tỷ đồng), số âm, số lẻ: không tràn ô, không bị cắt mất dấu.
- Bảng 0 dòng, 1 dòng và 5.000 dòng.
- Màn rộng 320px và màn rất rộng từ 1920px.
- Màu dây Trắng trên nền sáng, Đen trên nền tối, và đợt hai màu.
- Dữ liệu thiếu: hiện dấu gạch và lý do, không hiện 0 và không điền số thay.
- Trạng thái chỉ khác nhau bằng màu: phải có thêm chữ hoặc biểu tượng.
- Máy bật "giảm chuyển động" hoặc "tăng tương phản".
- In khi đang ở chế độ tối hoặc ngoài trời.
- Hộp chọn, lịch, menu mở bên trong hộp thoại: phải nổi trên hộp thoại, không bị cắt.
- Điện thoại yếu và mạng chậm: dung lượng tải về không được tăng đáng kể.
- Hai nhánh 002 và 003 đang sửa cùng các tệp giao diện: khi gộp phải giữ đủ phần của hai nhánh.
- Người dùng đã lưu chế độ xem, độ rộng cột, lựa chọn sáng tối trước đây: sau khi lên bản mới vẫn còn.

## Requirements *(mandatory)*

### Functional Requirements

**Nền**

- **FR-001**: Hệ thống PHẢI có một nguồn duy nhất cho màu, chữ, khoảng cách, bo góc, bóng, chuyển động, thứ tự lớp nổi và các mốc bề rộng màn hình. Mọi kiểu khác chỉ được tham chiếu nguồn này, không ghi giá trị riêng.
- **FR-002**: Màu chính PHẢI là Đỏ Lotus như hiện nay. Bộ màu PHẢI có đủ: trung tính, đạt, cảnh báo, nguy, thông tin; màu dây; trạng thái lô; màu khu trên bản đồ; bảng màu phân loại cho biểu đồ (ít nhất tám màu); một thang màu liên tục và một thang hai chiều.
- **FR-003**: Hệ thống PHẢI có ba chế độ hiển thị: sáng, tối và ngoài trời. Trên máy tính PHẢI có hai mật độ: gọn và thoáng, chọn ở menu tài khoản trên thanh trên. Lựa chọn PHẢI được nhớ trên máy của người dùng.
- **FR-004**: Mọi cặp chữ và nền trong bộ màu PHẢI đạt tương phản từ 4,5:1 với chữ thường và từ 3:1 với chữ lớn, biểu tượng và đường viền của ô nhập. Ở chế độ ngoài trời, chữ chính PHẢI đạt từ 7:1.
- **FR-005**: Hệ thống PHẢI có một bảng từ vựng trạng thái dùng chung cho mọi phân hệ. Mỗi trạng thái (nháp, chờ duyệt, chờ ký, đã duyệt, đã xong, trả lại, mở lại, đã hủy, đến hạn, quá hạn, cách ly) có một nhãn tiếng Việt, một tông màu và một biểu tượng.
- **FR-006**: Mọi thành phần bấm được PHẢI có các trạng thái thường, rê chuột, đang bấm, đang đứng và vô hiệu. Vị trí đang đứng PHẢI luôn thấy được khi dùng bàn phím.
- **FR-007**: Hành động nguy hiểm và trạng thái lỗi PHẢI phân biệt được với nút chính màu đỏ bằng kiểu nút, biểu tượng hoặc chữ, không chỉ bằng màu.
- **FR-008**: Không trạng thái hay mức độ nào được thể hiện chỉ bằng màu.
- **FR-009**: Hệ thống PHẢI tôn trọng lựa chọn "giảm chuyển động" của máy.
- **FR-010**: Số trong bảng, ô số liệu và biểu đồ PHẢI dùng chữ số đều cột, có dấu tách nghìn và đơn vị theo cách đã dùng trong Lotus.

**Bảng dữ liệu**

- **FR-011**: Bảng dùng chung PHẢI giữ nguyên mọi chức năng hiện có: lọc kiểu Excel, sắp xếp, ẩn hiện cột, chế độ xem đã lưu, chọn dòng, cột số thứ tự, dòng tổng, phân trang, xuất Excel, mở chi tiết khi bấm dòng.
- **FR-012**: Tiêu đề cột và dòng tổng PHẢI đứng yên khi cuộn thân bảng.
- **FR-013**: Mọi bảng PHẢI theo cùng một mật độ (gọn hoặc thoáng) mà người dùng chọn ở menu tài khoản, và nhớ lựa chọn này. KHÔNG đặt nút chọn mật độ phía trên bảng (quy ước trong `AGENTS.md`).
- **FR-013a**: Bảng Kho PHẢI giữ kiểu đã nghiệm thu: căn giữa mọi ô và tiêu đề, có viền dọc giữa các cột. Kiểu này là một biến thể có tên của bảng dùng chung, không phải kiểu viết riêng.
- **FR-014**: Bảng PHẢI có sẵn các kiểu ô: nhãn trạng thái, số có đơn vị, tiền, ngày, ngày kèm số ngày quá hạn, thanh tiến độ, chấm màu dây, người kèm chữ cái đầu, và số kèm xu hướng.
- **FR-015**: Bảng PHẢI có trạng thái trống (phân biệt "chưa có dữ liệu" và "lọc không ra kết quả"), trạng thái đang tải dạng khung chờ, và trạng thái lỗi kèm nút thử lại.
- **FR-016**: Trên điện thoại, mỗi dòng của bảng PHẢI hiện thành một thẻ, không cuộn ngang.

**Bộ thành phần máy tính**

- **FR-017**: Bộ thành phần máy tính PHẢI gồm đủ các nhóm đã liệt kê ở User Story 3: hành động, nhập liệu, hiển thị, phản hồi, lớp nổi, điều hướng và bố cục.
- **FR-018**: Mỗi ô nhập PHẢI có nhãn, và khi cần thì có gợi ý, dấu bắt buộc và lỗi hiện ngay dưới ô.
- **FR-019**: Hộp thoại, ngăn kéo và menu PHẢI đóng được bằng Esc, giữ con trỏ bàn phím ở bên trong khi đang mở, và trả con trỏ về chỗ cũ khi đóng.
- **FR-020**: Hộp chọn, lịch và menu mở bên trong hộp thoại PHẢI nổi trên hộp thoại và không bị cắt.
- **FR-021**: Các mẫu bố cục đã chốt PHẢI có sẵn dưới dạng mẫu dùng lại: trang danh sách (hàng một là nút hành động, nút tạo đứng đầu bên trái; hàng hai là tìm và lọc; rồi đến bảng và phân trang), hộp nhập (nút lưu bên phải), trang tổng hợp theo thẻ (bấm thẻ mở hộp chi tiết).
- **FR-022**: Toàn bộ chữ hiển thị PHẢI bằng tiếng Việt.

**Bộ điện thoại**

- **FR-023**: Bộ điện thoại PHẢI có: nút, ô nhập, ô chọn, hộp kiểm, ô số có nút cộng trừ, thẻ, dòng danh sách, ô số liệu, nhãn trạng thái, chọn theo đoạn, tab, hộp thoại và hộp mở từ dưới lên, dải thông báo, thông báo nổi, khung chờ, trạng thái trống.
- **FR-024**: Mọi vùng bấm trên điện thoại PHẢI từ 44px; ở chế độ ngoài trời từ 48px.
- **FR-025**: Chế độ ngoài trời PHẢI bật và tắt được bằng một nút trong ứng dụng điện thoại.
- **FR-026**: Ứng dụng điện thoại PHẢI báo rõ khi mất mạng và khi có mạng lại.
- **FR-027**: Thanh điều hướng dưới PHẢI có chữ dưới mỗi biểu tượng và ẩn khi bàn phím mở.
- **FR-028**: Không màn điện thoại nào được tràn ngang ở bề rộng 320px.

**Bộ thành phần nông nghiệp**

- **FR-029**: Hệ thống PHẢI có thẻ lô dùng chung cho mọi màn có hiện lô, với cùng bố cục và cùng màu trạng thái.
- **FR-030**: Hệ thống PHẢI có lưới lô hiện toàn bộ lô của một vườn theo khu, tô màu theo chỉ tiêu được chọn, có chú giải, và bấm vào ô thì mở chi tiết lô.
- **FR-031**: Nhãn màu dây PHẢI hiện đúng màu của từng đợt, hỗ trợ đợt hai màu, và luôn có viền để màu rất sáng hoặc rất tối vẫn thấy trên mọi nền.
- **FR-032**: Hệ thống PHẢI có nhãn tuần và dải tuần theo tuần ISO, đánh dấu tuần hiện tại.
- **FR-033**: Hệ thống PHẢI có thước đến hạn và nhãn cách ly, ghi số ngày còn lại hoặc đã quá và ngày mốc.
- **FR-034**: Ô số liệu PHẢI hiện tên, số, đơn vị và phần so sánh nếu có. Khi không có số PHẢI hiện dấu gạch kèm lý do, không hiện 0.
- **FR-035**: Hệ thống PHẢI có mẫu biểu đồ dự thu theo tuần và biểu đồ tuổi buồng dùng bảng màu chung.
- **FR-036**: Hệ thống PHẢI có chú giải bản đồ, nhãn khu, thẻ ca xưởng, dòng thời gian của lô và nhãn tổ, đội.
- **FR-037**: Các thành phần nông nghiệp PHẢI dùng được trên cả máy tính và điện thoại.
- **FR-038**: Thành phần nông nghiệp chỉ hiển thị số được đưa vào. Không thành phần nào tự tính, tự suy hay tự điền số.

**Trang mẫu và giữ chuẩn**

- **FR-039**: Hệ thống PHẢI có trang mẫu liệt kê toàn bộ nền, thành phần, bảng, bộ điện thoại, bộ nông nghiệp và các mẫu màn hình, với nút đổi chế độ và mật độ.
- **FR-040**: Trang mẫu PHẢI ghi rõ mọi số liệu trên trang là dữ liệu mẫu, không đọc và không ghi dữ liệu thật, và không có trong bản chạy thật.
- **FR-041**: Hệ thống PHẢI có kiểm tra tự động cho: tương phản của bộ màu; không ghi màu riêng ngoài nguồn chung; mọi thành phần của bộ có mặt trên trang mẫu; hành vi của thành phần có đóng mở, chọn, lọc.
- **FR-042**: Bộ giao diện PHẢI có hướng dẫn ngắn bằng tiếng Việt cho người làm: khi nào dùng thành phần nào, cách đặt tên, cách thêm thành phần mới.

**Chuyển đổi**

- **FR-043**: Việc đổi giao diện KHÔNG được đổi nghiệp vụ, số liệu, quyền hạn, trạng thái chứng từ, cách ký, cách chống gửi trùng hay cách các ứng dụng điện thoại hoạt động khi mất mạng.
- **FR-044**: Màn chưa chuyển PHẢI tiếp tục chạy đúng trong lúc các màn khác đã chuyển.
- **FR-045**: Khung chung (thanh bên, thanh trên, tab, hộp thoại, thanh công cụ danh sách) và các màn vườn, buồng, thu hoạch, dự thu PHẢI được chuyển sang bộ mới trong đợt này.
- **FR-046**: Mỗi phân hệ sau khi chuyển PHẢI xóa các kiểu riêng không còn dùng.
- **FR-047**: Lựa chọn người dùng đã lưu trước đây (chế độ xem bảng, độ rộng cột, sáng hay tối) PHẢI còn nguyên sau khi lên bản mới.

**Biểu đồ, bản đồ, bản in**

- **FR-048**: Biểu đồ PHẢI lấy màu, chữ và kiểu chú thích từ nguồn chung, ở cả sáng và tối.
- **FR-049**: Bản đồ PHẢI có chú giải và nút điều khiển theo kiểu chung.
- **FR-050**: Bản in PHẢI luôn có nền trắng chữ đen, dùng chung kiểu chữ, khung và vị trí chữ ký.

### Key Entities

- **Giá trị nền**: một tên gọi cho một giá trị giao diện (màu, cỡ chữ, khoảng cách, bo góc, bóng). Có nhóm, có giá trị theo từng chế độ sáng, tối, ngoài trời.
- **Chế độ hiển thị** và **mật độ**: sáng, tối, ngoài trời; gọn, thoáng. Lưu theo máy của người dùng.
- **Thành phần**: một khối giao diện dùng lại. Có tên, nền tảng (máy tính, điện thoại hoặc cả hai), biến thể, cỡ và các trạng thái.
- **Trạng thái nghiệp vụ**: một mục trong bảng từ vựng chung. Có mã, nhãn tiếng Việt, tông màu và biểu tượng.
- **Màu dây**: một màu hoặc cặp màu trong vòng màu của vườn. Có mã, tên và màu hiển thị.
- **Trạng thái lô**: tình trạng của một lô theo một chỉ tiêu (báo cáo hôm nay, đến hạn chăm sóc, đến tuổi thu, cách ly). Dùng để tô thẻ lô và lưới lô.
- **Mẫu màn hình**: cách xếp sẵn các thành phần cho một loại màn (trang danh sách, hộp nhập, trang tổng hợp theo thẻ).
- **Trang mẫu**: nơi trưng bày toàn bộ các mục trên bằng dữ liệu mẫu.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% cặp chữ và nền của bộ màu đạt mức tương phản ở FR-004, đo tự động ở cả ba chế độ.
- **SC-002**: Mỗi trạng thái nghiệp vụ chỉ có một cách thể hiện: cùng nhãn, màu và biểu tượng ở mọi phân hệ đã chuyển.
- **SC-003**: 100% thành phần của bộ có mặt trên trang mẫu, mỗi thành phần hiện đủ biến thể và trạng thái.
- **SC-004**: Toàn bộ kiểm tra tự động có trước khi làm vẫn qua sau khi làm; không màn nào mất chức năng.
- **SC-005**: Ở bề rộng 320px, không màn mẫu điện thoại nào tràn ngang; 100% vùng bấm đạt kích thước ở FR-024.
- **SC-006**: Người làm dựng được một trang danh sách có lọc, bảng và hộp nhập mà không viết thêm kiểu riêng nào.
- **SC-007**: Trong các màn vườn, buồng, thu hoạch, dự thu, số kiểu thẻ lô, chấm màu dây và ô số liệu viết riêng giảm về 0.
- **SC-008**: Dung lượng kiểu tải về của mỗi ứng dụng (máy tính và từng ứng dụng điện thoại), đo sau khi nén, không tăng quá 15% so với trước khi làm.
- **SC-009**: Thời gian mở các màn chính không chậm hơn trước khi làm.
- **SC-010**: Chủ vườn xem trang mẫu và duyệt diện mạo trước khi bản này lên máy chủ thật.
- **SC-011**: Người dùng điện thoại đọc được số và bấm đúng nút ngoài nắng ở chế độ ngoài trời: chữ chính đạt tương phản từ 7:1 và vùng bấm từ 48px trên mọi màn mẫu.

## Assumptions

- Nhánh này tách từ `002-cham-soc-thu-hoach-du-thu`, nên lên máy chủ sau bản 002. Nhánh 003 (mua hàng và ký điện tử) đang sửa một số tệp giao diện chung; khi gộp phải giữ đủ phần của nhánh đó.
- Không thêm thư viện giao diện mới. Các thư viện đang dùng cho máy tính, điện thoại, bảng, biểu đồ và bản đồ được giữ nguyên phiên bản.
- Kiểu chữ giữ như hiện nay.
- Các quy ước trong `AGENTS.md` và nguyên tắc V của constitution vẫn có hiệu lực. Bộ mới là bản nâng cấp của chuẩn đó, không phải chuẩn thứ hai.
- Trang mẫu là công cụ cho người làm và để chủ vườn duyệt; người dùng thường không thấy.
- Kiểm tra tự động và bản dựng thử chạy trên máy chủ thử hoặc GitHub, không chạy trên máy làm việc.
- Chỉ đưa lên máy chủ thật khi chủ vườn yêu cầu.

**Ngoài phạm vi**:

- Màn hình cho nghiệp vụ mới, thay đổi luồng nghiệp vụ, báo cáo mới.
- Đổi màu chính, đổi logo.
- Số liệu thời tiết hoặc cảm biến: hiện chưa có nguồn dữ liệu thật, nên không làm thành phần hiển thị loại số này.
- Việc xóa bảng dữ liệu đời cũ (thuộc spec 002).
- Ứng dụng Android gốc trong thư mục `android/`.
