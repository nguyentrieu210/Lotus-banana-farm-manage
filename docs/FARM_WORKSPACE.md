# Workspace Công việc nông trường

Đường dẫn: `/lotus/cong-viec?farm=LOTUS-222`.
Mở từ Trang chủ Lotus, menu Giao việc nhanh, Kho hoặc Nhân sự & chấm công.

## Các phần

- Tổng quan: số lô/thửa, tổ hoạt động, công việc thiếu năng suất và thửa thiếu vụ
  đang Active/Harvesting; chỉ rõ thửa có nhiều vụ đang hoạt động.
- Kế hoạch: phiếu đúng nông trường/ngày, trạng thái Nháp/Đã nộp/Đã hủy, xem chi tiết;
  lập kế hoạch qua Giao việc nhanh hiện có. Không tự tạo phiếu hoặc nộp phiếu.
- Tiến độ: dòng việc đã giao, khối lượng giao/đã làm, tổ, trạng thái; lọc tổ và trạng
  thái, tìm công việc/thửa. Ghi kết quả qua màn công việc hiện có.
- Danh mục & cấu hình: công việc/năng suất, nhóm công đoạn, tổ lao động,
  vụ cây theo thửa, giống cây, danh mục lô/thửa. Có tìm kiếm và biểu mẫu lưu tại chỗ.

## Chuẩn bị giao việc

1. Công việc & năng suất: chọn công việc, nhập số đơn vị thực hiện trong một công.
   Giữ đúng đơn vị. Không nhập năng suất minh họa làm số thực tế.
2. Giống cây: bổ sung giống thực tế nếu chưa có.
3. Vụ cây theo thửa: chọn đúng thửa, thêm vụ; vụ đầu tiên bắt buộc ngày trồng,
   vụ chồi bắt buộc vụ trước cùng thửa. Chọn trạng thái theo thực tế.
4. Tổ lao động: cập nhật danh mục tổ hoặc ngừng sử dụng; không tự bịa số lao động.
5. Giao việc nhanh: backend tiếp tục kiểm tra năng suất, vụ, đợt chồi và các quyền.

Điều kiện sẵn sàng cơ bản trên Tổng quan không thay thế kiểm tra từng dòng giao việc.
Work Type, Work Category, Banana Variety là danh mục dùng chung, UI nêu rõ điều này.

## Quyền và dữ liệu

API đọc `lotus_farm.farm_workspace.load` kiểm tra quyền đọc Farm, lọc từng danh mục
bằng `frappe.get_list`, không bỏ qua quyền hoặc truy vấn ngoài nông trường với
Block/Plot/Team/Cycle/Plan. Danh mục không có quyền đọc trả rỗng.
Form dùng lại `lotus_farm.console.schema/detail/save`: kiểm tra quyền create/write,
CSRF, khóa bản ghi và `base_modified`; chặn ghi đè từ phiên bản cũ. Phiếu đã nộp chỉ
hiển thị trong workspace này. Không bỏ qua validation Crop Cycle hoặc Work Type.

Không tự điền giống, ngày trồng, năng suất, vụ, kế hoạch hoặc kết quả mẫu.
Banana Variety được bổ sung vào danh mục cho phép của console, vẫn dùng quyền
Frappe hiện có. Không mở thêm quyền vai trò hay quyền Farm.

## Xác minh

- Build Vite và bộ kiểm thử frontend, gồm điều hướng offline vào đúng entry riêng.
- Kiểm tra trên site frontend: 64 lô / 210 thửa / 9 tổ / 8 công việc, 8 năng suất
  và 210 vụ hoạt động còn thiếu ban đầu.
- Trong transaction rollback: lưu năng suất giảm số thiếu, lưu giống và vụ cây
  làm giảm số thửa thiếu vụ; bản lưu stale bị chặn, Guest bị từ chối đọc Farm.
- Kiểm tra trình duyệt: Tổng quan, cấu hình năng suất, lọc và tạo vụ theo thửa,
  Kế hoạch/Tiến độ chưa có phiếu thì hiện trạng thái rỗng.

Entry `farm-work.html` được đăng ký trong Vite, router website và service worker.
Không cache API hoặc tài liệu riêng tư. Cần mạng để đọc/lưu cấu hình mới.

## Lập kế hoạch / giao việc bằng modal

Các nút tạo kế hoạch/giao việc trong workspace mở chung modal ngay tại chỗ.
Modal dùng lại AssignApp ở chế độ embedded: không có thanh điều hướng hoặc
trang riêng bên trong. Nhận nông trường/ngày đang chọn; giữ nông trường cố định.
Chọn tổ, lô/thửa, nhiều công việc, khối lượng; xem trước rồi xác nhận như API cũ.
Sau khi tạo thành công, phát sự kiện về workspace để cập nhật ngày và tải lại
kế hoạch/tiến độ. Không đóng/hủy giữa lúc đang gửi hoặc kiểm tra.

Các ô chọn tìm kiếm được đưa vào DOM của dialog để hiện đúng trong modal native.
Biểu mẫu bị khóa khi kiểm tra/gửi, tránh thay đổi đầu vào sau khi xem trước.
Trang chủ Lotus và menu chung trỏ về `/lotus/cong-viec?action=assign`; sau khi
mở modal, bỏ tham số action khỏi URL. Đường dẫn giao việc cũ giữ để tương thích,
nhưng workspace không còn dẫn người dùng ra trang đó.

## Hình thức công và định mức vật tư

Work Type có hai trường Check `allow_piecework` và `allow_daywork`, bật độc lập
và đồng thời được. `payment_basis` là trường chỉ đọc suy ra Piece/Daywork/Both.
Patch dual_work_payment giữ lựa chọn cũ khi nâng cấp, không tự chọn cho dữ liệu trống. Đây là cấu hình hình thức công, không tự tạo bảng lương hoặc đơn giá.

Cấu hình chính gồm Công việc & năng suất, Tổ lao động, Vụ cây. Định mức vật tư
nằm trong modal của từng công việc, có thể tạo cơ sở định mức tại chỗ; danh sách
tổng hợp vẫn có trong Danh mục bổ trợ. Ẩn dòng công ty/nông trường và tiêu đề lặp, ngày kế hoạch và nút
giao việc trên tab cấu hình. Các danh mục khác nằm trong Danh mục bổ trợ.

Định mức vật tư dùng Material Norm Profile / Material Norm Line hiện có:
nông trường, công việc, phiên bản, hiệu lực, Nháp/Đã duyệt; mỗi dòng có vật tư,
đơn vị tồn kho, lượng định mức, cơ sở định mức, khối lượng cơ sở, số lần và hệ
số quy đổi. Cơ sở định mức (Norm Basis) dùng cùng đơn vị công việc. API lựa chọn
lọc vật tư tồn kho đang hoạt động và cơ sở phù hợp công việc, kiểm tra quyền.

Bản đã duyệt chỉ xem; nút Tạo phiên bản mới tạo nháp, giữ dòng vật tư và tăng
phiên bản. Không tự duyệt, sửa hoặc xóa lịch sử đã duyệt. Ngày kết thúc bắt buộc
khi duyệt; backend chặn khoảng hiệu lực chồng lấn và sai đơn vị.

Kiểm tra site trong transaction rollback: lưu cả hai hình thức công, tạo cơ sở,
tạo/duyệt bộ định mức, chặn sửa bản đã duyệt và chặn Guest. Không giữ định mức
hoặc dữ liệu thử nghiệm. Thêm field Work Type cần reload-doc hoặc migrate site
khi triển khai sang site khác.

Đơn vị dùng chung units.js cho công việc, vật tư và kho; tìm không dấu bằng tên
tiếng Việt trên danh sách UOM đã được kiểm tra quyền, ưu tiên đơn vị thường dùng.
Mã UOM gửi về backend giữ nguyên.
