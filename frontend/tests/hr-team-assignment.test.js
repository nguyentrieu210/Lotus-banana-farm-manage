import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {hrHref,hrNavigation,normalizeHrView} from '../src/hr-navigation.js'

const hr=readFileSync(new URL('../src/HrApp.vue',import.meta.url),'utf8')
const attendance=readFileSync(new URL('../src/TimekeepingApp.vue',import.meta.url),'utf8')
const assignment=readFileSync(new URL('../src/components/HrTeamAssignments.vue',import.meta.url),'utf8')

test('Phân tổ is a dedicated HR destination, not attendance',()=>{
 const item=hrNavigation.find(v=>v.id==='teams')
 assert.ok(item)
 assert.equal(item.label,'Phân tổ/đội')
 assert.equal(hrHref(item),'/lotus/nhan-su?hr_view=teams')
 assert.equal(normalizeHrView('teams'),'teams')
 assert.match(hr,/<HrTeamAssignments v-if="tab==='teams'"/)
 assert.doesNotMatch(attendance,/class="tk-team-org"/)
 assert.doesNotMatch(attendance,/v-model="teamFilter"/)
})
test('HR team screen shows actual employees, teams, and supports bulk assignment',()=>{
 assert.match(assignment,/lotus_farm\.hr_workspace\.assign_teams/)
 assert.match(assignment,/t\.lotus_team_type==='Internal'/)
 assert.match(assignment,/Lưu phân tổ/)
 assert.match(assignment,/Chưa phân tổ/)
 assert.match(assignment,/p\.data\.lotus_work_team/)
 // Employees are picked in the shared DataTable (sort, filters, pager) with its native tick column.
 assert.match(assignment,/<DataTable :rows="rows" :columns="peopleColumns" row-key="name"/)
 assert.match(assignment,/:selected-row-keys="checked"/)
 assert.match(assignment,/e\.modified/)
})
