// Yêu cầu cấp vật tư (spec 005): the pure part of the screens. State names and colours, the split of a total over the
// chosen lô (by area, whole units kept whole), the lines sent to lotus_farm.issue_request.save, the "only lower" check of
// the approver, the client_event_id reused for a retry of the same command, and the copy of the form kept on the device.
import {saveDraft,loadDraft,clearDraft} from './form-drafts.js'

// State codes as lotus_farm.issue_request sends them (`state_code`; `state` is the Vietnamese label).
export const STATES=['draft','sent','returned','waiting','picking','partial','done','closed','cancelled']
export const STATE_LABELS={draft:'Nháp',sent:'Chờ duyệt',returned:'Trả lại',waiting:'Chờ cấp',picking:'Kho đang lập phiếu',partial:'Đã cấp một phần',done:'Đã cấp đủ',closed:'Đã đóng',cancelled:'Đã hủy'}
export const STATE_TONES={draft:'neutral',sent:'warning',returned:'danger',waiting:'info',picking:'info',partial:'info',done:'success',closed:'neutral',cancelled:'neutral'}
const LABEL_CODES=Object.fromEntries(Object.entries(STATE_LABELS).map(([code,label])=>[label.toLowerCase(),code]))
LABEL_CODES['đã huỷ']='cancelled'
// A row (state_code, else its label) or a bare code / label.
export function stateKey(value){
 if(value&&typeof value==='object')return stateKey(value.state_code||value.state)
 const raw=String(value||'').trim()
 return STATE_LABELS[raw]?raw:LABEL_CODES[raw.toLowerCase()]||''
}
export const stateLabel=value=>STATE_LABELS[stateKey(value)]||String((value&&typeof value==='object'?value.state:value)||'')
export const stateTone=value=>STATE_TONES[stateKey(value)]||'neutral'
// States after approval that are not finished: the "Quá hạn chưa cấp" label only applies to them.
export const OPEN_AFTER_APPROVAL=['waiting','picking','partial']
export function isOverdue(row,today){
 if(row?.overdue!=null)return !!row.overdue
 const needed=row?.needed||row?.schedule_date
 return !!(today&&needed&&needed<today&&OPEN_AFTER_APPROVAL.includes(stateKey(row)))
}

// Count cards of the list (Giao việc): the server counts (by state code, plus `approve`), else counted from the rows.
export const COUNT_CARDS=[
 {key:'approve',label:'Chờ bạn duyệt'},
 {key:'sent',label:'Chờ duyệt'},
 {key:'returned',label:'Trả lại'},
 {key:'waiting',label:'Chờ cấp'},
 {key:'issuing',label:'Đang cấp'},
 {key:'done',label:'Đã cấp (7 ngày)'},
]
export const toApprove=row=>!!(row?.can_approve??row?.actions?.approve)&&stateKey(row)==='sent'
export function inGroup(row,group){
 const key=stateKey(row)
 if(group==='approve')return toApprove(row)
 if(group==='issuing')return key==='picking'||key==='partial'
 return key===group
}
export function countRequests(rows,counts){
 const out={}
 for(const card of COUNT_CARDS){
  if(counts&&Object.keys(counts).length)out[card.key]=card.key==='issuing'?(Number(counts.picking)||0)+(Number(counts.partial)||0):Number(counts[card.key])||0
  else out[card.key]=(rows||[]).filter(r=>inGroup(r,card.key)).length
 }
 return out
}

// Units sold whole: the split keeps them whole (largest remainder) so the lô still add up to the total.
const WHOLE=new Set(['chai','gói','goi','bao','can','cái','cai','thùng','thung','hộp','hop','cuộn','cuon','bình','binh','lọ','lo','túi','tui','nos','unit','box','bottle','pack','bag','pair','set'])
export const isWholeUnit=(uom,flag)=>flag!=null?!!flag:WHOLE.has(String(uom||'').trim().toLowerCase())
const round3=n=>Math.round(Number(n||0)*1000)/1000

// Split `total` over the lô in proportion to their area. A lô without area takes no share (it is listed in `missing`,
// never guessed); a lô left with 0 after rounding whole units is listed in `dropped`. The shares always add up to the
// total: largest remainder, in whole units or in thousandths.
export function splitByArea(total,blocks,whole=false){
 const amount=Number(total)||0
 const valid=(blocks||[]).filter(b=>Number(b.area)>0),missing=(blocks||[]).filter(b=>!(Number(b.area)>0)).map(b=>b.key)
 const qty={},dropped=[]
 if(!valid.length||amount<=0)return {qty,missing,dropped}
 const scale=whole?1:1000,units=Math.round(amount*scale),area=valid.reduce((s,b)=>s+Number(b.area),0)
 const shares=valid.map((b,i)=>{const exact=units*Number(b.area)/area;return {key:b.key,i,base:Math.floor(exact+1e-9),rest:exact-Math.floor(exact+1e-9)}})
 let left=units-shares.reduce((s,r)=>s+r.base,0)
 for(const r of [...shares].sort((a,b)=>b.rest-a.rest||a.i-b.i)){if(left<=0)break;r.base++;left--}
 for(const r of shares){if(r.base>0)qty[r.key]=r.base/scale;else dropped.push(r.key)}
 return {qty,missing,dropped}
}
export const sumQty=map=>round3(Object.values(map||{}).reduce((s,v)=>s+(Number(v)||0),0))

// The lines of a request: one per vật tư × lô with a quantity, in the order the lô were picked.
export function buildLines(materials,blocks,assignments={}){
 const lines=[]
 for(const m of materials||[])for(const block of blocks||[]){
  const qty=round3(m.qty?.[block])
  if(!m.item_code||!(qty>0))continue
  lines.push({item_code:m.item_code,farm_block:block,qty,notes:String(m.notes||'').trim(),assignment:assignments[block]||null})
 }
 return lines
}
export const MAX_LINES=100
export function linesProblem(lines){
 if(!lines.length)return 'Chọn ít nhất một lô và một vật tư có số lượng lớn hơn 0.'
 if(lines.length>MAX_LINES)return 'Yêu cầu có '+lines.length+' dòng, quá '+MAX_LINES+' dòng. Tách thành hai yêu cầu.'
 return ''
}
// What lotus_farm.issue_request.save receives as `values`.
export function requestValues(form,lines){
 return {team:form.team||'',work_type:form.work_type,needed:form.needed,warehouse:form.warehouse,receiver:form.receiver||'',note:String(form.note||'').trim(),lines}
}
// Rebuild the form materials from saved lines (edit a returned request, or "Lập lại từ yêu cầu này").
export function materialsFromLines(lines){
 const by=new Map()
 for(const l of lines||[]){
  const code=l.item_code||l.item
  if(!by.has(code))by.set(code,{item_code:code,item_name:l.item_name||code,uom:l.stock_uom||l.uom||'',whole:l.whole,mode:'each',each:null,total:null,notes:l.notes||'',qty:{}})
  by.get(code).qty[l.farm_block]=Number(l.qty)||0
 }
 return [...by.values()]
}

// The approver may only lower a quantity or drop a line (0). Returns the changed lines, or the reason it is refused.
export function lowered(old,next){
 const changed=[]
 for(const line of old||[]){
  if(!(line.name in (next||{})))continue
  const raw=next[line.name],value=raw===''||raw==null?NaN:Number(raw)
  if(!Number.isFinite(value)||value<0)return {error:'Số mới của '+(line.item_name||line.item_code)+' · '+(line.block_code||line.farm_block)+' không hợp lệ.',lines:[]}
  if(value>Number(line.qty)+1e-9)return {error:'Chỉ được giảm số hoặc bỏ dòng. Muốn tăng số thì bấm Trả lại để người lập sửa.',lines:[]}
  if(Math.abs(value-Number(line.qty))>1e-9)changed.push({name:line.name,qty:round3(value)})
 }
 return {error:'',lines:changed}
}

// One client_event_id per command: a retry of the same command (same body) after a lost answer reuses the id, so the
// server answers with the first result; a different body gets a new id.
export function newEventId(){return globalThis.crypto?.randomUUID?.()||'ir-'+Date.now()+'-'+Math.random().toString(36).slice(2)}
export function eventFor(previous,body){
 const text=JSON.stringify(body)
 return previous&&previous.text===text?previous:{id:newEventId(),text}
}

// The form being typed is kept on the device until the server has it (lost signal, closed app).
export const draftKey=(farm,crew,name)=>'issue-request:'+(farm||'')+':'+(crew||'')+':'+(name||'new')
export const keepLocal=(key,values)=>saveDraft(key,values)
export const readLocal=key=>loadDraft(key)?.values||null
export const dropLocal=key=>clearDraft(key)

export const qtyText=v=>Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
export const shortDate=value=>{const m=String(value||'').match(/^(\d{4})-(\d{2})-(\d{2})/);return m?m[3]+'/'+m[2]:''}
// Lô codes of a row, whatever form the server sends them in.
export const blockList=row=>Array.isArray(row?.blocks)?row.blocks.map(b=>typeof b==='string'?b:b.block_code||b.code||b.name).join(', '):String(row?.blocks||row?.block_codes||'')
export const crewTeam=row=>[row?.crew_name,row?.team_name||(row?.team?'':'Cả đội')].filter(Boolean).join(' · ')
// detail() sends its lines as `items` (`lines` on a card is their count).
export const detailLines=d=>Array.isArray(d?.items)?d.items:Array.isArray(d?.lines)?d.lines:[]
// stock() answers {item_code: {available, approved_waiting}}; quantities only.
export function stockFor(stock,code){
 const s=Array.isArray(stock)?stock.find(r=>r.item_code===code):stock?.[code]
 return s?{available:Number(s.available)||0,waiting:Number(s.approved_waiting??s.approved_open)||0}:null
}
// A warning is {kind, message} from the server (or plain text).
export const warningText=w=>typeof w==='string'?w:w?.message||''
