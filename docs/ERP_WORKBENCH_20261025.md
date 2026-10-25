# Giao diện ERP riêng trong Lotus

## Phạm vi bản hiện tại

Lotus tự dựng menu phân hệ, danh sách, biểu mẫu và báo cáo bằng Vue. Không nhúng Desk, không mở liên kết Desk để thay cho một màn nghiệp vụ. Dữ liệu và việc ghi sổ vẫn chạy trên DocType, controller, báo cáo, quyền và hooks ERPNext/HRMS đang cài.

- Các đường dẫn Kho, Mua hàng, Kế toán, Nhân sự và Chấm công dùng chung workbench. Tài khoản chỉ ký tài chính tiếp tục vào màn ký được phép.
- Danh sách tìm kiếm, lọc và phân trang ở máy chủ; xuất Excel gồm toàn bộ dữ liệu theo bộ lọc.
- Biểu mẫu giữ tab, section, bảng con và điều kiện metadata; tra cứu liên kết, quy đổi đơn vị, tính thuế/tổng tiền, đính kèm tệp riêng tư và in PDF.
- Thêm nhanh Supplier/Item quay lại trường và dòng đang nhập. Supplier dùng chung; lịch sử báo giá, đơn mua, phiếu nhận, hóa đơn, thanh toán và công nợ theo công ty. Quyền kế toán bảo vệ trường ngân hàng.
- Đề nghị, báo giá, đơn mua, nhận hàng, hóa đơn, trả hàng và thanh toán dùng mapping native. Đề nghị mua, đơn mua và phiếu chi giữ chuỗi ký Lotus; API lưu/duyệt chung không vượt được chuỗi ký.
- Phiếu nhập trực tiếp vẫn cần lý do Purchase/Recovery/Surplus; Surplus không cần đơn mua. Quy tắc ghi tài khoản và nguồn thu hồi do hooks hiện có kiểm tra.
- Kế hoạch tài chính, nhu cầu vật tư vườn, báo cáo kế toán Việt Nam, chọn báo giá, chi hộ/hoàn ứng và công nợ ngày chốt còn truy cập được trong nhóm Lotus.
- Báo cáo tài chính dựng bộ lọc, tổng hợp, biểu đồ, bảng cây và drilldown trong Lotus. Cấu hình bộ lọc được xuất từ mã ERPNext/HRMS đang cài bằng AST; không thực thi JavaScript lấy từ Desk.
- Timeout bao phủ cả response header và body. Gửi lại thủ công giữ mã yêu cầu cũ; kiểm tra phiên bản và claim duy nhất ở máy chủ chống lưu trùng.

## Kiểm tra đã thực hiện

Các ca integration chỉ chạy trên `procurement.test`, có chặn site và db host, dùng dữ liệu nhân tạo và rollback. Không chạy các ca ghi sổ trên production.

- CRUD NCC, retry cùng mã yêu cầu, nội dung khác cùng mã và phiên bản cũ.
- Không giả trạng thái phê duyệt khi tạo đơn; đề nghị mua không nộp trực tiếp để bỏ chuỗi ký.
- Mapping và ghi sổ nhận/hóa đơn từng phần cho Material, Tool, Service và Asset, gồm VAT/vận chuyển; kiểm tra số còn chờ và tổng GL cân đối.
- Người chỉ có Stock User tạo phiếu nhận từ đơn đã duyệt, không tạo đơn mua hoặc đọc sổ kế toán/ngân hàng.
- Nhập thừa Surplus không cần đơn, bắt buộc lý do và đúng tài khoản đối ứng.
- Số tổng hợp báo cáo hợp nhất bằng báo cáo native. Excel danh sách Account vượt trang 100 dòng vẫn đủ số bản ghi.
- Cây tài khoản, ngân hàng NCC và lịch sử theo công ty.
- Mount frontend: danh sách mở editor trong Lotus, native tab/validation, giữ key khi retry, drilldown, bookmark cũ và chống phản hồi muộn điều hướng từ màn đã rời.
- Ba PWA kiểm tra 320×740, 390×844 và 844×390: header/bottom hiện, không tràn ngang. Chạy lại kiểm tra DOM dùng chung.

Ảnh và số đo nằm ngoài repo tại `outputs/erp-workbench-qa-20261025` trong workspace cha. Nhật ký kiểm tra local nằm ở `outputs-erp-*.log` và không đưa vào Git.

## Phần cần làm tiếp để nghiệm thu ngang toàn bộ ERPNext

Bản này là nền giao diện và các luồng mua/kho/kế toán đã nêu, chưa phải bản sao hoàn chỉnh mọi hành vi Desk. Không thực thi tự động client script native. Các Page/công cụ chuyên biệt, custom button và wizard riêng từng DocType (sản xuất, đối chiếu ngân hàng, nghiệp vụ tài sản và nhân sự nâng cao), dashboard native và kiểm thử toàn bộ từng phân hệ chưa được chuyển hết. Không đưa các Page chưa triển khai vào menu như một chức năng đã hoạt động.

Bản phát hành hiện tại gồm nền workbench và các luồng đã nêu trong phạm vi trên. Các chức năng chuyên biệt còn thiếu tiếp tục được theo dõi riêng. Image của PR trước vẫn ở trạng thái `withheld_user_scope_change`; bản này cần image từ commit mới và quy trình triển khai có sao lưu, đồng bộ schema, kiểm tra dữ liệu và phương án quay lại.

## Tiếng Việt

Danh mục hiển thị được xuất từ PO tiếng Việt của Frappe/ERPNext/HRMS đang cài bằng `tools/export_erp_vietnamese.py`, kết hợp thuật ngữ Lotus trong `lotus_farm/erp_vi_overrides.tsv`. Menu, nhãn trường, lựa chọn, trạng thái và phần tổng hợp báo cáo dùng chung danh mục. File Excel dùng nhãn tiếng Việt và tên trang tính tiếng Việt.

Chỉ chuyển ngữ nội dung hiển thị; mã DocType, enum, liên kết và dữ liệu lưu/API giữ nguyên. Các bản dịch nguồn còn thiếu được liệt kê trong audit khi xuất danh mục; bản này chưa dịch hết mọi gợi ý và thuật ngữ của toàn bộ ERPNext/HRMS.

## Dữ liệu và schema

Chỉ thêm DocType nội bộ `Lotus ERP Command` để giữ claim chống gửi trùng. Không thêm sổ kho/kế toán thứ hai; không nhập lại dữ liệu nguồn. Thông tin Supplier/Item và chứng từ hiện có giữ nguyên.

Khi phát hành cần sao lưu database/files/config, đồng bộ DocType mới, kiểm tra schema và giữ image/commit quay lại. So sánh số chứng từ, hash Supplier/Item, GL và Stock Ledger trước/sau. Dùng image từ đúng commit đã kiểm chứng; CI hosted hiện bị chặn bởi billing tài khoản GitHub, không báo CI xanh thay cho kiểm thử local.
