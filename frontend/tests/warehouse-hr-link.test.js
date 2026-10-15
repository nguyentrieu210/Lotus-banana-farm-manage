import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const stock=readFileSync(new URL('../src/StockApp.vue',import.meta.url),'utf8')
const picker=readFileSync(new URL('../src/components/LinkPicker.vue',import.meta.url),'utf8')
const centered=readFileSync(new URL('../src/warehouse-table-center.css',import.meta.url),'utf8')

test('warehouse managers and issue receivers use HRMS Employee links',()=>{
 assert.match(stock,/v-model="master\.lotus_contact_employee"/)
 assert.match(stock,/v-model="form\.receiver_employee"/)
 assert.doesNotMatch(stock,/v-model="master\.lotus_contact_name"/)
 assert.doesNotMatch(stock,/v-model="form\.receiver"[^_]/)
 assert.match(stock,/employee\.label/)
})

test('warehouse code is derived from entered name and company abbreviation',()=>{
 assert.match(stock,/const warehouseCode=computed/)
 assert.match(stock,/:model-value="warehouseCode"/)
})

test('selected link shows display label instead of stored identifier',()=>{
 assert.match(picker,/chosenLabel\.value=\{value:row\.value,label:row\.label/)
 assert.match(picker,/:value="isOpen\?query:shownValue"/)
 assert.match(stock,/:display-value="row\.item_name/)
})

test('all StockApp table cells and headers are center-aligned',()=>{
 assert.match(centered,/\.stock-shell \.lotus-ag-grid \.ag-cell/)
 assert.match(centered,/text-align:center/)
 assert.match(centered,/\.excel-sort/)
})
