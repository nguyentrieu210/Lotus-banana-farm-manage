// What changed, newest first, written for the people who use the app. Add a new entry on top with each release.
// Ids sort by date; a second update on one day takes a suffix (2026-11-09b).
export const RELEASE_NOTES=[
 {id:'2026-11-11',title:'Cập nhật ngày 11/11/2026: dọn hẳn các màn hình cũ',items:[
  {title:'Bỏ các màn cũ không còn dùng',text:'Các màn ghi chép, kế hoạch, dự thu và nhập liệu đời cũ (thửa, vụ, kế hoạch ngày, lô thu hoạch, nhập OneDrive…), trang Cảnh báo và trang Cấu hình đã được gỡ. Việc ngoài vườn, màu dây, thu hoạch, xưởng, dự thu và báo cáo nằm ở Công việc ngoài vườn; dữ liệu cũ được lưu trữ trước khi xóa.'},
  {title:'Kho',text:'Phiếu xuất dùng còn hai cách: Thủ công và Theo yêu cầu đã duyệt.'},
  {title:'Tài chính',text:'Bỏ chiều "Vụ" trong báo cáo chi phí. Danh sách chờ hạch toán liệt kê ca đóng gói đã đóng mà chưa có phiếu nhập kho đã duyệt; giá thành tháng chờ các phiếu này.'},
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
