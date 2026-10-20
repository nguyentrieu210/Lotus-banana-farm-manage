import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'../..')
const read=f=>readFileSync(path.join(root,f),'utf8')
const py=read('lotus_farm/www/lotus_material_proposal_print.py')
const html=read('lotus_farm/www/lotus_material_proposal_print.html')
const stock=read('lotus_farm/www/lotus_stock_print.py')
const stockHtml=read('lotus_farm/www/lotus_stock_print.html')
const buy=read('frontend/src/BuyingMobile.vue')
const warehouse=read('frontend/src/WarehouseMobile.vue')

test('material proposals distinguish buying requests from warehouse release requests',()=>{
 assert.match(py,/material_request_type not in \("Purchase", "Material Issue"\)/)
 assert.match(py,/doc\.check_permission\("read"\)/)
 assert.match(py,/doc\.check_permission\("print"\)/)
 assert.match(py,/PHIẾU ĐỀ XUẤT MUA VẬT TƯ/)
 assert.match(py,/PHIẾU ĐỀ XUẤT CẤP VẬT TƯ/)
 assert.match(py,/context\.farm_label/)
 assert.match(py,/context\.rows = \[\]/)
 assert.match(py,/context\.company_label/)
 assert.match(py,/"Bin"/)
 assert.match(py,/"actual_qty"/)
})
test('buy and warehouse proposals mirror Excel column lists and four signatures',()=>{
 for(const x of ['Quy cách / Thông số kỹ thuật','SL tồn kho hiện tại','SL đề xuất mua',
   'Đơn giá dự kiến (đồng)','Thành tiền (đồng)','Thời gian cần hàng',
   'Nhà cung cấp đề xuất','Mục đích sử dụng',
   'Định mức','SL đề xuất cấp','SL kho cấp phát','Lô / Vị trí sử dụng','Ghi chú',
   'Người đề xuất','Phụ trách bộ phận','Thủ kho','Giám đốc phê duyệt','Phòng Kế toán / Mua hàng'])
  assert.ok(html.includes(x),x)
 assert.match(html,/@page\{size:A4 landscape/)
 assert.match(html,/if purchase/)
 assert.match(html,/Số tiền bằng chữ/)
 assert.match(html,/thead\{display:table-header-group\}/)
 assert.match(html,/number\(total\) if all_priced/)
 assert.doesNotMatch(html,/Trương Văn Hải|19\/10\/2026|19\/11\/2026/)
})
test('proposals cannot claim a completed stock issue or approval without recorded evidence',()=>{
 assert.match(py,/issued_qty=None/)
 assert.match(py,/is_private and file\.attached_to_doctype/)
 assert.match(py,/context\.approval = _safe_signature/)
 assert.match(py,/context\.amount_words = _money_words_vn/)
 assert.match(html,/không chứng minh đã đặt mua hoặc đã xuất kho/)
 assert.match(html,/Chữ ký chỉ hiển thị khi có sự kiện ký/)
 assert.match(html,/Tồn kho là số tại thời điểm/)
})
test('old material request print route and mobile apps open the new print layout',()=>{
 assert.ok(stock.includes("if dt in ('Material Request', 'Material Requirement'):"))
 assert.match(stock,/context\.is_material_proposal = True/)
 assert.ok(stock.includes("if doctype in ('Material Request', 'Material Requirement'):"))
 assert.match(stockHtml,/if is_material_proposal/)
 assert.match(buy,/lotus_material_proposal_print\?name=/)
 assert.match(warehouse,/lastPostedDocument\.value=\{doctype:'Material Request'/)
 assert.match(warehouse,/screen\.value='done'/)
})
test('actual Lotus plan-based material requirements print the issue request, not a stock entry',()=>{
 const work=read('lotus_farm/work_mobile.py')
 const field=read('frontend/src/WorkMobile.vue')
 const schema=JSON.parse(read('lotus_farm/lotus_farm/doctype/material_requirement/material_requirement.json'))
 assert.ok(schema.fields.some(f=>f.fieldname==='lines'))
 assert.match(py,/def _farm_requirement_context\(context, name\)/)
 assert.match(py,/frappe\.get_doc\("Material Requirement", name\)/)
 assert.match(py,/qty=flt\(line\.required_qty\)/)
 assert.match(py,/norm=flt\(line\.norm_qty\)/)
 assert.match(py,/stock=None/)
 assert.match(py,/issued_qty=None/)
 assert.match(work,/task\["material_requirement"\] = requirements\.get\(line\)/)
 assert.match(field,/In phiếu đề xuất cấp vật tư \/ PDF/)
 assert.match(field,/canPrepare&&selected\.material_requirement/)
 assert.match(stock,/if dt in \('Material Request', 'Material Requirement'\)/)
});