// Mua hàng Lotus offline shell: never store ERP records, credentials or user HTML.
importScripts('/assets/lotus_farm/lotus-push-worker.js?v=2');
const CACHE='lotus-buying-shell-'+__BUYING_VERSION__
const ASSETS=__BUYING_ASSETS__
const OFFLINE='/assets/lotus_farm/buying-offline.html'

self.addEventListener('install', event=>{
 event.waitUntil(
  caches.open(CACHE).then(async cache=>{
   // A temporary static-file failure must not prevent the PWA from installing.
   await cache.add(OFFLINE).catch(()=>{})
   await Promise.allSettled(ASSETS.filter(url=>url!==OFFLINE).map(url=>cache.add(url)))
  }).then(()=>self.skipWaiting())
 )
})
self.addEventListener('activate', event=>{
 event.waitUntil(caches.keys()
  .then(keys=>Promise.all(keys.filter(key=>key.startsWith('lotus-buying-shell-')&&key!==CACHE).map(key=>caches.delete(key))))
  .then(()=>self.clients.claim())
 )
})
self.addEventListener('fetch', event=>{
 const request=event.request
 if(request.method!=='GET')return
 const url=new URL(request.url)
 if(url.origin!==self.location.origin)return
 if(url.pathname.startsWith('/api/')||url.pathname.startsWith('/private/')||
    url.pathname.startsWith('/files/')||url.pathname==='/login'||url.pathname==='/logout')return

 if(request.mode==='navigate' && url.pathname.replace(/\/$/,'')==='/buying'){
  event.respondWith(fetch(request,{cache:'no-store'}).catch(async()=>{
   return (await (await caches.open(CACHE)).match(OFFLINE))||
    new Response('Mất kết nối. Kết nối mạng để mở Mua hàng Lotus.',{
     status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}})
  }))
  return
 }
 if(ASSETS.includes(url.pathname)){
  event.respondWith(caches.open(CACHE).then(async cache=>(await cache.match(url.pathname))||fetch(request)))
 }
})
