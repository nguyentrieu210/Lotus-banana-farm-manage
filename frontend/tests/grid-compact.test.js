import test from 'node:test'
import assert from 'node:assert/strict'
import {numberFormatter,unitColumn,emptyColumn,groupNumber} from '../src/grid-format.js'
import {summableColumn,totalsRow} from '../src/grid-totals.js'
import {load,mount,tick,document} from './support/mount.mjs'

const raw=(row,col)=>col.valueGetter?col.valueGetter({data:row}):row[col.field]
const key=col=>col.field||col.colId

test('plain numbers get digit grouping; codes, years and formatted columns are left alone',()=>{
 const f=numberFormatter({field:'stock_qty',headerName:'SL ĐVT kho'})
 assert.equal(f({value:8482.96}),groupNumber(8482.96))
 assert.equal(f({value:3651163.5084}),(3651163.508).toLocaleString('vi-VN'),'at most three decimals')
 assert.equal(f({value:'abc'}),'abc')
 for(const col of [{field:'year',headerName:'Năm'},{field:'item_code',headerName:'Mã'},{field:'x',headerName:'Năm tài chính'},{field:'qty',valueFormatter:p=>p.value},{field:'qty',groupNumbers:false}])
  assert.equal(numberFormatter(col),null,JSON.stringify(col))
})

test('quantities in different units are not added together; one unit is kept on the total row',()=>{
 const columns=[{field:'item',headerName:'Vật tư'},{field:'stock_qty',headerName:'SL ĐVT kho'},{field:'uom',headerName:'ĐVT'},{field:'stock_uom',headerName:'ĐVT kho'},{field:'gross',headerName:'Tổng trả'}]
 assert.equal(unitColumn(columns[1],columns).field,'stock_uom','stock_qty pairs with stock_uom')
 assert.equal(unitColumn({field:'qty',headerName:'Số lượng'},columns).field,'uom')
 assert.equal(unitColumn({field:'gross',headerName:'Tổng trả'},columns),null)
 assert.equal(unitColumn({field:'n',headerName:'Số lượng',unitField:'stock_uom'},columns).field,'stock_uom')
 const mixed=[{item:'Kali',stock_qty:8482.96,stock_uom:'kg',gross:1},{item:'Kali Sillic',stock_qty:3606,stock_uom:'Lít',gross:2}]
 assert.equal(summableColumn(columns[1],mixed,raw,columns),false,'kg + lít has no meaning')
 assert.equal(summableColumn(columns[4],mixed,raw,columns),true,'money still adds up')
 const same=mixed.map(r=>({...r,stock_uom:'kg'}))
 assert.equal(summableColumn(columns[1],same,raw,columns),true)
 const total=totalsRow(columns,[columns[1],columns[4]],same,raw,key,'Tổng')
 assert.equal(total.stock_qty,12088.96)
 assert.equal(total.stock_uom,'kg','the single unit is carried onto the total row')
 assert.equal(total.item,'Tổng (2 dòng)')
})

test('a column is empty only when no row has anything in it, not even 0',()=>{
 const col={field:'valid_till',headerName:'Hiệu lực'}
 assert.equal(emptyColumn(col,[{valid_till:null},{valid_till:''},{}],raw),true)
 assert.equal(emptyColumn(col,[{valid_till:null},{valid_till:'2026-11-30'}],raw),false)
 assert.equal(emptyColumn({field:'freight'},[{freight:0}],raw),false,'zero is a value')
 assert.equal(emptyColumn(col,[],raw),false,'no rows: keep the headers')
 assert.equal(emptyColumn({...col,autoHide:false},[{}],raw),false)
})

const DataTable=await load('components/DataTable.vue')
const settle=async()=>{await tick();await tick()}
const headers=root=>[...root.querySelectorAll('.ag-header-cell')].map(h=>h.getAttribute('col-id')).filter(id=>!id.startsWith('__lotus'))

test('empty and defaultHidden columns start hidden and come back from Cột hiển thị',async()=>{
 try{localStorage.clear()}catch{}
 const rows=[{name:'Q1',qty:802.92,net:10,valid_till:null},{name:'Q2',qty:3606.028,net:20,valid_till:''}]
 const columns=[{field:'name',headerName:'Báo giá'},{field:'qty',headerName:'Số lượng'},{field:'net',headerName:'Chưa thuế',defaultHidden:true},{field:'valid_till',headerName:'Hiệu lực'}]
 const view=mount(DataTable,{rows,columns,rowKey:'name',storageKey:'compact-test',autoHideEmpty:true})
 await settle()
 assert.deepEqual(headers(view.root),['name','qty'])
 assert.equal(view.root.querySelector('.ag-row[row-id="Q1"] [col-id="qty"]').textContent,groupNumber(802.92))
 view.unmount()
 const plain=mount(DataTable,{rows,columns,rowKey:'name',storageKey:'compact-test-off'})
 await settle()
 assert.deepEqual(headers(plain.root),['name','qty','valid_till'],'other grids (calendars, matrices) keep empty columns')
 plain.unmount()
})

test('a list page puts Cột hiển thị and Xuất Excel on the toolbar row',async()=>{
 const ListPage=await load('components/ListPage.vue')
 const view=mount(ListPage,{rows:[{name:'A',amount:1}],columns:[{field:'name',headerName:'Mã'},{field:'amount',headerName:'Số tiền'}],rowKey:'name'})
 await settle();await settle()
 const tools=view.root.querySelector('.workspace-list-row .workspace-list-tools .lotus-data-table__export')
 assert.ok(tools,'table tools are inside the toolbar row')
 assert.match(tools.textContent,/Xuất Excel/)
 assert.equal(view.root.querySelectorAll('.lotus-data-table__export').length,1,'no second row of tools above the grid')
 view.unmount()
})
