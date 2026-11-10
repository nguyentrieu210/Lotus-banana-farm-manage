// Báo cáo ngày của tổ (lotus_farm.lot_report): pure helpers for the lô cards and the entry dialog of one lô. Which inputs a
// việc needs, the lines sent back to the server, the colours a line may take, who works by default, and the draft kept on
// the phone while the network is gone. The server stays the authority on every rule and number.
export const stageLabels={'Sucker Select':'Chọn chồi','Bud Injection':'Chích bắp','Cut Bud':'Cắt bắp','Bag':'Bao buồng','Care':'Tỉa',
 'Prop':'Chống đổ','Reject':'Hủy buồng','Harvest':'Thu hoạch'}
export const groupLabels={Bunch:'Chăm sóc buồng',Field:'Việc vườn',Protection:'Phun bón, sâu bệnh'}
export const stateLabels={Draft:'Chưa gửi',Sent:'Đã gửi, chờ xác nhận',Confirmed:'Đã xác nhận',Reopened:'Mở lại để sửa',Voided:'Đã hủy'}
export const stateTone={Draft:'neutral',Reopened:'warning',Sent:'info',Confirmed:'success'}
export const severities=['Nhẹ','Vừa','Nặng']
export const BEFORE_CUT='Before Cut',AFTER_CUT='After Cut'
export const rejectStages=[{value:BEFORE_CUT,label:'Trước cắt bắp'},{value:AFTER_CUT,label:'Sau cắt bắp'}]

// What a việc asks for. kind: disease | sucker | bunch | field.
export function workSchema(work){
 const stage=work?.stage||''
 const kind=work?.records_disease?'disease':stage==='Sucker Select'?'sucker':stage?'bunch':'field'
 return {kind,stage,
  qtyLabel:kind==='disease'?'Số cây bị':kind==='bunch'?'Số buồng':'Khối lượng'+(work?.uom?' ('+work.uom+')':''),
  autoColour:stage==='Cut Bud',
  pickColour:['Bag','Harvest'].includes(stage),
  rejectColour:stage==='Reject',
  kg:stage==='Harvest',
  reason:stage==='Reject',
  materials:kind!=='disease'&&(!!work?.requires_material||work?.group==='Protection'),
  materialsRequired:!!work?.requires_material,
  done:kind==='field'||kind==='sucker',
  whole:kind==='bunch'||kind==='disease'}
}

let seq=0
export const lineKey=()=>'l'+(++seq)+'-'+Math.random().toString(36).slice(2,7)

export function blankLine(work){
 return {key:lineKey(),work_type:work?.name||'',qty:null,area_ha:null,bunch_tag:'',reject_stage:'',reason:'',weight_kg:null,
  disease:'',severity:'',done:false,notes:'',materials:[],people:{}}
}

// Server lines of one lô → the editable lines (Draft) and the ones shown read-only (sent, confirmed).
export function linesFromLot(lot){
 const editable=[],locked=[]
 for(const l of lot?.lines||[]){
  if(l.state==='Draft')editable.push({key:l.name,name:l.name,work_type:l.work_type,qty:l.stage==='Sucker Select'?null:l.qty,area_ha:l.area_ha||null,
   bunch_tag:l.bunch_tag||'',reject_stage:l.reject_stage||'',reason:l.reason||'',weight_kg:l.weight_kg||null,disease:l.disease||'',
   severity:l.severity||'',done:!!l.done,notes:l.notes||'',machine_read:!!l.machine_read,review_flags:l.review_flags||'',
   materials:(l.materials||[]).map(m=>({item_code:m.item_code,qty:m.qty,dose:m.dose||'',stock_entry:m.stock_entry||''})),
   people:Object.fromEntries((l.people||[]).map(p=>[p.employee,{morning:p.morning?1:0,afternoon:p.afternoon?1:0}]))})
  else locked.push(l)
 }
 return {editable,locked}
}

const num=v=>v===''||v==null?null:Number(String(v).replace(',','.'))
export function payloadLines(lines){
 return lines.filter(l=>l.work_type).map(l=>({work_type:l.work_type,qty:num(l.qty),area_ha:num(l.area_ha),bunch_tag:l.bunch_tag||null,
  reject_stage:l.reject_stage||null,reason:l.reason||null,weight_kg:num(l.weight_kg),disease:l.disease||null,severity:l.severity||null,
  done:l.done?1:0,notes:l.notes||'',machine_read:l.machine_read?1:0,
  materials:(l.materials||[]).filter(m=>m.item_code).map(m=>({item_code:m.item_code,qty:num(m.qty),dose:m.dose||'',stock_entry:m.stock_entry||null})),
  people:Object.entries(l.people||{}).filter(([,f])=>f.morning||f.afternoon).map(([employee,f])=>({employee,morning:f.morning?1:0,afternoon:f.afternoon?1:0}))}))
}
export const fingerprint=lines=>JSON.stringify(payloadLines(lines))

// Who works on a new line: the tổ's members the clock shows present, on the buổi they were present.
export function defaultPeople(present){
 return Object.fromEntries((present||[]).filter(p=>p.own).map(p=>[p.employee,{morning:p.morning?1:0,afternoon:p.afternoon?1:0}]))
}
export const peopleCount=people=>Object.values(people||{}).reduce((n,f)=>n+Number(!!f.morning)+Number(!!f.afternoon),0)

// What is left of each colour on this lô before the lines of the dialog: the server's count (lines already sent and other
// tổ included) plus this lô's own drafts, which saving replaces. left: on the plants; bag: not bagged yet.
const takesLeft=(stage,rejectStage)=>stage==='Harvest'||(stage==='Reject'&&rejectStage===AFTER_CUT)
export function colourRoom(lot){
 const room={}
 for(const c of lot?.colours||[])room[c.tag]={left:Number(c.left)||0,bag:Number(c.bag_left)||0}
 for(const l of lot?.lines||[]){
  const slot=l.state==='Draft'&&room[l.bunch_tag]
  if(!slot)continue
  if(l.stage==='Bag')slot.bag+=Number(l.qty)||0
  else if(takesLeft(l.stage,l.reject_stage))slot.left+=Number(l.qty)||0
 }
 return room
}

// Colours a line may take on this lô: bao buồng those with bunches still unbagged, thu hoạch and hủy sau cắt those with
// bunches still on the plants. A line already on a colour keeps it.
export function colourChoices(lot,stage,current,room=colourRoom(lot)){
 const field=stage==='Bag'?'bag':'left'
 const rows=(lot?.colours||[]).filter(c=>c.tag===current||(room[c.tag]?.[field]||0)>0)
 return rows.map(c=>({value:c.tag,label:c.label+' · tuần '+c.week+' · còn '+(room[c.tag]?.[field]||0)}))
}

// The chosen colour of a bao, thu or hủy sau cắt line against what is left of it, all lines of the dialog on that colour
// taken off: the count left as a hint, or an error once they take more than there is. stageOf(line) -> stage of its việc.
export function colourCheck(room,lines,stageOf,line){
 const stage=stageOf(line),tag=line.bunch_tag,slot=room[tag],bag=stage==='Bag'
 if(!tag||!slot||(!bag&&!takesLeft(stage,line.reject_stage)))return {hint:'',error:''}
 const base=bag?slot.bag:slot.left,word=bag?'chưa bao':'trên cây'
 const used=lines.filter(l=>l.bunch_tag===tag&&(bag?stageOf(l)==='Bag':takesLeft(stageOf(l),l.reject_stage))).reduce((n,l)=>n+(Number(l.qty)||0),0)
 if(used>base)return {hint:'',error:'Vượt '+(used-base)+' buồng: màu này chỉ còn '+base+' buồng '+word+'.'}
 return {hint:'Còn '+base+' buồng '+word+(used?', lưu xong còn '+(base-used):''),error:''}
}

// What the card of a lô says: how many việc today and where the report stands.
export function lotSummary(lot){
 const lines=lot?.lines||[]
 const states=new Set(lines.map(l=>l.state))
 const state=!lines.length?'':states.has('Draft')?'Draft':states.has('Sent')?'Sent':'Confirmed'
 return {count:lines.length,state,
  works:[...new Set(lines.map(l=>l.stage?stageLabels[l.stage]:''))].filter(Boolean),
  due:(lot?.assignments||[]).filter(a=>a.kind==='Round').length,
  held:!!lot?.quarantine_until}
}

// The draft of one lô kept on the phone: written while typing, cleared once the server has it. It is only offered back
// while the report on the server is the one it was typed on (same `modified`); a newer report wins.
const draftKey=(report,block)=>'lotus-lot-draft:'+report+':'+block
export function saveDraft(report,block,lines,modified=''){
 try{localStorage.setItem(draftKey(report,block),JSON.stringify({at:Date.now(),modified,lines}))}catch{/* private window */}
}
export function loadDraft(report,block,modified){
 try{
  const raw=localStorage.getItem(draftKey(report,block)),draft=raw?JSON.parse(raw):null
  return draft&&(modified===undefined||draft.modified===modified)?draft:null
 }catch{return null}
}
export function clearDraft(report,block){
 try{localStorage.removeItem(draftKey(report,block))}catch{/* nothing to clear */}
}

// The ribbon catalogue stores colour codes (DO, CAM, XANH_LA, DO_XANH_LA…), not CSS colours. Two-colour ribbons show half each.
const RIBBON={XANH_DUONG:'#1976d2',XANH_LA:'#2e7d32',TRANG:'#ffffff',CAM:'#f57c00',DEN:'#212121',TIM:'#7b1fa2',DO:'#d32f2f'}
export function swatch(code){
 if(!code)return 'transparent'
 if(/^(#|rgb|hsl)/i.test(code))return code
 let rest=String(code).toUpperCase().replace(/[\s-]+/g,'_')
 const colours=[]
 while(rest){
  const key=Object.keys(RIBBON).find(k=>rest.startsWith(k))
  if(!key)return 'transparent'
  colours.push(RIBBON[key]);rest=rest.slice(key.length).replace(/^_/,'')
 }
 return colours.length>1?`linear-gradient(90deg,${colours[0]} 50%,${colours[1]} 50%)`:colours[0]||'transparent'
}

export const amountText=v=>Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
export const money=v=>Math.round(Number(v||0)).toLocaleString('vi-VN')+' đ'
