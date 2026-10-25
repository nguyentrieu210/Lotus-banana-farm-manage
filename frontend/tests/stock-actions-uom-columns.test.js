import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {excelPopupLeft} from '../src/excel-filter-state.js'
import {stockItemUomOptions,unitLabel} from '../src/units.js'

import {khoSource,khoFile} from './support/kho-source.mjs'
const stock=khoSource()
const master=readFileSync(new URL('../../lotus_farm/warehouse_masters.py',import.meta.url),'utf8')
const excel=readFileSync(new URL('../src/components/ExcelHeader.vue',import.meta.url),'utf8')

test('Excel popup opens to the right and clamps at the viewport edge',()=>{
 assert.equal(excelPopupLeft(200,312,1200),208)
 assert.equal(excelPopupLeft(1190,312,1200),880)
 assert.equal(excelPopupLeft(15,304,320),8)
 assert.match(excel,/excelPopupLeft\(rect\.right, width, window\.innerWidth\)/)
})

test('Can can be chosen as base UOM or packaging UOM in Lotus Item',()=>{
 const rows=['Kg','Bao','Can','Litre','Abampere'].map(name=>({name}))
 assert.deepEqual(stockItemUomOptions(rows).map(row=>row.name),['Kg','Litre','Bao','Can'])
 assert.equal(unitLabel('Can'),'Can')
 assert.match(master,/for name in \('Bao', 'Can'\):/)
 assert.match(stock,/const uomOptions=computed\(\(\)=>stockItemUomOptions/)
 assert.match(stock,/const packOptions=computed\(\(\)=>uomOptions\.value\.filter\(u=>u\.value!==master\.uom\)\)/)
})

test('Four stock actions are quick buttons above the stock table and call existing stock forms',()=>{
 for(const kind of ['receipt','issue','transfer','count'])assert.match(stock,new RegExp("kind:'"+kind+"'"))
 const inventory=khoFile('components/stock/StockInventory.vue')
 assert.match(inventory,/aria-label="Thao tác kho nhanh"/)
 assert.match(inventory,/kind:'receipt-order',label:'Nhập theo đơn'/)
 assert.match(inventory,/:disabled="!canCreate\|\|!permissions\[action\.doctype\]"/)
 assert.ok(inventory.indexOf('<ListPage')<inventory.indexOf('Thao tác kho nhanh'),'actions sit in the list toolbar, above the table')
 // Receiving against a purchase order opens the shared picker; the other actions open the shared stock document form.
 assert.match(stock,/@receive="receivingView\.openPicker\(\)"/)
 assert.match(stock,/@create="kind=>documentForm\.open\(kind\)"/)
})

test('Stock columns prioritize item and group and use short Vietnamese wording',()=>{
 const columns=khoFile('stock-columns.js'),def=columns.slice(columns.indexOf('export const stockColumns=['),columns.indexOf('export function documentColumns'))
 const items=["headerName:'Tên hàng'","field:'item_group',headerName:'Nhóm hàng'","headerName:'ĐVT'","'Tồn kho'","headerName:'Tồn quy đổi'","'Tối thiểu chung'","'Cần dùng'","'Sắp về'","'Cần mua'"]
 let previous=-1
 for(const item of items){
  const at=def.indexOf(item)
  assert.ok(at>previous,'Column absent or out of order: '+item)
  previous=at
 }
 assert.match(def,/number\('shortage_qty','Thiếu tối thiểu'/)
 assert.match(def,/number\('demand_shortage_qty','Thiếu theo nhu cầu'/)
 assert.match(def,/field:'coverage_status',headerName:'Tình trạng nhu cầu'/)
})
