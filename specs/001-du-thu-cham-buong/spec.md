# Feature Specification: Dự thu chuối từ số liệu chăm sóc buồng hằng ngày

**Feature Branch**: `nghien-cuu/du-thu`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "Cải tiến tính năng dự thu chuối từ số liệu cắt bắp, chích bắp, số liệu chọn chồi và tuổi cây; làm bài bản cả phần nhập liệu chăm sóc buồng hằng ngày."

## Clarifications

### Session 2026-11-09

- Q: Ghi nhận theo lô hay theo khu? → A: Theo lô.
- Q: Số buồng đã có ngoài vườn trước ngày áp dụng lấy thế nào? → A: Không kiểm đếm lại. Nhập từ sổ cắt bắp của vườn (file "CẮT BẮP FARM 222").
- Q: Số cây và tuổi cây lấy từ đâu? → A: Từ số đã có trong hệ thống (64 lô, 530.373 cây).
- Q: Cột "(RÚT)" trong sổ cắt bắp là gì? → A: Lần cắt 1 trong tuần (thứ 3-4, thắt nút); cột còn lại là lần 2 (thứ 6-7).
- Q: Mục tiêu sai số? → A: ±10% cho 4 tuần tới và ±15% cho 12 tuần tới.
- Q: Dự thu vụ sau lấy số lượng từ đâu, có đếm chồi không? → A: Lấy từ số kiểm kê, không đếm chồi. Chọn chồi chỉ ghi ngày và diện tích đã làm.
- Q: Quản lý đến mức nào? → A: Lô là đơn vị nhỏ nhất, không dùng thửa tưới. Vụ gắn trực tiếp vào lô. Vụ 1 là vụ trồng mới (đã thu xong); toàn bộ 64 lô hiện ở vụ 2.
- Q: Ai nhập, ai xác nhận? → A: Anh Hải giao việc và xác nhận; tổ trưởng nhập.
- Q: Khu D, E? → A: Làm sau; hệ thống có danh mục theo lô để nhập về sau.
- Q: Có cân được theo lô và màu dây khi thu hoạch không? → A: Có.
- Q: Số cây khu A trong hệ thống là gì? → A: Là số kiểm kê; số cây trong sổ cắt bắp không dùng.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ghi chăm sóc buồng hằng ngày theo lô (Priority: P1)

Cuối ngày, tổ trưởng chăm buồng mở điện thoại, chọn lô và nhập số đã làm trong ngày cho từng việc: chọn chồi, chích bắp, cắt bắp, bao buồng, chống đổ, và số buồng bị loại kèm lý do. Khi nhập cắt bắp, màu dây của tuần được điền sẵn. Đội trưởng xác nhận báo cáo của các tổ.

**Why this priority**: Đây là nguồn số liệu của toàn bộ dự thu. Hiện chưa có số liệu chăm buồng nào trong hệ thống, nên không có bước này thì mọi cải tiến dự thu đều không có đầu vào.

**Independent Test**: Một tổ nhập một ngày làm việc trên 3 lô. Đội trưởng xác nhận. Kiểm tra được số lũy kế theo lô, theo việc và theo màu dây khớp với số đã nhập.

**Acceptance Scenarios**:

1. **Given** tổ được phân chăm buồng lô A5, **When** tổ trưởng nhập cắt bắp 120 buồng ngày trong tuần màu Đỏ, **Then** hệ thống ghi 120 buồng màu Đỏ cho lô A5 mà tổ trưởng không phải chọn màu.
2. **Given** lô A5 đã cắt bắp 120 buồng màu Đỏ và đã bao 100, **When** tổ trưởng nhập bao thêm 30 buồng màu Đỏ, **Then** hệ thống báo vượt số đã cắt và không cho xác nhận nếu không sửa hoặc ghi lý do.
3. **Given** tổ trưởng nhập loại 5 buồng màu Đỏ, **When** chưa chọn lý do (gãy đổ, sâu bệnh, buồng xấu…), **Then** hệ thống yêu cầu chọn lý do trước khi lưu.
4. **Given** báo cáo đã được đội trưởng xác nhận, **When** cần sửa số, **Then** việc sửa phải ghi lý do và vẫn xem lại được số cũ.

---

### User Story 2 - Dự thu 13 tuần tới từ buồng đã cắt bắp (Priority: P2)

Quản lý vườn mở màn dự thu và thấy số buồng, số kg dự kiến thu theo từng tuần trong 13 tuần tới, theo lô và theo màu dây, tính từ số buồng đã thực sự cắt bắp trừ phần đã loại.

**Why this priority**: Đây là phần dự thu chắc chắn nhất và có giá trị ngay cho việc xếp nhân công thu hoạch, xưởng đóng gói và cam kết bán hàng.

**Independent Test**: Nhập cắt bắp mẫu cho 2 màu dây ở 2 lô, xem tuần thu dự kiến và số buồng có đúng theo số đã nhập trừ số loại, cộng số ngày từ cắt bắp đến thu.

**Acceptance Scenarios**:

1. **Given** lô A5 cắt 120 buồng màu Đỏ tuần 46 và thời gian từ cắt bắp đến thu là 65 ngày, **When** xem dự thu, **Then** 120 buồng (đã áp tỷ lệ hao hụt) nằm ở tuần thu tương ứng, ghi rõ lô và màu Đỏ.
2. **Given** vừa nhập loại 5 buồng màu Đỏ ở lô A5, **When** tải lại dự thu, **Then** số dự thu của màu đó giảm tương ứng.
3. **Given** một con số trên màn dự thu, **When** bấm vào, **Then** thấy được các ngày cắt bắp, số buồng và tham số đã tạo ra con số đó.

---

### User Story 3 - Dự thu xa hơn từ chích bắp, chọn chồi và tuổi cây (Priority: P3)

Ban giám đốc xem dự thu đến 12 tháng tới. Với mỗi lô, hệ thống dùng số liệu gần với thu hoạch nhất đang có: đã cắt bắp, rồi đã chích bắp, rồi đã chọn chồi, cuối cùng là tuổi cây. Mỗi phần số liệu ghi rõ nguồn và mức tin cậy.

**Why this priority**: Phục vụ kế hoạch tài chính và hợp đồng bán hàng, nhưng phụ thuộc vào số liệu của Story 1 và độ chính xác thấp dần theo thời gian.

**Independent Test**: Tạo 4 lô, mỗi lô chỉ có một loại số liệu (cắt bắp / chích bắp / chọn chồi / tuổi cây), kiểm tra mỗi lô dùng đúng nguồn và hiện đúng mức tin cậy.

**Acceptance Scenarios**:

1. **Given** một lô đã có số chích bắp nhưng chưa cắt bắp, **When** xem dự thu, **Then** số buồng lấy từ số chích bắp nhân tỷ lệ đạt, mốc thu tính từ ngày chích, đánh dấu tin cậy "khá".
2. **Given** một lô chỉ có tuổi cây và số cây, **When** xem dự thu, **Then** con số được đánh dấu tin cậy "thấp" và tách riêng khỏi phần đã có số liệu thực tế trong tổng.
3. **Given** một đợt cây đã có số cắt bắp, **When** tổng hợp dự thu, **Then** đợt đó không bị tính thêm lần nữa từ số chích bắp, chọn chồi hay tuổi cây.

---

### User Story 4 - So dự thu với thực tế và hiệu chỉnh tham số (Priority: P4)

Khi thu hoạch, tổ thu ghi số buồng và kg thu theo lô và màu dây. Quản lý xem sai số giữa dự thu và thực tế, và duyệt tham số mới (số ngày từ cắt bắp đến thu, tỷ lệ hao hụt, kg/buồng) dựa trên số thực tế đó.

**Why this priority**: Giúp dự thu chính xác dần, nhưng chỉ có ý nghĩa sau khi các lứa cắt bắp đầu tiên được thu hoạch.

**Independent Test**: Nhập thu hoạch mẫu cho một màu dây, kiểm tra báo cáo sai số và tham số đề xuất đúng theo số mẫu; tham số chỉ áp dụng sau khi được duyệt.

**Acceptance Scenarios**:

1. **Given** màu Đỏ lô A5 có 120 buồng cắt bắp, thu được 114 buồng, 2.280 kg, **When** xem đối chiếu, **Then** thấy tỷ lệ thu 95%, 20 kg/buồng và số ngày thực tế từ cắt bắp đến thu.
2. **Given** hệ thống đề xuất tham số mới, **When** chưa được duyệt, **Then** dự thu vẫn dùng bộ tham số đang có hiệu lực, và các lần dự thu trước vẫn xem lại được theo tham số cũ.

---

### User Story 5 - Biết ngay lô nào chưa báo hoặc số liệu bất thường (Priority: P5)

Đội trưởng và quản lý vườn mỗi sáng thấy danh sách lô chưa có báo cáo hôm trước, và các số bất thường như tỷ lệ chích bắp vượt số cây, hay lô có cây đến tuổi trổ mà nhiều ngày không có số.

**Why this priority**: Giữ chất lượng số liệu lâu dài, nhưng làm sau khi có luồng nhập liệu.

**Independent Test**: Bỏ trống báo cáo của một lô trong một ngày và nhập một số vượt tổng số cây, kiểm tra cả hai xuất hiện trong danh sách cảnh báo.

**Acceptance Scenarios**:

1. **Given** lô B3 được phân cho tổ 2 và hôm qua không có báo cáo, **When** đội trưởng mở màn hình đầu ngày, **Then** lô B3 nằm trong danh sách chưa báo.
2. **Given** lũy kế chích bắp của một đợt vượt số cây của lô, **When** xác nhận báo cáo, **Then** hệ thống cảnh báo rõ lô và con số.

---

### Edge Cases

- Tuần 43/2026 vườn dùng dây chống đổ màu xanh thay dây Đỏ vì chưa có dây màu: thu hoạch phải nhận ra lô này là màu Đỏ của tuần 43.
- Tuần chuyển màu dây: nhập cắt bắp bù cho ngày trước phải lấy màu theo ngày làm việc, không theo ngày nhập.
- Hai màu dây lặp lại sau 12 tuần: phải phân biệt được cùng màu nhưng khác đợt cắt bắp.
- Buồng cắt bắp trước ngày áp dụng chưa có trong hệ thống (số liệu đầu kỳ).
- Một lô do hai tổ cùng làm trong một ngày: không được tính trùng.
- Sửa hoặc huỷ số cắt bắp sau khi đã bao buồng hoặc đã thu hoạch màu đó.
- Thu hoạch nhiều hơn số đã cắt bắp của một màu (đếm sai hoặc nhầm màu).
- Thu rải nhiều ngày cho một màu: cửa sổ thu kéo dài, không dồn vào một ngày.
- Lô bị gió đổ hàng loạt: loại số lớn một lần và dự thu giảm ngay.
- Thay đổi số lô, gộp lô, hoặc cây phá bỏ trồng lại làm đổi tuổi cây.
- Mùa khô và mùa mưa có số ngày từ cắt bắp đến thu khác nhau.

## Requirements *(mandatory)*

### Functional Requirements

**Nhập liệu chăm sóc buồng**

- **FR-001**: Hệ thống PHẢI cho ghi hằng ngày theo từng lô chăm sóc (64 lô, không gộp theo khu) các việc: chọn chồi, chích bắp, cắt bắp, bao buồng, tỉa, chống đổ, thu hoạch.
- **FR-002**: Mỗi lần ghi PHẢI có ngày làm việc, lô, việc, số lượng, tổ thực hiện và người nhập.
- **FR-003**: Cắt bắp PHẢI tự gắn màu dây theo tuần của ngày làm việc và lần cắt trong tuần (lần 1 thứ 3-4 có thắt nút đầu cuối dây, lần 2 thứ 6-7 không thắt nút), và đợt cắt bắp phải phân biệt được giữa hai chu kỳ màu.
- **FR-004**: Thứ tự công đoạn của vườn là chích bắp, chống đổ, tỉa, cắt bắp, bao buồng. Bao buồng và thu hoạch PHẢI gắn với màu dây, tổng lũy kế theo lô và màu không được vượt số đã cắt bắp. Chống đổ và tỉa làm trước cắt bắp nên không chọn màu dây, trần báo theo số cây của lô (chủ vườn chốt ngày 09/11/2026; không dùng số đã chích làm trần vì số chích trước ngày áp dụng không nhập bù).
- **FR-005**: Việc loại buồng PHẢI ghi số lượng, màu dây (nếu đã cắt bắp) và lý do từ danh mục.
- **FR-006**: Đội trưởng PHẢI xác nhận số của các tổ theo ngày; người nhập không được tự xác nhận số của mình. Số đã xác nhận chỉ sửa được khi có lý do và giữ lại lịch sử.
- **FR-007**: Nhập liệu PHẢI dùng được trên điện thoại. Tổ trưởng nhập nhiều lô trên một màn hình trong một lần, không phải tạo phiếu và không phải gắn từng người vào từng lô đối với các việc công nhật (chích bắp, cắt bắp, thu hoạch). Không nhập cùng một số ở hai nơi.
- **FR-008**: Hệ thống PHẢI nhận số đầu kỳ từ sổ cắt bắp của vườn theo lô, tuần, màu dây và lần cắt, không cần kiểm đếm lại. Mỗi dòng phải giữ nguồn là file đó; ngày cắt lấy theo khoảng ngày của lần cắt. Dòng có lô hoặc số không hợp lệ phải báo ra, không tự bỏ qua. Số chích bắp và trổ chưa cắt bắp trước ngày áp dụng không nhập bù, được ghi từ ngày áp dụng.

**Tính dự thu**

- **FR-023**: Chọn chồi PHẢI ghi theo ngày và diện tích đã làm trong lô, không bắt đếm từng chồi. Số chồi của phần đã làm được ước tính bằng số cây kiểm kê nhân tỷ lệ diện tích đã làm trên diện tích lô, và phải ghi rõ là ước tính.
- **FR-024**: Danh mục lô PHẢI cho quản lý vườn nhập và sửa về sau, trên màn hình hoặc bằng file Excel, các thông tin: số cây, vụ hiện tại, ngày trổ dự kiến, ngày chọn chồi. Khu D, E được bổ sung qua danh mục này khi áp dụng.
- **FR-009**: Dự thu của mỗi đợt PHẢI dùng nguồn gần thu hoạch nhất đang có, theo thứ tự: đã cắt bắp, đã chích bắp, đã chọn chồi, tuổi cây và số cây.
- **FR-010**: Một đợt đã có số ở tầng cao hơn PHẢI không còn được tính ở tầng thấp hơn, và tổng dự thu không được đếm trùng.
- **FR-011**: Số cây và tuổi cây của lô PHẢI lấy từ số đang có trong hệ thống (số cây đã chốt theo lô; ngày trồng và ngày trổ ước tính theo khu). Mỗi con số dựa trên tuổi cây phải ghi rõ đó là số ước tính theo khu.
- **FR-025**: Số chích bắp trước ngày áp dụng không nhập bù. Các đợt cắt bắp trong thời gian từ ngày áp dụng đến hết số ngày từ chích đến cắt không được trừ vào số đã chích.
- **FR-026**: Chọn chồi của lô chưa có chích bắp trong vụ hiện tại thuộc vụ hiện tại; lô đã có chích bắp thì thuộc vụ kế tiếp.
- **FR-027**: Buồng loại đã ghi thực tế PHẢI được tính vào tỷ lệ hao hụt, không trừ hai lần.
- **FR-028**: Phần dự thu theo số cây có thời điểm đã qua mà chưa có số thực tế PHẢI được chuyển sang các tuần tới và cảnh báo.
- **FR-012**: Dự thu PHẢI cho kết quả theo tuần và theo tháng, theo lô, khu và toàn vườn, gồm số buồng, kg và quy đổi thùng.
- **FR-013**: Thu hoạch của một đợt PHẢI trải theo cửa sổ nhiều ngày, không dồn vào một ngày.
- **FR-014**: Mỗi con số dự thu PHẢI ghi rõ nguồn, mức tin cậy và truy ngược được về số liệu gốc cùng bộ tham số đã dùng.
- **FR-015**: Khi số liệu gốc thay đổi, dự thu PHẢI cập nhật theo trong cùng ngày.
- **FR-016**: Các tham số (số ngày giữa các mốc, tỷ lệ đạt, kg/buồng theo vụ, cửa sổ thu) PHẢI có phiên bản và ngày hiệu lực, phải được duyệt mới áp dụng, và có thể khác nhau theo lô hoặc theo mùa.
- **FR-017**: Hệ thống PHẢI lưu ảnh chụp mỗi lần chốt dự thu để so sánh về sau, kể cả sau khi tham số thay đổi.

**Đối chiếu và kiểm soát**

- **FR-018**: Hệ thống PHẢI so dự thu đã chốt với thực tế thu theo lô, màu dây và tuần, cho biết sai số về số buồng, kg và số ngày.
- **FR-019**: Hệ thống PHẢI đề xuất tham số mới từ số thực tế, và chỉ áp dụng khi người có quyền duyệt.
- **FR-020**: Hệ thống PHẢI hiển thị danh sách lô chưa báo cáo và các số bất thường (vượt số cây, vượt số cắt bắp, lô đến tuổi trổ mà không có số).
- **FR-021**: Dự thu chính thức PHẢI chỉ dùng số đã xác nhận; số chưa xác nhận chỉ được hiển thị tách riêng.
- **FR-022**: Phải thay thế, không chạy song song, các cách tính dự thu đang tồn tại, để toàn hệ thống chỉ có một con số dự thu.

### Key Entities

- **Lô chăm sóc**: đơn vị canh tác, có khu, diện tích, số cây, giống, tuổi cây và tổ chăm sóc.
- **Đợt cây (lứa)**: nhóm cây cùng mốc trong một lô, là đối tượng được theo dõi xuyên suốt từ chọn chồi đến thu hoạch.
- **Ghi nhận chăm sóc buồng**: một việc trong một ngày, ở một lô, số lượng, tổ, trạng thái xác nhận.
- **Đợt cắt bắp theo màu dây**: lô, màu dây, tuần, lần cắt trong tuần và chu kỳ màu, số buồng; là mốc chính của dự thu ngắn hạn.
- **Buồng loại bỏ**: số lượng, màu dây, lý do, ngày.
- **Thu hoạch thực tế**: lô, màu dây, ngày, số buồng, kg.
- **Bộ tham số dự thu**: số ngày giữa các mốc, tỷ lệ đạt, kg/buồng, phạm vi áp dụng, ngày hiệu lực, người duyệt.
- **Bản dự thu đã chốt**: ảnh chụp kết quả theo tuần tại một thời điểm, gắn với bộ tham số.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tổ trưởng hoàn tất báo cáo chăm buồng của một lô trong dưới 2 phút.
- **SC-002**: Sau 4 tuần áp dụng, ít nhất 95% số ngày-lô được phân công có báo cáo đã xác nhận trước 10 giờ sáng hôm sau.
- **SC-003**: Sai số dự thu số buồng theo tuần, đo trên 4 tuần tới, không quá ±10% ở cấp toàn vườn sau lần hiệu chỉnh đầu tiên.
- **SC-004**: Sai số dự thu số buồng theo tuần, đo trên 12 tuần tới, không quá ±15% ở cấp toàn vườn.
- **SC-005**: 100% con số dự thu truy ngược được về số liệu gốc và bộ tham số.
- **SC-006**: Không có đợt cây nào được tính hai lần trong tổng dự thu.
- **SC-007**: Quản lý xem được dự thu 13 tuần và lô chưa báo cáo mà không cần file Excel ngoài.

## Assumptions

- Hiện trạng đã kiểm tra ngày 09/11/2026:
  - Cách tính dự thu đang dùng chỉ dựa vào số cây theo lô, ngày trổ ước tính và tỷ lệ cố định; không đọc số liệu chăm sóc buồng. Cách tính theo nhật ký chặt mẹ đã bị tắt.
  - Trên hệ thống thật, số bản ghi của báo cáo ngày, thao tác buồng, chọn chồi và thu hoạch đều bằng 0. Có 64 lô với 530.373 cây, 358 dòng nhật ký chặt mẹ, và lịch màu dây đã có đến hết 2027.
  - Báo cáo giấy của đội hiện ghi việc chăm buồng theo khu (A, B…) và theo số lượng trong ngày, chưa có màu dây.
  - Sổ cắt bắp của vườn có 593 buồng cắt ở khu A (lô A1 đến A13), tuần 43 đến 45/2026. Các cột số cây đã cắt, số cây còn lại và tỷ lệ trong sổ bị lỗi công thức nên không dùng.
  - Số cây khu A trong hệ thống (108.512) là số kiểm kê, chủ vườn xác nhận ngày 09/11/2026. Cột số cây trong sổ cắt bắp (105.632) không dùng.
  - Hệ thống chưa có ngày trồng thật theo lô; tuổi cây hiện suy theo khu, mỗi khu cách nhau một tháng.
- Toàn bộ nhập liệu và dự thu chỉ quản lý đến lô; thửa tưới không tham gia. Mỗi lô có một số vụ hiện tại, do quản lý vườn chốt khi lô chuyển vụ.
- Lịch 12 màu dây theo tuần hiện có được giữ nguyên.
- Số kiểm kê được cập nhật mỗi vụ một lần để phản ánh cây chết, đổ ngã và gốc không có chồi.
- Giá trị khởi đầu của tham số lấy từ bộ đang dùng: trổ đến chích 5 ngày, chích đến cắt bắp 16 ngày, cắt bắp đến thu 60 đến 70 ngày (cơ sở 65), cắt bắp/cây 90%, thu/cắt bắp 97%, đóng gói/thu 98%, thành phẩm 19/20/19 kg/buồng cho vụ 1/2/3 trở đi. Các giá trị này được coi là tạm thời cho tới khi hiệu chỉnh bằng số thực tế.
- Áp dụng trước cho Đội khu A + B. Khu D, E chưa áp dụng; mốc của các khu này giữ ước tính cho tới khi nhập qua danh mục lô.
- Mỗi tổ trưởng cần có tài khoản; hiện 9 tổ chưa có.
- Bao buồng, tỉa, chống đổ vẫn báo theo phiếu vì trả khoán theo số lượng.
- Có wifi ở văn phòng, chưa cần nhập khi mất mạng; tổ trưởng có thể nhập khi có sóng trong ngày.
- Việc tính tiền khoán theo báo cáo ngày đã có và giữ nguyên quy tắc hiện tại.
- Ngoài phạm vi: kế hoạch bán hàng, phân bổ đơn hàng theo dự thu, tính chi phí theo lô, và đếm từng buồng bằng mã riêng.
