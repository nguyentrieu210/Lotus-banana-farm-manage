// What changed, newest first, written for the people who use the app. Add a new entry on top with each release.
// Ids sort by date; a second update on one day takes a suffix (2026-11-09b).
export const RELEASE_NOTES=[
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
