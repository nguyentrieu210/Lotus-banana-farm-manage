# Dự thu tự động 36 tháng — bước đầu

- Màn đầu /lotus/forecast mặc định là kế hoạch dự thu theo tháng / lô / vụ, 36 tháng tính từ ngày bắt đầu lựa chọn.
- Không yêu cầu tạo phiếu riêng trước khi xem.
- Nguồn ưu tiên theo đợt: cắt bắp > trổ buồng > chọn chồi > ngày trồng > vụ chồi tương lai.
- Khi cùng một đợt có nhiều giai đoạn, không cộng gộp. Khi một phần của đợt chưa chuyển công đoạn, hệ thống cảnh báo cần tách đợt.
- Dữ liệu thiếu mã đợt được cảnh báo, không cộng trùng với đợt đã có mã.
- Số trồng = diện tích lô × mật độ cây, mang độ tin cậy thấp, chỉ sử dụng với bộ hệ số đã duyệt.
- Hai thông số bổ sung cho Harvest Profile: planting_to_harvest_days và ratoon_interval_days, **không có giá trị mặc định tự bịa**.
- Dự phóng vụ chồi chưa có ghi nhận được sinh trên báo cáo, không tạo Crop Cycle hay Harvest Forecast.
- Không phát hành dự thu, không tạo phiếu kho/giữ hàng; các phiếu đã phát hành vẫn vận hành theo nghiệp vụ cũ trong mục nâng cao.
- Dữ liệu không đủ căn cứ tạo cảnh báo, không tự bổ khuyết bằng số giả.
- Khi chưa có bộ hệ số được duyệt, biểu đồ có thể trống và hiện cảnh báo.
- Lưu ý: ước tính theo diện tích lô, chưa xử lý sản lượng của các đợt cây không gắn được quan hệ phân tách; bắt buộc đối chiếu trước khi sử dụng để cam kết giao hàng.
