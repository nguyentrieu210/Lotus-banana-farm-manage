import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import * as ps from '../src/purchase-status.js'

const root=path.resolve(import.meta.dirname,'../..')
const read=p=>fs.readFileSync(path.join(root,p),'utf8')

test('purchase status names match the server vocabulary',()=>{
 const server=read('lotus_farm/purchase_status.py')+read('lotus_farm/proposal_rules.py')
 for(const name of [...ps.PROPOSAL_STAGES,...ps.ORDER_STATES,...ps.RECEIPT_STATES,...ps.BILLING_STATES,...ps.INVOICE_STATES,...ps.VOUCHER_STATES,...ps.QUOTE_STATES])
  assert.ok(server.includes("'"+name+"'"),'server lacks '+name)
})

test('older stored names map to the current vocabulary per document kind',()=>{
 assert.equal(ps.purchaseState('order','Từ chối'),'Bị trả lại')
 assert.equal(ps.purchaseState('proposal','Hoàn tất'),'Đã xong')
 assert.equal(ps.purchaseState('proposal','Đã duyệt chờ mua'),'Chờ mua')
 assert.equal(ps.purchaseState('receipt','Đã ghi sổ'),'Đã nhập kho')
 assert.equal(ps.purchaseState('receipt','Đã xác nhận'),'Đã nhập kho')
 // A confirmed quote keeps its own name.
 assert.equal(ps.purchaseState('quote','Đã xác nhận'),'Đã xác nhận')
 assert.equal(ps.purchaseState('order',null),'')
})

test('every state has a tone, unknown text falls back to draft',()=>{
 for(const name of [...ps.PROPOSAL_STAGES,...ps.ORDER_STATES,...ps.RECEIPT_STATES,...ps.BILLING_STATES,...ps.INVOICE_STATES,...ps.VOUCHER_STATES,...ps.QUOTE_STATES])
  assert.notEqual(ps.stateTone(name),undefined)
 assert.equal(ps.stateTone('Quá hạn'),'late')
 assert.equal(ps.stateTone('Đã xong'),'done')
 assert.equal(ps.stateTone('???'),'draft')
})
