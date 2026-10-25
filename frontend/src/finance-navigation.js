// Kế toán destinations for the sidebar, page titles and ?tab= routing (same shape as Kho / Mua hàng / Nhân sự).
// Users without ledger access (payment approvers) only see the vouchers waiting for their signature.
export const financeNavigation=[
 {id:'overview',label:'Tổng quan',icon:'chart'},
 {id:'planning',label:'Kế hoạch tài chính',icon:'trending'},
 {id:'pending',label:'Chờ hạch toán',icon:'clock'},
 {id:'journal',label:'Nhật ký kế toán',icon:'document'},
 {id:'sales',label:'Bán hàng – Phải thu',icon:'receive'},
 {id:'payables',label:'Công nợ phải trả',icon:'issue'},
 {id:'cash',label:'Thu / Chi',icon:'wallet'},
 {id:'assets',label:'Tài sản cố định',icon:'package'},
 {id:'reports',label:'Báo cáo',icon:'chart'},
 {id:'settings',label:'Thiết lập',icon:'settings',setup:true},
 {id:'guide',label:'Hướng dẫn',icon:'list',setup:true},
].map(r=>({...r,path:'tai-chinh'}))
const signOnly={id:'sign',label:'Phiếu chi chờ ký',icon:'check',path:'tai-chinh'}
export function visibleFinanceNavigation(session){return session?.capabilities?.finance_ledger?financeNavigation:session?.capabilities?.finance?[signOnly]:[]}
export function normalizeFinanceView(value,session){if(value==='sign'||session&&!session.capabilities?.finance_ledger)return 'sign';return financeNavigation.some(r=>r.id===value)?value:'overview'}
export const financeQuery=id=>({tab:id})
export const financeViewTitle=(value,session)=>(normalizeFinanceView(value,session)==='sign'?signOnly:financeNavigation.find(r=>r.id===normalizeFinanceView(value))).label
