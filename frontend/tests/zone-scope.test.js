import test from 'node:test'
import assert from 'node:assert/strict'
import {loadModule} from './support/mount.mjs'
import {createPinia,setActivePinia} from 'pinia'
import {pages,navGroups} from '../src/domain.js'
setActivePinia(createPinia())
const {useScope}=await loadModule('store.js')
test('changing zone clears care block and old parcel/cycle scopes',()=>{
 const scope=useScope();Object.assign(scope,{farm:'LOTUS-222',zone:'B',block:'A1',plot:'legacy',cycle:'old'})
 scope.clearBelow('zone')
 assert.equal(scope.zone,'B');assert.equal(scope.farm,'LOTUS-222')
 assert.equal(scope.block,'');assert.equal(scope.plot,'');assert.equal(scope.cycle,'')
 assert.equal(scope.query().zone,'B')
 scope.clearBelow('farm');assert.equal(scope.zone,'')
})
test('one overview menu replaces home today and reports, with a separate care map',()=>{
 const paths=navGroups.flatMap(g=>g.items.map(([path])=>path))
 assert.equal(paths.filter(p=>['mobile','today','reports'].includes(p)).length,1)
 assert.equal(new Map(pages).get('reports'),'Tổng quan')
 assert.equal(new Map(pages).get('map'),'Bản đồ chăm sóc')
})
test('single permitted company defaults on every route hydration, including routes without company',()=>{
 const scope=useScope(),farms=[{name:'LOTUS-222',company:'Lotus Agritech'}]
 scope.fromQuery({farm:'LOTUS-222'},'2026-10-19',farms)
 assert.equal(scope.company,'Lotus Agritech')
 scope.fromQuery({company:''},'2026-10-19',farms)
 assert.equal(scope.company,'Lotus Agritech')
})
