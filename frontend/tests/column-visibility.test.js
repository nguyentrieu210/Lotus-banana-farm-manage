import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {unzipSync,strFromU8} from 'fflate'
import {buildXlsx} from '../src/excel-export.js'
import {columnId,loadHiddenColumns,saveHiddenColumns,loadColumnLayout,saveColumnLayout,normalizeColumnLayout,changeColumnVisibility,selectableColumns,orderedColumns,displayedColumns,moveColumn,pinColumn,setVisibleColumns} from '../src/grid-visibility.js'

const cols=[
 {field:'date',headerName:'Ngày'},
 {field:'item',headerName:'Tên vật tư'},
 {field:'quantity',headerName:'Số lượng'},
 {field:'notes',headerName:'Nội dung'},
 {field:'internal',headerName:'Cột hệ thống',hide:true},
 {field:'pick',headerName:'Chọn',columnChooserLocked:true,suppressExport:true}
]

test('Old browser hidden-column preferences are migrated and isolated per table',()=>{
 const old=globalThis.localStorage
 const data=new Map()
 globalThis.localStorage={getItem:key=>data.get(key)||null,setItem:(key,v)=>data.set(key,v)}
 try{
  saveHiddenColumns('warehouse',['quantity'])
  const original=loadColumnLayout('warehouse',cols)
  assert.deepEqual(original.hidden,['quantity'])
  const changed=saveColumnLayout('warehouse',cols,{...original,order:['notes','date','item','quantity'],pinned:['notes']})
  assert.deepEqual(loadColumnLayout('warehouse',cols),changed)
  assert.deepEqual(loadColumnLayout('farms',cols).hidden,[])
  assert.deepEqual(loadHiddenColumns('warehouse'),['quantity'])
 }finally{globalThis.localStorage=old}
})
test('No hidden all, no technical columns, stale state is discarded, pinned limited to 2',()=>{
 assert.deepEqual(selectableColumns(cols).map(columnId),['date','item','quantity','notes'])
 assert.deepEqual(changeColumnVisibility(cols,[],'internal'),[])
 assert.deepEqual(changeColumnVisibility(cols,[],'pick'),[])
 assert.deepEqual(normalizeColumnLayout(cols,{hidden:['date','item','quantity','notes','deleted'],pinned:['item','notes','quantity'],order:['notes','deleted','date','date']}),
 {hidden:['item','quantity','notes'],order:['notes','date','item','quantity'],pinned:[]})
 const layout=normalizeColumnLayout(cols,{pinned:['item','date','notes']})
 assert.deepEqual(layout.pinned,['item','date'])
})
test('Moving and pinning alter display order without mutating source columns',()=>{
 const initial=normalizeColumnLayout(cols,{})
 const reordered=moveColumn(cols,initial,'notes',-1)
 assert.deepEqual(reordered.order,['date','item','notes','quantity'])
 assert.deepEqual(orderedColumns(cols,reordered).map(columnId),['date','item','notes','quantity','internal','pick'])
 assert.deepEqual(pinColumn(cols,reordered,'notes').pinned,['notes'])
 assert.deepEqual(displayedColumns(cols,pinColumn(cols,reordered,'notes')).map(columnId),['notes','date','item','quantity','pick'])
 assert.deepEqual(pinColumn(cols,pinColumn(cols,reordered,'notes'),'notes').pinned,[])
 const compact=setVisibleColumns(cols,initial,['date','quantity'])
 assert.deepEqual(compact.hidden,['item','notes'])
 assert.deepEqual(cols.map(columnId),['date','item','quantity','notes','internal','pick'])
})
test('Excel follows visible columns and custom order, without action columns',()=>{
 const layout=normalizeColumnLayout(cols,{order:['notes','item','date','quantity'],hidden:['item']})
 const exportCols=orderedColumns(cols,layout).filter(c=>!c.hide&&!c.suppressExport&&!c.columnChooserLocked&&!layout.hidden.includes(columnId(c)))
 const xml=strFromU8(unzipSync(buildXlsx(exportCols,[{date:'2026-10-28',item:'NPK',quantity:12,notes:'Xuất chăm sóc'}]))['xl/worksheets/sheet1.xml'])
 assert.ok(xml.indexOf('Nội dung')<xml.indexOf('Ngày'))
 assert.ok(xml.indexOf('Ngày')<xml.indexOf('Số lượng'))
 assert.ok(!xml.includes('Tên vật tư'))
 assert.ok(!xml.includes('Chọn'))
})
test('Column picker uses single-line buttons, search, show all, pin and move',()=>{
 const menu=readFileSync(new URL('../src/components/ColumnVisibilityMenu.vue',import.meta.url),'utf8')
 const table=readFileSync(new URL('../src/components/DataTable.vue',import.meta.url),'utf8')
 const farm=readFileSync(new URL('../src/FarmLandApp.vue',import.meta.url),'utf8')
 const ledger=readFileSync(new URL('../src/components/stock/StockLedger.vue',import.meta.url),'utf8')
 assert.match(menu,/v-model="query" type="search"/)
 assert.match(menu,/lotus-column-picker__toggle/)
 assert.doesNotMatch(menu,/type="checkbox"/)
 assert.match(menu,/grid-template-columns:minmax\(0,1fr\) 28px 28px 28px/)
 assert.match(menu,/@click="emit\('pin',columnId\(col\)\)"/)
 assert.match(menu,/@click="emit\('move',columnId\(col\),-1\)"/)
 assert.match(table,/applyColumnState\(\{state:cols.map/)
 assert.match(table,/applyOrder:true/)
 assert.match(table,/const bytes=buildXlsx\(activeColumns.value,records\)/)
 assert.match(farm,/:column-layout="normalizedLandLayout"/)
 assert.match(ledger,/:column-presets="columnPresets"/)
})
