// Công việc ngoài vườn: phiếu giao việc theo lô (lotus_farm.field_report). Pure helpers shared by the desktop workspace
// and the /work phone app: labels, which fields a report shows for each work group, the money preview, the split by
// buổi and the payload of a day's report. The server stays the authority on every number.
export const groups={Bunch:'Chăm sóc buồng',Field:'Việc vườn',Protection:'BVTV / phân bón'}
export const payModes={Count:'Khoán số lượng',Lot:'Khoán lô (nghiệm thu)',Daywork:'Công nhật'}
export const payShort={Count:'Khoán SL',Lot:'Khoán lô',Daywork:'Công nhật'}
export const capBases={CutBud:'Số buồng đã cắt bắp cùng màu',LotTrees:'Số cây của lô',LotArea:'Diện tích lô',None:'Không giới hạn'}
export const states={Open:'Đang làm',Assigned:'Đã giao',Working:'Đang làm',Late:'Quá hạn',Reported:'Tổ báo xong',Approved:'Chờ nghiệm thu',
 Passed:'Đạt',Failed:'Không đạt – làm lại',Locked:'Đã khoá, tính tiền',Cancelled:'Đã huỷ',Done:'Xong',Ended:'Hết giao'}
export const stateTone={Assigned:'neutral',Working:'info',Open:'info',Late:'danger',Reported:'warning',Approved:'warning',
 Passed:'success',Failed:'danger',Locked:'success',Cancelled:'muted'}
export const colourStages=['Bag','Care','Prop']

// Which inputs a report on a phiếu shows, by work group and bunch stage.
export function groupSchema(ticket){
 const group=ticket?.work_group||'Field',stage=ticket?.work_stage||''
 return {
  group,
  ribbon:group==='Bunch'&&(stage==='Cut Bud'||colourStages.includes(stage)),
  ribbonChoice:colourStages.includes(stage),
  materials:group==='Protection'||!!ticket?.requires_material,
  materialsRequired:!!ticket?.requires_material,
  done:true,
  qtyLabel:group==='Bunch'?'Số buồng / cây hôm nay':group==='Protection'?'Số cây / ha đã làm hôm nay':'Khối lượng hôm nay',
 }
}

export const unitText=(uom,basis)=>basis==='Area'?'ha':basis==='Trees'?'cây':uom||''
export const money=v=>Math.round(Number(v||0)).toLocaleString('vi-VN')+' đ'
export const amountText=v=>Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:3})

export function wholeLot(ticket){
 if(ticket?.basis==='Area')return Number(ticket.lot_area_ha||0)
 if(ticket?.basis==='Trees')return Number(ticket.lot_trees||0)
 return null
}
// Same rule as field_report_rules.pay_amount: counted work pays what was reported, khoán lô the whole lô once it passes.
export function previewAmount(ticket,qtyTotal){
 if(ticket?.pay_mode==='Count')return Math.round(Number(qtyTotal||0)*Number(ticket.rate||0))
 if(ticket?.pay_mode==='Lot')return Math.round(Number(wholeLot(ticket)||0)*Number(ticket.rate||0))
 return 0
}
// Same rule as field_report_rules.split_by_sessions: by buổi, rounded, the remainder to the person with most buổi.
export function splitBySessions(amount,sessions){
 const entries=Object.entries(sessions).filter(([,n])=>n>0),total=entries.reduce((s,[,n])=>s+n,0)
 const out=Object.fromEntries(Object.keys(sessions).map(e=>[e,0]))
 if(!total||!amount)return out
 for(const [e,n] of entries)out[e]=Math.floor(amount*n/total)
 const rest=Math.round(amount)-Object.values(out).reduce((s,v)=>s+v,0)
 if(rest){const top=entries.slice().sort((a,b)=>b[1]-a[1]||String(b[0]).localeCompare(String(a[0])))[0][0];out[top]+=rest}
 return out
}

// Who can be put on the phiếu today: everyone the clock shows present. By default the present members of the
// phiếu's tổ, each on the buổi they were present for and not yet on another phiếu.
export function peopleRows(present,ticket,entry){
 const chosen=Object.fromEntries((entry?.people||[]).map(p=>[p.employee,p]))
 return (present||[]).map(p=>{
  const takenMorning=p.taken?.Morning&&p.taken.Morning.assignment!==ticket?.name
  const takenAfternoon=p.taken?.Afternoon&&p.taken.Afternoon.assignment!==ticket?.name
  const saved=chosen[p.employee]
  const member=!!ticket?.work_team&&p.team===ticket.work_team
  // A saved report keeps exactly its people; a new one starts with the tổ's present members.
  const pick=(flag,taken,present)=>entry?.people?.length?(saved&&Number(saved[flag])?1:0):(member&&present&&!taken?1:0)
  return {employee:p.employee,employee_name:p.employee_name,team:p.team,member,
   can_morning:!!p.morning&&!takenMorning,can_afternoon:!!p.afternoon&&!takenAfternoon,
   taken_morning:!!takenMorning,taken_afternoon:!!takenAfternoon,
   morning:pick('morning',takenMorning,p.morning),afternoon:pick('afternoon',takenAfternoon,p.afternoon)}
 }).sort((a,b)=>Number(b.member)-Number(a.member)||Number(b.morning+b.afternoon)-Number(a.morning+a.afternoon)||String(a.employee_name).localeCompare(String(b.employee_name)))
}
export const sessionCount=rows=>rows.reduce((n,r)=>n+Number(!!r.morning)+Number(!!r.afternoon),0)

const num=v=>v===''||v==null?null:Number(v)
export function entryPayload(ticket,date,form,people){
 return {assignment:ticket.name,date,qty:num(form.qty),bunch_tag:form.bunch_tag||null,done:form.done?1:0,notes:form.notes||'',
  expected_modified:ticket.entry?.modified||null,
  people:JSON.stringify(people.filter(p=>p.morning||p.afternoon).map(p=>({employee:p.employee,morning:p.morning?1:0,afternoon:p.afternoon?1:0}))),
  materials:JSON.stringify((form.materials||[]).filter(m=>m.item_code).map(m=>({item_code:m.item_code,qty:num(m.qty),dose:m.dose||'',stock_entry:m.stock_entry||null})))}
}

// Bunches of one colour after cắt bắp against what was cut of that colour in the lô (server counts, other reports).
export function ribbonLeft(ticket,tag,{cut={},done={}}={}){
 if(!tag||!ticket?.farm_block)return null
 const c=Number(cut[ticket.farm_block+'|'+tag]||0),d=Number(done[ticket.farm_block+'|'+tag+'|'+ticket.work_stage]||0)
 const mine=Number(ticket.entry?.bunch_tag===tag?ticket.entry.qty||0:0)
 return Math.max(c-d+mine,0)
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
