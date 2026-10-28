import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,h,tick} from './support/mount.mjs'

const Component=await load('components/DataTable.vue')
test('record cards retain the same row actions as the desktop grid',async()=>{
 let selected
 const row={name:'TS1',asset_name:'Máy bơm'}
 const view=mount(Component,{rows:[row],columns:[{field:'name',headerName:'Mã'},{field:'actions',headerName:'Thao tác'}],rowKey:'name'},{'cell-actions':({row})=>h('button',{onClick:()=>{selected=row.name}},'Chi tiết '+row.name)})
 await tick()
 const button=view.root.querySelector('.lotus-mobile-record-detail button')
 assert.equal(button.textContent,'Chi tiết TS1')
 button.click();await tick();assert.equal(selected,'TS1')
 view.unmount()
})
test('interactive cards keep selection separate from opening the record without nested buttons',async()=>{
 let opened
 const row={name:'TS1'}
 const view=mount(Component,{rows:[row],columns:[{field:'name',headerName:'Mã'},{colId:'actions',headerName:'Thao tác'}],rowKey:'name',interactive:true,onOpen:value=>{opened=value}},{'cell-actions':()=>h('button',{},'Nested')})
 await tick()
 const records=view.root.querySelector('.lotus-mobile-records'),card=records.querySelector('.lotus-mobile-record')
 assert.equal(records.querySelectorAll('button').length,2,'one selection button and one record button')
 assert.equal(card.tagName,'BUTTON')
 assert.equal(card.querySelector('button'),null,'neither selection nor cell actions are nested buttons')
 const select=records.querySelector('button[aria-label="Chọn dòng"]')
 select.click();await tick()
 assert.equal(select.getAttribute('aria-pressed'),'true')
 assert.equal(opened,undefined,'selection does not open the record')
 card.click();await tick();assert.equal(opened,row)
 view.unmount()
})
