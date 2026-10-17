import {test} from 'node:test'
import assert from 'node:assert/strict'
import {forecastStates,filterForecasts,blockTotals,peakWeek,percent,kg} from '../src/forecast-planning.js'
const rows=[
 {name:'HF-1',farm:'Vườn 222 Thuận Phú',farm_block:'Lô 01',crop_cycle:'Vụ 1',supply_state:'Released',gross_forecast_kg:16000,packed_forecast_kg:10000,available_to_promise_kg:8000,expected_harvest_bunch_qty:700,actual_gross_kg:500},
 {name:'HF-2',farm:'Vườn 222 Thuận Phú',farm_block:'Lô 01',crop_cycle:'Vụ 1',supply_state:'Superseded',gross_forecast_kg:17000,packed_forecast_kg:11000,available_to_promise_kg:11000},
 {name:'HF-3',farm:'Vườn 180 Thuận Phú',farm_block:'Lô 02',crop_cycle:'Vụ 1',supply_state:'Draft',gross_forecast_kg:14000,packed_forecast_kg:9000,available_to_promise_kg:9000},
 {name:'HF-4',farm:'Vườn 180 Thuận Phú',farm_block:'Lô 02',crop_cycle:'Vụ 1',supply_state:'Released',gross_forecast_kg:12000,packed_forecast_kg:7500,available_to_promise_kg:7000,expected_harvest_bunch_qty:500},
]
test('trạng thái thân thiện',()=>assert.equal(forecastStates.Superseded,'Đã thay thế'))
test('lọc đồng thời lô/trạng thái và tìm không phân biệt chữ',()=>{
 assert.deepEqual(filterForecasts(rows,{state:'Released',block:'Lô 01',query:'hf-1'}).map(r=>r.name),['HF-1'])
 assert.equal(filterForecasts(rows,{query:'vườn 180'}).length,2)
 assert.equal(filterForecasts(rows,{query:'không tìm thấy'}).length,0)
})
test('không cộng trùng bản nháp và bản đã thay thế',()=>{
 const totals=blockTotals(rows)
 assert.equal(totals.length,2)
 assert.equal(totals.find(r=>r.farm_block==='Lô 01').gross,16000)
 assert.equal(totals.find(r=>r.farm_block==='Lô 01').available,8000)
 assert.equal(totals.reduce((s,r)=>s+r.packed,0),17500)
})
test('thang biểu đồ có ngưỡng hợp lý và không chia 0',()=>{
 assert.equal(peakWeek([]),1)
 assert.equal(peakWeek([{packed_kg:50,gross_kg:80,actual_gross_kg:30}]),80)
 assert.equal(percent(20,80),25)
 assert.equal(percent(-10,80),0)
 assert.equal(percent(180,80),100)
})
test('định dạng kg không ghi số giả cho chưa có quyền',()=>{assert.equal(kg(null),'—');assert.equal(kg(1200),'1.200')})
