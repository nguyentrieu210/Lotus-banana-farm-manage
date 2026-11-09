import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {allTicked,buttonLabel,crossFilter,isTicked,matches,toggle,toggleAll} from '../src/pivot-filter.js'

const options=[{value:'A',label:'A'},{value:'B',label:'B'},{value:'C',label:'C'}]

test('with no filter everything is ticked, as in Excel',()=>{
 assert.equal(isTicked({},'zone','A'),true);assert.equal(allTicked({},'zone'),true)
})
test('unticking one value keeps the others',()=>{
 const s=toggle({},'zone','B',options)
 assert.deepEqual(s,{zone:['A','C']})
 assert.equal(isTicked(s,'zone','B'),false);assert.equal(allTicked(s,'zone'),false)
})
test('ticking the last one back removes the filter',()=>{
 assert.deepEqual(toggle({zone:['A','C']},'zone','B',options),{})
})
test('select all clears, and from all it empties so one value can be picked',()=>{
 assert.deepEqual(toggleAll({},'zone'),{zone:[]})
 assert.deepEqual(toggleAll({zone:['A']},'zone'),{})
 assert.deepEqual(toggle({zone:[]},'zone','B',options),{zone:['B']})
})
test('other fields are left alone',()=>{
 assert.deepEqual(toggle({year:['2026']},'zone','A',options),{year:['2026'],zone:['B','C']})
})
test('the button says how many are chosen',()=>{
 assert.equal(buttonLabel('Khu',{},'zone'),'Khu')
 assert.equal(buttonLabel('Khu',{zone:['A','B']},'zone'),'Khu (2)')
})
test('search ignores case and spaces around',()=>{
 assert.equal(matches({label:'Tuần 46'},' tuần'),true)
 assert.equal(matches({label:'Tuần 46'},'tháng'),false)
 assert.equal(matches({label:'x'},''),true)
})
test('a tick row reads across, against the app-wide stacked labels',()=>{
 const css=readFileSync(new URL('../src/components/report/report.css',import.meta.url),'utf8')
 assert.match(css,/\.pivot-filter__panel label\.pivot-filter__row\{display:flex;flex-direction:row/)
})
test('a click on a chart filters to that value, a second click lifts it',()=>{
 assert.deepEqual(crossFilter({},'week','W1'),{week:['W1']})
 assert.deepEqual(crossFilter({week:['W1']},'week','W1'),{})
 assert.deepEqual(crossFilter({week:['W1','W2']},'week','W1'),{week:['W1']})
 assert.deepEqual(crossFilter({zone:['A']},'week','W1'),{zone:['A'],week:['W1']})
})
