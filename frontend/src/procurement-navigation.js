// Mua hàng sidebar: one entry per job. Views that belong together (báo giá + so sánh, đơn + nhận hàng, the accounting
// views) share one entry and switch with the tabs at the top of the page; `group` names the entry a view lives under.
export const procurementNavigation=[
 {id:'quick',label:'Mua nhanh',icon:'cart',quick:true},
 {id:'needs',label:'Đề nghị mua',icon:'list'},
 {id:'compare',label:'Báo giá & so sánh',icon:'chart',tab:'So sánh giá'},
 {id:'quotes',label:'Danh sách báo giá',icon:'document',group:'compare'},
 {id:'orders',label:'Đơn mua & nhận hàng',icon:'cart',tab:'Đơn mua'},
 {id:'receipts',label:'Phiếu nhận hàng',icon:'receive',group:'orders'},
 {id:'invoices',label:'Hóa đơn & công nợ',icon:'document',finance:true,invoice:true,tab:'Hóa đơn'},
 {id:'payments',label:'Thanh toán',icon:'wallet',finance:true,group:'invoices'},
 {id:'payables',label:'Công nợ',icon:'wallet',finance:true,group:'invoices'},
 {id:'reports',label:'Báo cáo',icon:'chart',finance:true,group:'invoices'},
 {id:'suppliers',label:'Nhà cung cấp',icon:'people',setup:true},
 {id:'items',label:'Hàng mua',icon:'boxes',setup:true},
].map(r=>({...r,path:'mua-hang'}))
export const normalizeBuyingView=value=>procurementNavigation.some(r=>r.id===value)?value:'orders'
// The sidebar entry a view is shown under (quotes → compare).
export const buyingMenu=value=>{const id=normalizeBuyingView(value);return procurementNavigation.find(r=>r.id===id).group||id}
// The views of one sidebar entry, in order: the tabs at the top of that page.
export const buyingGroupViews=value=>{const menu=buyingMenu(value);return procurementNavigation.filter(r=>r.id===menu||r.group===menu)}
const allowed=(r,session)=>(!r.finance||session.capabilities?.purchasing_finance)&&(!r.invoice||session.capabilities?.purchasing_invoice_read)
export function visibleBuyingNavigation(session){
 // An accounting entry whose first view is hidden (no invoice right) still opens on its first visible view.
 return procurementNavigation.filter(r=>!r.group).flatMap(r=>{
  if(allowed(r,session))return [{...r,menu:r.id}]
  const first=procurementNavigation.find(v=>v.group===r.id&&allowed(v,session))
  return first?[{...first,label:r.label,menu:r.id}]:[]
 })
}
export const buyingQuery=id=>({buying_view:id})
// Kho navigation moved to stock-navigation.js; re-exported for older imports.
export {normalizeStockView,stockNavigation} from './stock-navigation.js'
