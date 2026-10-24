import {unitLabel} from './units.js'
export function stockLine(kind='receipt'){return {item:'',item_name:'',qty:kind==='count'?0:1,uom:'',area:'',rate:0}}
export function stockDraft(kind,{date='',warehouse='',event=crypto.randomUUID()}={}){
 return {kind,posting_date:date,source:warehouse,target:kind==='transfer'?'':warehouse,receipt_reason:'',supplier:'',count_purpose:'Stock Reconciliation',issue_mode:'Manual',work_plan:'',receiver:'',receiver_employee:'',notes:'',additional_costs:[],existing_name:'',base_modified:'',client_event_id:event,lines:[stockLine(kind)]}
}
export function stockUnits(row,items=[],conversions=[]){
 const item=items.find(i=>i.name===row.item)||{}
 const base=row.stock_uom||item.stock_uom||row.uom
 const values=[base,row.uom,row.pack_uom||item.pack_uom,...(row.uoms||item.uoms||[]).map(c=>c.uom),...conversions.filter(c=>c.parent===row.item).map(c=>c.uom)]
 return [...new Set(values.filter(Boolean))].map(value=>({value,label:unitLabel(value)}))
}
export function selectStockLine(row,option,kind){
 const uom=option.stock_uom||option.uom||''
 return {...row,item:option.value||option.name,item_name:option.label||option.item_name,uom,stock_uom:uom,uoms:option.uoms||[],pack_uom:option.pack_uom||'',pack_factor:Number(option.pack_factor)||0,actual_qty:option.actual_qty,...(kind==='count'?{qty:option.actual_qty??0}:{})}
}
export function validateStockDraft(d){
 if(!d.posting_date)return 'Chọn ngày chứng từ.'
 if(['issue','transfer'].includes(d.kind)&&!d.source)return 'Chọn kho xuất.'
 if(['receipt','transfer','count'].includes(d.kind)&&!d.target)return 'Chọn kho nhận.'
 if(d.kind==='transfer'&&d.source===d.target)return 'Kho nhận phải khác kho xuất.'
 if(!d.lines?.length||d.lines.length>100)return 'Phiếu cần từ 1 đến 100 dòng vật tư.'
 for(const row of d.lines){
  if(!row.item)return 'Chọn vật tư cho từng dòng.'
  const qty=Number(row.qty)
  if(String(row.qty??'').trim()===''||!Number.isFinite(qty)||qty<(d.kind==='count'||d.kind==='issue'&&d.issue_mode!=='Manual'?0:0.000001))return 'Nhập số lượng hợp lệ cho từng dòng.'
  if(d.kind==='issue'&&d.issue_mode!=='Manual'&&qty>Number(row.remaining_qty||0))return 'Số lượng vượt phần nhu cầu còn được cấp.'
  if(d.kind==='receipt'&&!row.uom)return 'Chọn đơn vị nhập hàng.'
  if((d.kind==='receipt'||d.kind==='count'&&d.count_purpose==='Opening Stock')&&(!Number.isFinite(Number(row.rate))||Number(row.rate)<0))return 'Đơn giá phải là số không âm.'
  if((d.kind==='issue'||d.kind==='receipt'&&d.receipt_reason==='Recovery')&&!String(row.area||'').trim())return 'Nhập lô hoặc nơi sử dụng cho từng dòng.'
 }
 if(d.kind==='issue'&&!d.receiver_employee&&!(d.existing_name&&d.receiver))return 'Chọn người nhận vật tư trong danh sách nhân sự HRMS.'
 if(d.kind==='issue'&&d.issue_mode==='Manual'&&!String(d.notes||'').trim())return 'Nhập lý do xuất thủ công.'
 return ''
}
export function stockDraftRequest(company,d){
 const fields=['kind','posting_date','source','target','notes','count_purpose','issue_mode','work_plan','receiver','receiver_employee','additional_costs','existing_name','base_modified','client_event_id']
 const result=Object.fromEntries(fields.map(k=>[k,d[k]]))
 result.company=company
 result.lines=(d.kind==='issue'&&d.issue_mode!=='Manual'?d.lines.filter(r=>Number(r.qty)>0):d.lines).map(r=>({...r,qty:Number(r.qty),rate:Number(r.rate||0)}))
 if(d.kind==='receipt'){result.receipt_reason=d.receipt_reason;result.supplier=d.supplier}
 return result
}
