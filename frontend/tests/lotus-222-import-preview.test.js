import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const root=new URL('../../',import.meta.url)
const read=p=>readFileSync(new URL(p,root),'utf8')
test('Bảng nhập mẫu sử dụng API riêng có kiểm tra quyền, không ghi sổ',()=>{
 const server=read('lotus_farm/forecast_import_preview.py')
 assert.match(server,/has_permission\("Farm Block", "read"\)/)
 assert.match(server,/has_permission\("Harvest Forecast", "read"\)/)
 assert.match(server,/land_scope\(farm=FARM, block=block\)/)
 assert.match(server,/land_filters/)
 assert.match(server,/get_site_path\("private", "files", DATA_FILE\)/)
 assert.doesNotMatch(server,/\.insert\(|\.save\(|set_value\(|\.db\.set_value\(|\.db\.sql\(/)
})
test('Không biến số cây trong ảnh thành mật độ trồng hoặc trổ thực tế',()=>{
 const src=read('lotus_farm/forecast_import_preview.py')
 assert.doesNotMatch(src,/set_value\(|\.insert\(|\.save\(|write_csv\(/)
 assert.match(src,/Ước tính người dùng/)
 assert.match(src,/ready_for_release": False/)
 assert.match(src,/2026-11-01/)
 assert.match(src,/2027-01-17/)
 assert.match(src,/2027-03-29/)
})
test('Giao diện gọi API có kiểm tra quyền, hiển thị chờ xác nhận',()=>{
 const app=read('frontend/src/App.vue')
 const ui=read('frontend/src/components/LotusImportPreview.vue')
 assert.match(app,/import\('\.\/components\/LotusImportPreview\.vue'\)/)
 assert.match(app,/<LotusImportPreview /)
 assert.match(ui,/lotus_farm\.forecast_import_preview\.preview/)
 assert.match(ui,/ƯỚC TÍNH KHU A/)
 assert.match(ui,/Chưa xác nhận/)
 assert.match(ui,/tree_count===null/)
 assert.doesNotMatch(ui,/localStorage|indexedDB|\.save\(/)
})
