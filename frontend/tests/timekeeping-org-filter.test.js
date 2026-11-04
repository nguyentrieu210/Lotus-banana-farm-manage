import test from 'node:test'
import assert from 'node:assert/strict'
import {organizationOf,filterAttendanceOrganization,organizationOptions,UNASSIGNED} from '../src/attendance-org-filters.js'

const parents={
 'Ban quản lý vườn - LT':'All Departments',
 'Bộ phận vật tư - LT':'Ban quản lý vườn - LT',
 'Phòng Kỹ thuật Vườn - LT':'Ban quản lý vườn - LT',
 'Production - LT':'All Departments',
}
const rows=[
 {employee:'E1',designation:'Thủ kho',department:'Bộ phận vật tư - LT',selected:false},
 {employee:'E2',designation:'Kỹ thuật viên',department:'Phòng Kỹ thuật Vườn - LT',selected:false},
 {employee:'E3',designation:'Giám đốc',department:'Ban quản lý vườn - LT',selected:false},
 {employee:'E4',designation:'Công nhân',department:'Production - LT',selected:false},
 {employee:'E5',designation:'Công nhân',department:'',selected:false},
]
test('department hierarchy separates parent phòng ban and child bộ phận',()=>{
 assert.deepEqual(organizationOf(rows[0],parents),{
  designation:'Thủ kho',department:'Ban quản lý vườn - LT',division:'Bộ phận vật tư - LT'})
 assert.deepEqual(organizationOf(rows[3],parents),{
  designation:'Công nhân',department:'Production - LT',division:''})
})
test('combining all 3 filters returns only the correct employee',()=>{
 const match=filterAttendanceOrganization(rows,{
  designation:'Thủ kho',department:'Ban quản lý vườn - LT',division:'Bộ phận vật tư - LT'},parents)
 assert.deepEqual(match.map(r=>r.employee),['E1'])
 assert.deepEqual(filterAttendanceOrganization(rows,{department:'Ban quản lý vườn - LT'},parents).map(r=>r.employee),['E1','E2','E3'])
})
test('unassigned employees can be filtered without disappearing by default',()=>{
 assert.equal(filterAttendanceOrganization(rows,{},parents).length,5)
 assert.deepEqual(filterAttendanceOrganization(rows,{department:UNASSIGNED},parents).map(r=>r.employee),['E5'])
 assert.deepEqual(filterAttendanceOrganization(rows,{division:UNASSIGNED},parents).map(r=>r.employee),['E3','E4','E5'])
})
test('options come from actual employees rather than full master table',()=>{
 const options=organizationOptions(rows,'division',parents,'Chưa phân bộ phận')
 assert.equal(options[0].value,UNASSIGNED)
 assert.ok(options.some(o=>o.value==='Bộ phận vật tư - LT'))
 assert.ok(!options.some(o=>o.value==='Bộ phận văn phòng - LT'))
})
