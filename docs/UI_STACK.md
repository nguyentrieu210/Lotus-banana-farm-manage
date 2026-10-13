# Giao diện Lotus Manage: shadcn-style + Attio + AG Grid

## Phân công rõ ràng
- **Vue 3** dựng các màn hình; ERPNext/Frappe vẫn là nơi xử lý nghiệp vụ và quyền.
- **Frappe UI** vẫn được giữ trong dự án; không thay API, session, CSRF hay đồng bộ offline trong lần đổi giao diện này.
- **shadcn-vue-style local Button** tại `frontend/src/components/ui/Button.vue`: nút Vue có biến thể mặc định, phụ, viền và trạng thái đang chạy. Đây là component tự giữ trong repo, làm theo cách tổ chức của shadcn-vue; **chưa cài trọn bộ shadcn-vue CLI** hay chuyển dự án sang React/Tailwind v4.
- **Attio-inspired CSS** tại `frontend/src/attio.css` và `assign-attio.css`: lấy cảm hứng từ bố cục sáng, gọn, viền mảnh, không sao chép mã nguồn hay hình ảnh Attio.
- **AG Grid Community 36.2.0** tại `OpsList.vue`: thay bảng HTML trên màn hình quản lý. Lọc, sắp xếp và co giãn cột trong dữ liệu **của trang hiện tại**, không thay phân trang và bộ lọc phía máy chủ.

## Quy tắc khi làm tiếp
- Màn hình văn phòng có nhiều cột: dùng `OpsList` / AG Grid. Khi muốn sửa ô, phải xây dựng riêng API lưu có kiểm tra quyền và đối soát; **chưa bật sửa hàng loạt**.
- Điện thoại: danh sách chuyển thành các nút từng phiếu; thao tác giao việc nhanh vẫn là form riêng.
- Form đặc thù (giao khoán, chấm công, vật tư) phải ưu tiên thao tác ít bước, không tự động mang bảng Excel vào điện thoại.
- Các thành phần mới nên theo bộ màu và kích thước trong `attio.css`, không thêm một framework giao diện nữa.

## Kiểm tra trước khi nhập vào main
```bash
npm ci --prefix frontend
npm run --prefix frontend build
npm run --prefix frontend test
```
Sau khi triển khai lên **một Frappe site thử nghiệm**, phải mở và thử: `/lotus/today`, danh sách công việc/vật tư/chấm công, mở một phiếu từ AG Grid, `/lotus/mobile`, `/lotus/giao-viec`; xem cả điện thoại và máy tính. Xác nhận quyền đọc/ghi và tính năng khi mất mạng không thay đổi.

**Trạng thái:** Sửa code giao diện, chưa được chứng nhận là đã chạy thành công trên site sản xuất. Không áp dụng tự động tới bản ERPNext Desk `/app` hoặc giao diện hiện trường dự phòng HTML.
