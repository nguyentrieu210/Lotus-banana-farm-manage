# Chat nội bộ Lotus

Bong bóng dùng chung có hai tab: Trợ lý AI và Tin nhắn. Chat riêng giữ một hội thoại duy nhất cho mỗi cặp tài khoản. Nhóm có tên và danh sách thành viên do người tạo chọn, tối đa 50 người. Tin nhắn được lưu trên máy chủ, có phân trang, tin chưa đọc, trạng thái online, đang nhập và đã xem. Chưa có sửa/xóa tin nhắn hay thay đổi thành viên sau khi tạo nhóm.

Tệp được tải riêng tư trước khi gửi, tối đa 20 MB/tệp và 5 tệp mỗi lượt. Gửi lại dùng cùng mã tin để tránh trùng sau lỗi mạng. Tải tệp/xem ảnh đều kiểm tra thành viên qua `lotus_farm.chat.download`; File tiếp tục gắn với tin nhắn riêng tư. Hook `before_validate` ngăn chuyển tệp sang public trước khi Frappe di chuyển tệp trên đĩa.

## Dữ liệu và quyền

- `Lotus Chat Room`: loại, tên nhóm, khóa cặp chat riêng, thứ tự tin cuối.
- `Lotus Chat Member`: bảng con gồm tài khoản và thứ tự tin đã đọc.
- `Lotus Chat Message`: nội dung văn bản nguyên dạng, thứ tự và thông tin tệp.
- API yêu cầu tài khoản System User đang hoạt động và kiểm tra thành viên trước mọi thao tác trên hội thoại. Permission/query hooks cũng áp dụng cho REST, đọc File và công cụ AI. Tin nhắn không được gửi tới AI tự động.
- Khóa dòng hội thoại đảm bảo thứ tự gửi và trạng thái đọc chỉ tăng. Mã tin được suy ra từ hội thoại, người gửi và mã gửi của trình duyệt.

## Thông báo tin nhắn

- Ứng dụng gửi Web Push đến thiết bị người nhận đã chủ động bật thông báo, kể cả khi tài khoản đang mở Lotus trên máy tính hoặc trình duyệt khác. Không gửi lại cho người gửi; mỗi hội thoại/người nhận giới hạn một lần gửi đẩy trong 30 giây.
- Mở tab **Tin nhắn** trên điện thoại, chọn **Bật thông báo tin nhắn** một lần trên thiết bị (hoặc đã bật qua chuông thông báo của PWA). Thiết bị không cấp quyền vẫn thấy số tin chưa đọc khi mở ứng dụng.
- Bấm thông báo sẽ mở thẳng cửa sổ chat của PWA; trong ứng dụng dùng dấu số tin chưa đọc. Phải kiểm tra thực tế trên Android/iPhone vì hệ điều hành quyết định hiển thị thông báo và có thể giới hạn chạy nền.

## Realtime và phát hành

Socket.IO dùng namespace của site, phiên đăng nhập hiện tại và phòng riêng theo người dùng của Frappe. Redis chỉ phát thông báo tới thành viên; sự kiện chứa mã hội thoại/thứ tự, nội dung được lấy qua API có kiểm tra quyền. Khi mất socket, trình duyệt tự đồng bộ mỗi 5 giây; khi có socket, đồng bộ định kỳ 30 giây. Trình duyệt không lưu lịch sử chat nội bộ vào offline cache.

`deployment/fix-websocket-origin.py` giữ Origin trình duyệt trong mẫu nginx để kiểm tra cùng hostname của Frappe hoạt động qua tên miền public; không thay đổi kiểm tra Origin ở máy chủ socket.

Sau sao lưu và kiểm tra schema, image mới có thể thêm đúng ba DocType bằng:

```sh
bench --site frontend execute lotus_farm.chat.install
```

Lệnh này không migrate các schema nghiệp vụ khác. Khi rollback về image chưa có permission hooks chat, phải khóa quyền đọc/select của ba DocType mới trước khi bật lại truy cập để lịch sử còn lại không được mở qua REST.

Kiểm thử backend chỉ chạy trên site dùng thử:

```sh
python -m unittest lotus_farm.tests.test_chat lotus_farm.tests.test_ai_chat
```

Frontend: `npm test` và `npm run build` trong `frontend/`. Kiểm tra trình duyệt bằng nhiều tài khoản riêng trên site thử, gồm gửi/tải tệp, người ngoài hội thoại, reconnect và bốn PWA ở màn hẹp.
