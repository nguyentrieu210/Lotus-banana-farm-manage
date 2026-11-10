# Màu dây, thu hoạch, xưởng và dự thu

Hướng dẫn cho đội trưởng, quản lý vườn, xưởng và kế toán (spec 002, 10/11/2026). Mọi số ở đây đọc từ sổ lô đã xác nhận; cách nhập số mỗi ngày xem `FIELD_REPORT.md`.

## Màu dây & thu hoạch

Mỗi màu dây của một tuần cắt bắp (lần 1 hoặc lần 2) là một thẻ: số đã cắt, đã bao, hủy sau cắt, đã thu, còn trên cây, tuổi (tuần) và khoảng ngày thu dự kiến theo bộ tham số đang áp dụng.

- **Cần thu tuần này**: lô và màu đến tuổi hoặc quá tuổi thu, cũ nhất trước. Chọn **Tuần sau** hoặc **Hai tuần nữa** để chuẩn bị người cắt và xưởng.
- Lô đang cách ly thuốc được ghi rõ ngày hết cách ly; trong thời gian đó dòng thu hoạch bị chặn.
- Bấm thẻ màu để xem từng lô; bảng xuất Excel được.
- **Xuất sổ cắt bắp (Excel)**: số cắt bắp đã xác nhận theo đúng mẫu sổ của vườn, mười tuần một trang.
- Trên điện thoại, đội trưởng xem phần **Màu dây & cần thu** ở tab **Xác nhận**.

## Xưởng

Màn **Xưởng** (quyền ca đóng gói: tổ trưởng xưởng hoặc quản lý vườn).

1. Bấm **Thêm ca**: mã ca, ngày, giờ bắt đầu và kết thúc.
2. Tick các dòng thu hoạch đã xác nhận làm nguồn buồng. Mặc định lấy hết số buồng còn lại của dòng và kg tương ứng; sửa nếu ca chỉ nhận một phần.
3. Nhập kết quả: kg thành phẩm, kg phụ phẩm, số thùng. Hao hụt và tỷ lệ đóng gói tự tính.
4. **Lưu ca** để sửa tiếp sau, hoặc **Lưu và đóng ca**. Đóng ca thì không sửa được.

Một màu của một lô không nhận quá số buồng đã thu mà chưa vào ca khác. Ca đã đóng hiện bảng chia theo lô: kg vào, thành phẩm, thùng, kg/buồng, thùng/buồng, tỷ lệ đóng gói. **Truy vết về lô** cho biết buồng của ca đến từ dòng thu nào, và lô đó đã phun gì trong 90 ngày trước khi thu (thuốc, liều, thời gian cách ly).

**Kế toán: nhập kho thành phẩm theo ca**

- Trước tiên chọn **Chuối thành phẩm**, **Chuối phụ phẩm** và **Kho thành phẩm** ở Tài chính – Kế toán › Thiết lập. Kho thành phẩm ghi vào TK 155.
- Mở ca đã đóng, bấm **Lập phiếu nhập kho thành phẩm**. Hệ thống tạo phiếu nhập kho **nháp**: mỗi lô nguồn có dòng thành phẩm và phụ phẩm theo kg, giá trị = kg buồng của lô vào ca × giá thành tạm tính của lô (giá thực tế tháng gần nhất, nếu chưa có thì giá kế hoạch đặt ở Thiết lập). Nợ 155 / Có 154 theo lô.
- Kế toán kiểm phiếu ở Kho rồi duyệt. Mỗi ca một phiếu.

## Dự thu

Trang **Dự thu**, tab **13 tuần** và **12 tháng**. Mỗi buồng chỉ tính một lần, ở mốc gần thu hoạch nhất:

| Nguồn | Mức tin cậy | Ý nghĩa |
|---|---|---|
| Đã cắt bắp | Cao | Số thật theo lô và màu dây |
| Đã chích bắp | Khá | Đã chích, chưa cắt |
| Theo chọn chồi | Thấp | Số chồi ước tính từ diện tích, thời gian theo ngày chọn thật |
| Theo số cây | Thấp | Số cây và ngày trổ ước tính theo khu |

**Bản chốt mỗi tuần**: mỗi thứ Hai có một bản chốt dự thu, tính như sổ lô lúc 0 giờ sáng thứ Hai (chỉ dòng đã xác nhận trước đó, bộ tham số đã duyệt trước đó). Máy chủ không có lịch chạy riêng: người đầu tiên mở ứng dụng trong tuần sẽ kích hoạt việc dựng, kể cả bù các tuần bị lỡ (tối đa 8 tuần). Bản dựng lại lấy số cây và ngày trổ hiện tại; điều này được ghi trong bản chốt.

Tab **So với thực tế** so mỗi tuần với bản chốt của chính tuần đó, kèm kg/buồng và thùng/buồng thật của xưởng. Mục tiêu sai số 10% cho 4 tuần tới, 15% cho 12 tuần tới ở cấp toàn vườn. Quản lý vườn bấm **Chốt bản dự thu hôm nay** khi cần một bản giữa tuần. Tham số đề xuất từ số thu thật không tự áp dụng; quản lý vườn duyệt ở tab **Bộ thông số**.

## Báo cáo

Màn **Báo cáo**, ba tab. Mỗi thẻ là một câu hỏi với một con số; bấm thẻ để xem bảng chi tiết, lọc và xuất Excel.

- **Sáng nay**: tổ chưa gửi báo cáo hôm qua, báo cáo chờ xác nhận, số bất thường, việc quá hạn vòng chăm sóc, lô đang cách ly, màu dây đến tuổi thu.
- **Tuần**: việc đã làm theo lô, buồng còn trên cây, thu hoạch, xưởng, dự thu so với thực tế, lô cần chú ý, và bản đồ lô tô màu theo tình trạng (cách ly, quá hạn, có thu hoạch).
- **Tháng**: sản lượng thu, cắt bắp/cây, kg/buồng, thùng/buồng theo lô; công và tiền khoán theo lô; vật tư xuất kho so với vật tư báo dùng theo lô.

## Cho người bảo trì

- `lotus_farm/ribbon_board.py` (bảng màu dây, cần thu, sổ cắt bắp) trên `bunch_report_rules.py`.
- `lotus_farm/shift.py` (ca theo nguồn buồng, truy vết) trên `packout_rules.py`; `finance/costing.receive_shift` (phiếu nhập kho nháp).
- `lotus_farm/forecast_snapshot.py` (`ensure_weeks`, `ensure_all`, `queue_missing_weeks`) trên `forecast_snapshot_rules.py`; dự thu `block_forecast.bunch_summary(farm, as_of)`.
- `lotus_farm/field_reports.py` (morning, week, month); màn `frontend/src/components/report/FieldReports.vue`, `ReportCards.vue`.
- Kiểm thử tích hợp: `verify_bunch_forecast.py`, `verify_packout_sources.py`, `verify_field_reports.py`.
