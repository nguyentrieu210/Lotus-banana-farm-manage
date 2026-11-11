import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const root = new URL('../../', import.meta.url)
const read = p => readFileSync(new URL(p,root),'utf8')
test('lô có thể khai ngày trồng mà chưa phải tạo hồ sơ vụ',()=>{
 const doc=JSON.parse(read('lotus_farm/lotus_farm/doctype/farm_block/farm_block.json'))
 assert.equal(doc.fields.find(x=>x.fieldname==='planting_date')?.fieldtype,'Date')
})
test('màn chính chỉ dùng nguồn dự thu lô 36 tháng',()=>{
 const app=read('frontend/src/App.vue'), ui=read('frontend/src/BlockForecastApp.vue')
 assert.match(app,/import\('\.\/BlockForecastApp\.vue'\)/)
 assert.match(ui,/lotus_farm\.block_forecast\.board/)
 assert.doesNotMatch(app,/forecast_calendar\.calendar|forecast_workspace\.board|<ForecastPlanner|forecast-legacy/)
})
