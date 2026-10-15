import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {updateColumnFilter,shiftISODate,hasStockSearchFilters,stockEmptyKind} from '../src/stock-filter-state.js'

const app=readFileSync(new URL('../src/StockApp.vue',import.meta.url),'utf8')
const header=readFileSync(new URL('../src/components/ExcelHeader.vue',import.meta.url),'utf8')
const backend=readFileSync(new URL('../../lotus_farm/warehouse.py',import.meta.url),'utf8')

test('Stock screen contains only compact scope filters and its inventory table',()=>{
 assert.match(app,/<div class="stock-scope">/)
 assert.match(app,/<section v-if="tab==='stock'" class="stock-panel stock-inventory-table">/)
 assert.match(app,/@filter="filterStock"/)
 assert.match(app,/v-if="tab==='stock'&&hasStockFilters"/)
 assert.match(app,/<WorkspaceBar .*:actions="workspaceActions"/)
 for(const obsolete of ['stock-overview-metrics','stock-filter-panel','stock-actions','stock-filter-period','stock-welcome','Kỳ nhu cầu dự kiến','Dưới tồn tối thiểu','Thiếu theo nhu cầu']){
  assert.equal(app.includes(obsolete),false,'Redundant screen element '+obsolete)
 }
})

test('column filter changes only the requested column',()=>{
 assert.deepEqual(updateColumnFilter({item_group:['A'],stock_status:['Dưới tối thiểu']},'item_group',null),{stock_status:['Dưới tối thiểu']})
 assert.deepEqual(updateColumnFilter({},'coverage_status',['Cần mua']),{coverage_status:['Cần mua']})
 assert.equal(hasStockSearchFilters(' phân ',{}),true)
 assert.equal(hasStockSearchFilters('',{}),false)
})

test('selecting all column values removes the header filter',()=>{
 assert.match(header,/values\.length===choices\.value\.length\?null:values/)
})

test('catalogue empty state and zero results remain distinct',()=>{
 const d={company:'Lotus Agritech',warehouseCount:4,catalogueCount:55,filteredCount:0,loading:false}
 assert.equal(stockEmptyKind(d),'no-matches')
 assert.equal(stockEmptyKind({...d,catalogueCount:0}),'no-items')
 assert.equal(stockEmptyKind({...d,warehouseCount:0}),'no-warehouse')
 assert.equal(stockEmptyKind({...d,filteredCount:5}),'results')
 assert.equal(stockEmptyKind({...d,loading:true}),'loading')
 assert.equal(stockEmptyKind({...d,company:''}),'no-company')
})

test('server uses independent catalogue and stock quantities',()=>{
 assert.match(backend,/catalogue_count=catalogue_count,stocked_count=stocked_count/)
 assert.match(app,/:show-empty-headers="\(data\?\.catalogue_count\?\?0\)>0"/)
 assert.doesNotMatch(app,/!stocks\.length\)\&\&tab===/)
})

test('table search applies on submit, not on each keypress',()=>{
 assert.match(app,/searchDraft=ref\(''\)/)
 assert.match(app,/function applySearch\(\)\{search\.value=searchDraft\.value\.trim\(\);refresh\(true\)\}/)
 assert.match(app,/@submit\.prevent="applySearch"/)
 assert.match(app,/v-model="searchDraft"/)
})

test('document history and stock ledger keep independent pagination',()=>{
 assert.match(app,/start:documentStart\.value/)
 assert.match(app,/@click="documentStart-=50;refresh\(\)"/)
 assert.match(app,/@click="movementStart-=50;refresh\(\)"/)
})

test('internal demand default handles date boundaries even without extra UI',()=>{
 assert.equal(shiftISODate('2028-02-28',1),'2028-02-29')
 assert.equal(shiftISODate('2026-10-15',6),'2026-10-21')
 assert.equal(shiftISODate('',6),'')
})
