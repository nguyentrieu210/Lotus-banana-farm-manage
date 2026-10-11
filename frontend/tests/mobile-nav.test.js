import {test} from 'node:test'
import assert from 'node:assert/strict'
import {shortcuts,pathWithFarm,taskStatus} from '../src/mobile-nav.js'

const session={modules:{work:['Daily Work Plan'],materials:['Material Requirement'],packhouse:['Packout Run']},commands:{work:true}}
test('manager sees only enabled shortcuts',()=>{
 const result=shortcuts({features:['assign','tasks','management']},session)
 assert.deepEqual(result.map(r=>r.name),['Giao việc','Kế hoạch ngày','Vật tư'])
})
test('a team leader with no parent DocType read still has the mobile task list',()=>{
 assert.deepEqual(shortcuts({features:['tasks']},{modules:{},commands:{}}),[])
})
test('ungranted role cannot gain a shortcut merely by having another module',()=>{
 assert.deepEqual(shortcuts({features:[]},session),[])
})
test('URL parameter does not accept injection or corrupt accented names',()=>{
 assert.equal(pathWithFarm('/lotus/giao-viec','Lô A & B'),'/lotus/giao-viec?farm=L%C3%B4%20A%20%26%20B')
})
test('task statuses are understandable',()=>{
 assert.equal(taskStatus('Blocked'),'Đang vướng')
 assert.equal(taskStatus('Completed'),'Đã hoàn thành')
})
