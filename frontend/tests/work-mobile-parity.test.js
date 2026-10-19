import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const work=readFileSync(new URL('../src/WorkMobile.vue',import.meta.url),'utf8')
const warehouse=readFileSync(new URL('../src/WarehouseMobile.vue',import.meta.url),'utf8')
const shared=readFileSync(new URL('../src/warehouse-mobile.css',import.meta.url),'utf8')
const workCss=readFileSync(new URL('../src/work-mobile.css',import.meta.url),'utf8')
function need(content,phrase){assert.ok(content.includes(phrase),phrase)}
test('work and warehouse use the SAME Vant 4 header, logo and navigation',()=>{
 const shell=readFileSync(new URL('../src/components/LotusMobileShell.vue',import.meta.url),'utf8')
 const mobileCss=readFileSync(new URL('../src/mobile-ui.css',import.meta.url),'utf8')
 for(const app of [work,warehouse]){
  need(app,"import LotusMobileShell")
  need(app,"<LotusMobileShell")
  need(app,":keyboard-open=\"keyboard\"")
 }
 need(shell,"LotusMobileHeader")
 need(shell,"LotusMobileBottomNav")
 const header=readFileSync(new URL('../src/components/LotusMobileHeader.vue',import.meta.url),'utf8')
 const bottom=readFileSync(new URL('../src/components/LotusMobileBottomNav.vue',import.meta.url),'utf8')
 need(header,"lotus-pwa-logo")
 need(header,"NavBar")
 need(bottom,"Tabbar")
 const theme=readFileSync(new URL('../src/mobile-ui-theme.js',import.meta.url),'utf8')
 need(theme,"navBarHeight:'54px'")
 assert.doesNotMatch(work,/class="work-head"/)
})
test('work home uses shared Vant action tiles in two columns',()=>{
 need(work,'class="mobile-actions"')
 assert.match(work,/<LotusMobileAction\b[^>]*\bprimary\b/)
 need(work,'v-if="canAssign"')
 need(work,'@select="openAssign"')
 need(workCss,'grid-template-columns:repeat(2,minmax(0,1fr))')
 assert.doesNotMatch(work,/work-stats|work-brand-icon|work-task-card/)
})
test('all four work tabs use shared icon-only accessible Vant Tabbar',()=>{
 const shell=readFileSync(new URL('../src/components/LotusMobileShell.vue',import.meta.url),'utf8')
 for(const label of ['Trang chủ','Lịch sử','Công việc','Tôi'])need(work,"label:'"+label+"'")
 const bottom=readFileSync(new URL('../src/components/LotusMobileBottomNav.vue',import.meta.url),'utf8')
 need(shell,'LotusMobileBottomNav')
 need(bottom,':aria-label="item.label"')
 need(bottom,'TabbarItem')
 need(bottom,'lotus-sr-only')
 need(work,':disabled="saving"')
 assert.doesNotMatch(work,/<nav class="mobile-bottom"/)
})
test('fields reuse the same searchable Warehouse picker',()=>{
 need(work,'import MobileLinkField')
 need(work,'import MobileLiveSearch')
 need(work,':searchable="true"')
 need(work,'@update:modelValue="editAssign"')
 need(work,'placeholder="Gõ mã Lô…"')
})
test('hardware Back and swipe remain inside the app',()=>{
 need(work,'window.history.back()')
 need(work,"window.addEventListener('popstate',onPopstate)")
 need(work,'createTabSwipe({enabled:')
 need(work,'lotusWorkRoot')
 need(work,"document.dispatchEvent(new Event('warehouse-dismiss-picker'))")
})
test('work forms keep unsaved edits, disable during submission and preserve offline queue',()=>{
 need(work,'class="mobile-form-fields" :disabled="saving"')
 need(work,'class="mobile-leave-dialog"')
 need(work,'function confirmLeave()')
 need(work,'function beforeUnload(e)')
 need(work,'queueCapture(session.value.user,event,photo.value)')
 need(work,'syncCaptures(session.value.user')
 need(work,"target_doctype:'Daily Work Result'")
 need(work,'startDiscard(r)')
 assert.doesNotMatch(work,/const reason=prompt\(/)
})
test('interface retains Work business workflow',()=>{
 for(const label of ['Lập kế hoạch / Giao việc','Báo kết quả','Công việc đã giao','Việc vướng mắc','Kết quả đã ghi','Xem lại kế hoạch','Gửi chờ duyệt giá']){
  need(work,label)
 }
 need(work,'lotus_farm.mobile_assignment.preview')
 need(work,'lotus_farm.mobile_assignment.create')
 need(work,'lotus_farm.rate_approval.decide')
})