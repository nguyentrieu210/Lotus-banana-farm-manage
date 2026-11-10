# Feature Specification: Làm lại chăm sóc vườn, chăm sóc buồng, thu hoạch, báo cáo và dự thu

**Feature Branch**: `002-cham-soc-thu-hoach-du-thu`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "Làm lại phần chăm sóc vườn, buồng, thu hoạch, báo cáo và dự thu."

## Ý tưởng chính

Mọi việc làm trên một lô, từ cắt lá, phun thuốc, chích bắp, cắt bắp đến thu hoạch, là một dòng trong **sổ lô**. Tổ chỉ nhập ở **một báo cáo ngày**. Từ sổ lô, hệ thống tự dựng ra các phần sau mà không ai phải nhập lại:

1. **Vòng chăm sóc**: lô nào đến hạn, lô nào quá hạn việc gì.
2. **Bảng màu dây**: mỗi lô còn bao nhiêu buồng của từng đợt màu, đợt nào đến tuổi thu.
3. **Dự thu**: một con số duy nhất, tự chốt mỗi tuần, so được với thực tế.
4. **Báo cáo và tiền khoán**.

Cả vườn chạy theo nhịp tuần, giống lịch màu dây: đầu tuần giao việc đến hạn và chốt dự thu, hằng ngày báo cáo, cuối tuần xem lại.

Mọi bảng, màn hình và mã đời cũ của mảng này bị xóa hẳn sau khi lưu trữ dữ liệu, để chỉ còn một cách làm.

## Clarifications

### Session 2026-11-10

- Q: Ai nhập báo cáo ngày? → A: Cả hai. Tổ trưởng tự nhập trên điện thoại, hoặc đội trưởng/thống kê nhập hộ từ phiếu giấy của tổ. Có thêm chụp ảnh phiếu giấy để máy điền sẵn số.
- Q: Giao việc thế nào? → A: Theo vòng chăm sóc. Hệ thống liệt kê lô đến hạn, đội trưởng chỉ chọn tổ. Phiếu riêng chỉ còn cho việc khoán cả lô cần nghiệm thu.
- Q: Khi nào tính tiền khoán bằng bản mới? → A: Không có mốc phải giữ. Mảng này trên bản hiện tại chỉ là bản thử, chưa vận hành. Tiền khoán tính bằng sổ lô khi bản mới chạy; không phải giữ luồng cũ chạy song song hay chuyển số nhập thử.
- Q: Bảng, màn hình và mã đời cũ chỉ ẩn đi hay xóa? → A: Xóa hẳn cho sạch, làm luôn trong spec này, không để spec riêng.
- Q: Bỏ lô thu hoạch cũ thì nhập kho thành phẩm thế nào? → A: Chủ vườn duyệt: nhập kho thành phẩm theo từng ca đóng gói. Mỗi ca một phiếu nhập nháp (thành phẩm, phụ phẩm theo kg); giá trị lấy từ chi phí dở dang của các lô có buồng trong ca, chia theo kg.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Một báo cáo ngày cho mỗi tổ, đủ mọi việc trên lô (Priority: P1)

Cuối ngày, người nhập của tổ mở **Hôm nay** và thấy các lô tổ đang làm, mỗi lô một thẻ. Bấm vào một lô thì mở hộp nhập có mọi việc của lô đó: việc vườn (cắt lá, làm cỏ, chọn chồi…), phun thuốc và bón phân kèm vật tư, việc buồng (chích bắp, tỉa, chống đổ, cắt bắp, bao buồng, hủy buồng) và thu hoạch. Nhập xong các lô thì gửi một lần cho cả ngày. Đội trưởng xem lại và xác nhận một lần cho cả tổ.

**Why this priority**: Không có số đầu vào thì vòng chăm sóc, bảng màu dây, dự thu, báo cáo và tiền khoán đều trống. Đến ngày 09/11/2026 hệ thống thật chưa có báo cáo ngày nào, và tổ trưởng đang phải nhập ở hai màn với ba cách khác nhau tùy việc.

**Independent Test**: Một tổ nhập một ngày làm ở 3 lô, mỗi lô có cả việc vườn, việc buồng và phun thuốc, rồi đội trưởng xác nhận. Mỗi việc phải hiện đúng một lần trong sổ của lô đó, đúng tổ, đúng ngày. Màu dây của cắt bắp phải tự điền.

**Acceptance Scenarios**:

1. **Given** tổ 3 đang làm lô A5 và A6, **When** người nhập mở Hôm nay, **Then** thấy thẻ A5 và A6, và nhập được mọi nhóm việc của một lô trong cùng một hộp, không phải chuyển sang màn khác.
2. **Given** ngày thứ Ba của tuần màu Đỏ, **When** nhập cắt bắp 120 buồng ở A5, **Then** hệ thống ghi 120 buồng màu Đỏ, lần cắt 1, mà người nhập không phải chọn màu.
3. **Given** phun một loại thuốc có thời gian cách ly 14 ngày ở A5, **When** lưu, **Then** phải nhập vật tư và liều, và lô A5 chuyển sang trạng thái cách ly đến hết 14 ngày.
4. **Given** báo cáo đã được xác nhận, **When** cần sửa một số, **Then** phải ghi lý do, và số cũ vẫn xem lại được.
5. **Given** người nhập đang nhập dở 2 lô thì mất sóng, **When** mở lại, **Then** số đã nhập vẫn còn.
6. **Given** tổ 3 có 12 người chấm công buổi sáng, **When** nhập việc buổi sáng, **Then** 12 người đó có sẵn, người nhập chỉ bỏ ra người không làm việc đó.
7. **Given** dòng bao buồng khoán số lượng của tổ 3 vừa được xác nhận, **When** tổ trưởng mở mục của mình, **Then** thấy tiền khoán tạm tính của tổ và của từng người.
8. **Given** đội trưởng nhập hộ báo cáo của tổ 3 từ phiếu giấy, **When** gửi, **Then** báo cáo ghi tổ làm là tổ 3, người nhập là đội trưởng, và phải do quản lý vườn xác nhận.
9. **Given** ảnh chụp phiếu giấy của tổ 3 in từ hệ thống, **When** tải lên, **Then** các dòng lô, việc, số được điền sẵn, dòng đọc không chắc được đánh dấu, và chỉ gửi được sau khi người nhập kiểm lại.
10. **Given** tổ kiểm tra sâu bệnh ở A5, **When** nhập kết quả, **Then** phải chọn bệnh, số cây bị và mức độ, và dòng đó hiện trong báo cáo phun bón.

---

### User Story 2 - Bảng màu dây và thu hoạch theo lô và đợt màu (Priority: P2)

Quản lý vườn và đội trưởng mở **bảng màu dây**. Mỗi lô và mỗi đợt màu dây (màu và tuần cắt bắp) có: số đã cắt, đã bao, đã hủy, đã thu, còn trên cây, và tuổi tính bằng tuần. Đợt nào đến tuổi thu thì nằm trong danh sách cần thu của tuần. Tổ thu hoạch ghi số buồng và số kg theo lô và đợt màu. Lô đang cách ly thuốc thì không ghi thu được.

**Why this priority**: Số buồng còn trên cây theo màu là căn cứ để xếp người thu, xếp xưởng và hứa hàng với khách, và là đầu vào chắc nhất của dự thu. Hiện thu hoạch nhập qua sổ buồng không bị chặn khi lô đang cách ly thuốc.

**Independent Test**: Nhập cắt bắp hai màu ở hai lô, hủy một phần, thu một phần. Từng ô của bảng màu dây phải khớp với số đã nhập. Ghi thu ở lô đang cách ly phải bị chặn.

**Acceptance Scenarios**:

1. **Given** A5 có đợt Đỏ tuần 46 cắt 120 buồng, đã hủy 3, **When** đợt này đến tuổi thu, **Then** A5 Đỏ tuần 46 nằm trong danh sách cần thu với 117 buồng.
2. **Given** A5 đang cách ly đến 20/11, **When** ghi thu hoạch ngày 18/11, **Then** hệ thống chặn và báo ngày hết cách ly.
3. **Given** đợt Đỏ tuần 46 của A5 còn 40 buồng, **When** ghi thu 45 buồng, **Then** hệ thống không cho lưu và chỉ ra số còn lại.
4. **Given** màu Đỏ lặp lại sau 12 tuần, **When** xem bảng, **Then** hai đợt Đỏ là hai dòng riêng, không cộng chung.

---

### User Story 3 - Vòng chăm sóc theo lô thay cho giao từng phiếu (Priority: P3)

Mỗi việc vườn có một vòng (ví dụ cắt lá 14 ngày một lần) do quản lý vườn đặt. Với mỗi lô và mỗi việc, hệ thống biết lần làm xong gần nhất, ngày đến hạn và số ngày quá hạn. Đầu tuần, đội trưởng xem danh sách lô đến hạn và chọn tổ cho nhiều lô một lần. Lô báo xong trong báo cáo ngày thì tự sang vòng sau.

**Why this priority**: Chủ vườn cần thấy ngay lô nào bị bỏ sót chăm sóc. Hiện đội trưởng phải tạo phiếu cho từng lô và từng việc, còn "Lịch chăm sóc theo lô" đang tính từ cách dự thu cũ.

**Independent Test**: Đặt vòng cắt lá 14 ngày. Báo xong cắt lá ở A5 ngày 01/11. Kiểm tra A5 đến hạn ngày 15/11 và hiện quá hạn từ ngày 16/11 nếu chưa làm.

**Acceptance Scenarios**:

1. **Given** vòng cắt lá 14 ngày và A5 xong ngày 01/11, **When** xem ngày 17/11, **Then** A5 quá hạn cắt lá 2 ngày.
2. **Given** 10 lô đến hạn làm cỏ trong tuần, **When** đội trưởng chọn tổ 2 cho 6 lô, **Then** 6 lô hiện trên Hôm nay của tổ 2, còn 4 lô vẫn nằm trong danh sách chưa giao.
3. **Given** một việc khoán cả lô, **When** tổ báo xong, **Then** lô chờ nghiệm thu, và chỉ tính tiền khi nghiệm thu đạt.

---

### User Story 4 - Một con số dự thu, tự chốt mỗi tuần, so với thực tế (Priority: P4)

Dự thu giữ cách tính đã thống nhất ở spec 001: mỗi đợt cây lấy số liệu gần thu hoạch nhất đang có (đã cắt bắp, rồi đã chích bắp, rồi chọn chồi, cuối cùng là số cây). Khác ở chỗ dự thu đọc từ sổ lô và bảng màu dây, và là con số duy nhất trên mọi màn. Bản chốt đầu tuần luôn có. Sai số và tham số đề xuất dựa trên số thu hoạch và đóng gói thật.

**Why this priority**: Hiện còn nhiều chỗ đọc dự thu theo cách cũ, và bản chốt sáng thứ Hai không tự chạy trên máy chủ thật, nên phần so với thực tế sẽ trống.

**Independent Test**: Không mở trang dự thu từ thứ Sáu đến thứ Tư. Mở vào thứ Tư, kiểm tra vẫn có bản chốt của tuần này và bản chốt đúng với số liệu đã có trước 0 giờ thứ Hai.

**Acceptance Scenarios**:

1. **Given** không ai mở trang dự thu cả tuần, **When** mở vào thứ Tư, **Then** có bản chốt đầu tuần, đúng như số liệu trước 0 giờ thứ Hai.
2. **Given** Tổng quan, kế hoạch tài chính và trang dự thu cùng hiện dự thu tháng 01/2027 toàn vườn, **When** so ba màn, **Then** ba con số bằng nhau.
3. **Given** đợt Đỏ tuần 46 của A5 đã thu xong, **When** xem phần so với thực tế, **Then** thấy chênh lệch số buồng, số kg và số ngày so với bản chốt.

---

### User Story 5 - Báo cáo theo người xem: Sáng nay, Tuần, Tháng (Priority: P5)

Ba màn báo cáo cố định. Mỗi số là một thẻ; bấm vào thẻ thì mở chi tiết trong hộp và xuất được Excel.

- **Sáng nay** (đội trưởng, quản lý vườn): tổ chưa gửi hoặc chưa xác nhận, số bất thường, việc quá hạn, lô đang cách ly, đợt màu đến tuổi thu.
- **Tuần** (quản lý vườn, giám đốc): bản đồ lô tô màu theo tình trạng, việc đã làm theo lô, bảng màu dây, thu hoạch và đóng gói, dự thu 13 tuần so với thực tế.
- **Tháng** (giám đốc, kế toán): sản lượng và các tỷ lệ (cắt bắp/cây, thu/cắt bắp, kg/buồng, thùng/buồng), ngày công và tiền khoán theo lô, vật tư xuất kho so với vật tư báo dùng theo lô.

**Why this priority**: Hiện có bốn trang biểu đồ tự chọn kiểu Pivot, mỗi trang một nguồn, người xem phải tự dựng mới ra câu trả lời.

**Independent Test**: Với số mẫu của một tuần, trả lời ba câu hỏi: tổ nào chưa báo hôm qua, lô nào quá hạn cắt lá, tuần này cần thu bao nhiêu buồng. Mỗi câu chỉ cần nhìn một thẻ.

**Acceptance Scenarios**:

1. **Given** hôm qua tổ 2 chưa gửi báo cáo, **When** đội trưởng mở Sáng nay, **Then** tổ 2 nằm đầu danh sách.
2. **Given** thẻ "Thu hoạch tuần 47", **When** bấm vào, **Then** mở hộp chi tiết theo lô và đợt màu, có nút xuất Excel.
3. **Given** bản đồ lô trên màn Tuần, **When** bấm lô A5, **Then** mở hộp sổ lô A5: việc làm gần nhất, các đợt màu còn trên cây, cách ly, thu hoạch.

---

### User Story 6 - Nối thu hoạch với xưởng đóng gói (Priority: P6)

Xưởng ghi theo ca: số buồng và số kg nhận theo lô và đợt màu (lấy từ thu hoạch trong ngày), số thùng ra, phụ phẩm, hao hụt. Hệ thống tính kg/buồng, thùng/buồng và tỷ lệ đóng gói thật theo lô. Từ một ca đóng gói, truy ngược được về lô, đợt màu, ngày thu và các lần phun thuốc trước đó.

**Why this priority**: Xưởng hiện chỉ ghi tổng theo ca, không biết buồng từ lô nào, nên không có thùng/buồng thật theo lô để hiệu chỉnh dự thu, và không truy vết được khi khách hỏi.

**Independent Test**: Ghi một ca nhận buồng từ hai lô, ra một số thùng. Kiểm tra thùng chia đúng cho từng lô và truy ngược từ ca về đúng hai lô.

**Acceptance Scenarios**:

1. **Given** ca sáng nhận 300 buồng A5 Đỏ (6.000 kg) và 200 buồng A6 Đỏ (3.800 kg), ra 650 thùng, **When** xem kết quả ca, **Then** thùng được chia cho A5 và A6 theo kg nhận, và mỗi lô có thùng/buồng riêng.
2. **Given** một ca đóng gói, **When** truy vết, **Then** thấy các lô, đợt màu, ngày thu và các lần phun thuốc ở các lô đó trước ngày thu.
3. **Given** một ca đóng gói đã xong, **When** kế toán lập nhập kho thành phẩm, **Then** phiếu nhập có thành phẩm và phụ phẩm theo kg, và giá trị lấy từ chi phí dở dang của các lô trong ca theo tỷ lệ kg nhận.

---

### User Story 7 - Dọn sạch đồ cũ (Priority: P7)

Khi các phần mới đã chạy đúng, toàn bộ bảng, màn hình, menu và mã đời cũ của mảng này bị xóa hẳn, không chỉ ẩn đi. Trước khi xóa, dữ liệu của từng bảng được lưu ra tệp. Kho, tài chính và lương đang đọc các bảng cũ được chuyển sang đọc sổ lô, hoặc bỏ phần chức năng chỉ phục vụ cách làm cũ.

**Why this priority**: Chủ vườn muốn hệ thống sạch. Ba lớp đồ cũ chồng nhau làm người dùng nhầm chỗ nhập, và mỗi lần sửa phải giữ tương thích với chúng. Việc này làm sau cùng vì phải chuyển kho, tài chính, lương sang nguồn mới trước.

**Independent Test**: Sau khi dọn, quét mã, cơ sở dữ liệu và menu không còn tên bảng nào trong danh sách xóa. Kho, tài chính và lương chạy hết kịch bản kiểm thử của chúng.

**Acceptance Scenarios**:

1. **Given** đã dọn xong, **When** tìm bất kỳ bảng nào trong danh sách xóa, **Then** bảng đó không còn trong cơ sở dữ liệu, trong mã và trên menu.
2. **Given** tệp lưu trữ đồ cũ, **When** mở ra, **Then** mỗi bảng có đủ số dòng như lúc đếm trước khi xóa.
3. **Given** kỳ lương và sổ sách của các tháng đã khóa, **When** xem lại sau khi dọn, **Then** số liệu không thay đổi.
4. **Given** kho xuất thuốc cho phun, **When** lập phiếu xuất, **Then** chọn được "Thủ công" hoặc "Theo yêu cầu đã duyệt"; không còn "Theo kế hoạch đã duyệt".

---

### Edge Cases

- Hai tổ cùng làm một lô, cùng một việc, trong một ngày: không tính trùng số lượng, mỗi tổ nhận phần của mình.
- Nhập bù ngày hôm trước: màu dây lấy theo ngày làm, không theo ngày nhập.
- Lô đổi tổ phụ trách giữa vòng.
- Một lô làm nhiều ngày mới xong (cắt lá lô 5 ha trong 3 ngày): chỉ ngày báo xong mới tính xong vòng; các ngày trước là đang làm.
- Một lần phun cho nhiều lô dùng chung một phiếu xuất kho.
- Nhiều lần phun chồng nhau: cách ly lấy ngày hết muộn nhất.
- Thu rải nhiều ngày cho một đợt màu, và thu vét đợt cũ.
- Gió đổ hàng loạt: hủy một số lớn một lần, bảng màu dây và dự thu giảm ngay.
- Thu hoạch ở đợt cắt bắp trước ngày áp dụng mà sổ đầu kỳ chưa có.
- Sửa số của tháng đã chốt tiền khoán.
- Đổi mã lô, gộp hoặc tách lô.
- Một ca đóng gói nhận buồng của nhiều lô; buồng của một lô đóng ở hai ca.
- Ngày chưa có màu dây trong lịch.
- Vòng chăm sóc đổi giữa chừng, ví dụ mùa mưa cắt lá dày hơn.
- Một bảng cũ có dữ liệu gắn với chứng từ kế toán đã ghi sổ (ví dụ phiếu kho trỏ về kế hoạch ngày cũ, hay bút toán có chiều Vụ).
- Kỳ lương đã khóa từng lấy chi phí công theo lô từ bảng phân bổ cũ.

## Requirements *(mandatory)*

### Functional Requirements

**Sổ lô: một nơi ghi, một cách tính**

- **FR-001**: Mọi việc làm trên lô (việc vườn, phun thuốc, bón phân, việc buồng, thu hoạch) PHẢI được ghi vào cùng một sổ theo lô. Mỗi dòng có ngày làm, lô, việc, số lượng và đơn vị, tổ làm, người nhập và trạng thái xác nhận.
- **FR-002**: Lô chăm sóc là đơn vị nhỏ nhất; thửa tưới không tham gia.
- **FR-003**: Vòng chăm sóc, bảng màu dây, dự thu, báo cáo và tiền khoán PHẢI chỉ đọc từ sổ lô. Một việc chỉ có một nơi nhập.
- **FR-004**: Các cách ghi và cách tính đang có cho cùng các việc này PHẢI được thay thế, không chạy song song. Bản hiện tại là bản thử nên không phải chuyển số nhập thử. Dữ liệu gốc của vườn PHẢI được giữ và giữ nguồn: sổ cắt bắp đầu kỳ, số cây kiểm kê theo lô, danh mục việc và bảng giá khoán, đội và tổ, lịch màu dây.

**Báo cáo ngày**

- **FR-005**: Mỗi tổ có một báo cáo mỗi ngày, gồm mọi lô và mọi việc trong ngày. Màn nhập dùng thẻ theo lô và hộp nhập, không trải bảng phẳng.
- **FR-006**: Báo cáo của một tổ PHẢI nhập được theo hai cách: tổ trưởng tự nhập trên điện thoại, hoặc đội trưởng/thống kê nhập hộ từ phiếu giấy của tổ trên máy tính hay điện thoại. Báo cáo ghi rõ tổ làm và người nhập.
- **FR-036**: In được phiếu giấy của ngày cho từng tổ, có sẵn các lô và việc đến hạn, để tổ ghi tay. Chụp ảnh phiếu đã ghi thì máy điền sẵn các dòng; dòng nào máy đọc không chắc thì đánh dấu. Không dòng nào do máy đọc được gửi khi chưa có người kiểm lại.
- **FR-007**: Việc buồng theo các quy tắc đã chốt: cắt bắp tự gắn màu dây theo tuần và lần cắt; chích bắp, tỉa và chống đổ không chọn màu và không vượt số cây của lô; bao buồng và thu hoạch chọn trong các đợt màu còn buồng. Bao, hủy sau cắt và thu cộng dồn không vượt số đã cắt của lô và đợt màu.
- **FR-008**: Phun thuốc và bón phân PHẢI ghi vật tư và liều. Thuốc có thời gian cách ly đặt lô vào trạng thái cách ly đến ngày hết muộn nhất.
- **FR-009**: Người nhập không tự xác nhận số của mình. Đội trưởng xác nhận một lần cho một tổ trong một ngày. Số đã xác nhận chỉ sửa khi có lý do và giữ lịch sử.
- **FR-010**: Người làm theo buổi lấy mặc định từ chấm công của tổ; người nhập chỉ sửa trường hợp khác.
- **FR-011**: Số đang nhập dở không mất khi mất sóng hoặc đóng ứng dụng.

**Vòng chăm sóc và giao việc**

- **FR-012**: Mỗi việc vườn có vòng tính bằng ngày, có ngày hiệu lực, có thể khác theo khu hoặc theo mùa. Quản lý vườn đặt.
- **FR-013**: Với mỗi lô và việc, hệ thống PHẢI tính lần xong gần nhất, ngày đến hạn và số ngày quá hạn. Việc làm nhiều ngày chỉ tính xong vòng khi báo xong cả lô.
- **FR-014**: Đội trưởng giao việc theo danh sách lô đến hạn: chọn tổ cho nhiều lô một lần, không tạo phiếu cho từng lô. Phiếu riêng chỉ dùng cho việc khoán cả lô cần nghiệm thu. Đổi tổ hoặc hủy giao phải có lý do.
- **FR-015**: Lô giao cố định cho tổ chăm buồng có hiệu lực đến khi đổi, không phải giao lại mỗi vòng.

**Bảng màu dây và thu hoạch**

- **FR-016**: Với mỗi lô và đợt màu dây, hệ thống PHẢI cho thấy số đã cắt, đã bao, đã hủy, đã thu, còn trên cây và tuổi tính bằng tuần. Cùng một màu ở hai chu kỳ 12 tuần là hai đợt riêng.
- **FR-017**: Đợt đến tuổi thu theo bộ tham số đang hiệu lực PHẢI nằm trong danh sách cần thu của tuần.
- **FR-018**: Thu hoạch ghi theo lô và đợt màu, gồm số buồng và số kg.
- **FR-019**: Không ghi được thu hoạch ở lô đang cách ly thuốc.
- **FR-020**: Không ghi được số thu nhiều hơn số còn trên cây của đợt màu đó.

**Xưởng đóng gói**

- **FR-021**: Xưởng ghi theo ca: buồng và kg nhận theo lô và đợt màu, thùng ra theo quy cách, phụ phẩm, hao hụt.
- **FR-022**: Hệ thống PHẢI tính kg/buồng, thùng/buồng và tỷ lệ đóng gói theo lô và đợt màu; ca nhận nhiều lô thì chia theo kg nhận.
- **FR-023**: Từ một ca đóng gói PHẢI truy ngược được về lô, đợt màu, ngày thu và các lần phun thuốc trước ngày thu.

**Dự thu**

- **FR-024**: Dự thu giữ cách tính và quy tắc đã chốt ở spec 001 (FR-009 đến FR-028 của spec 001), nhưng đọc từ sổ lô.
- **FR-025**: Toàn hệ thống chỉ có một con số dự thu; mọi màn có số dự thu dùng chung con số đó.
- **FR-026**: Mỗi tuần PHẢI có một bản chốt dự thu, đúng như số liệu đã có trước 0 giờ thứ Hai, kể cả khi không ai mở trang trong tuần.
- **FR-027**: Tham số đề xuất lấy từ thu hoạch và đóng gói thật, chỉ áp dụng khi người có quyền duyệt.

**Báo cáo**

- **FR-028**: Có ba màn báo cáo theo người xem: Sáng nay, Tuần, Tháng, với nội dung như User Story 5.
- **FR-029**: Mỗi số là một thẻ. Bấm thẻ mở chi tiết trong hộp. Mọi chi tiết xuất được Excel.
- **FR-030**: Bản đồ lô tô màu theo tình trạng: quá hạn chăm sóc, đang cách ly, có đợt màu đến tuổi thu, chưa báo cáo.
- **FR-031**: Lọc được theo khu, lô, tổ, tuần và tháng.

**Tiền khoán**

- **FR-032**: Tiền khoán tính từ các dòng đã xác nhận của sổ lô theo cách trả của từng việc (khoán số lượng; khoán cả lô sau khi nghiệm thu đạt; công nhật theo chấm công), chụp đơn giá lúc xác nhận. Tiền khoán bắt đầu tính bằng sổ lô khi bản mới chạy; không có mốc 01/12/2026 phải giữ.
- **FR-033**: Tổ trưởng và người làm xem được số tiền khoán tạm tính của mình ngay khi dòng được xác nhận.

**Danh mục và menu**

- **FR-034**: Danh mục việc PHẢI có: nhóm (vườn, phun bón, buồng, thu hoạch), đơn vị, vòng, cách trả, có gắn màu dây hay không, mức trần.
- **FR-035**: Cả mảng trên máy tính gom lại tối đa 7 mục menu: Hôm nay, Giao việc, Màu dây & thu hoạch, Xưởng, Dự thu, Báo cáo, Thiết lập.

**Dọn sạch đồ cũ**

- **FR-037**: Toàn bộ bảng dữ liệu, màn hình, mục menu và mã đời cũ của mảng này PHẢI bị xóa hẳn, không chỉ ẩn. Gồm bốn nhóm: ghi chép vườn cũ; thu hoạch, chất lượng, đóng gói cũ; dự thu, kế hoạch, định mức cũ; nhập từ OneDrive và chuyển đổi từ hệ thống cũ. Danh sách đủ ở [cleanup.md](cleanup.md).
- **FR-038**: Trước khi xóa, hệ thống PHẢI sao lưu và xuất toàn bộ dữ liệu của từng bảng ra tệp lưu trữ, kèm số dòng và mã kiểm. Nếu một bảng có dữ liệu gắn với chứng từ kế toán đã ghi sổ thì dừng và báo chủ vườn trước.
- **FR-039**: Các phần khác đang dùng đồ cũ PHẢI được chuyển sang nguồn mới hoặc bỏ chức năng tương ứng, không để lỗi:
  - giá thành tập theo lô, bỏ chiều kế toán "Vụ", số vụ ghi kèm;
  - nhập kho thành phẩm theo ca đóng gói;
  - kế hoạch tài chính đọc dự thu chung;
  - chi phí công theo lô lấy từ sổ lô;
  - kho bỏ chế độ xuất theo kế hoạch ngày và phần nhu cầu lấy từ kế hoạch cũ;
  - Vườn & lô bỏ lớp thửa.
- **FR-040**: Kiểm tra sâu bệnh PHẢI là một việc trong báo cáo ngày, gồm bệnh, số cây bị và mức độ. Việc này thay cho màn kiểm tra sâu bệnh cũ.

### Key Entities

- **Lô chăm sóc**: khu, diện tích, số cây, vụ hiện tại, tổ phụ trách, trạng thái cách ly.
- **Việc**: tên, nhóm, đơn vị, vòng, cách trả, có gắn màu dây hay không, mức trần.
- **Dòng sổ lô**: một việc trong một ngày ở một lô; số lượng, đợt màu (nếu có), vật tư và liều (nếu có), tổ, người làm theo buổi, người nhập, trạng thái, lịch sử sửa.
- **Báo cáo ngày của tổ**: các dòng sổ lô của một tổ trong một ngày, người gửi, người xác nhận.
- **Giao lô**: lô, việc, tổ, ngày giao, hạn; hoặc giao cố định cho tổ chăm buồng.
- **Vòng chăm sóc**: lô và việc, lần xong gần nhất, ngày đến hạn, số ngày quá hạn.
- **Đợt màu dây**: lô, màu, tuần cắt, lần cắt, chu kỳ màu; số đã cắt, đã bao, đã hủy, đã thu, còn trên cây.
- **Ca đóng gói**: ngày, ca, buồng và kg nhận theo lô và đợt màu, thùng, phụ phẩm, hao hụt.
- **Bộ tham số dự thu** và **bản chốt dự thu**: như spec 001.
- **Tệp lưu trữ đồ cũ**: dữ liệu của từng bảng bị xóa, kèm số dòng, mã kiểm và ngày xuất.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sau 2 tuần áp dụng cho Đội khu A + B, ít nhất 95% tổ-ngày có báo cáo được xác nhận trước 10 giờ sáng hôm sau.
- **SC-002**: Nhập báo cáo một ngày cho một tổ làm 5 lô mất dưới 10 phút.
- **SC-003**: 100% việc trên lô được nhập trong báo cáo ngày; không việc nào phải nhập ở màn khác.
- **SC-004**: 100% con số trên báo cáo, dự thu và tiền khoán truy ngược được về dòng sổ lô gốc.
- **SC-005**: Không có lần ghi thu hoạch nào ở lô đang cách ly.
- **SC-006**: Mỗi tuần có đúng một bản chốt dự thu, kể cả tuần không ai mở trang.
- **SC-007**: Quản lý vườn trả lời được "lô nào quá hạn việc gì" và "tuần này cần thu bao nhiêu buồng ở lô nào" trong dưới 1 phút.
- **SC-008**: Sai số dự thu giữ mục tiêu của spec 001: ±10% cho 4 tuần tới, ±15% cho 12 tuần tới, ở cấp toàn vườn.
- **SC-009**: Số mục menu của cả mảng giảm từ khoảng 16 xuống tối đa 7 (không tính Vườn & lô).
- **SC-010**: Sau khi nối xưởng, ít nhất 90% đợt màu đã thu có kg/buồng và thùng/buồng thật.
- **SC-011**: Mảng vườn còn tối đa 25 bảng dữ liệu, giảm từ 99. Không còn mã, màn hình hay mục menu nào trỏ tới bảng đã xóa.
- **SC-012**: Sổ cái, tồn kho và bảng lương của các tháng đã khóa không thay đổi sau khi dọn.

## Assumptions

- Hiện trạng đã kiểm tra ngày 10/11/2026:
  - Bản đang chạy là bản ngày 09/11/2026, gồm phiếu giao việc theo lô (làm lại ngày 31/10) và sổ buồng của spec 001. Chủ vườn xác nhận ngày 10/11/2026: mảng này mới là bản thử, chưa vận hành.
  - Đến ngày 09/11, hệ thống thật chưa có báo cáo ngày nào; 9 tổ chưa có tài khoản; sổ cắt bắp đầu kỳ có 593 buồng ở khu A.
  - Tổ trưởng phải nhập ở hai màn với ba cách: tab Buồng cho chích bắp, cắt bắp, hủy và thu hoạch; phiếu trong Hôm nay cho bao buồng, tỉa, chống đổ, việc vườn và phun bón; riêng chọn chồi báo theo ha trên phiếu Chọn F.
  - Mảng này đang có khoảng 50 bảng dữ liệu (kể cả bảng con), thuộc ba lớp làm ở ba thời điểm, chồng lên nhau.
  - Thu hoạch nhập qua sổ buồng không kiểm tra cách ly thuốc; chỉ cách ghi thu hoạch cũ có kiểm tra.
  - Xưởng ghi tổng theo ca (kg vào, thành phẩm, phụ phẩm, hao hụt, số thùng), không gắn với lô.
  - "Lịch chăm sóc theo lô" đang tính từ cách dự thu cũ, theo số cây và ngày trổ ước tính theo khu.
  - Còn 9 nơi đọc dự thu theo cách cũ (việc T040 của spec 001 chưa làm).
  - Bản chốt dự thu sáng thứ Hai chưa tự chạy trên máy chủ thật.
  - Cả mảng có khoảng 16 mục menu, chưa tính Vườn & lô (đất, bản đồ), phần này giữ riêng.
- Giữ các quyết định chủ vườn đã chốt: lô là đơn vị nhỏ nhất; nhập liệu và xem số bằng thẻ và hộp, không bảng phẳng; lịch 12 màu dây theo tuần, hai lần cắt mỗi tuần; thứ tự công đoạn chích bắp, chống đổ, tỉa, cắt bắp, bao buồng; tham số khởi đầu và mục tiêu sai số của spec 001; quy tắc tiền khoán hiện hành.
- Vòng chăm sóc khởi đầu do quản lý vườn nhập; việc chưa có vòng thì không hiện đến hạn hay quá hạn.
- Cân được theo lô và màu dây khi thu hoạch (đã xác nhận ở spec 001).
- Áp dụng trước cho Đội khu A + B; khu D, E bổ sung qua danh mục lô.
- Có wifi ở văn phòng; không cần chạy khi mất mạng hẳn, chỉ cần không mất số đang nhập.
- Nếu dùng chụp ảnh phiếu giấy, ảnh được gửi ra dịch vụ đọc ảnh bên ngoài, giống phần đọc chứng từ mua hàng đang dùng.
- Cách hạch toán giá thành giữ nguyên, chỉ đổi hai điểm: bỏ chiều "Vụ" và nhập kho thành phẩm theo ca đóng gói. Cách nhập kho thu hoạch cũ (theo lô thu hoạch, cần bật quản lý theo lô hàng) chưa từng chạy trên bản thật.
- Lứa thu đầu dự kiến cuối tháng 12/2026. Phần nhập kho thành phẩm theo ca phải chạy được trước thời điểm đó.
- Ngoài phạm vi: kế hoạch bán hàng và phân bổ đơn hàng; tưới; đếm từng buồng bằng mã riêng; định mức vật tư theo khu và tuổi cây (định mức cũ bị xóa, nếu cần thì làm lại ở spec khác).
