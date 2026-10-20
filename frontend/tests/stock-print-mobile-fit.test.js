import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const root=new URL('../', import.meta.url)
const read=path=>readFileSync(new URL(path,root),'utf8')

test('Lotus Print previews fit the phone viewport without changing A4 paper layout',()=>{
 const doc=read('../lotus_farm/templates/print/document.html')
 const css=read('../lotus_farm/templates/print/lotus_print.css')
 assert.equal(read('../lotus_farm/www/lotus_stock_print.html').trim(),'{{ html }}','stock print renders the shared shell')
 assert.match(doc,/<meta name="viewport"/)
 assert.match(css,/@page\{size:A4 portrait/)
 assert.match(doc,/matchMedia\('\(max-width:600px\)'\)/)
 assert.match(doc,/window\.innerWidth-12/)
 assert.match(css,/\.lp-sheet\{zoom:var\(--lp-zoom,1\)\}/)
 assert.match(css,/zoom:1!important/)
})
test('Print headings consistently use vườn chuối instead of dự án chuối',()=>{
 const kit=read('../lotus_farm/print_kit.py')
 const settings=read('../lotus_farm/warehouse_planning.py')
 assert.match(kit,/def garden_label\(raw\)/)
 assert.match(kit,/'VƯỜN CHUỐI'/)
 assert.match(kit,/project=garden_label\(/)
 assert.match(settings,/label='Vườn chuối trên phiếu in'/)
})
