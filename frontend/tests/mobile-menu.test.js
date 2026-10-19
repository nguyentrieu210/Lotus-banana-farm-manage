import {test} from 'node:test'
import assert from 'node:assert/strict'
import {hasMobileAccess,mobileActions,mobileGroups,mobileTabs} from '../src/mobile-menu.js'

const session=(modules={},commands={},creatable={},capabilities={})=>({modules,commands,creatable,capabilities})

test('single app combines different permitted jobs without switching persona',()=>{
 const user=session({work:['Daily Work Plan','Daily Work Result'], 'incoming-qc':['Incoming Quality Inspection'],farms:['Farm']},{work:true},{'Daily Work Result':true})
 const actions=mobileActions(user).map(a=>a.id)
 for(const id of ['assign','work','actual','qc','farms'])assert.ok(actions.includes(id),id)
 assert.equal(hasMobileAccess(user),true)
 assert.equal(new Set(actions).size,actions.length)
})

test('read access does not create writing actions',()=>{
 const user=session({work:['Daily Work Plan'], 'incoming-qc':['Incoming Quality Inspection']},{work:false},{'Daily Work Result':false})
 const ids=mobileActions(user).map(a=>a.id)
 assert.ok(ids.includes('work'))
 assert.ok(ids.includes('qc'))
 assert.ok(!ids.includes('assign'))
 assert.ok(!ids.includes('actual'))
 assert.ok(!ids.includes('disease'))
})

test('unauthorized options stay absent even with command role flag',()=>{
 const user=session({farms:['Farm']},{work:true},{'Daily Work Result':true})
 assert.ok(!mobileActions(user).some(a=>['work','assign','actual'].includes(a.id)))
 assert.equal(mobileTabs(user)[0].path,'mobile')
 assert.ok(mobileTabs(user).every(tab=>tab.path==='mobile'||mobileActions(user).some(a=>a.path===tab.path)))
})

test('QC-only account has a usable landing tab without full dashboard access',()=>{
 const user=session({'incoming-qc':['Incoming Quality Inspection']})
 assert.equal(hasMobileAccess(user),true)
 assert.ok(mobileTabs(user).some(t=>t.path==='incoming-qc'))
 assert.ok(!mobileActions(user).some(a=>a.id==='reports'))
 assert.equal(mobileGroups(user).length,1)
})

test('unassigned user has no module actions',()=>{
 const user=session()
 assert.equal(hasMobileAccess(user),false)
 assert.deepEqual(mobileTabs(user),[{id:'mobile',label:'Trang chủ',path:'mobile',icon:'home'}])
})

test('stock-only account can open warehouse from mobile home without farm permissions',()=>{
 const user=session({}, {}, {}, {stock:true})
 assert.equal(hasMobileAccess(user),true)
 assert.deepEqual(mobileActions(user).map(a=>a.id),['stock'])
 assert.equal(mobileActions(user)[0].href,'/lotus/kho')
})
