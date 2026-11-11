import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,document} from './support/mount.mjs'

const DataTable=await load('components/DataTable.vue')
const settle=async()=>{await tick();await tick()}
const picker=(root,id)=>root.querySelector(`.ag-row[row-id="${id}"] [col-id="__lotus_select"] button`)
const rows=[{name:'A',docstatus:0},{name:'B',docstatus:1}]
const columns=[{field:'name',headerName:'Số phiếu'}]

test('a plain table has no tick column: ticking would do nothing',async()=>{
 const view=mount(DataTable,{rows,columns,rowKey:'name'})
 try{
  await settle()
  assert.ok(view.root.querySelector('.ag-row[row-id="A"]'))
  assert.equal(view.root.querySelector('[col-id="__lotus_select"]'),null)
  assert.equal(view.root.querySelector('.lotus-grid-select-toggle'),null)
 }finally{view.unmount()}
})

test('ticked drafts are deleted together; posted rows are not sent',async()=>{
 const calls=[],deleted=[]
 globalThis.fetch=async(url,opts={})=>{
  const method=new URL(url,'http://localhost').pathname.replace('/api/method/','')
  calls.push({method,body:JSON.parse(opts.body||'{}')})
  return {ok:true,status:200,json:async()=>({message:{deleted:[{doctype:'Stock Entry',name:'A'}],failed:[]}})}
 }
 const view=mount(DataTable,{rows,columns,rowKey:'name',deleteItem:row=>row.docstatus===0?{doctype:'Stock Entry',name:row.name}:null,onDeleted:r=>deleted.push(r)})
 try{
  await settle()
  picker(view.root,'A').click();await settle()
  picker(view.root,'B').click();await settle()
  const button=view.root.querySelector('.lotus-data-table__delete')
  assert.match(button.textContent,/Xóa 1 phiếu/)
  button.click();await settle()
  const confirmButton=[...document.querySelectorAll('.workspace-confirm__actions button')].find(b=>!/Hủy|Không/.test(b.textContent))
  assert.ok(confirmButton,'asks before deleting')
  confirmButton.click();await settle();await settle()
  assert.equal(calls.length,1)
  assert.equal(calls[0].method,'lotus_farm.bulk_delete.drafts')
  assert.deepEqual(JSON.parse(calls[0].body.items),[{doctype:'Stock Entry',name:'A'}])
  assert.equal(deleted.length,1)
 }finally{view.unmount();for(const b of document.querySelectorAll('.workspace-confirm__actions button'))b.click()}
})
