import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const read=path=>readFileSync(new URL(path,import.meta.url),'utf8')
const apps=[
 {id:'warehouse',root:'WarehouseMobile.vue',entry:'warehouse-mobile-main.js'},
 {id:'buying',root:'BuyingMobile.vue',entry:'buying-mobile-main.js'},
 {id:'work',root:'WorkMobile.vue',entry:'work-mobile-main.js'}
]
test('all three PWAs delegate installation to one explicit onboarding component',()=>{
 const shell=read('../src/components/LotusMobileShell.vue')
 const guide=read('../src/components/LotusMobileOnboarding.vue')
 assert.match(shell,/LotusMobileOnboarding/)
 assert.match(guide,/beforeinstallprompt/)
 assert.match(guide,/appinstalled/)
 assert.match(guide,/enableMobilePush\(props.app\)/)
 for(const app of apps){
  const source=read('../src/'+app.root)
  assert.match(source,/function openSetup\(\)/,app.id)
  assert.match(source,/lotus:open-setup/,app.id)
  assert.doesNotMatch(source,/beforeinstallprompt|installPrompt|showInstallHelp|installHelp/,app.id)
  assert.match(source,/<LotusMobileShell/,app.id)
 }
})
test('mobile input and select expose shared accessible hint and server error states',()=>{
 for(const name of ['LotusMobileInput.vue','LotusMobileSelect.vue']){
  const source=read('../src/components/'+name)
  assert.match(source,/hint:String,error:String/)
  assert.match(source,/:aria-invalid="!!error"/)
  assert.match(source,/:error-message="error\|\|undefined"/)
  assert.match(source,/lotus-pwa-field-hint/)
 }
 const style=read('../src/mobile-ui.css')
 assert.match(style,/\.lotus-pwa-field-hint/)
 assert.match(style,/:focus-visible/)
})
test('header and touch controls remain usable at 320 px and avoid clipping brand art',()=>{
 const css=read('../src/mobile-ui.css')
 assert.match(css,/@media\(max-width:360px\)/)
 assert.match(css,/\.lotus-pwa-logo\{[^}]*object-fit:contain/)
 assert.match(css,/\.lotus-pwa-logo-frame\{width:94px;flex-basis:94px;height:36px\}/)
 assert.match(css,/\.lotus-pwa-back\{width:44px;min-width:44px/)
 assert.match(css,/--lotus-pwa-touch:var\(--lotus-touch\)/)
 assert.match(read('../src/lotus-tokens.css'),/--lotus-touch:44px/)
})
test('Work PWA consumes a legacy mobile compatibility layer, not Warehouse page stylesheet',()=>{
 const work=read('../src/work-mobile-main.js')
 const styles=read('../src/mobile-work-legacy.css')
 assert.match(work,/mobile-work-legacy\.css/)
 assert.doesNotMatch(work,/warehouse-mobile\.css/)
 for(const rule of ['.mobile-container','.mobile-field','.mobile-inline','.mobile-list-card','.mobile-line']){
  assert.ok(styles.includes(rule),'missing shared primitive: '+rule)
 }
 assert.match(work,/mobile-ui\.css/)
})
test('three independently installable PWAs declare unique IDs and safe maskable icons',()=>{
 const ids=new Set()
 for(const app of apps){
  const manifest=JSON.parse(read('../../lotus_farm/public/'+app.id+'.webmanifest'))
  assert.equal(manifest.id,'/'+app.id)
  ids.add(manifest.id)
  assert.equal(manifest.scope,'/'+app.id)
  assert.ok(manifest.icons.some(x=>x.sizes==='192x192'))
  const icon=manifest.icons.find(x=>x.purpose==='maskable'&&x.sizes==='512x512')
  assert.ok(icon,'missing maskable icon: '+app.id)
  const filename=icon.src.split('/').pop()
  const img=readFileSync(new URL('../../lotus_farm/public/images/'+filename,import.meta.url))
  assert.equal(img.toString('hex',0,8),'89504e470d0a1a0a')
  assert.equal(img.readUInt32BE(16),512)
  assert.equal(img.readUInt32BE(20),512)
 }
 assert.equal(ids.size,3)
})
test('Buying keeps its scoped login shell when PWA session expires',()=>{
 const py=read('../../lotus_farm/www/buying.py')
 const html=read('../../lotus_farm/www/buying.html')
 assert.match(py,/if context\.guest/)
 assert.match(html,/redirect-to=%2Fbuying/)
 assert.match(html,/Cần đăng nhập/)
})
