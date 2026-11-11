import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import path from 'node:path'

const root=path.resolve(import.meta.dirname,'../..')
const read=f=>readFileSync(path.join(root,f),'utf8')

test('purchase role and submit permission are still required, author is not excluded',()=>{
 const code=read('lotus_farm/purchasing.py')
 const approve=code.slice(code.indexOf('def can_approve(doc):'),code.indexOf('def _ensure_version'))
 const guard=code.slice(code.indexOf('def check_submission'),code.indexOf('@frappe.whitelist()',code.indexOf('def check_submission')))
 assert.match(approve,/_approver\(\)/)
 assert.match(approve,/doc\.has_permission\("submit"\)/)
 assert.match(guard,/saved_state != PENDING/)
 assert.match(guard,/if not _approver\(\):/)
 assert.doesNotMatch(approve+guard,/doc\.owner\s*[!=]=\s*frappe\.session\.user/)
 const signature=read('lotus_farm/digital_signature.py')
 const initials=signature.slice(signature.indexOf('def initial_purchase_order'),signature.indexOf('def _assert_signer_qr'))
 assert.match(initials,/_approver\(\)/)
 assert.doesNotMatch(initials,/actor in \(doc\.owner/)
})

