import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const table=readFileSync(new URL('../src/components/DataTable.vue',import.meta.url),'utf8')
const attendance=readFileSync(new URL('../src/TimekeepingApp.vue',import.meta.url),'utf8')
const styles=readFileSync(new URL('../src/timekeeping.css',import.meta.url),'utf8')
const pager=readFileSync(new URL('../src/components/ui/pagination/Pagination.vue',import.meta.url),'utf8')

test('attendance uses one checkbox column and links to the same employee selection as save/approve',()=>{
 const columns=attendance.slice(attendance.indexOf('const attendanceColumns='),attendance.indexOf('const rowState='))
 assert.doesNotMatch(columns,/field:'selected',headerName:'Chọn'/)
 assert.doesNotMatch(attendance,/label="Chọn tất cả nhân viên đang hiện"/)
 assert.match(attendance,/:selected-row-keys="selected.map\(row=>row.employee\)"/)
 assert.match(attendance,/@row-selection-change="selectAttendanceRow"/)
 assert.match(attendance,/@page-selection-change="selectAttendancePage"/)
 assert.match(attendance,/@selection-clear="clearAttendanceSelection"/)
 assert.match(attendance,/function chooseStaffRows\(rows,selectedValue\)/)
 assert.match(attendance,/const selected=computed\(\(\)=>staff.value.filter\(r=>r.selected\)\)/)
 assert.match(attendance,/const rows=selected.value.filter\(/)
})
test('two shared utility columns are compact and totals label is not placed in a checkbox cell',()=>{
 assert.match(table,/const selectDef=\{colId:'__lotus_select',headerName:'Chọn',width:42,minWidth:42,maxWidth:42/)
 assert.match(table,/const sttDef=\{colId:'__lotus_stt',headerName:'STT',width:52,minWidth:52,maxWidth:52/)
 assert.match(table,/totalsRow\(props.columns.filter\(c=>columnId\(c\)!==nativeSelectId.value\)/)
 assert.match(table,/const gridDefs=computed/)
})
test('attendance scroll exists only in the shared grid, not nested in the panel',()=>{
 assert.match(styles,/\.tk-roster\{overflow:visible;padding:0\}/)
 assert.match(table,/class="lotus-ag-grid-shell"/)
})
test('single page still displays range without disabled previous/next buttons',()=>{
 assert.match(pager,/<PaginationRoot v-if="total && total>pageSize"/)
 assert.match(pager,/<div v-else-if="!total&&\(start>0\|\|hasMore\)"/)
})
