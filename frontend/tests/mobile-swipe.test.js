import {test} from 'node:test'
import assert from 'node:assert/strict'
import {swipeStep} from '../src/mobile-swipe.js'
const gesture={dx:-120,dy:12,elapsed:200,startX:220,width:390}
test('intentional horizontal swipe changes one tab in the correct direction',()=>{
 assert.equal(swipeStep(gesture),1)
 assert.equal(swipeStep({...gesture,dx:120}),-1)
})
test('vertical scroll, short tap and diagonal drag do not change tabs',()=>{
 assert.equal(swipeStep({...gesture,dy:160}),0)
 assert.equal(swipeStep({...gesture,dx:30}),0)
 assert.equal(swipeStep({...gesture,dy:80}),0)
 assert.equal(swipeStep({...gesture,elapsed:900}),0)
})
test('phone edge gestures remain available to native browser back',()=>{
 assert.equal(swipeStep({...gesture,startX:10}),0)
 assert.equal(swipeStep({...gesture,startX:380}),0)
})

test('shared tab swipe moves one root tab and ignores form controls',async()=>{
 const {createTabSwipe}=await import('../src/mobile-swipe.js')
 globalThis.window??={};window.innerWidth=390
 let screen='home';const visited=[]
 const swipe=createTabSwipe({enabled:()=>true,ignore:'input',tabs:()=>['home','history','profile'],current:()=>screen,go:tab=>{visited.push(tab);screen=tab}})
 const target={closest:()=>null},touch=(x,y)=>({clientX:x,clientY:y})
 swipe.start({touches:[touch(300,200)],target});swipe.end({changedTouches:[touch(180,205)]})
 assert.deepEqual(visited,['history'])
 swipe.start({touches:[touch(300,200)],target:{closest:()=>({})}});swipe.end({changedTouches:[touch(180,205)]})
 assert.deepEqual(visited,['history'],'swipe starting on an ignored control does nothing')
 swipe.start({touches:[touch(300,200)],target});swipe.cancel();swipe.end({changedTouches:[touch(180,205)]})
 assert.deepEqual(visited,['history'],'cancelled swipe does nothing')
})
