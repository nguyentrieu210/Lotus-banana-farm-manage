import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const get=(p)=>readFileSync(new URL('../'+p,import.meta.url),'utf-8')

test('one Vant push inbox shared by warehouse, buying, and work headers',()=>{
 const shell=get('src/components/LotusMobileShell.vue')
 assert.match(shell,/LotusMobileNotifications/)
 assert.match(shell,/:app="app"/)
 for(const [file,app] of [['WarehouseMobile.vue','warehouse'],['BuyingMobile.vue','buying'],['WorkMobile.vue','work']]){
  assert.match(get('src/'+file),new RegExp('LotusMobileShell app="'+app+'"'))
 }
})

test('three separate push service-worker scopes each import the same listener',()=>{
 for(const file of ['warehouse-worker.js','buying-worker.js','work-worker.js']){
  assert.match(get('../lotus_farm/public/'+file),/importScripts\('\/assets\/lotus_farm\/lotus-push-worker\.js/)
 }
 const worker=get('../lotus_farm/public/lotus-push-worker.js')
 assert.match(worker,/addEventListener\('push'/)
 assert.match(worker,/addEventListener\('notificationclick'/)
 assert.match(worker,/url\.origin!==self\.location\.origin/)
 assert.match(worker,/clients\.openWindow/)
})

test('users must explicitly enable push and logout revokes the local device',()=>{
 const c=get('src/components/LotusMobileNotifications.vue')
 assert.match(c,/Notification\.requestPermission\(\)/)
 assert.match(c,/pushManager\.subscribe/)
 assert.match(c,/applicationServerKey/)
 assert.match(c,/api\('subscribe'/)
 assert.match(c,/api\('unsubscribe'/)
 // Every PWA signs out through the shared helper, which revokes this device's push endpoint first.
 const session=get('src/mobile-push-session.js')
 assert.match(session,/export async function logoutPwa\(app,\{csrf='',home\}\)\{\s*await revokeDevicePush\(app\)/)
 assert.match(session,/'\/api\/method\/logout',\{method:'POST'/)
 for(const [file,app] of [['WarehouseMobile.vue','warehouse'],['BuyingMobile.vue','buying'],['WorkMobile.vue','work'],['HrMobile.vue','hr']]){
  assert.match(get('src/'+file),new RegExp(`logoutPwa\\('${app}'`))
  assert.doesNotMatch(get('src/'+file),/href="\/logout"/)
 }
})

test('backend requires login and isolates alerts by user and app',()=>{
 const b=get('../lotus_farm/push_notifications.py')
 assert.match(b,/if not user or user == "Guest"/)
 assert.match(b,/filters=\{"user": user, "app": app\}/)
 assert.match(b,/ALLOWED_PUSH_HOSTS/)
 assert.match(b,/enqueue_after_commit=True/)
})
