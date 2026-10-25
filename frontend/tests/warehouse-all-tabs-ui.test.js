import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

import {khoSource,khoFile} from './support/kho-source.mjs'
const stock=khoSource()
const planning=readFileSync(new URL('../src/components/WarehousePlanning.vue',import.meta.url),'utf8')
const css=readFileSync(new URL('../src/warehouse-workspace-audit.css',import.meta.url),'utf8')
const planningAPI=readFileSync(new URL('../../lotus_farm/warehouse_planning.py',import.meta.url),'utf8')

test('all operational stock lists share the compact filter bar and Excel table headers',()=>{
 for(const name of ['StockInventory.vue','StockDocumentList.vue','StockLedger.vue','StockReport.vue','StockMasterList.vue']){
  const view=khoFile('components/stock/'+name)
  assert.match(view,/<ListPage /,name+' uses the shared list page')
  assert.match(view,/show-empty-headers/,name)
 }
 for(const name of ['StockDocumentList.vue','StockLedger.vue']){
  const view=khoFile('components/stock/'+name)
  assert.match(view,/<StockScope dates /,name+' filters by date range')
  assert.match(view,/:filter-values="data\?\.filter_values"/,name)
  assert.match(view,/function clearFilters\(\)/,name)
 }
 assert.doesNotMatch(stock,/class="movement-filters"/)
})

test('document & movement columns use readable concise Vietnamese labels',()=>{
 const columns=khoFile('stock-columns.js'),section=columns.slice(columns.indexOf('export function documentColumns'),columns.indexOf('export function receiptDetailColumns'))
 for(const label of ['Số phiếu','Loại phiếu','Kho liên quan','Tồn trước','Tồn sau','Tên hàng','ĐVT']){
  assert.ok(section.includes(label),'Missing clear header: '+label)
 }
 assert.match(columns,/valueFormatter:p=>formatDate\(p\.value\)/)
 assert.match(columns,/String\(p\.value\|\|''\)\.split\(' · '\)\.map\(warehouseLabel\)/)
})

test('purchase and demand use same live search and Excel-style table filters',()=>{
 assert.match(planning,/watch\(searchDraft,value=>/)
 assert.match(planning,/\},220\)/)
 // One shared list page for demand, purchase requests and orders: live search, date range and Excel-style filters.
 assert.match(planning,/<ListPage /)
 assert.match(planning,/v-model:search="searchDraft"/)
 assert.match(planning,/<DateRangePicker v-model:from="from" v-model:to="to"\/>/)
 assert.match(planning,/function resetFilters\(\)/)
 assert.match(planning,/:filter-values="view==='coverage'\?data\?\.filter_values:undefined"/)
 assert.match(planning,/else if\(view\.value==='requests'\)openRequest\(row\.name\);else openOrder\(row\.name\)/)
 assert.match(planning,/const unit=unitLabel/)
 assert.match(planningAPI,/faceted_distinct\(rows,fields,selected/)
})

test('warehouse setup is table-first with small action buttons, not onboarding cards',()=>{
 const masters=khoFile('components/stock/StockMasterList.vue')
 assert.match(masters,/<ListPage /)
 for(const label of ['Thêm kho','Thêm vật tư','Thêm nhóm vật tư','Thêm đơn vị tính'])assert.ok(masters.includes(label),label)
 assert.match(masters,/interactive [^>]*@open="row=>emit\('edit-master',info\.master,row\.name\)"/)
 assert.doesNotMatch(stock,/<UiCard>/)
})

test('stock voucher forms retain required details and group their controls',()=>{
 const form=khoFile('components/stock/StockDocumentForm.vue'),detail=khoFile('components/stock/StockDocumentDetail.vue')
 assert.match(form,/<ModalForm /)
 assert.match(form,/@submit="save"/)
 assert.match(detail,/@submit="post"/)
 assert.match(form,/<FormSection title="Thông tin phiếu">/)
 assert.match(form,/<LineItemsEditor v-model="form\.lines" title="Hàng hóa trên phiếu"/)
 assert.match(form,/v-model="form\.receiver_employee"/)
 assert.match(form,/field:'rate'/)
 assert.match(form,/class="lotus-modal-form__description"/)
})
