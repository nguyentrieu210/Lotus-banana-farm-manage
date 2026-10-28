export const purchaseKinds=[{value:'Material',label:'Nguyên vật liệu'},{value:'Tool',label:'Công cụ'},{value:'Asset',label:'Tài sản'},{value:'Service',label:'Dịch vụ'}]
export {procurementNavigation} from './procurement-navigation.js'
export const procurementTabs=[['quick','Mua nhanh'],['needs','Đề nghị'],['quotes','Báo giá'],['compare','So sánh giá'],['orders','Đơn mua'],['receipts','Nhận / nghiệm thu'],['invoices','Hóa đơn'],['payments','Thanh toán'],['payables','Công nợ'],['reports','Báo cáo'],['suppliers','Nhà cung cấp'],['items','Hàng mua']]
export const purchaseKind=item=>item?.lotus_default_purchase_kind||(item?.is_fixed_asset?'Asset':item?.is_stock_item?'Material':'Service')
export function allowedKinds(item){return purchaseKinds.filter(k=>item?.is_fixed_asset?k.value==='Asset':item?.is_stock_item?['Material','Tool'].includes(k.value):k.value==='Service')}
export const money=value=>value==null?'Chưa có giá':Number(value).toLocaleString('vi-VN',{maximumFractionDigits:0})
export const docUrl=(doctype,name)=>'/app/'+doctype.toLowerCase().replaceAll(' ','-')+'/'+encodeURIComponent(name)
export const newKey=()=>globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+Math.random().toString(36).slice(2)
// So sánh giá (lotus_farm.procurement.compare): rows = request lines / items, offers = quote lines with unit_cost per stock unit.
// A supplier's cell shows its cheapest priced line for that row.
export function supplierOffer(row,supplier){return (row.offers||[]).filter(o=>o.supplier===supplier&&o.unit_cost!=null).sort((a,b)=>a.unit_cost-b.unit_cost)[0]||null}
export function cheapestCost(row){const costs=(row.offers||[]).map(o=>o.unit_cost).filter(c=>c!=null);return costs.length?Math.min(...costs):null}
// Same tolerance as procurement_rules.needs_reason on the server.
export function needsReason(row,line){const offer=(row.offers||[]).find(o=>o.line===line),best=cheapestCost(row);if(!offer||offer.unit_cost==null||best==null)return true;return offer.unit_cost>best*(1+1e-9)+0.005}
export function defaultChoices(rows){return Object.fromEntries(rows.filter(r=>r.best_line).map(r=>[r.key,r.best_line]))}
// Selections for select_quotes: never more than the request still needs (stock units), converted back to the quote's unit.
export function compareSelections(rows,choices,reasons={}){
 return rows.filter(r=>choices[r.key]).map(r=>{
  const offer=r.offers.find(o=>o.line===choices[r.key]),factor=offer.qty?offer.stock_qty/offer.qty:1
  const qty=r.need_qty!=null&&offer.stock_qty>r.need_qty?r.need_qty/factor:offer.qty
  return {quotation:offer.quotation,line:offer.line,modified:offer.modified,qty,reason:needsReason(r,offer.line)?String(reasons[r.key]||'').trim():''}
 })
}
export function quoteChoices(rows,selections){return rows.filter(r=>selections[r.name]?.selected).map(r=>({quotation:r.quotation,line:r.name,modified:r.modified,qty:selections[r.name].qty||r.qty,reason:selections[r.name].reason||''}))}
// MariaDB snapshot conflicts roll back the whole HTTP request. Reuse its key and payload.
export async function purchaseRequest(call,method,args={},write=false){
 for(let attempt=0;attempt<3;attempt++){
  try{return await call(method,args,write)}catch(error){if(!write||!args.client_key&&!args.client_event_id||!['QueryDeadlockError','QueryTimeoutError'].includes(error.code)||attempt===2)throw error}
 }
}
