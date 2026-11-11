# Công việc ngoài vườn: báo cáo ngày theo lô (Vườn 222)

Làm lại ngày 10/11/2026 theo spec 002. Đơn vị nhỏ nhất là lô. Mỗi tổ có một báo cáo mỗi ngày, gồm các dòng của từng lô.
Số chỉ được tính (dự thu, bảng màu dây, vòng chăm sóc, tiền khoán) sau khi đội trưởng xác nhận.

Menu **Việc hằng ngày** trên máy tính có 7 mục: Hôm nay, Giao việc, Màu dây & thu hoạch, Xưởng, Dự thu, Báo cáo và Thiết lập.
Trên điện thoại (`/work`) có 4 tab: Hôm nay, Giao việc, Xác nhận, Tôi.

## Tổ trưởng: nhập và gửi báo cáo ngày

1. Mở **Hôm nay**, kiểm tra đúng ngày và đúng tổ.
2. Mỗi lô được giao cho tổ là một thẻ. Bấm vào thẻ lô để mở hộp nhập của lô đó. Lô làm thêm ngoài lô được giao thì chọn ở **Nhập cho lô khác**.
3. Trong hộp của lô, bấm nút việc đã làm, ví dụ **+ Cắt bắp**, **+ Bao buồng**, **+ Thu hoạch**, rồi nhập số:
   - **Cắt bắp**: số buồng. Màu dây tự lấy theo ngày.
   - **Bao buồng**, **Thu hoạch**, **Hủy sau cắt bắp**: chọn màu dây. Hộp hiện số buồng còn lại của màu đó. Nhập quá số còn lại thì không lưu được.
   - **Thu hoạch**: bắt buộc nhập kg. Lô đang cách ly thuốc thì không thu được.
   - **Việc vườn** (cắt lá, làm cỏ…): khối lượng, và tick **Đã làm xong cả lô** vào ngày làm xong. Chỉ ngày báo xong mới tính là xong vòng chăm sóc.
   - **Phun thuốc, bón phân**: bắt buộc ghi vật tư và liều.
   - **Kiểm tra sâu bệnh**: bệnh, số cây bị, mức độ.
4. Người làm mặc định là người của tổ có lượt máy chấm công buổi đó. Bỏ tick người không làm việc này.
5. Bấm **Lưu lô này**. Số đang gõ được giữ trên máy nếu mất sóng.
6. Làm xong các lô thì bấm **Gửi báo cáo**. Đã gửi thì chỉ đội trưởng mở lại mới sửa được.

### Phiếu giấy

Tổ không dùng điện thoại thì in phiếu:

1. Ở **Hôm nay**, phần **Phiếu giấy**, bấm **In phiếu giấy**. Phiếu có mã báo cáo ở góc phải, mỗi lô của tổ một hàng, mỗi cột một việc có mã C1, C2…, và màu dây cắt bắp của ngày.
2. Tổ ghi số vào ô. Việc vườn làm xong cả lô thì đánh dấu vào ô "xong".
3. Cuối ngày bấm **Đọc ảnh phiếu** (hoặc **Chụp ảnh phiếu** trên điện thoại), chụp rõ cả tờ phiếu.
4. Máy điền sẵn các dòng nháp, gắn nhãn "Máy đọc, chưa kiểm". Ảnh hiện cạnh danh sách lô cần kiểm.
5. Bấm **Kiểm lô này**, so số với ảnh, sửa nếu sai (màu dây, lý do hủy…), rồi bấm **Đã kiểm, lưu lô này**.
6. Còn lô máy đọc chưa kiểm thì chưa gửi được. Lô đã nhập tay trước khi đọc ảnh được giữ nguyên.

## Đội trưởng

**Xác nhận**: tab **Xác nhận** trên điện thoại hoặc dải tình hình các tổ trên **Hôm nay** cho biết tổ nào chưa gửi, chờ xác nhận, đã xác nhận. Mở tổ, xem số, bấm **Xác nhận**.

- Không xác nhận được báo cáo do chính mình nhập hộ; cần quản lý vườn xác nhận.
- Sửa số đã xác nhận: bấm **Sửa có lý do**, nhập số đúng và lý do. Nhập 0 nếu dòng đó nhập nhầm. Dòng cũ được giữ trong lịch sử.
- **Mở lại** báo cáo đã gửi hoặc đã xác nhận phải ghi lý do; dòng đã xác nhận vẫn giữ, tổ chỉ thêm hoặc sửa dòng chưa xác nhận.

**Giao việc** (giao theo vòng chăm sóc):

- Mỗi việc có một thẻ: bao nhiêu lô quá hạn, đến hạn trong kỳ, đã giao, chưa giao. Chọn kỳ: tuần này, hai tuần hoặc bốn tuần tới.
- Bấm thẻ việc, tick các lô (hoặc **Chọn cả khu**), chọn tổ, hạn xong, bấm **Giao cho tổ**. Mỗi lô thành một phiếu; lô đã có phiếu đang mở cho việc đó thì không giao lại.
- **Bảng lô × việc** cho cái nhìn toàn đội.
- **Phiếu đã giao**: xem, đổi tổ hoặc hủy (phải ghi lý do). Phiếu riêng (không theo vòng) dùng cho việc khoán cả lô cần nghiệm thu.
- Tổ báo xong cả lô và đội trưởng xác nhận ngày đó thì phiếu tự đóng, lô sang vòng sau. Việc khoán cả lô thì chờ nghiệm thu.

## Kỹ thuật vườn: nghiệm thu khoán cả lô

Ở **Giao việc**, phần **Chờ nghiệm thu khoán lô**. Đội trưởng không nghiệm thu đội mình. Mức đạt: việc buồng 95%, việc vườn và BVTV 90%. Đạt thì phiếu khóa và tính tiền cả lô; không đạt thì tổ làm lại.

## Quản lý vườn

**Thiết lập**:

- **Đội, tổ & lô**: đội theo khu, tổ trong đội, tổ trưởng và đội trưởng.
- **Việc & cách trả**: nhóm việc, cách trả (khoán số lượng, khoán cả lô, công nhật), có bắt buộc ghi vật tư không.
- **Bảng giá khoán**: đơn giá theo ngày hiệu lực. Việc khoán số lượng chưa có giá thì không xác nhận được.
- **Vòng chăm sóc**: mỗi việc vườn làm lại sau bao nhiêu ngày, cho cả vườn hoặc một khu, từ ngày nào. Mỗi thay đổi là một phiên bản mới, chờ duyệt rồi mới áp dụng. Lô đến hạn = ngày báo xong cả lô gần nhất + số ngày của vòng; lô chưa làm lần nào đến hạn từ ngày áp dụng.
- **Màu dây cắt bắp**, **Tham số dự thu**.

## Tiền khoán

- Khoán số lượng: số đã xác nhận × đơn giá của ngày, chia cho người làm theo buổi.
- Khoán cả lô: trả khi nghiệm thu đạt.
- Công nhật: theo máy chấm công; buổi làm khoán không tính công nhật.
- **Báo cáo › Tháng** có tiền khoán theo lô; **Tiền khoán theo người** mở từ đó. Số này vào bảng lương.

## Yêu cầu cấp vật tư

- **Giao việc › Yêu cầu cấp vật tư** (điện thoại: tab Giao việc của `/work`). Đội trưởng lập cho đội mình, quản lý vườn lập cho mọi đội; tổ trưởng không lập (chủ vườn quyết định 11/11/2026).
- Mỗi dòng là vật tư × lô (chọn cả khu thì chia theo diện tích, đơn vị nguyên làm tròn giữ tổng), kèm việc, ngày cần và kho xuất. Mở từ phiếu giao thì điền sẵn lô và việc.
- Đội trưởng duyệt yêu cầu của đội mình, kể cả yêu cầu tự lập ("Lưu và duyệt" một lần); quản lý vườn duyệt mọi yêu cầu. Người duyệt chỉ giảm hoặc bỏ dòng, có lý do; muốn tăng thì trả lại kèm lý do.
- Duyệt xong yêu cầu vào hàng chờ của Kho (**Kho › Phiếu xuất › Cấp theo yêu cầu**). Người lập nhận thông báo khi Kho lập phiếu, cấp, hoặc hủy phiếu cấp; xem phần còn lại theo lô trong chi tiết. Đóng phần chưa cấp, mở lại, hủy đều ghi lý do.
- Duyệt chỉ làm được trong Lotus: nộp, hủy, dừng Material Request loại Material Issue từ Desk hay REST bị chặn.

## Cho người bảo trì

- Sổ lô: `Lotus Work Entry` (trạng thái Nháp → Đã gửi → Đã xác nhận / Đã hủy, `source_key` duy nhất), `Lotus Daily Report` (tổ-ngày), `Lotus Work Session` (buổi có trọng số).
- API: `lotus_farm/lot_report.py` (today, open_report, save_lot, send, confirm, amend, reopen, status, my_pay), `lot_paper_form.py` (phiếu giấy, đọc ảnh), `care_cycle.py` (vòng chăm sóc), `field_report.py` (phiếu giao, nghiệm thu, tiền khoán).
- Quy tắc thuần có test: `lot_ledger_rules.py`, `care_cycle_rules.py`, `lot_paper_form_rules.py`, `field_report_rules.py`.
- Màn: `frontend/src/components/field/` (LotToday, LotCards, LotEntryModal, PaperPhotoReview, CareDueList, CareCycleSettings, WorkAssign, WorkTicket, WorkInspect).
- Kiểm thử tích hợp: `tests/integration/verify_lot_ledger.py`, `verify_bunch_forecast.py`, `verify_care_cycle.py`, `verify_paper_form.py`.
- Yêu cầu cấp vật tư: API `lotus_farm/issue_request.py` (ghi qua `client_event_id` chống bấm hai lần), quy tắc thuần `issue_request_rules.py`, màn `MaterialRequests`, `MaterialRequestForm`, `MaterialRequestDetail`, kiểm thử `tests/integration/verify_issue_request.py`.
