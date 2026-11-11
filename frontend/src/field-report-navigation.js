// Công việc ngoài vườn: the whole field area in one sidebar group of 7 entries (spec 002): Hôm nay, Giao việc, Màu dây &
// thu hoạch, Xưởng, Dự thu, Báo cáo and Thiết lập (setup entries, listed under one toggle). Dự thu and Màu dây cắt bắp
// are their own pages; the rest are views of /cong-viec?field_view=. Nghiệm thu and Tiền khoán theo người are reached
// from Giao việc and Báo cáo, not from the menu. Old links (?field_view=day / reports / bunch …) open Hôm nay.
export const fieldNavigation=[
 {id:'today',label:'Hôm nay',icon:'clipboard'},
 {id:'assign',label:'Giao việc',icon:'users'},
 {id:'ribbon',label:'Màu dây & thu hoạch',icon:'flag'},
 {id:'packhouse',label:'Xưởng',icon:'package'},
 {id:'forecast',label:'Dự thu',icon:'trending',path:'forecast',open:true},
 {id:'reports',label:'Báo cáo',icon:'chart'},
 {id:'lots',label:'Đội, tổ & lô',icon:'people',setup:true},
 {id:'catalog',label:'Việc & cách trả',icon:'settings',setup:true},
 {id:'rates',label:'Bảng giá khoán',icon:'document',setup:true},
 {id:'cycles',label:'Vòng chăm sóc',icon:'refresh',setup:true},
 {id:'ribbons',label:'Màu dây cắt bắp',icon:'calendar',path:'mau-day',setup:true,open:true},
 {id:'forecast-params',label:'Tham số dự thu',icon:'sliders',path:'forecast',setup:true,open:true},
 {id:'inspect',label:'Nghiệm thu',icon:'check',hidden:true},
 {id:'payable',label:'Tiền khoán theo người',icon:'wallet',hidden:true},
 // Spec 005: yêu cầu cấp vật tư, reached from Giao việc ("Xem tất cả") and from alerts (?field_view=materials&request=).
 {id:'materials',label:'Yêu cầu cấp vật tư',icon:'package',hidden:true},
].map(r=>({path:'cong-viec',...r}))
const views=new Set(fieldNavigation.filter(r=>r.path==='cong-viec').map(r=>r.id))
export function normalizeFieldView(value){return views.has(value)?value:'today'}
export const fieldQuery=id=>id==='forecast-params'?{tab:'profiles'}:fieldNavigation.find(r=>r.id===id)?.path==='cong-viec'?{field_view:id}:{}
export const fieldViewTitle=value=>fieldNavigation.find(r=>r.id===normalizeFieldView(value)).label
// The menu: the views need the field-report capability; Dự thu and Màu dây cắt bắp stay for anyone allowed those pages,
// and Xưởng for packhouse supervisors and the accountant who receives shifts (they are not in the field teams).
export function visibleFieldNavigation(session){
 const field=!!session?.capabilities?.field_report,packhouse=!!session?.capabilities?.packhouse
 return fieldNavigation.filter(r=>!r.hidden&&(field||r.open||(packhouse&&r.id==='packhouse')))
}
