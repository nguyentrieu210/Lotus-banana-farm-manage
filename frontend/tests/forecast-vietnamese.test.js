import {test} from 'node:test'
import assert from 'node:assert/strict'
import {label,stateLabel,docLabel} from '../src/labels.js'
import {readFileSync} from 'node:fs'

test('Dự thu hiển thị tiếng Việt nhưng vẫn giữ nguyên mã dữ liệu',()=>{
 assert.equal(label('forecast_basis','Forecast Basis'),'Nguồn tính dự thu')
 assert.equal(label('source_bunch_qty','Source Bunch Qty'),'Số buồng làm căn cứ')
 assert.equal(label('avg_bunch_weight_kg'),'Bình quân kg mỗi buồng')
 assert.equal(label('output_plan'),'Danh sách thành phẩm dự kiến')
 assert.equal(label('packout_profile'),'Bộ hệ số đóng gói')
 assert.equal(label('supersedes'),'Điều chỉnh từ phiếu')
 assert.equal(label('revision_reason'),'Lý do điều chỉnh')
 assert.equal(docLabel('Harvest Forecast'),'Dự thu')
})

test('Lựa chọn Dự thu và Kế hoạch dịch chữ, không thay giá trị lưu ERP',()=>{
 const values=[
  ['Manual','Nhập tay'],['Sucker Selection','Theo đợt chọn chồi'],
  ['Shooting Operations','Theo số buồng đã trổ'],['Cut Bud Operations','Theo số buồng đã cắt bắp'],
  ['Week','Theo tuần'],['Month','Theo tháng'],['Custom','Tự chọn ngày'],
  ['Low','Thấp'],['Medium','Trung bình'],['High','Cao'],
  ['Available','Còn nguồn'],['Tight','Nguồn còn ít'],['Overcommitted','Đã giữ vượt dự thu'],
  ['Released','Đã phát hành'],['Superseded','Đã thay thế'],
  ['Not Required','Không cần duyệt'],['Stock Entry Reversal','Hoàn tác phiếu kho'],
 ]
 for(const [raw,display] of values)assert.equal(stateLabel(raw),display,raw)
 const doc=JSON.parse(readFileSync(new URL('../../lotus_farm/lotus_farm/doctype/harvest_forecast/harvest_forecast.json',import.meta.url)))
 assert.equal(doc.fields.find(f=>f.fieldname==='forecast_basis').options.split('\n')[0],'Manual')
 assert.equal(doc.fields.find(f=>f.fieldname==='supply_state').default,'Draft')
})

test('Các trường kế hoạch và đối soát có tiêu đề tiếng Việt',()=>{
 assert.equal(label('rate_approval_signature'),'Xác nhận duyệt đơn giá')
 assert.equal(label('reconciliation_type'),'Loại đối soát nguồn cung')
 assert.equal(label('reservation_disposition'),'Cách xử lý lượng hàng đã giữ')
 assert.equal(label('expected_packed_kg'),'Thành phẩm dự kiến (kg)')
 assert.equal(label('gross_forecast_kg'),'Dự thu ngoài vườn (kg buồng)')
})
