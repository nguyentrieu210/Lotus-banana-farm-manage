import test from 'node:test'
import assert from 'node:assert/strict'
import {procurementNavigation,visibleBuyingNavigation,buyingMenu,buyingGroupViews,normalizeBuyingView} from '../src/procurement-navigation.js'

const full={capabilities:{purchasing_finance:true,purchasing_invoice_read:true}}

test('the Mua hàng sidebar has one entry per job, Mua nhanh first',()=>{
 const main=visibleBuyingNavigation(full).filter(r=>!r.setup).map(r=>r.label)
 assert.deepEqual(main,['Mua nhanh','Đề nghị mua','Báo giá & so sánh','Đơn mua & nhận hàng','Hóa đơn & công nợ'])
 assert.deepEqual(visibleBuyingNavigation(full).filter(r=>r.setup).map(r=>r.id),['suppliers','items'])
 assert.deepEqual(visibleBuyingNavigation({capabilities:{}}).map(r=>r.id),['quick','needs','compare','orders','suppliers','items'],'no finance right: no accounting entry')
})

test('every view keeps its own URL and lights up the entry it lives under',()=>{
 for(const r of procurementNavigation)assert.equal(normalizeBuyingView(r.id),r.id)
 assert.equal(buyingMenu('quotes'),'compare')
 assert.equal(buyingMenu('receipts'),'orders')
 assert.equal(buyingMenu('payables'),'invoices')
 assert.equal(buyingMenu('quick'),'quick')
 assert.deepEqual(buyingGroupViews('payments').map(r=>r.id),['invoices','payments','payables','reports'])
 assert.deepEqual(buyingGroupViews('needs').map(r=>r.id),['needs'],'a single view needs no tabs')
})

test('without the invoice right the accounting entry opens on its first allowed view',()=>{
 const entry=visibleBuyingNavigation({capabilities:{purchasing_finance:true}}).find(r=>r.menu==='invoices')
 assert.equal(entry.id,'payments')
 assert.equal(entry.label,'Hóa đơn & công nợ')
})
