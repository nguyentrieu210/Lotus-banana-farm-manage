import {test} from 'node:test'
import assert from 'node:assert/strict'
import {hasMobileAccess,mobileActions,mobileGroups,mobileTabs} from '../src/mobile-menu.js'

const session=(modules={},capabilities={})=>({modules,capabilities})

test('single app combines different permitted jobs without switching persona',()=>{
 const user=session({farms:['Farm','Farm Block'],forecast:['Lotus Block Forecast Profile']},{field_report:true,packhouse:true,stock:true})
 const actions=mobileActions(user).map(a=>a.id)
 for(const id of ['farm-work','packhouse','stock','farms','forecast'])assert.ok(actions.includes(id),id)
 for(const id of ['assign','actual','disease','qc','harvest','fruit','materials'])assert.ok(!actions.includes(id),id+': the old field and packhouse screens are gone')
 assert.deepEqual(mobileActions(session({alerts:['x'],settings:['x']})),[],'Cảnh báo and Cấu hình are gone')
 assert.equal(hasMobileAccess(user),true)
 assert.equal(new Set(actions).size,actions.length)
})

test('the daily report and the xưởng need their own capability',()=>{
 const ids=mobileActions(session({farms:['Farm']})).map(a=>a.id)
 assert.ok(!ids.includes('farm-work'),'the daily report needs the field_report capability')
 assert.ok(!ids.includes('packhouse'))
 const packhouse=mobileActions(session({}, {packhouse:true}))
 assert.deepEqual(packhouse.map(a=>a.id),['packhouse'])
 assert.equal(packhouse[0].href,'/lotus/cong-viec?field_view=packhouse','the xưởng opens in Công việc ngoài vườn')
 assert.equal(hasMobileAccess(session({}, {packhouse:true})),true)
})

test('every tab opens a permitted page of the workspace',()=>{
 const user=session({farms:['Farm'],map:['Farm Block Geometry']},{field_report:true})
 assert.equal(mobileTabs(user)[0].path,'mobile')
 assert.deepEqual(mobileTabs(user).map(t=>t.path),['mobile','farms','map'])
 assert.ok(mobileTabs(user).every(tab=>tab.path==='mobile'||mobileActions(user).some(a=>a.path===tab.path)))
})

test('map-only account has a usable landing tab without full dashboard access',()=>{
 const user=session({map:['Farm Block Geometry']})
 assert.equal(hasMobileAccess(user),true)
 assert.ok(mobileTabs(user).some(t=>t.path==='map'))
 assert.ok(!mobileActions(user).some(a=>a.id==='reports'))
 assert.equal(mobileGroups(user).length,1)
})

test('unassigned user has no module actions',()=>{
 const user=session()
 assert.equal(hasMobileAccess(user),false)
 assert.deepEqual(mobileTabs(user),[{id:'mobile',label:'Trang chủ',path:'mobile',icon:'home'}])
})

test('stock-only account can open warehouse from mobile home without farm permissions',()=>{
 const user=session({}, {stock:true})
 assert.equal(hasMobileAccess(user),true)
 assert.deepEqual(mobileActions(user).map(a=>a.id),['stock'])
 assert.equal(mobileActions(user)[0].href,'/lotus/kho')
})
