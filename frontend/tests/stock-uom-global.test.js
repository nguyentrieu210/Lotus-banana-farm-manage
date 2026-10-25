import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const ui=readFileSync(new URL('../src/StockApp.vue',import.meta.url),'utf8')
const api=readFileSync(new URL('../../lotus_farm/warehouse.py',import.meta.url),'utf8')
const config=readFileSync(new URL('../../lotus_farm/warehouse_masters.py',import.meta.url),'utf8')

test('new item has global minimum without choosing a warehouse',()=>{
 assert.match(ui,/Tồn tối thiểu chung toàn bộ kho/)
 assert.doesNotMatch(ui,/v-model="master\.minimum_warehouse"/)
 assert.match(config,/lotus_minimum_stock_global/)
 assert.match(api,/global_qty=sum\(/)
 assert.match(api,/item\.shortage_qty=max\(0,item\.minimum_stock-global_qty\)/)
})

test('new item uses ERPNext Item UOM Conversion Detail',()=>{
 assert.match(ui,/v-model="master\.pack_uom"/)
 assert.match(ui,/v-model\.number="master\.pack_factor"/)
 assert.match(config,/item\.append\('uoms'/)
 assert.match(config,/conversion_factor=factor/)
 assert.match(config,/for name in \('Bao', 'Can'\):/)
 assert.match(config,/uom_name=name/)
})

test('receipt permits package quantities and correctly scales entered unit prices',()=>{
 assert.match(ui,/Đơn vị nhập hàng/)
 assert.match(ui,/row\.stock_uom/)
 assert.match(api,/entry_uom=str\(row\.get\('uom'\)/)
 assert.match(api,/values\['basic_rate'\] = rate\/factor/)
 assert.match(api,/basic_total \+= qty \* rate/)
 assert.match(api,/doc\.stock_entry_type!='Material Receipt'/)
})
