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
