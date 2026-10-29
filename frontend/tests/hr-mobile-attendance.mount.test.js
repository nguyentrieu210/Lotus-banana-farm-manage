import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick} from './support/mount.mjs'

const calls=[];let routes={}
globalThis.fetch=async(url,options={})=>{
 const target=new URL(url,'http://localhost:8080'),method=target.pathname.replace('/api/method/','')
 const args=options.body?JSON.parse(options.body):Object.fromEntries(target.searchParams)
 calls.push({method,args})
 return {ok:true,status:200,json:async()=>({message:structuredClone(routes[method])})}
}
const Attendance=await load('components/hr/HrMobileAttendance.vue')
const row=(employee,am,pm)=>({employee,row_key:employee,employee_name:employee,daily_presence:true,status:am&&pm?'Present':'Half Day',working_hours:(am+pm)*4,docstatus:0,
 morning_present:am,afternoon_present:pm,morning_time:am?'2026-10-20 06:46:00':null,afternoon_time:pm?'2026-10-20 17:01:00':null,
 matches:!!(am&&pm),machine:{checkins:am+pm,status:am&&pm?'Present':'Half Day',needs_review:0}})
const base={
 'lotus_farm.timekeeping.bootstrap':{can_manage_shifts:true,capabilities:{Attendance:{read:true,create:true,submit:true}}},
 'lotus_farm.timekeeping.catalogue':{shifts:[]},
 'lotus_farm.attendance_day.board':{date:'2026-10-20',period_closed:false,counts:{matching:1,review:0,manual:0},rows:[row('An',1,1),row('Bình',1,0),row('Chi',0,1)]}
}

test('phone shows one row per employee, two session stamps, and a half-day filter',async()=>{
 calls.length=0;routes={...base,'lotus_farm.attendance_day.approve_matching':{approved:1}}
 const view=mount(Attendance,{company:'Lotus',today:'2026-10-20'});await tick();await tick();await tick()
 assert.equal(view.root.querySelectorAll('.hr-att__row').length,3)
 assert.equal(view.root.querySelectorAll('.hr-att__group h3').length,0)
 assert.match(view.root.textContent,/Sáng 06:46 · Chiều 17:01/)
 assert.equal(Number(calls.find(c=>c.method.endsWith('.board')).args.daily_presence),1)
 view.root.querySelectorAll('.hr-att__stats button')[1].click();await tick()
 assert.deepEqual([...view.root.querySelectorAll('.hr-att__row strong')].map(s=>s.textContent),['Bình','Chi'])
 const approve=[...view.root.querySelectorAll('button')].find(b=>b.textContent.includes('Duyệt 1 dòng'))
 approve.click();await tick();await tick()
 assert.equal(calls.find(c=>c.method.endsWith('approve_matching')).args.daily_presence,1)
 view.unmount()
})

test('phone edits the two presences together, with no shift selection',async()=>{
 calls.length=0;routes={...base,'lotus_farm.timekeeping.save_staff':{names:['ATT-1']}}
 const view=mount(Attendance,{company:'Lotus',today:'2026-10-20'});await tick();await tick();await tick()
 view.root.querySelector('.hr-att__row').click();await tick();await tick()
 assert.ok(![...document.querySelectorAll('button')].some(b=>b.textContent==='Đổi ca'))
 assert.doesNotMatch(document.querySelector('.hr-att__sheet').textContent,/tăng ca/i)
 const afternoon=document.body.querySelector('.hr-att__sheet select[aria-label="Chiều"]')
 afternoon.value='0';afternoon.dispatchEvent(new Event('change',{bubbles:true}));await tick()
 assert.match(document.querySelector('.hr-att__sheet').textContent,/0.5 công/)
 document.querySelector('.hr-att__sheet').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()
 const saved=calls.find(c=>c.method.endsWith('save_staff'))
 assert.equal(saved.args.daily_presence,1)
 assert.equal(saved.args.rows[0].morning_present,1);assert.equal(Number(saved.args.rows[0].afternoon_present),0)
 view.unmount()
})
