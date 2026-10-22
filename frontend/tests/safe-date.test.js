import test from 'node:test'
import assert from 'node:assert/strict'
import {isISODate,safeLotusDate,lotusDateMinus,lotusDatePlus} from '../src/date-safe.js'
import {loadModule} from './support/mount.mjs'
import {createPinia,setActivePinia} from 'pinia'
setActivePinia(createPinia())
const {useScope}=await loadModule('store.js')

test('invalid/empty date filters fall back to a legitimate Lotus business date',()=>{
 assert.equal(isISODate('2026-10-22'),true)
 for(const invalid of ['',undefined,'2026-02-30','Invalid Date','2026-15-22','10/22/2026'])assert.equal(isISODate(invalid),false)
 assert.equal(safeLotusDate('',undefined,'2026-10-22'),'2026-10-22')
 assert.equal(lotusDateMinus('2026-10-22',29),'2026-09-23')
 assert.equal(lotusDatePlus('2026-10-22',6),'2026-10-28')
 assert.equal(isISODate(safeLotusDate()),true)
})
test('stale saved scope and empty route dates cannot enter reports and field APIs',()=>{
 const scope=useScope()
 const farms=[{name:'LOTUS-222',company:'Lotus Agritech'}]
 scope.fromQuery({date:'',from_date:'2026-02-30',to_date:'nonsense',farm:'LOTUS-222'},'2026-10-22',farms)
 assert.deepEqual([scope.date,scope.from_date,scope.to_date],['2026-10-22','',''])
 scope.fromQuery({date:'2026-02-30'},'2026-10-22',farms)
 assert.equal(scope.date,'2026-10-22')
 assert.equal(scope.query().date,'2026-10-22')
})
