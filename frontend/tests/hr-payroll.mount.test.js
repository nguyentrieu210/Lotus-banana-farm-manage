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
const HrApp=await load('HrApp.vue')
const employee={name:'HR-EMP-1',employee_name:'An',lotus_onboarding_state:'Ready',status:'Active',lotus_payment_basis:'Daywork'}
const sheet={month:'2026-09',standard_days:26,currency:'VND',draft:true,totals:{gross:5250000,crew_amount:1500000,employees:1,workdays:21},
 employees:[{employee:'HR-EMP-1',employee_name:'An',payment_basis:'Daywork',workdays:21,paid_leave:0,weekly_off_days:0,holiday_days:0,overtime_hours:0,time_pay:5250000,off_day_pay:0,overtime_pay:0,total:5250000,via_crew:false,issues:[]}],
 crews:[{team_name:'Đội A',foreman:'Ba',work_name:'Bao buồng',completed_qty:500,uom:'Buồng',unit_rate:3000,amount:1500000,workdays:10}],issues:[]}
const routesFor=manager=>({
 'lotus_farm.hr_workspace.bootstrap':{user:'hr@lotus',today:'2026-10-19',csrf_token:'t',companies:[{name:'Lotus'}],is_hr_manager:manager},
 'lotus_farm.hr_workspace.catalogue':{farms:[],departments:[],designations:[],teams:[],grades:[],employment_types:[],genders:[],openings:[],designation_groups:{},worker_categories:['Seasonal'],payment_bases:['Monthly','Daywork']},
 'lotus_farm.hr_workspace.overview':{employees:[employee],candidates:[]},
 'lotus_farm.hr_workspace.employee_detail':{...employee,modified:'2026-10-01 00:00:00',onboarding_gaps:[],lotus_daily_rate:250000,lotus_base_salary:0},
 'lotus_farm.hr_workspace.payroll_readiness':{month:'2026-09',employees:1,employees_without_salary:[],attendance_draft_count:2,crew_pending_count:0,open_punches:0,onboarding_pending:[]},
 'lotus_farm.hr_period.period_status':{month:'2026-09',status:'Open',future:false,blockers:[{code:'draft_attendance',label:'Phiếu công nhân sự còn nháp',count:2}]},
 'lotus_farm.hr_period.payroll_sheet':sheet,
})
const text=root=>root.textContent.replace(/\s+/g,' ')
const tab=(root,label)=>[...root.querySelectorAll('[role=tab]')].find(b=>b.textContent===label)
const button=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label)

test('payroll tab shows last month, blockers keep the close button disabled, sheet and crew payable listed',async()=>{
 calls.length=0;routes=routesFor(true)
 const view=mount(HrApp,{embedded:true});await tick()
 tab(view.root,'Kỳ công & bảng lương').click();await tick();await tick()
 assert.equal(calls.find(c=>c.method==='lotus_farm.hr_period.payroll_sheet').args.month,'2026-09','defaults to the month just ended')
 assert.match(text(view.root),/Phiếu công nhân sự còn nháp: 2/)
 assert.ok(button(view.root,'Khóa kỳ').disabled,'cannot close while blockers remain')
 assert.match(text(view.root),/Bảng lương 2026-09 · bản nháp/)
 assert.match(text(view.root),/Đội A.*Bao buồng.*500 Buồng/)
 const link=[...view.root.querySelectorAll('a')].find(a=>a.textContent==='Xuất bảng lương Excel')
 assert.match(link.getAttribute('href'),/export_payroll\?company=Lotus&month=2026-09/)
 view.unmount()
})

test('pay rate inputs follow the payment basis and only managers see payroll',async()=>{
 routes=routesFor(true)
 const view=mount(HrApp,{embedded:true});await tick()
 button(view.root,'Xem / sửa').click();await tick();await tick()
 const labels=[...document.querySelectorAll('.hr-form-grid label')].map(l=>l.firstChild?.textContent?.trim())
 assert.ok(labels.includes('Đơn giá công nhật (VND)'))
 assert.ok(!labels.includes('Lương cơ bản tháng (VND)'),'daywork has no monthly base salary field')
 assert.ok(button(document.body,'Cho nghỉ việc'))
 view.unmount()
 routes=routesFor(false)
 const staff=mount(HrApp,{embedded:true});await tick()
 assert.equal(tab(staff.root,'Kỳ công & bảng lương'),undefined)
 staff.unmount()
})
