import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const app=readFileSync(new URL('../src/App.vue',import.meta.url),'utf8')

test('Thiết lập dự thu dùng nút Lưu thiết lập, không gọi là lưu phiếu nháp',()=>{
 assert.match(app,/editor\.doctype==='Harvest Profile'\?'Lưu thiết lập':'Lưu nháp'/)
 assert.match(app,/editor\.doctype==='Harvest Profile'.*?CHỈNH SỬA BỘ HỆ SỐ/s)
 assert.match(app,/HarvestProfileSettings/)
})
test('Lý do hủy sửa không hiển thị khi nhập một chứng từ bình thường',()=>{
 assert.doesNotMatch(app,/<label>Lý do hủy \/ sửa \/ mở lại/)
 assert.match(app,/v-if="pendingDocumentAction && editor\.name"/)
 assert.match(app,/@click="pendingDocumentAction='cancel';reason=''"/)
 assert.match(app,/@click="pendingDocumentAction='amend';reason=''"/)
 assert.match(app,/:disabled="!reason\.trim\(\)\|\|dialogBusy"/)
 assert.match(app,/@click="pendingDocumentAction='';reason=''"/)
})
test('Giữ luồng xử lý và quyền trên máy chủ, reset trạng thái khi mở phiếu khác',()=>{
 assert.match(app,/consoleAPI\('document_action'/)
 assert.match(app,/pendingDocumentAction\.value='';audit\.value=null/)
 assert.match(app,/schema\.permissions\.cancel/)
 assert.match(app,/schema\.permissions\.amend/)
 assert.match(app,/schema\.permissions\.submit/)
})
