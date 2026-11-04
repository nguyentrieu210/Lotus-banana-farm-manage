// ERPNext/HRMS business added into the existing Lotus modules (lotus_farm/erp_catalog.py), permission-filtered by the
// server and delivered with the session bootstrap (session.erp_sections = {stock:[…], buying:[…], finance:[…], hr:[…]}).
// A section is one more sidebar entry of its module, opened with that module's own view parameter as "erp-<id>".
let sections={}
export function setErpSections(value){sections=value&&typeof value==='object'?value:{}}
export const isErpView=value=>typeof value==='string'&&value.startsWith('erp-')
export const erpSections=module=>sections[module]||[]
export function erpSection(module,view){return isErpView(view)?erpSections(module).find(s=>'erp-'+s.id===view)||null:null}
// Sidebar items in the module's own shape (id, label, icon, path, setup); extra keys go on every item.
export function erpNavItems(module,extra={}){return erpSections(module).filter(s=>s.nav!==false).map(s=>({id:'erp-'+s.id,label:s.label,icon:s.icon,setup:!!s.setup,after:s.after||null,erp:true,...extra}))}
// The module's sidebar with its added sections in place: each one right after the Lotus entry of the same business
// (Nghỉ phép after Chấm công, Lô & hạn dùng after Kiểm kê…), others before the setup group, setup ones in that group.
export function withErpNav(base,module,extra={}){
 const items=[...base]
 for(const item of erpNavItems(module,extra)){
  if(item.setup){items.push(item);continue}
  let at=item.after?items.findIndex(i=>i.id===item.after):-1
  if(at<0){const setup=items.findIndex(i=>i.setup);items.splice(setup<0?items.length:setup,0,item);continue}
  while(items[at+1]?.erp&&items[at+1].after===item.after)at++
  items.splice(at+1,0,item)
 }
 return items
}
export const erpViewLabel=(module,view)=>erpSection(module,view)?.label
