export const purchaseKinds=[{value:'Material',label:'Nguyên vật liệu'},{value:'Tool',label:'Công cụ'},{value:'Asset',label:'Tài sản'},{value:'Service',label:'Dịch vụ'}]
export {procurementNavigation} from './procurement-navigation.js'
export const procurementTabs=[['needs','Đề nghị'],['quotes','Báo giá'],['orders','Đơn mua'],['receipts','Nhận / nghiệm thu'],['invoices','Hóa đơn'],['payments','Thanh toán'],['payables','Công nợ'],['reports','Báo cáo'],['suppliers','Nhà cung cấp'],['items','Hàng mua']]
export const purchaseKind=item=>item?.lotus_default_purchase_kind||(item?.is_fixed_asset?'Asset':item?.is_stock_item?'Material':'Service')
export function allowedKinds(item){return purchaseKinds.filter(k=>item?.is_fixed_asset?k.value==='Asset':item?.is_stock_item?['Material','Tool'].includes(k.value):k.value==='Service')}
export const money=value=>value==null?'Chưa có giá':Number(value).toLocaleString('vi-VN',{maximumFractionDigits:0})
export const docUrl=(doctype,name)=>'/app/'+doctype.toLowerCase().replaceAll(' ','-')+'/'+encodeURIComponent(name)
export const newKey=()=>globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+Math.random().toString(36).slice(2)
export function quoteChoices(rows,selections){return rows.filter(r=>selections[r.name]?.selected).map(r=>({quotation:r.quotation,line:r.name,modified:r.modified,qty:selections[r.name].qty||r.qty,reason:selections[r.name].reason||''}))}
// MariaDB snapshot conflicts roll back the whole HTTP request. Reuse its key and payload.
export async function purchaseRequest(call,method,args={},write=false){
 for(let attempt=0;attempt<3;attempt++){
  try{return await call(method,args,write)}catch(error){if(!write||!args.client_key&&!args.client_event_id||!['QueryDeadlockError','QueryTimeoutError'].includes(error.code)||attempt===2)throw error}
 }
}
