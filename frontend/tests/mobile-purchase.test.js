import test from 'node:test'
import assert from 'node:assert/strict'
import {newPurchaseDraft,purchasePayload,purchaseFromRequest,savePurchaseDraft,retryPurchaseQuote,MAX_QUOTE_BYTES} from '../src/mobile-purchase.js'
const catalog={items:[{name:'I1',stock_uom:'Kg'}],conversions:[{parent:'I1',uom:'Bao'}]}
function draft(){const d=newPurchaseDraft('K1','2026-10-17');d.supplier='S1';d.items[0]={...d.items[0],item:'I1',qty:2,uom:'Bao',rate:300};return d}
test('shared purchase payload retains request lines and converts quantity exactly once',()=>{
 const d=purchaseFromRequest(draft(),{expected_date:'2026-10-19',items:[{item:'I1',qty:3,uom:'Bao',warehouse:'K2',material_request:'MR1',material_request_item:'MRI1'}]})
 const payload=purchasePayload(d,catalog)
 assert.equal(payload.expected_date,'2026-10-19');assert.equal(payload.warehouse,'K2')
 assert.equal(payload.items[0].qty,3);assert.equal(payload.items[0].material_request_item,'MRI1')
 assert.ok(!('id' in payload.items[0]))
})
test('purchase preflight rejects nonfinite, negative and empty quantities/prices and invalid unit',()=>{
 for(const qty of ['',0,-1,'NaN','Infinity']){const d=draft();d.items[0].qty=qty;assert.throws(()=>purchasePayload(d,catalog),/Số lượng/)}
 for(const rate of [-1,'NaN','Infinity']){const d=draft();d.items[0].rate=rate;assert.throws(()=>purchasePayload(d,catalog),/Đơn giá/)}
 const d=draft();d.items[0].uom='Tấn';assert.throws(()=>purchasePayload(d,catalog),/đơn vị/)
})
test('purchase preflight rejects missing warehouse, invalid calendar dates and oversized quote',()=>{
 const d=draft();d.warehouse='';assert.throws(()=>purchasePayload(d,catalog),/kho nhận/)
 d.warehouse='K1';d.expected_date='2026-02-31';assert.throws(()=>purchasePayload(d,catalog),/ngày/)
 d.expected_date='2026-10-17';assert.throws(()=>purchasePayload(d,catalog,{size:MAX_QUOTE_BYTES+1}),/10 MB/)
})
test('attachment failure retains saved order identity and retry performs no second purchase save',async()=>{
 const d=draft(),quote={name:'test.pdf',size:1000};let writes=0,uploads=0,committed=false
 const result=await savePurchaseDraft({company:'C',draft:d,catalog,quote,
  save:async args=>{writes++;assert.equal(args.name,null);return {name:'PO1',modified:'v1'}},
  onSaved:saved=>{committed=true;assert.equal(d.name,'PO1');assert.equal(saved.name,'PO1')},
  upload:async()=>{uploads++;assert.ok(committed);throw Error('Mất mạng tải file')}})
 assert.equal(result.name,'PO1');assert.match(result.quoteError,/Mất mạng/);assert.equal(d.modified,'v1')
 await retryPurchaseQuote({saved:result,quote,upload:async(file,doctype,name)=>{uploads++;assert.equal(name,'PO1');assert.equal(doctype,'Purchase Order')}})
 assert.equal(writes,1);assert.equal(uploads,2)
})
test('editing a rejected draft preserves document name and optimistic modified token',async()=>{
 const d=draft();d.name='PO2';d.modified='revision-3'
 const result=await savePurchaseDraft({company:'C',draft:d,catalog,save:async args=>{
  assert.equal(args.name,'PO2');assert.equal(args.modified,'revision-3');return {name:'PO2',modified:'revision-4'}},upload:async()=>assert.fail('No attachment selected')})
 assert.equal(result.quoteError,'');assert.equal(d.modified,'revision-4')
})
test('invalid purchase data never invokes the write API',async()=>{
 const d=draft();d.items[0].qty=0
 await assert.rejects(savePurchaseDraft({company:'C',draft:d,catalog,save:async()=>assert.fail('Unexpected write')}),/Số lượng/)
})
