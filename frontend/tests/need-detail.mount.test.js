import test from 'node:test'
import assert from 'node:assert/strict'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,mount,tick} from './support/mount.mjs'

const NeedDetail=await load('components/procurement/NeedDetail.vue')
const settle=async(n=4)=>{for(let i=0;i<n;i++)await tick()}
const exact=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label)
const type=async(el,value)=>{el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));await tick()}
const base=(over={})=>({name:'MAT-MR-9',company:'C',modified:'m1',docstatus:1,state:'Đã duyệt',stage:'Chờ mua',step:null,reason:'Bón phân khu A',department:'Đội A',total:2400000,
 items:[],signatures:[],signers:{},progress:{stage:'Chờ mua',lines:[]},print_url:'/lotus/in-de-xuat?name=MAT-MR-9',...over})
function harness(detail,answers={}){
 const calls=[],asked=[],events=[]
 const callFn=async(method,args)=>{calls.push({method:method.split('.').pop(),args});const a=answers[method.split('.').pop()];return typeof a==='function'?a(args):a}
 const view=mount(NeedDetail,{detail,company:'C',canOrder:true,ask:async text=>{asked.push(text);return true},callFn,
  onChanged:d=>events.push(['changed',d]),onDeleted:n=>events.push(['deleted',n]),onNotice:t=>events.push(['notice',t]),onError:t=>t&&events.push(['error',t]),onOrder:()=>events.push(['order'])})
 return {view,calls,asked,events}
}

test('an approved proposal shows its stage and offers order, close, cancel, print and the signed copy',async()=>{
 const {view,events}=harness(base({can_close:true,can_cancel:true,signed_copy:{url:'/api/method/lotus_farm.signing.signed_pdf?name=MAT-MR-9',pdf_sha256:'abc'}}))
 await settle()
 assert.match(view.root.textContent,/Chờ mua · Đội A · Bón phân khu A · 2\.400\.000 đ/)
 for(const label of ['Lập đơn từ đề xuất','Đóng phần chưa mua','Hủy đề xuất'])assert.ok(exact(view.root,label),label)
 assert.ok(!exact(view.root,'Xóa nháp')&&!exact(view.root,'Trả lại'),'actions follow the flags the server sent')
 const links=[...view.root.querySelectorAll('a')].map(a=>[a.textContent.trim(),a.getAttribute('href')])
 assert.deepEqual(links.filter(([t])=>/In đề xuất|Tải bản PDF đã ký/.test(t)),[['In đề xuất','/lotus/in-de-xuat?name=MAT-MR-9'],['Tải bản PDF đã ký','/api/method/lotus_farm.signing.signed_pdf?name=MAT-MR-9']])
 exact(view.root,'Lập đơn từ đề xuất').click();await tick()
 assert.deepEqual(events.at(-1),['order'])
 view.unmount()
})

test('closing the unbought part and cancelling both need a reason',async()=>{
 const closed=base({stage:'Đã xong',closed:true})
 const {view,calls,events}=harness(base({can_close:true,can_cancel:true}),{close_remainder:closed,cancel_proposal:base({docstatus:2,stage:'Đã hủy'})})
 await settle()
 exact(view.root,'Đóng phần chưa mua').click();await tick()
 const confirmClose=()=>[...view.root.querySelectorAll('.need-detail__form button')].find(b=>b.textContent.trim()==='Đóng phần chưa mua')
 assert.ok(confirmClose().disabled,'no closing without a reason')
 await type(view.root.querySelector('.need-detail__form textarea'),'Đủ hàng trong kho')
 assert.equal(confirmClose().disabled,false)
 confirmClose().click();await settle()
 assert.deepEqual(calls.find(c=>c.method==='close_remainder').args,{name:'MAT-MR-9',modified:'m1',reason:'Đủ hàng trong kho'})
 assert.equal(events.find(e=>e[0]==='changed')[1].stage,'Đã xong')
 exact(view.root,'Hủy đề xuất').click();await tick()
 const confirmCancel=()=>[...view.root.querySelectorAll('.need-detail__form button')].find(b=>b.textContent.trim()==='Hủy đề xuất')
 assert.ok(confirmCancel().disabled)
 await type(view.root.querySelector('.need-detail__form textarea'),'Đổi kế hoạch')
 confirmCancel().click();await settle()
 assert.deepEqual(calls.find(c=>c.method==='cancel_proposal').args,{name:'MAT-MR-9',modified:'m1',reason:'Đổi kế hoạch',cancel_quotes:0})
 view.unmount()
})

test('signing confirms what is signed; an imported proposal asks its reason first',async()=>{
 const draft=base({docstatus:0,state:'Nháp',stage:'Nháp',step:0,step_title:'Người đề xuất',reason:'',needs_reason:true,needs_signers:false,can_sign:true,can_delete:true,
  signatures:[{action:'PROPOSE',title:'Người đề xuất',name:'An',state:''}]})
 const {view,calls,asked,events}=harness(draft,{sign:base({docstatus:0,stage:'Đang ký',step:1}),delete_proposal:{name:'MAT-MR-9'}})
 await settle()
 const sign=()=>exact(view.root,'Ký và gửi phụ trách bộ phận')
 assert.ok(sign().disabled,'the reason comes first')
 await type(view.root.querySelector('textarea'),'Nhập từ danh mục tháng 11')
 assert.equal(sign().disabled,false)
 sign().click();await settle()
 assert.match(asked[0],/Phiếu đề xuất mua vật tư · MAT-MR-9 · 2\.400\.000 đ · bước Người đề xuất/)
 assert.equal(calls.find(c=>c.method==='sign').args.reason,'Nhập từ danh mục tháng 11')
 exact(view.root,'Xóa nháp').click();await settle()
 assert.match(asked[1],/Xóa đề xuất nháp MAT-MR-9/)
 assert.deepEqual(events.at(-1),['deleted','MAT-MR-9'])
 view.unmount()
})
