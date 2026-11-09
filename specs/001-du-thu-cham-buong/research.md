# Research: Dự thu từ số liệu chăm sóc buồng

## R1. Dùng engine nào

- **Decision**: Giữ `block_forecast_engine` cho phần theo số cây. Thêm `bunch_forecast_engine` kết hợp số thực tế với phần đó, trả về qua `block_forecast.board`. Khi xong, gỡ `forecast_calendar`, `vip126_timeline`, `vip126_trial` khỏi giao diện và `Vip126RollingForecast`.
- **Rationale**: `block_forecast_engine` đang là engine chính thức, có bộ tham số duyệt và phân đợt trổ. Nó chưa đọc số thực tế.
- **Alternatives**: Mở rộng `forecast_calendar` (đã có thứ tự ưu tiên nguồn) nhưng nó theo vụ và đợt chồi, lấy một nguồn cao nhất cho cả đợt, không xử lý được lô đang trổ dần. Phục hồi dự thu theo nhật ký chặt mẹ bị loại theo quyết định ngày 26/10 (`docs/FORECAST_BOOK2_AUDIT_20261026.md`).

## R2. Lưu số thực tế ở đâu

- **Decision**: Tạo một bảng sổ buồng theo lô, `Lotus Bunch Event`. Mỗi việc chọn chồi, chích bắp, cắt bắp, loại buồng, thu hoạch và số đầu kỳ là một dòng, có nguồn và khóa chống trùng. Dự thu chỉ đọc bảng này.
- **Rationale**: Chủ vườn quyết định ngày 09/11/2026 chỉ quản lý đến lô, không dùng thửa tưới. `Bunch Operation`, `Harvest Actual`, `Bunch Cancellation` và `Crop Cycle` kế thừa đều bắt buộc có thửa, và chưa có dòng dữ liệu nào, nên không có gì phải chuyển đổi.
- **Alternatives**: Gắn mỗi lô vào thửa lớn nhất (đã thử, ghi được 10/10 bước, nhưng trái quyết định trên và ghi số của cả lô vào một thửa). Nới kiểm tra thửa ở các bảng cũ phải sửa nhiều chỗ kiểm tra dùng chung và vẫn kéo theo khái niệm vụ.
- **Hệ quả**: Xưởng đóng gói sau này cần `Harvest Actual` thì phải làm cầu nối; hiện chưa dùng.

## R2b. Vụ

- **Decision**: Vụ gắn trực tiếp vào lô bằng `lotus_current_cycle_no`; mỗi dòng sổ buồng lưu số vụ tại lúc ghi. Chọn chồi ghi cho vụ kế tiếp. Vụ 1 là trồng mới, 64 lô hiện ở vụ 2, nên thành phẩm hiện tính 20 kg/buồng và chọn chồi đang làm thuộc vụ 3.
- **Rationale**: Chủ vườn chốt lô là đơn vị nhỏ nhất. Thành phẩm mỗi buồng tính theo vụ. Trong một lô, thu hoạch vụ này và chọn chồi vụ sau diễn ra cùng lúc, nên số vụ phải nằm trên từng dòng.

## R2c. Bảng nhập nhanh

- **Decision**: Chích bắp, cắt bắp, loại buồng và thu hoạch nhập trên một bảng theo lô, ghi thẳng vào sổ buồng ở trạng thái nháp, mỗi lô, ngày, việc, màu và tổ một dòng; lưu lại thì thay dòng cũ. Chọn chồi vẫn báo trên phiếu theo ha vì trả tiền theo lô, khi xác nhận mới sinh dòng sổ buồng. Bao buồng, tỉa, chống đổ giữ nguyên phiếu.
- **Rationale**: Phiếu buộc mỗi người mỗi buổi chỉ thuộc một phiếu, tức một lô, trong khi một nhóm làm nhiều lô trong một buổi. Các việc này trả công nhật theo chấm công nên không cần gắn người vào lô. Từ khi có hệ thống chưa có báo cáo nào theo phiếu.

## R3. Xác nhận theo ngày

- **Decision**: Thêm `confirmed_by`, `confirmed_at` vào `Lotus Work Entry`. Đội trưởng xác nhận theo ngày cho phiếu chăm buồng. Chỉ số đã xác nhận mới được ghi vào sổ buồng.
- **Rationale**: Phiếu chăm buồng là phiếu thường trực nhiều ngày, còn bước duyệt hiện tại là theo cả phiếu. Dự thu cần số mỗi ngày.
- **Alternatives**: Tạo phiếu mới mỗi ngày làm tăng thao tác của đội trưởng.

## R4. Lần cắt và màu dây

- **Decision**: Dùng `Bunch Tag` hiện có: nửa tuần 1 (thứ 2 đến thứ 5) là lần 1, nửa tuần 2 (thứ 6 đến chủ nhật) là lần 2. Mỗi tuần có mã riêng nên hai chu kỳ màu không lẫn.
- **Rationale**: Lịch đã có đến hết 2027, trùng với cách vườn cắt thứ 3-4 và thứ 6-7.

## R5. Không đếm trùng giữa các tầng

- **Decision**: Tính dòng chảy theo lô. Tầng 1: cắt bắp theo màu trừ loại, trừ đã thu. Tầng 2: chích bắp lũy kế trừ cắt bắp lũy kế, lấy theo thứ tự chích trước cắt trước; các đợt cắt trong 16 ngày đầu sau ngày áp dụng không trừ vì thuộc lứa chích trước đó (FR-025). Tầng 3: số buồng theo số cây của vụ trừ đi số đã quan sát, trừ dần từ đợt trổ sớm nhất. Tầng 4: vụ sau lấy số lượng từ số kiểm kê, lấy thời điểm từ ngày chọn chồi thật nếu có.
- **Rationale**: Thực tế vườn không tách được "đợt" khi nhập. Trừ theo dòng chảy luôn giữ tổng không vượt.
- **Alternatives**: Bắt nhập theo đợt làm nặng thao tác ngoài vườn.

## R6. Nhập sổ cắt bắp

- **Decision**: Đọc theo vị trí cột (G đến Z, mỗi tuần 2 cột), không theo nhãn, vì tuần 46 hai cột cùng ghi "CAM". Cột đầu là lần 1, cột sau là lần 2. Ngày cắt: thứ 4 cho lần 1, thứ 7 cho lần 2. Bỏ qua cột C, D, E. Ghi `legacy_source_key` là lô, tuần, lần.
- **Rationale**: Số đã xác nhận với chủ vườn ngày 09/11/2026. Khóa nguồn giúp chạy lại không trùng.

## R7. Thời gian thu và cửa sổ

- **Decision**: Từ tham số: cắt bắp đến thu 60 đến 70 ngày, chia đều số nguyên theo ngày. Tỷ lệ thu chỉ áp cho phần hao hụt còn lại sau khi đã trừ buồng loại thật (FR-027). Phần theo số cây đã quá thời điểm được dồn sang các tuần tới (FR-028). Nếu lô có số đo thực tế thì hiệu chỉnh ở bộ tham số.
- **Rationale**: Khớp xác nhận ngày 18/10 và phép chia bảo toàn tổng đang dùng. Dạng phân bố thực tế sẽ có sau các lứa thu đầu.

## R8. Tham số

- **Decision**: Dùng `Lotus Block Forecast Profile`, đã có phiên bản, duyệt, ngày hiệu lực, phạm vi vườn hoặc lô. Mùa được biểu diễn bằng khoảng hiệu lực. Thêm tham số cắt bắp đến thu sớm và muộn nếu chưa có.

## R9. Chốt bản dự thu

- **Decision**: Tạo `Lotus Forecast Snapshot` lưu kết quả theo tuần và lô mỗi thứ 2, kèm bộ tham số.
- **Alternatives**: `Harvest Forecast` theo từng vụ và có quy trình phát hành nặng, không phù hợp để lưu bản tổng hằng tuần.

## R10. Việc nhập mới

- **Decision**: Gán công đoạn `Sucker Select` cho việc "Chọn F (chọn chồi)" đang có, báo theo ha như tiền công hiện tại, không đếm chồi; số chồi ước tính bằng số cây kiểm kê nhân tỷ lệ ha đã làm trên diện tích lô, tổng không vượt số cây. Vụ của chọn chồi theo FR-026.
- **Rationale**: Mỗi gốc thường giữ một chồi nên số chồi gần bằng số cây sống. Giá trị chính của chọn chồi cho dự thu là ngày chọn theo lô.
- **Khác**: Dự thu cũ còn được đọc ở trang chủ, cung ứng, kế hoạch tài chính và khoảng 10 nơi khác; việc gỡ phải liệt kê đủ (T040).
