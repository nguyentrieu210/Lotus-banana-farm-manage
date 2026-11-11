import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync,existsSync} from 'node:fs'
import {khoSource} from './support/kho-source.mjs'

// The old "Lite" purchase screen is gone: purchase orders live in Mua hàng, receiving in the shared WarehouseReceiving dialog.
// These rules now check the screens that carry them, plus the warehouse_buying_lite backend they still use.
const src=name=>readFileSync(new URL('../src/'+name,import.meta.url),'utf8')
const stock=khoSource()
const workspace=src('components/ProcurementWorkspace.vue'),form=src('components/ProcurementDocumentForm.vue'),purchase=src('mobile-purchase.js'),receiving=src('components/WarehouseReceiving.vue')
const backend=readFileSync(new URL('../../lotus_farm/warehouse_buying_lite.py',import.meta.url),'utf8')
const install=readFileSync(new URL('../../lotus_farm/install.py',import.meta.url),'utf8')

test('purchases live in Mua hàng, not in a separate Kho screen',()=>{
 assert.equal(existsSync(new URL('../src/components/WarehouseBuyingLite.vue',import.meta.url)),false)
 assert.match(stock,/stockNavigation/)
 assert.doesNotMatch(stock,/WarehouseBuyingLite/)
 assert.match(workspace,/<ListPage v-else-if="!mobile"/)
})

test('supplier, item, quote and investor-directed purchase fields are supported',()=>{
 for(const field of ['modelValue.supplier','modelValue.warehouse','modelValue.expected_date','modelValue.notes'])assert.ok(form.includes(field),field)
 assert.match(purchase,/PURCHASE_MODES=\['Kho tự mua','Chủ đầu tư chỉ định'\]/)
 assert.match(purchase,/await upload\(quote,'Purchase Order',result\.name\)/)
 assert.match(backend,/lotus_purchase_mode/)
 assert.match(install,/install_buying_fields\(\)/)
})

test('purchase orders track arrival and can be received in parts using standard ERPNext receipts',()=>{
 // One status vocabulary computed in purchase_status.order_state; late delivery is the separate flag `overdue`.
 assert.match(backend,/purchase_status\.order_state\(/)
 assert.match(backend,/overdue=_overdue\(doc\)/)
 const states=readFileSync(new URL('../../lotus_farm/purchase_status.py',import.meta.url),'utf8')
 for(const state of ['Nháp','Chờ duyệt','Bị trả lại','Đã duyệt','Đã gửi NCC','NCC đã xác nhận','Đang nhận','Đã nhận đủ','Đã đóng','Đã hủy'])assert.ok(states.includes("'"+state+"'"),state)
 assert.match(receiving,/api\('receive_order'/)
 assert.match(receiving,/post:1/)
 assert.match(readFileSync(new URL('../src/components/procurement/ReceiptDetail.vue',import.meta.url),'utf8'),/action\('submit',extra\)/)
 // Spec 003: no submit without the named approver's signature (purchasing.approve_order / check_submission).
 assert.doesNotMatch(backend,/def submit_order/)
})

test('purchase list is permission-scoped and server-side faceted filtered',()=>{
 assert.match(backend,/_company\(company\)/)
 assert.match(backend,/doc\.check_permission\('read'\)/)
 assert.match(backend,/faceted_distinct\(rows,fields,selected\)/)
 assert.match(backend,/if warehouse:/)
 assert.match(backend,/status=='pending'/)
})

test('approved material request can populate a purchase order without losing lineage',()=>{
 assert.match(workspace,/method\('warehouse_buying_lite','request_detail'/)
 assert.match(form,/Lấy dòng từ đề xuất đã duyệt/)
 assert.match(backend,/material_request=doc.name/)
 assert.match(backend,/material_request_item=r.name/)
 assert.match(backend,/material_request_item=original.name/)
 assert.match(backend,/Số lượng vượt phần đề xuất mua còn lại/)
})
