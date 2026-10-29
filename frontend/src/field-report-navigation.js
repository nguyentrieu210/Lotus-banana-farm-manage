// Báo cáo ngày (Công việc vườn) destinations for the sidebar, page titles and ?field_view= routing (same shape as kho/mua hàng).
export const fieldNavigation=[
 {id:'day',label:'Báo cáo ngày',icon:'clipboard'},
 {id:'reports',label:'Danh sách báo cáo',icon:'list'},
 {id:'bunch',label:'Chăm sóc buồng',icon:'sprout'},
 {id:'payable',label:'Tiền khoán tháng',icon:'wallet'},
 {id:'lots',label:'Đội, tổ & lô',icon:'people',setup:true},
 {id:'rates',label:'Bảng giá khoán',icon:'document',setup:true},
 {id:'catalog',label:'Danh mục công việc',icon:'settings',setup:true},
].map(r=>({...r,path:'cong-viec'}))
export function normalizeFieldView(value){return fieldNavigation.some(r=>r.id===value)?value:'day'}
export const fieldQuery=id=>({field_view:id})
export const fieldViewTitle=value=>fieldNavigation.find(r=>r.id===normalizeFieldView(value)).label
export function visibleFieldNavigation(session){return session?.capabilities?.field_report?fieldNavigation:[]}
