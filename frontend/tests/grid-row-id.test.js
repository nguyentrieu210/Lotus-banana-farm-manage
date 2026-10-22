import test from 'node:test'
import assert from 'node:assert/strict'
import {gridRowId} from '../src/grid-row-id.js'

test('grid row identity follows the document through filters, sorting, and cloned reloads',()=>{
 const records=[
  {name:'LOTUS-222-A1',block_code:'A1',area_ha:2},
  {name:'LOTUS-222-B3',block_code:'B3',area_ha:4},
  {name:'LOTUS-180-A1',block_code:'A1',area_ha:3},
 ]
 const ids=records.map(gridRowId)
 assert.equal(new Set(ids).size,3)
 assert.equal(gridRowId(records[1]),'LOTUS-222-B3')
 const filtered=records.filter(r=>r.area_ha>=3).sort((a,b)=>b.area_ha-a.area_ha)
 assert.deepEqual(filtered.map(gridRowId),['LOTUS-222-B3','LOTUS-180-A1'])
 assert.equal(gridRowId({...records[1]}),'LOTUS-222-B3')
 assert.equal(gridRowId({block_code:'B3',db_id:'77'},'db_id'),'77')
})

test('unkeyed rows retain object identity without referring to their view index',()=>{
 const a={label:'first'},b={label:'second'}
 const first=gridRowId(a),second=gridRowId(b)
 assert.notEqual(first,second)
 assert.equal(gridRowId(a),first)
 assert.deepEqual([b,a].map(gridRowId),[second,first])
})
