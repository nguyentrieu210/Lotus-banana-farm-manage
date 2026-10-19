import test from 'node:test'
import assert from 'node:assert/strict'
import {ref,nextTick} from 'vue'
import {toast,dismissToast,useToastState,useNoticeToast} from '../src/use-toast.js'

test('toasts carry tone, keep at most four and give actions time to be used',()=>{
 const state=useToastState()
 state.items.splice(0)
 const id=toast.success('Đã lưu')
 assert.equal(state.items.at(-1).tone,'success')
 assert.equal(state.items.at(-1).duration,5000)
 toast.error('Không lưu được')
 assert.equal(state.items.at(-1).duration,8000,'errors stay longer')
 toast({title:'Đã xóa dòng',action:{label:'Hoàn tác',run(){}}})
 assert.equal(state.items.at(-1).duration,8000,'undo needs time')
 toast.info('a');toast.info('b')
 assert.equal(state.items.length,4)
 dismissToast(state.items[0].id)
 assert.equal(state.items.length,3)
 assert.equal(state.items.some(item=>item.id===id),false)
})

test('success refs become toasts and are cleared so the same text can show again',async()=>{
 const state=useToastState()
 state.items.splice(0)
 const notice=ref('')
 useNoticeToast(notice)
 notice.value='Đã lưu nhân viên NV-1'
 await nextTick();await nextTick()
 assert.equal(state.items.at(-1).title,'Đã lưu nhân viên NV-1')
 assert.equal(notice.value,'')
})
