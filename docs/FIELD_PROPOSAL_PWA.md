# App đề xuất vật tư và chi phí (đội trưởng)

Địa chỉ sau khi triển khai: `https://lotus.gpcds.site/field-proposals`.

## Đội trưởng làm gì
1. Đăng nhập tài khoản nhân viên được cấp vai trò **Lotus Team Leader**.
2. Chọn **Đề xuất vật tư** hoặc **Đề xuất chi phí**; chọn vườn, lô (nếu có), ngày cần, lý do.
3. Nhập một hoặc nhiều khoản. Vật tư tìm từ danh mục ERP, vật tư mới có thể ghi tên; chi phí bắt buộc có số tiền dự kiến.
4. **Lưu nháp** hoặc **Gửi quản lý**. Nếu bị trả lại, mở phiếu để sửa và gửi lại.

## Quản lý làm gì
- Người có vai trò **Lotus Field Supervisor** hoặc **Lotus Farm Manager** sẽ thấy tab **Chờ duyệt**.
- Chọn **Đã duyệt**, **Trả lại**, **Từ chối**. Khi trả lại/từ chối phải nêu lý do.
- Không thể tự duyệt phiếu do chính mình tạo.
- Thông báo về phiếu được gửi tới hộp chuông ứng dụng; Web Push chỉ hoạt động sau khi thiết bị cho phép.

## Ranh giới nghiệp vụ
- Phiếu ở đây ghi nhận **nhu cầu**, không phải chứng từ mua hàng, cấp phát kho hay kế toán.
- Phê duyệt **không tự làm xuất kho, tạo đơn mua, tạm ứng hoặc thanh toán**.
- Bộ phận kho/mua hàng/kế toán tiếp tục xử lý theo quy trình hiện có. Bước nối tự động giữa đề xuất đã duyệt và chứng từ thực tế chưa nằm trong phiên bản đầu tiên.
- API chỉ cho phép người lập sửa nháp hoặc phiếu trả lại; người khác không đọc được phiếu của đội trưởng nếu không có vai trò quản lý. Tính lại tổng tiền ở máy chủ, không tin số tiền từ điện thoại.

## Kỹ thuật / vận hành
- Trang: `www/field_proposals.py`; app Vue/Vant 4: `frontend/src/FieldProposalMobile.vue`.
- Dữ liệu: `Lotus Field Proposal`, `Lotus Field Proposal Line`, không sửa trực tiếp chứng từ ERPNext.
- Chạy `npm test`, `npm run build` trong `frontend`; Python `test_field_proposal.py`. Sau khi sao lưu và so schema phải `bench --site frontend migrate` để tạo 2 DocType và thêm app `proposal` cho Push Device / Mobile Alert.
- Không tự gán quyền cho tất cả nhân viên. Quản trị cấp đúng vai trò người gửi/duyệt trước khi bàn giao ứng dụng.
- PWA có service worker riêng. Không cache API, file riêng tư hay dữ liệu đề xuất. Khi mất mạng không gửi hay ghi giả thành công.
