import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const read=path=>readFileSync(new URL(path,import.meta.url),'utf8')
const widget=read('../src/components/LotusMobileSignatureSettings.vue')
const backend=read('../../lotus_farm/digital_signature.py')
const installation=read('../../lotus_farm/install.py')

test('all four mobile Tôi tabs share the account signature settings',()=>{
 for(const filename of ['WarehouseMobile.vue','BuyingMobile.vue','WorkMobile.vue','HrMobile.vue']){
  const source=read('../src/'+filename)
  assert.match(source,/import LotusMobileSignatureSettings from/)
  assert.match(source,/<LotusMobileSignatureSettings :user="session\?\.user\|\|''"\/>/)
 }
})
test('signature profile always distinguishes provider preference from certificate activation',()=>{
 assert.match(backend,/def my_signature_profile\(\)/)
 assert.match(backend,/"connected": False/)
 assert.match(backend,/"certificate_verified": False/)
 assert.match(backend,/"can_sign_pdf": False/)
 assert.match(backend,/user == "Guest"/)
 assert.match(backend,/provider not in PROVIDERS/)
 assert.match(backend,/frappe\.db\.set_value\("User", user, FIELD, provider\)/)
 assert.match(installation,/install_signature_fields\(\)/)
 assert.match(widget,/lotus_farm\.digital_signature\./)
 assert.match(widget,/set_signature_provider/)
 assert.match(widget,/Chưa kết nối/)
 assert.match(widget,/Bấm Duyệt hiện chưa tự ký số vào PDF/)
 assert.doesNotMatch(widget,/private_key|passphrase|pin_code/)
})
