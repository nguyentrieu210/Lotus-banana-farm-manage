import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync,readdirSync} from 'node:fs'

// Screens rebuilt on the shared form standard. Add a file here once it is converted; it must then stay on the standard.
const src=new URL('../src/',import.meta.url)
const dir=name=>readdirSync(new URL(name,src)).filter(f=>f.endsWith('.vue')).map(f=>name+f)
const standard=['StockApp.vue','components/ListPage.vue','components/ProcurementField.vue','components/StockReceiptReason.vue','components/WarehousePlanning.vue','components/PurchaseReceiptCosts.vue',...dir('components/form/'),...dir('components/stock/')]
const read=name=>readFileSync(new URL(name,src),'utf8')
const template=text=>text.slice(text.indexOf('<template'))

test('standard screens build fields with LotusField, not hand-made label + control markup',()=>{
 for(const name of standard){
  const markup=template(read(name))
  assert.doesNotMatch(markup,/<label[^>]*>[^<{]+<(Ui|Date|Link|Month|Combobox|Select|Input|Textarea)/,name+': use <LotusField label="…">')
  assert.doesNotMatch(markup,/<(input|select|textarea)[\s>]/,name+': native controls live only in components/ui')
  assert.doesNotMatch(markup,/<(UiInput|Input)[^>]*type="(date|month)"/,name+': dates use DatePicker / MonthPicker')
 }
})

test('standard screens use the shared dialog, confirm and reason prompts',()=>{
 for(const name of standard){
  const text=read(name)
  assert.doesNotMatch(text,/window\.(prompt|confirm|alert)\(/,name+': use WorkspaceConfirm / ReasonDialog')
  assert.doesNotMatch(text,/<WorkspaceModal[^>]*\bbare\b/,name+': data entry uses ModalForm')
  if(/<form[\s>]/.test(template(text)))assert.equal(name,'components/form/ModalForm.vue',name+': forms are ModalForm')
 }
})

test('Kho views are list pages driven by the sidebar, with one view per menu entry',()=>{
 const nav=read('stock-navigation.js'),shell=read('StockApp.vue')
 for(const id of ['stock','receipts','issues','transfers','counts','movements','planning','report','warehouses','items','groups','uoms'])assert.match(nav,new RegExp("id:'"+id+"'"),id)
 for(const view of ['StockInventory','StockDocumentList','StockLedger','StockReport','WarehousePlanning','StockMasterList'])assert.match(shell,new RegExp('<'+view+' '),view)
 assert.match(shell,/<WorkspaceTabs v-if="!embedded&&!warehousePwa"/,'embedded Kho has no in-page tabs: the sidebar navigates')
 assert.match(read('module-navigation.js'),/stock:\{paths:\['kho'\]/)
})
