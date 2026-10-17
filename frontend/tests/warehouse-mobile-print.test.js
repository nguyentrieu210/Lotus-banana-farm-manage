import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const root=new URL('../',import.meta.url)
const read=path=>readFileSync(new URL(path,root),'utf8')

test('Kho phone offers print for ALL posted stock vouchers in history, including receiving',()=>{
 const ui=read('src/WarehouseMobile.vue')
 assert.match(ui,/const stockPrintURL=\(doctype,name\)=>'\/lotus\/in-phieu\?'\+new URLSearchParams\(\{doctype,name\}\)/)
 assert.match(ui,/\['Stock Entry','Stock Reconciliation','Purchase Receipt'\]\.includes\(historyDetail\.doctype\)&&historyDetail\.docstatus===1/)
 assert.match(ui,/stockPrintURL\(historyDetail\.doctype,historyDetail\.name\)/)
 assert.match(ui,/In phiếu \/ Lưu PDF/)
 assert.match(ui,/target="_blank" rel="noopener noreferrer"/)
})
test('Kho shows print after regular stock posting and after purchase-order receiving',()=>{
 const ui=read('src/WarehouseMobile.vue')
 assert.match(ui,/lastPostedDocument\.value=\{doctype:d\.doctype,name:d\.name\}/)
 assert.match(ui,/lastPostedDocument\.value=\{doctype:'Purchase Receipt',name:postedReceipt\.value\.name\}/)
 assert.match(ui,/v-if="lastPostedDocument"/)
 assert.match(ui,/stockPrintURL\(lastPostedDocument\.doctype,lastPostedDocument\.name\)/)
 assert.match(ui,/function startRequest\(\)\{\s+lastPostedDocument\.value=null/)
})
test('Mobile stock print is a permission-protected A4 template that can download PDF',()=>{
 const roles=read('../lotus_farm/warehouse_access.py')
 const printPage=read('../lotus_farm/www/lotus_stock_print.html')
 const handler=read('../lotus_farm/www/lotus_stock_print.py')
 assert.match(roles,/'Stock Entry':\('read','create','write','submit','print'\)/)
 assert.match(handler,/doc\.check_permission\('print'\)/)
 assert.match(handler,/def download_pdf\(doctype,name\):/)
 assert.match(handler,/lotus-agritech-header-v2\.png/)
 assert.match(printPage,/@page\{size:A4 portrait/)
 assert.match(printPage,/window\.print\(\)/)
 assert.match(printPage,/\{\{\(farm_label or company_label\)\|e\}\}/)
 assert.doesNotMatch(printPage,/Vườn Chuối 222/)
})
