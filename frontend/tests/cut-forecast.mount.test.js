import test from 'node:test'
import assert from 'node:assert/strict'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,loadModule,createApp,h,tick,document,window} from './support/mount.mjs'
import {createPinia,setActivePinia} from 'pinia'
import {createRouter,createMemoryHistory} from 'vue-router'

globalThis.history??=window.history
globalThis.FileReader??=window.FileReader
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
const pinia=createPinia();setActivePinia(pinia)
const CutForecastApp=await load('CutForecastApp.vue')
const {useSession}=await loadModule('store.js')
Object.assign(useSession(),{user:'farm@lotus',today:'2026-10-21',ready:true,farms:[],modules:{forecast:['Harvest Forecast']},capabilities:{},commands:{}})
const M='lotus_farm.cut_forecast.'
const PARAMS=[['days_to_first_shoot','Chặt mẹ lần 2 → bắt đầu đợt trổ 1 (ngày)','days',120],['wave_step_days','Bước giữa 2 đợt trổ (ngày)','days',30],['cut_rate','Tỷ lệ cắt bắp / số cây trổ','rate',0.9],['kg_per_bunch','Kg sơ chế / buồng','kg',20],
 ['wave_1_share','Tỷ lệ trổ đợt 1','rate',0.17],['wave_2_share','Tỷ lệ trổ đợt 2','rate',0.4],['wave_3_share','Tỷ lệ trổ đợt 3','rate',0.25],['wave_4_share','Tỷ lệ trổ đợt 4','rate',0.18]]
const month=(m,over)=>({month:m,shoot:0,inject:0,budcut:0,harvest:0,pack:0,kg:0,tonnes:0,...over})
const board=canEdit=>({farms:[{name:'LOTUS-222',farm_name:'Vườn 222',has_journal:true}],farm:'LOTUS-222',zone:'',zone_list:['A','C'],can_edit:canEdit,params:PARAMS,
 profile:{name:'P1',version:1,source:'Excel',approved_at:'2026-10-21 10:00:00',days_to_first_shoot:120,wave_step_days:30,cut_rate:0.9,kg_per_bunch:20,wave_1_share:0.17,wave_2_share:0.4,wave_3_share:0.25,wave_4_share:0.18},
 profiles:[{name:'P1',version:1,source:'Excel',approved_by:'Administrator',approved_at:'2026-10-21 10:00:00',days_to_first_shoot:120,cut_rate:0.9,harvest_rate:0.97,pack_rate:0.98,kg_per_bunch:20}],
 issues:[],imports:[{name:'I1',file_name:'du-thu.xlsx',source_file:'/private/files/du-thu.xlsx',sha256:'abcdef1234567890',new_rows:358,existing_rows:0,conflict_rows:0,error_rows:0,trees:430871,imported_by:'Administrator',imported_at:'2026-10-21 10:00:00'}],
 months:[month('2026-08',{shoot:63,inject:63}),month('2026-11',{shoot:27240,inject:22978,budcut:12462,harvest:227,pack:223,kg:4460,tonnes:4.46}),month('2027-05',{shoot:16460,budcut:32834,harvest:94518,pack:92632,kg:1852640,tonnes:1852.64})],
 zones:[{zone:'A',trees:95315,entries:65,first_cut:'2026-03-31',last_cut:'2026-08-12',shoot:95315,budcut:85803,harvest:83236,pack:81579,tonnes:1631.58},{zone:'C',trees:98701,entries:98,first_cut:'2026-06-19',last_cut:'2026-10-03',shoot:98701,budcut:88849,harvest:86188,pack:84465,tonnes:1689.3}],
 zone_months:{A:{'2026-11':4.46},C:{'2027-05':900}},
 rows:[{entry:'E1',zone:'A',cut_date:'2026-03-31',tree_qty:73,source_ref:'Khu A | dòng 7',wave:1,share:0.17,shoot_qty:12,shoot_from:'2026-07-29',shoot_to:'2026-08-27',shoot_date:'2026-08-12',inject_date:'2026-08-17',budcut_date:'2026-09-01',budcut_qty:11,harvest_date:'2026-11-05',harvest_qty:11,pack_qty:11,kg:220}],
 totals:{trees:430871,entries:358,suckers:430871,shoot:430871,inject:430871,budcut:387859,harvest:376247,pack:368750,kg:7375000,tonnes:7375,first_cut:'2026-03-31',last_cut:'2026-10-03',first_harvest:'2026-11-05',last_harvest:'2027-08-08',peak_month:'2027-05',peak_tonnes:1852.64,zones:['A','C']}})
async function open(path){
 const router=createRouter({history:createMemoryHistory('/lotus'),routes:[{path:'/:p(.*)*',component:{render:()=>null}}]})
 await router.push(path);await router.isReady()
 const root=document.createElement('div');document.body.append(root)
 const app=createApp({render:()=>h(CutForecastApp,{embedded:true})});app.use(pinia);app.use(router);app.mount(root)
 await tick();await tick()
 return {root,router,unmount:()=>{app.unmount();root.remove()}}
}
const text=root=>root.textContent.replace(/\s+/g,' ')
const button=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.includes(label))

test('the forecast shows totals and stages in the order trổ → chích bắp → cắt bắp → thu hoạch',async()=>{
 calls.length=0;routes={[M+'board']:board(false)}
 const view=await open('/forecast')
 const page=text(view.root)
 assert.match(page,/Cây mẹ chặt lần 2\s*430\.871/)
 assert.match(page,/Tấn sơ chế\s*7\.375 tấn/)
 assert.match(page,/Tháng cao điểm\s*05\/2027/)
 const head=[...view.root.querySelector('.cutfc-table .lotus-ag-grid').querySelectorAll('.ag-header-cell[col-id]')].map(th=>th.getAttribute('col-id'))
 assert.deepEqual(head,['month','shoot','inject','budcut','harvest','pack','tonnes'])
 assert.ok(head.indexOf('inject')<head.indexOf('budcut'),'chích bắp comes before cắt bắp')
 const first=view.root.querySelector('.cutfc-table .ag-row')
 assert.match(first.textContent,/08\/2026.*đã qua/,'a past month is marked')
 assert.ok(!button(view.root,'Nhập Excel'),'readers cannot import')
 view.unmount()
})

test('the journal tab lists each wave with its dates; zone filter goes to the server',async()=>{
 routes={[M+'board']:board(false)}
 const view=await open('/forecast')
 button(view.root,'Nhật ký & lịch từng đợt').click();await tick()
 const row=view.root.querySelector('.cutfc-journal .ag-row').textContent
 assert.match(row,/31\/03\/2026.*12.*29\/07\/2026 – 27\/08\/2026.*12\/08\/2026.*17\/08\/2026.*01\/09\/2026.*05\/11\/2026/)
 await view.router.push('/forecast?zone=C');await tick();await tick()
 assert.equal(calls.at(-1).args.zone,'C')
 view.unmount()
})

test('a manager previews an upload and imports the new rows with the file parameters',async()=>{
 calls.length=0
 routes={[M+'board']:board(true),
  [M+'preview_import']:{token:'T1',new:2,same:356,conflict:1,errors:0,new_trees:500,param_errors:[],has_profile:true,
   param_changes:[{field:'days_to_first_shoot',label:'Chặt mẹ lần 2 → bắt đầu đợt trổ 1 (ngày)',old:120,new:180}],file_totals:{trees:431371,pack:369000,tonnes:7380},
   rows:[{line:7,zone:'C',cut_date:'2026-07-30',tree_qty:300,state:'conflict',old_qty:290,errors:[]}]},
  [M+'commit_import']:{saved:2,trees:500,profile:2,batch:'I2'}}
 const view=await open('/forecast')
 button(view.root,'Nhập Excel').click();await tick()
 const input=document.body.querySelector('input[type=file]')
 Object.defineProperty(input,'files',{value:[new window.File(['x'],'du-thu.xlsx')]})
 input.dispatchEvent(new window.Event('change'));for(let i=0;i<6;i++)await tick()
 const modal=text(document.body)
 assert.match(modal,/2 dòng mới \(500 cây\)/)
 assert.match(modal,/Đã nhập 290 cây, file ghi 300 cây/)
 assert.match(modal,/7\.380 tấn sơ chế/)
 const go=[...document.body.querySelectorAll('button')].find(b=>/Nhập 2 dòng và thông số/.test(b.textContent))
 assert.ok(go,'the file parameters are applied by default when they differ');go.click();for(let i=0;i<4;i++)await tick()
 const commit=calls.find(c=>c.method===M+'commit_import')
 assert.deepEqual([commit.args.token,commit.args.apply_params],['T1',1])
 view.unmount()
})

test('the parameter form shows rates as percent and blocks wave shares that do not add up',async()=>{
 routes={[M+'board']:board(true),[M+'save_profile']:{version:2}}
 const view=await open('/forecast')
 button(view.root,'Thông số & lần nhập').click();await tick()
 const inputs=[...view.root.querySelectorAll('.cutfc-params input')]
 assert.equal(inputs[2].value,'90','cắt bắp 0.9 is shown as 90%')
 assert.match(text(view.root),/Tổng 4 đợt trổ: 100%/,'only the four shares count, not the wave step days')
 inputs[7].value='10';inputs[7].dispatchEvent(new window.Event('input'));await tick()
 assert.match(text(view.root),/Tổng 4 đợt trổ: 92%/)
 assert.ok(button(view.root,'Lưu thành phiên bản mới').disabled)
 inputs[7].value='18';inputs[7].dispatchEvent(new window.Event('input'));await tick()
 view.root.querySelector('.cutfc-params').dispatchEvent(new window.Event('submit',{cancelable:true}));for(let i=0;i<4;i++)await tick()
 const saved=JSON.parse(calls.find(c=>c.method===M+'save_profile').args.values)
 assert.equal(saved.wave_4_share,0.18)
 view.unmount()
})