import test from 'node:test'
import {readFileSync} from 'node:fs'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document,createApp} from './support/mount.mjs'
import {createRouter,createMemoryHistory} from 'vue-router'
import {pages,navGroups} from '../src/domain.js'

const card=(extra={})=>({tag:'T1',colour:'Đỏ',week:43,lan:1,first_cut:'2026-10-21',start:'2026-12-20',end:'2026-12-30',status:'waiting',cut:113,rejected:0,harvested:0,left:113,lots:[{block:'B1',code:'A1',cut:20,rejected:1,harvested:2,left:17}],...extra})
let calls=[],replies={}
globalThis.fetch=async(url)=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.replace('/api/method/lotus_farm.bunch_report.','')
 calls.push({method,query:u.search})
 if(!(method in replies))return {ok:false,status:404,json:async()=>({message:'Missing '+method})}
 return {ok:true,status:200,json:async()=>({message:replies[method]})}
}
async function settle(){for(let i=0;i<8;i++)await tick()}
const dialog=()=>document.querySelector('dialog[open]')

test('Báo cáo công việc holds the four reports, Dự thu stays apart',()=>{
 const group=navGroups.find(g=>g.label==='Báo cáo công việc')
 assert.deepEqual(group.items.map(i=>i[2]),['Báo cáo chăm sóc vườn','Báo cáo chăm sóc buồng','Xưởng đóng gói','BVTV'])
 assert.ok(navGroups.find(g=>g.label==='Dự thu').items.some(i=>i[0]==='forecast'))
 for(const [id] of group.items)assert.ok(pages.some(([p])=>p===id),id)
})
const round={tag:'T',colour:'Đỏ',year:2026,week:43,lan:1,first_cut:'2026-10-21',cut:100,bag:88,care:40,prop:0,rejected:0,harvested:0,left:100,lots:[]}
const fact={w:'2026-W43',m:'2026-10',z:'A',b:'A1',t:'Tổ 01',c:'Đỏ',l:'1',k:0}
const sections={options:{year:[{value:'2026',label:'2026'}]},zones:['A','B'],
 cube:[{...fact,s:'inject',c:'',q:40},{...fact,s:'prop',c:'',q:20},{...fact,s:'care',c:'',q:30},{...fact,s:'cut',q:100},{...fact,s:'bag',q:88},{...fact,s:'reject',q:2},{...fact,s:'left',t:'',q:88},{...fact,s:'harvest',q:10,k:200},{...fact,b:'A10',s:'cut',q:5}],
 dashboard:{totals:{inject:40,cut:100,bag:88,care:30,prop:20,reject:2,harvest:10,kg:200},weeks:[{week:'2026-W43',number:43,start:'2026-10-19',inject:40,cut:100,bag:88,care:40,prop:0,reject:2,harvest:10,kg:200}],lots:[{block:'B',code:'A1',inject:40,cut:100,bag:88,care:40,prop:0,reject:2,harvest:10,kg:200}]},
 stock:{cards:[{...card(),year:2026}],left:113,due:0,overdue:0},cut_weeks:[{week:'2026-W43',number:43,colour:'Đỏ',lan1:60,lan2:40,total:100,lots:[]}],progress:[round,{...round,tag:'U',lan:2,cut:20,bag:2,care:0}],
 injection:{weeks:[],injected:40,waiting:30,late:[{code:'A5',late_days:23,qty:12}],late_total:12},rejects:{total:2,before:0,after:2,rate:2,cards:[{reason:'Gãy đổ',qty:2,lots:1,worst:[],rows:[]}]},harvest:{qty:10,kg:200,kg_per:20,cards:[]}}
async function openPage(){
 replies={sections};calls=[]
 const Page=await load('components/report/BunchCareReport.vue')
 const router=createRouter({history:createMemoryHistory('/lotus'),routes:[{path:'/:p(.*)*',component:{render:()=>null}}]})
 await router.push('/bao-cao-cham-soc-buong?farm=F');await router.isReady()
 const el=document.createElement('div');document.body.appendChild(el)
 const app=createApp({render:()=>h(Page,{embedded:true})});app.use(router);app.mount(el);await settle()
 return {el,close(){app.unmount();el.remove()}}
}
test('the dashboard follows the work from first stage to last',async()=>{
 const ui=await openPage()
 try{
  assert.deepEqual([...ui.el.querySelectorAll('.stage-chain span')].map(n=>n.textContent),['Chích bắp','Chống đổ','Tỉa, vệ sinh','Cắt bắp','Bao buồng','Hủy buồng','Tồn buồng','Thu hoạch'])
  assert.deepEqual([...ui.el.querySelectorAll('.bi-stage h2')].map(n=>[...n.childNodes].filter(x=>x.nodeName==='B'||x.nodeType===3).map(x=>x.textContent).join('').trim()),['1Chích bắp','2Chống đổ','3Tỉa, vệ sinh','4Cắt bắp','5Bao buồng','6Hủy buồng','7Tồn buồng','8Thu hoạch','Bảng tổng hợp'])
  assert.ok(ui.el.querySelectorAll('.lotus-chart-card').length>=27,'several charts')
  assert.match(ui.el.querySelector('.stage-chain').textContent,/Bao buồng\s*88\s*84% số đã cắt/)
  assert.match(ui.el.querySelector('.stage-chain').textContent,/Chống đổ\s*20\s*50% số đã chích/,'before cắt bắp it is measured against chích')
  assert.equal(ui.el.querySelector('[aria-label="Vườn"]'),null,'the box at the top of the app chooses the vườn')
  assert.deepEqual([...ui.el.querySelectorAll('.pivot-filter__button')].map(b=>b.textContent.trim()),['Năm','Tháng','Tuần','Khu','Lô','Tổ','Màu dây','Lần cắt'])
  assert.match(ui.el.textContent,/Quá hạn cắt\s*⚠ 12/)
 }finally{ui.close()}
})
const cardNamed=(el,title)=>[...el.querySelectorAll('.lotus-chart-card')].find(c=>c.querySelector('h3')?.textContent===title)
test('tồn buồng opens by màu dây, by khu and by lô, side by side',async()=>{
 const ui=await openPage()
 try{
  for(const title of ['Tồn buồng theo màu dây','Tồn buồng theo khu','Tồn buồng theo lô'])assert.ok(cardNamed(ui.el,title),title)
 }finally{ui.close()}
})
test('each chart keeps its own choices',async()=>{
 const ui=await openPage()
 try{
  const card=cardNamed(ui.el,'Tồn buồng theo khu')
  const by=card.querySelector('select[aria-label="Xem theo"]')
  by.value='w';by.dispatchEvent(new window.Event('change',{bubbles:true}));await settle()
  assert.ok(cardNamed(ui.el,'Tồn buồng theo tuần'),'this chart changed')
  assert.ok(cardNamed(ui.el,'Tồn buồng theo màu dây'),'its neighbour did not')
  assert.ok(cardNamed(ui.el,'Cắt bắp theo màu dây'),'nor another công đoạn')
 }finally{ui.close()}
})
test('a chart offers only what its công đoạn has',async()=>{
 const ui=await openPage()
 try{
  const options=title=>[...cardNamed(ui.el,title).querySelectorAll('select[aria-label="Xem theo"] option')].map(o=>o.textContent)
  assert.deepEqual(options('Chích bắp theo khu'),['Khu','Tuần','Tháng','Tổ','Lô'],'no ribbon before cắt bắp')
  assert.ok(options('Hủy buồng theo lý do').includes('Lý do'))
  assert.ok(!options('Tồn buồng theo khu').includes('Tổ'))
 }finally{ui.close()}
})
test('a chart can change kind, and a round one is not split',async()=>{
 const ui=await openPage()
 try{
  const card=cardNamed(ui.el,'Tồn buồng theo màu dây')
  assert.deepEqual([...card.querySelectorAll('select[aria-label="Kiểu biểu đồ"] option')].map(o=>o.textContent),['Cột','Thanh ngang','Đường','Miền','Tròn'])
  assert.equal(card.querySelector('select[aria-label="Tách theo"]'),null)
 }finally{ui.close()}
})
test('every chart of the dashboard prints its numbers',()=>{
 const page=readFileSync(new URL('../src/components/report/BunchCareReport.vue',import.meta.url),'utf8')+readFileSync(new URL('../src/components/report/PivotChart.vue',import.meta.url),'utf8')
 assert.equal(page.split('<LotusChart ').length-1,page.split('<LotusChart show-values ').length-1)
 const chart=readFileSync(new URL('../src/components/LotusChart.vue',import.meta.url),'utf8')
 assert.match(chart,/Number\(p\.value\)\?number\(p\.value\):''/,'a zero prints nothing')
})
