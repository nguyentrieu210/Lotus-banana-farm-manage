// Pure helpers for the ERP screens: DocType metadata (lotus_farm.erp_workbench.schema) → layout, controls and display.
// No network, no Vue: unit-tested in tests/erp-meta.test.js.
import {systemLabel} from './system-translations.js'
import {formatDate,formatDateTime} from './format.js'
import {catalogName} from './hr-catalog-labels.js'

// Desk-only widgets the Lotus form does not render (buttons run client scripts, HTML is server markup).
const SKIP=new Set(['HTML','Button','Image','Heading','Fold','Signature','Geolocation','HTML Editor','Barcode','Password','Icon','Autocomplete'])
const DATA_TYPES=new Set(['Data','Link','Dynamic Link','Select','Date','Datetime','Time','Int','Float','Currency','Percent','Check','Small Text','Text','Long Text','Text Editor','Read Only','Phone','Duration','Rating','Color','Code','JSON','Markdown Editor','Attach','Attach Image'])

// Vietnamese for every label the ERPNext/HRMS screens show: the shared catalogue (system-translations.js) plus the few
// HRMS/ERPNext labels it does not have yet. Stored values and API names stay unchanged.
const OVERRIDES={'Age as on':'Tính tuổi đến ngày','Consolidate Leave Types':'Gộp các loại nghỉ','Disable Opening Balance Calculation':'Không tính số dư đầu kỳ',
 'Employee Status':'Trạng thái nhân viên','Exit Interview Pending':'Chờ phỏng vấn nghỉ việc','Exit Questionnaire Pending':'Chờ phiếu khảo sát nghỉ việc',
 'FnF Pending':'Chờ quyết toán nghỉ việc','Include Revaluation Journals':'Gồm bút toán đánh giá lại','Interview Status':'Trạng thái phỏng vấn','Owner':'Người tạo',
 'Show Alternate UOM Balance':'Hiện tồn theo đơn vị quy đổi','Show Employer Contributions':'Hiện phần doanh nghiệp đóng',
 // ERPNext's own Vietnamese wording that reads wrong in accounting terms
 'Ngày đăng':'Ngày hạch toán','Thời gian đăng':'Giờ hạch toán','Mục':'Hàng hóa','Bút toán Kế toán':'Dòng hạch toán',
 'Là Trả lại (Bút toán ghi có)':'Hóa đơn trả hàng (ghi giảm)','Là Mục Điều chỉnh Tỷ giá (Bút toán ghi nợ)':'Hóa đơn điều chỉnh giá (ghi tăng)'}
export const tr=value=>typeof value==='string'&&value?(OVERRIDES[value]??systemLabel(value)):value
// A section/tab "label" that is only a technical fieldname (section_break_30) is no title at all.
export const sectionTitle=value=>!value||/^[a-z0-9_]+$/.test(value)?'':tr(value)

// Fields a farm company does not use (POS, inter-company, loyalty, commissions, print setup, barcode scanning…): not shown.
// Desk still has them; values ERPNext fills by default are kept on save.
const SME_HIDDEN=new Set(['is_pos','pos_profile','is_consolidated','consolidated_invoice','scan_barcode','letter_head','select_print_heading','language','group_same_items',
 'amended_from','represents_company','inter_company_invoice_reference','inter_company_order_reference','inter_company_reference','is_internal_customer','is_internal_supplier',
 'loyalty_program','redeem_loyalty_points','loyalty_points','loyalty_amount','loyalty_redemption_account','loyalty_redemption_cost_center','sales_partner','commission_rate',
 'total_commission','auto_repeat','subscription','campaign','source','utm_source','utm_medium','utm_campaign','utm_content','set_posting_time','posting_time','is_old_subcontracting_flow',
 // child tables ERPNext fills itself or a farm does not use: pricing rules applied, per-item tax detail, bundles, project timesheets,
 // POS payments, sales team commissions, tax withheld at source
 'pricing_rules','item_wise_tax_details','packed_items','timesheets','payments','sales_team','tax_withholding_entries','apply_tds','tax_withholding_category'])
const empty=v=>v==null||v===''||(Array.isArray(v)&&!v.length)
// Shown in the Lotus form? Desk-only and SME-irrelevant fields, a numbering series already filled by default, and read-only
// fields with nothing in them (Được sửa đổi từ —, Mã số thuế công ty —) stay out of the way.
export function lotusShown(f,doc,isReadonly){
 if(SME_HIDDEN.has(f.fieldname))return false
 if(f.fieldname==='naming_series'&&!empty((doc||{}).naming_series))return false
 if(isReadonly&&!['Table','Table MultiSelect'].includes(f.fieldtype)&&empty((doc||{})[f.fieldname]))return false
 return true
}

// Small helpers ERPNext metadata expressions use (eval:in_list([...], doc.x), cint(doc.y)…).
const frappeStub={session:{user:''},user:{has_role:()=>false},boot:{sysdefaults:{}},defaults:{get_default:()=>'',get_user_default:()=>''},
 datetime:{get_today:()=>new Date().toISOString().slice(0,10),nowdate:()=>new Date().toISOString().slice(0,10)},meta:{get_docfield:()=>({})},
 utils:{is_empty:v=>v==null||v===''||(Array.isArray(v)&&!v.length)}}
const cache=new Map()
// depends_on / mandatory_depends_on / read_only_depends_on: "eval:<expression>" or a plain fieldname (truthy).
// The expressions come from DocType metadata on the server (as on Desk). Anything that fails to evaluate counts as true,
// so a field is never hidden by a script the Lotus form cannot run.
export function evaluate(expr,doc,parent){
 if(expr==null||expr==='')return true
 const text=String(expr).trim()
 if(!text.startsWith('eval:'))return Boolean((doc||{})[text])
 try{
  let fn=cache.get(text)
  if(!fn){fn=new Function('doc','parent','in_list','cint','flt','frappe','erpnext','"use strict";return ('+text.slice(5)+')');cache.set(text,fn)}
  return Boolean(fn(doc||{},parent||{},(list,v)=>Array.isArray(list)&&list.includes(v),v=>parseInt(v,10)||0,v=>parseFloat(v)||0,frappeStub,{}))
 }catch{return true}
}

// Tabs → sections → columns, like the Desk form. Empty columns/sections/tabs are dropped.
export function layout(fields){
 const tabs=[];let tab=null,section=null,column=null
 const newTab=f=>{tab={label:f?.label||'Thông tin',depends_on:f?.depends_on,sections:[]};tabs.push(tab);section=null;column=null}
 const newSection=f=>{if(!tab)newTab();section={label:f?.label||'',collapsible:!!f?.collapsible,depends_on:f?.depends_on,columns:[]};tab.sections.push(section);column=null}
 const newColumn=()=>{if(!section)newSection();column=[];section.columns.push(column)}
 for(const f of fields){
  if(f.fieldtype==='Tab Break'){newTab(f);continue}
  if(f.fieldtype==='Section Break'){newSection(f);continue}
  if(f.fieldtype==='Column Break'){newColumn();continue}
  if(SKIP.has(f.fieldtype))continue
  if(!column)newColumn()
  column.push(f)
 }
 return tabs.map(t=>({...t,sections:t.sections.map(s=>({...s,columns:s.columns.filter(c=>c.length)})).filter(s=>s.columns.length)})).filter(t=>t.sections.length)
}

export const visible=(f,doc,parent)=>!f.hidden&&evaluate(f.depends_on,doc,parent)
export const required=(f,doc,parent)=>Boolean(f.reqd)||(f.mandatory_depends_on?evaluate(f.mandatory_depends_on,doc,parent):false)
// Submitted documents only accept allow_on_submit fields; read_only_depends_on locks a field by state.
export function readonly(f,doc,{locked=false,parent}={}){
 if(f.read_only||f.fieldtype==='Read Only')return true
 if(locked&&!f.allow_on_submit)return true
 return f.read_only_depends_on?evaluate(f.read_only_depends_on,doc,parent):false
}

// Which shared control renders a field (LotusField types, plus link / table / attach handled by the form).
export function control(f){
 switch(f.fieldtype){
  case 'Check':return 'checkbox'
  case 'Date':return 'date'
  case 'Datetime':return 'datetime'
  case 'Time':return 'time'
  case 'Currency':return 'money'
  case 'Int':case 'Float':case 'Percent':case 'Duration':case 'Rating':return 'number'
  case 'Select':return 'select'
  case 'Link':case 'Dynamic Link':return 'link'
  case 'Small Text':case 'Text':case 'Long Text':case 'Text Editor':case 'Code':case 'JSON':case 'Markdown Editor':return 'textarea'
  case 'Attach':case 'Attach Image':return 'attach'
  case 'Table':case 'Table MultiSelect':return 'table'
  case 'Read Only':return 'readonly'
  default:return 'text'
 }
}

// Select choices in Vietnamese; the stored value stays the ERPNext one.
export function selectOptions(f){
 return String(f.options||'').split('\n').map(v=>v.trim()).filter((v,i,all)=>v&&all.indexOf(v)===i).map(value=>({value,label:tr(value)}))
}

const money=(v,currency='VND')=>Number(v||0).toLocaleString('vi-VN',{style:'currency',currency:currency||'VND',maximumFractionDigits:currency==='VND'?0:2})
const number=v=>Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
// Read-only text of a value (list cells, submitted forms, report cells).
export function display(value,f={},currency){
 if(value==null||value==='')return '—'
 switch(f.fieldtype){
  case 'Date':return formatDate(value)
  case 'Datetime':return formatDateTime(value)
  case 'Check':return Number(value)?'Có':'Không'
  case 'Currency':return money(value,currency)
  case 'Int':case 'Float':case 'Percent':return number(value)+(f.fieldtype==='Percent'?' %':'')
  case 'Select':return tr(String(value))
  // ERPNext default masters (All Supplier Groups, Raw Material…) keep their English record names: show them in Vietnamese.
  default:return typeof value==='string'?(catalogName(value)??tr(value)):String(value)
 }
}
export const docstatusLabel=s=>['Nháp','Đã ghi sổ','Đã hủy'][Number(s)]??''

// Columns of a child table grid: the fields Desk shows in the grid (in_list_view), else the first data fields.
export function childColumns(fields,max=7){
 const data=fields.filter(f=>DATA_TYPES.has(f.fieldtype)&&!f.hidden)
 const listed=data.filter(f=>f.in_list_view)
 return (listed.length?listed:data).slice(0,max)
}
// Link fields whose value names a document of the type held in another field (Dynamic Link).
export const dynamicTarget=(f,doc)=>f.fieldtype==='Dynamic Link'?(doc||{})[f.options]:f.options
