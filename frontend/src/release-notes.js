// What changed, newest first, written for the people who use the app. Add a new entry on top with each release.
// Ids sort by date; a second update on one day takes a suffix (2026-11-09b).
export const RELEASE_NOTES=[
 {id:'2026-11-10',title:'Mua hàng và ký điện tử (cập nhật 10/11/2026)',items:[
  {title:'Chờ tôi ký',text:'Một danh sách các chứng từ đang chờ bạn ký, có trên điện thoại và máy tính. Mỗi lần ký đều hỏi lại số chứng từ và số tiền.'},
  {title:'Bản PDF đã ký',text:'Ký đủ thì hệ thống lưu một bản PDF cố định kèm chữ ký và mã QR. Tải lại lúc nào cũng ra đúng bản đó.'},
  {title:'Đề xuất mua',text:'Một tên giai đoạn cho mọi màn: Nháp, Đang ký, Chờ mua, Đang mua, Đã nhận đủ, Đã xong. Đóng phần chưa mua và hủy đề xuất đều ghi lý do.'},
  {title:'Đơn mua',text:'Giám đốc ký mọi đơn. Đơn lập từ đề xuất giữ nhà cung cấp và giá của báo giá đã chọn. Lưu đơn là thấy ngay dòng nào sẽ bị chặn khi duyệt.'},
  {title:'Nhập kho theo đơn',text:'Nhận hàng một bước: số thực nhận, chi phí, ảnh, người giao ký trên màn hình hoặc chụp phiếu giao hàng có chữ ký. Bấm Xác nhận nhập kho là thủ kho ký.'},
  {title:'Trả hàng, hủy phiếu',text:'Trả hàng và hủy phiếu nhập làm ngay trong Lotus, có lý do. Phiếu đã có hóa đơn thì hệ thống nhắc lập hóa đơn điều chỉnh.'},
  {title:'Hóa đơn chờ nhập',text:'Mọi phiếu nhập chưa có hóa đơn, kể cả Mua nhanh, nằm ở một danh sách. Kế toán gõ hóa đơn theo bản in, file gốc hiện ngay cạnh biểu mẫu.'},
  {title:'Công nợ nhà cung cấp',text:'Xem theo ngày chốt: tuổi nợ, khoản đến hạn trong 7 ngày, hàng đã nhận chưa có hóa đơn, sổ chi tiết và biên bản đối chiếu từng nhà cung cấp.'},
  {title:'Phiếu chi',text:'Một phiếu chi trả được nhiều hóa đơn; phần trả thêm ghi rõ là tạm ứng. In được phiếu chi và giấy đề nghị chi.'},
  {title:'Mua nhanh',text:'Hàng mua lẻ không qua đơn gọi thống nhất là Mua nhanh ở Kho, Mua hàng và Tài chính.'},
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
