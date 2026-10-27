/* HR PWA worker: cache only build files and a static offline notice. Never private HR data. */
importScripts('/assets/lotus_farm/lotus-push-worker.js?v=2');
const CACHE='lotus-hr-mobile-__HR_VERSION__'
const ASSETS=__HR_ASSETS__
const OFFLINE='/assets/lotus_farm/hr-mobile-offline.html'
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting())))
self.addEventListener('activate',event=>event.waitUntil(
 caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('lotus-hr-mobile-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())
))
self.addEventListener('fetch',event=>{
 const req=event.request,url=new URL(req.url)
 if(req.method!=='GET'||url.origin!==self.location.origin)return
 if(url.pathname.startsWith('/api/')||url.pathname.startsWith('/private/')||url.pathname.startsWith('/files/')||url.pathname==='/login'||url.pathname==='/logout')return
 if(req.mode==='navigate'&&url.pathname.replace(/\/$/,'')==='/hr-mobile'){
  event.respondWith(fetch(req,{cache:'no-store'}).catch(async()=>{
   const cache=await caches.open(CACHE)
   return (await cache.match(OFFLINE))||new Response('Mất mạng. Kết nối lại để sử dụng Nhân sự.',{status:503})
  }))
  return
 }
 if(ASSETS.includes(url.pathname))
  event.respondWith(caches.open(CACHE).then(async cache=>(await cache.match(url.pathname))||fetch(req)))
})
