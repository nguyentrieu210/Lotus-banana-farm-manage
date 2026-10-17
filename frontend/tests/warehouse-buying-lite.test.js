import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const buying=readFileSync(new URL('../src/components/WarehouseBuyingLite.vue',import.meta.url),'utf8')
const stock=readFileSync(new URL('../src/StockApp.vue',import.meta.url),'utf8')
const backend=readFileSync(new URL('../../lotus_farm/warehouse_buying_lite.py',import.meta.url),'utf8')
const install=readFileSync(new URL('../../lotus_farm/install.py',import.meta.url),'utf8')

test('purchase lite is separate from demand and uses same filtered Stock table',()=>{
 assert.match(stock,/planning:'Nhu cầu vật tư',buying:'Mua hàng'/)
 assert.match(stock,/<WarehouseBuyingLite v-if="tab==='buying'"/)
 assert.match(buying,/<DataTable :rows="rows" :columns="columns" show-empty-headers server-sort/)
 assert.match(buying,/:filter-values="choices"/)
 assert.match(buying,/@filter="changeFilter"/)
 assert.match(buying,/setTimeout\(\(\)=>load\(true\),220\)/)
})

test('supplier, item, quote and investor-directed purchase fields are supported',()=>{
 for(const field of ['draft.supplier','draft.mode','draft.warehouse','draft.expected_date','draft.notes','newSupplier']){
  assert.ok(buying.includes(field),field)
 }
 assert.match(buying,/Chủ đầu tư chỉ định/)
 assert.match(buying,/Kho tự mua/)
 assert.match(buying,/type="file" accept="\.pdf,image\/png,image\/jpeg,image\/webp"/)
 assert.match(buying,/await upload\(quote.value,'Purchase Order',result.name\)/)
 assert.match(buying,/:href="q.file_url"/)
 assert.match(backend,/lotus_purchase_mode/)
 assert.match(install,/install_buying_fields\(\)/)
})

test('purchase orders track arrival and can be received in parts using standard ERPNext receipts',()=>{
 for(const state of ['Nháp','Chờ hàng','Về một phần','Quá hẹn','Đã nhận đủ']){
  assert.ok(backend.includes(state),state)
 }
 assert.match(buying,/receivingAPI\('receive_order'/)
 assert.match(buying,/receivingAPI\('receipt_action'/)
 assert.match(buying,/receiptConfirm/)
 assert.match(backend,/doc\.check_permission\('submit'\)/)
 assert.match(backend,/flt\(r\.rate\)<=0/)
})

test('purchase list is permission-scoped and server-side faceted filtered',()=>{
 assert.match(backend,/_company\(company\)/)
 assert.match(backend,/doc\.check_permission\('read'\)/)
 assert.match(backend,/faceted_distinct\(rows,fields,selected\)/)
 assert.match(backend,/if warehouse:/)
 assert.match(backend,/status=='pending'/)
})

test('approved material request can populate Lite purchase order without losing lineage',()=>{
 assert.match(buying,/function pickRequest\(\)/)
 assert.match(buying,/api\('request_detail'/)
 assert.match(buying,/Từ đề nghị mua \(không bắt buộc\)/)
 assert.match(backend,/material_request=doc.name/)
 assert.match(backend,/material_request_item=r.name/)
 assert.match(backend,/material_request_item=original.name/)
 assert.match(backend,/Số lượng vượt phần đề nghị mua còn lại/)
})
