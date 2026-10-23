export const budgetFields=[
 ['gross_kg','Thu hoạch (kg)','production'],['sales_kg','Thành phẩm bán (kg)','production'],['price_per_kg','Giá bán chưa VAT (đ/kg)','production'],
 ['materials','Vật tư (đ)','cost'],['labour','Nhân công (đ)','cost'],['services','Dịch vụ (đ)','cost'],
 ['packing_per_kg','Đóng gói (đ/kg)','cost'],['transport_per_kg','Vận chuyển (đ/kg)','cost'],['overhead','Quản lý (đ)','cost'],
 ['depreciation','Khấu hao (đ)','cost'],['interest','Lãi vay (đ)','cost'],['tax','Thuế dự kiến (đ)','cost'],
 ['capex','Đầu tư (đ)','cash'],['funding','Vốn vào / vay mới (đ)','cash'],['debt_payment','Trả gốc vay (đ)','cash'],
 ['other_receipts','Thu công nợ đầu kỳ / thu khác (đ)','cash'],['other_payments','Trả công nợ đầu kỳ / chi khác (đ)','cash'],
]
export const factorFields=[['quantity_percent','Sản lượng (%)'],['price_percent','Giá bán (%)'],['variable_cost_percent','Đóng gói / vận chuyển (%)']]
export const formatMonth=value=>value?value.slice(5,7)+'/'+value.slice(0,4):'—'
export const formatNumber=(value,digits=0)=>value==null?'—':Number(value).toLocaleString('vi-VN',{maximumFractionDigits:digits})
export function planMonths(start,count){
 if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(start)||!Number.isInteger(Number(count))||count<1||count>36)return []
 const [year,month]=start.split('-').map(Number)
 return Array.from({length:Number(count)},(_,i)=>{const index=year*12+month-1+i;return Math.floor(index/12)+'-'+String(index%12+1).padStart(2,'0')})
}
export function resizeRows(values){
 const previous=new Map((values.rows||[]).map(r=>[r.month,r]))
 return planMonths(values.start_month,values.month_count).map(month=>previous.get(month)||{month,...Object.fromEntries(budgetFields.map(([key])=>[key,0]))})
}
export function newPlan(today){
 const values={title:'Kế hoạch tài chính '+today.slice(0,4),farm:'',start_month:today.slice(0,4)+'-01',month_count:12,
  opening_cash:0,collection_delay:0,payment_delay:0,quantity_percent:100,price_percent:100,variable_cost_percent:100,notes:''}
 return {...values,rows:resizeRows(values)}
}
export function compareResults(result){
 const keys=[['gross_kg','Thu hoạch (kg)'],['sales_kg','Thành phẩm bán (kg)'],['revenue','Doanh thu (đ)'],['operating_cost','Chi phí hoạt động (đ)'],
  ['profit','Lợi nhuận kế hoạch sau thuế (đ)'],['closing_cash','Tiền cuối kỳ (đ)'],['funding_gap','Thiếu vốn cao nhất (đ)'],
  ['receivables_after_horizon','Doanh thu còn thu sau kỳ (đ)'],['payables_after_horizon','Chi phí còn trả sau kỳ (đ)']]
 return keys.map(([key,label])=>({key,label,base:result.base.totals[key],scenario:result.scenario.totals[key],difference:result.scenario.totals[key]-result.base.totals[key]}))
}
export function resultCsv(result){
 const keys=['month','gross_kg','sales_kg','revenue','operating_cost','depreciation','interest','tax','profit','opening_cash','cash_in','cash_out','closing_cash','funding_gap']
 const labels=['Tháng','Thu hoạch (kg)','Thành phẩm bán (kg)','Doanh thu (đ)','Chi phí hoạt động (đ)','Khấu hao (đ)','Lãi vay (đ)','Thuế dự kiến (đ)','Lợi nhuận (đ)','Tiền đầu tháng (đ)','Thu (đ)','Chi (đ)','Tiền cuối tháng (đ)','Thiếu vốn (đ)']
 return '\ufeff'+[labels,...result.rows.map(r=>keys.map(k=>k==='month'?formatMonth(r[k]):r[k]))].map(row=>row.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(';')).join('\r\n')
}
