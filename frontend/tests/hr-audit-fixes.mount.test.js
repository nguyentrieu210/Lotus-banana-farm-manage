import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick} from './support/mount.mjs'

const calls=[]
const all={read:true,create:true,write:true,submit:true,cancel:true,delete:true}
const machine=shift=>({checkins:2,status:'Present',working_hours:4,in_time:'2026-10-20 07:00:00',out_time:'2026-10-20 11:00:00',shift,clean:true,needs_review:0,suggested_overtime:0})
const fixtures=()=>({
 'lotus_farm.timekeeping.bootstrap':{user:'synthetic-hr',today:'2026-10-20',csrf_token:'test',companies:[{name:'SYNTHETIC',default_currency:'VND'}],capabilities:{Employee:all,Attendance:all,'Lotus Crew Attendance':all}},
 'lotus_farm.timekeeping.catalogue':{farms:[],teams:[],works:[],shifts:[{name:'A',start_time:'07:00',end_time:'11:00'},{name:'B',start_time:'13:00',end_time:'17:00'}],employees:[],departments:[],genders:[],uoms:[]},
 'lotus_farm.attendance_day.board':{date:'2026-10-20',has_calendar:true,holiday:null,period_closed:false,counts:{matching:2,review:0,manual:0},
  rows:['E1','E2'].map(employee=>({employee,employee_name:'Synthetic '+employee,row_key:employee,review_hash:'review-'+employee,name:'ATT-'+employee,modified:'version-1',status:'Present',working_hours:8,overtime_hours:0,morning_present:1,afternoon_present:1,daily_presence:true,docstatus:0,matches:true,machine:machine('')}))},
 'lotus_farm.attendance_day.approve_matching':{approved:2,names:['ATT-A','ATT-B']},
 'lotus_farm.timekeeping.save_staff':{names:['ATT-A']}
})
let routes={}
globalThis.fetch=async(url, options={})=>{
 const method=new URL(url,'http://localhost:8080').pathname.replace('/api/method/','')
 calls.push({method,args:options.body?JSON.parse(options.body):null})
 return {ok:true,status:200,json:async()=>({message:structuredClone(routes[method])})}
}
const Timekeeping=await load('TimekeepingApp.vue')
const Roster=await load('components/timekeeping/TkRoster.vue')
const button=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label)
const ready=async()=>{routes=fixtures();calls.length=0;const view=mount(Timekeeping,{embedded:true});await tick();await tick();await tick();return view}

test('unsaved attendance blocks matching approval and browser unload',async()=>{
 const view=await ready()
 const input=view.root.querySelector('.ag-row[row-id="E1"] input[type=number]')
 input.value='3';input.dispatchEvent(new Event('input',{bubbles:true}));await tick()
 assert.match(view.root.textContent,/Chưa lưu/)
 assert.equal(button(view.root,'Duyệt 2 dòng khớp máy').disabled,true)
 const event=new Event('beforeunload',{cancelable:true});window.dispatchEvent(event)
 assert.equal(event.defaultPrevented,true)
 assert.equal(calls.filter(c=>c.method.endsWith('approve_matching')).length,0)
 view.unmount()
})

test('one employee/day has two session controls and saves half a day after clearing afternoon',async()=>{
 const view=await ready()
 assert.equal(view.root.querySelector('select[aria-label="Ca làm việc"]'),null)
 const afternoon=view.root.querySelector('.ag-row[row-id="E1"] [aria-label="Chiều Synthetic E1"]')
 afternoon.click();await tick()
 button(view.root,'Lưu nháp').click();await tick();await tick()
 const saved=calls.find(c=>c.method.endsWith('save_staff'))
 assert.equal(saved.args.rows.length,1)
 assert.equal(saved.args.daily_presence,1)
 assert.equal(saved.args.rows[0].morning_present,1)
 assert.equal(saved.args.rows[0].afternoon_present,0)
 assert.equal(view.root.querySelector('.ag-row[row-id="E2"] [aria-label="Chiều Synthetic E2"]').getAttribute('data-state'),'checked')
 view.unmount()
})

test('matching approval sends one reviewed version per employee/day',async()=>{
 const view=await ready()
 button(view.root,'Duyệt 2 dòng khớp máy').click();await tick()
 document.querySelector('dialog[open] form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))
 await tick();await tick()
 const approved=calls.find(c=>c.method.endsWith('approve_matching'))
 assert.equal(approved.args.daily_presence,1)
 assert.deepEqual(approved.args.reviewed_rows,[{row_key:'E1',review_hash:'review-E1'},{row_key:'E2',review_hash:'review-E2'}])
 view.unmount()
})

test('the common header tick selects rows for a morning action and one daily save',async()=>{
 routes=fixtures();calls.length=0
 for(const row of routes['lotus_farm.attendance_day.board'].rows)Object.assign(row,{name:null,status:'Absent',working_hours:0,morning_present:0,afternoon_present:0,matches:false})
 const view=mount(Timekeeping,{embedded:true});await tick();await tick();await tick()
 for(let i=0;i<12&&!view.root.querySelector('.lotus-grid-select-header button');i++)await tick()
 view.root.querySelector('.lotus-grid-select-header button').click();await tick()
 assert.match(view.root.textContent,/Đã chọn 2/)
 button(view.root,'Chấm sáng').click();await tick()
 assert.equal(button(view.root,'Lưu nháp').disabled,false)
 button(view.root,'Lưu nháp').click();await tick();await tick()
 const saved=calls.find(c=>c.method.endsWith('save_staff'))
 assert.equal(saved.args.rows.length,2)
 assert.ok(saved.args.rows.every(row=>row.morning_present===1&&row.afternoon_present===0))
 view.unmount()
})

test('roster accepts an explicit non-overlapping set of daily shifts',async()=>{
 routes=fixtures();calls.length=0
 routes['lotus_farm.shift_admin.roster']={can_manage:true,days:[{date:'2026-10-19',closed:false}],rows:[{employee:'E1',employee_name:'Synthetic An',cells:[{date:'2026-10-19',shift:'',shifts:[]}]}]}
 routes['lotus_farm.shift_admin.set_roster']={applied:[{employee:'E1'}],errors:[],warnings:[]}
 const view=mount(Roster,{company:'SYNTHETIC',today:'2026-10-20',shifts:routes['lotus_farm.timekeeping.catalogue'].shifts})
 await tick();await tick()
 view.root.querySelector('.tk-cell').dispatchEvent(new Event('pointerdown',{bubbles:true}));window.dispatchEvent(new Event('pointerup'));await tick()
 button(view.root,'Nhiều ca trong ngày').click();await tick()
 const dialog=document.querySelector('dialog[open]')
 for(const checkbox of dialog.querySelectorAll('[role=checkbox]')){checkbox.click();await tick()}
 dialog.querySelector('form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()
 const saved=calls.find(c=>c.method.endsWith('set_roster'))
 assert.deepEqual(saved.args.changes[0].shifts,['A','B'])
 view.unmount()
})
