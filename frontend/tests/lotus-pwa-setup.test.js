import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const root=new URL('../',import.meta.url)
const read=path=>readFileSync(new URL(path,root),'utf8')
test('Mobile header shows the complete brand without cropping and aligns to the left',()=>{
 const header=read('src/components/LotusMobileHeader.vue')
 const style=read('src/mobile-ui.css')
 assert.match(header,/#left/)
 assert.match(header,/lotus-agritech-header-v2\.png/)
 assert.match(style,/\.lotus-pwa-header \.van-nav-bar__left/)
 assert.match(style,/\.lotus-pwa-logo\{display:block;max-width:100%;max-height:100%;width:100%;height:100%;object-fit:contain/)
 assert.doesNotMatch(style,/left:-10px;top:-9px/)
})
test('All three applications share the first-time installation and notification guide',()=>{
 const shell=read('src/components/LotusMobileShell.vue')
 const onboarding=read('src/components/LotusMobileOnboarding.vue')
 const push=read('src/mobile-push-subscription.js')
 assert.match(shell,/LotusMobileOnboarding/)
 assert.match(onboarding,/beforeinstallprompt/)
 assert.match(onboarding,/appinstalled/)
 assert.match(onboarding,/display-mode: standalone/)
 assert.match(onboarding,/localStorage/)
 assert.match(onboarding,/enableMobilePush\(props.app\)/)
 assert.match(onboarding,/Bỏ qua thiết lập/)
 assert.match(onboarding,/Thêm vào Màn hình chính/)
 assert.match(push,/Notification\.requestPermission\(\)/)
 for(const name of ['WarehouseMobile.vue','BuyingMobile.vue','WorkMobile.vue']){
  const app=read('src/'+name)
  assert.match(app,/Cài ứng dụng và thông báo/)
  assert.match(app,/lotus:open-setup/)
  assert.match(app,/Rời đi/)
 }
})
test('Installed garden app is called Công việc ngoài vườn',()=>{
 const manifest=JSON.parse(read('../lotus_farm/public/work.webmanifest'))
 const page=read('../lotus_farm/www/work.html')
 assert.equal(manifest.name,'Công việc ngoài vườn')
 assert.equal(manifest.short_name,'Công việc ngoài vườn')
 assert.match(page,/apple-mobile-web-app-title\" content=\"Công việc ngoài vườn\"/)
})
