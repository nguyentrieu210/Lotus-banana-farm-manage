import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {gridRowId} from '../src/grid-row-id.js'

const table=readFileSync(new URL('../src/components/DataTable.vue',import.meta.url),'utf8')
const list=readFileSync(new URL('../src/components/ListPage.vue',import.meta.url),'utf8')
const farm=readFileSync(new URL('../src/FarmLandApp.vue',import.meta.url),'utf8')

test('Every shared table has fixed tick column first and STT second',()=>{
 assert.match(table,/return \[select,sttDef,\.\.\.body\]/)
 assert.match(table,/:column-defs="gridDefs"/)
 assert.match(table,/const selectDef=\{colId:'__lotus_select'/)
 assert.match(table,/const sttDef=\{colId:'__lotus_stt'/)
 assert.match(table,/pinned:'left',lockPinned:true,lockPosition:'left',suppressMovable:true/)
 assert.match(table,/state:\[\{colId:nativeSelectId.value\|\|'__lotus_select',pinned:'left',hide:false,width:42\},\{colId:'__lotus_stt',pinned:'left',width:52\}/)
})
test('Selection is keyed by row identity and does not trigger opening the document',()=>{
 assert.match(table,/const getSelectionId=row=>gridRowId\(row,props.rowKey\)/)
 assert.match(table,/setRowSelected\(row,!selectedIds.value.has\(getSelectionId\(row\)\)\)/)
 assert.match(table,/event.preventDefault\(\);event.stopPropagation\(\)/)
 assert.match(table,/page-selection-change/)
 assert.match(table,/selection-clear/)
 assert.equal(gridRowId({name:'HR-EMP-00014'},'name'),'HR-EMP-00014')
})
test('STT follows grid row order and starts after server pagination offset',()=>{
 assert.match(table,/props.rowIndexOffset\+params.node.rowIndex\+1/)
 assert.match(list,/:row-index-offset="paged\?start:0"/)
 assert.match(table,/props.paginate\?\(api.paginationGetCurrentPage\?\.\(\)\|\|0\)\*props.pageSize:0/)
})
test('Farm lot selection is connected to existing bulk editing, without duplicate tick column',()=>{
 assert.doesNotMatch(farm,/field:'__picked'/)
 assert.match(farm,/:selected-row-keys="\[\.\.\.picked\]"/)
 assert.match(farm,/@row-selection-change="\(\{id,selected\}\)=>setLandSelected\(id,selected\)"/)
 assert.match(farm,/@page-selection-change="\(\{rows,selected\}\)=>setLandPageSelected\(rows,selected\)"/)
 assert.match(farm,/function setLandPageSelected\(rows,selected\)/)
 assert.match(farm,/function togglePickAll\(\)/)
})
test('STT and tick remain display-only, not part of business column chooser or Excel data',()=>{
 assert.match(table,/const activeColumns=computed\(\(\)=>activeDisplayColumns.value.filter/)
 assert.match(table,/const bytes=buildXlsx\(activeColumns.value,records\)/)
 assert.doesNotMatch(table,/props.columns.unshift\(/)
})
