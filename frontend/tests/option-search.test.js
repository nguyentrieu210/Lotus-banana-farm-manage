import test from 'node:test'
import assert from 'node:assert/strict'
import {matchesOption,filterOptions} from '../src/option-search.js'

test('pickers match Vietnamese without accents, spaces or dashes',()=>{
 const options=[{value:'LO-A1',label:'Lô A-1',group:'Đồng Nai'},{value:'BD-01',label:'Bình Dương 01'},{value:'VT-9',label:'Phân NPK',subtitle:'Bao 50 kg'}]
 assert.deepEqual(filterOptions(options,'lo a1').map(o=>o.value),['LO-A1'])
 assert.deepEqual(filterOptions(options,'binh duong').map(o=>o.value),['BD-01'])
 assert.deepEqual(filterOptions(options,'dong nai').map(o=>o.value),['LO-A1'],'group text is searchable')
 assert.deepEqual(filterOptions(options,'50kg').map(o=>o.value),['VT-9'],'subtitle is searchable')
 assert.equal(filterOptions(options,'').length,3)
 assert.equal(matchesOption({value:'X'},'đ'),false)
})
