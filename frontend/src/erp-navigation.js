// "Nghiệp vụ ERP" sidebar group: one entry per ERP area the server says this user may open (session.erp_modules,
// built from lotus_farm/erp_catalog.py). Same shape as hr/stock navigation: path + ?erp_view=<id>.
const icons={'ban-hang':'document','mua-hang':'cart','kho':'warehouse','ke-toan':'wallet','tai-san':'package','nhan-su':'people','nghi-phep':'calendar','luong':'wallet'}
export function visibleErpNavigation(session){
 return (session?.erp_modules||[]).map(m=>({id:m.id,label:m.label,icon:icons[m.id]||'list',path:'erp'}))
}
export const normalizeErpView=value=>String(value||'')
export const erpQuery=id=>({erp_view:id})
export function erpViewTitle(value,session){
 const item=(session?.erp_modules||[]).find(m=>m.id===value)
 return item?item.label:'Nghiệp vụ ERP'
}
