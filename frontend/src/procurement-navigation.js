export const procurementNavigation=[
 {id:'needs',label:'Đề nghị mua',icon:'list'},
 {id:'quotes',label:'Báo giá',icon:'document'},
 {id:'compare',label:'So sánh giá',icon:'chart'},
 {id:'orders',label:'Đơn mua',icon:'cart'},
 {id:'receipts',label:'Nhận / nghiệm thu',icon:'receive'},
 {id:'invoices',label:'Hóa đơn',icon:'document',finance:true,invoice:true},
 {id:'payments',label:'Thanh toán',icon:'wallet',finance:true},
 {id:'payables',label:'Công nợ',icon:'wallet',finance:true},
 {id:'reports',label:'Báo cáo',icon:'chart',finance:true},
 {id:'suppliers',label:'Nhà cung cấp',icon:'people',setup:true},
 {id:'items',label:'Hàng mua',icon:'boxes',setup:true},
].map(r=>({...r,path:'mua-hang'}))
export const normalizeBuyingView=value=>procurementNavigation.some(r=>r.id===value)?value:'orders'
export function visibleBuyingNavigation(session){return procurementNavigation.filter(r=>!r.finance||session.capabilities?.purchasing_finance).filter(r=>!r.invoice||session.capabilities?.purchasing_invoice_read)}
export const buyingQuery=id=>({buying_view:id})
// Kho navigation moved to stock-navigation.js; re-exported for older imports.
export {normalizeStockView,stockNavigation} from './stock-navigation.js'
