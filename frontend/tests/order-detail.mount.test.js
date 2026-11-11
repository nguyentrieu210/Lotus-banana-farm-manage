import test from 'node:test'
import assert from 'node:assert/strict'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,mount,tick} from './support/mount.mjs'
import {purchaseFromRequest,purchaseDraftFromOrder,newPurchaseDraft} from '../src/mobile-purchase.js'

const OrderDetail=await load('components/procurement/OrderDetail.vue')
const CompareCards=await load('components/procurement/CompareCards.vue')
const settle=async(n=4)=>{for(let i=0;i<n;i++)await tick()}
const exact=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label)
const type=async(el,value)=>{el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));await tick()}
const order=(over={})=>({name:'PUR-ORD-7',company:'C',modified:'m1',docstatus:0,status:'Nháp',supplier:'KN',supplier_name:'Kết Nông',amount:12600000,currency:'VND',
 expected_date:'2026-11-20',items:[],warnings:[],print_url:'/lotus/in-don-mua?name=PUR-ORD-7',...over})
function harness(detail,answers={}){
 const calls=[],asked=[],events=[]
 const callFn=async(method,args)=>{const name=method.split('.').pop();calls.push({name,args});const a=answers[name];return typeof a==='function'?a(args):a}
 const view=mount(OrderDetail,{detail,chain:null,company:'C',ask:async text=>{asked.push(text);return true},callFn,
  onChanged:(d,c)=>events.push(['changed',d,c]),onDeleted:n=>events.push(['deleted',n]),onEdit:()=>events.push(['edit']),onReceive:()=>events.push(['receive']),
  onNotice:t=>events.push(['notice',t]),onError:t=>t&&events.push(['error',t])})
 return {view,calls,asked,events}
}

test('a draft shows lines approval would refuse and cannot be sent until they are fixed',async()=>{
 const warnings=[{line:2,item:'Vôi bột',code:'no_source',message:'Dòng 2 (Vôi bột): không lấy từ đề xuất mua đã duyệt. Hàng đã mua lẻ dùng Mua nhanh.'}]
 const {view,events}=harness(order({can_write:true,can_request_approval:true,can_delete:true,warnings}),{approver_options:{steps:[{key:'PREPARE'},{key:'APPROVE',title:'Người duyệt mua'}],candidates:{APPROVE:[{user:'gd@lotus',name:'Giám đốc'}]}}})
 await settle()
 assert.match(view.root.querySelector('[role=alert]').textContent,/Dòng 2 \(Vôi bột\): không lấy từ đề xuất mua đã duyệt/)
 assert.ok(exact(view.root,'Gửi duyệt đơn').disabled,'blocking lines stop the send')
 exact(view.root,'Sửa đơn').click();await tick()
 assert.deepEqual(events.at(-1),['edit'])
 assert.equal([...view.root.querySelectorAll('a')].find(a=>a.textContent.trim()==='In đơn mua').getAttribute('href'),'/lotus/in-don-mua?name=PUR-ORD-7')
 view.unmount()
})

test('the approver signs after a confirmation, or returns the order with a reason',async()=>{
 const pending=order({status:'Chờ duyệt',can_approve:true,signing:{steps:[{key:'PREPARE',title:'Người lập đơn',state:'Đã ký',name:'An'},{key:'APPROVE',title:'Người duyệt mua',state:'Chờ ký',name:'Giám đốc'}]}})
 const approved=order({docstatus:1,status:'Đã duyệt',can_manage:true,signed_copy:{url:'/api/method/x',pdf_sha256:'a'}})
 const {view,calls,asked,events}=harness(pending,{approve_order:{},reject_order:{},detail:approved,chain:{progress:[]}})
 await settle()
 exact(view.root,'Trả lại').click();await tick()
 assert.ok(exact(view.root,'Trả lại đơn').disabled,'a return needs a reason')
 await type(view.root.querySelector('textarea'),'Giá cao hơn báo giá')
 exact(view.root,'Trả lại đơn').click();await settle()
 assert.deepEqual(calls.find(c=>c.name==='reject_order').args,{name:'PUR-ORD-7',modified:'m1',reason:'Giá cao hơn báo giá'})
 exact(view.root,'Duyệt đơn').click();await settle()
 assert.match(asked[0],/Đơn mua hàng · PUR-ORD-7 · 12\.600\.000 đ · bước Người duyệt mua/)
 assert.ok(calls.some(c=>c.name==='approve_order'))
 assert.equal(events.filter(e=>e[0]==='changed').at(-1)[1].status,'Đã duyệt','the fresh detail is handed to the host')
 view.unmount()
})

test('an approved order is sent, rescheduled, closed or cancelled with reasons',async()=>{
 const approved=order({docstatus:1,status:'Đã duyệt',overdue:true,can_manage:true,can_close:true,can_cancel:true,can_receive:true})
 const {view,calls,asked,events}=harness(approved,{mark_order_sent:{},cancel_order:{},detail:approved,chain:{progress:[]}})
 await settle()
 assert.match(view.root.textContent,/Đã duyệt · quá hẹn giao/,'late delivery is a flag beside the status')
 exact(view.root,'Đã gửi NCC').click();await settle()
 assert.ok(calls.some(c=>c.name==='mark_order_sent'))
 exact(view.root,'Nhận / nghiệm thu từng phần').click();await tick()
 assert.ok(events.some(e=>e[0]==='receive'))
 exact(view.root,'Hủy đơn').click();await tick()
 assert.ok(exact(view.root,'Hủy đơn mua').disabled)
 await type(view.root.querySelector('textarea'),'NCC không giao được')
 exact(view.root,'Hủy đơn mua').click();await settle()
 assert.match(asked.at(-1),/Hủy đơn PUR-ORD-7.*Chờ mua/)
 assert.equal(calls.find(c=>c.name==='cancel_order').args.reason,'NCC không giao được')
 view.unmount()
})

test('phone comparison: one card per item, a dearer choice asks why',async()=>{
 const rows=[{key:'L1',item:'UREA',item_name:'Ure Phú Mỹ',stock_uom:'Kg',request:'MR-1',need_qty:1000,approved:true,
  offers:[{line:'Q1-1',supplier:'KN',unit_cost:12600,docstatus:1},{line:'Q2-1',supplier:'NN',unit_cost:12000,docstatus:0}]}]
 let choices={L1:'Q2-1'},reasons={}
 const props=()=>({rows,suppliers:[{name:'KN',label:'Kết Nông'},{name:'NN',label:'Nguyễn Ngọc'}],choices,reasons,'onUpdate:choices':v=>{choices=v},'onUpdate:reasons':v=>{reasons=v}})
 let view=mount(CompareCards,props());await settle()
 const offers=[...view.root.querySelectorAll('button.compare-card__offer')]
 assert.deepEqual(offers.map(b=>b.getAttribute('aria-pressed')),['true','false'],'cheapest first, the chosen one pressed')
 assert.match(offers[0].textContent,/Nguyễn Ngọc.*rẻ nhất.*báo giá nháp/)
 assert.equal(view.root.querySelector('input'),null,'the cheapest needs no reason')
 offers[1].click();await tick()
 assert.deepEqual(choices,{L1:'Q1-1'})
 view.unmount()
 view=mount(CompareCards,props());await settle()
 assert.ok(view.root.querySelector('[aria-label="Lý do chọn Ure Phú Mỹ"]'),'a dearer pick asks why')
 view.unmount()
})

test('an order from a proposal keeps the chosen supplier, price and quote link; editing keeps every line field',()=>{
 const request={name:'MR-1',supplier:'',suppliers:['KN','NN'],items:[
  {item:'UREA',qty:10,uom:'Bao',rate:120000,warehouse:'KHO 1',supplier:'KN',vat_code:'5',freight:50000,supplier_quotation:'SQ-1',supplier_quotation_item:'Q1-1',reason:'Giá thấp nhất',material_request:'MR-1',material_request_item:'L1'},
  {item:'VOI',qty:5,uom:'Kg',rate:9000,warehouse:'KHO 1',supplier:'NN',material_request:'MR-1',material_request_item:'L2'},
  {item:'DAP',qty:2,uom:'Bao',rate:0,warehouse:'KHO 1',material_request:'MR-1',material_request_item:'L3'}]}
 const draft=purchaseFromRequest(newPurchaseDraft('KHO 1','2026-11-10'),request)
 assert.equal(draft.supplier,'KN','the first chosen supplier')
 assert.deepEqual(draft.other_suppliers,['NN'],'lines chosen for another supplier get their own order')
 assert.deepEqual(draft.items.map(r=>[r.item,r.rate,r.vat_code,r.supplier_quotation]),[['UREA',120000,'5','SQ-1'],['DAP','','KCT','']])
 const again=purchaseDraftFromOrder({name:'PO-1',modified:'m',supplier:'KN',mode:'Kho tự mua',expected_date:'2026-11-20',notes:'',
  items:[{item:'UREA',qty:10,rate:120000,uom:'Bao',warehouse:'KHO 1',kind:'Material',vat_code:'5',freight:50000,supplier_quotation:'SQ-1',supplier_quotation_item:'Q1-1',material_request:'MR-1',material_request_item:'L1'}]})
 assert.deepEqual([again.name,again.items[0].vat_code,again.items[0].freight,again.items[0].supplier_quotation,again.items[0].material_request_item],['PO-1','5',50000,'SQ-1','L1'])
})
