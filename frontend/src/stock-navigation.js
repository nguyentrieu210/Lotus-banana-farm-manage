// Kho destinations for the sidebar, page titles and ?stock_view= routing (same shape as procurement/hr navigation).
export const stockNavigation=[
 {id:'stock',label:'Tồn kho',icon:'boxes'},
 {id:'receipts',label:'Nhập kho',icon:'receive',doctypes:['Purchase Receipt','Stock Entry']},
 {id:'issues',label:'Xuất kho',icon:'issue',doctypes:['Stock Entry']},
 {id:'transfers',label:'Chuyển kho',icon:'transfer',doctypes:['Stock Entry']},
 {id:'counts',label:'Kiểm kê',icon:'check',doctypes:['Stock Reconciliation']},
 {id:'movements',label:'Sổ kho',icon:'document'},
 {id:'planning',label:'Nhu cầu vật tư',icon:'list'},
 {id:'report',label:'Báo cáo nhập – xuất – tồn',icon:'chart'},
 {id:'warehouses',label:'Kho',icon:'warehouse',setup:true},
 {id:'items',label:'Vật tư',icon:'package',setup:true},
 {id:'groups',label:'Nhóm vật tư',icon:'clipboard',setup:true},
 {id:'uoms',label:'Đơn vị tính',icon:'ruler',setup:true},
].map(r=>({...r,path:'kho'}))
// Old links: ?stock_view=history (all documents) and setup (danh mục) keep working.
const aliases={history:'receipts',setup:'warehouses'}
export const documentViews={receipts:'receipt',issues:'issue',transfers:'transfer',counts:'count'}
export function normalizeStockView(value){const id=aliases[value]||value;return stockNavigation.some(r=>r.id===id)?id:'stock'}
export const stockQuery=id=>({stock_view:id})
export const stockViewTitle=value=>stockNavigation.find(r=>r.id===normalizeStockView(value)).label
export function visibleStockNavigation(session){return session?.capabilities?.stock===false?[]:stockNavigation}
