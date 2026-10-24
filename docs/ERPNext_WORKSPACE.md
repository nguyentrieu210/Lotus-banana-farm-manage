# ERPNext trong Lotus

Mục ERPNext dùng Sidebar resolver của Frappe 16 đang cài để hiển thị các phân hệ ERPNext và HRMS theo quyền người đăng nhập. Bao gồm Kho, Mua hàng, Bán hàng, Kế toán, Tài sản, Sản xuất, Dự án, CRM và các nghiệp vụ nhân sự. Liên kết mở chứng từ, báo cáo, công cụ hoặc thiết lập native trong tab mới. Chức năng chỉ hiện khi resolver, domain/module profile và quyền DocType/Report cho phép; không cấp thêm quyền.

`/lotus/erpnext?module=Stock` giữ phân hệ trên URL. Công ty, kho, khoảng ngày và tìm kiếm được giữ khi tải lại/quay lại. Tìm kiếm riêng dùng `erp_search`, tránh thay đổi tìm kiếm của màn khác. Danh mục Supplier/Item vẫn dùng chung; bộ lọc công ty được mang sang các chứng từ có trường company và các báo cáo hỗ trợ. Kho được mang sang các trường/filter warehouse phù hợp. Báo cáo khác giữ bộ lọc native của chính nó.

StockDocumentForm và stock-document.js dùng chung cho desktop và PWA: nhập không theo đơn với lý do mua ngoài/thu hồi/thừa kiểm kê, xuất, chuyển, kiểm kê và tồn đầu kỳ. Quy đổi lấy từ Item UOM Conversion Detail. Nhận theo đơn dùng WarehouseReceiving chung cho màn Kho, Nhu cầu vật tư và PWA, tìm tất cả đơn chờ nhận, nhận từng phần bằng đơn vị kho, thêm chi phí, mở lại, in và thao tác chứng từ theo quyền. Lý do nhập và nguồn lô tiếp tục quyết định hạch toán ở backend.

Chứng từ native tiếp tục chạy validation, hook, chuỗi ký và quyền ERPNext/Lotus đang có. Phần này không thay đổi schema, tự nhập lịch sử hay tạo chứng từ trên production.

Kiểm thử: frontend mount các form ở hai chế độ, bốn loại phiếu, link bất đồng bộ, chuyển màn giữ bộ nhớ; integration trên site procurement.test kiểm tra quyền Stock User, tài khoản web, module bị chặn, phạm vi công ty/kho/ngày. Kiểm thử lý do nhập thực sự ghi sổ native và kiểm tra tài khoản/lô, trong database thử riêng.
