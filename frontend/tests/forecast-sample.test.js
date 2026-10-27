import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {sampleForecastCalendar} from '../src/forecast-sample.js'
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8')
test('dự thu mẫu có đủ 36 tháng và nguồn ưu tiên, hoàn toàn tách biệt với 64 lô thật',()=>{
 const r=sampleForecastCalendar('2026-10-17')
 assert.equal(r.months.length,36)
 assert.equal(r.from_date,'2026-10-01')
 assert.equal(r.to_date,'2029-09-30')
 assert.equal(r.summary.blocks,4)
 assert.ok(r.summary.gross_kg>0)
 assert.deepEqual([...new Set(r.rows.map(x=>x.source))].sort(),['cut','future','plant','shoot','sucker'])
 assert.ok(r.rows.every(x=>x.block_name.startsWith('[MẪU]') && x.commit_ready===false))
 assert.equal(r.summary.gross_kg,r.months.reduce((n,m)=>n+m.gross_kg,0))
 assert.equal(r.rows.length,new Set(r.rows.map(x=>x.farm_block+':'+x.cycle)).size)
})
test('nút mẫu phải có cảnh báo, không cho phát hành phiếu dự thu thật',()=>{
 const src=read('../src/components/ForecastPlanner.vue')
 const app=read('../src/App.vue')
 assert.match(src,/ĐANG XEM DỮ LIỆU MẪU/)
 assert.match(src,/demoMode/)
 assert.match(src,/sampleForecastCalendar/)
 assert.doesNotMatch(app,/<ForecastPlanner|forecast-legacy/)
 assert.doesNotMatch(app,/@demo-changed/)
})
test('tệp nhập ngày trồng chỉ xuất dữ liệu, không tự cập nhật',()=>{
 const server=read('../../lotus_farm/forecast_setup.py')
 assert.match(server,/has_permission\("Farm Block", "read"\)/)
 assert.match(server,/land_scope/)
 assert.match(server,/writer\.writerow/)
 assert.doesNotMatch(server,/\.insert\(|\.save\(|set_value|db\.sql\(/)
})
