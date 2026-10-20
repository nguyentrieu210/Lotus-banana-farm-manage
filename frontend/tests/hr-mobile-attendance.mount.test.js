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
const Attendance=await load('components/hr/HrMobileAttendance.vue')
const m=(over={})=>({checkins:2,status:'Present',working_hours:8,in_time:'2026-10-20 06:05:00',out_time:'2026-10-20 14:40:00',late_entry:0,early_exit:0,needs_review:0,reason:'',late_minutes:0,early_minutes:0,after_minutes:40,suggested_overtime:0.5,clean:true,shift:'Ca 1',...over})
const board={date:'2026-10-20',period_closed:false,counts:{matching:1,review:1,manual:0},synced:{synced:3,needs_review:0},rows:[
 {employee:'E1',employee_name:'An',shift:'Ca 1',status:'',docstatus:0,matches:true,machine:m()},
 {employee:'E2',employee_name:'Bình',shift:'Ca 1',status:'',docstatus:0,matches:false,machine:m({checkins:1,status:'',out_time:null,needs_review:1,reason:'Thiếu lượt chấm',clean:false})},
 {employee:'E3',employee_name:'Chi',shift:'Ca 3',status:'',docstatus:0,matches:false,machine:m({checkins:2,in_time:'2026-10-20 22:10:00',out_time:'2026-10-21 06:02:00',late_entry:1,late_minutes:10,suggested_overtime:0,shift:'Ca 3',clean:true})}]}
const base={'lotus_farm.timekeeping.bootstrap':{can_manage_shifts:true,capabilities:{Attendance:{read:true,create:true,submit:true}}},
 'lotus_farm.timekeeping.catalogue':{shifts:[{name:'Ca 1',start_time:'06:00:00',end_time:'14:00:00'},{name:'Ca 3',start_time:'22:00:00',end_time:'06:00:00'}]},
 'lotus_farm.attendance_day.board':board}
const text=root=>root.textContent.replace(/\s+/g,' ')
const button=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(label))

test('today on the phone: rows by shift with device times, night shift marked, one-tap approval',async()=>{
 calls.length=0
 routes={...base,'lotus_farm.attendance_day.approve_matching':{approved:1,names:['A1']}}
 const view=mount(Attendance,{company:'Lotus',today:'2026-10-20'});await tick();await tick();await tick()
 assert.deepEqual([...view.root.querySelectorAll('.hr-att__group h3')].map(h=>h.childNodes[0].textContent.trim()),['Ca 1','Ca 3'])
 assert.match(text(view.root),/Chi.*22:10 → 06:02 \(\+1\).*Muộn 10′/)
 assert.match(text(view.root),/Máy chấm vừa gửi thêm 3 lượt/)
 ;[...view.root.querySelectorAll('.hr-att__stats button')][1].click();await tick()
 assert.deepEqual([...view.root.querySelectorAll('.hr-att__row strong')].map(s=>s.textContent),['Bình'],'the review filter keeps only rows to check')
 ;[...view.root.querySelectorAll('.hr-att__stats button')][1].click();await tick()
 button(view.root,'Duyệt 1 người khớp máy').click();await tick();await tick()
 assert.ok(calls.some(c=>c.method==='lotus_farm.attendance_day.approve_matching'&&c.args.date==='2026-10-20'))
 view.unmount()
})

test('a shift manager changes one person\'s shift from the sheet',async()=>{
 calls.length=0
 routes={...base,'lotus_farm.shift_admin.set_roster':{applied:[{employee:'E1'}],errors:[],warnings:[]}}
 const view=mount(Attendance,{company:'Lotus',today:'2026-10-20'});await tick();await tick();await tick()
 ;[...view.root.querySelectorAll('.hr-att__row')][0].click();await tick();await tick()
 button(document.body,'Đổi ca').click();await tick()
 const select=document.body.querySelector('.hr-att__sheet select');select.value='Ca 3';select.dispatchEvent(new Event('change'));await tick()
 document.body.querySelector('.hr-att__sheet').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()
 assert.deepEqual(calls.find(c=>c.method==='lotus_farm.shift_admin.set_roster').args.changes,[{employee:'E1',from:'2026-10-20',to:'2026-10-20',shift:'Ca 3'}])
 view.unmount()
})
