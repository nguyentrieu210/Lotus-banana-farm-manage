import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

import {khoSource,khoFile} from './support/kho-source.mjs'
const stock=khoSource()
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
 // LinkPicker wraps the shared Combobox, which remembers the chosen row and shows its label
 const combobox=readFileSync(new URL('../src/components/ui/combobox/Combobox.vue',import.meta.url),'utf8')
 assert.match(picker,/<Combobox /)
 assert.match(combobox,/chosen\.value=row/)
 assert.match(combobox,/const shown=\(\)=>props\.displayValue\|\|current\.value\?\.label/)
 assert.match(stock,/displayValue:r=>r\.item_name/)
})

test('all StockApp table cells and headers are center-aligned',()=>{
 assert.match(centered,/\.stock-shell \.lotus-ag-grid \.ag-cell/)
 assert.match(centered,/text-align:center/)
 assert.match(centered,/\.excel-sort/)
})
