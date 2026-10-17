import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const read=file=>readFileSync(new URL(file,import.meta.url),'utf8')
const shell=read('../src/components/LotusMobileShell.vue')
const tile=read('../src/components/LotusMobileAction.vue')
const style=read('../src/mobile-ui.css')
for(const [name,filename,entry] of [
 ['Kho','WarehouseMobile.vue','warehouse-mobile-main.js'],
 ['Mua hàng','BuyingMobile.vue','buying-mobile-main.js'],
 ['Công việc ngoài Vườn','WorkMobile.vue','work-mobile-main.js']
]){
 test(name+' reuses Vant 4 shared shell and tokens',()=>{
  const app=read('../src/'+filename),main=read('../src/'+entry)
  assert.match(app,/import LotusMobileShell/)
  assert.match(app,/<LotusMobileShell/)
  assert.match(app,/:tabs="mobileTabs"/)
  assert.match(app,/@navigate=/)
  assert.match(main,/vant\/lib\/index.css/)
  assert.match(main,/mobile-ui.css/)
 })
}
test('shared shell uses compact logo, keyboard-aware icon-only bottom and screen back',()=>{
 const header=read('../src/components/LotusMobileHeader.vue')
 const bottom=read('../src/components/LotusMobileBottomNav.vue')
 assert.match(shell,/ConfigProvider/)
 assert.match(shell,/LotusMobileHeader/)
 assert.match(shell,/LotusMobileBottomNav/)
 assert.match(header,/NavBar/)
 assert.match(header,/class="lotus-pwa-logo"/)
 assert.match(header,/@click="emit\('back'\)"/)
 assert.match(bottom,/TabbarItem/)
 assert.match(bottom,/v-if="!hidden"/)
 assert.match(bottom,/safe-area-inset-bottom/)
 assert.match(bottom,/:aria-label="item.label"/)
 assert.match(bottom,/class="lotus-sr-only"/)
 const theme=read('../src/mobile-ui-theme.js')
 assert.match(theme,/navBarHeight:'54px'/)
 assert.match(theme,/tabbarHeight:'60px'/)
})
test('shared home action uses Vant Cell and keeps permissions',()=>{
 assert.match(tile,/import \{Button,Icon\} from 'vant'/)
 assert.match(tile,/class="lotus-pwa-action-icon"/)
 assert.match(tile,/:disabled="disabled"/)
 assert.match(tile,/@click="choose"/)
 const warehouse=read('../src/WarehouseMobile.vue')
 assert.match(warehouse,/v-if="setup\?\.can_request"/)
 assert.match(warehouse,/@select="startRequest"/)
 assert.ok(warehouse.indexOf('title="Tạo đơn mua"')<warehouse.indexOf('title="Nhập theo đơn"'))
})

