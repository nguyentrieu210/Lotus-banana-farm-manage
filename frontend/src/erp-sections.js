// ERPNext/HRMS business added into the existing Lotus modules (lotus_farm/erp_catalog.py), permission-filtered by the
// server and delivered with the session bootstrap (session.erp_sections = {stock:[…], buying:[…], finance:[…], hr:[…]}).
// A section is one more sidebar entry of its module, opened with that module's own view parameter as "erp-<id>".
let sections={}
export function setErpSections(value){sections=value&&typeof value==='object'?value:{}}
export const isErpView=value=>typeof value==='string'&&value.startsWith('erp-')
export const erpSections=module=>sections[module]||[]
export function erpSection(module,view){return isErpView(view)?erpSections(module).find(s=>'erp-'+s.id===view)||null:null}
// Sidebar items in the module's own shape (id, label, icon, path, setup); extra keys go on every item.
export function erpNavItems(module,extra={}){return erpSections(module).filter(s=>s.nav!==false).map(s=>({id:'erp-'+s.id,label:s.label,icon:s.icon,setup:!!s.setup,erp:true,...extra}))}
export const erpViewLabel=(module,view)=>erpSection(module,view)?.label
