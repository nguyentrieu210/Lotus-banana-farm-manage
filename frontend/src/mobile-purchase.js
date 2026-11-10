// Shared purchase rules and save/attachment workflow for /warehouse and /buying.
export const PURCHASE_MODES=['Kho tự mua','Chủ đầu tư chỉ định']
export const MAX_QUOTE_BYTES=10*1024*1024
export const newPurchaseLine=()=>({id:Math.random().toString(36).slice(2),item:'',qty:1,uom:'',rate:'',warehouse:'',material_request:'',material_request_item:'',kind:'',vat_code:'KCT',freight:0})
export const newPurchaseDraft=(warehouse='',today='')=>({name:'',modified:'',supplier:'',mode:PURCHASE_MODES[0],warehouse,expected_date:today,notes:'',items:[newPurchaseLine()]})
export function purchaseUnits(code,items=[],conversions=[]){return [...new Set([items.find(i=>i.name===code)?.stock_uom,...conversions.filter(c=>c.parent===code).map(c=>c.uom)].filter(Boolean))]}
export function purchaseTotal(draft){return (draft?.items||[]).reduce((total,r)=>total+Number(r.qty||0)*Number(r.rate||0)*(1+(r.vat_code==='KCT'?0:Number(r.vat_code||0))/100)+Number(r.freight||0),0)}
// Lines of an approved proposal for one order (spec 003, FR-032). A line whose quote was chosen brings that supplier,
// price, VAT, freight and quote link; a line without a choice keeps the proposal's estimated price. One order has one
// supplier: lines chosen for another supplier are left out and named in `other_suppliers` so they get their own order.
export function purchaseFromRequest(draft,request){
 if(!request)return {...draft,items:[newPurchaseLine()]}
 const supplier=draft.supplier||request.supplier||request.suppliers?.[0]||''
 const lines=request.items.filter(r=>!r.supplier||!supplier||r.supplier===supplier)
 return {...draft,supplier,other_suppliers:(request.suppliers||[]).filter(s=>s!==supplier),
  warehouse:lines[0]?.warehouse||request.items[0]?.warehouse||draft.warehouse,expected_date:lines.find(r=>r.expected_date)?.expected_date||request.expected_date||draft.expected_date,
  items:lines.map(r=>({...newPurchaseLine(),item:r.item,uom:r.uom,qty:r.qty,rate:r.rate||'',warehouse:r.warehouse,kind:r.kind||'',vat_code:r.vat_code||'KCT',freight:r.freight||0,
   reason:r.reason||'',supplier_quotation:r.supplier_quotation||'',supplier_quotation_item:r.supplier_quotation_item||'',
   material_request:r.material_request,material_request_item:r.material_request_item}))}
}
// A saved draft or returned order back into the form, keeping every line field (quote link, VAT, freight, farm).
export function purchaseDraftFromOrder(order,fallbackWarehouse=''){
 return {name:order.name,modified:order.modified,supplier:order.supplier,mode:PURCHASE_MODES.includes(order.mode)?order.mode:PURCHASE_MODES[0],
  warehouse:order.items?.[0]?.warehouse||fallbackWarehouse,expected_date:order.expected_date,notes:order.notes||'',
  items:(order.items||[]).map(r=>({...newPurchaseLine(),item:r.item,qty:r.qty,rate:r.rate,uom:r.uom,warehouse:r.warehouse,kind:r.kind||'',vat_code:r.vat_code||'KCT',freight:r.freight||0,
   lotus_farm:r.lotus_farm||'',reason:r.reason||'',supplier_quotation:r.supplier_quotation||'',supplier_quotation_item:r.supplier_quotation_item||'',
   material_request:r.material_request||'',material_request_item:r.material_request_item||''}))}
}
export function purchasePayload(draft,{items=[],conversions=[]}={},quote){
 if(!draft?.supplier)throw Error('Chọn nhà cung cấp.')
 if(!draft.warehouse)throw Error('Chọn kho nhận.')
 if(!/^\d{4}-\d{2}-\d{2}$/.test(draft.expected_date||'')||Number.isNaN(Date.parse(draft.expected_date))||new Date(draft.expected_date).toISOString().slice(0,10)!==draft.expected_date)throw Error('Chọn ngày giao dự kiến.')
 if(!PURCHASE_MODES.includes(draft.mode))throw Error('Chọn cách mua hàng hợp lệ.')
 if(quote?.size>MAX_QUOTE_BYTES)throw Error('Báo giá không được quá 10 MB.')
 if(!draft.items?.length)throw Error('Thêm ít nhất một mặt hàng.')
 const lines=draft.items.map((r,index)=>{
  const item=items.find(i=>i.name===r.item),qty=Number(r.qty),rate=Number(r.rate||0),uom=r.uom||item?.stock_uom
  if(!item)throw Error('Chọn tên hàng ở dòng '+(index+1)+'.')
  if(String(r.qty??'').trim()===''||!Number.isFinite(qty)||qty<=0)throw Error('Số lượng ở dòng '+(index+1)+' phải lớn hơn 0.')
  if(!Number.isFinite(rate)||rate<0)throw Error('Đơn giá ở dòng '+(index+1)+' không hợp lệ.')
  if(!purchaseUnits(r.item,items,conversions).includes(uom))throw Error('Chọn đơn vị hợp lệ ở dòng '+(index+1)+'.')
  const freight=Number(r.freight||0)
  if(!Number.isFinite(freight)||freight<0)throw Error('Vận chuyển ở dòng '+(index+1)+' không hợp lệ.')
  return {item:r.item,qty,rate,uom,warehouse:r.warehouse||draft.warehouse,expected_date:draft.expected_date,
   ...(r.kind?{kind:r.kind}:{}),...(r.vat_code&&r.vat_code!=='KCT'?{vat_code:r.vat_code}:{}),...(freight?{freight}:{}),
   ...(r.lotus_farm?{lotus_farm:r.lotus_farm}:{}),
   ...(r.supplier_quotation?{supplier_quotation:r.supplier_quotation,supplier_quotation_item:r.supplier_quotation_item,reason:r.reason}:{}),
   material_request:r.material_request||undefined,material_request_item:r.material_request_item||undefined}
 })
 return {supplier:draft.supplier,mode:draft.mode,warehouse:draft.warehouse,expected_date:draft.expected_date,notes:String(draft.notes||'').slice(0,500),items:lines}
}
export async function savePurchaseDraft({company,draft,catalog,quote,save,upload,onSaved}){
 const data=purchasePayload(draft,catalog,quote)
 const result=await save({company,data,name:draft.name||null,modified:draft.modified||null})
 // Commit the identity before upload. An attachment failure must never repeat insert.
 draft.name=result.name;draft.modified=result.modified
 onSaved?.(result)
 let quoteError=''
 if(quote){try{await upload(quote,'Purchase Order',result.name)}catch(error){quoteError=error?.message||'Chưa tải được báo giá.'}}
 return {...result,quoteError}
}
export async function retryPurchaseQuote({saved,quote,upload}){
 if(!saved?.name||!quote)throw Error('Chưa có đơn đã lưu hoặc tệp báo giá.')
 if(quote.size>MAX_QUOTE_BYTES)throw Error('Báo giá không được quá 10 MB.')
 await upload(quote,'Purchase Order',saved.name)
}
export const purchaseLeaveMessage=quotePending=>quotePending?'Đơn đã lưu nhưng báo giá chưa tải lên. Rời màn hình sẽ mất tệp đang chọn.':'Bạn có thông tin chưa lưu. Rời màn hình sẽ mất phần đang nhập.'
