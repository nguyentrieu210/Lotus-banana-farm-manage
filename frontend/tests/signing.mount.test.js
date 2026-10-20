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
const Panel=await load('components/SigningPanel.vue')
const S='lotus_farm.signing.'
const steps=(states,names=['An','Bình','Chi'])=>['Người lập phiếu','Người giao / nhận','Thủ kho / người kiểm tra'].map((title,i)=>({key:['PREPARE','HANDOVER','STOREKEEPER'][i],title,name:names[i],assignee:names[i].toLowerCase()+'@lotus',state:states[i]||'',signed_at:states[i]==='Đã ký'?'2026-10-20 08:00:00':'',note:'',image:''}))
const status=over=>({chain:'stock_document',label:'Phiếu kho',round:1,returned:false,done:false,current:1,can_sign:false,can_return:false,can_start:false,steps:steps(['Đã ký','Chờ ký','Chưa đến lượt']),...over})
const button=(root,text)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(text))
const text=root=>root.textContent.replace(/\s+/g,' ')

test('preparer picks named signers; a step with one eligible person is preselected and empty steps explain why',async()=>{
 calls.length=0
 routes={[S+'chain_status']:status({round:0,current:null,can_start:true,steps:steps([],['','',''])}),
  [S+'candidates']:{steps:[{key:'PREPARE',title:'Người lập phiếu'},{key:'HANDOVER',title:'Người giao / nhận'},{key:'STOREKEEPER',title:'Thủ kho / người kiểm tra'}],remembered:{},
   candidates:{HANDOVER:[{user:'binh@lotus',name:'Bình'},{user:'dung@lotus',name:'Dũng'}],STOREKEEPER:[]}},
  [S+'request_signatures']:status()}
 const view=mount(Panel,{doctype:'Stock Entry',name:'MAT-STE-1',company:'Lotus'});await tick();await tick()
 assert.match(text(view.root),/Chưa có nhân sự nào có quyền ký bước này\. Gắn tài khoản đăng nhập/)
 assert.ok(button(view.root,'Ký người lập và gửi ký').disabled,'every later step needs a named signer')
 view.unmount()
 routes[S+'candidates'].candidates.STOREKEEPER=[{user:'chi@lotus',name:'Chi'}]
 routes[S+'candidates'].remembered={HANDOVER:'dung@lotus'}
 const again=mount(Panel,{doctype:'Stock Entry',name:'MAT-STE-1',company:'Lotus'});await tick();await tick()
 const send=button(again.root,'Ký người lập và gửi ký')
 assert.ok(!send.disabled,'remembered and single choices fill the picker')
 send.click();await tick();await tick()
 assert.deepEqual(calls.find(c=>c.method===S+'request_signatures').args.signers,{HANDOVER:'dung@lotus',STOREKEEPER:'chi@lotus'})
 assert.match(text(again.root),/Bình · đang chờ ký/)
 again.unmount()
})

test('only the waiting signer sees sign and return; a return needs a reason',async()=>{
 calls.length=0
 routes={[S+'chain_status']:status(),[S+'confirm']:status({current:2,steps:steps(['Đã ký','Đã ký','Chờ ký'])}),[S+'return_document']:status({returned:true,current:null})}
 const other=mount(Panel,{doctype:'Stock Entry',name:'MAT-STE-1'});await tick();await tick()
 assert.ok(!button(other.root,'Ký:'),'not my turn')
 other.unmount()
 routes[S+'chain_status']=status({can_sign:true,can_return:true})
 const mine=mount(Panel,{doctype:'Stock Entry',name:'MAT-STE-1'});await tick();await tick()
 button(mine.root,'Trả lại người lập').click();await tick()
 const confirm=[...mine.root.querySelectorAll('button')].find(b=>b.textContent.trim()==='Trả lại')
 assert.ok(confirm.disabled,'a reason is required')
 button(mine.root,'Ký: Người giao / nhận').click();await tick();await tick()
 assert.ok(calls.some(c=>c.method===S+'confirm'&&c.args.name==='MAT-STE-1'))
 assert.match(text(mine.root),/Chi · đang chờ ký/)
 mine.unmount()
})
