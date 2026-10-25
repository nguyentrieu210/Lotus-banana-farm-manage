import {formatDate} from './format'
import {unitLabel} from './units'
// Column definitions for every Kho list. Kho shows quantities only: valuation and stock value stay in Kế toán.
export const fmt=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
export const statusLabel=s=>['Nháp','Đã ghi sổ','Đã hủy'][s]??s
export const entryTypeLabel=t=>({'Material Receipt':'Nhập kho','Material Issue':'Xuất dùng','Material Transfer':'Chuyển kho','Repack':'Đóng gói','Opening Stock':'Tồn đầu kỳ','Stock Reconciliation':'Kiểm kê'})[t]||t
const number=(field,headerName,minWidth=100)=>({field,headerName,minWidth,type:'numericColumn',valueFormatter:p=>p.value==null?'—':fmt(p.value)})
function itemCell(params){const cell=document.createElement('span');cell.className='lotus-item-cell';for(const [cls,text] of [['name',params.data.item_name],['code',params.data.name||params.data.item_code]]){const span=document.createElement('span');span.className=cls;span.textContent=text;cell.append(span)}return cell}

// Natural reading order: item identity → actual stock → global minimum → demand/arrival.
export const stockColumns=[
 {field:'name',valueGetter:p=>p.data.item_name,headerName:'Tên hàng',minWidth:200,flex:1.6,cellRenderer:itemCell,tooltipValueGetter:p=>p.data.item_name+' · '+p.data.name,mobileValue:r=>r.item_name+' · '+r.name},
 {field:'item_group',headerName:'Nhóm hàng',minWidth:130},
 {field:'stock_uom',headerName:'ĐVT',minWidth:78,valueFormatter:p=>unitLabel(p.value)},
 number('actual_qty','Tồn kho',105),
 {field:'pack_actual_qty',headerName:'Tồn quy đổi',minWidth:132,tooltipValueGetter:p=>p.data?.pack_uom&&p.data?.pack_factor?'1 '+unitLabel(p.data.pack_uom)+' = '+fmt(p.data.pack_factor)+' '+unitLabel(p.data.stock_uom):'Chưa có đơn vị quy đổi',valueFormatter:p=>p.data?.pack_uom&&p.value!=null?fmt(p.value)+' '+unitLabel(p.data.pack_uom):'—'},
 number('minimum_stock','Tối thiểu chung',135),
 number('shortage_qty','Thiếu tối thiểu',125),
 {field:'stock_status',headerName:'Cảnh báo tồn',minWidth:125},
 number('demand_qty','Cần dùng',100),
 number('available_qty','Có thể dùng',115),
 number('demand_shortage_qty','Thiếu theo nhu cầu',145),
 number('incoming_qty','Sắp về',95),
 number('to_buy_qty','Cần mua',100),
 {field:'coverage_status',headerName:'Tình trạng nhu cầu',minWidth:150,cellClass:p=>'lotus-coverage-state '+({'Đủ hàng':'is-covered','Chờ nhập':'is-incoming','Cần mua':'is-short'}[p.value]||'')}
]

export function documentColumns(warehouseLabel){return [
 {field:'posting_date',headerName:'Ngày',minWidth:110,valueFormatter:p=>formatDate(p.value)},
 {field:'name',headerName:'Số phiếu',minWidth:215,flex:1.5},
 {field:'kind',headerName:'Loại phiếu',minWidth:125},
 {field:'warehouses',headerName:'Kho liên quan',minWidth:210,valueFormatter:p=>String(p.value||'').split(' · ').map(warehouseLabel).join(' · ')},
 {field:'docstatus',headerName:'Trạng thái',minWidth:120,valueFormatter:p=>statusLabel(p.value)}
]}

export function movementColumns(warehouseLabel){return [
 {field:'posting_date',headerName:'Ngày',minWidth:105,valueFormatter:p=>formatDate(p.value)},
 {field:'item_code',headerName:'Tên hàng',minWidth:200,flex:1.6,valueFormatter:p=>p.data?p.data.item_name+' · '+p.value:p.value},
 {field:'warehouse',headerName:'Kho',minWidth:130,valueFormatter:p=>warehouseLabel(p.value)},
 number('opening_qty','Tồn trước',80),number('in_qty','Nhập',75),number('out_qty','Xuất',75),number('qty_after_transaction','Tồn sau',85),
 {field:'stock_uom',headerName:'ĐVT',minWidth:65,valueFormatter:p=>unitLabel(p.value)},
 {field:'voucher_no',headerName:'Số phiếu',minWidth:170},
 {field:'kind',headerName:'Loại biến động',minWidth:95}
]}

// Nhập – xuất – tồn (quantities). The value version of this report lives in Kế toán → Báo cáo.
export function reportColumns(warehouseLabel){return [
 {field:'item_code',headerName:'Tên hàng',minWidth:220,flex:1.6,valueFormatter:p=>p.data?p.data.item_name+' · '+p.value:p.value},
 {field:'item_group',headerName:'Nhóm hàng',minWidth:130},
 {field:'warehouse',headerName:'Kho',minWidth:140,valueFormatter:p=>warehouseLabel(p.value)},
 {field:'stock_uom',headerName:'ĐVT',minWidth:70,valueFormatter:p=>unitLabel(p.value)},
 number('opening_qty','Tồn đầu kỳ',110),number('in_qty','Nhập trong kỳ',120),number('out_qty','Xuất trong kỳ',120),number('closing_qty','Tồn cuối kỳ',115)
]}

export function detailColumns(warehouseLabel){return [
 {headerName:'Vật tư',minWidth:220,flex:2,valueGetter:p=>p.data.item_name||p.data.item},
 {field:'item',headerName:'Mã vật tư'},
 {field:'qty',headerName:'Số lượng',type:'numericColumn',valueFormatter:p=>fmt(p.value)},
 {field:'uom',headerName:'Đơn vị',valueFormatter:p=>unitLabel(p.value)},
 {field:'area',headerName:'Khu vực / lô'},
 {headerName:'Kho xuất / nhận',minWidth:220,valueGetter:p=>[p.data.source,p.data.target].filter(Boolean).map(warehouseLabel).join(' → ')}
]}

// Receipt lines keep the entered rate and allocated costs (what was paid), never the valuation rate.
export function receiptDetailColumns(cash){return [
 {field:'rate',headerName:'Đơn giá',type:'numericColumn',valueFormatter:p=>cash(p.value)},
 {field:'additional_cost',headerName:'Chi phí phân bổ',type:'numericColumn',valueFormatter:p=>cash(p.value)},
 {field:'amount',headerName:'Thành tiền',type:'numericColumn',valueFormatter:p=>cash(p.value)}
]}

export const masterColumns={
 warehouses:[{field:'warehouse_name',headerName:'Tên kho',minWidth:180,flex:1.2},{field:'name',headerName:'Mã kho',minWidth:160},{field:'lotus_address',headerName:'Địa chỉ kho',minWidth:220,flex:1.4},{field:'lotus_contact_name',headerName:'Người phụ trách',minWidth:150},{field:'lotus_contact_phone',headerName:'Liên hệ',minWidth:120},{field:'lotus_default_lead_days',headerName:'Chờ hàng (ngày)',minWidth:120,type:'numericColumn'}],
 items:[{field:'item_name',headerName:'Tên vật tư',minWidth:220,flex:1.6},{field:'name',headerName:'Mã vật tư',minWidth:160},{field:'item_group',headerName:'Nhóm vật tư',minWidth:140},{field:'stock_uom',headerName:'ĐVT gốc',minWidth:90,valueFormatter:p=>unitLabel(p.value)},{field:'pack_uom',headerName:'Quy đổi',minWidth:150,valueFormatter:p=>p.value?'1 '+unitLabel(p.value)+' = '+fmt(p.data.pack_factor)+' '+unitLabel(p.data.stock_uom):'—'},number('minimum_stock','Tồn tối thiểu',120),{field:'disabled',headerName:'Trạng thái',minWidth:110,valueFormatter:p=>p.value?'Ngừng dùng':'Đang dùng'}],
 groups:[{field:'name',headerName:'Nhóm vật tư',minWidth:200,flex:1.4},{field:'parent_item_group',headerName:'Thuộc nhóm',minWidth:180}],
 uoms:[{field:'name',headerName:'Mã đơn vị',minWidth:160},{headerName:'Tên hiển thị',minWidth:160,flex:1,valueGetter:p=>unitLabel(p.data.name)},{field:'must_be_whole_number',headerName:'Chỉ số nguyên',minWidth:120,valueFormatter:p=>p.value?'Có':'Không'},{field:'enabled',headerName:'Trạng thái',minWidth:120,valueFormatter:p=>p.value?'Đang dùng':'Ngừng dùng'}]
}
