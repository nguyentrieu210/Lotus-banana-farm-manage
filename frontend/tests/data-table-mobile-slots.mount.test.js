import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,h,tick} from './support/mount.mjs'

const Component=await load('components/DataTable.vue')
test('record cards retain the same row actions as the desktop grid',async()=>{
 let selected
 const row={name:'TS1',asset_name:'Máy bơm'}
 const view=mount(Component,{rows:[row],columns:[{field:'name',headerName:'Mã'},{field:'actions',headerName:'Thao tác'}],rowKey:'name'},{'cell-actions':({row})=>h('button',{onClick:()=>{selected=row.name}},'Chi tiết '+row.name)})
 await tick()
 const button=view.root.querySelector('.lotus-mobile-records button')
 assert.equal(button.textContent,'Chi tiết TS1')
 button.click();await tick();assert.equal(selected,'TS1')
 view.unmount()
})
test('interactive record cards remain a single button without nested action buttons',async()=>{
 const view=mount(Component,{rows:[{name:'TS1'}],columns:[{field:'name',headerName:'Mã'},{field:'actions',headerName:'Thao tác'}],rowKey:'name',interactive:true},{'cell-actions':()=>h('button',{},'Nested')})
 await tick()
 assert.equal(view.root.querySelector('.lotus-mobile-records').querySelectorAll('button').length,1)
 view.unmount()
})
