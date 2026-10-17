// Shared purchase rules and save/attachment workflow for /warehouse and /buying.
export const PURCHASE_MODES=['Kho tự mua','Chủ đầu tư chỉ định']
export const MAX_QUOTE_BYTES=10*1024*1024
export const newPurchaseLine=()=>({id:Math.random().toString(36).slice(2),item:'',qty:1,uom:'',rate:'',warehouse:'',material_request:'',material_request_item:''})
export const newPurchaseDraft=(warehouse='',today='')=>({name:'',modified:'',supplier:'',mode:PURCHASE_MODES[0],warehouse,expected_date:today,notes:'',items:[newPurchaseLine()]})
export function purchaseUnits(code,items=[],conversions=[]){return [...new Set([items.find(i=>i.name===code)?.stock_uom,...conversions.filter(c=>c.parent===code).map(c=>c.uom)].filter(Boolean))]}
export function purchaseTotal(draft){return (draft?.items||[]).reduce((total,r)=>total+Number(r.qty||0)*Number(r.rate||0),0)}
export function purchaseFromRequest(draft,request){
 if(!request)return {...draft,items:[newPurchaseLine()]}
 return {...draft,warehouse:request.items[0]?.warehouse||draft.warehouse,expected_date:request.expected_date||draft.expected_date,
  items:request.items.map(r=>({...newPurchaseLine(),item:r.item,uom:r.uom,qty:r.qty,warehouse:r.warehouse,material_request:r.material_request,material_request_item:r.material_request_item}))}
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
  return {item:r.item,qty,rate,uom,warehouse:r.warehouse||draft.warehouse,expected_date:draft.expected_date,
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
