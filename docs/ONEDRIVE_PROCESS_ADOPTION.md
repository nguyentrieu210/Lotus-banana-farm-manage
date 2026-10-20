# Quy trình OneDrive vào Lotus ERPNext

Nguồn chính: thư mục **AnhDung**, master `#100.1_11062025_File master data chuối - MĐ2600.xlsx`.
Thông số và engine QTHT tháng 7/2025 là phiên bản tham chiếu bổ sung, có SHA-256 riêng;
không gộp thành cùng bản master tháng 6. Thư viện và nguồn nằm tại
`lotus_farm/data/onedrive_protocol_v1.json`; 45.788 dòng tham số chi tiết được giữ trong
`onedrive_reference_v1.json.gz`. Đây là dữ liệu tham chiếu, không nhập thành thực tế của Lotus.

## Mốc bàn giao và chọn chồi

- Nhật ký chặt cây cũ thuộc **LOTUS-222**, người dùng xác nhận 20/10/2026.
- 301 đợt theo ngày/khu, 430.871 cây: A 95.315, B 88.824, C 98.701, D 80.253, E 67.778.
- Ngày từ 31/03 đến 03/10/2026 là **chặt cây cũ lần đầu**; người dùng quy ước ngày này
  tương đương ngày chọn chồi để chuyển đổi. Không suy ngược thành ngày trồng thực tế.
- `Báo cáo Chọn chồi.xlsx`, `Tổng hợp!K6:U6`: dọn toàn bộ chồi tại `EDATE(K6,4)`;
  các lần chọn tại `EDATE(K6,6)`, `EDATE(K6,12)`, … `EDATE(K6,42)`.
- Mỗi kỳ tính từ **ngày mốc gốc**, giữ ngày cuối tháng; không cộng 90/180 ngày và không
  nối ngày đã làm tròn tháng trước. Chọn đầu tiên ở tháng 6 nuôi vụ chồi 2.
- Thực tế chọn chồi nằm tại `NL_Chọn chồi!B` (vụ), `C` (ngày làm), `Y` (số cây chọn).
- Đợt bàn giao chỉ ở cấp **khu/ngày**. Chọn chồi vụ tiếp theo phải ghi đúng lô/thửa/vụ,
  ngày làm và số chồi đã kiểm đếm. Liên kết bàn giao chỉ để truy nguyên; không phân bổ
  ngầm 430.871 cây cũ xuống các lô và không ghi thành số chồi thực tế.

Nhập lại cùng ngày/khu/nhóm nguồn không tạo trùng; file đổi số lượng được chặn đối soát.
File nguồn private, SHA-256, sheet và ô nguồn được lưu cùng từng đợt.

## Màu dây và truy xuất

`Chăm sóc buồng và thu hoạch.xlsx / DmMauDay` có 183 kỳ. 13 kỳ đầu 7 ngày, 170 kỳ sau
5 ngày; giữ cả khoảng trống lịch sử. Có **17 mã M01–M17**; tên vật lý ghép màu từng thời
điểm có cách viết khác nhau, không coi tên khác cách viết là mã màu thứ 18.

Đối soát đủ 183 dòng `E:H,N:O`:

- E/F: ngày đầu/cuối **cắt bắp**.
- G/H: E/F trừ 14 ngày, **chích bắp**.
- N: E cộng 55 ngày, bắt đầu cửa sổ dự thu.
- O: F cộng 70 ngày, kết thúc cửa sổ dự thu.

Lịch nguồn kết thúc 01/01/2026. Kỳ sau đó là **lịch kéo dài có phiên bản**, dùng nhịp
5 ngày và thứ tự 17 mã cuối nguồn. Phát hành lịch không tạo một buồng đã cắt bắp.
Mã tag gồm vườn + phiên bản + kỳ, tránh đụng mã giữa vườn/năm/vòng màu.

Chích bắp và cắt bắp kiểm theo ngày công đoạn đúng kỳ. Phun, bao, chăm sóc, đo trái và
thu hoạch giữ tag của **chứng từ cắt bắp gốc đã xác nhận**, cùng vườn/lô/thửa/vụ/chồi;
không kiểm ngày chăm sóc bằng ngày hiệu lực cắt bắp. Thu cộng dồn không vượt số buồng
gốc; đợt cắt bắp đã được dùng không sửa/cancel mất truy xuất. Tag cũ giữ cơ chế cũ.

## Hệ số và lịch dự thu

- 57 bộ `tsSXKD`: 19 vườn nguồn × năm 1, 2, 3+.
- 9 bộ `tsSXKD6`: Tốt/Trung bình/Xấu × năm vụ; CB/cây lần lượt 90/75/65%.
- 33.846 dòng riêng theo thửa `tsKHTH_R`; 4.536 dòng chung `tsKHTH_C`.
- 2.610 dòng phân phẩm cấp theo tháng `tsPC_C`; `tsPC_R` rỗng ở bản nguồn.
- `tsRaHoa`: 109 dòng; 8 đơn vị × 18 vụ; mỗi đường cong cộng đủ 100%.
- Vụ mẹ: thu ở tuổi tháng 8–11, chia 20/40/30/10%.
- Vụ chồi đầu: tuổi trồng tháng 15–18; tính từ mốc chọn chồi tháng 6 là **+9…12 tháng**,
  chia 17/25/40/18%. Các đợt chọn sau cách nhau 6 tháng.
- PowerQuery đưa mốc ngày 1/2 về tháng kế hoạch trước bằng
  `Date.AddMonths(anchor, age - (day<=2 ? 1 : 0))`. Đây là kỳ kế hoạch, không phải ngày
  khẳng định sẽ thu đúng ngày đó.
- Kg nguyên buồng = số cây × tỷ lệ CB/cây × TH/CB × kg nguyên buồng.
- Kg sơ chế = số cây × CB/cây × TH/CB × SC/TH × kg sơ chế/buồng.
  Không nhân thêm lần nữa tỷ lệ đóng gói đã nằm trong kg sơ chế nguồn.

Mỗi vườn chọn bộ tham số có tên nguồn và hiệu lực rõ ràng. Bản duyệt bất biến; bản mới
chỉ thay thế tương lai, không lấn đợt cắt bắp đã ghi. Lịch màu đã phát hành giữ phiên bản
gốc; đợt cắt bắp mới phải dùng phiên bản đang có hiệu lực. Số liệu từ cây cũ là một
**mô phỏng riêng có giả định 1 cây cũ : 1 chồi**, bật bằng thao tác người dùng;
không cộng vào dự thu từ chồi đã kiểm đếm, không phát hành bán, không tạo tồn kho.
Hệ số tham chiếu phải được hiệu chuẩn từ số liệu Lotus qua các vụ, không gọi là năng
suất đã đo tại Lotus.

Khi có cắt bắp thực tế, phần buồng đó thay thế dự báo từ số chồi, trừ số đã thu/hủy;
không cộng hai lần. Đợt có màu dùng đúng cửa sổ E+55/F+70. Khi chưa có đo trái, lượng
trong cửa sổ được phân bổ đều theo ngày để tổng hợp tháng; đây là giả định phân bổ,
không phải đường cong theo ngày đã đo trong OneDrive. Các đợt Plan Cohort xem riêng,
không tự gộp với đợt chọn chồi thực tế chưa có ánh xạ chắc chắn.

Vườn đã áp dụng quy trình phải ghi mã màu theo phiên bản khi chích/cắt bắp và chọn
đợt cắt bắp gốc khi chăm sóc, đo trái, thu hoạch. Ô chọn đợt gốc chỉ đưa chứng từ cắt
bắp đã xác nhận, tự điền cùng vườn/lô/thửa/vụ/chồi và màu dây.

## Luồng ERP sử dụng

| Dữ liệu/công đoạn OneDrive | Lotus ERPNext |
| --- | --- |
| Nhật ký bàn giao khu/ngày | Lotus Handover Cohort |
| Datalo, trồng mới, trồng dặm | Farm / Farm Block / Farm Plot / Crop Cycle / Planting Event |
| Chọn chồi thực tế | Sucker Selection Batch |
| KH Chọn chồi, công việc và vật tư | Plan Cohort / Work Schedule Rule / Daily Work Plan / Material Norm Profile |
| Cắt chồi, bón phân, cắt lá, làm/phát cỏ, BVTV | Work Type / Daily Work Result / Labor Allocation / Material Consumption |
| Fusarium và hủy buồng | Disease Observation / Bunch Cancellation / Defect Reason |
| Chích bắp, cắt bắp, phun/bao/chống đổ | Bunch Operation / Bunch Tag / source_cut_operation |
| Đo trái theo luống, mẫu đo | Fruit Measurement / bảng mẫu con / ribbon_color |
| KHSL tuần/tháng | Dự thu OneDrive / Harvest Forecast có duyệt và kiểm soát phát hành |
| Thu hoạch, cân và nhận buồng | Harvest Actual / Scale Reading / Harvest Lot |
| QC đầu vào, lỗi sơ chế, phẩm cấp | Incoming Quality Inspection / Defect Reason / Product Grade |
| Xưởng đóng gói, vật tư, phụ phẩm | Packhouse Shift / Packout Run / Material Recovery / Secondary Product Movement |
| Nhập thành phẩm, mua/cấp vật tư, bán | Stock Entry / Material Request / Purchase Order / Sales Order / Reservation |
| Báo cáo kết quả ngày và kết vụ | Daily Production Close / Cycle Closing Report |
| Nhân công và trả công | Work Team / Daily Labor Summary / HRMS Attendance / Payroll |

Các luồng kho, tài chính và nhân sự tiếp tục sử dụng chứng từ ERPNext/HRMS hiện có.
Không tạo dữ liệu thực tế của các vườn nguồn BP/ER thành thực tế Lotus; không lấy chi
phí hay liều lượng vật tư thực dùng của một ngày làm định mức chuẩn khi chưa có mẫu số
và phiên bản được duyệt. Biểu mẫu nguồn bổ sung đã kiểm tra gồm chăm sóc vườn, đo trái
theo luống, phiếu xưởng đóng gói và báo cáo kết vụ. Danh sách cột nguồn được lưu trong
`onedrive_form_headers.json` để mở rộng ánh xạ mà giữ đúng đơn vị và ý nghĩa.

Quy tắc việc định kỳ hỗ trợ cả ngày và **tháng lịch**; gợi ý giao việc và tính nhân công,
vật tư dùng cùng mốc gốc. Định mức chưa có dữ liệu hiển thị thiếu, không thay bằng số 0
hoặc tự đoán năng suất/đơn giá/liều lượng.
