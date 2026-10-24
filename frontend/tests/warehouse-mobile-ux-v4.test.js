import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {foldVietnamese,validateReceiptInputs} from '../src/warehouse-mobile-helpers.js'

const app=readFileSync(new URL('../src/WarehouseMobile.vue',import.meta.url),'utf8')
const link=readFileSync(new URL('../src/components/MobileLinkField.vue',import.meta.url),'utf8')
const css=readFileSync(new URL('../src/warehouse-mobile.css',import.meta.url),'utf8')

test('search for warehouse, suppliers and items ignores Vietnamese accents',()=>{
 assert.equal(foldVietnamese('Đơn hàng CHỜ NHẬN'),'don hang cho nhan')
 assert.ok(foldVietnamese('Bao buồng chuối').includes('buong'))
})
test('receiving converts quantities exactly once, including a partial delivery',()=>{
 const rows=[{line:'PO1',remaining_qty:12,conversion_factor:24},{line:'PO2',remaining_qty:4,conversion_factor:1}]
 assert.deepEqual(validateReceiptInputs(rows,{PO1:'5',PO2:'0'}),{valid:true,reason:'',quantities:{PO1:120}})
 assert.equal(validateReceiptInputs(rows,{PO1:'12.1'}).valid,false)
 assert.equal(validateReceiptInputs(rows,{PO1:'-1'}).valid,false)
 assert.equal(validateReceiptInputs(rows,{PO1:'Infinity'}).valid,false)
 assert.deepEqual(validateReceiptInputs(rows,{}).quantities,{})
})
test('history includes purchase orders and shortcut to receiving',()=>{
 assert.match(app,/historyMode=ref\('stock'\)/)
 assert.match(app,/historyMode\.value==='orders'/)
 assert.match(app,/buyingAPI\('order_detail'/)
 assert.match(app,/Nhận hàng theo đơn/)
 assert.match(app,/historyWarehouse/)
 assert.match(app,/inventoryWarehouse/)
})
test('stale list results cannot replace fresh list results',()=>{
 for(const flag of ['historyRequest','inventoryRequest'])assert.ok(app.includes('request!=='+flag),flag)
})
test('purchase order is saved once if quote upload fails and quote can retry separately',()=>{
 const shared=readFileSync(new URL('../src/mobile-purchase.js',import.meta.url),'utf8')
 assert.match(shared,/quote\?\.size>MAX_QUOTE_BYTES/)
 assert.match(app,/order\.value\.name=result\.name/)
 assert.match(app,/failedQuote\.value=!!result.quoteError/)
 assert.match(app,/function retryQuote/)
 assert.match(app,/order\.value\.name\|\|savedPurchase\.value\)return/)
})
test('link dropdown supports keyboard, pop-up above screen bottom and larger tap targets',()=>{
 assert.match(link,/ArrowDown/)
 assert.match(link,/aria-activedescendant/)
 assert.match(link,/mobile-link-up/)
 assert.match(link,/if\(props\.disabled\|\|open\.value\)return/)
 assert.match(css,/\.mobile-link-options\.mobile-link-up/)
 // Back now lives in the shared PWA header with a 44px tap target.
 assert.match(readFileSync(new URL('../src/mobile-ui.css',import.meta.url),'utf8'),/\.lotus-pwa-back\{width:44px;min-width:44px/)
})
test('quick search opens suggestions immediately and never needs Enter or a Tìm button',()=>{
 const picker=readFileSync(new URL('../src/components/MobileLiveSearch.vue',import.meta.url),'utf8')
 assert.match(picker,/@focus="open"/)
 assert.match(picker,/@input="typed"/)
 assert.match(picker, /emit\('update:modelValue',event.target.value\)/)
 assert.match(picker, /role="listbox"/)
 assert.match(picker, /emit\('select',row\)/)
 for(const query of ['historySearch','inventorySearch'])assert.match(app,new RegExp('v-model="'+query+'"'))
 assert.doesNotMatch(app,/<button type="submit">Tìm<\/button>/)
})
test('header and icon-only bottom navigation reuse shared Vant components',()=>{
 const shell=readFileSync(new URL('../src/components/LotusMobileShell.vue',import.meta.url),'utf8')
 assert.match(app,/<LotusMobileShell/)
 assert.match(app,/:keyboard-open="keyboard"/)
 const header=readFileSync(new URL('../src/components/LotusMobileHeader.vue',import.meta.url),'utf8')
 const bottom=readFileSync(new URL('../src/components/LotusMobileBottomNav.vue',import.meta.url),'utf8')
 assert.match(shell,/LotusMobileHeader/)
 assert.match(shell,/LotusMobileBottomNav/)
 assert.match(header,/NavBar/)
 assert.match(bottom,/TabbarItem/)
 assert.match(bottom,/:aria-label="item.label"/)
 assert.match(bottom,/lotus-sr-only/)
 for(const label of ['Trang chủ','Lịch sử','Xuất nhập tồn','Tôi'])assert.ok(app.includes("label:'"+label+"'"))
 assert.doesNotMatch(app,/<nav class="mobile-bottom"/)
})
