import {erpSection,withErpNav,erpViewLabel} from './erp-sections.js'
// Kho destinations for the sidebar, page titles and ?stock_view= routing (same shape as procurement/hr navigation).
export const stockNavigation=[
 {id:'stock',label:'Tồn kho',icon:'boxes'},
 {id:'receipts',label:'Nhập kho',icon:'receive',doctypes:['Purchase Receipt','Stock Entry']},
 {id:'issues',label:'Xuất kho',icon:'issue',doctypes:['Stock Entry']},
 {id:'transfers',label:'Chuyển kho',icon:'transfer',doctypes:['Stock Entry']},
 {id:'counts',label:'Kiểm kê',icon:'check',doctypes:['Stock Reconciliation']},
 {id:'movements',label:'Sổ kho',icon:'document'},
 {id:'planning',label:'Nhu cầu cấp cho công việc',icon:'list'},
 {id:'report',label:'Báo cáo nhập – xuất – tồn',icon:'chart'},
 {id:'warehouses',label:'Kho',icon:'warehouse',setup:true},
 {id:'items',label:'Vật tư',icon:'package',setup:true},
 {id:'groups',label:'Nhóm vật tư',icon:'clipboard',setup:true},
 {id:'uoms',label:'Đơn vị tính',icon:'ruler',setup:true},
].map(r=>({...r,path:'kho'}))
// Old links: ?stock_view=history (all documents) and setup (danh mục) keep working.
const aliases={history:'receipts',setup:'warehouses'}
export const documentViews={receipts:'receipt',issues:'issue',transfers:'transfer',counts:'count'}
export function normalizeStockView(value){const id=aliases[value]||value;return stockNavigation.some(r=>r.id===id)||erpSection('stock',id)?id:'stock'}
export const stockQuery=id=>({stock_view:id})
export const stockViewTitle=value=>{const id=normalizeStockView(value);return erpViewLabel('stock',id)||stockNavigation.find(r=>r.id===id).label}
// ERP sections (Lô & hạn dùng, Phiếu kho khác…) follow the Kho entries; setup ones join the Danh mục kho group.
export function visibleStockNavigation(session){return session?.capabilities?.stock===false?[]:withErpNav(stockNavigation,'stock',{path:'kho'})}
