import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,window} from './support/mount.mjs'

const DataTable=await load('components/DataTable.vue')
const settle=async()=>{await tick();await tick()}
const selectSize=async(root,size)=>{
 const select=root.querySelector('select[aria-label="Số dòng mỗi trang"]')
 assert.ok(select,'shared pager exposes its row limit')
 assert.deepEqual([...select.options].map(option=>option.value).filter(value=>value!=='0'),['20','50','100'])
 select.value=String(size);select.dispatchEvent(new window.Event('change',{bubbles:true}));await settle()
}

test('changing local page size resets the offset, grid selection and mobile rows together',async()=>{
 const rows=Array.from({length:135},(_,i)=>({name:'R'+String(i+1).padStart(3,'0'),qty:1}))
 const view=mount(DataTable,{rows,rowKey:'name',columns:[{field:'name',headerName:'Mã'},{field:'qty',headerName:'Số lượng'}]})
 try{
  await settle()
  view.root.querySelector('[aria-label="Trang sau"]').click();await settle()
  assert.match(view.root.querySelector('.lotus-pagination__range').textContent,/51–100/)
  for(const size of [20,100,50]){
   await selectSize(view.root,size)
   assert.equal(view.root.querySelectorAll('.lotus-mobile-record-entry').length,size)
   assert.match(view.root.querySelector('.lotus-pagination__range').textContent,new RegExp(`1–${size}`))
   assert.ok(view.root.querySelector('.ag-row[row-id="R001"]'),'AG Grid returns to the first page')
   view.root.querySelector('.ag-header-cell[col-id="__lotus_select"] button').click();await settle()
   assert.match(view.root.querySelector('.lotus-data-table__selected').textContent,new RegExp(`${size} dòng đã chọn`))
   view.root.querySelector('.lotus-data-table__selected button').click();await settle()
   view.root.querySelector('[aria-label="Trang sau"]').click();await settle()
   assert.match(view.root.querySelector('.lotus-pagination__range').textContent,new RegExp(`${size+1}–${Math.min(135,size*2)}`))
  }
  assert.match(view.root.querySelector('.lotus-mobile-total dt').textContent,/135 dòng/,'total still includes all filtered rows')
  view.root.querySelector('.lotus-pagination button:not([aria-label])').click();await settle()
  assert.equal(view.root.querySelectorAll('.lotus-mobile-record-entry').length,135)
  assert.match(view.root.querySelector('.lotus-pagination__range').textContent,/1–135/)
  assert.equal(view.root.querySelector('[aria-label="Trang sau"]'),null)
  view.root.querySelector('.ag-header-cell[col-id="__lotus_select"] button').click();await settle()
  assert.match(view.root.querySelector('.lotus-data-table__selected').textContent,/135 dòng đã chọn/)
  await selectSize(view.root,20)
  assert.equal(view.root.querySelectorAll('.lotus-mobile-record-entry').length,20)
 }finally{view.unmount()}
})

for(const [path,props,parameter] of [
 ['stock/StockInventory.vue',{company:'C'},'length'],
 ['stock/StockDocumentList.vue',{company:'C',kind:'issues'},'length'],
 ['stock/StockLedger.vue',{company:'C'},'length'],
 ['WarehousePlanning.vue',{company:'C',today:'2026-11-02'},'length'],
 ['ProcurementMasters.vue',{company:'C',kind:'items'},'page_length'],
]){
 test(`${path} reloads server pages with the selected limit and resets to the first page`,async()=>{
  const Screen=await load('components/'+path),calls=[]
  globalThis.fetch=async(url,opts={})=>{
   const parsed=new URL(url,'http://localhost'),args=opts.body?JSON.parse(opts.body):Object.fromEntries(parsed.searchParams)
   calls.push(args)
   const size=Number(args[parameter]||50),start=Number(args.start||0)
   const rows=Array.from({length:Math.min(size,135-start)},(_,i)=>({name:'R'+(start+i),item:'I'+(start+i),item_name:'Vật tư '+i,stock_uom:'Kg',supplier_name:'NCC '+i}))
   return {ok:true,json:async()=>({message:{rows,items:rows,total_count:135,has_more:start+size<135,catalogue_count:135,warnings:[],warehouses:[],requests:[],orders:[],summary:{}}})}
  }
  const view=mount(Screen,props)
  try{
   await settle()
   view.root.querySelector('[aria-label="Trang sau"]').click();await settle()
   assert.equal(Number(calls.at(-1).start),50)
   for(const size of [20,100,50]){
    await selectSize(view.root,size)
    assert.equal(Number(calls.at(-1)[parameter]),size)
    assert.equal(Number(calls.at(-1).start),0)
    assert.match(view.root.querySelector('.lotus-pagination__range').textContent,new RegExp(`1–${size}`))
    assert.equal(view.root.querySelectorAll('.lotus-pagination').length,1,'server pages have one pager')
   }
   const beforeAll=calls.length
   const showAll=[...view.root.querySelectorAll('button')].find(button=>button.textContent==='Hiện toàn bộ')
   showAll.click();await settle()
   assert.deepEqual(calls.slice(beforeAll).map(args=>[Number(args.start),Number(args[parameter])]),[[0,100],[100,100]])
   assert.equal(view.root.querySelectorAll('.lotus-mobile-record-entry').length,135)
   assert.match(view.root.querySelector('.lotus-pagination__range').textContent,/1–135/)
   assert.equal(view.root.querySelector('[aria-label="Trang sau"]'),null)
   await selectSize(view.root,20)
   assert.equal(Number(calls.at(-1).start),0)
   assert.equal(Number(calls.at(-1)[parameter]),20)
  }finally{view.unmount()}
 })
}
