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
  rows:['A','B'].map(shift=>({employee:'E1',employee_name:'Synthetic An',row_key:'E1::'+shift,shift,review_hash:'review-'+shift,name:'ATT-'+shift,modified:'version-1',status:'Present',working_hours:4,overtime_hours:0,docstatus:0,matches:true,machine:machine(shift)}))},
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
 const input=view.root.querySelector('.ag-row[row-id="E1::A"] input[type=number]')
 input.value='3';input.dispatchEvent(new Event('input',{bubbles:true}));await tick()
 assert.match(view.root.textContent,/Chưa lưu/)
 assert.equal(button(view.root,'Duyệt 2 dòng khớp máy').disabled,true)
 const event=new Event('beforeunload',{cancelable:true});window.dispatchEvent(event)
 assert.equal(event.defaultPrevented,true)
 assert.equal(calls.filter(c=>c.method.endsWith('approve_matching')).length,0)
 view.unmount()
})

test('editing one shift selects and saves only that employee-shift row',async()=>{
 const view=await ready()
 const input=view.root.querySelector('.ag-row[row-id="E1::A"] input[type=number]')
 input.value='3';input.dispatchEvent(new Event('input',{bubbles:true}));await tick()
 button(view.root,'Lưu nháp').click();await tick();await tick()
 const saved=calls.find(c=>c.method.endsWith('save_staff'))
 assert.equal(saved.args.rows.length,1)
 assert.equal(saved.args.rows[0].shift,'A')
 assert.equal(saved.args.rows[0].working_hours,3)
 assert.equal(view.root.querySelector('.ag-row[row-id="E1::B"] input[type=number]').value,'4')
 view.unmount()
})

test('matching approval sends the reviewed version of each distinct shift',async()=>{
 const view=await ready()
 button(view.root,'Duyệt 2 dòng khớp máy').click();await tick()
 document.querySelector('dialog[open] form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))
 await tick();await tick()
 const approved=calls.find(c=>c.method.endsWith('approve_matching'))
 assert.deepEqual(approved.args.reviewed_rows,[{row_key:'E1::A',review_hash:'review-A'},{row_key:'E1::B',review_hash:'review-B'}])
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
