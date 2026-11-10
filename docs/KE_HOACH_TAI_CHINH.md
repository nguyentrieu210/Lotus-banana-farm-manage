# Kế hoạch tài chính

Truy cập **Tài chính – Kế toán → Kế hoạch tài chính** (`/lotus/tai-chinh?tab=planning`).

## Phạm vi

- Lập và lưu nhiều kế hoạch 1–36 tháng, theo công ty và tùy chọn một vườn.
- Ngân sách từng tháng: kg thu hoạch, kg thành phẩm dự kiến bán, giá bán; vật tư, nhân công, dịch vụ, đóng gói/kg, vận chuyển/kg, quản lý, khấu hao, lãi vay, thuế dự kiến; đầu tư, vốn vào, trả gốc, thu/chi khác.
- Lấy sản lượng từ dự thu chung (màn Dự thu) của vườn của kế hoạch, hoặc của mọi vườn trong công ty người lập được xem; dự thu tự kiểm tra quyền từng vườn. Xem trước nguồn rồi thay sản lượng từ tháng hiện tại đến hết kế hoạch; các tháng đã qua giữ nguyên. Không cộng dồn khi bấm lại. Giá và ngân sách giữ nguyên. Không tạo dữ liệu giả hoặc tự đặt giá chuối/hệ số nông học.
- Tính doanh thu, lợi nhuận quản trị, dòng tiền, tiền cuối tháng, mức thiếu vốn cao nhất và khoản thu/chi còn sau kỳ kế hoạch.
- So sánh cơ sở với kịch bản tự nhập: tỷ lệ sản lượng, giá bán và đơn giá đóng gói/vận chuyển. Cơ sở = 100%; không tự gán xác suất hoặc mức tăng/giảm.
- Kế toán lưu nháp; kế toán trưởng duyệt khóa kế hoạch và chốt kết quả cùng phiên bản công thức. Nhân bản để lập phương án mới, giữ bản đã duyệt. Mỗi lần lưu kiểm tra phiên bản để chặn ghi đè thay đổi của người khác.

## Quy tắc tính

Doanh thu = kg thành phẩm dự kiến bán × giá chưa VAT. Kg thành phẩm không vượt kg thu hoạch. Đây là ngân sách quản trị: giả định bán hết số thành phẩm khai báo trong tháng; chi phí sản xuất được tính ở tháng lập ngân sách, chưa mô phỏng tồn kho/dở dang hay giá vốn chuẩn mực.

Chi phí hoạt động = vật tư + nhân công + dịch vụ + quản lý + kg thành phẩm × (đóng gói/kg + vận chuyển/kg). Lợi nhuận trước thuế = doanh thu − chi phí hoạt động − khấu hao − lãi vay; sau thuế trừ ngân sách thuế do người lập nhập. Không tự tính nghĩa vụ thuế.

Thu doanh thu và chi hoạt động lùi theo số tháng người lập chọn (0–12). Lãi vay, thuế, đầu tư, trả gốc và thu/chi khác thực hiện trong tháng khai báo. Khấu hao không chi tiền; vốn vào và trả gốc không làm thay đổi lợi nhuận. Công nợ trước kỳ nhập vào thu/chi khác của tháng dự kiến thanh toán. Cuối kỳ hiển thị riêng doanh thu chưa thu và chi phí chưa trả; không làm mất khoản ngoài khoảng dự phóng.

Lấy sản lượng dự thu (`planning_rules.forecast_quantities`): dự thu chung tính từ hôm nay, mỗi buồng xếp vào tháng của ngày dự kiến thu. Kg thành phẩm = số buồng × kg thành phẩm mỗi buồng của vụ × tỷ lệ đóng gói, đúng số màn Dự thu. Dự thu không có kg buồng cân ngoài vườn: kg thu hoạch là mọi buồng thu nhân cùng kg mỗi buồng, nên chỉ khác kg thành phẩm ở số buồng không đóng gói.

- Tháng trước tháng hiện tại giữ nguyên số đang có: dự thu không nói gì về những ngày đã qua.
- Tháng hiện tại = kg các ca đóng gói đã đóng từ đầu tháng đến hôm nay (thu hoạch là kg đưa vào ca, thành phẩm là kg thành phẩm) cộng dự thu những ngày còn lại. Buồng của ca đã đóng đều đã ghi thu hoạch, nên dự thu không tính lại chúng; buồng đã ghi thu hoạch mà chưa vào ca nào đã đóng thì chưa có trong tháng (thường chỉ là buồng thu trong ngày).
- Các tháng sau = dự thu. Tháng không có nguồn về 0. Buồng dự kiến thu ngoài các tháng của kế hoạch bị bỏ.
- Mỗi tháng, vườn và căn cứ (ca đã đóng, buồng đã cắt bắp, đã chích bắp, theo chồi đã chọn, theo số cây) có một dòng nguồn ghi số buồng và kg, cho biết số đó chắc đến đâu. Lô đang dùng thông số mặc định (chưa có bộ được duyệt) có cảnh báo.
- Kế hoạch mà mọi tháng đã qua thì không có gì để thay.

## Nghiệm thu và triển khai

- Lưu/mở lại/nhân bản có đủ tháng, ngân sách và dấu nguồn. Nháp sửa được, bản duyệt bị khóa cả API lẫn Desk.
- Xem trước lấy dự thu cho biết các tháng được thay, các tháng giữ nguyên, nguồn từng tháng và cảnh báo; dự thu hay ca đóng gói đổi sau khi xem trước thì yêu cầu xem lại.
- Kiểm thử số học tiền, thu/chi trễ qua năm, công nợ ngoài kỳ, đầu tư/khấu hao/vốn, nguồn dự thu và phân quyền; mount giao diện lưu, lỗi và thay đổi bộ lọc; build frontend.
- Triển khai cần migrate DocType mới và build assets. Việc thêm module không tạo GL Entry, hóa đơn hoặc phiếu thu/chi và không tự kích hoạt ghi sổ kế toán.
