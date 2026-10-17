import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const root=new URL('../', import.meta.url)
const read=path=>readFileSync(new URL(path,root),'utf8')

test('Stock print preview fits the phone viewport without changing A4 paper layout',()=>{
 const html=read('../lotus_farm/www/lotus_stock_print.html')
 assert.match(html, /<meta name="viewport"/)
 assert.match(html, /@page\{size:A4 portrait/)
 assert.match(html, /@media screen and \(max-width:600px\)/)
 assert.match(html, /zoom:var\(--mobile-sheet-zoom,1\)/)
 assert.match(html, /window\.innerWidth - 16/)
 assert.match(html, /available \/ pageWidth/)
 assert.match(html, /window\.addEventListener\('resize', fitPage\)/)
 assert.match(html, /@media print[\s\S]*?\.sheet\{[^}]*zoom:1!important/)
})
test('Print headings consistently use vườn chuối instead of dự án chuối',()=>{
 const stock=read('../lotus_farm/www/lotus_stock_print.py')
 const staff=read('../lotus_farm/www/lotus_timekeeping_print.py')
 const settings=read('../lotus_farm/warehouse_planning.py')
 assert.match(stock, /context\.project_label=re\.sub/)
 assert.match(stock, /'VƯỜN CHUỐI'/)
 assert.match(staff, /context\.project_label=re\.sub/)
 assert.match(settings, /label='Vườn chuối trên phiếu in'/)
})
