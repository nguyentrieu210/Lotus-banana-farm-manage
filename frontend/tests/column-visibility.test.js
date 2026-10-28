import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {columnId,loadHiddenColumns,saveHiddenColumns,normalizeHiddenColumns,changeColumnVisibility,selectableColumns} from '../src/grid-visibility.js'
const columns=[
 {field:'date',headerName:'Ngày'},
 {field:'item',headerName:'Tên vật tư'},
 {field:'quantity',headerName:'Số lượng'},
 {field:'internal',headerName:'Hệ thống',hide:true},
 {field:'picker',headerName:'Chọn',columnChooserLocked:true}
]
test('Each table stores its own selected hidden columns',()=>{
 const original=globalThis.localStorage
 const data=new Map()
 globalThis.localStorage={getItem:key=>data.get(key)||null,setItem:(key,value)=>data.set(key,value)}
 try{
  saveHiddenColumns('lotus-stock-ledger',['quantity'])
  saveHiddenColumns('lotus-farm-land',['item'])
  assert.deepEqual(loadHiddenColumns('lotus-stock-ledger'),['quantity'])
  assert.deepEqual(loadHiddenColumns('lotus-farm-land'),['item'])
 }finally{globalThis.localStorage=original}
})
test('Cannot hide every visible column, and fixed/technical columns are excluded',()=>{
 assert.deepEqual(selectableColumns(columns).map(columnId),['date','item','quantity'])
 const first=changeColumnVisibility(columns,[],'item')
 assert.deepEqual(first,['item'])
 const second=changeColumnVisibility(columns,first,'quantity')
 assert.deepEqual(second,['item','quantity'])
 assert.deepEqual(changeColumnVisibility(columns,second,'date'),second)
 assert.deepEqual(changeColumnVisibility(columns,second,'quantity'),['item'])
 assert.deepEqual(changeColumnVisibility(columns,[],'internal'),[])
 assert.deepEqual(changeColumnVisibility(columns,[],'picker'),[])
 assert.deepEqual(normalizeHiddenColumns(columns,['item','quantity','obsolete','date']),['item','quantity'])
})
test('Shared table synchronizes grid, mobile view and Excel with hidden columns',()=>{
 const source=readFileSync(new URL('../src/components/DataTable.vue',import.meta.url),'utf8')
 assert.match(source, /colId:c.colId\|\|key\(c\),hide:Boolean\(c.hide\|\|selectedHidden.value.includes/)
 assert.match(source, /:hidden="selectedHidden" @toggle="toggleColumn" @reset="resetColumns"/)
 assert.match(source, /const bytes=buildXlsx\(activeColumns.value,records\)/)
 assert.match(source, /const mobileColumns=computed\(\(\)=>props.columns.filter\(c=>!c.hideOnMobile&&!c.hide&&!selectedHidden.value.includes/)
 assert.match(source, /saveHiddenColumns\(widthKey.value,chosen\)/)
})
test('Farm land keeps its column picker in the existing aligned filter actions',()=>{
 const source=readFileSync(new URL('../src/FarmLandApp.vue',import.meta.url),'utf8')
 assert.match(source, /<ColumnVisibilityMenu :columns="gridColumns" :hidden="normalizedLandHidden"/)
 assert.match(source, /:columns-menu="false" :hidden-columns="normalizedLandHidden"/)
 assert.match(source, /const cols=shownLandColumns.value.filter/)
})
