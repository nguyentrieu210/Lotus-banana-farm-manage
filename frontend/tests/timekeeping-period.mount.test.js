import test from 'node:test'
import assert from 'node:assert/strict'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,mount,tick} from './support/mount.mjs'

const calls=[]
let routes={}
// Frappe /api/method stand-in: GET args come from the query string, POST args from the JSON body.
globalThis.fetch=async(url,options={})=>{
 const target=new URL(url,'http://localhost:8080'),method=target.pathname.replace('/api/method/','')
 const args=options.body?JSON.parse(options.body):Object.fromEntries(target.searchParams)
 calls.push({method,args})
 const handler=routes[method]
 if(!handler)return {ok:false,status:404,json:async()=>({exc_type:'DoesNotExistError',message:method})}
 return {ok:true,status:200,json:async()=>({message:typeof handler==='function'?handler(args):handler})}
}
const TimekeepingApp=await load('TimekeepingApp.vue')
const all={read:true,create:true,write:true,submit:true,cancel:true,delete:true,export:true,print:true}
const base=(day)=>({
 'lotus_farm.timekeeping.bootstrap':{user:'hr@lotus',today:'2026-10-14',csrf_token:'t',companies:[{name:'Lotus',default_currency:'VND'}],is_hr_manager:true,can_read_checkins:true,
  capabilities:{Employee:all,Attendance:all,'Work Team':all,'Lotus Crew Attendance':all}},
 'lotus_farm.timekeeping.catalogue':{farms:[],teams:[],works:[],shifts:[],departments:[],genders:[],uoms:[]},
 'lotus_farm.timekeeping.staff_day':{date:'2026-10-14',rows:[
  {employee:'E1',employee_name:'An',name:null,status:'',working_hours:0,overtime_hours:0,docstatus:0},
  {employee:'E2',employee_name:'Bình',name:null,status:'',working_hours:0,overtime_hours:0,docstatus:0}],holiday:null,has_calendar:true,...day},
})
const text=root=>root.textContent.replace(/\s+/g,' ')
const button=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label)
const row=(root,name)=>[...root.querySelectorAll('.attendance-roster tbody tr')].find(tr=>tr.textContent.includes(name))

test('machine check-ins fill reviewable drafts and flag missing punches',async()=>{
 calls.length=0
 routes={...base({period_closed:false}),
  'lotus_farm.timekeeping.propose_from_checkins':{date:'2026-10-14',checkins:3,rows:[
   {employee:'E1',checkins:2,status:'Present',working_hours:9,overtime_hours:1,in_time:'2026-10-14 07:00:00',out_time:'2026-10-14 17:00:00',late_entry:0,early_exit:0,needs_review:0,reason:''},
   {employee:'E2',checkins:1,status:'',working_hours:0,overtime_hours:0,in_time:'2026-10-14 07:05:00',out_time:null,late_entry:0,early_exit:0,needs_review:1,reason:'Thiếu lượt chấm'}]},
  'lotus_farm.timekeeping.save_staff':{names:['HR-ATT-1']}}
 const view=mount(TimekeepingApp,{embedded:true});await tick();await tick()
 button(view.root,'Lấy công từ máy chấm').click();await tick()
 assert.equal(row(view.root,'An').querySelector('select').value,'Present')
 assert.match(row(view.root,'An').textContent,/07:00–17:00/)
 assert.ok(row(view.root,'Bình').classList.contains('attendance-review'),'a single punch is flagged, not guessed')
 assert.match(row(view.root,'Bình').textContent,/Cần kiểm tra/)
 assert.equal(row(view.root,'Bình').querySelector('select').value,'')
 button(view.root.querySelector('.attendance-toolbar'),'Lưu nháp').click();await tick()
 const save=calls.find(c=>c.method==='lotus_farm.timekeeping.save_staff')
 assert.deepEqual(save.args.rows.map(r=>[r.employee,r.status,r.overtime_hours,r.in_time]),[['E1','Present',1,'2026-10-14 07:00:00']],'only reviewed rows with a status are saved')
 view.unmount()
})

test('a closed month is read-only',async()=>{
 routes=base({period_closed:true})
 const view=mount(TimekeepingApp,{embedded:true});await tick();await tick()
 assert.match(text(view.root),/Tháng 2026-10 đã khóa công/)
 const toolbar=view.root.querySelector('.attendance-toolbar')
 for(const label of ['Lấy công từ máy chấm','Lưu nháp','Duyệt đã chọn','Có mặt tất cả'])assert.ok(!button(toolbar,label),label+' is hidden')
 assert.ok(row(view.root,'An').querySelector('select').disabled)
 view.unmount()
})

test('status chips filter the roster and the month sheet shades days off',async()=>{
 routes={...base({period_closed:false}),'lotus_farm.timekeeping.monthly':{month:'2026-10',days:31,rows:[{employee:'E1',employee_name:'An',days:{'1':[{status:'Present',docstatus:1}],'2':[{status:'Absent',docstatus:0}]},workdays:1,working_hours:8,overtime_hours:0,draft_count:1}],holidays:{'4':1,'20':0},period_closed:true},'lotus_farm.timekeeping.crew_monthly':{month:'2026-10',days:31,rows:[],holidays:{}}}
 routes['lotus_farm.timekeeping.staff_day'].rows[0]={...routes['lotus_farm.timekeeping.staff_day'].rows[0],name:'ATT-1',status:'Present',docstatus:1}
 const view=mount(TimekeepingApp,{embedded:true});await tick();await tick()
 const chip=label=>[...view.root.querySelectorAll('.tk-views button')].find(b=>b.textContent.startsWith(label))
 chip('Đã duyệt').click();await tick()
 assert.deepEqual([...view.root.querySelectorAll('.attendance-roster tbody tr strong')].map(n=>n.textContent),['An'])
 chip('Chưa chấm').click();await tick()
 assert.deepEqual([...view.root.querySelectorAll('.attendance-roster tbody tr strong')].map(n=>n.textContent),['Bình'])
 ;[...view.root.querySelectorAll('[role=tab]')].find(b=>b.textContent==='Bảng công tháng').click();await tick();await tick()
 const head=[...view.root.querySelectorAll('.tk-sheet thead th')]
 assert.ok(head[4].classList.contains('is-off'),'4/10 is a weekly off day')
 assert.ok(head[20].classList.contains('is-holiday'),'20/10 is a public holiday')
 const cells=[...view.root.querySelectorAll('.tk-sheet tbody tr')[0].querySelectorAll('td')]
 assert.equal(cells[0].textContent,'X');assert.ok(cells[1].classList.contains('is-draft'),'draft attendance is marked, not counted')
 assert.match(view.root.textContent,/Đã khóa kỳ/)
 view.unmount()
})
