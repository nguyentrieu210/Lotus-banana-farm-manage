import {test} from 'node:test'
import assert from 'node:assert/strict'
import {placeOptions,cleanItems} from '../src/assign-model.js'

test('one picker shows block OR plot; plots carry parent label',()=>{
 const options=placeOptions({blocks:[{name:'B1',block_code:'A01'}],plots:[{name:'P1',plot_code:'A01-01',farm_block:'B1'}]})
 assert.deepEqual(options.map(o=>o.value),['block:B1','plot:P1'])
 assert.match(options[1].subtitle,/A01/)
})
test('multiple jobs retain only location, work type and quantity',()=>{
 assert.deepEqual(cleanItems([{location:'block:B1',work_type:'BAG',qty:'800'},
  {location:'plot:P1',work_type:'LEAF',qty:'1.25'}]),
  [{location:'block:B1',work_type:'BAG',qty:800},{location:'plot:P1',work_type:'LEAF',qty:1.25}])
})
test('missing or invalid jobs are rejected before network access',()=>{
 assert.throws(()=>cleanItems([]),/ít nhất/)
 assert.throws(()=>cleanItems([{location:'',work_type:'W',qty:5}]),/vị trí|lô hoặc thửa/)
 assert.throws(()=>cleanItems([{location:'plot:P1',work_type:'',qty:5}]),/công việc/)
 assert.throws(()=>cleanItems([{location:'plot:P1',work_type:'W',qty:-1}]),/số lượng/)
 assert.throws(()=>cleanItems([{location:'plot:P1',work_type:'W',qty:'NaN'}]),/số lượng/)
})
