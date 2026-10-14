# Audit kho Lotus — 14/10/2026

Phạm vi: mã nguồn Lotus, đối chiếu các luồng kho với ERPNext đang chạy; không chỉnh dữ liệu vận hành.

| Mức | Phát hiện | Cách xử lý cần kiểm chứng |
|---|---|---|
| Cao | `overview.shortage_qty` chỉ là thiếu so với tồn tối thiểu, không phải nhu cầu công việc | Tách cảnh báo tối thiểu và bảng nhu cầu có thời hạn, nguồn và kho cấp |
| Cao | Báo cáo vật tư trừ lượng tiêu hao trong khi sổ kho đã trừ lượng xuất; có thể tính thiếu thêm hàng đang ở đội | Tách cần cấp, đã cấp, đang lập phiếu, đã dùng và thu hồi; nhu cầu cấp trừ phiếu xuất đã ghi sổ |
| Cao | Phiếu nháp giữ hạn mức nguồn nhưng chưa giữ tồn khả dụng giữa các nguồn | Tính các dòng xuất/chuyển nháp trong khả dụng; tránh trừ hai lần phiếu nháp thuộc nhu cầu đang xét |
| Cao | Chưa tổng hợp đơn mua đang chờ nhận; tạo đề nghị mua theo từng nhu cầu có thể tranh cùng tồn | Tổng hợp theo vật tư/kho, dùng đơn mua đã duyệt và lượng chưa nhận, hiển thị ngày hẹn; chống tạo đề nghị mua trùng |
| Cao | Kiểm kê gửi `rate:0` mặc định, máy chủ chấp nhận là giá vốn mới | Kiểm kê thường chỉ sửa số lượng, giữ giá vốn theo thời điểm kiểm kê; tồn đầu kỳ nhập giá riêng |
| Vừa | Danh sách phiếu chỉ 20 phiếu kho + 10 kiểm kê, không theo kho đã chọn | Danh sách đầy đủ, lọc trước phân trang, theo kho/ngày/tìm mã |
| Vừa | Lưu phiếu mới chưa có khóa chống gửi lặp sau mất phản hồi | Khóa yêu cầu theo người dùng, so nội dung; thử lại trả cùng phiếu |
| Vừa | Nguồn chưa xác định kho và thiếu quyền dữ liệu có thể bị hiểu là đủ hàng | Hiển thị rõ chưa xác định kho/chưa đủ quyền, không trả số đủ hàng giả |

Nền tảng đã có: danh mục, nhập/xuất/chuyển/kiểm kê, chi phí phân bổ vào giá nhập, lịch sử sổ kho, hạn mức nguồn xuất có khóa, tiêu hao/thu hồi liên kết phiếu, kiểm quyền và kiểm tra liên kết khi xóa.

Lô/serial, quy trình mua hàng/kế toán nâng cao vẫn dùng nghiệp vụ ERPNext chuẩn; audit này không tự thay đổi chính sách kế toán hoặc tự ghi sổ/duyệt phiếu kinh doanh.

## Kết quả sửa

Đã xử lý các phát hiện trong bảng trên. Màn `Nhu cầu & mua vật tư` tổng hợp nhu cầu được duyệt theo vật tư/kho/khoảng ngày, trừ lượng cấp ròng sau thu hồi, tách giữ chỗ của nhu cầu đang xem với nhu cầu khác. Yêu cầu cấp liên kết kế hoạch không được cộng thêm một lần. Nguồn chưa có kho, kế hoạch chưa duyệt nhu cầu hoặc thiếu quyền được báo rõ, không gán trạng thái đủ hàng.

Đề nghị mua nháp/đã duyệt không tính là hàng chờ nhận. Đơn mua đã duyệt chỉ góp phần chờ nhập theo số chưa nhận và ngày hẹn trong kỳ; đơn hẹn sau kỳ và quá hẹn được hiển thị riêng. Kho lập phiếu nhận nháp theo đơn mua, nhập lượng thực nhận theo đơn vị tồn, dùng quy đổi và giá/tax chuẩn của đơn mua. Ghi sổ riêng có xác nhận và cập nhật số đã nhận/chờ nhập. Không tự tạo công nợ nhà cung cấp từ một phiếu nhập kho thủ công.

Danh sách phiếu lấy đủ tài liệu trước lọc/phân trang, theo kho/ngày/mã, gồm nhận hàng theo đơn mua. Lịch sử có tồn đầu và tồn cuối mỗi giao dịch lấy từ Stock Ledger, không cộng dồn từ trang hiện tại. Bản in Lotus kiểm quyền, in đủ dòng, có trạng thái nháp/hủy, chi phí khi phù hợp và ô chữ ký.

Kho Stores chưa có Bin, phiếu hoặc sổ kho; đã gỡ mặc định khỏi 47 Item Default và Stock Settings rồi xóa bằng API chuẩn. Giữ nguyên 47 vật tư, 2 Stock Entry và 1 Stock Ledger Entry tại thời điểm xử lý. Form xóa kho có xác nhận gỡ mặc định, kiểm quyền từng Item/Stock Settings và hoàn tác toàn bộ nếu còn liên kết khác. Không xóa cưỡng bức.

Kiểm chứng: 80 unit test Python, 21 test frontend; build Vite. Script `tests/integration/verify_warehouse_audit.py` chạy trong bench local site `frontend`, company `Lotus Agritech`, dùng dữ liệu riêng và rollback toàn bộ giao dịch thử. Kiểm tra đủ: nguồn chưa xác định, giữ phiếu nháp, cấp một phần, tiêu hao, thu hồi, nguồn cấp trùng kế hoạch, đơn mua, chống đề nghị mua trùng, nhận một phần và chống nhận quá đơn, gửi lại cùng yêu cầu, giữ giá vốn kiểm kê, lọc kho, tồn đầu/cuối và render bản in có kiểm quyền; đã tạo PDF hợp lệ từ phiếu thực tế (23.802 byte).

Công ty đã đổi tên bằng frappe.rename_doc thành Lotus Agritech; giữ mã LT, toàn bộ liên kết và số tồn/giá trị tồn. Đầu bản in và PDF dùng tên công ty, dưới là Farm 222 Thuận Phú (Company.lotus_print_farm). Chạy lại toàn bộ integration sau đổi tên: đạt, PDF hợp lệ, rollback dữ liệu thử.
