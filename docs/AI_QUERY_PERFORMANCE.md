# Hiệu năng tra cứu AI

Các lỗi chờ 85 giây trước đây chủ yếu do gọi lại mô hình/key bị giới hạn theo phút hoặc ngày, chờ mạng tối đa 35 giây mỗi lượt và vòng tra cứu nhiều bước. Hai key hợp lệ không tự gộp hạn mức theo mô hình/tài khoản.

`ai_chat._complete` luân phiên hai key cấu hình sẵn, bỏ qua từng cặp mô hình/key đang cooldown và chuyển dự phòng ngay. HTTP 429 dùng Retry-After thực tế, gồm hạn mức ngày; lỗi mạng được tạm bỏ qua 30 giây. Không ngủ chờ hạn mức trong request. Qwen dùng chế độ không suy luận; các GPT-OSS dự phòng dùng mức thấp. Request JSON gửi UTF-8 gọn, lịch sử và kết quả công cụ đều giới hạn kích thước.

`ai_reports.answer` xử lý trực tiếp các câu hỏi đầu tiên, rõ phạm vi về tồn kho, nhân viên đang làm việc, chi phí tháng này, đơn mua chờ hàng và chấm công hôm nay. Các câu này gọi cùng công cụ query kiểm tra quyền, lấy dữ liệu mới và không gọi mô hình. Câu hỏi tiếp nối hoặc có vườn/kỳ riêng tiếp tục qua mô hình để giữ ngữ cảnh. Khoản chi khác công ty/tiền tệ và số lượng khác đơn vị không được cộng chung; dữ liệu đạt giới hạn không tạo kết luận tồn tối thiểu.

Response có `timing.total_ms`, `timing.model_calls`; đường trực tiếp có `route=direct`. Log lỗi mô hình chỉ lưu tên mô hình, vị trí key, loại lỗi và cooldown, không ghi key hoặc nội dung hỏi đáp. Desktop không đưa lượt gửi thất bại vào lịch sử; các lượt lặp y hệt từ client cũ được gộp trước khi xử lý.

Kiểm thử: `lotus_farm.tests.test_ai_chat`, `test_ai_reports`, `test_ai_provider`; kiểm tra thực tế trên site thử bằng tài khoản hạn quyền và đo HTTP trước khi phát hành. Không lưu cache câu trả lời chứa dữ liệu nghiệp vụ.
