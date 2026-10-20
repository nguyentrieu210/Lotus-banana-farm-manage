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
const Proposal=await load('components/MobilePurchaseProposal.vue')
const P='lotus_farm.purchase_proposal.'
const signatures=state=>['Người đề xuất','Phụ trách bộ phận','Phòng Kế toán / Mua hàng','Giám đốc phê duyệt'].map((title,i)=>({action:'S'+i,title,name:i<state?'An':'',signed_at:i<state?'2026-10-20 07:31:00':'',image:''}))
const detail=(over={})=>({name:'MAT-MR-1',modified:'m1',docstatus:0,state:'Chờ phụ trách bộ phận',step:1,step_title:'Phụ trách bộ phận',proposer:'An',department:'Đội A',date:'2026-10-20',reason:'Chăm sóc vườn',warehouse:'KHO 1',
 items:[{name:'r1',item_name:'Ure',uom:'Tonne',qty:32,rate:0,amount:0,stock:null,schedule_date:'2026-10-22',lotus_specification:'',lotus_supplier_hint:'',lotus_purpose:'Bón khu A',lotus_notes:''}],
 total:0,signatures:signatures(1),can_sign:false,can_return:false,can_delete:false,edit:null,print_url:'/lotus/in-de-xuat?name=MAT-MR-1',...over})
const text=root=>root.textContent.replace(/\s+/g,' ')
const button=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(label))

test('the todo list shows proposals waiting for my signature and opens the four-step detail',async()=>{
 calls.length=0
 routes={[P+'proposals']:[{name:'MAT-MR-1',date:'2026-10-20',needed:'2026-10-22',state:'Chờ phụ trách bộ phận',proposer:'An',department:'Đội A',reason:'Chăm sóc vườn',total:0,lines:1,can_sign:true}],
  [P+'detail']:detail({can_sign:true,can_return:true})}
 const view=mount(Proposal,{company:'Lotus',today:'2026-10-20'});await tick()
 assert.equal(calls[0].args.view,'todo','opens on what waits for me')
 assert.match(text(view.root),/MAT-MR-1.*Chờ phụ trách bộ phận/)
 button(view.root,'MAT-MR-1').click();await tick()
 const steps=[...view.root.querySelectorAll('.lotus-signature-timeline__list li')]
 assert.equal(steps.length,4)
 assert.ok(steps[0].classList.contains('is-signed')&&steps[1].classList.contains('is-active'))
 assert.ok(button(view.root,'Ký xác nhận: Phụ trách bộ phận'))
 assert.ok(button(view.root,'Trả lại người đề xuất').disabled,'a return needs a reason')
 assert.equal(view.root.querySelector('a.pp-print').getAttribute('href'),'/lotus/in-de-xuat?name=MAT-MR-1')
 view.unmount()
})

const signerOptions={steps:[{key:'PROPOSE',title:'Người đề xuất'},{key:'DEPARTMENT',title:'Phụ trách bộ phận'},{key:'PURCHASING',title:'Phòng Kế toán / Mua hàng'},{key:'APPROVE',title:'Giám đốc phê duyệt'}],remembered:{},
 candidates:{DEPARTMENT:[{user:'binh@lotus',name:'Bình'}],PURCHASING:[{user:'chi@lotus',name:'Chi'}],APPROVE:[{user:'dung@lotus',name:'Dũng'}]}}

test('a new proposal repeats date and purpose on added lines, then saves and signs',async()=>{
 calls.length=0
 routes={[P+'proposals']:[],[P+'form_data']:{proposer:'An',department:'Đội A',warehouses:[{name:'KHO 1',warehouse_name:'KHO 1'}],items:[{name:'UREA',item_name:'Ure',stock_uom:'Tonne'}],conversions:[]},
  [P+'stock_on_hand']:{qty:4},[P+'signer_options']:signerOptions,[P+'save_proposal']:detail({state:'Nháp',step:0,signatures:signatures(0),modified:'m0'}),[P+'sign']:detail()}
 const view=mount(Proposal,{company:'Lotus',today:'2026-10-20'});await tick()
 button(view.root,'+ Lập đề xuất mua').click();await tick()
 const lines=()=>view.root.querySelectorAll('.pp-line')
 assert.equal(lines().length,1)
 const purpose=lines()[0].querySelectorAll('input')
 const field=[...purpose].find(i=>i.closest('.van-field,.lotus-mobile-input,label')&&i.getAttribute('maxlength')==='140'&&i.placeholder.startsWith('VD: Bón'))
 field.value='Bón khu A';field.dispatchEvent(new Event('input'));await tick()
 button(view.root,'+ Thêm vật tư').click();await tick()
 assert.equal(lines().length,2)
 const second=[...lines()[1].querySelectorAll('input')].find(i=>i.placeholder.startsWith('VD: Bón'))
 assert.equal(second.value,'Bón khu A','the next line copies the purpose')
 button(view.root,'Ký và gửi phụ trách bộ phận').click();await tick();await tick()
 assert.deepEqual(calls.filter(c=>c.method.startsWith(P)&&['save_proposal','sign'].includes(c.method.slice(P.length))).map(c=>c.method.slice(P.length)),['save_proposal','sign'])
 assert.equal(calls.find(c=>c.method===P+'sign').args.modified,'m0','signs the version just saved')
 assert.deepEqual(calls.find(c=>c.method===P+'sign').args.signers,{DEPARTMENT:'binh@lotus',PURCHASING:'chi@lotus',APPROVE:'dung@lotus'},'the only eligible person of each step is preselected')
 view.unmount()
})

test('accounting step edits prices only',async()=>{
 routes={[P+'proposals']:[{name:'MAT-MR-1',date:'2026-10-20',needed:'2026-10-22',state:'Chờ kế toán / mua hàng',proposer:'An',reason:'x',total:0,lines:1,can_sign:true}],
  [P+'detail']:detail({state:'Chờ kế toán / mua hàng',step:2,step_title:'Phòng Kế toán / Mua hàng',signatures:signatures(2),edit:'prices',can_sign:true}),
  [P+'form_data']:{proposer:'An',warehouses:[{name:'KHO 1'}],items:[{name:'UREA',item_name:'Ure',stock_uom:'Tonne'}],conversions:[]}}
 const view=mount(Proposal,{company:'Lotus',today:'2026-10-20'});await tick()
 button(view.root,'MAT-MR-1').click();await tick()
 button(view.root,'Cập nhật đơn giá').click();await tick()
 assert.match(text(view.root),/chỉ cập nhật đơn giá dự kiến/)
 assert.ok(!button(view.root,'+ Thêm vật tư'),'no new lines at this step')
 assert.ok(!button(view.root,'Ký và gửi phụ trách bộ phận'))
 view.unmount()
})
