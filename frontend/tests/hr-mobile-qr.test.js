import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const src=path=>readFileSync(new URL(path,import.meta.url),'utf8')
test('HR mobile is a separate Vant 4 entry with the shared Lotus shell',()=>{
 const vite=src('../vite.config.js')
 const main=src('../src/hr-mobile-main.js')
 const app=src('../src/HrMobile.vue')
 assert.match(vite,/hr-mobile\.html/)
 assert.match(main,/vant\/lib\/index.css/)
 assert.match(app,/LotusMobileShell/)
 assert.match(app,/CccdQrScanner/)
 assert.match(app,/check_cccd/)
 assert.match(app,/save_employee/)
 assert.match(app,/set_onboarding_ready/)
 assert.match(app,/lotus_onboarding_state/)
})
test('CCCD camera uses a body-level solid overlay and fast scan config',()=>{
 const code=src('../src/components/CccdQrScanner.vue')
 assert.match(code,/<Teleport to="body">/)
 assert.match(code,/background:#fff!important/)
 assert.match(code,/fps:18/)
 assert.match(code,/stopCamera/)
 assert.doesNotMatch(code,/console\.log\(/)
})
test('HR PWA has an isolated service worker and never caches private data',()=>{
 const worker=src('../../lotus_farm/public/hr-mobile-worker.js')
 const manifest=JSON.parse(src('../../lotus_farm/public/hr-mobile.webmanifest'))
 assert.equal(manifest.scope,'/hr-mobile')
 assert.equal(manifest.start_url,'/hr-mobile')
 assert.match(worker,/cache:'no-store'/)
 assert.match(worker,/url\.pathname\.startsWith\('\/api\/'\)/)
 assert.match(worker,/url\.pathname\.startsWith\('\/private\/'\)/)
})
