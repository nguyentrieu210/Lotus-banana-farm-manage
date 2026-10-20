import test from 'node:test'
import assert from 'node:assert/strict'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,mount,tick} from './support/mount.mjs'

const calls=[]
let routes={}
globalThis.fetch=async(url,options={})=>{
 const target=new URL(url,'http://localhost:8080'),method=target.pathname.replace('/api/method/','')
 const args=options.body?JSON.parse(options.body):Object.fromEntries(target.searchParams)
 calls.push({method,args})
 const handler=routes[method]
 if(!handler)return {ok:false,status:404,json:async()=>({exc_type:'DoesNotExistError',message:method})}
 return {ok:true,status:200,json:async()=>({message:typeof handler==='function'?handler(args):handler})}
}
const Roster=await load('components/timekeeping/TkRoster.vue')
const ShiftForm=await load('components/timekeeping/TkShiftForm.vue')
const A='lotus_farm.shift_admin.'
const shifts=[{name:'Ca 1',start_time:'06:00:00',end_time:'14:00:00',lotus_color:'#c43224'},{name:'Ca 2',start_time:'14:00:00',end_time:'22:00:00'},{name:'Ca 3',start_time:'22:00:00',end_time:'06:00:00'}]
const days=['2026-10-12','2026-10-13','2026-10-14'].map(date=>({date,off:false,closed:false}))
const grid=(manage,over={})=>({start:'2026-10-12',can_manage:manage,days,rows:[{employee:'E1',employee_name:'An',department:'',designation:'Tổ trưởng',cells:days.map(d=>({date:d.date,shift:'Ca 1',worked:false}))},
 {employee:'E2',employee_name:'Bình',department:'',designation:'',cells:days.map(d=>({date:d.date,shift:'',worked:false}))}],...over})
const buttons=(root,text)=>[...root.querySelectorAll('button')].filter(b=>b.textContent.trim().startsWith(text))
const cell=(root,label)=>[...root.querySelectorAll('.tk-cell')].find(b=>b.getAttribute('aria-label').startsWith(label))
const text=root=>root.textContent.replace(/\s+/g,' ')

test('managers pick cells and set one change per run; the grid reloads',async()=>{
 calls.length=0
 routes={[A+'roster']:grid(true),[A+'set_roster']:{applied:[{employee:'E2'}],errors:[],warnings:[{employee:'E2',message:'Bình: 1 ngày đã có công theo ca cũ — kiểm tra lại công các ngày đó.'}]}}
 const view=mount(Roster,{company:'Lotus',today:'2026-10-14',shifts});await tick();await tick()
 assert.equal(calls[0].args.start,'2026-10-12','the week starts on Monday')
 for(const d of ['12/10','13/10']){const c=cell(view.root,'Bình '+d);c.dispatchEvent(new Event('pointerdown',{bubbles:true}));window.dispatchEvent(new Event('pointerup'))}
 await tick()
 assert.match(text(view.root),/Đã chọn 2 ô · 1 người/)
 buttons(view.root,'Ca 3').find(b=>b.classList.contains('tk-rosterbar__shift')).click();await tick();await tick()
 assert.deepEqual(calls.find(c=>c.method===A+'set_roster').args.changes,[{employee:'E2',from:'2026-10-12',to:'2026-10-13',shift:'Ca 3'}])
 assert.match(text(view.root),/1 ngày đã có công theo ca cũ/)
 assert.equal(calls.filter(c=>c.method===A+'roster').length,2,'reloaded after saving')
 view.unmount()
})

test('a closed day and readers without the right cannot change cells',async()=>{
 routes={[A+'roster']:grid(false)}
 const view=mount(Roster,{company:'Lotus',today:'2026-10-14',shifts});await tick();await tick()
 assert.ok(cell(view.root,'An 12/10').disabled,'read-only for non managers')
 assert.match(text(view.root),/Chỉ xem\. Quản trị viên hoặc Quản lý nhân sự đổi ca/)
 assert.ok(!buttons(view.root,'Xoay ca theo tuần').length)
 view.unmount()
 routes={[A+'roster']:grid(true,{days:days.map((d,i)=>({...d,closed:i===0}))})}
 const closed=mount(Roster,{company:'Lotus',today:'2026-10-14',shifts});await tick();await tick()
 assert.ok(cell(closed.root,'An 12/10').disabled,'closed month is frozen')
 assert.ok(!cell(closed.root,'An 13/10').disabled)
 closed.unmount()
})

test('editing a shift sends its id and version, and says approved days keep their times',async()=>{
 calls.length=0
 routes={[A+'update_shift']:{name:'Ca 3',open_drafts:0}}
 const shift={name:'Ca 3',modified:'v1',start_time:'22:00:00',end_time:'06:00:00',late_grace:10,early_grace:10,check_in_before:60,check_out_after:120,half_day_hours:4,absent_hours:2,color:'',assigned:12}
 const view=mount(ShiftForm,{modelValue:true,company:'Lotus',shift});await tick();await tick()
 const body=document.body.textContent.replace(/\s+/g,' ')
 assert.match(body,/qua đêm/,'night shift is explained')
 assert.match(body,/Công đã duyệt giữ nguyên giờ ca lúc chấm/)
 document.body.querySelector('.tk-shift-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()
 const sent=calls.find(c=>c.method===A+'update_shift')
 assert.equal(sent.args.name,'Ca 3');assert.equal(sent.args.modified,'v1');assert.equal(sent.args.values.start_time,'22:00')
 view.unmount()
})
