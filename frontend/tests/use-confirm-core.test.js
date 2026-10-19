import test from 'node:test'
import assert from 'node:assert/strict'
import {useConfirmCore} from '../src/use-confirm-core.js'

test('one confirm at a time; a double tap never stacks a second dialog',async()=>{
 const events=[]
 const confirm=useConfirmCore({onShow:()=>events.push('show'),onHide:()=>events.push('hide')})
 const first=confirm.ask('Rời màn hình?')
 assert.equal(confirm.message.value,'Rời màn hình?')
 assert.equal(await confirm.ask('Lần bấm thứ hai'),false)
 confirm.finish(true)
 assert.equal(await first,true)
 assert.equal(confirm.pending.value,false)
 const second=confirm.ask('Đăng xuất?');confirm.finish(0)
 assert.equal(await second,false)
 assert.deepEqual(events,['show','hide','show','hide'])
})
