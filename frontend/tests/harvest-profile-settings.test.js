import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const root=new URL('../../',import.meta.url)
const read=p=>readFileSync(new URL(p,root),'utf8')
test('giao diện hệ số chia 3 bước, giải thích từng số và thêm phép thử không ghi dữ liệu',()=>{
 const ui=read('frontend/src/components/HarvestProfileSettings.vue')
 assert.match(ui,/1\. Áp dụng cho vườn nào/)
 assert.match(ui,/2\. Bao lâu thì đến kỳ thu/)
 assert.match(ui,/3\. Một buồng cho ra bao nhiêu kg/)
 assert.match(ui,/DỮ LIỆU|Chỉ thiết lập cách TÍNH dự thu/)
 assert.match(ui,/1\.000 buồng/)
 assert.match(ui,/readonly="readonly"/)
 assert.match(ui,/Trồng|trồng/)
 assert.match(ui,/SchemaForm/)
 assert.doesNotMatch(ui,/\.insert\(|\.save\(|consoleAPI\(/)
})
test('tất cả trường bắt buộc của DocType vẫn có trong các nhóm, không tạo hệ số mặc định',()=>{
 const doc=JSON.parse(read('lotus_farm/lotus_farm/doctype/harvest_profile/harvest_profile.json'))
 const ui=read('frontend/src/components/HarvestProfileSettings.vue')
 const groupText=ui.slice(ui.indexOf('const sections=['),ui.indexOf('const help={'))
 for(const field of doc.fields.filter(f=>f.reqd)){
  assert.match(groupText,new RegExp("'"+field.fieldname+"'"),'Chưa đưa trường bắt buộc vào giao diện: '+field.fieldname)
 }
 for(const field of ['planting_to_harvest_days','ratoon_interval_days','sucker_to_harvest_days','shooting_to_harvest_days','cut_bud_to_harvest_days']){
  assert.match(groupText,new RegExp("'"+field+"'"))
  assert.equal(doc.fields.find(f=>f.fieldname===field)?.default,undefined)
 }
 assert.doesNotMatch(groupText,/calibration_json|calibration_hash/)
})
test('màn sửa bộ hệ số dùng biểu mẫu hướng dẫn, không đổi dữ liệu nghiệp vụ',()=>{
 const app=read('frontend/src/App.vue')
 assert.match(app,/import HarvestProfileSettings from/)
 assert.match(app,/editor\.doctype==='Harvest Profile'/)
 assert.match(app,/<SchemaForm v-else :schema="schema"/)
})
