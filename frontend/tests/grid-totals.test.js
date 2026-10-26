import test from 'node:test'
import assert from 'node:assert/strict'
import {summableColumn,totalsRow} from '../src/grid-totals.js'

const raw=(row,col)=>col.valueGetter?col.valueGetter({data:row}):row[col.field]
const key=col=>col.field||col.colId
const rows=[{item:'Phân',qty:2,amount:1000,rate:500,uom:'kg',year:2026},{item:'Thuốc',qty:3.5,amount:2500,rate:714,uom:'lít',year:2026}]

test('sums quantities and money, never prices, codes, years or text',()=>{
 const columns=[{field:'item',headerName:'Vật tư'},{field:'qty',headerName:'Số lượng'},{field:'amount',headerName:'Thành tiền'},{field:'rate',headerName:'Đơn giá'},{field:'uom',headerName:'ĐVT'},{field:'year',headerName:'Năm'}]
 assert.deepEqual(columns.filter(c=>summableColumn(c,rows,raw)).map(key),['qty','amount'])
 assert.equal(summableColumn({field:'rate',headerName:'Đơn giá',sum:true},rows,raw),true,'a column can opt in')
 assert.equal(summableColumn({field:'qty',headerName:'Số lượng',sum:false},rows,raw),false,'a column can opt out')
 assert.equal(summableColumn({field:'balance',headerName:'Số dư'},[{balance:1},{balance:2}],raw),false,'running balances are not added up')
 const period=[{a:1,b:2},{a:3,b:4}]
 for(const headerName of ['Giá trị nhập','Nhập trong kỳ','Tồn cuối kỳ','Giờ làm','Ngày công','Chi phí tháng'])assert.equal(summableColumn({field:'a',headerName},period,raw),true,headerName)
 for(const headerName of ['Tháng','Năm','Vụ','Tuổi cây','Giá bán'])assert.equal(summableColumn({field:'a',headerName},period,raw),false,headerName)
})

test('the sum row labels the first text column with the row count',()=>{
 const columns=[{field:'item',headerName:'Vật tư'},{field:'qty',headerName:'Số lượng'},{field:'amount',headerName:'Thành tiền'}]
 const total=totalsRow(columns,columns.slice(1),rows,raw,key,'Tổng')
 assert.deepEqual({item:total.item,qty:total.qty,amount:total.amount},{item:'Tổng (2 dòng)',qty:5.5,amount:3500})
})

test('numeric codes shown as words are not summed',()=>{
 const docs=[{docstatus:1},{docstatus:2},{docstatus:1}]
 assert.equal(summableColumn({field:'docstatus',headerName:'Trạng thái',valueFormatter:p=>['Nháp','Đã ghi sổ','Đã hủy'][p.value]},docs,raw),false)
 assert.equal(summableColumn({field:'x',headerName:'Cờ',valueFormatter:p=>p.value?'Ngừng dùng':'Đang dùng'},[{x:1},{x:0}],raw),false)
 assert.equal(summableColumn({field:'qty',headerName:'Số lượng',valueFormatter:p=>p.value+' kg'},[{qty:1},{qty:2}],raw),true,'formatted amounts still add up')
 assert.equal(summableColumn({field:'v',headerName:'Giá trị nhập',valueFormatter:p=>p.value?p.value.toLocaleString('vi-VN'):''},[{v:0},{v:1600000}],raw),true,'a blank zero does not hide the column')
})
