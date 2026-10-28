import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const land=readFileSync(new URL('../src/FarmLandApp.vue',import.meta.url),'utf8')
const css=readFileSync(new URL('../src/land.css',import.meta.url),'utf8')
const table=readFileSync(new URL('../src/components/DataTable.vue',import.meta.url),'utf8')
const columns=readFileSync(new URL('../src/stock-columns.js',import.meta.url),'utf8')
const backend=readFileSync(new URL('../../lotus_farm/warehouse.py',import.meta.url),'utf8')

test('Sổ kho shows original movement, running balance and document context',()=>{
 const source=columns.slice(columns.indexOf('export function movementColumns'),columns.indexOf('// Nhập – xuất – tồn'))
 for(const field of ['posting_date','voucher_no','transaction_type','content','item_name','item_code','warehouse','stock_uom','opening_qty','in_qty','out_qty','qty_after_transaction','receiver','usage_area','work_team']){
  assert.ok(source.includes("field:'"+field+"'")||['opening_qty','in_qty','out_qty','qty_after_transaction'].some(name=>name===field&&source.includes("number('"+field+"'")),'missing column '+field)
 }
 assert.match(backend,/voucher_detail_no/)
 assert.match(backend,/frappe\.get_all\('Stock Entry Detail'/)
 assert.match(backend,/frappe\.has_permission\('Daily Work Plan', 'read'\)/)
 assert.match(backend,/if len\(teams\) == 1 else ''/)
 assert.match(backend,/row\.receiver =/)
 assert.match(backend,/row\.usage_area =/)
})

test('Farm list has one aligned Excel button with selection count, not another row',()=>{
 assert.match(land,/<div class="land-filter-actions">/)
 assert.match(land,/Xuất bảng Excel/)
 assert.match(land,/:exportable="false" :columns-menu="false" :hidden-columns="normalizedLandHidden" row-key="name"/)
 assert.match(land,/Xuất mẫu Excel/)
 assert.match(css,/\.land-filter-actions\{display:flex;flex-wrap:wrap;align-items:center/)
 assert.match(table,/v-if="columnsMenu\|\|exportable" class="lotus-data-table__export"/)
})
