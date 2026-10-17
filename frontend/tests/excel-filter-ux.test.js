import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {excelKey,filterExcelChoices,toggleExcelVisible,excelAppliedValues,excelDefaultSelection} from '../src/excel-filter-state.js'

const stock=readFileSync(new URL('../src/StockApp.vue',import.meta.url),'utf8')
const header=readFileSync(new URL('../src/components/ExcelHeader.vue',import.meta.url),'utf8')
const style=readFileSync(new URL('../src/stock-overview.css',import.meta.url),'utf8')

test('Excel search finds Vietnamese labels without requiring accents',()=>{
 const choices=[{value:1,label:'Phân bón'},{value:2,label:'Thuốc BVTV'},{value:null,label:'(Trống)'}]
 assert.deepEqual(filterExcelChoices(choices,'phan').map(r=>r.value),[1])
 assert.deepEqual(filterExcelChoices(choices,'BVTV').map(r=>r.value),[2])
 assert.deepEqual(filterExcelChoices(choices,'').length,3)
 assert.equal(excelKey(null),'__LOTUS_BLANK__')
})

test('Typing in a column filter selects matching rows instead of leaving every row selected',()=>{
 const choices=[{value:'A',label:'Phân bón'},{value:'B',label:'Thuốc BVTV'},{value:'C',label:'Đường ống'}]
 assert.deepEqual(excelDefaultSelection(choices,undefined,'thuoc'),['B'])
 assert.deepEqual(excelAppliedValues(choices,excelDefaultSelection(choices,undefined,'thuoc')),['B'])
 assert.deepEqual(excelDefaultSelection(choices,['A'],'duong'),['C'])
 assert.deepEqual(excelDefaultSelection(choices,['A'],''),['A'])
 assert.deepEqual(excelDefaultSelection(choices,undefined,'không có'),[])
 assert.deepEqual(excelAppliedValues(choices,[]),[])
 assert.deepEqual(excelAppliedValues([],[]),[])
 assert.deepEqual(filterExcelChoices(choices,'DUONG').map(r=>r.value),['C'])
})

test('Checkbox changes keep manual selections when the search text changes',()=>{
 assert.match(header,/const manualSelection = ref\(false\)/)
 assert.match(header,/watch\(search, value =>/)
 assert.match(header,/!manualSelection\.value/)
 assert.match(header,/manualSelection\.value = true/)
 assert.match(header,/excelDefaultSelection\(choices\.value, props\.params\.selection, value\)/)
})

test('Select all in searched results keeps values selected outside the search',()=>{
 const choices=[{value:'A'},{value:'B'},{value:'C'}]
 const selected=['C']
 const next=toggleExcelVisible(selected,[choices[0],choices[1]],false)
 assert.deepEqual(next.sort(),['A','B','C'])
 assert.deepEqual(toggleExcelVisible(next,[choices[0],choices[1]],true),['C'])
})

test('Apply uses original value types and clearing all selections filters to zero rows',()=>{
 const options=[{value:10},{value:20},{value:null}]
 assert.deepEqual(excelAppliedValues(options,['10','__LOTUS_BLANK__']),[10,null])
 assert.equal(excelAppliedValues(options,['10','20','__LOTUS_BLANK__']),null)
 assert.deepEqual(excelAppliedValues(options,[]),[])
})

test('Excel dropdown is anchored outside AG Grid clipping and supports keyboard focus',()=>{
 assert.match(header,/<Teleport to="body">/)
 assert.match(header,/@change="selectVisible"/)
 assert.match(header,/ref="searchInput"/)
 assert.match(header,/@click="clear"/)
 assert.match(header,/@click="apply"/)
 assert.match(header,/onKeydown/)
})

test('compact live search aligned right of warehouse scope, no submit button',()=>{
 assert.match(stock,/watch\(searchDraft,value=>/)
 assert.match(stock,/setTimeout\(\(\)=>/)
 assert.match(stock,/\},220\)/)
 const scopeStart=stock.indexOf('class="stock-scope"')
 const scope=stock.slice(scopeStart,stock.indexOf('<section v-if="tab===\'stock\'"',scopeStart))
 assert.ok(scope.indexOf('>Kho<UiSelect')<scope.indexOf('stock-search--instant'))
 assert.match(style,/\.stock-search--instant\{[\s\S]*?margin-left:auto/)
 assert.match(style,/flex:0 0 180px/)
 assert.ok(!scope.includes('type="submit"'))
 assert.match(style,/\.ag-header-cell/)
 assert.match(style,/\.ag-cell/)
 assert.match(style,/border-right:1px solid/)
})

test('Company scope filters hidden when user has only one authorized company',()=>{
 for(const name of ['StockApp.vue','HrApp.vue','TimekeepingApp.vue']){
  const src=readFileSync(new URL('../src/'+name,import.meta.url),'utf8')
  assert.match(src,/v-if="\(session\?\.companies\?\.length\|\|0\)>1">Công ty/)
 }
 const app=readFileSync(new URL('../src/App.vue',import.meta.url),'utf8')
 assert.match(app,/v-if="companies.length>1">Công ty/)
 assert.match(app,/if\(companies.value.length===1\)scope.company=companies.value\[0\]/)
})

test('UI labels use Vườn rather than Nông trường without changing Farm data keys',()=>{
 for(const name of ['StockApp.vue','HrApp.vue','TimekeepingApp.vue','AssignApp.vue','FarmWorkApp.vue']){
  const src=readFileSync(new URL('../src/'+name,import.meta.url),'utf8')
  assert.doesNotMatch(src,/Nông trường|nông trường|NÔNG TRƯỜNG/)
 }
})

test('Schema generated fields and table headings localize Farm label at render time',()=>{
 const schema=readFileSync(new URL('../src/components/SchemaForm.vue',import.meta.url),'utf8')
 const datatable=readFileSync(new URL('../src/components/DataTable.vue',import.meta.url),'utf8')
 assert.match(schema,/fieldCaption=f=>uiFarmLabel/)
 assert.match(datatable,/headerName:uiFarmLabel\(c.headerName\)/)
})
