import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick} from './support/mount.mjs'
const WorkJournal=await load('WorkJournalApp.vue')
const button=(root,text)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===text)
let writable=true,writes=[]
const source={row_id:'12345678-abcd',work_team:'T',farm_block:'B',work_type:'W',uom:'Tree',quantity:25,workdays:0,notes:'Báo qua Zalo'}
globalThis.fetch=async(url,options={})=>{
 const method=new URL(url,'http://localhost').pathname.split('.').at(-1)
 const data={bootstrap:{user:'clerk',today:'2026-10-20',farms:[{name:'F',farm_name:'Vườn thử'}],capabilities:{}},catalogue:{teams:[{name:'T',team_name:'Tổ A',active:1}],blocks:[{name:'B',block_code:'A1',active:1}],works:[{name:'W',work_name:'Chăm sóc',uom:'Tree',active:1}]},get:{name:'J',rows:[source],modified:'m1',modified_by:'clerk',owner:'clerk',can_write:writable},save:{name:'J',rows:[source],modified:'m2',can_write:true}}
 if(method==='save')writes.push(JSON.parse(options.body))
 return {ok:true,json:async()=>({message:data[method]})}
}
test('phone journal shows scoped tracking data, clones rows and warns without merging',async()=>{
 localStorage.clear();writable=true;writes=[]
 const view=mount(WorkJournal,{mobile:true});await tick();await tick()
 try{
  assert.match(view.root.textContent,/Chăm sóc.*Tổ A/s)
  assert.ok(button(view.root,'Thêm dòng'))
  button(view.root,'Xem / sửa').click();await tick()
  assert.match(document.body.textContent,/Dòng nhật ký/)
  button(document.body,'Nhân bản').click();await tick()
  assert.match(view.root.textContent,/Có dòng trùng tổ, lô và công việc/)
  button(view.root,'Lưu nhật ký').click();await tick();await tick()
  assert.equal(writes.length,1)
  assert.equal(writes[0].rows.length,2)
  assert.notEqual(writes[0].rows[0].row_id,writes[0].rows[1].row_id)
  assert.equal(writes[0].expected_user,'clerk')
 }finally{view.unmount()}
})

test('desktop journal opens existing row with values including zero, then closes without changing data',async()=>{
 localStorage.clear();writable=true;writes=[]
 const view=mount(WorkJournal,{mobile:false});await tick();await tick()
 try{
  assert.ok(button(view.root,'Thêm dòng'))
  assert.ok(button(view.root,'Lưu nhật ký')===undefined || button(view.root,'Lưu nhật ký').disabled)
  assert.ok(view.root.querySelector('.lotus-data-table'))
  const item=view.root.querySelector('.lotus-mobile-record')
  assert.ok(item,'Desktop table exposes a row for open action')
  item.click();await tick()
  const dialog=view.root.querySelector('dialog.journal-editor')
  assert.ok(dialog?.open,'Row editor is an open desktop dialog')
  assert.match(dialog.textContent,/Tổ\/đội/)
  assert.match(dialog.textContent,/Tổng công/)
  assert.equal(dialog.querySelector('input[aria-label="Tổng công"]')?.value,'0')
  button(dialog,'Hủy').click();await tick()
  assert.equal(dialog.open,false)
  assert.equal(writes.length,0)
 }finally{view.unmount()}
})


test('desktop operator updates a row, saves exactly once and preserves a zero workday value',async()=>{
 localStorage.clear();writable=true;writes=[]
 const view=mount(WorkJournal,{mobile:false});await tick();await tick()
 try{
  view.root.querySelector('.lotus-mobile-record').click();await tick()
  const dialog=view.root.querySelector('dialog.journal-editor')
  const qty=dialog.querySelector('input[aria-label="Số lượng thực hiện"]')
  assert.ok(qty)
  qty.value='30';qty.dispatchEvent(new Event('input',{bubbles:true}));await tick()
  button(dialog,'Giữ dòng').click();await tick()
  assert.equal(dialog.open,false)
  const saveButton=button(view.root,'Lưu nhật ký')
  assert.ok(saveButton&&!saveButton.disabled)
  saveButton.click();await tick();await tick()
  assert.equal(writes.length,1)
  assert.equal(Number(writes[0].rows[0].quantity),30)
  assert.equal(Number(writes[0].rows[0].workdays),0)
  assert.equal(writes[0].rows[0].row_id,source.row_id)
  assert.equal(writes[0].expected_modified,'m1')
 }finally{view.unmount()}
})


test('desktop reader may inspect a journal row but cannot edit or save',async()=>{
 localStorage.clear();writable=false;writes=[]
 const view=mount(WorkJournal,{mobile:false});await tick();await tick()
 try{
  assert.equal(button(view.root,'Thêm dòng'),undefined)
  assert.equal(button(view.root,'Lưu nhật ký'),undefined)
  view.root.querySelector('.lotus-mobile-record').click();await tick()
  const dialog=view.root.querySelector('dialog.journal-editor')
  assert.ok(dialog?.open)
  assert.ok(dialog.querySelector('fieldset')?.disabled)
  assert.equal(button(dialog,'Giữ dòng'),undefined)
  assert.ok(button(dialog,'Đóng'))
  button(dialog,'Đóng').click();await tick()
  assert.equal(dialog.open,false)
  assert.equal(writes.length,0)
 }finally{view.unmount()}
})

test('same-farm reader sees rows and Excel but no data-entry controls',async()=>{
 localStorage.clear();writable=false
 const view=mount(WorkJournal,{mobile:true});await tick();await tick()
 try{assert.match(view.root.textContent,/Chăm sóc/);assert.ok(view.root.querySelector('a[href*=".export?"]'));assert.equal(button(view.root,'Thêm dòng'),undefined);assert.equal(button(view.root,'Lưu nhật ký'),undefined)}finally{view.unmount()}
})
