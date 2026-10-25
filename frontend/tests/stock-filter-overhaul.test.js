import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {updateColumnFilter,shiftISODate,hasStockSearchFilters,stockEmptyKind} from '../src/stock-filter-state.js'

import {khoSource,khoFile} from './support/kho-source.mjs'
const app=khoSource()
const header=readFileSync(new URL('../src/components/ExcelHeader.vue',import.meta.url),'utf8')
const backend=readFileSync(new URL('../../lotus_farm/warehouse.py',import.meta.url),'utf8')

test('Stock screen contains only compact scope filters and its inventory table',()=>{
 const inventory=khoFile('components/stock/StockInventory.vue')
 assert.match(inventory,/<ListPage title="Tồn kho" class="stock-inventory-table"/)
 assert.match(inventory,/<template #filters><StockScope /)
 assert.match(inventory,/@filter="\(\{field,values\}\)=>/)
 assert.match(inventory,/v-if="hasFilters" variant="outline" @click="clearFilters">Bỏ lọc/)
 // One topbar for every module: the /lotus shell owns it, Stock renders none of its own.
 assert.match(readFileSync(new URL('../src/App.vue',import.meta.url),'utf8'),/<WorkspaceBar [^>]*:actions="workspaceActions"/)
 assert.equal(app.includes('<WorkspaceBar'),false)
 for(const obsolete of ['stock-overview-metrics','stock-filter-panel','stock-filter-period','stock-welcome','Kỳ nhu cầu dự kiến','Dưới tồn tối thiểu']){
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
 assert.match(header,/excelAppliedValues\(choices\.value, selected\.value\)/)
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

test('table search works while typing without requiring Enter',()=>{
 assert.match(app,/watch\(searchDraft,value=>/)
 assert.match(app,/\},220\)/)
 assert.match(app,/v-model:search="searchDraft"/)
 assert.doesNotMatch(app,/@submit\.prevent="applySearch"/)
})

test('document history and stock ledger keep independent pagination',()=>{
 // Each list owns its offset, so paging one list never moves another.
 for(const name of ['StockInventory.vue','StockDocumentList.vue','StockLedger.vue']){
  const view=khoFile('components/stock/'+name)
  assert.match(view,/start=ref\(0\)/,name)
  assert.match(view,/@update:start="value=>\{start=value;load\(\)\}"/,name)
  assert.match(view,/start:start\.value/,name)
 }
})

test('internal demand default handles date boundaries even without extra UI',()=>{
 assert.equal(shiftISODate('2028-02-28',1),'2028-02-29')
 assert.equal(shiftISODate('2026-10-15',6),'2026-10-21')
 assert.equal(shiftISODate('',6),'')
})
