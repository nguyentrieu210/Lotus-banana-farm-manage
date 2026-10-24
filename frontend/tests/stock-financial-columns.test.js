import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const source=readFileSync(new URL('../src/StockApp.vue',import.meta.url),'utf8')
function columnsOf(name){
 const start=source.indexOf('const '+name+'=')
 assert.ok(start>=0,'Missing table '+name)
 const end=source.indexOf('\n\n',start)
 return source.slice(start,end)
}

test('warehouse balance does not display stock valuation or total value columns',()=>{
 const columns=columnsOf('stockColumns')
 assert.doesNotMatch(columns,/valuation_rate|stock_value|Giá vốn|Giá trị tồn/)
 assert.match(columns,/actual_qty/)
 assert.match(columns,/available_qty/)
})
test('movement ledger does not display monetary movement value',()=>{
 const columns=columnsOf('movementColumns')
 assert.doesNotMatch(columns,/stock_value_difference|Giá trị biến động/)
 assert.match(columns,/qty_after_transaction/)
})
test('receipt document does not display valuation rate as a grid column',()=>{
 const columns=columnsOf('receiptDetailColumns')
 assert.doesNotMatch(columns,/valuation_rate|Giá vốn/)
 // Keep the operational receipt costs and rate inputs: hiding a grid
 // column must not alter calculations or the persisted accounting values.
 assert.match(columns,/field:'rate'/)
 assert.match(source,/<StockDocumentForm/)
 const form=readFileSync(new URL('../src/components/StockDocumentForm.vue',import.meta.url),'utf8')
 assert.match(form,/:model-value="row\.rate"/)
})
