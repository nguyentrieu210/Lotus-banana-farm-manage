import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {
 STOCK_QUICK_FILTERS,updateColumnFilter,toggleStockQuickFilter,
 shiftISODate,hasStockSearchFilters,stockEmptyKind
} from '../src/stock-filter-state.js'

const app=readFileSync(new URL('../src/StockApp.vue',import.meta.url),'utf8')
const head=readFileSync(new URL('../src/components/ExcelHeader.vue',import.meta.url),'utf8')
const backend=readFileSync(new URL('../../lotus_farm/warehouse.py',import.meta.url),'utf8')

test('quick filters switch instead of silently stacking contradictory statuses',()=>{
 const initial={item_group:['Fertilizer'],stock_status:['Dưới tối thiểu']}
 const next=toggleStockQuickFilter(initial,'demand')
 assert.deepEqual(next,{item_group:['Fertilizer'],coverage_status:['Cần mua','Chờ nhập']})
 const cleared=toggleStockQuickFilter(next,'demand')
 assert.deepEqual(cleared,{item_group:['Fertilizer']})
 assert.deepEqual(toggleStockQuickFilter({},'minimum'),{stock_status:['Dưới tối thiểu']})
 assert.deepEqual(STOCK_QUICK_FILTERS.minimum.values,['Dưới tối thiểu'])
})

test('individual column filter clears without destroying unrelated filters',()=>{
 assert.deepEqual(updateColumnFilter({item_group:['A'],stock_status:['Dưới tối thiểu']},'item_group',null),{stock_status:['Dưới tối thiểu']})
 assert.deepEqual(updateColumnFilter({},'coverage_status',['Cần mua']),{coverage_status:['Cần mua']})
 assert.equal(hasStockSearchFilters(' phân ',{}),true)
 assert.equal(hasStockSearchFilters('',{}),false)
})

test('all selected values do not create a phantom Excel header filter',()=>{
 assert.match(head,/values\.length===choices\.value\.length\?null:values/)
})

test('empty inventory catalogue and no matches are distinct states',()=>{
 const defaults={company:'Lotus Agritech',warehouseCount:4,catalogueCount:55,filteredCount:0,loading:false}
 assert.equal(stockEmptyKind(defaults),'no-matches')
 assert.equal(stockEmptyKind({...defaults,catalogueCount:0}),'no-items')
 assert.equal(stockEmptyKind({...defaults,warehouseCount:0}),'no-warehouse')
 assert.equal(stockEmptyKind({...defaults,filteredCount:5}),'results')
 assert.equal(stockEmptyKind({...defaults,loading:true}),'loading')
 assert.equal(stockEmptyKind({...defaults,company:''}),'no-company')
})

test('demand presets are calendar-correct across leap years',()=>{
 assert.equal(shiftISODate('2028-02-28',1),'2028-02-29')
 assert.equal(shiftISODate('2026-10-15',6),'2026-10-21')
 assert.equal(shiftISODate('',6),'')
})

test('unfiltered catalog KPIs are separate from result counts in API and UI',()=>{
 assert.match(backend,/catalogue_count=catalogue_count,stocked_count=stocked_count/)
 assert.match(app,/data\.catalogue_count\?\?0/)
 assert.match(app,/data\.total_count\?\?0/)
 assert.doesNotMatch(app,/!stocks\.length\)\&\&tab===/)
 assert.match(app,/stockState==='no-matches'/)
})

test('search applies only on submission and resets cleanly',()=>{
 assert.match(app,/const session=ref\(null\).*searchDraft=ref\(''\)/)
 assert.match(app,/function applySearch\(\)\{search\.value=searchDraft\.value\.trim\(\);refresh\(true\)\}/)
 assert.match(app,/@submit\.prevent="applySearch"/)
 assert.match(app,/v-model="searchDraft"/)
})

test('filter headers remain accessible with zero results; document and movement pagers are independent',()=>{
 assert.match(app,/:show-empty-headers="\(data\?\.catalogue_count\?\?0\)>0"/)
 assert.match(app,/start:documentStart\.value/)
 assert.match(app,/@click="documentStart-=50;refresh\(\)"/)
 assert.match(app,/@click="movementStart-=50;refresh\(\)"/)
})
