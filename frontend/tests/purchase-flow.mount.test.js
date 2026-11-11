import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,window} from './support/mount.mjs'
const Progress=await load('components/PurchaseProgress.vue')
const Form=await load('components/ProcurementDocumentForm.vue')
const Mobile=await load('components/MobilePurchaseProposal.vue')
const Workspace=await load('components/ProcurementWorkspace.vue')

test('purchase progress opens native chain documents inside the workspace',async()=>{
 let opened
 const view=mount(Progress,{navigate:true,progress:{stage:'Đang mua',lines:[],orders:[{name:'PO-1',docstatus:1}],payments:[{name:'PAY-1',docstatus:0,amount:100}],outstanding_amount:200},onOpen:(row,type)=>{opened={row,type}}})
 await tick()
 const order=[...view.root.querySelectorAll('a')].find(a=>a.textContent.includes('PO-1'))
 assert.ok(order)
 order.click();await tick()
 assert.deepEqual(opened,{row:{name:'PO-1',docstatus:1},type:'orders'})
 assert.match(view.root.textContent,/Đang mua/)
 assert.match(view.root.textContent,/Còn nợ/)
 assert.match(view.root.textContent,/PAY-1/)
 view.unmount()
})

test('independent proposal form exposes department, reason, stock and expected price without a work plan',async()=>{
 const view=mount(Form,{type:'need',catalog:{items:[],warehouses:[],conversions:[]},modelValue:{department:'Kho',notes:'Mua dự trữ',warehouse:'',expected_date:'2026-11-07',items:[{item:'',qty:2,rate:0,uom:''}]}})
 await tick()
 assert.match(view.root.textContent,/Bộ phận đề xuất/)
 assert.ok(view.root.querySelector('[aria-label="Giá dự kiến dòng 1"]'))
 assert.ok(view.root.querySelector('[aria-label="Tồn tham khảo dòng 1"]'))
 assert.equal(view.root.querySelector('[aria-label*="công việc"]'),null)
 view.unmount()
})

test('mobile proposals filter purchasing progress independently of signature state',async()=>{
 const previous=globalThis.fetch
 globalThis.fetch=async()=>({ok:true,json:async()=>({message:{rows:[{name:'MR-DRAFT',state:'Nháp',stage:'Nháp'},
  {name:'MR-ORDERED',state:'Đã duyệt',stage:'Đang mua'}],counts:{'Nháp':1,'Đang mua':1}}})})
 const view=mount(Mobile,{company:'C'})
 try {
  await tick();await tick()
  ;[...view.root.querySelectorAll('[role=tab]')].find(b=>b.textContent==='Tất cả').click()
  await tick();await tick()
  const select=view.root.querySelector('select[aria-label="Giai đoạn"]')
  assert.ok(select)
  assert.match(select.textContent,/Đang mua \(1\)/,'each stage shows its count')
  select.value='Đang mua';select.dispatchEvent(new window.Event('change',{bubbles:true}))
  await tick()
  assert.match(view.root.textContent,/MR-ORDERED/)
  assert.doesNotMatch(view.root.textContent,/MR-DRAFT/)
 } finally {view.unmount();globalThis.fetch=previous}
})

test('editing a proposal preserves each existing line needed date',async()=>{
 const previous=globalThis.fetch
 let saved
 const items=[{name:'L1',item_code:'I1',item_name:'Vật tư 1',qty:1,uom:'Kg',rate:0,warehouse:'WH',schedule_date:'2026-11-08'},
  {name:'L2',item_code:'I2',item_name:'Vật tư 2',qty:1,uom:'Kg',rate:0,warehouse:'WH',schedule_date:'2026-11-15'}]
 const detail={name:'MR',company:'C',modified:'v1',docstatus:0,state:'Nháp',edit:'all',reason:'Mua dự trữ',department:'Kho',warehouse:'WH',items,signatures:[],signers:{},progress:{lines:[]}}
 globalThis.fetch=async(url,opts={})=>{
  const u=new URL(url,'http://localhost'),method=u.pathname.split('/').pop(),args=opts.body?JSON.parse(opts.body):Object.fromEntries(u.searchParams)
  let message=[]
  if(method.endsWith('procurement.bootstrap'))message=args.company?{can_need:true,items:items.map(r=>({name:r.item_code,item_name:r.item_name,stock_uom:'Kg'})),warehouses:[{name:'WH'}],suppliers:[],conversions:[],requests:[],farms:[]}:{companies:[{name:'C'}],today:'2026-11-07'}
  if(method.endsWith('.needs'))message=[{name:'MR',status:'Nháp'}]
  if(method.endsWith('purchase_proposal.detail'))message=detail
  if(method.endsWith('.signer_options'))message={steps:[],candidates:{}}
  if(method.endsWith('.stock_on_hand'))message={qty:10}
  if(method.endsWith('.save_proposal')){saved=args.values;message=detail}
  return {ok:true,status:200,json:async()=>({message})}
 }
 const view=mount(Workspace,{company:'C',buyingView:'needs',mobile:true,embedded:true,today:'2026-11-07'})
 const click=async text=>{const button=[...window.document.querySelectorAll('button')].find(b=>b.textContent.trim()===text);assert.ok(button,text+' '+window.document.body.textContent);button.click();await tick();await tick()}
 try {
  await tick();await tick()
  const row=[...view.root.querySelectorAll('.van-cell')].find(cell=>cell.textContent.includes('MR'))
  row.click();await tick();await tick()
  await click('Sửa đề xuất')
  await click('Lưu nháp đề xuất')
  assert.deepEqual(saved.items.map(r=>r.schedule_date),['2026-11-08','2026-11-15'])
 } finally {view.unmount();globalThis.fetch=previous}
})

test('proposal return requires a reason and calls the shared signing workflow',async()=>{
 const previous=globalThis.fetch
 let returned
 let detail={name:'MR',company:'C',modified:'v1',docstatus:0,state:'Chờ phụ trách bộ phận',stage:'Đang ký',step:1,can_return:true,can_sign:false,items:[],signatures:[],progress:{lines:[]}}
 globalThis.fetch=async(url,opts={})=>{
  const u=new URL(url,'http://localhost'),method=u.pathname.split('/').pop(),args=opts.body?JSON.parse(opts.body):Object.fromEntries(u.searchParams)
  let message=[]
  if(method.endsWith('procurement.bootstrap'))message=args.company?{items:[],suppliers:[],warehouses:[],conversions:[],farms:[]}:{companies:[{name:'C'}]}
  if(method.endsWith('.needs'))message=[{name:'MR',status:'Chờ ký'}]
  if(method.endsWith('.signer_options'))message={steps:[],candidates:{}}
  if(method.endsWith('.return_proposal')){returned=args;detail={...detail,state:'Trả lại',can_return:false};message=detail}
  if(method.endsWith('purchase_proposal.detail'))message=detail
  return {ok:true,status:200,json:async()=>({message})}
 }
 const view=mount(Workspace,{company:'C',buyingView:'needs',mobile:true,embedded:true})
 try {
  await tick();await tick()
  const row=[...view.root.querySelectorAll('.van-cell')].find(cell=>cell.textContent.includes('MR'))
  row.click();await tick();await tick()
  const find=text=>[...window.document.querySelectorAll('button')].find(b=>b.textContent.trim()===text)
  find('Trả lại').click();await tick()
  assert.ok(find('Trả lại người đề xuất').disabled,'a return needs a reason')
  const reason=window.document.querySelector('textarea')
  reason.value='Kiểm tra lại số lượng';reason.dispatchEvent(new window.Event('input',{bubbles:true}));await tick()
  assert.equal(find('Trả lại người đề xuất').disabled,false)
  find('Trả lại người đề xuất').click();await tick();await tick()
  assert.equal(returned.reason,'Kiểm tra lại số lượng')
  assert.equal(returned.name,'MR')
 } finally {view.unmount();globalThis.fetch=previous}
})
