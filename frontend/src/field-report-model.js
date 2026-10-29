// Báo cáo ngày (đội): line shapes, the payload sent to lotus_farm.field_report.save and a client-side preview of the
// numbers the server computes (cả lô, đơn giá, thành tiền, chưa đạt ngày công). The server stays the authority.
export const payKinds=[{value:'Daywork',label:'CN – công nhật'},{value:'Piece',label:'CK – công khoán'}]
export const payShort={Daywork:'CN',Piece:'CK'}
export const locations=[{value:'Block',label:'Một lô'},{value:'Blocks',label:'Nhiều lô'},{value:'Zone',label:'Cả khu'}]
export const reportStates={Draft:'Nháp',Confirmed:'Đã xác nhận',Returned:'Trả lại sửa'}
export const sections={Field:'Việc vườn',Bunch:'Chăm sóc buồng'}
export const basisLabels={Area:'theo ha của lô',Trees:'theo số cây của lô',Count:'theo số đếm'}
const SENT=['line_id','work_type','pay_kind','work_team','location','farm_block','blocks','zone','workdays_am','workdays_pm','qty','whole_lot','under_norm_reason','comment','proposal','note']

export function lineId(){
 const random=globalThis.crypto?.randomUUID?.()||Math.random().toString(16).slice(2)+Date.now().toString(16)
 return random.replace(/-/g,'').slice(0,20)
}
export function newLine(section='Field',team=''){
 return {line_id:lineId(),section,work_type:'',pay_kind:'Daywork',work_team:team,location:'Block',farm_block:'',blocks:'',zone:'',
  workdays_am:null,workdays_pm:null,qty:null,whole_lot:0,under_norm_reason:'',comment:'',proposal:'',note:'',materials:[],editable:true}
}
const num=value=>value===''||value==null?null:Number(value)
export function payload(lines){
 return lines.filter(l=>l.editable!==false).map(l=>({...Object.fromEntries(SENT.map(k=>[k,l[k]??null])),
  location:l.pay_kind==='Piece'?'Block':l.location||'Block',workdays_am:num(l.workdays_am),workdays_pm:num(l.workdays_pm),qty:num(l.qty),
  whole_lot:num(l.qty)==null?1:0,materials:(l.materials||[]).filter(m=>m.item_code).map(m=>({item_code:m.item_code,qty:num(m.qty)}))}))
}
// Same rule as field_report_rules.rate_for: the latest price whose period covers the day.
export function rateFor(rates,workType,day){
 let found=null
 for(const r of rates||[]){
  if(r.work_type!==workType||String(r.valid_from)>day||(r.valid_to&&String(r.valid_to)<day))continue
  if(!found||String(r.valid_from)>String(found.valid_from))found=r
 }
 return found
}
export function wholeLot(basis,block){
 if(!block)return null
 if(basis==='Area')return Number(block.area_ha||0)
 if(basis==='Trees')return Number(block.trees||0)
 return null
}
// What the server will store for this line: quantity (cả lô when left empty), price, money and the norm check.
export function preview(line,{rates,blocks,day}){
 const price=rateFor(rates,line.work_type,day)
 const block=(line.pay_kind==='Piece'||(line.location||'Block')==='Block')?blocks?.[line.farm_block]:null
 const whole=wholeLot(price?.basis,block)
 const qty=whole!=null&&(line.whole_lot||num(line.qty)==null)?whole:Number(line.qty||0)
 const rate=line.pay_kind==='Piece'?Number(price?.rate||0):0
 const workdays=Number(line.workdays_am||0)+Number(line.workdays_pm||0)
 const low=!!(workdays&&price?.norm_min&&qty&&qty/workdays<Number(price.norm_min))
 return {price,qty,whole,rate,amount:Math.round(qty*rate),workdays,low,missingPrice:line.pay_kind==='Piece'&&!!line.work_type&&!price}
}
export function totals(lines,ctx){
 let workdays=0,amount=0,low=0
 for(const l of lines){const p=preview(l,ctx);workdays+=p.workdays;amount+=p.amount;if(p.low)low++}
 return {workdays:Math.round(workdays*100)/100,amount,low,lines:lines.length}
}
export const money=v=>Math.round(Number(v||0)).toLocaleString('vi-VN')+' đ'
export const amountText=v=>Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
