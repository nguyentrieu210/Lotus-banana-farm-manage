import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const root=new URL('../../',import.meta.url)
const read=p=>readFileSync(new URL(p,root),'utf8')
const entries=[
 ['main.js','App.vue'],['stock-main.js','StockApp.vue'],['assign-main.js','AssignApp.vue'],
 ['farm-work-main.js','FarmWorkApp.vue'],['hr-main.js','HrApp.vue'],['timekeeping-main.js','TimekeepingApp.vue']
]
test('mọi ứng dụng máy tính nạp đúng chuẩn Lotus, không tác động mobile Vant',()=>{
 for(const [main,app] of entries){
  assert.match(read('frontend/src/'+main),/desktop-system\.css/)
  assert.match(read('frontend/src/'+main),/desktop-components\.css/)
  assert.match(read('frontend/src/'+main),/desktop-shell\.css/)
  assert.match(read('frontend/src/'+app),/lotus-ui/)
 }
 for(const mobile of ['warehouse-mobile-main.js','buying-mobile-main.js','work-mobile-main.js']){
  const src=read('frontend/src/'+mobile)
  assert.doesNotMatch(src,/desktop-system\.css|desktop-shell\.css/)
 }
})
test('tokens và giao diện máy tính chỉ áp dụng khi khung nhìn đủ rộng',()=>{
 const css=read('frontend/src/desktop-system.css')
 assert.match(css,/@media \(min-width:901px\)/)
 assert.match(css,/\.lotus-ui\.app-shell/)
 assert.match(css,/\.lotus-ui\.stock-shell/)
 assert.match(css,/prefers-reduced-motion:reduce/)
 assert.match(css,/focus-visible/)
})
test('màn dự thu dùng các khối hiển thị chuẩn, biểu đồ được tải trễ',()=>{
 const src=read('frontend/src/components/ForecastPlanner.vue')
 assert.match(src,/DesktopPageHeading/)
 assert.match(src,/DesktopMetricCard/)
 assert.match(src,/DesktopEmptyState/)
 assert.match(src,/defineAsyncComponent\(\(\)=>import\('\.\/DesktopForecastChart\.vue'\)\)/)
 const chart=read('frontend/src/components/DesktopForecastChart.vue')
 assert.match(chart,/echarts\/core/)
 assert.match(chart,/actual_gross_kg/)
 assert.doesNotMatch(chart,/\.insert\(|\.save\(|frappe\.db/)
})
