import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {excelPopupLeft} from '../src/excel-filter-state.js'
import {stockItemUomOptions,unitLabel} from '../src/units.js'

const stock=readFileSync(new URL('../src/StockApp.vue',import.meta.url),'utf8')
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
 assert.match(stock,/v-for="u in visibleUoms"/)
 assert.match(stock,/v-for="u in selectablePackUoms"/)
})

test('Four stock actions are quick buttons above the stock table and call existing stock forms',()=>{
 for(const kind of ['receipt','issue','transfer','count']){
   assert.match(stock,new RegExp("kind:'"+kind+"'"))
 }
 assert.match(stock,/const quickStockActions=/)
 assert.match(stock,/aria-label="Thao tác kho nhanh"/)
 assert.match(stock,/@click="quickAction\(action\.kind\)"/)
 assert.match(stock,/function quickAction\(kind\)|async function quickAction\(kind\)/)
 assert.match(stock,/buyingView\.value\?\.startReceiving\(\)/)
 assert.match(stock,/:disabled="!canCreate\|\|busy\|\|!session\?\.permissions/)
 const actionsIndex=stock.indexOf('aria-label="Thao tác kho nhanh"')
 const tableIndex=stock.indexOf('class="stock-panel stock-inventory-table"')
 assert.ok(actionsIndex>=0&&tableIndex>actionsIndex)
})

test('Stock columns prioritize item and group and use short Vietnamese wording',()=>{
 const def=stock.slice(stock.indexOf('const stockColumns=['),stock.indexOf('const historyRows='))
 const items=["headerName:'Tên hàng'","field:'item_group',headerName:'Nhóm hàng'","headerName:'ĐVT'","'Tồn kho'","headerName:'Tồn quy đổi'","'Tối thiểu chung'","'Cần dùng'","'Sắp về'","'Cần mua'"]
 let previous=-1
 for(const item of items){
  const at=def.indexOf(item)
  assert.ok(at>previous,'Column absent or out of order: '+item)
  previous=at
 }
 assert.match(def,/stockNumber\('shortage_qty','Thiếu tối thiểu'/)
 assert.match(def,/stockNumber\('demand_shortage_qty','Thiếu theo nhu cầu'/)
 assert.match(def,/field:'coverage_status',headerName:'Tình trạng nhu cầu'/)
})
