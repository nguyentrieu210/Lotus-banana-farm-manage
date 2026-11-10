import test from 'node:test'
import assert from 'node:assert/strict'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,mount,tick} from './support/mount.mjs'

const Sheet=await load('components/signing/SignSheet.vue')
const Inbox=await load('components/signing/SigningInboxPage.vue')
const Settings=await load('components/signing/SignatureSettings.vue')
const exact=(text)=>[...document.querySelectorAll('button')].find(b=>b.textContent.trim()===text)
const starts=(text)=>[...document.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(text))
const settle=async(n=4)=>{for(let i=0;i<n;i++)await tick()}

function fake(answers){
 const calls=[]
 const fn=async(method,args)=>{calls.push({method,args});const key=Object.keys(answers).find(k=>method.endsWith(k));const a=answers[key];return typeof a==='function'?a(args):a}
 fn.calls=calls
 return fn
}
const voucher={doctype:'Payment Entry',name:'ACC-PAY-1',chain:'payment_voucher',chain_label:'Phiếu chi',amount:1500000,currency:'VND',modified:'m1',
 step_title:'Kế toán trưởng',creator_name:'An',print_url:'/lotus/in-phieu-chi?doctype=Payment+Entry&name=ACC-PAY-1',desktop_url:'/lotus/tai-chinh?tab=cash'}
const waiting={chain:'payment_voucher',label:'Phiếu chi',round:1,returned:false,done:false,current:1,can_sign:true,can_return:true,can_reassign:true,
 steps:[{key:'PREPARE',title:'Kế toán lập phiếu',state:'Đã ký',name:'An'},{key:'CHIEF',title:'Kế toán trưởng',state:'Chờ ký',name:'Bình',assignee:'binh@lotus'},
  {key:'APPROVE',title:'Giám đốc duyệt chi',state:'Chưa đến lượt',name:'Chi'}]}

test('sign sheet shows the print and the facts, confirms what is signed, then signs through sign_many',async()=>{
 const callFn=fake({chain_status:waiting,sign_many:{results:[{doctype:'Payment Entry',name:'ACC-PAY-1',ok:true,message:'Đã ký'}],signed:1}})
 const done=[]
 const view=mount(Sheet,{modelValue:true,row:voucher,callFn,onDone:e=>done.push(e)})
 await settle()
 assert.ok(document.querySelector('iframe[src*="in-phieu-chi"]'),'the print page is shown beside the actions')
 assert.match(document.body.textContent,/Người lập: An · Số tiền: 1\.500\.000 đ/)
 starts('Ký: Kế toán trưởng').click();await settle()
 assert.match(document.body.textContent,/Phiếu chi · ACC-PAY-1 · 1\.500\.000 đ · bước Kế toán trưởng/,'the confirmation names what is signed')
 assert.ok(!callFn.calls.some(c=>c.method.endsWith('sign_many')),'nothing is signed before confirming')
 exact('Ký').click();await settle()
 assert.deepEqual(callFn.calls.find(c=>c.method.endsWith('sign_many')).args.items,[{doctype:'Payment Entry',name:'ACC-PAY-1',modified:'m1'}])
 assert.equal(done.length,1)
 view.unmount()
})

test('return needs a reason and goes through return_any; reassign lists only other eligible people',async()=>{
 const callFn=fake({chain_status:waiting,return_any:{ok:1},candidates:{candidates:{CHIEF:[{user:'binh@lotus',name:'Bình'},{user:'dung@lotus',name:'Dũng',designation:'Kế toán trưởng'}]}}})
 const view=mount(Sheet,{modelValue:true,row:voucher,callFn})
 await settle()
 exact('Trả lại').click();await settle()
 const send=exact('Trả lại người lập')
 assert.equal(send.disabled,true,'no return without a reason')
 const reason=document.querySelector('textarea')
 reason.value='Sai số tiền';reason.dispatchEvent(new Event('input'));await settle()
 assert.equal(exact('Trả lại người lập').disabled,false)
 exact('Trả lại người lập').click();await settle()
 assert.deepEqual(callFn.calls.find(c=>c.method.endsWith('return_any')).args,{doctype:'Payment Entry',name:'ACC-PAY-1',reason:'Sai số tiền',modified:'m1'})
 view.unmount()
 const second=mount(Sheet,{modelValue:true,row:voucher,callFn})
 await settle()
 starts('Chuyển người ký').click();await settle()
 assert.ok(callFn.calls.some(c=>c.method.endsWith('candidates')&&c.args.chain==='payment_voucher'))
 assert.equal(exact('Chuyển người ký').disabled,false,'the toggle stays usable')
 second.unmount()
})

test('Chờ tôi ký lists waiting documents and keeps Ký nhiều off until something is chosen',async()=>{
 const callFn=fake({inbox:{rows:[voucher,{...voucher,name:'ACC-PAY-2',amount:200000}],total:2}})
 const view=mount(Inbox,{callFn})
 await settle(6)
 assert.ok(callFn.calls.some(c=>c.method.endsWith('inbox')))
 const bulk=starts('Chọn chứng từ để ký nhiều')
 assert.ok(bulk&&bulk.disabled,'nothing chosen yet')
 assert.match(document.body.textContent,/ACC-PAY-2/)
 view.unmount()
})

test('Chữ ký của tôi on desktop shows the saved images and offers upload, drawing and removal',async()=>{
 const profile={has_signature:true,signature_preview:'data:image/png;base64,AA',has_initials:false,initials_preview:'',date_format:'DD/MM/YYYY'}
 const callFn=fake({my_signature_profile:profile,remove_my_signature_image:{...profile,has_signature:false,signature_preview:''}})
 const view=mount(Settings,{modelValue:true,callFn})
 await settle()
 assert.ok(document.querySelector('img[alt="Chữ ký đã lưu"]'))
 assert.match(document.body.textContent,/Chưa có ký nháy/)
 assert.equal(document.querySelectorAll('input[type=file]').length,2,'one upload per kind')
 starts('Vẽ chữ ký').click();await settle()
 assert.ok(document.querySelector('canvas.lotus-signature-pad'),'drawing uses the shared pad')
 exact('Hủy').click();await settle()
 exact('Xóa').click();await settle()
 assert.match(document.body.textContent,/Chứng từ đã ký trước đây không đổi/)
 const confirmButtons=[...document.querySelectorAll('button')].filter(b=>b.textContent.trim()==='Xóa')
 confirmButtons[confirmButtons.length-1].click();await settle()
 assert.ok(callFn.calls.some(c=>c.method.endsWith('remove_my_signature_image')))
 view.unmount()
})
