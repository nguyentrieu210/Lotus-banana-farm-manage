# Lotus — khoán sản lượng và công nhật (bản triển khai V1)

## Nguyên tắc nghiệp vụ

Hai hình thức tồn tại song song theo **loại công việc**, nhưng mỗi kết quả công việc chỉ được tính tiền theo **một hình thức**:

- **Khoán sản lượng (Piece)**: tiền dự kiến trả = **số lượng được nghiệm thu** × **đơn giá khoán đã duyệt có hiệu lực tại ngày làm**. Không nhân với số công, số người, hay tiền công nhật.
- **Công nhật (Daywork)**: số công được xác nhận × đơn giá công (ví dụ thực tế Lotus thông tin 300.000đ/công). Đường thanh toán công nhật vẫn giữ quy trình hiện tại; PR này **không** tạo bảng thanh toán công nhật mới.
- Định mức như buồng/công vẫn dùng cho lập kế hoạch và KPI. 10 công được báo cáo chỉ là dữ liệu tham khảo trong phiếu thanh toán khoán; không làm tăng số tiền khoán.

## Ví dụ đối chiếu với ảnh bảng khoán

Một tổ trưởng nhận bao buồng tại thửa A01:
- Sản lượng báo và nghiệm thu: 800 buồng.
- Đơn giá đã duyệt: 4.000 VND/buồng, còn hiệu lực trong ngày làm.
- Tiền khoán: **800 × 4.000 = 3.200.000 VND**.
- Có 10 người (hoặc 10 công được ghi ở nhật ký): **không nhân thêm 10 × 300.000**.
- Nếu báo 850 nhưng chỉ nghiệm thu 800: số lượng trả 800, ghi lý do giảm 50; không sửa phiếu báo cáo gốc.

Các đơn giá của những công việc khác trong ảnh viết tay chưa được xác minh; không đưa số mặc định vào code.

## Cách nhập liệu trong app

1. Quản lý mở **Danh mục → Work Type** và đặt *Cách trả công = Piece* cho công việc bao buồng; giữ *Daywork* cho việc công nhật.
2. Tạo **Work Piece Rate**, chọn nông trường, công việc, đơn vị (ví dụ Bunch), 4.000 VND và khoảng ngày hiệu lực. **Submit** để phê duyệt. Không cho hai đơn giá đã nộp cùng loại việc/nông trường có thời gian hiệu lực chồng nhau.
3. Đội trưởng giao một hoặc nhiều việc/lô qua **Daily Work Plan**. Từng dòng kế hoạch phải chỉ rõ **Work Team** để xác định tổ nhận việc.
4. Tổ trưởng báo sản lượng theo thửa vào **Daily Work Result**, đính kèm ảnh/GPS nếu có. Kết quả đã nộp là bằng chứng đầu vào. Với Piece, **không cần nhập actual_workdays trên từng việc**; nếu có thì chỉ là thông tin KPI, không phải căn cứ tính khoán. Chấm công đầu ngày được quản lý riêng.
5. Có thể đặt **foreman_name** trong **Work Team** để cố định người nhận khoán mà không quản lý danh sách nhân công. Quản lý mở **Công việc → Work Piece Settlement**, chọn kết quả đã nộp, người nhận khoán (tự lấy từ Work Team nếu có), đơn giá đã duyệt và **accepted_qty**. Số báo cáo, thửa, loại việc, tổ, đơn vị, giá chốt, tiền và ngày làm lấy từ chứng từ gốc, không tin giá tiền gửi từ giao diện.
6. **Submit** để nghiệm thu: số tiền được chốt, người duyệt và thời điểm duyệt lưu lại. Một Work Result chỉ có tối đa một phiếu khoán đang có hiệu lực.
7. Muốn thay đổi số đã nghiệm thu: hủy phiếu nghiệm thu cũ có lý do, tạo bản sửa mới; trước khi hủy Work Result phải hủy phiếu nghiệm thu liên quan. Giá dùng trên phiếu cũ được lưu lại để kiểm toán.

## Kiểm soát đã triển khai

- Việc Piece không bị buộc phân bổ công vào từng dòng nhiệm vụ để chuyển sang Ready hoặc chốt ngày.\n- Không được dùng giá nháp, giá ngoài ngày hiệu lực, giá sai đơn vị, giá ở nông trường/công việc khác.
- Không được nghiệm thu hơn số lượng của Daily Work Result. Nghiệm thu ít hơn bắt buộc nêu lý do.
- Một kết quả không được tạo 2 phiếu nghiệm thu đang có hiệu lực, kể cả hai yêu cầu gần như đồng thời (khóa bản ghi nguồn).
- Tính tiền với Decimal, chỉ làm tròn VND sau phép nhân.
- Giá và phiếu nghiệm thu đã **Submit** lưu lịch sử và không được sửa trực tiếp. Giá có phiếu nghiệm thu đang hiệu lực không được hủy.
- Người duyệt phải có vai trò **Lotus Farm Manager** và được phân quyền nông trường. Auditor chỉ xem.

## Những việc CHƯA có trong PR

- **Không ghi sổ kế toán, không tạo Payment Entry / Payroll**. Đây mới là phiếu nghiệm thu tiền khoán để đối chiếu, chưa phải chứng từ thanh toán hay chứng nhận đã trả tiền.
- **Chưa có xác nhận hai tài khoản độc lập** (tổ trưởng + đội trưởng); hiện Submit bởi Farm Manager là bước nghiệm thu của quản lý. Cần xây cơ chế xác nhận đăng nhập riêng trước khi triển khai chính thức.
- Chưa có thanh toán theo tuần, đối soát công nợ tổ trưởng, xuất thanh toán kế toán, VAT/thuế, hay quy chế ký nhận và giải quyết tranh chấp.
- Công nhật 300.000đ/công chưa có quy tắc thanh toán mới ở PR này; không cộng với Piece.
- Chưa kiểm thử UAT trên dữ liệu/nông trường Lotus thật. Thử trên site ERPNext v16 riêng trước khi dùng trong vận hành.

## Code và test

- `lotus_farm/piece_pay.py` — quy tắc tính tiền và giới hạn nghiệm thu.
- `Work Type.payment_basis` — cách trả công mỗi loại việc.
- `Work Piece Rate` — danh mục giá được duyệt và thời hạn.
- `Work Piece Settlement` — giá chốt × sản lượng nghiệm thu từ Daily Work Result.
- `tests/test_piece_pay.py` — unit tests không cần Frappe.
- `lotus_farm/tests/test_brd.py` — kiểm thử với site ERPNext v16 nếu CI/site sẵn sàng.
