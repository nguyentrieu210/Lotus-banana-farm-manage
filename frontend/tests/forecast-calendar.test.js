import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const root = new URL('../../', import.meta.url)
const read = p => readFileSync(new URL(p,root),'utf8')
test('bộ hệ số có ngày trồng và chu kỳ vụ chồi nhưng không gán số mặc định',()=>{
 const doc = JSON.parse(read('lotus_farm/lotus_farm/doctype/harvest_profile/harvest_profile.json'))
 for(const name of ['planting_to_harvest_days','ratoon_interval_days']){
  const f = doc.fields.find(x=>x.fieldname===name)
  assert.equal(f?.fieldtype,'Int')
  assert.equal(f?.default,undefined)
 }
})
test('lô có thể khai ngày trồng mà chưa phải tạo hồ sơ vụ',()=>{
 const doc=JSON.parse(read('lotus_farm/lotus_farm/doctype/farm_block/farm_block.json'))
 assert.equal(doc.fields.find(x=>x.fieldname==='planting_date')?.fieldtype,'Date')
 assert.match(read('lotus_farm/forecast_calendar.py'),/block_row\.planting_date/)
})
test('màn chính chỉ dùng nguồn dự thu lô 36 tháng',()=>{
 const app=read('frontend/src/App.vue'), ui=read('frontend/src/BlockForecastApp.vue')
 assert.match(app,/import\('\.\/BlockForecastApp\.vue'\)/)
 assert.match(ui,/lotus_farm\.block_forecast\.board/)
 assert.doesNotMatch(app,/forecast_calendar\.calendar|forecast_workspace\.board|<ForecastPlanner|forecast-legacy/)
})

test('màn kế hoạch không gọi phát hành hàng hóa',()=>{
 const ui=read('frontend/src/components/ForecastPlanner.vue')
 assert.match(ui,/Dự thu 3 năm/)
 assert.match(ui,/chưa chốt/)
 assert.doesNotMatch(ui,/releaseForecast|stock_entry|Released/)
})
