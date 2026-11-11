import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document,window} from './support/mount.mjs'

// detail() as lotus_farm.issue_request returns it: card fields, `items` (lines with required/posted/draft/remaining),
// `stock` keyed by vật tư, `history` {at, by, text}, `actions`.
const items=[{name:'L1',idx:1,item_code:'ANVIL',item_name:'Anvil 5SC',uom:'Litre',whole:0,farm_block:'B12',block_code:'A12',qty:1.5,notes:'0,5 lít/ha',assignment:null,required:1.5,posted:0,draft:0,remaining:1.5,issues:[]},
 {name:'L2',idx:2,item_code:'ANVIL',item_name:'Anvil 5SC',uom:'Litre',whole:0,farm_block:'B13',block_code:'A13',qty:1.5,notes:'',assignment:null,required:1.5,posted:1,draft:0.5,remaining:0,issues:[]}]
const codes={pending:['Chờ duyệt','sent'],draft:['Nháp','draft'],approved:['Chờ cấp','waiting'],issuing:['Kho đang lập phiếu','picking'],closed:['Đã đóng','closed']}
const doc=(extra={})=>{const [state,state_code]=codes[extra.state||'pending'];return {name:'MR-1',modified:'m1',title:'Phun thuốc · Tổ 3 · A12, A13',overdue:false,docstatus:0,crew_name:'Đội A + B',team:'T3',team_name:'Tổ 3',work_type:'PHUN',work_name:'Phun thuốc',
 warehouse:'Kho vườn - L',needed:'2026-11-12',lines:2,open_lines:1,receiver:'EMP',receiver_name:'Nguyễn Văn Nhận',owner:'dt@x',owner_name:'Đội trưởng A',approver_name:'Đội trưởng A',approved_by_name:'',
 items,stock:{ANVIL:{item_code:'ANVIL',uom:'Litre',available:12,approved_waiting:5}},issues:[],history:[{at:'2026-11-11 08:00:00',by:'Đội trưởng A',text:'Gửi duyệt'}],warnings:[],
 actions:{},print_url:null,...extra,state,state_code}}

let calls=[],replies={}
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.split('/api/method/lotus_farm.issue_request.')[1]
 const call={method,query:Object.fromEntries(u.searchParams),body:opts.body?JSON.parse(opts.body):null}
 calls.push(call)
 if(!(method in replies))return {ok:false,status:417,json:async()=>({message:'Missing '+method})}
 return {ok:true,status:200,json:async()=>({message:typeof replies[method]==='function'?replies[method](call):replies[method]})}
}
const Detail=await load('components/field/MaterialRequestDetail.vue')
async function settle(){for(let i=0;i<10;i++)await tick()}
const button=(root,text)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(text))
const reasonDialog=()=>document.querySelector('dialog[open]')
async function answer(text){const box=reasonDialog().querySelector('textarea');box.value=text;box.dispatchEvent(new window.Event('input',{bubbles:true}));await settle();reasonDialog().querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await settle()}
let events=[]
function show(){calls=[];events=[];return mount({setup:()=>()=>h(Detail,{name:'MR-1',onChanged:d=>events.push(['changed',d]),onEdit:n=>events.push(['edit',n]),onCopy:n=>events.push(['copy',n]),onDeleted:n=>events.push(['deleted',n])})})}
const labels=root=>[...root.querySelectorAll('.issue-detail__actions button')].map(b=>b.textContent.trim())

test('each vật tư lists its lô: đề nghị, đã cấp, Kho đang lập phiếu, còn; stock is quantity only',async()=>{
 replies={detail:doc()}
 const view=show();await settle()
 const text=view.root.textContent
 assert.match(text,/Chờ duyệt/)
 assert.match(text,/Lô A12.*Đề nghị 1,5 · Đã cấp 0 · Còn 1,5/)
 assert.match(text,/Lô A13.*Đề nghị 1,5 · Đã cấp 1 · Kho đang lập phiếu 0,5 · Còn 0/)
 assert.match(text,/Kho còn 12 .*có thể cấp · đã duyệt chờ cấp cho yêu cầu khác 5/)
 assert.doesNotMatch(text,/₫|VND/,'no money for field staff')
 assert.match(text,/Gửi duyệt/,'history')
 view.unmount()
})

test('buttons follow the actions the server allows',async()=>{
 replies={detail:doc({actions:{approve:true,lower:true,return:true}})}
 let view=show();await settle()
 assert.deepEqual(labels(view.root),['Duyệt','Giảm số rồi duyệt','Trả lại'])
 view.unmount()
 replies={detail:doc({state:'draft',actions:{send:true,edit:true,delete:true}})}
 view=show();await settle()
 assert.deepEqual(labels(view.root),['Gửi duyệt','Sửa','Xóa nháp'])
 view.unmount()
 replies={detail:doc({state:'approved',actions:{close:true,cancel:true,copy:true}})}
 view=show();await settle()
 assert.deepEqual(labels(view.root),['Đóng phần còn lại','Hủy yêu cầu','Lập lại từ yêu cầu này'])
 assert.equal(view.root.querySelector('.issue-detail__print'),null,'no print link without print_url')
 view.unmount()
 replies={detail:doc({state:'closed',close_reason:'Kho hết hàng',actions:{reopen:true},print_url:'/lotus/in-de-xuat?name=MR-1'})}
 view=show();await settle()
 assert.deepEqual(labels(view.root),['Mở lại'])
 assert.match(view.root.textContent,/Lý do đóng: Kho hết hàng/)
 assert.equal(view.root.querySelector('.issue-detail__print').getAttribute('href'),'/lotus/in-de-xuat?name=MR-1')
 view.unmount()
})

test('approve asks once, then submits with modified and a client_event_id',async()=>{
 replies={detail:doc({actions:{approve:true}}),approve:()=>doc({state:'approved',modified:'m2',actions:{close:true}})}
 const view=show();await settle()
 button(view.root,'Duyệt').click();await settle()
 assert.match(view.root.querySelector('.lotus-delete-confirm').textContent,/Duyệt yêu cầu MR-1/)
 button(view.root.querySelector('.lotus-delete-confirm'),'Duyệt').click();await settle()
 const sent=calls.find(c=>c.method==='approve')
 assert.equal(sent.body.name,'MR-1');assert.equal(sent.body.modified,'m1');assert.ok(sent.body.client_event_id)
 assert.match(view.root.textContent,/Chờ cấp/)
 assert.equal(events[0][0],'changed')
 view.unmount()
})

test('lowering refuses an increase, needs a reason, sends only the changed lines',async()=>{
 replies={detail:doc({actions:{approve:true,lower:true}}),approve:()=>doc({state:'approved',modified:'m2'})}
 const view=show();await settle()
 button(view.root,'Giảm số rồi duyệt').click();await settle()
 const field=label=>document.getElementById([...view.root.querySelectorAll('label')].find(l=>l.textContent.includes(label))?.htmlFor)
 const set=(label,value)=>{const e=field(label);assert.ok(e,label);e.value=value;e.dispatchEvent(new window.Event('input',{bubbles:true}));e.dispatchEvent(new window.Event('change',{bubbles:true}))}
 set('Anvil 5SC · A12','3');await settle()
 button(view.root,'Duyệt với số mới').click();await settle()
 assert.match(view.root.querySelector('[role=alert]').textContent,/Muốn tăng số thì bấm Trả lại/)
 assert.equal(calls.filter(c=>c.method==='approve').length,0)
 set('Anvil 5SC · A12','1');await settle()
 button(view.root,'Duyệt với số mới').click();await settle()
 assert.match(view.root.querySelector('[role=alert]').textContent,/Ghi lý do giảm số/)
 set('Lý do giảm số','Lô A12 đã phun một phần');await settle()
 button(view.root,'Duyệt với số mới').click();await settle()
 const sent=calls.find(c=>c.method==='approve')
 assert.ok(sent);assert.deepEqual(sent.body.lines,[{name:'L1',qty:1}]);assert.equal(sent.body.reason,'Lô A12 đã phun một phần')
 view.unmount()
})

test('trả lại, đóng, mở lại and hủy ask a reason first; cancelling the reason sends nothing',async()=>{
 for(const [action,label,method] of [['return','Trả lại','return_request'],['close','Đóng phần còn lại','close'],['reopen','Mở lại','reopen'],['cancel','Hủy yêu cầu','cancel']]){
  replies={detail:doc({actions:{[action]:true}}),[method]:()=>doc({modified:'m2',actions:{}})}
  const view=show();await settle()
  button(view.root,label).click();await settle()
  assert.ok(reasonDialog(),label+' asks a reason')
  button(reasonDialog(),'Hủy').click();await settle()
  assert.equal(calls.filter(c=>c.method===method).length,0,label+' cancelled')
  button(view.root,label).click();await settle()
  await answer('Lý do '+label)
  const sent=calls.find(c=>c.method===method)
  assert.ok(sent,label);assert.equal(sent.body.reason,'Lý do '+label);assert.equal(sent.body.modified,'m1')
  view.unmount()
 }
})

test('a refused close names the draft issue that holds the quantity',async()=>{
 replies={detail:doc({state:'issuing',actions:{close:true}})}
 const view=show();await settle()
 button(view.root,'Đóng phần còn lại').click();await settle()
 const original=globalThis.fetch
 globalThis.fetch=async(url,opts)=>String(url).endsWith('.close')?{ok:false,status:417,json:async()=>({exc_type:'ValidationError',_server_messages:JSON.stringify([JSON.stringify({message:'Kho còn phiếu xuất nháp MAT-STE-0001 giữ số của yêu cầu.'})])})}:original(url,opts)
 try{await answer('Hết hàng');assert.match(view.root.querySelector('[role=alert]').textContent,/MAT-STE-0001/)}
 finally{globalThis.fetch=original;view.unmount()}
})

test('withdraw, edit, copy and delete',async()=>{
 replies={detail:doc({actions:{withdraw:true}}),withdraw:()=>doc({state:'draft',modified:'m2',actions:{edit:true,send:true,delete:true,copy:true}}),delete_draft:{deleted:'MR-1'}}
 const view=show();await settle()
 button(view.root,'Rút lại').click();await settle()
 assert.ok(calls.find(c=>c.method==='withdraw'))
 assert.deepEqual(labels(view.root),['Gửi duyệt','Sửa','Xóa nháp','Lập lại từ yêu cầu này'])
 button(view.root,'Sửa').click();button(view.root,'Lập lại').click();await settle()
 assert.deepEqual(events.filter(e=>e[0]!=='changed'),[['edit','MR-1'],['copy','MR-1']])
 button(view.root,'Xóa nháp').click();await settle()
 button(view.root.querySelector('.lotus-delete-confirm'),'Xóa nháp').click();await settle()
 assert.equal(calls.find(c=>c.method==='delete_draft').body.modified,'m2')
 assert.deepEqual(events.at(-1),['deleted','MR-1'])
 view.unmount()
})
