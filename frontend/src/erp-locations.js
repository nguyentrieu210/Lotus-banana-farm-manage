// Preserve existing Lotus bookmarks while all ERP documents use the shared editor.
const buying={needs:['DocType','Material Request'],quotes:['DocType','Supplier Quotation'],orders:['DocType','Purchase Order'],receipts:['DocType','Purchase Receipt'],invoices:['DocType','Purchase Invoice'],payments:['DocType','Payment Entry'],payables:['Report','Accounts Payable'],reports:['Report','Purchase Register'],suppliers:['DocType','Supplier'],items:['DocType','Item']}
const stock={stock:['Report','Stock Balance'],planning:['Lotus','demand'],history:['DocType','Stock Entry'],movements:['Report','Stock Ledger'],setup:['DocType','Stock Settings']}
export function erpDestination(path,q={},module='Stock'){
 if(q.erp_doctype)return {kind:'DocType',name:q.erp_doctype,document:q.erp_doc||'',isNew:q.erp_new==='1'}
 if(q.erp_report)return {kind:'Report',name:q.erp_report}
 if(q.erp_custom)return {kind:'Lotus',name:q.erp_custom}
 if(q.erp_home==='1')return {kind:'Workspace',name:q.module||module}
 if(q.doctype&&q.doc)return {kind:'DocType',name:q.doctype,document:q.doc}
 let target
 if(path==='/mua-hang')target=buying[q.buying_view||'orders']
 if(path==='/kho')target=stock[q.stock_view||q.tab||'stock']
 if(path==='/tai-chinh'&&q.tab)target=['planning','cash','reports','settings'].includes(q.tab)?['Lotus',q.tab]:({journal:['DocType','Journal Entry'],payables:['Report','Accounts Payable'],sales:['DocType','Sales Invoice'],assets:['DocType','Asset']})[q.tab]
 if(path==='/nhan-su')target=({employees:['DocType','Employee'],candidates:['DocType','Job Applicant'],onboarding:['DocType','Employee Onboarding'],organization:['DocType','Department'],payroll:['Lotus','hr'],devices:['Lotus','hr'],import:['Lotus','hr']})[q.hr_view||'employees']
 if(path==='/cham-cong')target=['Lotus','attendance']
 return target?{kind:target[0],name:target[1],isNew:q.action==='create_order'}:{kind:'Workspace',name:module}
}
export function erpLegacyQuery(path,selection){const source=path==='/mua-hang'?buying:path==='/kho'?stock:null;if(!source)return {};const found=Object.entries(source).find(([,v])=>v[0]===selection.kind&&v[1]===selection.name);return found?{[path==='/kho'?'stock_view':'buying_view']:found[0]}:{}}
