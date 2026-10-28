import test from 'node:test'
import assert from 'node:assert/strict'
import {unzipSync,strFromU8} from 'fflate'
import {buildXlsx} from '../src/excel-export.js'
import {readFileSync} from 'node:fs'

test('XLSX contains Vietnamese headings, unrounded numbers and safe text',()=>{
 const rows=[{item_name:'Ống tưới',item_code:'A01',qty:250.75,content:'Nhập kho – Nhà cung cấp A & B',danger:'=1+1'}]
 const bytes=buildXlsx([
  {field:'item_name',headerName:'Tên hàng'},
  {field:'qty',headerName:'Số lượng',valueFormatter:p=>String(p.value).replace('.',',')},
  {field:'content',headerName:'Nội dung'},
  {field:'danger',headerName:'Chú thích'}
 ],rows)
 const files=unzipSync(bytes)
 assert.ok(files['xl/workbook.xml'])
 const sheet=strFromU8(files['xl/worksheets/sheet1.xml'])
 assert.match(sheet,/Ống tưới/)
 assert.match(sheet,/Nhập kho – Nhà cung cấp A &amp; B/)
 assert.match(sheet,/<c r="B2"><v>250.75<\/v><\/c>/)
 assert.match(sheet,/<t xml:space="preserve">=1\+1<\/t>/)
 assert.doesNotMatch(sheet,/<f>/)
 assert.match(sheet,/autoFilter ref="A1:D2"/)
})
test('Stock Ledger exposes its source voucher content and full-filter export',()=>{
 const columnSource=readFileSync(new URL('../src/stock-columns.js',import.meta.url),'utf8')
 assert.match(columnSource, /field:'content',headerName:'Nội dung'/)
 const ledger=readFileSync(new URL('../src/components/stock/StockLedger.vue',import.meta.url),'utf8')
 const backend=readFileSync(new URL('../../lotus_farm/warehouse.py',import.meta.url),'utf8')
 assert.match(ledger, /:export-rows="exportLedgerRows"/)
 assert.match(ledger, /for\(let offset=0;;offset\+=50\)/)
 assert.match(backend,/row\.content =/)
 assert.match(backend,/frappe\.has_permission\(doctype, 'read'\)/)
})
test('All shared DataTable screens show an export action',()=>{
 const table=readFileSync(new URL('../src/components/DataTable.vue',import.meta.url),'utf8')
 assert.match(table,/Xuất Excel/)
 assert.match(table,/const records=\[\]/)
 assert.match(table,/forEachNodeAfterFilterAndSort/)
})
