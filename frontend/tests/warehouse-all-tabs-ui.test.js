import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const stock=readFileSync(new URL('../src/StockApp.vue',import.meta.url),'utf8')
const planning=readFileSync(new URL('../src/components/WarehousePlanning.vue',import.meta.url),'utf8')
const css=readFileSync(new URL('../src/warehouse-workspace-audit.css',import.meta.url),'utf8')
const planningAPI=readFileSync(new URL('../../lotus_farm/warehouse_planning.py',import.meta.url),'utf8')

test('all operational stock lists share the compact filter bar and Excel table headers',()=>{
 assert.match(stock,/class="stock-scope"/)
 assert.match(stock,/class="stock-date-filters"/)
 assert.doesNotMatch(stock,/class="movement-filters"/)
 assert.match(stock,/<DataTable :rows="historyRows" :columns="historyColumns" show-empty-headers/)
 assert.match(stock,/<DataTable :rows="movementData\?\.rows\|\|\[\]" :columns="movementColumns" show-empty-headers/)
 assert.match(stock,/v-if="\['stock','history'\]\.includes\(tab\)" class="stock-quick-actions"/)
 assert.match(stock,/function clearTabFilters\(\)/)
 assert.match(stock,/:filter-values="documentData\?\.filter_values"/)
 assert.match(stock,/:filter-values="movementData\?\.filter_values"/)
})

test('document & movement columns use readable concise Vietnamese labels',()=>{
 const section=stock.slice(stock.indexOf('const historyColumns='),stock.indexOf('const receiptDetailColumns='))
 for(const label of ['Số phiếu','Loại phiếu','Kho liên quan','Tồn trước','Tồn sau','Tên hàng','ĐVT']){
  assert.ok(section.includes(label),'Missing clear header: '+label)
 }
 assert.match(stock,/dateLabel=value=>/)
 assert.match(stock,/String\(p\.value\|\|''\)\.split\(' → '\)\.map\(warehouseLabel\)/)
})

test('purchase and demand use same live search and Excel-style table filters',()=>{
 assert.match(planning,/watch\(searchDraft,value=>/)
 assert.match(planning,/\},220\)/)
 assert.match(planning,/stock-date-filters stock-planning-toolbar/)
 assert.match(planning,/class="stock-search stock-search--instant"/)
 assert.match(planning,/function resetFilters\(\)/)
 assert.match(planning,/:filter-values="data\?\.filter_values"/)
 assert.match(planning,/show-empty-headers :loading="busy" interactive @open="row=>openRequest/)
 assert.match(planning,/show-empty-headers :loading="busy" interactive @open="row=>openOrder/)
 assert.match(planning,/const unit=unitLabel/)
 assert.match(planningAPI,/faceted_distinct\(rows,fields,selected/)
})

test('warehouse setup is table-first with small action buttons, not onboarding cards',()=>{
 assert.match(stock,/class="stock-setup-toolbar"/)
 assert.match(stock,/class="stock-setup-grids"/)
 assert.match(stock,/>\+ Thêm nhóm hàng</)
 assert.match(stock,/>\+ Thêm vật tư</)
 assert.match(stock,/>\+ Thêm kho</)
 assert.match(stock,/show-empty-headers interactive @open="row=>editMaster\('warehouse'/)
 assert.doesNotMatch(stock,/<UiCard>/)
})

test('stock voucher forms retain required details and group their controls',()=>{
 assert.match(stock,/class="stock-form-help"/)
 assert.match(stock,/class="stock-form-section-title"/)
 assert.match(stock,/@submit\.prevent="save"/)
 assert.match(stock,/@submit\.prevent="postDocument"/)
 assert.match(stock,/v-model="form\.receiver_employee"/)
 assert.match(stock,/v-model\.number="row\.rate"/)
 assert.match(css,/\.stock-dialog \.stock-form-grid/)
 assert.match(css,/\.stock-setup-grids/)
})
