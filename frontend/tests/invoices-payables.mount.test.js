import test from 'node:test'
import assert from 'node:assert/strict'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,mount,tick,window,document} from './support/mount.mjs'

const InvoiceForm=await load('components/procurement/InvoiceForm.vue')
const InvoiceQueue=await load('components/procurement/InvoiceQueue.vue')
const InvoiceDetail=await load('components/procurement/InvoiceDetail.vue')
const PayablesView=await load('components/procurement/PayablesView.vue')
const VoucherDetail=await load('components/procurement/VoucherDetail.vue')
const settle=async(n=5)=>{for(let i=0;i<n;i++)await tick()}
const exact=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label)
const type=async(el,value)=>{el.value=value;el.dispatchEvent(new window.Event('input',{bubbles:true}));await tick()}
const field=(root,text)=>{const label=[...root.querySelectorAll('label')].find(l=>l.textContent.trim().startsWith(text));assert.ok(label,text);return document.getElementById(label.getAttribute('for'))}
function server(answers){
 const calls=[]
 const callFn=async(method,args)=>{const name=method.replace('lotus_farm.','');calls.push({name,args});const a=answers[name];if(a===undefined)throw new Error('no answer for '+name);return typeof a==='function'?a(args):a}
 return {calls,callFn}
}
const source={supplier:'KN',supplier_name:'Kết Nông',vat_in_cost:true,mua_nhanh:false,files:[{name:'F1',file_name:'hoa-don.jpg',file_url:'/private/files/hoa-don.jpg',attached_to_name:'MAT-PRE-1'}],
 lines:[{source_doctype:'Purchase Receipt',source_name:'MAT-PRE-1',source_item:'L1',item:'UREA',item_name:'Ure Phú Mỹ',qty:10,received_qty:10,uom:'Bao',rate:100000,order_rate:100000,vat_code:'5',freight:0,order:'PUR-ORD-7',fixed:false}]}

test('the invoice is typed by hand beside the original file; another price needs a reason; the printed total must agree',async()=>{
 const {calls,callFn}=server({'finance.supplier_invoice.source':source,'finance.supplier_invoice.create':{invoice:'ACC-PINV-1',amount:1155000,rounding_adjustment:0,warnings:[]}})
 const made=[]
 const view=mount(InvoiceForm,{modelValue:true,receipts:['MAT-PRE-1'],today:'2026-11-10',callFn,onCreated:r=>made.push(r),'onUpdate:modelValue':()=>{}});await settle()
 const form=document.body.querySelector('dialog[open] form')
 // The prefill is a read (URL parameters): the list goes as JSON, never as "A,B" (seen on the live-site copy, 10/11/2026).
 assert.equal(calls.find(c=>c.name==='finance.supplier_invoice.source').args.receipts,'["MAT-PRE-1"]')
 assert.ok(form.querySelector('aside img[alt="File gốc hoa-don.jpg"]'),'the original file is shown next to the form')
 assert.match(form.textContent,/hệ thống không đọc số từ file/)
 assert.match(form.textContent,/Hộ kinh doanh: thuế GTGT tính vào giá vốn/)
 const submit=[...form.querySelectorAll('button')].find(b=>b.textContent.trim()==='Ghi hóa đơn')
 assert.ok(submit.disabled);assert.match(form.textContent,/Nhập số hóa đơn\./)
 await type(field(form,'Số hóa đơn'),'0001234')
 await type(field(form,'Đơn giá theo hóa đơn'),'110000');await settle(2)
 assert.match(form.textContent,/đơn giá khác phiếu nhận, ghi lý do chênh lệch/)
 await type(field(form,'Lý do đơn giá khác phiếu nhận'),'NCC tăng giá theo thông báo');await settle(2)
 await type(field(form,'Tổng thanh toán in trên hóa đơn'),'1200000');await settle(2)
 assert.match(form.textContent,/Tổng các dòng lệch tổng in 45\.000 đ \(cho phép 1 đ\)/)
 await type(field(form,'Tổng thanh toán in trên hóa đơn'),'1155000');await settle(2)
 assert.equal(submit.disabled,false)
 form.dispatchEvent(new window.Event('submit',{cancelable:true}));await settle()
 const sent=calls.find(c=>c.name==='finance.supplier_invoice.create').args
 assert.deepEqual([sent.receipts,sent.bill_no,sent.printed_total,sent.lines],[['MAT-PRE-1'],'0001234',1155000,
  [{source_item:'L1',qty:10,rate:110000,vat_code:'5',variance_reason:'NCC tăng giá theo thông báo'}]])
 assert.equal(made[0].invoice,'ACC-PINV-1')
 view.unmount()
})

// Third review: a December receipt at 8 % invoiced in January 2027 takes 10 % in the form too (the server already does),
// so the preview and the printed-total check agree with what is posted; a rate picked by hand stays.
test('a receipt line whose rate ended before the invoice date takes the rate that followed',async()=>{
 const ending={...source,vat_ends:{'8':{to:'2026-12-31',then:'10'}},lines:[{...source.lines[0],vat_code:'8'}]}
 const {calls,callFn}=server({'finance.supplier_invoice.source':ending,'finance.supplier_invoice.create':{invoice:'ACC-PINV-2',amount:1100000,rounding_adjustment:0,warnings:[]}})
 const view=mount(InvoiceForm,{modelValue:true,receipts:['MAT-PRE-1'],today:'2026-12-30',callFn,'onUpdate:modelValue':()=>{}});await settle()
 try{
  const form=document.body.querySelector('dialog[open] form')
  await type(field(form,'Số hóa đơn'),'0009');await type(field(form,'Tổng thanh toán in trên hóa đơn'),'1100000');await settle(2)
  assert.match(form.textContent,/Tổng các dòng lệch tổng in 20\.000 đ/,'on 30/12/2026 the line is still at 8 %')
  await type(field(form,'Ngày hóa đơn'),'05/01/2027');await settle(2)  // the date field takes dd/mm/yyyy
  const submit=[...form.querySelectorAll('button')].find(b=>b.textContent.trim()==='Ghi hóa đơn')
  assert.equal(submit.disabled,false,'at 10 % the lines match the printed total')
  form.dispatchEvent(new window.Event('submit',{cancelable:true}));await settle()
  assert.equal(calls.find(c=>c.name==='finance.supplier_invoice.create').args.lines[0].vat_code,'10')
 }finally{view.unmount()}
})

test('receipts waiting for an invoice: one supplier and one kind per invoice; a posted invoice is cancelled with a reason',async()=>{
 const rows=[{doctype:'Purchase Receipt',name:'MAT-PRE-1',supplier:'KN',supplier_name:'Kết Nông',date:'2026-11-09',amount:1050000,mua_nhanh:false,source_type:'Nhận theo đơn',lines:[{item_name:'Ure'}],files:[]},
  {doctype:'Stock Entry',name:'MAT-STE-9',supplier:'KN',supplier_name:'Kết Nông',date:'2026-11-10',amount:200000,mua_nhanh:true,source_type:'Mua nhanh',lines:[{item_name:'Vôi'}],files:[{name:'F2',file_name:'hd.pdf',file_url:'/private/files/hd.pdf'}]}]
 const queue=server({'finance.supplier_invoice.queue':{rows,total:2,amount:1250000},'finance.supplier_invoice.source':source})
 const view=mount(InvoiceQueue,{company:'C',today:'2026-11-10',canPost:true,suppliers:[{value:'KN',label:'Kết Nông'}],callFn:queue.callFn});await settle()
 assert.match(view.root.textContent,/2 phiếu nhập chưa có hóa đơn đủ · tạm tính 1\.250\.000 đ/)
 assert.match(view.root.textContent,/Mua nhanh/)
 const boxes=[...view.root.querySelectorAll('[role=checkbox]')]
 boxes[0].click();await settle(2);boxes[1].click();await settle(2)
 assert.match(view.root.textContent,/Chọn riêng phiếu nhận theo đơn và phiếu Mua nhanh/)
 assert.ok(exact(view.root,'Nhập hóa đơn cho 2 phiếu đã chọn').disabled)
 view.unmount()
 const posted={name:'ACC-PINV-1',doctype:'Purchase Invoice',supplier:'KN',supplier_name:'Kết Nông',bill_no:'0001234',series:'1C26TKN',bill_date:'2026-11-10',due_date:'2026-11-25',docstatus:1,modified:'m1',currency:'VND',
  net:1100000,amount:1155000,outstanding_amount:1155000,printed_total:1155000,rounding_adjustment:0,status:'Chưa trả',taxes:[{description:'Thuế GTGT theo dòng',amount:55000}],settlements:[],receipts:['MAT-PRE-1'],quick_receipts:[],
  files:[{name:'F1',file_name:'hang-1.png',file_url:'/private/files/hang-1.png',attached_to_name:'MAT-PRE-1'},{name:'F2',file_name:'phieu-giao.png',file_url:'/private/files/phieu-giao.png',attached_to_name:'MAT-PRE-1'}],
  cost_adjustments:[{name:'MAT-LCV-1',kind:'cost',amount:100000,description:'Chênh lệch giá theo hóa đơn 0001234 (ACC-PINV-1)'},
   {name:'ACC-JV-1',kind:'vat',amount:-5000,description:''},{name:'ACC-JV-2',kind:'expense',amount:7000,description:''}],
  print_url:'/lotus/in-hoa-don?name=ACC-PINV-1',can_cancel:true,can_pay:true,can_credit:true,items:[{line:'I1',item_name:'Ure Phú Mỹ',qty:10,uom:'Bao',rate:110000,amount:1100000,vat_code:'5',variance_reason:'NCC tăng giá',receipt:'MAT-PRE-1'}]}
 const detail=server({'finance.supplier_invoice.detail':posted,'finance.supplier_invoice.cancel':{},'stock_attachments.files':[]})
 const asked=[],events=[]
 const page=mount(InvoiceDetail,{name:'ACC-PINV-1',ask:async t=>{asked.push(t);return true},callFn:detail.callFn,onPay:d=>events.push(['pay',d.name]),onNotice:t=>events.push(['notice',t]),onError:t=>t&&events.push(['error',t])});await settle()
 assert.match(page.root.textContent,/Hóa đơn nhà cung cấp · Chưa trả · Kết Nông · 1C26TKN · 0001234/)
 assert.match(page.root.textContent,/Lý do chênh lệch giá: NCC tăng giá/)
 // Receipt files are told apart (they ran together on the live-site copy, 10/11/2026); the cost adjustment is named.
 assert.match(page.root.textContent,/File ở phiếu nhận: hang-1\.png · phieu-giao\.png/)
 // Second review: each adjustment says what it did, with its sign (a VAT transfer is not a cost of the goods).
 const said=page.root.textContent.replace(/\s+/g,' ')
 assert.match(said,/Chênh lệch vào giá vốn hàng nhập: tăng 100\.000[^(]*\(MAT-LCV-1\) · Chênh lệch giá theo hóa đơn 0001234 \(ACC-PINV-1\)/)
 assert.match(said,/Thuế GTGT chênh chuyển từ 33881 về 3388 \(giá vốn không đổi\): 5\.000[^(]*\(ACC-JV-1\)/)
 assert.match(said,/Chênh lệch ghi vào chi phí kỳ này \(kỳ của phiếu nhận đã khóa, hoặc tài sản cố định\): tăng 7\.000[^(]*\(ACC-JV-2\)/)
 exact(page.root,'Trả tiền hóa đơn').click();await tick()
 assert.deepEqual(events[0],['pay','ACC-PINV-1'])
 exact(page.root,'Hủy hóa đơn').click();await tick()
 // The reason form sits above the action row: its button comes first.
 const confirm=[...page.root.querySelectorAll('button')].filter(b=>b.textContent.trim()==='Hủy hóa đơn').at(0)
 assert.ok(confirm.disabled,'cancelling needs a reason')
 await type(page.root.querySelector('textarea'),'Nhập nhầm nhà cung cấp');confirm.click();await settle()
 assert.deepEqual(detail.calls.find(c=>c.name==='finance.supplier_invoice.cancel').args,{name:'ACC-PINV-1',reason:'Nhập nhầm nhà cung cấp',modified:'m1'})
 assert.match(asked[0],/Hủy hóa đơn ACC-PINV-1/)
 page.unmount()
})

test('payables on a closing date lead to one payment voucher; signing a voucher asks first',async()=>{
 const payables={as_of:'2026-11-10',rows:[{name:'ACC-PINV-1',supplier:'KN',supplier_name:'Kết Nông',bill_no:'0001234',due_date:'2026-11-15',balance:1155000,due_soon:true}],
  owed:1655000,advance:100000,net:1555000,overdue:500000,due_7d:1155000,unbilled:-20000,unbilled_waiting:200000,unbilled_claims:220000,unbilled_ledger:-20000,unbilled_matches:true,ledger_balance:1555000,ledger_matches:true,
  aging:{current:1155000,d1_30:0,d31_60:500000,d61_90:0,d90_plus:0,no_due:0},aging_labels:{current:'Chưa đến hạn',d31_60:'Quá hạn 31–60 ngày'},
  suppliers:[{supplier:'KN',supplier_name:'Kết Nông',invoiced:1655000,advance:100000,net:1555000,due_7d:1155000,unbilled:200000,claim:220000,aging:{current:1155000,d31_60:500000}}]}
 const items={supplier:'KN',supplier_name:'Kết Nông',owed:1655000,items:[{doctype:'Purchase Invoice',name:'ACC-PINV-1',label:'0001234',date:'2026-11-10',due_date:'2026-11-15',total:1155000,outstanding:1155000,payable:1155000,waiting:0}]}
 const signers={steps:[{key:'PREPARE',title:'Kế toán lập phiếu'},{key:'CHIEF',title:'Kế toán trưởng'},{key:'APPROVE',title:'Giám đốc duyệt chi'}],candidates:{CHIEF:[{user:'ktt@lotus',name:'Kế toán trưởng'}],APPROVE:[{user:'gd@lotus',name:'Giám đốc'}]}}
 const {calls,callFn}=server({'procurement_queries.payables':payables,'finance.supplier_payment.open_items':items,'signing.candidates':signers,
  'finance.supplier_payment.prepare':{voucher:'ACC-PAY-1',doctype:'Payment Entry'}})
 const notices=[]
 const view=mount(PayablesView,{company:'C',today:'2026-11-10',canPay:true,suppliers:[],callFn,onNotice:t=>notices.push(t),onError:()=>{}});await settle()
 for(const text of [/Phải trả\s*1\.655\.000 đ/,/Trong đó quá hạn\s*500\.000 đ/,/Đến hạn trong 7 ngày\s*1\.155\.000 đ/,/Hàng đã nhận, chưa có hóa đơn\s*200\.000 đ/,/Quá hạn 31–60 ngày\s*500\.000 đ/,/khớp sổ cái tài khoản phải trả/])assert.match(view.root.textContent,text)
 // Third review: a claim for goods returned after their invoice is shown next to the goods still waiting, not netted away.
 assert.match(view.root.textContent,/Hàng trả sau hóa đơn, chờ hóa đơn điều chỉnh\s*220\.000 đ/)
 assert.match(view.root.textContent,/hàng chưa có hóa đơn 200\.000 đ · hàng trả sau hóa đơn, chờ hóa đơn điều chỉnh 220\.000 đ/)
 exact(view.root,'Trả tiền').click();await settle()
 const form=document.body.querySelector('dialog[open] form')
 assert.match(form.textContent,/Đang nợ theo hóa đơn 1\.655\.000 đ/)
 await type(form.querySelector('[aria-label="Số tiền trả 0001234"]'),'1200000');await settle(2)
 assert.match(form.textContent,/0001234: chỉ còn trả được 1\.155\.000 đ\. Phần trả thêm ghi vào ô tạm ứng\./)
 await type(form.querySelector('[aria-label="Số tiền trả 0001234"]'),'1155000')
 await type(field(form,'Tạm ứng thêm'),'45000')
 await type(field(form,'Số ủy nhiệm chi'),'UNC-77');await settle(2)
 form.dispatchEvent(new window.Event('submit',{cancelable:true}));await settle()
 const sent=calls.find(c=>c.name==='finance.supplier_payment.prepare').args
 assert.deepEqual([sent.supplier,sent.allocations,sent.advance_amount,sent.mode,sent.reference_no,sent.signers],
  ['KN',[{doctype:'Purchase Invoice',name:'ACC-PINV-1',amount:1155000}],45000,'bank','UNC-77',{CHIEF:'ktt@lotus',APPROVE:'gd@lotus'}])
 assert.match(notices[0],/Đã lập phiếu chi ACC-PAY-1/)
 view.unmount()
 const voucher={doctype:'Payment Entry',name:'ACC-PAY-1',kind:'Trả nhà cung cấp',party_name:'Kết Nông',amount:1200000,mode:'bank',reference:'UNC-77',posting_date:'2026-11-10',docstatus:0,unallocated:45000,
  lines:[{label:'0001234',amount:1155000}],references:[{name:'ACC-PINV-1',type:'invoices'}],print_url:'/lotus/in-phieu-chi?doctype=Payment+Entry&name=ACC-PAY-1',signed_copy:null,posting:'POST-1',can_reverse:false,can_cancel_draft:false,
  signing:{started:true,returned:false,current:2,can_sign:true,can_return:true,steps:[{key:'PREPARE',title:'Kế toán lập phiếu',state:'Đã ký',name:'An'},{key:'CHIEF',title:'Kế toán trưởng',state:'Đã ký',name:'Bình'},{key:'APPROVE',title:'Giám đốc duyệt chi',state:'Chờ ký',name:'Giám đốc'}]}}
 const pay=server({'procurement.voucher':voucher,'finance.payments.sign_payment':{},'stock_attachments.files':[]})
 const asked=[]
 const page=mount(VoucherDetail,{doctype:'Payment Entry',name:'ACC-PAY-1',ask:async t=>{asked.push(t);return true},callFn:pay.callFn,onNotice:()=>{},onError:()=>{}});await settle()
 assert.match(page.root.textContent,/Trả nhà cung cấp · Đang ký · Kết Nông · 1\.200\.000 đ · Chuyển khoản UNC-77/)
 assert.match(page.root.textContent,/Tạm ứng \(chưa gắn hóa đơn\)\s*45\.000 đ/)
 assert.equal([...page.root.querySelectorAll('a')].find(a=>a.textContent.trim()==='In giấy đề nghị chi').getAttribute('href'),voucher.print_url)
 exact(page.root,'Ký duyệt').click();await settle()
 assert.match(asked[0],/Phiếu chi · ACC-PAY-1 · 1\.200\.000 đ · bước Giám đốc duyệt chi/)
 assert.ok(pay.calls.some(c=>c.name==='finance.payments.sign_payment'))
 page.unmount()
})
