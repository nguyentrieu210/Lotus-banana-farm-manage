import test from 'node:test'
import assert from 'node:assert/strict'
import {readDeepLink,clearDeepLink,openDeepLink} from '../src/mobile-deep-link.js'

function fakeWindow(href){
 const location={href,get search(){return new URL(this.href).search}}
 const history={state:{keep:1},calls:[],replaceState(state,_,url){this.calls.push([state,url]);location.href=new URL(url,location.href).href}}
 return {location,history}
}

test('reads signing, document and older links',()=>{
 assert.deepEqual(readDeepLink('?sign_dt=Payment+Entry&sign_dn=ACC-PAY-1'),{kind:'sign',doctype:'Payment Entry',name:'ACC-PAY-1'})
 assert.deepEqual(readDeepLink('?doc=MAT-STE-1&doctype=Stock%20Entry'),{kind:'open',doctype:'Stock Entry',name:'MAT-STE-1'})
 assert.deepEqual(readDeepLink('?doc=PUR-ORD-1'),{kind:'open',doctype:'',name:'PUR-ORD-1'})
 assert.deepEqual(readDeepLink('?proposal=MAT-MR-2026-00005'),{kind:'open',doctype:'Material Request',name:'MAT-MR-2026-00005'})
 assert.deepEqual(readDeepLink('?request=1'),{kind:'request',name:'1'})
 assert.deepEqual(readDeepLink('?tab=leave'),{kind:'tab',name:'leave'})
 assert.equal(readDeepLink('?sign_dt=Payment+Entry'),null,'half a signing link opens nothing')
 assert.equal(readDeepLink(''),null)
})

test('clears only deep-link parameters and keeps the rest',()=>{
 const w=fakeWindow('https://lotus.test/buying?company=Lotus&sign_dt=Purchase+Order&sign_dn=PO-1#top')
 assert.equal(clearDeepLink(w),true)
 assert.deepEqual(w.history.calls,[[{keep:1},'/buying?company=Lotus#top']])
 assert.equal(clearDeepLink(w),false)
})

test('opens with the doctype opener, falls back to the generic one, ignores unknown kinds',async()=>{
 const seen=[]
 const openers={sign:l=>seen.push(['sign',l.doctype,l.name]),'Purchase Order':l=>seen.push(['po',l.name]),open:l=>seen.push(['open',l.doctype,l.name])}
 let w=fakeWindow('https://lotus.test/buying?sign_dt=Material+Request&sign_dn=MR-1')
 assert.equal((await openDeepLink(openers,w)).kind,'sign')
 w=fakeWindow('https://lotus.test/buying?doc=PO-1&doctype=Purchase+Order')
 await openDeepLink(openers,w)
 w=fakeWindow('https://lotus.test/buying?proposal=MR-2')
 await openDeepLink(openers,w)
 assert.deepEqual(seen,[['sign','Material Request','MR-1'],['po','PO-1'],['open','Material Request','MR-2']])
 w=fakeWindow('https://lotus.test/buying?tab=home')
 assert.equal(await openDeepLink(openers,w),null,'no tab opener registered')
 assert.equal(w.location.href,'https://lotus.test/buying','parameters are cleared even when nothing opens')
})
