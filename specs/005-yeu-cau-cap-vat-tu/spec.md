# Feature Specification: Yêu cầu cấp vật tư từ vườn đến Kho

**Feature Branch**: `005-yeu-cau-cap-vat-tu`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "Chưa màn nào trong Lotus lập được 'yêu cầu cấp vật tư', mà giờ đó là nguồn duy nhất cho xuất theo yêu cầu (chỉ lập được trong Desk ERPNext). Có cần làm màn này không?" Chủ vườn trả lời: có, làm.

## Ý tưởng chính

Spec 002 đã bỏ kế hoạch ngày và cách xuất "Theo kế hoạch đã duyệt". Từ 11/11/2026 Kho chỉ còn hai cách xuất: **Thủ công** và **Theo yêu cầu đã duyệt**. Cách thứ hai đọc một Material Request loại Material Issue đã duyệt (docstatus 1). Trên site thật chưa có yêu cầu nào như vậy, vì không màn Lotus nào lập được.

Spec này làm màn lập và duyệt **yêu cầu cấp vật tư** ở chỗ việc được giao và làm: **Công việc** trên máy tính và **/work** trên điện thoại. Kho nhận yêu cầu đã duyệt trong màn Xuất kho đang có.

1. Tổ trưởng hoặc đội trưởng lập yêu cầu: một việc, một kho cấp, một ngày cần, nhiều lô; mỗi dòng là một vật tư cho một lô.
2. Người duyệt (đội trưởng, hoặc quản lý vườn) duyệt, giảm số hoặc trả lại. Không ai tự duyệt yêu cầu của mình. Duyệt là submit chứng từ.
3. Kho thấy "Cấp theo yêu cầu (N)", lập phiếu xuất theo yêu cầu, cấp đủ hoặc cấp từng phần. Phiếu xuất mang đúng lô và việc của yêu cầu, nên chi phí 621 vào đúng lô và đúng việc.
4. Người lập và người duyệt theo dõi được: đã cấp bao nhiêu, còn bao nhiêu, phiếu xuất nào.

Không tạo DocType mới. Yêu cầu là Material Request của ERPNext. Các phần đã có đọc nó mà không phải đổi: chế độ xuất "Theo yêu cầu đã duyệt", khóa cấp vượt trong `warehouse_issue.py`, màn "Nhu cầu cấp cho công việc", bản in "PHIẾU ĐỀ XUẤT CẤP VẬT TƯ", và số đã cấp (`ordered_qty`, `per_ordered`, `status`) do ERPNext tự tính.

## Clarifications

### Session 2026-11-11

Chủ vườn chỉ trả lời "có, làm", không trả lời chi tiết. Các điểm dưới đây là mặc định do người viết spec chọn, kèm lý do. Chủ vườn có thể đổi bất kỳ điểm nào trước khi làm.

- Q: Lập yêu cầu ở đâu? → A: Ở Công việc (máy tính) và /work (điện thoại), chỗ việc được giao. Kho chỉ nhận và cấp. Lý do: người biết cần gì, cho lô nào, là tổ và đội; Kho không biết lô nào cần phun.
- Q: Ai được lập? → A: Tổ trưởng cho tổ của mình; đội trưởng cho cả đội hoặc cho một tổ của đội (nhập hộ, vì 9 tổ chưa có tài khoản tổ trưởng); quản lý vườn cho mọi đội của vườn được cấp. Kỹ thuật vườn chỉ xem. Lý do: giống quyền của báo cáo ngày (`field_report.access`).
- Q: Ai duyệt, mấy bước? → A: Một bước.
  - Yêu cầu của tổ trưởng: đội trưởng của đội duyệt; quản lý vườn duyệt thay được.
  - Yêu cầu của đội trưởng (kể cả nhập hộ): quản lý vườn duyệt.
  - Yêu cầu của quản lý vườn: một quản lý vườn khác duyệt.
  - Không ai tự duyệt. Lý do: giống luật "không ai xác nhận dòng mình nhập" của báo cáo ngày và nguyên tắc III. Đội trưởng là người giao việc và biết liều.
- Q: Có dùng chuỗi ký 4 bước "Phiếu đề xuất cấp vật tư" (Người đề xuất → Phụ trách bộ phận → Thủ kho → Giám đốc NT) không? → A: Không ở bản này. Chuỗi đó nằm trong `signing.py` / `signing_rules.py` mà spec 003 đang sửa, cần ảnh chữ ký, và 4 chữ ký cho mỗi lần phun thuốc làm chậm việc ngoài vườn. Thủ kho xác nhận bằng chính phiếu xuất khi ghi sổ.
- Q: Người duyệt có được sửa số không? → A: Chỉ được giảm số hoặc bỏ dòng, phải ghi lý do. Muốn tăng thì trả lại.
- Q: Một yêu cầu gồm gì? → A: Một việc, một kho cấp, một tổ (hoặc cả đội), một ngày cần, nhiều lô. Mỗi dòng là một vật tư cho một lô. Tối đa 100 dòng. Lý do: một phiếu xuất của Kho chỉ có một kho xuất và tối đa 100 dòng; lô là đơn vị nhỏ nhất.
- Q: Đơn vị trên yêu cầu? → A: Đơn vị tồn kho của vật tư. Màn hiện quy đổi sang đơn vị đóng gói để tham khảo. Kho vẫn xuất được theo đơn vị đóng gói; phần còn lại so theo đơn vị tồn kho như hiện nay.
- Q: Sau khi duyệt có sửa được không? → A: Không. Muốn đổi thì đóng phần còn lại (hoặc hủy nếu chưa cấp gì) rồi lập yêu cầu mới; có nút "Lập lại từ yêu cầu này" để chép sẵn.
- Q: Ai đóng phần còn lại? → A: Người lập, người duyệt, quản lý vườn, hoặc Quản lý kho khi Kho không có hàng. Luôn phải ghi lý do. Không đóng được khi Kho còn phiếu xuất nháp giữ số của yêu cầu. Mở lại: người duyệt hoặc quản lý vườn, có lý do.
- Q: Yêu cầu quá ngày cần? → A: Không tự đóng. Hiện nhãn "Quá hạn chưa cấp"; người có quyền đóng thì đóng.
- Q: Yêu cầu lập trong Desk ERPNext? → A: Mọi Material Request loại Material Issue chỉ được duyệt (submit), hủy, dừng hoặc mở lại qua Lotus. Desk vẫn lưu nháp được nhưng không submit được. Lý do: nếu không chặn thì người lập tự submit trong Desk là bỏ qua bước duyệt. Site thật chưa có yêu cầu loại này nên không mất gì.
- Q: Kho có bị cấm xuất Thủ công khi đã có yêu cầu cho cùng lô và vật tư không? → A: Không cấm ở bản này. 78 phiếu xuất đến nay đều là Thủ công; cấm ngay sẽ làm tắc Kho. Xem lại sau một tháng dùng.
- Q: Kho trên điện thoại có cấp theo yêu cầu không? → A: Có, nhưng là phần sau cùng (US5), làm sau khi đã gộp màn Kho điện thoại của spec 003. Bản đầu Kho cấp trên máy tính, như 78 phiếu hiện nay.
- Q: Người ngoài vườn có in phiếu không? → A: Không ở bản này. Trang in đòi quyền in Material Request mà vai trò vườn không có, và trang in thuộc phần spec 003 vừa sửa. Kho và người dùng máy tính có quyền in thì in như hiện nay.
- Q: Có cho người vườn xem tồn kho không? → A: Có, chỉ số lượng "có thể cấp lúc này" ở kho đã chọn, không có giá trị tiền.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lập, gửi và duyệt yêu cầu cấp vật tư (Priority: P1)

Tổ trưởng tổ 3 sắp phun thuốc ở A12 và A13. Trên /work, tab **Vật tư**, bấm "Đề nghị cấp vật tư": chọn việc Phun thuốc, ngày cần, kho cấp; chọn lô A12, A13; thêm Anvil 1,5 lít mỗi lô; người nhận là mình. Bấm "Gửi duyệt". Đội trưởng nhận thông báo, mở yêu cầu trong tab Xác nhận, thấy kho còn bao nhiêu, bấm Duyệt. Yêu cầu thành "Chờ cấp".

**Why this priority**: Đây là chỗ trống duy nhất: không có yêu cầu đã duyệt thì Kho không xuất theo yêu cầu được, chi phí vật tư không gắn được việc, màn "Nhu cầu cấp cho công việc" trống.

**Independent Test**: Trên bản sao site thật, một tổ trưởng lập yêu cầu 2 vật tư × 2 lô và gửi; tổ trưởng không tự duyệt được; đội trưởng duyệt. Yêu cầu có docstatus 1, `material_request_type` = Material Issue, mỗi dòng có lô, việc, `lotus_usage_area` = mã lô, và hiện trong danh sách nguồn của Kho.

**Acceptance Scenarios**:

1. **Given** tổ trưởng tổ 3 thuộc đội khu A + B, **When** mở form, **Then** chỉ chọn được tổ 3, các lô đang hoạt động trong khu của đội, và các việc của vườn.
2. **Given** form đã chọn A12, A13 và Anvil "1,5 lít mỗi lô", **When** gửi duyệt, **Then** tạo một Material Request loại Material Issue, 2 dòng, trạng thái "Chờ duyệt", người duyệt dự kiến là đội trưởng, và đội trưởng nhận thông báo trong /work.
3. **Given** cùng yêu cầu, **When** tổ trưởng gọi duyệt (qua màn, Desk hoặc REST), **Then** bị từ chối.
4. **Given** đội trưởng mở yêu cầu, **When** giảm A13 xuống 1 lít, ghi lý do rồi duyệt, **Then** yêu cầu thành "Chờ cấp", số cũ và lý do còn trong lịch sử, tổ trưởng nhận thông báo.
5. **Given** đội trưởng muốn tăng số, **When** sửa số lên cao hơn, **Then** bị từ chối, màn gợi ý "Trả lại".
6. **Given** đội trưởng trả lại có lý do, **When** tổ trưởng mở, **Then** thấy lý do, sửa được, gửi lại được.
7. **Given** đội trưởng nhập hộ cho tổ 5 (chưa có tài khoản tổ trưởng), **When** gửi, **Then** màn báo trước "quản lý vườn sẽ duyệt", và chỉ quản lý vườn (không phải đội trưởng đó) duyệt được.
8. **Given** "Tổng 6 lít, chia theo diện tích" cho 3 lô, **When** xem trước, **Then** số mỗi lô cộng lại đúng 6 lít, sửa tay được từng lô; với đơn vị nguyên (Chai, Gói, Bao) thì chia theo phần dư lớn nhất và vẫn đủ tổng.
9. **Given** đang nhập dở trên điện thoại thì mất sóng, **When** mở lại, **Then** số đã nhập còn; bấm gửi hai lần chỉ tạo một yêu cầu.

---

### User Story 2 - Kho cấp theo yêu cầu, chi phí vào đúng lô và việc (Priority: P1)

Thủ kho mở Kho › Xuất kho, thấy "Cấp theo yêu cầu (3)". Mở danh sách, chọn yêu cầu của tổ 3, bấm "Lập phiếu xuất". Form xuất kho đang có mở sẵn ở chế độ "Theo yêu cầu đã duyệt": kho xuất, người nhận và các dòng còn lại đã điền. Kho cấp đủ hoặc một phần rồi ghi sổ. Bút toán 621 mang lô và việc của yêu cầu.

**Why this priority**: Yêu cầu chỉ có ích khi Kho cấp được theo nó và chi phí ghi đúng chỗ.

**Independent Test**: Trên bản sao site thật, Kho lập phiếu xuất từng phần cho yêu cầu đã duyệt, rồi ghi sổ. `Stock Entry Detail` có `lotus_farm_block` và `lotus_work_type` lấy từ dòng yêu cầu; GL 621 mang hai chiều đó; yêu cầu thành "Đã cấp một phần"; cấp vượt bị chặn; cấp nốt thì "Đã cấp đủ".

**Acceptance Scenarios**:

1. **Given** 3 yêu cầu đã duyệt còn số, **When** Kho mở "Cấp theo yêu cầu", **Then** thấy 3 thẻ xếp theo ngày cần (quá hạn tô đỏ), mỗi thẻ ghi số, đội/tổ, lô, việc, kho, số dòng còn, người duyệt.
2. **Given** chọn một thẻ, **When** bấm "Lập phiếu xuất", **Then** form xuất kho mở ở chế độ "Theo yêu cầu đã duyệt" với kho xuất = kho của yêu cầu, người nhận = người nhận của yêu cầu, dòng = phần còn lại, lô không sửa được.
3. **Given** Kho lưu nháp một phần, **When** người lập xem yêu cầu, **Then** thấy "Kho đang lập phiếu" và số đang giữ.
4. **Given** Kho ghi sổ, **When** xem bút toán, **Then** dòng 621 mang lô và việc của dòng yêu cầu, kể cả khi trình duyệt gửi lô khác.
5. **Given** Kho nhập số lớn hơn phần còn lại, **When** lưu, **Then** bị chặn như hiện nay.
6. **Given** Kho hủy một phiếu đã ghi sổ, **When** xem yêu cầu, **Then** phần còn lại tăng lại và người lập nhận thông báo.
7. **Given** yêu cầu đã cấp đủ, **When** Kho mở danh sách nguồn, **Then** không còn thấy yêu cầu đó.

---

### User Story 3 - Theo dõi, đóng, mở lại, hủy và thông báo (Priority: P2)

Người lập, người duyệt và quản lý vườn xem các yêu cầu của đội ở dạng thẻ: Chờ bạn duyệt, Chờ duyệt, Trả lại, Chờ cấp, Đang cấp, Đã cấp (7 ngày). Mở một yêu cầu thì thấy từng vật tư, từng lô: đề nghị, đã cấp, Kho đang lập phiếu, còn; và các phiếu xuất. Khi Kho không có hàng, người có quyền đóng phần còn lại, có lý do.

**Why this priority**: Không có phần này thì yêu cầu treo mãi và người vườn phải gọi điện hỏi Kho.

**Independent Test**: Duyệt một yêu cầu, Kho lưu nháp, thử đóng (bị chặn), Kho xóa nháp, đóng được; Kho không chọn được yêu cầu đã đóng; mở lại được; hủy một yêu cầu chưa cấp được, yêu cầu đã cấp một phần thì không hủy được. Mỗi bước có thông báo và dòng lịch sử.

**Acceptance Scenarios**:

1. **Given** đội trưởng có 2 yêu cầu chờ duyệt, **When** mở Hôm nay (máy tính) hoặc tab Xác nhận (điện thoại), **Then** thấy thẻ "2 yêu cầu vật tư chờ bạn duyệt".
2. **Given** yêu cầu đã cấp một phần, **When** người lập mở, **Then** thấy từng lô: đề nghị, đã cấp, đang lập phiếu, còn, và số phiếu xuất, ngày, người nhận.
3. **Given** Kho còn phiếu nháp giữ số, **When** người lập bấm "Đóng phần còn lại", **Then** bị chặn, màn nêu số phiếu nháp.
4. **Given** không còn phiếu nháp, **When** đóng có lý do, **Then** yêu cầu "Đã đóng", Kho không chọn được, Kho và người lập nhận thông báo.
5. **Given** yêu cầu đã đóng, **When** người duyệt mở lại có lý do, **Then** yêu cầu trở lại "Chờ cấp" hoặc "Đã cấp một phần".
6. **Given** yêu cầu đã duyệt chưa cấp gì, **When** người lập hủy có lý do, **Then** docstatus 2; nếu đã có phiếu xuất (nháp hoặc ghi sổ) thì hủy bị chặn.
7. **Given** ngày cần đã qua mà còn số, **When** xem thẻ, **Then** có nhãn "Quá hạn chưa cấp"; không tự đóng.
8. **Given** duyệt một yêu cầu cấp vật tư, **When** xem thông báo, **Then** không có thông báo "Có đề xuất mua mới" gửi người duyệt mua.

---

### User Story 4 - Điền sẵn từ phiếu giao việc, vòng chăm sóc và lần trước (Priority: P3)

Đội trưởng vừa giao việc Phun thuốc cho tổ 3 ở 4 lô. Trong phiếu giao việc, mục "Vật tư cho phiếu này" có nút "Đề nghị cấp vật tư" điền sẵn lô, việc, tổ, phiếu. Trong form, có chip "Lô đang giao việc này cho tổ (4)" và "Lô đến hạn theo vòng chăm sóc (6)", và gợi ý "Lấy như lần trước (05/11, 0,5 lít/ha)".

**Why this priority**: Giảm gõ và giảm sai liều, nhưng US1–US3 vẫn dùng được khi chưa có phần này.

**Independent Test**: Mở form từ một phiếu giao việc: lô, việc, tổ đã điền, dòng mang `lotus_work_assignment`. Chip lô đến hạn khớp `care_cycle.due`. Gợi ý lần trước ghi rõ nguồn (số yêu cầu, ngày).

**Acceptance Scenarios**:

1. **Given** phiếu giao việc Phun thuốc tổ 3 lô A12, **When** bấm "Đề nghị cấp vật tư" trong phiếu, **Then** form mở với việc, tổ, lô A12 đã chọn và dòng gắn phiếu đó.
2. **Given** phiếu đã có yêu cầu, **When** mở phiếu, **Then** thấy vật tư · đề nghị · đã cấp · còn · trạng thái.
3. **Given** cùng vật tư × lô đang ở một yêu cầu khác còn mở, **When** gửi, **Then** màn cảnh báo tên yêu cầu đó và phải xác nhận mới gửi.
4. **Given** lô đang cách ly, **When** chọn, **Then** hiện chip "cách ly đến dd/mm" để biết, không chặn.

---

### User Story 5 - Kho cấp theo yêu cầu trên điện thoại (Priority: P3)

Thủ kho ở kho vườn mở /warehouse, thấy "Cấp theo yêu cầu (N)", chọn yêu cầu, sửa số thực cấp, chọn người nhận, "Lưu & ghi sổ".

**Why this priority**: Tiện cho thủ kho ở kho vườn, nhưng máy tính đã làm được. Làm sau khi gộp màn Kho điện thoại của spec 003 để không đụng nhau.

**Independent Test**: Trên điện thoại 390px, cấp một phần một yêu cầu bằng `create_draft` và `submit_document` đang có, có bước xác nhận tồn kho đang có; yêu cầu thành "Đã cấp một phần".

**Acceptance Scenarios**:

1. **Given** 2 yêu cầu chờ cấp, **When** mở /warehouse, **Then** thấy "Cấp theo yêu cầu (2)" ở trang đầu.
2. **Given** link thông báo /warehouse?issue_request=..., **When** mở, **Then** vào thẳng yêu cầu đó.

---

### Edge Cases

**Quyền và người duyệt**
- Người lập là đội trưởng, hoặc đội chưa có đội trưởng → chỉ quản lý vườn duyệt. Người lập là quản lý vườn → quản lý vườn khác. Tự duyệt bị chặn ở máy chủ, không chỉ ẩn nút.
- Đội trưởng đổi người giữa lúc gửi và lúc duyệt → đội trưởng hiện tại hoặc quản lý vườn duyệt được; người duyệt dự kiến cập nhật khi gửi lại.
- Một người vừa là tổ trưởng vừa là đội trưởng cùng đội → coi là đội trưởng.
- Tài khoản không có đội, tổ → thông báo giống /work: "Tài khoản chưa là tổ trưởng hoặc đội trưởng…".
- Kỹ thuật vườn → chỉ xem. Người chỉ có quyền xưởng → không vào được.
- Vườn chỉ có một quản lý vườn và chính người đó lập → không ai duyệt được; màn nói rõ cần quản lý vườn khác hoặc Administrator (Administrator duyệt được nếu không phải người lập).

**Lô, việc, vật tư**
- Lô ngoài khu của đội hoặc không hoạt động → từ chối.
- Nhiều việc trong một yêu cầu → từ chối; lập hai yêu cầu.
- Cùng vật tư × lô hai lần trong một yêu cầu → từ chối, gộp lại.
- Vật tư tắt, không phải hàng tồn kho, hoặc quản lý theo lô/serial → từ chối, ghi "nhờ Kho xuất trong ERPNext".
- Chia theo diện tích mà lô thiếu `area_ha` → không dùng được cách chia đó cho lô ấy; màn nói rõ, không đoán.
- Lô nhận 0 sau khi chia đơn vị nguyên → bỏ dòng, có báo.
- Hơn 100 dòng → từ chối, gợi ý tách hai yêu cầu.
- Ngày cần ở quá khứ khi gửi hoặc khi duyệt → từ chối.

**Kho và tồn**
- Kho đã chọn không đủ hàng → cảnh báo cho người lập và người duyệt, vẫn duyệt được (yêu cầu là nhu cầu). Màn "Nhu cầu cấp cho công việc" hiện "Cần mua" như hiện nay.
- Vật tư chỉ có ở kho khác → gợi ý đổi kho hoặc lập yêu cầu riêng. Một yêu cầu một kho.
- Hai thủ kho cùng cấp một yêu cầu → khóa và số giữ của phiếu nháp trong `validate_issue` (đã có).
- Kho tắt hoặc ra khỏi công ty sau khi duyệt → Kho không cấp được → đóng và lập yêu cầu mới.
- Người nhận không còn làm việc khi cấp → Kho chọn người khác trên phiếu xuất.
- ERPNext không cho ghi sổ hoặc hủy phiếu xuất gắn yêu cầu đã dừng (Stopped) → phải mở lại trước, có lý do.

**Đồng thời và mạng**
- Màn cũ → "Yêu cầu vừa thay đổi. Mở lại." (kiểm `modified` và khóa dòng).
- Bấm hai lần hoặc mất sóng → cùng `client_event_id` trả lại cùng kết quả; cùng mã mà khác nội dung bị từ chối.
- Duyệt cần mạng; không có hàng chờ ngoại tuyến cho duyệt.

**Desk, REST và đường khác**
- Submit, hủy, dừng, mở lại một Material Request loại Material Issue ngoài Lotus → bị chặn.
- Sửa nội dung một yêu cầu đang chờ duyệt (kể cả trong Desk) → bị chặn; người lập rút lại hoặc người duyệt trả lại trước.
- Material Request loại Purchase (đề xuất mua của spec 003) → không bị ảnh hưởng.

**Kế toán**
- Xuất theo yêu cầu luôn là mục đích Production (đã có trong `create_draft`).
- Phiếu Thủ công không đổi cách tính chiều.
- Tháng tài chính đã khóa vẫn chặn ghi sổ như hiện nay.

**Hàng thừa trả về**: đi bằng Nhập kho lý do "Thu hồi từ lô" như hiện nay; không mở lại yêu cầu.

## Requirements *(mandatory)*

### Functional Requirements

**Lập và gửi**
- **FR-001**: Hệ thống PHẢI cho tổ trưởng, đội trưởng và quản lý vườn lập yêu cầu cấp vật tư trong Công việc (máy tính) và /work (điện thoại), với quyền tính ở máy chủ bằng `field_report.access(farm, crew)`; không tin danh sách tổ do trình duyệt gửi.
- **FR-002**: Một yêu cầu PHẢI có: vườn, đội, tổ (hoặc trống = cả đội), một việc, một kho cấp, ngày cần, người nhận (nhân viên), lý do; và 1–100 dòng, mỗi dòng một vật tư cho một lô, số lượng lớn hơn 0 theo đơn vị tồn kho.
- **FR-003**: Mỗi dòng PHẢI lưu lô ở chiều kế toán `lotus_farm_block`, vườn ở `lotus_farm`, việc ở `lotus_work_type`, mã lô ở `lotus_usage_area`, tên việc ở `lotus_purpose`, liều và ghi chú ở `lotus_notes`, kho ở `warehouse`. Các giá trị này do máy chủ điền từ lô và việc đã kiểm.
- **FR-004**: Máy chủ PHẢI từ chối: lô không hoạt động hoặc ngoài khu của đội; việc không thuộc vườn; tổ ngoài đội hoặc không phải tổ của tổ trưởng đó; vật tư tắt, không tồn kho, có lô/serial; kho không thuộc công ty hoặc là nhóm; trùng vật tư × lô; ngày cần ở quá khứ khi gửi.
- **FR-005**: Form PHẢI có cách nhập "mỗi lô" và "tổng, chia theo diện tích"; phép chia giữ đúng tổng và tôn trọng đơn vị nguyên.
- **FR-006**: Mọi lệnh ghi PHẢI có `client_event_id` và đi qua Lotus ERP Command: gửi lại cùng mã trả cùng kết quả, cùng mã khác nội dung bị từ chối. Số đang gõ PHẢI giữ trên máy đến khi máy chủ nhận.
- **FR-007**: Khi lưu, máy chủ PHẢI cảnh báo (không chặn): vật tư × lô đã có trong yêu cầu khác còn mở; kho không đủ hàng; lô đang cách ly.

**Duyệt**
- **FR-010**: Hệ thống PHẢI xác định người duyệt theo luật: yêu cầu của tổ trưởng → đội trưởng của đội hoặc quản lý vườn; của đội trưởng hoặc đội không có đội trưởng → quản lý vườn; của quản lý vườn → quản lý vườn khác. Người lập không bao giờ duyệt yêu cầu của mình.
- **FR-011**: Người duyệt PHẢI có thể: Duyệt; Giảm số rồi duyệt (chỉ giảm hoặc bỏ dòng, có lý do, lưu số trước/sau); Trả lại (có lý do). Người lập PHẢI có thể Rút lại khi đang chờ duyệt.
- **FR-012**: Duyệt PHẢI là submit Material Request, chỉ chạy trong hàm duyệt của Lotus; khi duyệt ghi người duyệt, giờ duyệt, một Lotus Signature Event `APPROVE` và một dòng bình luận.
- **FR-013**: Hệ thống PHẢI chặn mọi submit, hủy, dừng, mở lại Material Request loại Material Issue không đi qua Lotus (Desk, REST, script), và chặn sửa nội dung khi yêu cầu đang chờ duyệt hoặc đã duyệt.

**Kho cấp**
- **FR-020**: Kho PHẢI thấy danh sách "Cấp theo yêu cầu (N)" trong Kho › Xuất kho: yêu cầu đã duyệt, chưa đóng, còn số, xếp theo ngày cần.
- **FR-021**: "Lập phiếu xuất" PHẢI mở form xuất kho đang có ở chế độ "Theo yêu cầu đã duyệt", điền sẵn kho xuất, người nhận và phần còn lại; phiếu đi qua `create_draft` và `submit_document` đang có.
- **FR-022**: Khi kiểm phiếu xuất theo yêu cầu, máy chủ PHẢI chép `lotus_farm`, `lotus_farm_block`, `lotus_work_type` từ dòng yêu cầu vào dòng phiếu, đè giá trị trình duyệt gửi.
- **FR-023**: Danh sách nguồn của Kho PHẢI bỏ yêu cầu đã cấp đủ, và ghi nhãn "số · đội/tổ · lô · việc · cần dd/mm".
- **FR-024**: Cấp vượt phần còn lại PHẢI tiếp tục bị chặn (luật đang có).

**Theo dõi và kết thúc**
- **FR-030**: Hệ thống PHẢI hiện trạng thái: Nháp, Chờ duyệt, Trả lại, Chờ cấp, Kho đang lập phiếu, Đã cấp một phần, Đã cấp đủ, Đã đóng, Đã hủy; và nhãn "Quá hạn chưa cấp". Số đã cấp lấy từ ERPNext và phiếu xuất, không chép ra bảng riêng.
- **FR-031**: Đóng phần còn lại PHẢI có lý do, do người lập, người duyệt, quản lý vườn hoặc Quản lý kho làm, và bị chặn khi còn phiếu xuất nháp giữ số.
- **FR-032**: Mở lại PHẢI có lý do, do người duyệt hoặc quản lý vườn làm.
- **FR-033**: Hủy PHẢI có lý do, chỉ khi chưa có phiếu xuất nháp hay đã ghi sổ.
- **FR-034**: Xóa nháp: chỉ người lập, khi yêu cầu ở Nháp hoặc Trả lại.
- **FR-035**: Hệ thống PHẢI gửi thông báo trong ứng dụng và đẩy: gửi duyệt → người duyệt; duyệt, trả lại, giảm số, đóng, mở lại, hủy → người lập (và người duyệt khi liên quan); duyệt → người Kho đọc được kho đó; Kho ghi sổ hoặc hủy phiếu theo yêu cầu → người lập và người duyệt. Lỗi gửi thông báo không làm hỏng thao tác.
- **FR-036**: Duyệt yêu cầu cấp vật tư KHÔNG ĐƯỢC gửi thông báo "Có đề xuất mua mới".
- **FR-037**: Mỗi thao tác đổi trạng thái PHẢI ghi một dòng lịch sử (bình luận trên chứng từ) gồm người, giờ, lý do.

**Điền sẵn (US4)**
- **FR-040**: Dòng yêu cầu CÓ THỂ gắn phiếu giao việc (`lotus_work_assignment`); máy chủ kiểm phiếu đúng lô, việc, tổ và còn mở.
- **FR-041**: Form PHẢI gợi ý lô đang có phiếu giao việc này cho tổ, lô đến hạn theo vòng chăm sóc, và số của yêu cầu đã duyệt gần nhất cùng việc của đội, ghi rõ nguồn.

**Giao diện**
- **FR-050**: Nhập liệu và số tổng hợp dùng thẻ và hộp thoại, không trải bảng phẳng trên trang. Chữ tiếng Việt. Không thêm mục vào menu Công việc (giữ 7 mục) và không thêm tab thứ năm trên /work.
- **FR-051**: Người vườn chỉ thấy số lượng tồn "có thể cấp lúc này", không thấy giá trị tiền.

### Key Entities

- **Yêu cầu cấp vật tư** = Material Request (`material_request_type` = Material Issue). Đầu phiếu: công ty, ngày lập, ngày cần, kho cấp, người lập (`owner`), lý do (`lotus_request_note`), bộ phận để in (`lotus_department`), và các trường mới của spec này: đội, tổ, người nhận, người duyệt dự kiến, giờ gửi, người duyệt, giờ duyệt, lý do trả lại, lý do đóng.
- **Dòng yêu cầu** = Material Request Item: vật tư, số lượng (đơn vị tồn kho), kho, ngày cần, lô (`lotus_farm_block`), vườn, việc (`lotus_work_type`), mã lô (`lotus_usage_area`), tên việc (`lotus_purpose`), liều/ghi chú (`lotus_notes`), phiếu giao việc (`lotus_work_assignment`, tùy chọn), số đã cấp (`ordered_qty`, ERPNext tính).
- **Phiếu xuất theo yêu cầu** = Stock Entry Material Issue chế độ Request (đã có), dòng gắn `material_request` / `material_request_item`.
- **Sự kiện duyệt** = Lotus Signature Event `APPROVE` (đã có).
- **Lệnh ghi** = Lotus ERP Command (đã có), chống gửi trùng.
- **Phiếu giao việc** = Lotus Work Assignment (đã có).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tổ trưởng lập và gửi một yêu cầu 1 việc × 4 lô × 2 vật tư trên điện thoại trong dưới 2 phút.
- **SC-002**: 100% yêu cầu loại Material Issue được submit có một sự kiện APPROVE của người khác người lập (kiểm bằng truy vấn trên site thật sau 1 tháng).
- **SC-003**: Mọi dòng phiếu xuất theo yêu cầu đã ghi sổ có lô và việc; báo cáo chi phí "Theo công việc" có chi phí vật tư cho các phiếu đó.
- **SC-004**: Số liệu của phiếu Thủ công, giá thành tháng và báo cáo vườn tháng giữ nguyên khi chạy lại trên bản sao site thật trước và sau khi triển khai.
- **SC-005**: Mở danh sách yêu cầu của một đội dưới 2 giây; mở một yêu cầu dưới 1 giây.
- **SC-006**: Sau 1 tháng dùng, ít nhất một nửa số phiếu xuất cho sản xuất là "Theo yêu cầu đã duyệt" (để chủ vườn quyết có cấm xuất Thủ công cho lô hay không).

## Assumptions

- Nhánh 005 phải gộp `main` (a8a304a, spec 003 đã chạy thật bản 68dd563) trước khi viết mã; mọi chỗ dẫn mã trong plan theo bản `main` đó.
- Material Request Item đã có các chiều kế toán `lotus_farm`, `lotus_farm_block`, `lotus_work_type` (tạo bởi `finance.setup.install_dimensions`); sẽ kiểm lại trên bản sao trước khi làm.
- Các trường `lotus_request_note`, `lotus_department`, `lotus_purpose`, `lotus_notes` do spec 003 cài (`purchase_proposal.install_fields`) được dùng lại để bản in đọc; spec này chỉ ghi vào, không định nghĩa lại.
- Vai trò vườn không có và không được thêm quyền Material Request; mọi đọc ghi của họ đi qua module mới với kiểm phạm vi riêng.
- 3 tài khoản tổ trưởng hiện có; các tổ khác do đội trưởng nhập hộ cho đến khi có tài khoản.
- Không có dữ liệu cần chuyển: site thật có 0 yêu cầu loại Material Issue.
- Test, build và diễn tập chạy trên khu test VPS hoặc GitHub Actions, không chạy trên máy này.
