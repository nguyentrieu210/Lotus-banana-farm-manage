import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import path from 'node:path'

const root=path.resolve(import.meta.dirname,'../..')
const read=f=>readFileSync(path.join(root,f),'utf8')

test('purchase orders need the named approver signature; the author is not excluded',()=>{
 const code=read('lotus_farm/purchasing.py')
 const approve=code.slice(code.indexOf('def can_approve(doc):'),code.indexOf('def _ensure_version'))
 const guard=code.slice(code.indexOf('def check_submission'),code.indexOf('def _earlier_submission_rule'))
 assert.match(approve,/_approver\(\)/)
 assert.match(approve,/doc\.has_permission\("submit"\)/)
 assert.match(guard,/saved != PENDING/)
 assert.match(guard,/Đơn mua chưa có đủ chữ ký của người duyệt được chỉ định/)
 assert.match(guard,/frappe\.session\.user not in \(approver, "Administrator"\)/)
 assert.doesNotMatch(guard,/lotus_policy_approved/,'no approval by policy (spec 003)')
 assert.doesNotMatch(approve+guard,/doc\.owner\s*[!=]=\s*frappe\.session\.user/)
 const signature=read('lotus_farm/digital_signature.py')
 assert.doesNotMatch(signature,/def initial_purchase_order|def create_signing_challenge|def _assert_signer_qr/)
})

