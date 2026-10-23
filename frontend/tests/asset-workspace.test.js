import test from 'node:test'
import assert from 'node:assert/strict'
import {registerRows,filterRegister,assetStatus,assetView,matches} from '../src/asset-workspace.js'

test('pending registrations and native assets have separate identities',()=>{
 const rows=registerRows({assets:[{name:'same',status:'Submitted',docstatus:1}],pending_assets:[{name:'same',operation:'same',status:'Pending'}]})
 assert.deepEqual(rows.map(r=>r.row_key),['operation:same','asset:same'])
 assert.equal(rows[0].pending,true)
 assert.equal(rows[1].pending,false)
})
test('register filters intersect status, group, position and farm and search Vietnamese names',()=>{
 const rows=registerRows({pending_assets:[{operation:'OP1',asset_name:'Máy bơm điện',lotus_asset_code:'TS01',asset_category:'Máy',location:'Kho',lotus_farm:'F1'}],assets:[{name:'A1',asset_name:'Xe vận tải',lotus_serial_no:'SERIAL99',status:'Submitted',docstatus:1}]})
 assert.equal(filterRegister(rows,'may bom dien',{category:'Máy',location:'Kho',farm:'F1',status:'Pending'}).length,1)
 assert.equal(filterRegister(rows,'may',{farm:'F2'}).length,0)
 assert.equal(filterRegister(rows,'serial99')[0].name,'A1')
})
test('posting replaces the pending source instead of retaining a duplicate',()=>{
 const data={assets:[],pending_assets:[{operation:'OP1',lotus_asset_code:'TS01'}]}
 assert.equal(registerRows(data).length,1)
 data.pending_assets=[];data.assets=[{name:'A1',lotus_asset_code:'TS01',docstatus:1,status:'Submitted'}]
 assert.deepEqual(registerRows(data).map(r=>r.row_key),['asset:A1'])
})
test('cancelled and suspended statuses stay distinct from pending',()=>{
 assert.equal(assetStatus({pending:true,docstatus:0}),'Pending')
 assert.equal(assetStatus({docstatus:2,lotus_usage_suspended:1}),'Cancelled')
 assert.equal(assetStatus({docstatus:1,lotus_usage_suspended:1}),'Suspended')
})
test('unknown section falls back to the register and empty searches are safe',()=>{
 assert.equal(assetView('categories'),'categories')
 assert.equal(assetView('unknown'),'assets')
 assert.equal(matches({},'', ['name']),true)
 assert.equal(matches({},'abc',['name']),false)
})
