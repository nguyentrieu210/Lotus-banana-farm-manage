// The daily bunch sheet of one tổ: what the screen edits, built from the lines stored for the day, and back.
export const INJECT='Bud Injection',CUT='Cut Bud',REJECT='Reject',HARVEST='Harvest',SUCKER='Sucker Select'
export const BEFORE_CUT='Before Cut',AFTER_CUT='After Cut'
export const eventLabels={[INJECT]:'Chích bắp',[CUT]:'Cắt bắp',[REJECT]:'Hủy buồng',[HARVEST]:'Thu hoạch',[SUCKER]:'Chọn chồi',Bag:'Bao buồng',Care:'Tỉa, vệ sinh buồng',Prop:'Chống đổ'}
export const kindLabels={inject:'Chích bắp',cut:'Cắt bắp',reject:'Hủy buồng',harvest:'Thu hoạch'}
const kinds={[INJECT]:'inject',[CUT]:'cut',[REJECT]:'reject',[HARVEST]:'harvest'}
// The entry dialog of a line; lines that come from a phiếu have none.
export const kindOf=row=>row.source_type==='Manual'?kinds[row.event_type]||null:null
export const stageOptions=[{value:BEFORE_CUT,label:'Trước cắt bắp'},{value:AFTER_CUT,label:'Sau cắt bắp'}]
export const stageLabels=Object.fromEntries(stageOptions.map(o=>[o.value,o.label]))
export const stateLabels={Draft:'Chờ xác nhận',Confirmed:'Đã xác nhận'}

let lineId=0
const nextLine=()=>'line-'+(++lineId)
export const blankReject=()=>({id:nextLine(),block:'',reject_stage:BEFORE_CUT,bunch_tag:'',reason:'',qty:''})
export const blankHarvest=()=>({id:nextLine(),block:'',bunch_tag:'',qty:'',weight_kg:''})
export const blankForm=()=>({inject:{},cut:{},rejects:[],harvests:[],locked:{inject:{},cut:{},lines:[]}})
const filled=v=>v!==''&&v!=null&&Number(v)!==0

export function formFromRows(rows,team){
 const form=blankForm()
 for(const r of rows||[]){
  if(r.work_team!==team||r.source_type!=='Manual')continue
  const confirmed=r.state==='Confirmed'
  if(r.event_type===INJECT||r.event_type===CUT){
   const key=r.event_type===INJECT?'inject':'cut'
   if(confirmed)form.locked[key][r.farm_block]=r.qty
   else form[key][r.farm_block]=r.qty
  }else if(confirmed)form.locked.lines.push(r)
  else if(r.event_type===REJECT)form.rejects.push({id:nextLine(),block:r.farm_block,reject_stage:r.reject_stage,bunch_tag:r.bunch_tag||'',reason:r.reason||'',qty:r.qty})
  else if(r.event_type===HARVEST)form.harvests.push({id:nextLine(),block:r.farm_block,bunch_tag:r.bunch_tag||'',qty:r.qty,weight_kg:r.weight_kg})
 }
 return form
}

// What is sent on save: only lines still open. A line with no number is a line not used.
export function sheetRows(form){
 const rows=[]
 const grid=(values,event_type)=>{for(const [block,qty] of Object.entries(values))if(filled(qty))rows.push({block,event_type,qty})}
 grid(form.inject,INJECT);grid(form.cut,CUT)
 for(const l of form.rejects)if(filled(l.qty))rows.push({block:l.block,event_type:REJECT,qty:l.qty,reject_stage:l.reject_stage,reason:l.reason,bunch_tag:l.reject_stage===AFTER_CUT?l.bunch_tag:null})
 for(const l of form.harvests)if(filled(l.qty))rows.push({block:l.block,event_type:HARVEST,qty:l.qty,bunch_tag:l.bunch_tag,weight_kg:l.weight_kg})
 return rows
}
export const sheetFingerprint=form=>JSON.stringify(sheetRows(form).map(r=>[r.block,r.event_type,Number(r.qty),r.reject_stage||'',r.reason||'',r.bunch_tag||'',Number(r.weight_kg||0)]).sort())

export const sum=values=>Object.values(values).reduce((total,v)=>total+(Number(v)||0),0)
export const lineSum=lines=>lines.reduce((total,l)=>total+(Number(l.qty)||0),0)

// Colours a bunch of this lô can still carry: those cut there and not yet harvested or rejected.
export function colourOptions(sheet,block,current){
 return (sheet?.tags||[]).map(t=>({t,left:(sheet.cut_left||{})[block+'|'+t.name]||0})).filter(x=>x.left>0||x.t.name===current)
  .map(({t,left})=>({value:t.name,label:t.label+' · tuần '+t.week+' · còn '+left}))
}

export function groupByZone(blocks){
 const zones=new Map()
 for(const b of blocks||[]){if(!zones.has(b.zone))zones.set(b.zone,[]);zones.get(b.zone).push(b)}
 return [...zones].map(([zone,items])=>({zone,items}))
}

export function confirmable(sheet,user){
 const rows=(sheet?.rows||[]).filter(r=>r.state==='Draft'&&r.entered_by!==user).length
 return rows+(sheet?.suckers||[]).filter(e=>e.entered_by!==user).length
}
