import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {DEFAULT_CCCD_ISSUER} from '../src/cccd-issuer.js'

const read=path=>readFileSync(new URL(path,import.meta.url),'utf8')
const api=read('../../lotus_farm/hr_workspace.py')
const page=read('../../lotus_farm/www/lotus_employee_print.py')
const html=read('../../lotus_farm/www/lotus_employee_print.html')
const desktop=read('../src/HrApp.vue')
const mobile=read('../src/HrMobile.vue')

test('issuer is suggested only; each employee form still allows edits',()=>{
 assert.equal(DEFAULT_CCCD_ISSUER,'Cục Cảnh sát quản lý hành chính về trật tự xã hội')
 for(const code of [desktop,mobile]){
  assert.match(code,/lotus_id_issue_at:DEFAULT_CCCD_ISSUER/)
  assert.match(code,/v-model="employee(?:Form)?\.lotus_id_issue_at"/)
 }
})

test('encrypted CCCD is revealed only through explicit permission-checked POST',()=>{
 assert.match(api,/@frappe\.whitelist\(methods=\["POST"\]\)\s+def reveal_employee_cccd/)
 const fn=api.slice(api.indexOf('def reveal_employee_cccd'),api.indexOf('def check_cccd'))
 assert.match(fn,/_manager\(\)/)
 assert.match(fn,/doc\.check_permission\("read"\)/)
 assert.match(fn,/get_password\("lotus_cccd"/)
 for(const source of [desktop,mobile]){
  assert.match(source,/reveal_employee_cccd/)
  assert.match(source,/revealedCccd/)
  assert.match(source,/Hiện đủ 12 số/)
 }
})

test('onboarding approval captures signer signature and printable form shows it only if recorded',()=>{
 assert.match(api,/def set_onboarding_ready/)
 assert.match(api,/signature_image_bytes\(actor\)/)
 assert.match(api,/is_private=1/)
 assert.match(api,/ONBOARD_APPROVE/)
 assert.match(page,/_manager\(\)/)
 assert.match(page,/signature_file/)
 assert.match(page,/file\.is_private/)
 assert.match(html,/{% if signature_image %}/)
 assert.match(html,/NGƯỜI LAO ĐỘNG/)
 assert.match(html,/NGƯỜI DUYỆT TIẾP NHẬN/)
 assert.match(html,/Số CCCD/)
 for(const source of [desktop,mobile])assert.match(source,/lotus_employee_print/)
})
