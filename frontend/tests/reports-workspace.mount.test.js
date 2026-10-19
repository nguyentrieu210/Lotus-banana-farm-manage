import test from 'node:test'
import assert from 'node:assert/strict'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,mount,tick,window} from './support/mount.mjs'

const ReportsWorkspace=await load('components/ReportsWorkspace.vue')
const LotusChart=await load('components/LotusChart.vue')
const charts={from_date:'2026-09-20',to_date:'2026-10-19',farms:['LOTUS-222'],
 land:{allowed:true,blocks:3,area_ha:10,trees:15000,counted_blocks:2,
  zones:[{zone:'A',blocks:2,area_ha:6,trees:15000,counted_blocks:2,counted_area_ha:6,trees_per_ha:2500},{zone:'B',blocks:1,area_ha:4,trees:0,counted_blocks:0,counted_area_ha:0,trees_per_ha:null}],
  flowering:[{month:'2026-11',blocks:2,trees:15000}]},
 work:{allowed:true,days:[{date:'2026-10-19',tasks:0,completion_percent:null,required_workdays:0,actual_workdays:0}],types:[]},
 harvest:{allowed:false},losses:{allowed:true,reasons:[],total:0},stock:{allowed:true,months:[]}}
const text=root=>root.textContent.replace(/\s+/g,' ')
const tab=(root,label)=>[...root.querySelectorAll('[role=tab]')].find(b=>b.textContent===label)

test('land tab shows census figures and only counted zones in density',async()=>{
 const view=mount(ReportsWorkspace,{charts});await tick();tab(view.root,'Vườn & cây').click();await tick()
 const stats=[...view.root.querySelectorAll('.lotus-stat strong')].map(n=>n.textContent)
 assert.deepEqual(stats.slice(0,3),['10','15.000','2.500'],'area, trees, density from counted blocks only (15000/6)')
 const titles=[...view.root.querySelectorAll('.lotus-chart-head h3')].map(n=>n.textContent)
 assert.deepEqual(titles,['Số cây theo khu','Diện tích theo khu','Mật độ cây theo khu','Lịch trổ dự kiến'])
 assert.match(text(view.root),/Kỳ báo cáo: 20\/09\/2026 – 19\/10\/2026/)
 view.unmount()
})

test('tabs without data explain why, and denied sections show no numbers',async()=>{
 const view=mount(ReportsWorkspace,{charts});await tick()
 tab(view.root,'Công việc').click();await tick()
 assert.match(text(view.root),/Chưa có kế hoạch công việc đã giao trong kỳ\./)
 assert.equal(view.root.querySelectorAll('.lotus-chart-canvas').length,0,'no empty canvas is drawn')
 tab(view.root,'Thu hoạch & đóng gói').click();await tick()
 assert.match(text(view.root),/Bạn không có quyền xem phần báo cáo này\./)
 assert.equal(view.root.querySelectorAll('.lotus-stat').length,0)
 view.unmount()
})

// Happy DOM has no 2D canvas; a no-op context lets echarts initialise so the chart path itself is exercised.
function fakeCanvas(){
 const proto=window.HTMLCanvasElement.prototype,original=proto.getContext
 const ctx=new Proxy({},{get:(t,key)=>key==='measureText'?()=>({width:0}):key in t?t[key]:()=>{},set:(t,key,v)=>{t[key]=v;return true}})
 proto.getContext=()=>ctx
 return ()=>{proto.getContext=original}
}

test('chart offers a table view with the same numbers',async()=>{
 const restore=fakeCanvas()
 const view=mount(LotusChart,{title:'Số cây theo khu',categories:['Khu A','Khu B'],series:[{name:'Số cây',data:[15000,5000]}],unit:'cây'});await tick()
 const toggle=view.root.querySelector('.lotus-chart-head button')
 assert.equal(toggle.textContent,'Xem bảng số liệu')
 toggle.click();await tick()
 const rows=[...view.root.querySelectorAll('.lotus-chart-table tbody tr')].map(r=>[...r.children].map(c=>c.textContent))
 assert.deepEqual(rows,[['Khu A','15.000'],['Khu B','5.000']])
 assert.equal(view.root.querySelector('.lotus-chart-table thead').textContent,'Số cây (cây)')
 view.unmount()
 const empty=mount(LotusChart,{title:'Rỗng',categories:['T1'],series:[{name:'X',data:[0]}],empty:'Không có số.'});await tick()
 assert.equal(empty.root.querySelector('.lotus-chart-empty').textContent,'Không có số.')
 assert.equal(empty.root.querySelector('.lotus-chart-head button'),null)
 empty.unmount()
 restore()
})

test('without a usable canvas the chart falls back to its table',async()=>{
 const view=mount(LotusChart,{title:'Kho',categories:['10/26'],series:[{name:'Nhập',data:[10]},{name:'Xuất',data:[1]}],unit:'phiếu'});await tick()
 assert.equal(view.root.querySelector('.lotus-chart-head button'),null,'no toggle when only the table can be shown')
 assert.deepEqual([...view.root.querySelectorAll('.lotus-chart-table tbody td')].map(c=>c.textContent),['10','1'])
 view.unmount()
})
