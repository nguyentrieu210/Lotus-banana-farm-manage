// Typed DataTable columns (spec 004, FR-014): text for filters, cards, the sum row and Excel; DOM cells for the grid.
import test from 'node:test'
import assert from 'node:assert/strict'
import {window} from './support/mount.mjs'
import {numberCol,moneyCol,qtyCol,percentCol,dateCol,dueCol,statusCol,progressCol,ribbonCol,personCol,deltaCol,chipNode} from '../src/grid-columns.js'
import {GRID_APP_KEYS} from '../src/grid-app-keys.js'
import {summableColumn} from '../src/grid-totals.js'

const fmt=(col,value,data={})=>col.valueFormatter({value,data})
const cell=(col,value,data={})=>col.cellRenderer({value,data})
const AG_KEYS=new Set(['field','headerName','type','cellClass','valueFormatter','cellRenderer','minWidth','flex','pinned','hide','width','sortable','tooltip','headerTooltip'])

test('numbers: Vietnamese grouping, units, right aligned, blanks stay blank',()=>{
 const n=numberCol('cut','Cắt bắp',{unit:'buồng'})
 assert.equal(n.type,'numericColumn');assert.equal(fmt(n,9328),'9.328 buồng');assert.equal(fmt(n,null),'');assert.equal(fmt(n,0),'0 buồng')
 assert.equal(fmt(moneyCol('amount','Thành tiền'),46200000),'46.200.000 đ')
 assert.equal(fmt(percentCol('rate','Tỉ lệ'),12.345),'12,3%')
 assert.equal(fmt(dateCol('date','Ngày'),'2026-11-10'),'10/11/2026')
})

test('quantities carry their unit and never add different units on the sum row',()=>{
 const q=qtyCol('qty','Số lượng',{unitField:'uom',digits:0})
 assert.equal(q.unitField,'uom');assert.equal(fmt(q,120,{uom:'bao'}),'120 bao')
 const rows=[{qty:120,uom:'bao'},{qty:35,uom:'cuộn'}],raw=(row,col)=>row[col.field]
 assert.equal(summableColumn(q,rows,raw,[q,{field:'uom'}]),false,'bao + cuộn is not a total')
 assert.equal(summableColumn(q,rows.map(r=>({...r,uom:'bao'})),raw,[q,{field:'uom'}]),true)
})

test('status, progress, ribbon, person and change cells draw kit markup; their text is plain',()=>{
 const s=statusCol('status','Trạng thái',{labelOf:v=>v==='Pending'?'Chờ xử lý':v})
 assert.equal(fmt(s,'Pending'),'Chờ xử lý')
 const chip=cell(s,'Overdue')
 assert.ok(chip.classList.contains('lotus-chip--danger'));assert.ok(chip.querySelector('svg.lotus-icon path'));assert.equal(chip.textContent,'Quá hạn')
 assert.equal(cell(s,''),'')
 const p=progressCol('received','Đã nhận',{maxField:'qty'})
 assert.equal(fmt(p,30,{qty:120}),'25%');assert.equal(fmt(p,30,{qty:0}),'')
 const bar=cell(p,30,{qty:120});assert.equal(bar.getAttribute('role'),'progressbar');assert.equal(bar.querySelector('.lotus-progress__bar').style.width,'25%')
 const r=ribbonCol('ribbon','Màu dây',{weekField:'week'})
 assert.equal(fmt(r,'XANH_LA_DO',{week:37}),'Xanh lá – Đỏ');assert.match(cell(r,'XANH_LA_DO',{week:37}).textContent,/Xanh lá – ĐỏT37/)
 const who=personCol('owner','Người lập',{teamField:'team'})
 const person=cell(who,'Nguyễn Văn An',{team:'Kho tổng'});assert.equal(person.querySelector('.lotus-avatar').textContent,'VA');assert.match(person.textContent,/Kho tổng/)
 const d=deltaCol('delta','Lệch',{unit:'buồng',goodWhen:'up'})
 assert.equal(fmt(d,-31),'−31 buồng');assert.ok(cell(d,-31).classList.contains('lotus-stat__delta--bad'));assert.ok(cell(d,12).classList.contains('lotus-stat__delta--good'))
})

test('a due date shows its state only when due or late',()=>{
 const due=dueCol('due','Hạn giao',{today:'2026-11-10'})
 assert.equal(fmt(due,'2026-11-04'),'04/11/2026')
 assert.match(cell(due,'2026-11-04').textContent,/04\/11\/2026Quá 6 ngày/)
 assert.equal(cell(due,'2026-11-30').querySelector('.lotus-chip'),null)
})

test('builders only produce AG Grid keys or the app flags DataTable strips',()=>{
 const cols=[numberCol('a','A'),moneyCol('b','B'),qtyCol('c','C',{unitField:'u'}),percentCol('d','D'),dateCol('e','E'),dueCol('f','F',{today:'2026-11-10'}),statusCol('g','G'),progressCol('h','H'),ribbonCol('i','I'),personCol('j','J'),deltaCol('k','K')]
 for(const col of cols)for(const key of Object.keys(col))assert.ok(AG_KEYS.has(key)||GRID_APP_KEYS.includes(key),col.field+': '+key)
 assert.ok(chipNode({tone:'info',label:'X',icon:''}).classList.contains('lotus-chip--bare'))
 assert.ok(window)
})
