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
test('Mobile stock print is a permission-protected Lotus Print page that can download and share PDF',()=>{
 const roles=read('../lotus_farm/warehouse_access.py')
 const handler=read('../lotus_farm/www/lotus_stock_print.py')
 const kit=read('../lotus_farm/print_kit.py')
 const doc=read('../lotus_farm/templates/print/document.html')
 assert.match(roles,/'Stock Entry':\('read','create','write','submit','print'\)/)
 assert.match(handler,/doc\.check_permission\('print'\)/)
 assert.match(handler,/def download_pdf\(doctype, name\):/)
 assert.match(kit,/lotus-agritech-header-v2\.png/)
 assert.match(doc,/window\.print\(\)/)
 assert.match(doc,/navigator\.canShare&&navigator\.canShare\(\{files:\[file\]\}\)/,'PDF goes to the share sheet (Zalo) on phones')
 assert.match(doc,/Gửi qua Zalo/)
 assert.doesNotMatch(handler,/Vườn Chuối 222/)
})
