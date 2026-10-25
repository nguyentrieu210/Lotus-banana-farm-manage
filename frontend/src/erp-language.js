import messages from './erp-vi-messages.js'

// Translate presentation strings only. Callers retain the raw record/enum in
// v-model, API payloads, filters, document links and idempotency fingerprints.
export function erpText(value){
 if(value==null)return ''
 const text=String(value),key=text.trim()
 if(Object.hasOwn(messages,key))return messages[key]
 if(/^['"].*['"]$/.test(key)){const inner=key.slice(1,-1);if(Object.hasOwn(messages,inner))return messages[inner]}
 return text
}
const systemLinks=new Set(['DocType','Country','Gender','UOM','Stock Entry Type','Warehouse Type','Role'])
export function erpLinkLabel(value,doctype){
 if(systemLinks.has(doctype))return erpText(value)
 if(doctype==='Warehouse'&&typeof value==='string'){
  const match=value.match(/^(Goods In Transit|Finished Goods|Work In Progress|Stores)( - .+)$/)
  if(match)return erpText(match[1])+match[2]
 }
 return value
}
export function erpOption(option){return typeof option==='object'?{...option,label:erpText(option.label??option.value)}:{value:option,label:erpText(option)}}
export function erpValue(value,field={}){
 if(Array.isArray(value))return value.map(v=>erpValue(v,field)).join(', ')
 if(['Select','Autocomplete'].includes(field.fieldtype)||['status','workflow_state','purpose','stock_entry_type','party_type','supplier_type','payment_type','material_request_type','lotus_purchase_kind'].includes(field.fieldname))return erpText(value)
 if(field.fieldtype==='Link')return erpLinkLabel(value,field.options)
 return value
}
