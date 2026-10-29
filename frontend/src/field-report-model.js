// Báo cáo ngày (đội): line shapes, the payload sent to lotus_farm.field_report.save and a client-side preview of the
// numbers the server computes (đơn giá, thành tiền khi Xong, chưa đạt ngày công, vượt số cắt bắp). The server stays the
// authority. Việc vườn is reported on phiếu giao (giao việc theo lô); chăm buồng on the lots each tổ holds.
export const payKinds=[{value:'Daywork',label:'CN – công nhật'},{value:'Piece',label:'CK – công khoán'}]
export const payShort={Daywork:'CN',Piece:'CK'}
export const locations=[{value:'Block',label:'Một lô'},{value:'Blocks',label:'Nhiều lô'},{value:'Zone',label:'Cả khu'}]
export const reportStates={Draft:'Nháp',Confirmed:'Đã xác nhận',Returned:'Trả lại sửa'}
export const sections={Field:'Việc vườn',Bunch:'Chăm sóc buồng'}
export const basisLabels={Area:'theo ha của lô',Trees:'theo số cây của lô',Count:'theo số đếm'}
export const assignmentStates={Assigned:'Đã giao',Working:'Đang làm',Reported:'Tổ báo xong',Late:'Quá hạn',Done:'Xong',Cancelled:'Đã huỷ',Ended:'Hết giao'}
// Bunch stages after cắt bắp: they carry the ribbon colour and may not exceed the cắt bắp count of that colour.
export const colourStages=['Bag','Care','Prop']
const SENT=['line_id','assignment','work_type','pay_kind','work_team','location','farm_block','blocks','zone','workdays_am','workdays_pm','qty','done','bunch_tag','under_norm_reason','comment','proposal','note']

export function lineId(){
 const random=globalThis.crypto?.randomUUID?.()||Math.random().toString(16).slice(2)+Date.now().toString(16)
 return random.replace(/-/g,'').slice(0,20)
}
export function newLine(section='Field',team=''){
 return {line_id:lineId(),section,assignment:null,work_type:'',pay_kind:'Daywork',work_team:team,location:'Block',farm_block:'',blocks:'',zone:'',
  workdays_am:null,workdays_pm:null,qty:null,done:0,bunch_tag:null,under_norm_reason:'',comment:'',proposal:'',note:'',materials:[],editable:true}
}
// A row ready to fill for a phiếu giao the tổ has not reported today. CK when the việc has a price that day.
export function lineFromAssignment(a,{rates,day}={}){
 return {...newLine('Field',a.work_team),assignment:a.name,work_type:a.work_type,farm_block:a.farm_block,
  pay_kind:rateFor(rates,a.work_type,day)?'Piece':'Daywork',fresh:true}
}
const num=value=>value===''||value==null?null:Number(value)
// A phiếu row with nothing entered is not sent: the tổ did not work on that lô today (clearing a saved one removes it).
export function untouched(l){
 return !!l.assignment&&num(l.workdays_am)==null&&num(l.workdays_pm)==null&&num(l.qty)==null&&!l.done
  &&!(l.materials||[]).some(m=>m.item_code)&&!l.comment&&!l.proposal&&!l.note
}
export function payload(lines){
 return lines.filter(l=>l.editable!==false&&!untouched(l)).map(l=>({...Object.fromEntries(SENT.map(k=>[k,l[k]??null])),
  location:l.pay_kind==='Piece'||l.assignment?'Block':l.location||'Block',workdays_am:num(l.workdays_am),workdays_pm:num(l.workdays_pm),qty:num(l.qty),
  done:l.done?1:0,materials:(l.materials||[]).filter(m=>m.item_code).map(m=>({item_code:m.item_code,qty:num(m.qty)}))}))
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
// What the server will store for this line. On a phiếu giao priced per ha or per tree the money is the whole lot, paid
// on the day it is ticked Xong; counted work is paid as reported (field_report_rules.round_amount).
export function preview(line,{rates,blocks,day}){
 const price=rateFor(rates,line.work_type,day)
 const block=blocks?.[line.farm_block]||null
 const whole=wholeLot(price?.basis,block)
 const qty=Number(line.qty||0)
 const rate=line.pay_kind==='Piece'?Number(price?.rate||0):0
 const byLot=whole!=null&&!!line.assignment
 const amount=line.pay_kind!=='Piece'?0:byLot?(line.done?Math.round(whole*rate):0):Math.round(qty*rate)
 const workdays=Number(line.workdays_am||0)+Number(line.workdays_pm||0)
 const low=!!(workdays&&price?.norm_min&&qty&&qty/workdays<Number(price.norm_min))
 return {price,qty,whole,rate,amount,byLot,workdays,low,missingPrice:line.pay_kind==='Piece'&&!!line.work_type&&!price}
}
export function totals(lines,ctx){
 let workdays=0,amount=0,low=0,done=0
 for(const l of lines){if(untouched(l))continue;const p=preview(l,ctx);workdays+=p.workdays;amount+=p.amount;if(p.low)low++;if(l.done)done++}
 return {workdays:Math.round(workdays*100)/100,amount,low,done,lines:lines.filter(l=>!untouched(l)).length}
}
// Bunches of one colour after cắt bắp against what was cut of that colour in that lô: the other reports (server counts)
// plus the lines of this report. stage: work type → lotus_bunch_stage; ribbon: today's cắt bắp tag name.
export function ribbonCount(line,lines,{stage,ribbon,cut={},done={}}){
 const s=stage(line.work_type)
 if(!colourStages.includes(s)||!line.bunch_tag||!line.farm_block)return null
 const sum=pick=>lines.filter(l=>l.farm_block===line.farm_block&&pick(l)).reduce((n,l)=>n+Number(l.qty||0),0)
 const cutHere=ribbon===line.bunch_tag?sum(l=>stage(l.work_type)==='Cut Bud'):0
 const doneHere=sum(l=>l.bunch_tag===line.bunch_tag&&stage(l.work_type)===s)
 const totalCut=Number(cut[line.farm_block+'|'+line.bunch_tag]||0)+cutHere
 const total=Number(done[line.farm_block+'|'+line.bunch_tag+'|'+s]||0)+doneHere
 return {cut:totalCut,total,over:total>totalCut}
}
// Lô × việc: one row per lô, one key per việc holding the phiếu of that cell (latest first).
export function boardRows(board){
 const rows=(board?.blocks||[]).map(b=>({...b,key:b.name,cells:{}}))
 const by=Object.fromEntries(rows.map(r=>[r.name,r]))
 for(const c of board?.cells||[]){
  const row=by[c.farm_block];if(!row)continue
  ;(row.cells[c.work_type]||=[]).push(c)
 }
 for(const r of rows)for(const list of Object.values(r.cells))list.sort((a,b)=>String(b.assigned_on).localeCompare(String(a.assigned_on)))
 return rows
}
export const money=v=>Math.round(Number(v||0)).toLocaleString('vi-VN')+' đ'
export const amountText=v=>Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
