# Audit PWA Lotus — 17/10/2026

Phạm vi: Kho (/warehouse), Mua hàng (/buying), Công việc (/work). Yêu cầu: logo lớn rõ chữ, header đỏ, một chuẩn Vant 4 và các nghiệp vụ liên quan dùng chung. Quy ước lâu dài nằm trong AGENTS.md và MOBILE_UI_STANDARD.md.

| Hạng mục | Chuẩn chung / xử lý |
| --- | --- |
| Khung 3 app | LotusMobileShell, Header, BottomNav, mobile-ui.css và theme; header đỏ, logo lớn rõ chữ, safe-area, bottom ẩn khi bàn phím mở |
| Trang chủ | LotusMobileAction; hai cột, thao tác chính toàn hàng; trạng thái disabled giữ quyền từng app |
| Link dữ liệu | MobileLinkField; tên vật tư/NCC/đề nghị luôn tìm/chọn, gõ chưa làm mất lựa chọn; IME, phím và kéo cuộn giữ nguyên |
| Lựa chọn ngắn | LotusMobileSelect/native: kho, công ty, đơn vị, cách mua; searchable=false khai báo rõ |
| Tạo/sửa đơn mua ở Kho và Mua hàng | Một MobilePurchaseOrderForm, cùng field, layout, đề nghị mua, đơn vị, tổng tiền, báo giá và kết quả lưu |
| Lưu và báo giá | mobile-purchase.js; kiểm tra ngày thật, số lượng dương, giá/đơn vị hợp lệ, giới hạn file; ghi nhận ID trước upload. Upload lỗi chỉ thử lại tệp, không gọi tạo đơn lần nữa |
| Nhà cung cấp | Một MobileSupplierForm; thêm NCC giữ mặt hàng của đơn và chọn NCC mới khi quay lại; giữ ID NCC trước bước làm mới dữ liệu |
| Chi tiết đơn mua | Một MobilePurchaseOrderDetail cho cả hai app; dòng hàng, trạng thái, tổng, đã nhận/còn chờ, báo giá, ghi chú. Duyệt/sửa/nhận giữ quyền API từng caller |
| Thông báo/tải | Một LotusMobileFeedback dùng NoticeBar/Loading cho lỗi, mất mạng, thành công, đang tải |
| Rời form | Một useMobileConfirm + LotusMobileDialog; ở lại giữ nội dung, rời xác nhận; supplier giữ đơn cha, beforeunload, khóa khi đang lưu |
| Phiếu kho/nhận hàng | Giữ các luồng nhập/xuất/chuyển, nháp/kiểm tra, số lượng và ngày nhận; dùng wrapper chung |
| Tồn kho/lịch sử | Giữ gợi ý tìm kiếm, lọc, phân trang và chặn phản hồi chi tiết đến muộn kéo người dùng khỏi tab hiện tại |
| Công việc | Dùng cùng shell/action/field/link/feedback/dialog; giữ giao việc, báo cáo, kết quả, hàng chờ offline, đồng bộ và quyền |
| Cài đặt/cập nhật PWA | Manifest/worker độc lập; build hash thay cache; giữ push inbox hiện có trên header |

## Lỗi tìm thấy và đã sửa

- Hai form mua trước đây khác trường và cách lưu: đã thay bằng một component và helper chung.
- Link đổi kiểu theo số lựa chọn: named link luôn searchable, native chỉ khi chỉ định.
- Nút wrapper dùng html-type, Vant 4 dùng native-type; nút lưu đã có DOM type=submit.
- CSS top label bỏ margin phải khiến control số lượng co về 0px: field top label xếp dọc và value đủ chiều rộng.
- Quay từ lưu NCC bằng history.back trong lúc saving có thể bị guard chặn: quay trực tiếp về form và cập nhật history.
- Upload báo giá lỗi sau khi tạo đơn có thể dẫn tới tạo lại đơn: lưu ID trước upload, dùng màn kết quả và retry attachment riêng.

## Kiểm chứng

- Frontend: 125/125 unit/static checks.
- Happy DOM: 24/24 luồng, gồm nhập/xuất/chuyển/nhận, popup/IME/cuộn/bàn phím, xác nhận, hai host cùng DOM form/validation, thêm NCC và giữ dòng (API giả, không ghi chứng từ thật).
- Vite production build đạt. Cảnh báo kích thước chunk desktop và class Tailwind có từ trước.
- Trình duyệt thực tế: 3 PWA × 3 kích thước (320×740, 390×844, 844×390); không tràn ngang, không có input co về 0px, header 54px và 4 tab. Popup NCC nằm dưới header; nhập số lượng và đi/quay lại form NCC giữ số lượng. Các trường/validation của hai form mua dùng chung, cùng chiều rộng; nút chọn file native có thể lệch 1px theo CSS font của host. Không có lỗi console trong phiên kiểm tra.

Không tạo/ghi sổ chứng từ thật trong QA. Các phép thử ghi của supplier/purchase dùng fixture; quyền backend và quy trình chứng từ tiếp tục do API hiện có quyết định.
