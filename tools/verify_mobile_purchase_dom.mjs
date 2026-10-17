// Extends the stock/receiving checks with both real Vue PWA purchase hosts.
import {compile,project,mount,tick,button,input,api,check,results} from './verify_warehouse_mobile_dom.mjs'
import {pathToFileURL} from 'node:url'
import assert from 'node:assert/strict'
const Warehouse=(await import(pathToFileURL(compile(project+'/src/WarehouseMobile.vue')))).default
const Buyer=(await import(pathToFileURL(compile(project+'/src/BuyingMobile.vue')))).default
const Link=(await import(pathToFileURL(compile(project+'/src/components/MobileLinkField.vue')))).default
let app=mount(Link,{modelValue:'S1',options:[{value:'S1',label:'Nhà cung cấp 1'},{value:'S2',label:'Nhà cung cấp 2'}]})
await check('named links use the same searchable control even with a small catalog',async()=>{
 assert.ok(app.root.querySelector('input[role=combobox]'));app.root.querySelector('input').focus();await tick()
 assert.equal(document.querySelectorAll('[role=option]').length,2)
})
app.app.unmount();app.root.remove()
function signature(root){return {
 labels:[...root.querySelectorAll('.lotus-purchase-form .van-field__label')].map(e=>e.textContent.trim()),
 inputs:[...root.querySelectorAll('.lotus-purchase-form input,.lotus-purchase-form select,.lotus-purchase-form textarea')].map(e=>({tag:e.tagName,type:e.type,required:e.required,min:e.min,max:e.max,step:e.step})),
 submit:root.querySelector('.lotus-purchase-form button[type=submit]').textContent.trim()
}}
let warehouseSignature
for(const [name,Component] of [['Warehouse',Warehouse],['Buyer',Buyer]]){
 app=mount(Component);await tick();await tick()
 button(app.root,'Tạo đơn mua').click();await tick();await tick()
 await check(name+' uses the canonical purchase form and retains native validation',async()=>{
  assert.ok(app.root.querySelector('.lotus-purchase-form'))
  assert.equal(app.root.querySelector('input[type=date]').required,true)
  const qty=app.root.querySelector('input[type=number]');assert.equal(qty.min,'0.000001');input(qty,'2');await tick()
  if(name==='Warehouse')warehouseSignature=signature(app.root)
  else assert.deepEqual(signature(app.root),warehouseSignature)
 })
 await check(name+' guards dirty purchase navigation and Stay retains quantity',async()=>{
  button(app.root,'Trang chủ').click();await tick()
  assert.ok(document.querySelector('.van-dialog'));assert.notEqual(document.querySelector('.van-dialog').style.display,'none')
  button(app.root,'Ở lại').click();await tick();assert.equal(app.root.querySelector('input[type=number]').value,'2')
 })
 await check(name+' opens the shared supplier form and returns to the purchase without losing rows',async()=>{
  button(app.root,'+ Thêm nhà cung cấp').click();await tick()
  assert.ok(app.root.querySelector('.lotus-supplier-form'))
  const fields=app.root.querySelectorAll('.lotus-supplier-form input')
  assert.equal(fields.length,3);input(fields[0],name+' test supplier');await tick();input(fields[1],'Test contact');await tick();input(fields[2],'0900000000');await tick()
  assert.equal(button(app.root,'Lưu nhà cung cấp').type,'submit')
  // Happy DOM does not dispatch a form submit from a native button click.
  app.root.querySelector('.lotus-supplier-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()
  assert.ok(app.root.querySelector('.lotus-purchase-form'))
  assert.equal(app.root.querySelector('input[type=number]').value,'2')
  assert.equal(app.root.querySelector('input[aria-label="Nhà cung cấp"]').value,name+' test supplier')
  const writes=api.calls.filter(c=>c.write&&c.method.endsWith('.save_supplier'))
  assert.equal(writes.at(-1).args.contact,'Test contact')
  assert.equal(writes.at(-1).args.phone,'0900000000')
 })
 await check(name+' confirmed navigation exits without sending a purchase order',async()=>{
  const before=api.calls.filter(c=>c.write&&c.method.endsWith('.save_order')).length
  button(app.root,'Trang chủ').click();await tick();button(app.root,'Tiếp tục').click();await tick()
  assert.equal(app.root.querySelector('.lotus-purchase-form'),null)
  assert.equal(api.calls.filter(c=>c.write&&c.method.endsWith('.save_order')).length,before)
 })
 app.app.unmount();app.root.remove();await tick()
}
console.log(JSON.stringify({passed:results.filter(r=>!r.startsWith('selected:')).length,results},null,2))

await window.happyDOM.close()
