import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const root = new URL('../../', import.meta.url)
const source = name => readFileSync(new URL(name, root), 'utf8')

test('mobile work result is a review draft; imported events retain immediate submit',()=>{
 const body=source('lotus_farm/field.py')
 assert.match(body,/work_review = \(target_doctype == 'Daily Work Result'/)
 const draft=body.split('if work_review:')[1].split('elif scoped:')[0]
 assert.match(draft,/review_state='Pending'/)
 assert.doesNotMatch(draft,/doc\.submit\(/)
 assert.match(draft,/assert_new_result\(values\)/)
 assert.match(draft,/revision_of/)
})
test('role-gated verify and approve can share a user but require both stages',()=>{
 const api=source('lotus_farm/work_review.py')
 const model=source('lotus_farm/lotus_farm/doctype/daily_work_result/daily_work_result.py')
 assert.doesNotMatch(api,/if doc\.owner == frappe\.session\.user/)
 assert.match(api,/if state != "Verified"/)
 assert.doesNotMatch(api,/if doc\.verified_by == frappe\.session\.user/)
 assert.match(api,/require_farm\(doc\.farm\)/)
 assert.match(api,/team not in allowed_teams/)
 assert.match(model,/not self\.verified_by or not self\.reviewed_by/)
 assert.doesNotMatch(model,/len\(\{self\.owner/)
})
test('pending reports remain invisible to submitted-result accounting',()=>{
 const day=source('lotus_farm/daily_api.py')
 assert.match(day,/\'docstatus\':1/)
})
test('mobile review fields exist for migration',()=>{
 const meta=JSON.parse(source('lotus_farm/lotus_farm/doctype/daily_work_result/daily_work_result.json'))
 for(const name of ['review_state','verified_by','verified_at','reviewed_by','reviewed_at','review_note'])
  assert.ok(meta.fields.some(field=>field.fieldname===name), name)
})
test('Block-only work accepts empty legacy small plot and crop cycle',()=>{
 for(const type of ['labor_allocation','material_requirement','material_consumption','material_recovery']){
  const schema=JSON.parse(source('lotus_farm/lotus_farm/doctype/'+type+'/'+type+'.json'))
  for(const fieldname of ['farm_plot','crop_cycle']){
   const field=schema.fields.find(x=>x.fieldname===fieldname)
   assert.ok(field, type+': '+fieldname)
   assert.equal(field.reqd,0,type+': '+fieldname)
  }
 }
})
test('work review submit cannot bypass guarded action via DocType API',()=>{
 const review=source('lotus_farm/work_review.py')
 const result=source('lotus_farm/lotus_farm/doctype/daily_work_result/daily_work_result.py')
 assert.match(review,/command\(doc, "review_result"\)/)
 assert.match(result,/command_allowed\(self, "review_result"\)/)
 assert.match(review,/if not can_approve\(\)/)
 assert.match(review,/if state != "Verified"/)
 assert.match(review,/doc\.actual_workdays/)
})
test('existing offline retries keep their original idempotent payload hash',()=>{
 const file=source('lotus_farm/field.py')
 assert.match(file,/if revision_of:payload\['revision_of'\]=revision_of/)
 assert.match(file,/previous\.payload_hash!=hashed/)
})
test('review inbox keeps notifications even if push is unavailable',()=>{
 const api=source('lotus_farm/work_review.py')
 assert.match(api,/_add_alert\(user, "work"/)
 assert.match(api,/enqueue_after_commit=True/)
 assert.match(api,/"Work Team"/)
 assert.match(api,/"Farm"/)
})