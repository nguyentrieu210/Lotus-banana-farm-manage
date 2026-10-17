import {test} from 'node:test'
import assert from 'node:assert/strict'
import {popupLayout} from '../src/mobile-popup-layout.js'

test('popup stays below a high field and above the bottom navigation',()=>{
 const p=popupLayout({left:16,top:120,bottom:176,width:358},{width:390,height:844},{header:66,footer:70})
 assert.equal(p.up,false)
 assert.equal(p.top,182)
 assert.ok(p.top+p.maxHeight<=844-70-8)
})
test('keyboard shrinks the visible viewport and opens lower fields upward',()=>{
 const p=popupLayout({left:16,top:300,bottom:356,width:358},{width:390,height:400},{header:66})
 assert.equal(p.up,true)
 assert.ok(p.top>=74)
 assert.ok(p.top+p.maxHeight<300)
})
test('panned iPhone viewport respects offset, safe header and visible edges',()=>{
 const p=popupLayout({left:-10,top:430,bottom:486,width:390},{left:0,top:200,width:375,height:360},{header:66})
 assert.equal(p.left,8)
 assert.equal(p.width,359)
 assert.ok(p.top>=208)
 assert.ok(p.top+p.maxHeight<=552)
})
test('short landscape space cannot produce a negative scroll area',()=>{
 const p=popupLayout({left:12,top:84,bottom:140,width:300},{width:320,height:200},{header:70,footer:60})
 assert.ok(p.maxHeight>=0)
 assert.ok(p.width<=304)
})
