import test from 'node:test'
import assert from 'node:assert/strict'
import {dismissOnBackdrop} from '../src/dialogs.js'

function fixture(){
 let closed=0
 const dialog={close:()=>closed++,getBoundingClientRect:()=>({left:100,right:400,top:100,bottom:400})}
 return {dialog,event:(x,y,target=dialog)=>({currentTarget:dialog,target,clientX:x,clientY:y}),closed:()=>closed}
}
test('native dialog closes for a click on the outside backdrop',()=>{
 const f=fixture()
 dismissOnBackdrop(f.event(20,200))
 assert.equal(f.closed(),1)
})
test('dialog padding, content clicks and pending saves do not dismiss',()=>{
 const f=fixture()
 dismissOnBackdrop(f.event(110,110))
 dismissOnBackdrop(f.event(20,200,{}))
 dismissOnBackdrop(f.event(20,200),true)
 assert.equal(f.closed(),0)
})
