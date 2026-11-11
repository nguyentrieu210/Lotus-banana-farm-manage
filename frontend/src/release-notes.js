// What changed, newest first, written for the people who use the app. Add a new entry on top with each release.
// Ids sort by date; a second update on one day takes a suffix (2026-11-09b).
export const RELEASE_NOTES=[
 {id:'2026-11-10b',title:'Mua hàng và ký điện tử (cập nhật 10/11/2026)',items:[
  {title:'Chờ tôi ký',text:'Một danh sách các chứng từ đang chờ bạn ký, có trên điện thoại và máy tính. Mỗi lần ký đều hỏi lại số chứng từ và số tiền.'},
  {title:'Bản PDF đã ký',text:'Ký đủ thì hệ thống lưu một bản PDF cố định kèm chữ ký và mã QR. Tải lại lúc nào cũng ra đúng bản đó.'},
  {title:'Đề xuất mua',text:'Một tên giai đoạn cho mọi màn: Nháp, Đang ký, Chờ mua, Đang mua, Đã nhận đủ, Đã xong. Đóng phần chưa mua và hủy đề xuất đều ghi lý do.'},
  {title:'Đơn mua',text:'Giám đốc ký mọi đơn. Đơn lập từ đề xuất giữ nhà cung cấp và giá của báo giá đã chọn. Lưu đơn là thấy ngay dòng nào sẽ bị chặn khi duyệt.'},
  {title:'Nhập kho theo đơn',text:'Nhận hàng một bước: số thực nhận, chi phí, ảnh, người giao ký trên màn hình hoặc chụp phiếu giao hàng có chữ ký. Bấm Xác nhận nhập kho là thủ kho ký.'},
  {title:'Trả hàng, hủy phiếu',text:'Trả hàng và hủy phiếu nhập làm ngay trong Lotus, có lý do. Phiếu đã có hóa đơn thì hệ thống nhắc lập hóa đơn điều chỉnh.'},
  {title:'Hóa đơn chờ nhập',text:'Mọi phiếu nhập chưa có hóa đơn, kể cả Mua nhanh, nằm ở một danh sách. Kế toán gõ hóa đơn theo bản in, file gốc hiện ngay cạnh biểu mẫu.'},
  {title:'Hóa đơn khác giá phiếu nhận',text:'Phần chênh giá hoặc thuế của đúng số lượng trên hóa đơn vào giá vốn (kỳ đã khóa sổ thì vào chi phí kỳ này), chi tiết hóa đơn ghi rõ từng khoản điều chỉnh. Hàng đã trả không bị tính lại vào hóa đơn và ra khỏi kho đúng giá vốn. Hóa đơn điều chỉnh đi theo cách hóa đơn gốc đã ghi.'},
  {title:'Phí vận chuyển theo từng dòng',text:'Mỗi mặt hàng mang đúng phí vận chuyển của nó. Phí của dòng dịch vụ tính vào chi phí dịch vụ.'},
  {title:'Thuế 8% hết hạn',text:'Hàng đặt với thuế 8% mà nhận hoặc có hóa đơn sau 31/12/2026 tự chuyển sang 10%.'},
  {title:'Trả hết hàng',text:'Phiếu nhận đã trả hết hàng ghi "Đã trả hết hàng", không cần lập hóa đơn. Hàng trả sau khi đã có hóa đơn hiện riêng ở Công nợ là khoản NCC phải hoàn, chờ hóa đơn điều chỉnh.'},
  {title:'Đơn đã đóng, tháng đã kết chuyển',text:'Hàng đã nhận của đơn đã đóng phần còn lại vẫn nhập được hóa đơn khác giá. Hóa đơn dùng tiền tạm ứng trả từ tháng đã kết chuyển vẫn ghi sổ được.'},
  {title:'Đối chiếu Tài chính',text:'Ô "Hàng về chưa có hóa đơn" và phép đối chiếu tính cả thuế chờ hóa đơn (33881), cùng số với màn Công nợ của Mua hàng.'},
  {title:'Công nợ nhà cung cấp',text:'Xem theo ngày chốt: tuổi nợ, khoản đến hạn trong 7 ngày, hàng đã nhận chưa có hóa đơn, sổ chi tiết và biên bản đối chiếu từng nhà cung cấp.'},
  {title:'Phiếu chi',text:'Một phiếu chi trả được nhiều hóa đơn; phần trả thêm ghi rõ là tạm ứng. Tạm ứng theo đơn chỉ tới phần chưa có hóa đơn, kiểm lại khi giám đốc ký. In được phiếu chi và giấy đề nghị chi.'},
  {title:'Mua nhanh',text:'Hàng mua lẻ không qua đơn gọi thống nhất là Mua nhanh ở Kho, Mua hàng và Tài chính.'},
 ]},
 {id:'2026-11-10',title:'Cập nhật ngày 10/11/2026: báo cáo ngày theo lô',items:[
  {title:'Hôm nay: nhập theo lô',text:'Mỗi lô của tổ là một thẻ. Bấm vào lô để nhập mọi việc của lô trong ngày: việc vườn, phun bón, kiểm tra sâu bệnh, cắt bắp, bao buồng, thu hoạch. Tổ trưởng gửi một lần cho cả ngày, đội trưởng xác nhận.'},
  {title:'Phiếu giấy',text:'In phiếu cho tổ ghi tay, chụp ảnh phiếu để máy điền sẵn. Dòng máy đọc phải được kiểm (mở lô, bấm "Đã kiểm, lưu lô này") rồi mới gửi được.'},
  {title:'Màu dây & thu hoạch',text:'Bảng buồng còn trên cây theo màu dây và lô, danh sách cần thu của tuần, lô đang cách ly thuốc. Thu hoạch không được vượt số buồng còn lại của màu.'},
  {title:'Giao việc theo vòng',text:'Mỗi việc vườn có vòng chăm sóc (ví dụ cắt lá 14 ngày). Hệ thống liệt kê lô đến hạn, quá hạn; đội trưởng chọn nhiều lô rồi giao cho tổ một lần. Quản lý vườn đặt vòng ở Thiết lập › Vòng chăm sóc.'},
  {title:'Xưởng',text:'Ca đóng gói nhận buồng từ dòng thu hoạch theo lô và màu dây; thùng và thành phẩm được chia theo kg cho từng lô; truy vết được về lô và các lần phun. Kế toán lập phiếu nhập kho thành phẩm theo ca.'},
  {title:'Dự thu chốt mỗi tuần',text:'Mỗi thứ Hai có một bản chốt dự thu tự dựng (kể cả tuần không ai mở ứng dụng), để so với số thu thật.'},
  {title:'Báo cáo',text:'Ba màn Sáng nay, Tuần, Tháng dạng thẻ; bấm thẻ để xem chi tiết và xuất Excel. Menu Việc hằng ngày gọn còn 7 mục. Sổ cắt bắp (Excel) xuất ở màn Màu dây & thu hoạch.'},
 ]},
 {id:'2026-11-09',title:'Cập nhật ngày 09/11/2026',items:[
  {title:'Báo cáo công việc',text:'Menu mới gom Báo cáo chăm sóc vườn, Báo cáo chăm sóc buồng, Xưởng đóng gói và BVTV vào một chỗ.'},
  {title:'Báo cáo chăm sóc buồng',text:'Xem theo đúng thứ tự công đoạn, từ Chích bắp đến Thu hoạch. Mỗi biểu đồ có lựa chọn riêng, bấm vào cột để xem chi tiết từng lô.'},
  {title:'Nhập buồng theo ngày',text:'Tab Buồng trên điện thoại để tổ nhập chích bắp, cắt bắp, hủy buồng và thu hoạch theo từng lô.'},
  {title:'Dự thu 13 tuần',text:'Dự thu tính theo từng tuần, từ số cắt bắp, chích bắp, chọn chồi và số cây.'},
  {title:'Chống đổ và Tỉa',text:'Không cần chọn màu dây nữa, số báo không vượt số cây của lô. Bao buồng vẫn chọn màu dây và không vượt số đã cắt.'},
  {title:'Menu gọn hơn',text:'Đã bỏ các màn Kế hoạch sản xuất, Bố trí nhân công, Chốt ngày, Hủy & tổn thất.'},
  {title:'Sửa lỗi',text:'Nút trên thanh đỏ không còn mất biểu tượng khi rê chuột.'},
 ]},
]

export const latestId=(notes=RELEASE_NOTES)=>notes[0]?.id||''

// Someone new only needs the latest update, not the whole history.
export function unseenNotes(notes,seen){
 if(!notes.length)return []
 return seen?notes.filter(note=>note.id>seen):[notes[0]]
}
