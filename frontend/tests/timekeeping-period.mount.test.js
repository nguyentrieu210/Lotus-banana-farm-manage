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
 'lotus_farm.attendance_day.board':{date:'2026-10-14',rows:[
  {employee:'E1',employee_name:'An',name:null,status:'',working_hours:0,overtime_hours:0,docstatus:0,matches:false,manual:false,machine:null},
  {employee:'E2',employee_name:'Bình',name:null,status:'',working_hours:0,overtime_hours:0,docstatus:0,matches:false,manual:false,machine:null}],holiday:null,has_calendar:true,counts:{matching:0,review:0,manual:0},synced:null,...day},
})
const text=root=>root.textContent.replace(/\s+/g,' ')
const button=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label)
const row=(root,name)=>[...root.querySelectorAll('.attendance-roster .ag-row')].find(tr=>tr.textContent.includes(name))

test('the board shows the device reading with minutes, and approves only matching rows in one step',async()=>{
 calls.length=0
 const machine={checkins:2,status:'Present',working_hours:8.6,in_time:'2026-10-14 06:12:00',out_time:'2026-10-14 14:50:00',late_entry:1,early_exit:0,needs_review:0,reason:'',
  late_minutes:12,early_minutes:0,after_minutes:50,suggested_overtime:0.75,clean:true,shift:'Ca 1'}
 routes={...base({period_closed:false,counts:{matching:1,review:1,manual:0}}),
  'lotus_farm.attendance_day.approve_matching':{approved:1,names:['HR-ATT-1']}}
 const rows=routes['lotus_farm.attendance_day.board'].rows
 rows[0]={...rows[0],matches:true,machine}
 rows[1]={...rows[1],machine:{checkins:1,status:'',in_time:'2026-10-14 07:05:00',out_time:null,needs_review:1,reason:'Thiếu lượt chấm',late_minutes:0,early_minutes:0,after_minutes:0,suggested_overtime:0,clean:false}}
 const view=mount(TimekeepingApp,{embedded:true});await tick();await tick()
 assert.equal(calls.find(c=>c.method==='lotus_farm.attendance_day.board').args.date,'2026-10-14')
 const first=[...view.root.querySelectorAll('.attendance-roster .ag-row strong')].map(n=>n.textContent)
 assert.deepEqual(first,['Bình','An'],'a row needing review comes first')
 assert.match(row(view.root,'An').textContent,/06:12 → 14:50/)
 assert.match(row(view.root,'An').textContent,/Muộn 12′/)
 assert.match(row(view.root,'An').textContent,/Dư 50′ → đề xuất TC 0.75 giờ/)
 assert.ok(row(view.root,'Bình').classList.contains('attendance-review'),'a single punch is flagged, not guessed')
 assert.equal(row(view.root,'An').querySelector('select').value,'','nothing is filled without a click')
 button(view.root.querySelector('.attendance-toolbar'),'Duyệt 1 dòng khớp máy').click();await tick()
 assert.match(document.body.textContent,/Tăng ca lấy theo đề xuất/)
 /* the confirmation is the standard dialog, rendered on <body> */document.querySelector('dialog[open] form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()
 assert.ok(calls.some(c=>c.method==='lotus_farm.attendance_day.approve_matching'&&c.args.date==='2026-10-14'))
 view.unmount()
})

test('using the device values fills one row only, keeping the suggested overtime',async()=>{
 calls.length=0
 const machine={checkins:2,status:'Present',working_hours:8.6,in_time:'2026-10-14 06:12:00',out_time:'2026-10-14 14:50:00',late_entry:1,early_exit:0,needs_review:0,reason:'',late_minutes:12,early_minutes:0,after_minutes:50,suggested_overtime:0.75,clean:true}
 routes={...base({period_closed:false,counts:{matching:0,review:0,manual:1}}),'lotus_farm.timekeeping.save_staff':{names:['HR-ATT-1']}}
 const rows=routes['lotus_farm.attendance_day.board'].rows
 rows[0]={...rows[0],name:'HR-ATT-1',modified:'m',status:'Present',working_hours:7,manual:true,machine}
 const view=mount(TimekeepingApp,{embedded:true});await tick();await tick()
 assert.match(row(view.root,'An').textContent,/Đã chỉnh tay, khác máy/)
 button(row(view.root,'An'),'Dùng số máy').click();await tick()
 button(view.root.querySelector('.attendance-toolbar'),'Lưu nháp').click();await tick()
 const save=calls.find(c=>c.method==='lotus_farm.timekeeping.save_staff')
 assert.deepEqual(save.args.rows.map(r=>[r.employee,r.working_hours,r.overtime_hours,r.in_time]),[['E1',8.6,0.75,'2026-10-14 06:12:00']])
 view.unmount()
})

test('a closed month is read-only',async()=>{
 routes=base({period_closed:true})
 const view=mount(TimekeepingApp,{embedded:true});await tick();await tick()
 assert.match(text(view.root),/Tháng 2026-10 đã khóa công/)
 const toolbar=view.root.querySelector('.attendance-toolbar')
 for(const label of ['Lưu nháp','Duyệt đã chọn','Có mặt tất cả'])assert.ok(!button(toolbar,label),label+' is hidden')
 assert.ok(row(view.root,'An').querySelector('select').disabled)
 view.unmount()
})

test('status chips filter the roster and the month sheet shades days off',async()=>{
 routes={...base({period_closed:false}),'lotus_farm.timekeeping.monthly':{month:'2026-10',days:31,rows:[{employee:'E1',employee_name:'An',days:{'1':[{status:'Present',docstatus:1}],'2':[{status:'Absent',docstatus:0}]},workdays:1,working_hours:8,overtime_hours:0,draft_count:1}],holidays:{'4':1,'20':0},period_closed:true},'lotus_farm.timekeeping.crew_monthly':{month:'2026-10',days:31,rows:[],holidays:{}}}
 routes['lotus_farm.attendance_day.board'].rows[0]={...routes['lotus_farm.attendance_day.board'].rows[0],name:'ATT-1',status:'Present',docstatus:1}
 const view=mount(TimekeepingApp,{embedded:true});await tick();await tick()
 const chip=label=>[...view.root.querySelectorAll('.tk-views button')].find(b=>b.textContent.startsWith(label))
 chip('Đã duyệt').click();await tick();await tick();await tick()
 assert.deepEqual([...view.root.querySelectorAll('.attendance-roster .ag-row strong')].map(n=>n.textContent),['An'])
 chip('Chưa chấm').click();await tick();await tick();await tick()
 assert.deepEqual([...view.root.querySelectorAll('.attendance-roster .ag-row strong')].map(n=>n.textContent),['Bình'])
 ;[...view.root.querySelectorAll('[role=tab]')].find(b=>b.textContent==='Bảng công tháng').click();await tick();await tick()
 const head=day=>view.root.querySelector('.tk-sheet .ag-header-cell[col-id="day_'+day+'"]')
 assert.ok(head(4).classList.contains('is-off'),'4/10 is a weekly off day')
 assert.ok(head(20).classList.contains('is-holiday'),'20/10 is a public holiday')
 const entry=day=>view.root.querySelector('.tk-sheet .ag-row[row-id="E1"] .ag-cell[col-id="day_'+day+'"]')
 assert.equal(entry(1).textContent,'X');assert.ok(entry(2).classList.contains('is-draft'),'draft attendance is marked, not counted')
 assert.match(view.root.textContent,/Đã khóa kỳ/)
 view.unmount()
})