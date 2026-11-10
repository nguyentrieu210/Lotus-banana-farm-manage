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

test('rate approval keeps role, over-price check and tamper-resistant signature',()=>{
 const code=read('lotus_farm/rate_approval.py')
 const decide=code.slice(code.indexOf('def decide(plan,'),code.indexOf('return {"plan": doc.name, "status": "Submitted"'))
 assert.match(decide,/require_role\("Lotus Price Approver"\)/)
 assert.match(decide,/needs_approval\(doc\)/)
 assert.match(decide,/_signature\(doc\)/)
 assert.doesNotMatch(decide,/doc\.owner\s*==\s*frappe\.session\.user/)
 const validate=code.slice(code.indexOf('def validate_plan'),code.indexOf('@frappe.whitelist()',code.indexOf('def validate_plan')))
 assert.match(validate,/hmac\.compare_digest/)
 assert.doesNotMatch(validate,/rate_approved_by\s*!=\s*doc\.owner/)
})

test('field review permits self review only for the actual verifier/finalizer role',()=>{
 const code=read('lotus_farm/work_review.py')
 const d=code.slice(code.indexOf('def decide(result,'),code.indexOf('def prepare_revision'))
 assert.match(d,/if not can_verify\(\)/)
 assert.match(d,/if not can_approve\(\)/)
 assert.match(d,/state != "Verified"/)
 assert.match(d,/actual_workdays/)
 assert.doesNotMatch(d,/doc\.owner\s*==\s*frappe\.session\.user/)
 assert.doesNotMatch(d,/verified_by\s*==\s*frappe\.session\.user/)
})
