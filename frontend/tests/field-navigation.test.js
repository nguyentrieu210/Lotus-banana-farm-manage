import test from 'node:test'
import assert from 'node:assert/strict'
import {fieldNavigation,visibleFieldNavigation,normalizeFieldView,fieldQuery} from '../src/field-report-navigation.js'
import {navGroups,pages} from '../src/domain.js'

const field={capabilities:{field_report:true}}

test('the field area has at most 7 menu entries, setup counted as one',()=>{
 const menu=visibleFieldNavigation(field)
 const top=menu.filter(r=>!r.setup).map(r=>r.label)
 assert.deepEqual(top,['Hôm nay','Giao việc','Màu dây & thu hoạch','Xưởng','Dự thu','Báo cáo'])
 assert.ok(top.length+(menu.some(r=>r.setup)?1:0)<=7)
 assert.deepEqual(menu.filter(r=>r.setup).map(r=>r.label),['Đội, tổ & lô','Việc & cách trả','Bảng giá khoán','Vòng chăm sóc','Màu dây cắt bắp','Tham số dự thu'])
})

test('nghiệm thu and tiền khoán theo người stay reachable without a menu entry',()=>{
 const menu=visibleFieldNavigation(field).map(r=>r.id)
 for(const id of ['inspect','payable']){assert.ok(!menu.includes(id),id);assert.equal(normalizeFieldView(id),id)}
 assert.equal(normalizeFieldView('bunch'),'today','old links open Hôm nay')
 assert.equal(normalizeFieldView('board'),'today')
})

test('Dự thu and the ribbon catalogue keep their pages; others without the field capability still see them',()=>{
 assert.deepEqual(fieldQuery('forecast-params'),{tab:'profiles'})
 assert.deepEqual(fieldQuery('reports'),{field_view:'reports'})
 assert.deepEqual(fieldQuery('forecast'),{})
 assert.deepEqual(visibleFieldNavigation({capabilities:{}}).map(r=>r.path),['forecast','mau-day','forecast'])
 assert.ok(fieldNavigation.filter(r=>r.path!=='cong-viec').every(r=>pages.some(([p])=>p===r.path)))
})

test('no separate group for the old pivot reports or for Dự thu',()=>{
 assert.ok(!navGroups.some(g=>g.label==='Báo cáo công việc'))
 assert.ok(!navGroups.some(g=>g.label==='Dự thu'))
 assert.ok(!pages.some(([p])=>p.startsWith('bao-cao-')))
})
