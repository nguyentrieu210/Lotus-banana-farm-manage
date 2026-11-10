import test from 'node:test'
import assert from 'node:assert/strict'
import {previewAmount,boardRows,wholeLot} from '../src/field-work-model.js'

test('money follows the pay mode of the phiếu',()=>{
 assert.equal(previewAmount({pay_mode:'Count',rate:4000},120),480000)
 assert.equal(previewAmount({pay_mode:'Lot',rate:300000,basis:'Area',lot_area_ha:4.48},1.2),1344000,'khoán lô: the whole lô')
 assert.equal(previewAmount({pay_mode:'Daywork',rate:0},10),0)
 assert.equal(wholeLot({basis:'Trees',lot_trees:10668}),10668)
})

test('board rows put each phiếu under its lô and việc, latest first',()=>{
 const rows=boardRows({blocks:[{name:'A8',block_code:'A8'}],cells:[{farm_block:'A8',work_type:'CL',assigned_on:'2026-10-01',display:'Locked'},{farm_block:'A8',work_type:'CL',assigned_on:'2026-10-20',display:'Working'}]})
 assert.deepEqual(rows[0].cells.CL.map(c=>c.display),['Working','Locked'])
})
