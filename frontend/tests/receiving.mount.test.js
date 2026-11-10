import test from 'node:test'
import assert from 'node:assert/strict'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,mount,tick,h,ref,window} from './support/mount.mjs'

const DeliveryEvidence=await load('components/procurement/DeliveryEvidence.vue')
const ReceiptDetail=await load('components/procurement/ReceiptDetail.vue')
const settle=async(n=4)=>{for(let i=0;i<n;i++)await tick()}
const exact=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label)
const type=async(el,value)=>{el.value=value;el.dispatchEvent(new window.Event('input',{bubbles:true}));await tick()}
function pick(root,label,files){
 const input=[...root.querySelectorAll('input[type=file]')].find(i=>i.getAttribute('aria-label')===label)
 assert.ok(input,label)
 Object.defineProperty(input,'files',{value:files,configurable:true})
 input.dispatchEvent(new window.Event('change',{bubbles:true}))
}

test('receiving against an order needs the deliverer: a signature with a name, or the signed delivery note',async()=>{
 const handle=ref(null),states=[],uploads=[]
 const uploader=async file=>{uploads.push(file.name);return {file_url:'/private/files/'+file.name}}
 const view=mount({render:()=>h(DeliveryEvidence,{ref:handle,required:true,uploader,'onUpdate:valid':v=>states.push(v)})});await settle()
 assert.equal(states.at(-1),false,'nothing yet: the receipt cannot be confirmed')
 assert.match(view.root.querySelector('[role=status]').textContent,/Cần chữ ký kèm họ tên của người giao hàng, hoặc ảnh phiếu giao hàng có chữ ký/)
 await type(view.root.querySelector('input:not([type=file])'),'Trần Văn Giao')
 assert.equal(states.at(-1),false,'a name without a signature is not a confirmation')
 const note={name:'phieu-giao.jpg',type:'image/jpeg'},goods={name:'hang.jpg',type:'image/jpeg'}
 pick(view.root,'Ảnh phiếu giao hàng có chữ ký',[note]);await settle()
 assert.equal(states.at(-1),true,'the photographed delivery note is enough')
 pick(view.root,'Ảnh hàng, hóa đơn',[goods]);await settle()
 const first=await handle.value.collect()
 assert.deepEqual(first,{deliverer_name:'Trần Văn Giao',deliverer_signature:'',delivery_proof:'/private/files/phieu-giao.jpg',files:['/private/files/hang.jpg']})
 await handle.value.collect()
 assert.deepEqual(uploads,['phieu-giao.jpg','hang.jpg'],'a retry after a refusal does not upload the files again')
 assert.equal(handle.value.dirty(),true)
 view.unmount()
 // Not required (other companies, drafts by someone who cannot post): always valid.
 const free=mount(DeliveryEvidence,{required:false,'onUpdate:valid':v=>states.push(v)});await settle()
 assert.equal(states.at(-1),true)
 free.unmount()
})

const receipt=(over={})=>({name:'MAT-PRE-1',doctype:'Purchase Receipt',docstatus:1,state:'Đã nhập kho',billing:'Chưa có hóa đơn',supplier:'KN',supplier_name:'Kết Nông',
 date:'2026-11-10',currency:'VND',modified:'m1',goods_total:1000000,valuation_charges:20000,incoming_total:1020000,is_return:0,return_against:'',
 deliverer_name:'Trần Văn Giao',deliverer_signed:true,delivery_proof:'',needs_evidence:true,has_evidence:true,signed_by:'Thủ kho An',signed_at:'2026-11-10 09:15:00',
 signed_copy:{url:'/api/method/x',pdf_sha256:'a'},print_url:'/lotus/in-phieu?doctype=Purchase+Receipt&name=MAT-PRE-1',invoices:[],files:[],
 can_submit:false,can_cancel:true,can_delete:false,can_return:true,
 items:[{line:'L1',item:'UREA',item_name:'Ure Phú Mỹ',qty:10,returned_qty:2,uom:'Bao',warehouse:'KHO 1',order:'PUR-ORD-7'}],...over})
function harness(detail,answers={},props={}){
 const calls=[],asked=[],events=[]
 const callFn=async(method,args)=>{const name=method.split('.').slice(-2).join('.');calls.push({name,args});const a=answers[name];return typeof a==='function'?a(args):a}
 const view=mount(ReceiptDetail,{name:detail.name,today:'2026-11-10',ask:async text=>{asked.push(text);return true},callFn,
  onChanged:d=>events.push(['changed',d]),onDeleted:n=>events.push(['deleted',n]),onOpen:(row,kind)=>events.push(['open',row.name,kind]),
  onCredit:(d,r)=>events.push(['credit',r.name]),onInvoice:()=>events.push(['invoice']),onNotice:t=>events.push(['notice',t]),onError:t=>t&&events.push(['error',t]),...props})
 return {view,calls,asked,events}
}

test('a posted receipt shows who delivered and who signed; goods go back in one step with a reason',async()=>{
 const posted=receipt()
 const {view,calls,asked,events}=harness(posted,{'procurement.receipt':posted,'stock_attachments.files':[],
  'procurement.return_receipt':{name:'MAT-PRE-2',docstatus:1,needs_credit_note:true,return_against:'MAT-PRE-1'}},{canInvoice:true})
 await settle()
 assert.match(view.root.textContent,/Phiếu nhập theo đơn · Đã nhập kho · Kết Nông · 10\/11\/2026 · Chưa có hóa đơn/)
 assert.match(view.root.textContent,/Người giao hàng: Trần Văn Giao · đã ký trên màn hình/)
 assert.match(view.root.textContent,/Thủ kho Thủ kho An đã ký khi xác nhận nhập kho lúc 10\/11\/2026 09:15/)
 assert.equal([...view.root.querySelectorAll('a')].find(a=>a.textContent.trim()==='In phiếu').getAttribute('href'),posted.print_url)
 assert.ok([...view.root.querySelectorAll('a')].some(a=>a.textContent.trim()==='Tải bản PDF đã ký'))
 assert.equal(exact(view.root,'Xác nhận nhập kho'),undefined,'nothing left to confirm')
 exact(view.root,'Lập hóa đơn').click();await tick()
 assert.ok(events.some(e=>e[0]==='invoice'))
 exact(view.root,'Trả hàng').click();await tick()
 assert.ok(exact(view.root,'Xác nhận trả hàng').disabled,'a return needs a quantity and a reason')
 const qty=view.root.querySelector('.receipt-detail__return input')
 await type(qty,'9')
 assert.match(view.root.textContent,/Ure Phú Mỹ: trả tối đa 8 Bao/,'what was already returned cannot go back twice')
 await type(qty,'3')
 await type(view.root.querySelector('textarea'),'Bao rách, vón cục')
 exact(view.root,'Xác nhận trả hàng').click();await settle()
 const sent=calls.find(c=>c.name==='procurement.return_receipt').args
 assert.deepEqual([sent.name,sent.quantities,sent.post,sent.reason,sent.posting_date],['MAT-PRE-1',{L1:3},1,'Bao rách, vón cục','2026-11-10'])
 assert.match(events.find(e=>e[0]==='notice')[1],/Đã trả hàng, phiếu MAT-PRE-2\..*cần lập hóa đơn điều chỉnh/)
 assert.deepEqual(events.find(e=>e[0]==='credit'),['credit','MAT-PRE-2'])
 // Cancelling says why.
 exact(view.root,'Hủy phiếu').click();await tick()
 assert.ok(exact(view.root,'Hủy phiếu và đảo sổ kho').disabled)
 await type(view.root.querySelector('textarea'),'Nhập nhầm đơn')
 exact(view.root,'Hủy phiếu và đảo sổ kho').click();await settle()
 const cancelled=calls.find(c=>c.name==='warehouse_planning.receipt_action').args
 assert.deepEqual([cancelled.action,cancelled.reason,cancelled.modified],['cancel','Nhập nhầm đơn','m1'])
 assert.match(asked.at(-1),/Hủy phiếu MAT-PRE-1 và đảo sổ kho/)
 view.unmount()
})

test('a draft receipt is not confirmed without the deliverer; confirming is the storekeeper signing',async()=>{
 const draft=receipt({docstatus:0,state:'Nháp',billing:'',deliverer_name:'',deliverer_signed:false,has_evidence:false,signed_by:'',signed_at:'',signed_copy:null,
  can_submit:true,can_cancel:false,can_delete:true,can_return:false})
 const uploader=async file=>({file_url:'/private/files/'+file.name})
 const {view,calls,asked,events}=harness(draft,{'procurement.receipt':draft,'stock_attachments.files':[],'warehouse_planning.receipt_action':{}},{uploader})
 await settle()
 assert.match(view.root.textContent,/Chưa có xác nhận của người giao hàng/)
 assert.ok(exact(view.root,'Xác nhận nhập kho').disabled)
 pick(view.root,'Ảnh phiếu giao hàng có chữ ký',[{name:'phieu.jpg',type:'image/jpeg'}]);await settle()
 assert.equal(exact(view.root,'Xác nhận nhập kho').disabled,false)
 exact(view.root,'Xác nhận nhập kho').click();await settle()
 assert.match(asked[0],/Xác nhận nhập kho MAT-PRE-1\? Xác nhận này là chữ ký của bạn trên phiếu nhập/)
 const sent=calls.find(c=>c.name==='warehouse_planning.receipt_action').args
 assert.deepEqual([sent.action,sent.delivery_proof,sent.deliverer_signature],['submit','/private/files/phieu.jpg',''])
 exact(view.root,'Xóa nháp').click();await settle()
 assert.deepEqual(events.find(e=>e[0]==='deleted'),['deleted','MAT-PRE-1'])
 view.unmount()
})
