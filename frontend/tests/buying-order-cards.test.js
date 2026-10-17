import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {purchaseOrderStatus,purchaseStatusTone} from '../src/buying-order-status.js'
const root=path.resolve(import.meta.dirname,'../..')
const read=p=>fs.readFileSync(path.join(root,p),'utf8')
test('Draft and pending order states display without being split',()=>{
 assert.equal(purchaseOrderStatus({docstatus:0,approval_status:'Nháp'}),'Nháp')
 assert.equal(purchaseStatusTone({docstatus:0,approval_status:'Nháp'}),'draft')
 assert.equal(purchaseOrderStatus({docstatus:0,approval_status:'Chờ duyệt'}),'Chờ duyệt')
 assert.equal(purchaseStatusTone({docstatus:0,approval_status:'Chờ duyệt'}),'pending')
 assert.equal(purchaseOrderStatus({docstatus:2,approval_status:'Đã duyệt'}),'Đã hủy')
 assert.equal(purchaseOrderStatus({docstatus:1,status:'Về một phần',approval_status:'Đã duyệt'}),'Về một phần')
})
test('Both homepage and orders tab reuse the same purchase card',()=>{
 const ui=read('frontend/src/BuyingMobile.vue')
 const matches=ui.match(/<BuyingOrderCard\s+v-for=/g)||[]
 assert.equal(matches.length,2)
 assert.match(ui,/:order="r"/)
 assert.match(ui,/show-date @select="openOrder"/)
 const card=read('frontend/src/components/BuyingOrderCard.vue')
 assert.match(card,/LotusMobileButton class="buy-order-card"/)
 assert.match(card,/buy-order-supplier/)
 assert.match(card,/buy-order-status/)
 assert.match(card,/buy-order-code/)
 assert.match(card,/buy-order-bottom/)
 assert.match(card,/buy-order-amount/)
})
test('Vant wrappers expand to full width while amounts and badges stay on one line',()=>{
 const css=read('frontend/src/buying-mobile.css')
 assert.match(css,/\.buy-order-card \.van-button__text\{/)
 assert.match(css,/\.buy-order-status\{[^}]*white-space:nowrap/s)
 assert.match(css,/\.buy-order-amount\{[^}]*white-space:nowrap/s)
 assert.match(css,/\.buy-order-supplier\{[^}]*text-overflow:ellipsis/s)
})
