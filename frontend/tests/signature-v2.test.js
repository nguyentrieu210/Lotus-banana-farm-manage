import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const read=path=>readFileSync(new URL(path,import.meta.url),'utf8')
const signing=read('../../lotus_farm/digital_signature.py')
const buying=read('../src/BuyingMobile.vue')
const purchasing=read('../../lotus_farm/purchasing.py')
const profile=read('../src/components/LotusMobileSignatureSettings.vue')
const draw=read('../src/components/LotusSignatureDraw.vue')
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
test('initials, approval and signature QR enforce permissions and audit separately',()=>{
 assert.match(signing,/def initial_purchase_order\(name, modified\)/)
 assert.doesNotMatch(signing,/actor in \(doc.owner, doc.get\("lotus_requested_by"\)\)/)
 assert.match(signing,/_approver\(\)/)
 assert.match(signing,/Lotus Purchase Reviewer/)
 assert.match(signing,/_event\(doc, "INITIAL"/)
 assert.match(signing,/_event\(doc, "APPROVE"/)
 assert.match(purchasing,/def approve_order\(name, modified, sign_token=None\)/)
 assert.match(purchasing,/_assert_signer_qr\(sign_token, name, modified\)/)
 assert.match(signing,/record.user != frappe.session.user/)
 assert.match(signing,/record.used_at/)
 assert.match(signing,/timedelta\(seconds=120\)/)
 assert.match(buying,/Hiện QR để duyệt trên điện thoại/)
 assert.match(buying,/Ký nháy xác nhận đã kiểm tra/)
 assert.match(signing,/needs_confirmation/)
})
test('QR verification checks hashed token and actual immutable PDF digest without disclosing signatures',()=>{
 assert.match(signing,/secrets.token_urlsafe\(32\)/)
 assert.match(signing,/def verify_document\(token\)/)
 assert.match(signing,/hmac.compare_digest\(actual, expected\)/)
 assert.match(signing,/doc.docstatus == 1/)
 assert.match(signing,/frappe.get_doc\("File", matched\[0\]\).get_content\(encodings=\[\]\)/)
 assert.match(signing,/_qr_png\(_verification_url\(verify_token\)\)/)
 assert.match(verify,/result.pdf_sha256/)
 assert.doesNotMatch(verify,/signature_preview|image_data|private_file_url/)
})
test('audit and challenge DocTypes are restricted and have safe identifiers',()=>{
 for(const name of ['lotus_signature_event','lotus_signing_challenge']){
  const j=JSON.parse(read('../../lotus_farm/lotus_farm/doctype/'+name+'/'+name+'.json'))
  assert.equal(j.autoname,'hash')
  assert.deepEqual(j.permissions.map(x=>x.role),['System Manager'])
 }
 const event=JSON.parse(read('../../lotus_farm/lotus_farm/doctype/lotus_signature_event/lotus_signature_event.json'))
 assert.ok(event.fields.some(x=>x.fieldname==='pdf_sha256'))
 const challenge=JSON.parse(read('../../lotus_farm/lotus_farm/doctype/lotus_signing_challenge/lotus_signing_challenge.json'))
 assert.ok(challenge.fields.some(x=>x.fieldname==='token_hash'&&x.unique===1))
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