# Lotus ProMax — thực hiện BRD ngày 07/10/2026

Nguồn yêu cầu: **Lotus Farm BRD 360° ProMax — Điều hành nông trường, dự thu, thu hoạch và đóng gói**, bản 06/10/2026 18:49 UTC. Bản này thay đổi phạm vi so với BRD đầu tiên, đặc biệt ở nhân công, vật tư, hủy buồng và đối chiếu ngày.

## Cấu trúc đất

**Company → Farm → Farm Block → Farm Plot → Crop Cycle → Sucker Selection Batch.**

Không có DocType Xí nghiệp. Work Team là đội thực hiện, không phải cấp quản lý đất. Legacy Organization Map giữ tên đơn vị cũ và chỉ được dùng sau khi duyệt. Không tự suy BP1/BP2/ER1 là Farm.

Mỗi vụ mới phải chọn Thửa. Hai thửa trong cùng lô có thể cùng chạy vụ số 1. Tổng diện tích thửa đang hoạt động không vượt diện tích lô. Vụ cũ chưa có Thửa được giữ nguyên; dùng **Legacy Cycle Plot Mapping** với lý do để bổ sung liên kết đất, theo thứ tự vụ mẹ trước rồi vụ chồi. Phải đóng/đối soát dự thu đã phát hành trước khi gắn. Không ghi đè chứng từ thực tế hoặc dự thu lịch sử.

## Từ kế hoạch tới chốt ngày

1. Tạo Work Category/Work Type, đơn vị tính và năng suất một công. Hệ thống không điền hệ số nông học giả định.
2. Tạo Norm Basis và Material Norm Profile theo Farm/công việc, phiên bản và ngày hiệu lực (khi duyệt cần cả ngày bắt đầu và kết thúc để có thể áp dụng phiên bản kế tiếp). Duyệt xong không sửa/xóa; không cho hai bộ định mức đã duyệt trùng thời gian cùng Farm/công việc.
3. Tạo Daily Work Plan: chọn Thửa/Vụ/Đợt chồi, việc và khối lượng. Số công cần = khối lượng / năng suất. Đơn vị công việc lấy từ Work Type.
4. Bấm **Tính nhu cầu vật tư**. Nhu cầu = khối lượng × định mức / lượng cơ sở × tần suất × hệ số đổi. Tạo lại sẽ trả phiếu đã có.
5. Nhu cầu vật tư có nút kiểm tra kho: số hiện có và số đã giữ lấy từ ERPNext Bin; khả dụng vật lý = max(actual_qty − reserved_stock, 0). Đây không phải số tồn dự kiến, không trừ các kế hoạch tương lai thêm lần nữa. Người dùng cần quyền đọc Stock Ledger và kho. Thiếu hàng thì tạo Material Request bản nháp; gọi lại trả đúng phiếu đã tạo.
6. Từ kế hoạch bấm **Bố trí nhân công** và **Ghi kết quả**. Mỗi dòng có một kết quả đã nộp. Chưa làm đủ phải ghi lý do. Nhân viên có mã ERP được bố trí tối đa một công mỗi ngày; phân công theo đội phải có ghi chú.
7. Material Consumption gắn với kết quả việc, nhu cầu và một dòng Material Issue đã nộp của ERPNext. Dòng xuất kho phải khớp Item/UOM/kho/ngày; không được dùng lại cho hai phiếu tiêu hao. Phần chưa dùng phải được thu hồi bằng một dòng Material Receipt đúng lượng, trước khi chốt ngày.
8. Hủy buồng phải chọn Cancellation Reason thuộc nhóm đang hoạt động. Alias cũ ở bảng riêng. Ngày dự kiến thu xác định phần dự thu bị ảnh hưởng; nếu gắn nguồn Bunch Operation thì không được hủy vượt số buồng nguồn.
9. Sau Harvest Lot phải nộp Incoming Quality Inspection. Packout không dùng quá lượng QC đã nhận đạt. Đầu ra được phân loại Finished/Secondary; toàn bộ reject/process loss phải có chi tiết nguyên nhân. Kho ERP vẫn là nguồn tồn duy nhất.
10. Daily Production Close kiểm tra kế hoạch/kết quả, lý do việc dở dang, công bố trí/thực tế, vật tư/nộp/thu hồi, các phiếu sản xuất, QC, cân đối đóng gói và chứng từ thành phẩm. Còn lỗi thì không nộp được. Muốn sửa sau chốt phải ghi lý do rồi hủy phiếu chốt ngày; chứng từ thực tế vẫn theo cancel/amend.

Daily Labor Summary giữ số hiện hữu/đi làm/vắng/định biên/thừa thiếu/công trên ha theo Farm/ngày/nhóm việc/vườn hoặc xưởng. Đây là báo cáo phân bổ thực địa; không tạo một bảng Attendance riêng thay Frappe HR.

## Dự thu và hủy buồng

Giữ nguyên dự thu đã phát hành và hash của lần phát hành. Dự thu nháp ghi cả số nguồn gốc, số hủy đã đưa vào tính, số nguồn còn lại và các chứng từ hủy trong source_snapshot; lưu lại không trừ hủy hai lần. Chỉ lấy hủy đúng Vụ/Đợt chồi/khoảng ngày dự kiến thu.

Hủy phát sinh sau phát hành giảm lượng khả dụng hiện tại và khả năng giữ hàng mới, theo tỷ lệ mất buồng trên số nguồn còn lại đã duyệt. Cam kết đã giữ không bị xóa: nếu thiếu, ATP âm/cảnh báo thiếu. Hủy phiếu hủy sẽ khôi phục khả dụng tới mức đã duyệt, không vượt dự thu gốc. Muốn phát hành số mới phải tạo revision theo quy tắc hiện có. Công thức chính thức và hệ số phải được phía vận hành duyệt trước pilot.

## Kết vụ, phụ phẩm và báo cáo

**Daily Operations** là Script Report chọn Farm/ngày, xem từng công việc theo Thửa, kế hoạch/thực tế, công cần/đã bố trí/đã dùng, lý do chưa xong và bấm vào phiếu nguồn. Không cộng khối lượng khác UOM vào một tổng sai nghĩa.

Cycle Closing Report lấy số cây trồng, buồng hủy, buồng thu, kg thu, kg thành phẩm/phụ phẩm/hao hụt và công thực tế từ các phiếu đã nộp. Các ca đóng gói trộn nhiều nguồn được chia theo tỷ lệ khối lượng đóng góp, giữ nguồn trong snapshot. Tấn/ha tính trên diện tích Thửa đã ghi vào lần kết vụ. Chỉ kết vụ sau khi đóng/đối soát dự thu và chốt các ngày vận hành. Muốn mở lại phải hủy báo cáo với lý do. Không sửa trạng thái Closed trực tiếp trên Crop Cycle.

Secondary Product Movement tham chiếu dòng xuất/chuyển kho ERP, Item và Batch phụ phẩm của ca đóng gói; không có ledger phụ phẩm thứ hai.

## Nguồn Excel và chuẩn hóa

Source File Registry: ID nguồn, path, file, SHA-256, kỳ nghiệp vụ, mốc phiên bản, ưu tiên, trạng thái và tầng A/B/C/D. Khi đã dùng trong import thì không sửa danh tính/hash; đăng ký phiên bản file khác.

Source Import Batch/Row: sheet, số dòng, hash, JSON gốc, mã tổ chức cũ, kết quả Imported/Rejected/Pending và đích thực tế. Imported yêu cầu mapping đã duyệt, đích cùng Farm; không nhận một dòng đã được nhập ở batch nộp trước. Rejected bắt buộc lý do + người phụ trách. Batch chỉ được nộp nếu ≥99.5% dòng đã giải quyết. Chưa có importer tự đọc toàn bộ OneDrive hoặc tự đoán cột/đơn vị; không coi registry là dữ liệu đã nhập.

`source_data.py` chuẩn hóa Unicode, số với locale khai báo rõ, phần trăm và ngày Excel/dd/mm/yyyy. Blank giữ None, không đổi thành zero; ngày filename không thay ngày sheet. UOM vật tư và mẫu số định mức tách riêng.

## Tên BRD và tên được giữ trong repo

| BRD | Code dùng hiện tại |
|---|---|
| Production Cohort / Cohort Selection Event | Sucker Selection Batch |
| Bunch Stage Observation | Bunch Operation |
| Labor Requirement | required_workdays và productivity snapshot trên Daily Work Plan Line |
| Forecast Snapshot / Line | Harvest Forecast + Forecast Output Plan, một nguồn sinh học và nhiều Item |
| Supply Allocation | Forecast Allocation |
| Packhouse Shift / Input Lot / Packout Detail | Packout Run / Packout Run Source / Packout Output |
| Incoming QC | Incoming Quality Inspection |
| Integration Log | Integration Event cho kết quả lệnh hiện có; chưa là hàng đợi tích hợp OneDrive |

Giữ tên cũ để không tạo hai bộ phiếu cùng làm một việc và không phá dữ liệu đã có.

## Kiểm tra và giới hạn nghiệm thu

- Pure suite kiểm tra công thức, schema, quyền lệnh và chuẩn hóa nguồn.
- Disposable ERPNext v16 suite cài/migrate hai lần và kiểm tra luồng kho thật, khóa giá trị đã duyệt, hai kết nối giữ hàng đồng thời (thử lại giao dịch khi database báo tranh chấp, dùng cùng event ID), QC, Thửa/Vụ, 5.000 tấm xốp/thu hồi/chốt ngày và hủy làm giảm ATP.
- Chỉ dùng kết quả workflow của **commit mới nhất** để kết luận chạy được. Không lấy lần pass cũ để chứng minh code mới.
- Chưa có dữ liệu Lotus thật, bảng mapping đã duyệt, kiểm kê toàn bộ OneDrive, kiểm thử tải/SLA, đối chiếu số liệu hoặc UAT/cutover. Chưa nghiệm thu 360°.
- Offline/PWA, GIS/GPS/QR, liên kết thiết bị cân với tài khoản, Power BI dataset, pipeline Excel tự động, hiệu chỉnh dự thu tự động theo thực tế/vintage accuracy và giao hàng một phần đầy đủ vẫn là phần tiếp theo. Không đánh dấu hoàn thành vì đã có form.
- Cấu hình kho/định giá/repack/thu hồi vật tư và tổ chức lao động thuê ngoài cần xác nhận tại Lotus. Các công thức và lựa chọn tích hợp ở đây là cách triển khai có kiểm soát, không phải xác nhận nghiệp vụ đã được chấp thuận.
