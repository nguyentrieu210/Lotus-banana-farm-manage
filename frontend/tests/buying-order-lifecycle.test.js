import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {purchasePdfUrl,sharePurchasePdf} from '../src/purchase-document.js'

const root=path.resolve(import.meta.dirname,'../..')
const read=p=>fs.readFileSync(path.join(root,p),'utf8')
test('Purchase order PDF URL serves the archived signed PDF when available',()=>{
 const url=purchasePdfUrl('PUR-ORD-2026 0001')
 assert.match(url,/^\/api\/method\/lotus_farm\.digital_signature\.download_purchase_pdf\?/)
 assert.equal(new URL('https://example.com'+url).searchParams.get('name'),'PUR-ORD-2026 0001')
})
test('PDF share does not silently mark order as sent',async()=>{
 let shares=0
 const result=await sharePurchasePdf('PO-1',{
  fetchPdf:async()=>({ok:true,blob:async()=>new Blob(['%PDF-1.4'],{type:'application/pdf'})}),
  shareApi:{canShare:()=>true,share:async({files})=>{shares++;assert.equal(files[0].type,'application/pdf')}},
  download:()=>assert.fail('must not download')
 })
 assert.equal(result,'shared');assert.equal(shares,1)
})
test('Share fallback downloads file and never modifies purchase record',async()=>{
 let filename=''
 const status=await sharePurchasePdf('PO-2',{
  fetchPdf:async()=>({ok:true,blob:async()=>new Blob(['%PDF'],{type:'application/pdf'})}),
  shareApi:{canShare:()=>false},
  download:file=>{filename=file.name}
 })
 assert.equal(status,'downloaded');assert.equal(filename,'PO-2.pdf')
})
test('Buyer can confirm send, supplier, ETA, close or cancel only through protected server actions',()=>{
 const py=read('lotus_farm/purchasing.py')
 const ui=read('frontend/src/BuyingMobile.vue')
 for(const action of ['mark_order_sent','confirm_supplier_order','reschedule_order','close_order','cancel_order']){
  assert.match(py,new RegExp('def '+action+'\\('))
  assert.ok(ui.includes("'"+action+"'"),action)
 }
 assert.match(py,/lock\("Purchase Order", name\)/)
 assert.match(py,/doc\.update_status\("Closed"\)/)
 assert.match(py,/doc\.check_permission\("cancel"\)|_submitted_order\(name, modified, permission="cancel"\)/)
 assert.match(py,/doc\.cancel\(\)/)
 assert.match(ui,/Đã gửi NCC/)
 assert.match(ui,/NCC đã xác nhận/)
 assert.match(ui,/Chia sẻ PDF/)
 assert.match(read('lotus_farm/warehouse_buying_lite.py'),/lotus_revised_delivery_date/)
})
test('Cancelled order is not shown as approved',()=>{
 const py=read('lotus_farm/purchasing.py')
 assert.match(py,/approval_status="Đã hủy" if doc\.docstatus == 2/)
})