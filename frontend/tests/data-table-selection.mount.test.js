import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick} from './support/mount.mjs'

const DataTable=await load('components/DataTable.vue')
const rows=[{name:'A'},{name:'B'},{name:'C'}]
const header=root=>root.querySelector('.ag-header-cell[col-id="__lotus_select"] button')
const picker=(root,id)=>root.querySelector(`.ag-row[row-id="${id}"] [col-id="__lotus_select"] button`)
const settle=async()=>{await tick();await tick()}

test('real grid headers and cells refresh after selecting rows, pages and clearing selection',async()=>{
 const errors=[],originalError=console.error
 console.error=(...args)=>{errors.push(args.join(' '));originalError(...args)}
 let view
 try{
  view=mount(DataTable,{rows,columns:[{field:'name',headerName:'Mã'}],rowKey:'name',pageSize:2})
  await settle()
  assert.ok(header(view.root),'selection header implements the AG Grid component lifecycle')
  assert.equal(header(view.root).getAttribute('aria-pressed'),'false')
  assert.ok(picker(view.root,'A'),'real grid rows render')
  picker(view.root,'A').click();await settle()
  assert.equal(picker(view.root,'A').getAttribute('aria-pressed'),'true','refreshCells updates the row button')
  assert.ok(header(view.root).classList.contains('is-partial'),'refreshHeader updates partial selection')

  header(view.root).click();await settle()
  assert.equal(header(view.root).getAttribute('aria-pressed'),'true')
  assert.equal(picker(view.root,'B').getAttribute('aria-pressed'),'true')
  assert.match(view.root.querySelector('.lotus-data-table__selected').textContent,/2 dòng đã chọn/)

  view.root.querySelector('.lotus-pagination [aria-label="Trang sau"]').click();await settle()
  assert.equal(header(view.root).getAttribute('aria-pressed'),'false','the next page has its own selection state')
  assert.equal(picker(view.root,'C').getAttribute('aria-pressed'),'false')
  header(view.root).click();await settle()
  assert.match(view.root.querySelector('.lotus-data-table__selected').textContent,/3 dòng đã chọn/)

  view.root.querySelector('.lotus-data-table__selected button').click();await settle()
  assert.equal(picker(view.root,'C').getAttribute('aria-pressed'),'false')
  assert.equal(header(view.root).getAttribute('aria-pressed'),'false')
  assert.equal(view.root.querySelector('.lotus-data-table__selected'),null)
  assert.deepEqual(errors,[])
 }finally{view?.unmount();console.error=originalError}
})

test('business selection columns render one native header and retain their row renderer',async()=>{
 const view=mount(DataTable,{rows:[rows[0]],rowKey:'name',columns:[
  {field:'choice',headerName:'Chọn',cellRenderer:()=>{const input=document.createElement('input');input.type='checkbox';input.setAttribute('aria-label','Chọn báo giá');return input}},
  {field:'name',headerName:'Mã'},
 ]})
 try{
  await settle()
  assert.equal(view.root.querySelectorAll('.ag-header-cell[col-id="choice"]').length,1)
  assert.equal(view.root.querySelector('.lotus-grid-native-select-header').textContent,'Chọn')
  assert.equal(header(view.root),null)
  assert.ok(view.root.querySelector('.ag-row[row-id="A"] input[aria-label="Chọn báo giá"]'))
 }finally{view.unmount()}
})
