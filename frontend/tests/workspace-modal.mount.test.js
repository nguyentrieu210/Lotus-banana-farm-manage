import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,ref,document,window} from './support/mount.mjs'

const WorkspaceModal=await load('components/WorkspaceModal.vue')

test('bare WorkspaceModal behaves like the native dialog it replaced',async()=>{
 const modal=ref(null),busy=ref(false),cancelled=[],closed=[]
 const view=mount({setup:()=>()=>h(WorkspaceModal,{ref:modal,bare:true,title:'Phiếu kho',busy:busy.value,class:'stock-dialog',onCancel:e=>cancelled.push(e),onClose:()=>closed.push(1)},()=>h('form',[h('header',[h('h2','Phiếu kho')])]))})
 await tick()
 const dialog=view.root.querySelector('dialog.stock-dialog')
 assert.ok(dialog,'renders in place with the caller class (screen-scoped CSS keeps working)')
 assert.equal(dialog.getAttribute('aria-label'),'Phiếu kho')
 assert.equal(view.root.querySelectorAll('.workspace-modal__header').length,0,'bare: caller keeps its own header')
 modal.value.showModal();assert.equal(modal.value.open,true,'showModal() is synchronous like <dialog>')
 dialog.dispatchEvent(new window.Event('cancel',{cancelable:true}));await tick()
 assert.equal(cancelled.length,1,'caller @cancel still runs');assert.equal(modal.value.open,false,'Esc closes when not busy')
 modal.value.showModal();modal.value.close();await tick()
 assert.equal(modal.value.open,false);assert.ok(closed.length>=1,'@close is forwarded')
 view.unmount()
})

test('Esc is ignored while busy and when the caller prevents it',async()=>{
 const modal=ref(null)
 const view=mount({setup:()=>()=>h(WorkspaceModal,{ref:modal,bare:true,title:'Đang lưu',busy:true},()=>h('p','…'))})
 await tick();modal.value.showModal()
 view.root.querySelector('dialog').dispatchEvent(new window.Event('cancel',{cancelable:true}));await tick()
 assert.equal(modal.value.open,true,'busy dialog stays open')
 view.unmount()
 const keep=ref(null)
 const second=mount({setup:()=>()=>h(WorkspaceModal,{ref:keep,bare:true,title:'Giao việc',onCancel:e=>e.preventDefault()},()=>h('p','…'))})
 await tick();keep.value.showModal()
 second.root.querySelector('dialog').dispatchEvent(new window.Event('cancel',{cancelable:true}));await tick()
 assert.equal(keep.value.open,true,'caller that handles cancel itself keeps control')
 second.unmount()
})

test('v-model WorkspaceModal still opens, shows the standard header and closes through the model',async()=>{
 const open=ref(false)
 const view=mount({setup:()=>()=>h(WorkspaceModal,{modelValue:open.value,'onUpdate:modelValue':v=>open.value=v,title:'Hồ sơ nhân viên'},()=>h('p','Nội dung'))})
 open.value=true;await tick()
 const dialog=document.querySelector('dialog.workspace-modal')
 assert.ok(dialog?.open,'teleported standard dialog opens from v-model')
 assert.match(dialog.querySelector('.workspace-modal__header').textContent,/Hồ sơ nhân viên/)
 dialog.querySelector('.workspace-modal__header button').click();await tick()
 assert.equal(open.value,false,'Đóng updates the model')
 view.unmount()
})
