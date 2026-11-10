import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const read=path=>readFileSync(new URL(path,import.meta.url),'utf8')
const signing=read('../../lotus_farm/digital_signature.py')
const buying=read('../src/BuyingMobile.vue')
const purchasing=read('../../lotus_farm/purchasing.py')
const profile=read('../src/components/LotusMobileSignatureSettings.vue')
const draw=read('../src/components/LotusSignatureDraw.vue')+read('../src/components/signing/SignaturePad.vue')
const verify=read('../../lotus_farm/www/verify/lotus.html')
test('signature and initials saved independently with a server-controlled signing clock',()=>{
 for(const x of ['INITIAL_FIELD','INITIAL_UPDATED_FIELD','DATE_FORMAT_FIELD','save_my_initials_image','remove_my_initials_image','save_my_signature_date_format']){
  assert.ok(signing.includes(x),x)
 }
 assert.match(signing,/date_format not in DATE_FORMATS/)
 assert.match(signing,/now_datetime\(\)/)
 assert.match(profile,/save_my_initials_image/)
 assert.match(profile,/save_my_signature_date_format/)
 assert.match(profile,/LotusSignatureDraw/)
 assert.match(draw,/@pointerdown="start"/)
 assert.match(draw,/toDataURL\('image\/png'\)/)
})
test('QR codes only verify; ký nháy comes from the checking step; approval needs no token (spec 003)',()=>{
 const core=read('../../lotus_farm/signing.py')
 const rules=read('../../lotus_farm/signing_rules.py')
 for(const removed of ['def initial_purchase_order','def create_signing_challenge','def signing_challenge_details','def _assert_signer_qr'])
  assert.ok(!signing.includes(removed),removed)
 assert.match(purchasing,/def approve_order\(name, modified\):/)
 assert.doesNotMatch(purchasing,/sign_token/)
 assert.doesNotMatch(buying,/Hiện QR để duyệt trên điện thoại|Ký nháy xác nhận đã kiểm tra|create_signing_challenge|initial_purchase_order/)
 assert.match(rules,/CHECKER_STEPS = \{'purchase_proposal': 2, 'purchase_order': 0, 'payment_voucher': 1\}/)
 assert.match(core,/if rules\.checker_step\(key\) == row\.step_index:/)
 assert.match(core,/initials_image_bytes\(frappe\.session\.user\)/)
 assert.match(core,/def print_initials\(doc\)/)
})
test('QR verification compares the stored signed PDF without disclosing signatures',()=>{
 const core=read('../../lotus_farm/signing.py')
 const copy=read('../../lotus_farm/signed_copy.py')
 assert.match(signing,/def verify_document\(token\)/,'older approved orders still verify by their token')
 assert.match(signing,/hmac.compare_digest\(actual, expected\)/)
 assert.match(signing,/doc.docstatus == 1/)
 assert.match(core,/archive_match=signed_copy\.matches\(copy\) if copy else None/)
 assert.match(copy,/def matches\(copy\)/)
 assert.match(verify,/Khớp bản lưu/)
 assert.match(verify,/result.pdf_sha256/)
 assert.doesNotMatch(verify,/signature_preview|image_data|private_file_url/)
})
test('audit and signed copy DocTypes are restricted and have safe identifiers',()=>{
 const event=JSON.parse(read('../../lotus_farm/lotus_farm/doctype/lotus_signature_event/lotus_signature_event.json'))
 assert.equal(event.autoname,'hash')
 assert.deepEqual(event.permissions.map(x=>x.role),['System Manager'])
 for(const field of ['pdf_sha256','ip','user_agent','roles','designation','round','step_key','content_hash','image_sha256'])
  assert.ok(event.fields.some(x=>x.fieldname===field),field)
 const copy=JSON.parse(read('../../lotus_farm/lotus_farm/doctype/lotus_signed_copy/lotus_signed_copy.json'))
 assert.deepEqual(copy.permissions.map(x=>x.role),['System Manager','Lotus Auditor'])
 assert.ok(copy.permissions.every(x=>!x.write&&!x.create&&!x.delete),'nobody edits a signed copy')
 const controller=read('../../lotus_farm/lotus_farm/doctype/lotus_signed_copy/lotus_signed_copy.py')
 assert.match(controller,/self\.name = copy_name\(self\.document_type, self\.document_name, self\.round\)/,'one copy per document and round')
})
test('migration registers every personal and order signature field',()=>{
 for(const field of ['IMAGE_FIELD','DATE_FIELD','INITIAL_FIELD','INITIAL_UPDATED_FIELD','DATE_FORMAT_FIELD',
   'lotus_signature_verify_hash','lotus_signature_pdf_sha256','lotus_initials_by',
   'lotus_initials_at','lotus_initials_snapshot','lotus_signed_purchase_pdf']){
  assert.ok(signing.includes('"fieldname": '+(field.endsWith('_FIELD')?field:'"'+field+'"')),field)
 }
 assert.match(signing,/def _current_file\(user, field=IMAGE_FIELD\):/)
 assert.match(signing,/initial_bytes = initials\.get_content\(encodings=\[\]\) if initials else None/)
 assert.match(signing,/"options": "\\n"\.join\(DATE_FORMATS\)/)
 assert.match(signing,/import hashlib/)
 assert.match(signing,/import secrets/)
})