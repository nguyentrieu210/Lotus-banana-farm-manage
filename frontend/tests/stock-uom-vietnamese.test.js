import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {unitLabel,stockItemUomOptions} from '../src/units.js'

import {khoSource,khoFile} from './support/kho-source.mjs'
const stock=khoSource()

test('unused technical English UOMs are not listed for farm stock items',()=>{
 const rows=['Abampere','Atmosphere','Kg','Bao','Box','Nos','Chai','Gói','Bunch','Tree'].map(name=>({name}))
 assert.deepEqual(stockItemUomOptions(rows).map(x=>x.name),['Kg','Nos','Bao','Chai','Gói','Box','Bunch','Tree'])
 assert.ok(!stockItemUomOptions(rows).some(x=>x.name==='Abampere'))
 assert.ok(!stockItemUomOptions(rows).some(x=>x.name==='Atmosphere'))
})

test('UOM names display in Vietnamese while stored ERPNext IDs remain unchanged',()=>{
 assert.equal(unitLabel('Kg'),'kg')
 assert.equal(unitLabel('Bao'),'Bao')
 assert.equal(unitLabel('Box'),'Hộp / thùng')
 assert.equal(unitLabel('Nos'),'Cái')
 assert.equal(unitLabel('Bunch'),'Buồng')
 assert.equal(unitLabel('Tree'),'Cây')
 assert.equal(unitLabel('Chai'),'Chai')
 assert.equal(unitLabel('Gói'),'Gói')
})

test('editing historical item retains custom unit but never exposes unrelated odd units',()=>{
 const rows=['Kg','Bao','Custom Unit','Electrical Unit'].map(name=>({name}))
 assert.deepEqual(stockItemUomOptions(rows,['Custom Unit']).map(x=>x.name),['Kg','Bao','Custom Unit'])
})

test('both stock and packaging UOM selectors are curated and conversion is a visible stock column',()=>{
 assert.match(stock,/const uomOptions=computed\(\(\)=>stockItemUomOptions/)
 assert.match(stock,/v-model="master\.uom" label="Đơn vị tồn kho gốc" :options="uomOptions"/)
 assert.match(stock,/v-model="master\.pack_uom" label="Đơn vị đóng gói \/ quy đổi" :options="packOptions"/)
 assert.doesNotMatch(stock,/catalog\.uoms\.filter\(u=>u\.name!==master\.uom\)/)
 assert.match(stock,/field:'pack_actual_qty',headerName:'Tồn quy đổi'/)
 assert.match(stock,/minWidth:132,tooltipValueGetter:/)
 assert.ok(stock.indexOf("field:'pack_actual_qty'")>stock.indexOf("number('actual_qty'"))
})
