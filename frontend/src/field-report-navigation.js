// Công việc ngoài vườn destinations for the sidebar, page titles and ?field_view= routing (same shape as kho/mua hàng).
// Old links (?field_view=day / reports / bunch) open Hôm nay.
export const fieldNavigation=[
 {id:'today',label:'Hôm nay',icon:'clipboard'},
 {id:'assign',label:'Giao việc theo lô',icon:'users'},
 {id:'inspect',label:'Nghiệm thu',icon:'check'},
 {id:'board',label:'Bảng lô × việc',icon:'map'},
 {id:'payable',label:'Tiền khoán theo người',icon:'wallet'},
 {id:'lots',label:'Đội, tổ & lô',icon:'people',setup:true},
 {id:'rates',label:'Bảng giá khoán',icon:'document',setup:true},
 {id:'catalog',label:'Việc & cách trả',icon:'settings',setup:true},
].map(r=>({...r,path:'cong-viec'}))
export function normalizeFieldView(value){return fieldNavigation.some(r=>r.id===value)?value:'today'}
export const fieldQuery=id=>({field_view:id})
export const fieldViewTitle=value=>fieldNavigation.find(r=>r.id===normalizeFieldView(value)).label
export function visibleFieldNavigation(session){return session?.capabilities?.field_report?fieldNavigation:[]}
