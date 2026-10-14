# Chấm công Lotus và Frappe HRMS

Địa chỉ: `/lotus/cham-cong`. Quản trị HRMS chính thức: `/desk/hr-setup`. `/hrms` là cổng tự phục vụ dành cho tài khoản có Employee liên kết, không phải trang quản trị cho Administrator.

## Nhân sự chủ chốt / ban điều hành

Tạo hồ sơ nhân viên thật ở Nhân sự & thiết lập (họ tên, giới tính, ngày sinh, ngày vào làm, chức vụ, bộ phận). Hồ sơ lưu vào Employee native. Không tự tạo User, không gửi email, không dùng nhân viên giả để điền chỗ trống.

Bảng ngày lưu Attendance native của HRMS. Chọn ngày/ca, nhập trạng thái và giờ làm, lưu nháp rồi duyệt các dòng đã kiểm tra. Có mặt = 1 công, nửa ngày = 0,5, từ xa = 1; vắng/nghỉ phép/chưa chấm = 0 công đi làm. Nghỉ phép dùng quy trình HRMS. Chưa có bản ghi luôn là chưa chấm, không tự chuyển thành vắng. Nhiều ca cùng ngày cộng giờ nhưng tổng công tối đa 1/người/ngày. Công tương lai và trước ngày vào làm bị chặn. Tổng công tháng chỉ tính bản đã duyệt; nháp có dấu `*`.

HRMS xử lý nghỉ phép, lịch/ca, chấm công tự động, lương theo cấu hình native khi cần. Đợt này chưa cấu hình máy chấm công hoặc cơ cấu lương thực tế.

## Công nhân khoán / đầu câu

Tạo nông trường (nếu chưa có), đội khoán, tên đầu câu. Mỗi đội có một phiếu công hiệu lực/ngày: tổng người, có mặt, tổng công thực tế, khối lượng, đơn vị khoán, đơn giá khoán và ghi chú. Số có mặt không vượt tổng người; tổng công không vượt số có mặt. Giá trị = khối lượng × đơn giá. Đây là bằng chứng công/khối lượng để quản trị, chưa phải chứng từ thanh toán/công nợ.

Phiếu có Nháp → Đã duyệt → Đã hủy, hủy cần lý do. Khi hủy có thể lập phiếu mới đúng ngày/đội. Không sửa danh tính phiếu đã lưu; hủy/lập lại nếu chọn sai. Tổng tháng và giá trị chỉ cộng phiếu đã duyệt. In bảng công và xuất CSV hỗ trợ riêng nhân sự/đội khoán, theo công ty/tháng/nông trường đang chọn.

## Quyền

- HR Manager quản trị nhân sự/chấm công theo quyền HRMS và các User Permission hiện có.
- Lotus Farm Manager quản trị phiếu công đội trong nông trường được cấp.
- Lotus Crew Leader nhập/sửa nháp và in công đội được cấp; không duyệt/hủy hay đọc Employee/Attendance chính thức.
- Quản trị viên cấp User Permission Company, Farm **và Work Team** cho từng đầu câu. Không tự gán role hoặc mở rộng quyền người dùng thật trong quá trình cài.
- Mọi API ghi dùng POST/CSRF, quyền native và kiểm modified. Nhập lại cùng mã yêu cầu không nhân đôi phiếu; nội dung khác cùng mã bị từ chối.

## Kiểm tra

`tests/integration/verify_timekeeping.py` chạy trong bench có HRMS và site `frontend`: tạo dữ liệu tạm, nháp/duyệt/hủy, đổi phiên bản, retry, tương lai, nửa ngày, tổng tháng, đội khoán, quyền đầu câu, HTML/PDF/CSV rồi rollback. Đặt `QA_ARTIFACT_DIR` nếu cần lưu PDF phục vụ kiểm tra trực quan; không commit thông tin nhân sự thật/bản in thật vào Git.
