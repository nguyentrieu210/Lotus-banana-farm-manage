import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document,window} from './support/mount.mjs'

// Shapes as lotus_farm.issue_request returns them (backend of spec 005, 11/11/2026).
const formData=(extra={})=>({farm:'F',crew:'C',crew_name:'Đội A + B',today:'2026-11-11',teams:[{name:'T3',team_name:'Tổ 3'},{name:'T5',team_name:'Tổ 5'}],
 blocks:[{name:'B12',block_code:'A12',zone:'A',area_ha:1.2},{name:'B13',block_code:'A13',zone:'A',area_ha:1.3},{name:'B14',block_code:'A14',zone:'A',area_ha:2.5,quarantine_until:'2026-11-20'},{name:'B21',block_code:'B1',zone:'B',area_ha:0}],
 works:[{name:'PHUN',work_name:'Phun thuốc'}],warehouses:[{name:'K',warehouse_name:'Kho vườn'}],warehouse:'K',
 receivers:[{name:'EMP',employee_name:'Nguyễn Văn Nhận',team:'T3'}],receiver:'EMP',approver:'leader@x',approver_label:'Đội trưởng A',can_approve:true,
 open_assignments:[],due_blocks:[],last:[],...extra})
const items=[{name:'ANVIL',item_name:'Anvil 5SC',stock_uom:'Litre',pack_uom:'',pack_factor:0,whole:0},{name:'CHAI',item_name:'Thuốc chai',stock_uom:'Chai',pack_uom:'',pack_factor:0,whole:1}]
const stock={ANVIL:{item_code:'ANVIL',uom:'Litre',available:12,approved_waiting:5},CHAI:{item_code:'CHAI',uom:'Chai',available:1,approved_waiting:0}}
const detail=(name,extra={})=>({name,modified:'m-'+name,state:'Nháp',state_code:'draft',items:[],actions:{edit:true,send:true,delete:true,approve:true},warnings:[],...extra})

let calls=[],replies={}
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.split('/api/method/lotus_farm.issue_request.')[1]
 const call={method,query:Object.fromEntries(u.searchParams),body:opts.body?JSON.parse(opts.body):null}
 calls.push(call)
 const reply=replies[method]
 if(reply===undefined)return {ok:false,status:404,json:async()=>({message:'Missing '+method})}
 const value=typeof reply==='function'?await reply(call):reply
 return {ok:true,status:200,json:async()=>({message:value})}
}
const Form=await load('components/field/MaterialRequestForm.vue')
async function settle(){for(let i=0;i<12;i++)await tick()}
const dialog=()=>document.querySelector('dialog[open]')
const button=text=>[...dialog().querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(text))
function control(prefix){
 const scope=dialog()
 return scope.querySelector(`[aria-label^="${prefix}"]`)||document.getElementById([...scope.querySelectorAll('label')].find(e=>e.textContent.replace(/\*/g,'').trim().startsWith(prefix))?.htmlFor)
}
function type(prefix,value){const e=control(prefix);assert.ok(e,prefix);e.value=value;e.dispatchEvent(new window.Event('input',{bubbles:true}));e.dispatchEvent(new window.Event('change',{bubbles:true}))}
function select(prefix,value){const e=control(prefix);assert.ok(e,prefix);e.value=value;e.dispatchEvent(new window.Event('change',{bubbles:true}))}
async function choose(prefix,text){
 const e=control(prefix);assert.ok(e,prefix);e.focus();e.click();await settle()
 const option=[...document.querySelectorAll('[role=option]')].find(o=>o.textContent.includes(text))
 assert.ok(option,'option '+text);option.click();await settle()
}
const submit=()=>dialog().querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}))
let saved=[]
function show(props={}){calls=[];saved=[];return mount({setup:()=>()=>h(Form,{farm:'F',crew:'C',prefill:{work_type:'PHUN'},onSaved:e=>saved.push(e),...props})})}
const base=()=>({form_data:formData(),item_options:items,stock,save:detail('MR-1'),approve:detail('MR-1',{state:'Chờ cấp',state_code:'waiting',actions:{}}),send:detail('MR-1',{state:'Chờ duyệt',state_code:'sent',actions:{}})})
test.beforeEach(()=>{localStorage.clear()})

test('the đội trưởng picks a whole khu, gives each lô the same quantity, then saves and approves at once',async()=>{
 replies=base()
 const view=show();await settle()
 assert.equal(calls[0].method,'form_data');assert.equal(calls[0].query.crew,'C');assert.equal(calls[0].query.farm,'F')
 assert.match(dialog().querySelector('button[type=submit]').textContent,/Lưu và duyệt/)
 assert.match(dialog().textContent,/cách ly đến 20\/11/)
 button('Chọn cả khu').click();await settle()
 await choose('Thêm vật tư','Anvil');await settle()
 assert.equal(calls.find(c=>c.method==='item_options')?.method,'item_options')
 type('Mỗi lô','2');await settle()
 const asked=calls.find(c=>c.method==='stock');assert.deepEqual(JSON.parse(asked.query.items),['ANVIL']);assert.equal(asked.query.warehouse,'K');assert.equal(asked.query.farm,'F')
 assert.match(dialog().textContent,/Kho còn 12 .* có thể cấp · đã duyệt chờ cấp cho yêu cầu khác 5/)
 submit();await settle()
 const save=calls.find(c=>c.method==='save')
 assert.ok(save,'save is called');assert.equal(save.body.send,0);assert.ok(save.body.client_event_id);assert.equal(save.body.name,null)
 assert.equal(save.body.values.work_type,'PHUN');assert.equal(save.body.values.warehouse,'K');assert.equal(save.body.values.team,'','Cả đội by default');assert.equal(save.body.values.receiver,'EMP')
 assert.deepEqual(save.body.values.lines.map(l=>[l.item_code,l.farm_block,l.qty]),[['ANVIL','B12',2],['ANVIL','B13',2],['ANVIL','B14',2]])
 assert.equal(calls.filter(c=>c.method==='send').length,0,'no send step for someone who approves')
 const approve=calls.find(c=>c.method==='approve')
 assert.ok(approve,'approved by the same person');assert.equal(approve.body.name,'MR-1');assert.equal(approve.body.modified,'m-MR-1');assert.ok(approve.body.client_event_id)
 assert.notEqual(approve.body.client_event_id,save.body.client_event_id)
 assert.match(saved[0].message,/Đã duyệt yêu cầu MR-1/)
 view.unmount()
})

test('a total split by area keeps whole bottles whole and adds up',async()=>{
 replies=base()
 const view=show({prefill:{work_type:'PHUN',blocks:['B12','B13','B14']}});await settle()
 await choose('Thêm vật tư','Thuốc chai');await settle()
 select('Cách nhập','total');await settle()
 type('Tổng','5');await settle()
 assert.match(dialog().textContent,/Kho không đủ hàng/,'stock shortage warns')
 submit();await settle()
 const lines=calls.find(c=>c.method==='save').body.values.lines
 assert.deepEqual(lines.map(l=>[l.farm_block,l.qty]),[['B12',1],['B13',1],['B14',3]])
 view.unmount()
})

test('a lô without area is named, never guessed',async()=>{
 replies=base()
 const view=show({prefill:{work_type:'PHUN',blocks:['B12','B21']}});await settle()
 await choose('Thêm vật tư','Anvil');select('Cách nhập','total');await settle();type('Tổng','6');await settle()
 assert.match(dialog().textContent,/Lô B1 chưa có diện tích/)
 view.unmount()
})

test('nothing is sent without a lô and a quantity',async()=>{
 replies=base()
 const view=show();await settle()
 submit();await settle()
 assert.equal(calls.filter(c=>c.method==='save').length,0)
 assert.match(dialog().querySelector('[role=alert]').textContent,/Chọn ít nhất một lô/)
 view.unmount()
})

test('pressing the button twice saves once',async()=>{
 let release
 replies={...base(),save:()=>new Promise(done=>{release=()=>done(detail('MR-3'))})}
 const original=globalThis.fetch
 let offline=true
 globalThis.fetch=async(url,opts)=>{if(String(url).endsWith('.save')&&offline){offline=false;throw new TypeError('Failed to fetch')}return original(url,opts)}
 try{
  const view=show({prefill:{work_type:'PHUN',blocks:['B12']}});await settle()
  await choose('Thêm vật tư','Anvil');type('Mỗi lô','1');await settle()
  submit();await settle()
  assert.match(dialog().textContent,/mất mạng/,'the lost answer is said')
  submit();submit();await settle()
  release?.();await settle()
  assert.equal(calls.filter(c=>c.method==='save').length,1,'the double press sends once')
  assert.equal(calls.filter(c=>c.method==='approve').length,1)
  view.unmount()
 }finally{globalThis.fetch=original}
})

test('the same body after a failure goes with the same client_event_id',async()=>{
 let n=0
 replies={...base(),save:()=>{n++;if(n===1)throw new Error('lỗi tạm');return detail('MR-4')}}
 const view=show({prefill:{work_type:'PHUN',blocks:['B12']}});await settle()
 await choose('Thêm vật tư','Anvil');type('Mỗi lô','1');await settle()
 submit();await settle();submit();await settle()
 const saves=calls.filter(c=>c.method==='save')
 assert.equal(saves.length,2);assert.equal(saves[0].body.client_event_id,saves[1].body.client_event_id)
 view.unmount()
})

test('numbers typed before losing the app come back',async()=>{
 replies=base()
 localStorage.setItem('lotus-draft:issue-request:F:C:new',JSON.stringify({savedAt:Date.now(),values:{work_type:'PHUN',team:'T3',needed:'2026-11-12',warehouse:'K',receiver:'EMP',note:'',picked:{B13:true},assignments:{},
  materials:[{item_code:'ANVIL',item_name:'Anvil 5SC',uom:'Litre',mode:'each',each:null,total:null,notes:'',qty:{B13:1.25}}],pending:null,name:'',modified:''}}))
 const view=show({prefill:null});await settle()
 assert.match(dialog().textContent,/Đã mở lại số đang nhập dở/)
 submit();await settle()
 const save=calls.find(c=>c.method==='save').body
 assert.deepEqual(save.values.lines.map(l=>[l.farm_block,l.qty]),[['B13',1.25]]);assert.equal(save.values.team,'T3')
 assert.equal(localStorage.getItem('lotus-draft:issue-request:F:C:new'),null,'the copy on the device goes once the server has it')
 view.unmount()
})

test('a warning (same vật tư × lô in another open request) must be confirmed first',async()=>{
 replies={...base(),save:detail('MR-6',{warnings:[{kind:'duplicate',request:'MR-0009',item_code:'ANVIL',farm_block:'B12',message:'ANVIL ở lô A12 đã có trong yêu cầu MR-0009 còn mở.'}]})}
 const view=show({prefill:{work_type:'PHUN',blocks:['B12']}});await settle()
 await choose('Thêm vật tư','Anvil');type('Mỗi lô','1');await settle()
 submit();await settle()
 assert.match(dialog().textContent,/ANVIL ở lô A12 đã có trong yêu cầu MR-0009 còn mở/)
 assert.equal(calls.filter(c=>c.method==='approve').length,0,'not approved yet')
 button('Vẫn duyệt').click();await settle()
 assert.equal(calls.filter(c=>c.method==='approve').length,1)
 view.unmount()
})

test('someone who may not approve sends, and is told who approves',async()=>{
 replies={...base(),form_data:formData({can_approve:false,approver:null,approver_label:'Quản lý vườn'})}
 const view=show({prefill:{work_type:'PHUN',blocks:['B12']}});await settle()
 assert.match(dialog().textContent,/Quản lý vườn sẽ duyệt/)
 assert.match(dialog().querySelector('button[type=submit]').textContent,/Gửi duyệt/)
 await choose('Thêm vật tư','Anvil');type('Mỗi lô','1');await settle()
 submit();await settle()
 assert.equal(calls.filter(c=>c.method==='approve').length,0)
 assert.equal(calls.find(c=>c.method==='send').body.modified,'m-MR-1')
 assert.match(saved[0].message,/Chờ duyệt/)
 view.unmount()
})

test('Lưu nháp saves without sending',async()=>{
 replies={...base(),save:detail('MR-8')}
 const view=show({prefill:{work_type:'PHUN',blocks:['B12']}});await settle()
 await choose('Thêm vật tư','Anvil');type('Mỗi lô','1');await settle()
 button('Lưu nháp').click();await settle()
 assert.equal(calls.filter(c=>['send','approve'].includes(c.method)).length,0)
 assert.match(saved[0].message,/Đã lưu nháp MR-8/)
 view.unmount()
})

test('a returned request opens with its lines and is saved under its name and modified',async()=>{
 replies={...base(),detail:detail('MR-11',{state:'Trả lại',state_code:'returned',team:'T5',work_type:'PHUN',needed:'2026-11-13',warehouse:'K',receiver:'EMP',note:'phun',
  items:[{name:'L1',item_code:'ANVIL',item_name:'Anvil 5SC',uom:'Litre',farm_block:'B12',block_code:'A12',qty:1.5,notes:'liều',assignment:'WA-1'}]}),save:detail('MR-11')}
 const view=show({name:'MR-11',prefill:null});await settle()
 submit();await settle()
 const save=calls.find(c=>c.method==='save').body
 assert.equal(save.name,'MR-11');assert.equal(save.modified,'m-MR-11');assert.equal(save.values.team,'T5')
 assert.deepEqual(save.values.lines,[{item_code:'ANVIL',farm_block:'B12',qty:1.5,notes:'liều',assignment:'WA-1'}])
 view.unmount()
})

test('US4: lô of the open phiếu, lô due by the care cycle and "như lần trước"',async()=>{
 replies={...base(),form_data:formData({open_assignments:[{name:'WA-9',farm_block:'B13',work_type:'PHUN',work_team:'T3',block_code:'A13',team_name:'Tổ 3'}],
  due_blocks:[{farm_block:'B12',block_code:'A12',work_type:'PHUN',due_date:'2026-11-10',status:'overdue'},{farm_block:'B14',block_code:'A14',work_type:'PHUN',due_date:'2026-11-12',status:'due'}],
  last:[{work_type:'PHUN',request:'MR-0001',date:'2026-11-05',items:[{item_code:'ANVIL',item_name:'Anvil 5SC',uom:'Litre',qty:1,area:2,blocks:2,per_block:0.5,per_ha:0.5,notes:'0,5 lít/ha'}]}]})}
 const view=show();await settle()
 button('Lô đang giao việc này cho tổ (1)').click();await settle()
 assert.ok(button('Lô đến hạn theo vòng chăm sóc (2)'))
 const last=button('Lấy như lần trước');assert.match(last.textContent,/MR-0001 · 05\/11/)
 last.click();await settle()
 submit();await settle()
 const lines=calls.find(c=>c.method==='save').body.values.lines
 assert.deepEqual(lines.map(l=>[l.farm_block,l.qty,l.assignment,l.notes]),[['B13',0.65,'WA-9','0,5 lít/ha']])
 view.unmount()
})

test('prefilled from a phiếu giao việc: việc, tổ, lô and the phiếu on the line',async()=>{
 replies=base()
 const view=show({prefill:{work_type:'PHUN',team:'T3',blocks:['B12'],assignments:{B12:'WA-1'}}});await settle()
 assert.match(dialog().textContent,/theo phiếu giao việc/)
 await choose('Thêm vật tư','Anvil');type('Mỗi lô','1');await settle()
 submit();await settle()
 const save=calls.find(c=>c.method==='save').body
 assert.equal(save.values.team,'T3');assert.equal(save.values.lines[0].assignment,'WA-1')
 view.unmount()
})
