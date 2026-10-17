# Mô hình VIP 126: dữ liệu thực + dự phóng cuốn chiếu 36 tháng

## Đã ghi vào dữ liệu vận hành
- Xóa duy nhất Crop Cycle `CYCLE-00001` ở lô A13 (Nammy), đã kiểm tra không có chứng từ Link và sao lưu tại `sites/frontend/private/backups/lotus_cycle_CYCLE-00001_before_delete_20261018.json`.
- Nạp thực 64 hồ sơ lô Vườn 222 với giống `VIP 126`. Số cây của 30 lô (227.004 cây) lưu trường riêng `lotus_tree_count`; 34 lô để rỗng.
- 13 lô khu A: trổ **dự kiến** 01/11/2026; ngày trồng **suy ngược** 19/02/2026 (255 ngày trước), lưu riêng khỏi `planting_date` thật.
- Harvest Profile `HP-00002` lưu bộ hệ số ban đầu ở tình trạng **Draft, active=0**, không tham gia dự thu chính thức.

## Dự phóng live thử nghiệm
- Endpoint `lotus_farm.vip126_timeline.calendar` chỉ đọc dữ liệu live, chọn khu A–E / cả vườn và kịch bản thấp/cơ sở/cao, trả về 36 tháng kể từ tháng hiện tại.
- Mốc ưu tiên *theo dòng thời gian*: khi ghi một ngày chọn chồi thật, phần dự phóng từ ngày trổ kế hoạch được tính lại từ ngày chọn chồi; khi trổ thật, ưu tiên ngày trổ; khi thu thực tế, không cộng kỳ đó vào dự phóng nữa và chỉ dự tính các vụ sau.
- **Không ghi đè** `planting_date`, `Bunch Operation`, `Harvest Actual` hoặc lịch sử duyệt; chỉ ghi đè tính toán.
- Một lô có nhiều đợt cây chưa liên kết vẫn phải cảnh báo vì hiện một mốc chủ đạo/lô; không tự cộng trùng nhiều đợt. Cần thiết kế cohort chi tiết nếu quản lý đồng thời nhiều đợt trên cùng một lô.
- Kịch bản thấp/cơ sở/cao chỉ là phép thử độ nhạy cho VIP 126, không phải hệ số đã hiệu chuẩn. Khối lượng buồng 16/20/24 kg và các tỷ lệ sống, QC, packout chưa được người quản lý xác nhận bằng số cân thực tế.
- Số có thể cam kết bán **bằng 0** cho đến khi có phê duyệt theo nghiệp vụ.
- Riêng B–E chưa có mốc sinh trưởng xác thực hoặc ước tính, nên không tạo tháng dự thu giả từ số cây.

## Hệ số tham khảo nguồn
- Khoảng 10–14 tuần từ trổ đến thu tham khảo tại https://www.fao.org/4/ad523e/ad523e05.htm .
- Mốc 255 ngày từ trồng đến trổ, 270 ngày giữa vụ chồi, tỷ lệ số cây sắp trổ và tỷ lệ thành phẩm là giả định vận hành để thử mô hình, không phải thông số đã được chứng minh cho vườn Lotus/VIP 126.

## Cần làm để nâng cấp từ dự phóng sang dự thu được duyệt
- Ghi ngày chọn chồi từng đợt, số chồi được chọn và số cây sẽ trổ theo đợt; liên kết với `Crop Cycle`.
- Tạo phiếu trổ, cắt bắp, cân buồng, nhập QC và packout để hiệu chuẩn hệ số.
- Khi cấp quản lý phê duyệt bộ hệ số, mới đưa vào `forecast_calendar.calendar` và quy trình phát hành.
