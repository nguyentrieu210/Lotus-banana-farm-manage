import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document,window} from './support/mount.mjs'

const A5='block-a5',A6='block-a6'
const works=[{name:'CB',label:'Cắt bắp',stage:'Cut Bud',group:'Bunch',pay_mode:'Daywork'},{name:'BB',label:'Bao buồng',stage:'Bag',group:'Bunch',pay_mode:'Count'},
 {name:'TH',label:'Thu hoạch buồng',stage:'Harvest',group:'Bunch',pay_mode:'Daywork'},{name:'CL',label:'Cắt lá',stage:'',group:'Field',pay_mode:'Lot',uom:'Ha'}]
const lot=(block,code,extra={})=>({block,code,zone:'A',area_ha:4,trees:8000,cycle:2,quarantine_until:null,active:true,assignments:[],lines:[],colours:[],...extra})
const today=(extra={})=>({date:'2026-11-10',farm:'F',team:'T1',team_name:'Tổ 01',crew:'C',
 report:{name:'R1',state:'Draft',modified:'m1',entered_name:'',on_behalf:0},
 lots:[lot(A5,'A5',{assignments:[{kind:'Round',work_type:'CL',due_date:'2026-11-12'}]}),lot(A6,'A6',{active:false})],
 blocks:[{block:A5,code:'A5',zone:'A'},{block:A6,code:'A6',zone:'A'}],works,ribbon:{name:'tag-o',label:'Cam',code:'#f80',week:46},
 reasons:[{name:'r1',reason_name:'Gãy đổ'}],diseases:[],severities:['Nhẹ','Vừa','Nặng'],
 present:[{employee:'E1',employee_name:'An',own:true,morning:true,afternoon:true}],rights:{write:true,confirm:false,manager:false,user:'to@x'},...extra})
const setup={teams:[{name:'T1',team_name:'Tổ 01',lotus_parent_team:'C'}],my_teams:['T1'],supervised_crews:[]}

let calls=[],replies={}
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.replace('/api/method/lotus_farm.lot_report.','')
 calls.push({method,body:opts.body?JSON.parse(opts.body):null})
 if(!(method in replies))return {ok:false,status:404,json:async()=>({message:'Missing '+method})}
 return {ok:true,status:200,json:async()=>({message:typeof replies[method]==='function'?replies[method]():replies[method]})}
}
const Page=await load('components/field/LotToday.vue')
async function settle(){for(let i=0;i<10;i++)await tick()}
const button=(root,text)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(text))
function type(input,value){input.value=value;input.dispatchEvent(new window.Event('input',{bubbles:true}));input.dispatchEvent(new window.Event('change',{bubbles:true}))}
const dialog=()=>document.querySelector('dialog.lot-entry-modal[open]')
function open(props={}){calls=[];try{window.localStorage.clear()}catch{};return mount({setup:()=>()=>h(Page,{farm:'F',crew:'C',setup,date:'2026-11-10','onUpdate:date':()=>{},...props})})}

test('the day shows one card per lô given to the tổ, no entry form until a lô is opened',async()=>{
 replies={today:()=>today()}
 const view=open();await settle()
 const cards=[...view.root.querySelectorAll('.lot-card')]
 assert.equal(cards.length,1,'only the active lô has a card')
 assert.match(cards[0].textContent,/Lô A5/);assert.match(cards[0].textContent,/Cắt lá/,'the việc given on the lô shows on its card')
 assert.equal(dialog(),null)
 assert.ok(button(view.root,'Gửi báo cáo'),'the tổ trưởng can send a draft day')
 view.unmount()
})

test('a lô opens in a dialog; a quick việc is added, the people default to the tổ, and the save sends one line',async()=>{
 replies={today:()=>today(),save_lot:()=>({saved:1,removed:0,errors:[],lines:[],modified:'m2'})}
 const view=open();await settle()
 view.root.querySelector('.lot-card__main').click();await settle()
 assert.ok(dialog(),'the lô opens in a dialog')
 button(dialog(),'+ Cắt bắp').click();await settle()
 assert.match(dialog().textContent,/Màu dây/);assert.match(dialog().textContent,/Cam/,'cắt bắp takes the ribbon of the day')
 type(dialog().querySelector('.lot-entry__line input'),'12');await settle()
 dialog().querySelector('button[type=submit]').click();await settle()
 const save=calls.find(c=>c.method==='save_lot')
 assert.ok(save,'save_lot is called')
 assert.equal(save.body.report,'R1');assert.equal(save.body.block,A5);assert.equal(save.body.expected_modified,'m1')
 assert.deepEqual(save.body.lines.map(l=>[l.work_type,l.qty]),[['CB',12]])
 assert.deepEqual(save.body.lines[0].people,[{employee:'E1',morning:1,afternoon:1}])
 view.unmount()
})

test('errors of a line are shown on that line and nothing is closed',async()=>{
 replies={today:()=>today(),save_lot:()=>({saved:0,removed:0,errors:[{index:0,message:'Việc khoán số lượng phải nhập khối lượng lớn hơn 0.'}]})}
 const view=open();await settle()
 view.root.querySelector('.lot-card__main').click();await settle()
 button(dialog(),'+ Cắt lá').click();await settle()
 type(dialog().querySelector('.lot-entry__line input'),'1');await settle()
 dialog().querySelector('button[type=submit]').click();await settle()
 assert.ok(dialog(),'the dialog stays open')
 assert.match(dialog().querySelector('.lot-entry__line.is-error').textContent,/phải nhập khối lượng/)
 view.unmount()
})

test('sending asks first, then sends the report',async()=>{
 replies={today:()=>today(),send:()=>({state:'Sent'})}
 const view=open();await settle()
 button(view.root,'Gửi báo cáo').click();await settle()
 assert.ok(view.root.querySelector('.lot-today__ask'),'a confirmation is asked in the page')
 assert.equal(calls.filter(c=>c.method==='send').length,0)
 button(view.root.querySelector('.lot-today__ask'),'Gửi').click();await settle()
 assert.equal(calls.filter(c=>c.method==='send').length,1)
 view.unmount()
})

test('the đội trưởng confirms a sent day; a sent day cannot be edited',async()=>{
 replies={today:()=>today({report:{name:'R1',state:'Sent',modified:'m3'},rights:{write:true,confirm:true,manager:false,user:'lead@x'}}),
  confirm:()=>({state:'Confirmed'}),status:()=>({date:'2026-11-10',teams:[],anomalies:[],overdue:0})}
 const view=open({setup:{...setup,supervised_crews:['C']}});await settle()
 assert.equal(button(view.root,'Gửi báo cáo'),undefined)
 button(view.root,'Xác nhận').click();await settle()
 button(view.root.querySelector('.lot-today__ask'),'Xác nhận').click();await settle()
 const sent=calls.find(c=>c.method==='confirm')
 assert.ok(sent);assert.equal(sent.body.expected_modified,'m3')
 view.root.querySelector('.lot-card__main').click();await settle()
 assert.equal(dialog().querySelector('button[type=submit]'),null,'a sent report opens read-only')
 view.unmount()
})

test('a việc already on the lô is not added twice; bao buồng may take another colour',async()=>{
 const drafted=lot(A5,'A5',{lines:[{name:'e1',state:'Draft',work_type:'CB',stage:'Cut Bud',qty:12,bunch_tag:'tag-o',people:[],materials:[]}],
  colours:[{tag:'tag-o',label:'Cam',week:46,left:12,bag_left:12},{tag:'tag-w',label:'Trắng',week:45,left:6,bag_left:6}]})
 replies={today:()=>today({lots:[drafted]})}
 const view=open();await settle()
 view.root.querySelector('.lot-card__main').click();await settle()
 assert.equal(dialog().querySelectorAll('.lot-entry__line').length,1)
 button(dialog(),'+ Cắt bắp').click();await settle()
 assert.equal(dialog().querySelectorAll('.lot-entry__line').length,1,'no second cắt bắp line')
 assert.match(dialog().textContent,/đã có ở lô này/)
 button(dialog(),'+ Bao buồng').click();await settle()
 button(dialog(),'+ Bao buồng').click();await settle()
 assert.equal(dialog().querySelectorAll('.lot-entry__line').length,3,'bao buồng can be entered for two colours')
 view.unmount()
})

test('thu hoạch shows the buồng left of its colour and more than that is stopped before the server',async()=>{
 const held=lot(A5,'A5',{assignments:[{kind:'Round',work_type:'CL'}],colours:[{tag:'red',label:'Đỏ',week:43,code:'DO',cut:10,bag:0,used:8,left:2,bag_left:10}],
  lines:[{name:'e1',state:'Draft',work_type:'TH',stage:'Harvest',qty:8,bunch_tag:'red',weight_kg:160,people:[],materials:[]}]})
 replies={today:()=>today({lots:[held]}),save_lot:()=>({saved:1,removed:0,errors:[],lines:[],modified:'m2'})}
 const view=open();await settle()
 view.root.querySelector('.lot-card__main').click();await settle()
 assert.match(dialog().textContent,/Còn 10 buồng trên cây, lưu xong còn 2/,'its own draft of 8 is given back to the colour')
 type(dialog().querySelector('.lot-entry__line input'),'12');await settle()
 assert.match(dialog().textContent,/Vượt 2 buồng: màu này chỉ còn 10 buồng trên cây/)
 dialog().querySelector('button[type=submit]').click();await settle()
 assert.equal(calls.filter(c=>c.method==='save_lot').length,0,'nothing is sent')
 assert.match(dialog().textContent,/nhiều buồng hơn số còn lại/)
 view.unmount()
})
