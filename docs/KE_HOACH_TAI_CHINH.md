# Kế hoạch tài chính

Truy cập **Tài chính – Kế toán → Kế hoạch tài chính** (`/lotus/tai-chinh?tab=planning`).

## Phạm vi

- Lập và lưu nhiều kế hoạch 1–36 tháng, theo công ty và tùy chọn một vườn.
- Ngân sách từng tháng: kg thu hoạch, kg thành phẩm dự kiến bán, giá bán; vật tư, nhân công, dịch vụ, đóng gói/kg, vận chuyển/kg, quản lý, khấu hao, lãi vay, thuế dự kiến; đầu tư, vốn vào, trả gốc, thu/chi khác.
- Lấy sản lượng từ Harvest Forecast đã phát hành, kiểm tra quyền và công ty/vườn. Xem trước nguồn rồi thay thế sản lượng các tháng; không cộng dồn khi bấm lại. Giá và ngân sách giữ nguyên. Không tạo dữ liệu giả hoặc tự đặt giá chuối/hệ số nông học.
- Tính doanh thu, lợi nhuận quản trị, dòng tiền, tiền cuối tháng, mức thiếu vốn cao nhất và khoản thu/chi còn sau kỳ kế hoạch.
- So sánh cơ sở với kịch bản tự nhập: tỷ lệ sản lượng, giá bán và đơn giá đóng gói/vận chuyển. Cơ sở = 100%; không tự gán xác suất hoặc mức tăng/giảm.
- Kế toán lưu nháp; kế toán trưởng duyệt khóa kế hoạch và chốt kết quả cùng phiên bản công thức. Nhân bản để lập phương án mới, giữ bản đã duyệt. Mỗi lần lưu kiểm tra phiên bản để chặn ghi đè thay đổi của người khác.

## Quy tắc tính

Doanh thu = kg thành phẩm dự kiến bán × giá chưa VAT. Kg thành phẩm không vượt kg thu hoạch. Đây là ngân sách quản trị: giả định bán hết số thành phẩm khai báo trong tháng; chi phí sản xuất được tính ở tháng lập ngân sách, chưa mô phỏng tồn kho/dở dang hay giá vốn chuẩn mực.

Chi phí hoạt động = vật tư + nhân công + dịch vụ + quản lý + kg thành phẩm × (đóng gói/kg + vận chuyển/kg). Lợi nhuận trước thuế = doanh thu − chi phí hoạt động − khấu hao − lãi vay; sau thuế trừ ngân sách thuế do người lập nhập. Không tự tính nghĩa vụ thuế.

Thu doanh thu và chi hoạt động lùi theo số tháng người lập chọn (0–12). Lãi vay, thuế, đầu tư, trả gốc và thu/chi khác thực hiện trong tháng khai báo. Khấu hao không chi tiền; vốn vào và trả gốc không làm thay đổi lợi nhuận. Công nợ trước kỳ nhập vào thu/chi khác của tháng dự kiến thanh toán. Cuối kỳ hiển thị riêng doanh thu chưa thu và chi phí chưa trả; không làm mất khoản ngoài khoảng dự phóng.

Không cộng dự thu nháp/đã thay thế/đã đóng. Một phiếu chỉ tính một lần ở tháng bắt đầu; phiếu qua nhiều tháng có cảnh báo, không tự chia đều. Phiếu vượt biên kỳ bị bỏ qua có cảnh báo. Kg thành phẩm lấy `packed_forecast_kg`, không lấy ATP (ATP đã trừ đơn đặt hàng).

## Nghiệm thu và triển khai

- Lưu/mở lại/nhân bản có đủ tháng, ngân sách và dấu nguồn. Nháp sửa được, bản duyệt bị khóa cả API lẫn Desk.
- Xem trước lấy dự thu cho biết phiếu và cảnh báo; nguồn đổi sau xem trước thì yêu cầu xem lại.
- Kiểm thử số học tiền, thu/chi trễ qua năm, công nợ ngoài kỳ, đầu tư/khấu hao/vốn, nguồn dự thu và phân quyền; mount giao diện lưu, lỗi và thay đổi bộ lọc; build frontend.
- Triển khai cần migrate DocType mới và build assets. Việc thêm module không tạo GL Entry, hóa đơn hoặc phiếu thu/chi và không tự kích hoạt ghi sổ kế toán.
