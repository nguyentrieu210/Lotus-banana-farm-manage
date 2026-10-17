/* Only /work is controlled by this worker. Warehouse has another worker/cache. */
importScripts('/assets/lotus_farm/lotus-push-worker.js?v=1');
const CACHE='lotus-work-shell-__WORK_VERSION__';
const ASSETS=__WORK_ASSETS__;
const OFFLINE='/assets/lotus_farm/work-offline.html';
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
 event.waitUntil(
  caches.keys()
   .then(keys=>Promise.all(keys.filter(key=>key.startsWith('lotus-work-')&&key!==CACHE).map(key=>caches.delete(key))))
   .then(()=>self.clients.claim())
 );
});
self.addEventListener('fetch',event=>{
 const request=event.request;
 if(request.method!=='GET')return;
 const url=new URL(request.url);
 if(url.origin!==self.location.origin)return;
 if(url.pathname.startsWith('/api/')||url.pathname.startsWith('/private/')||url.pathname.startsWith('/files/')||url.pathname==='/login'||url.pathname==='/logout')return;
 // Never cache an authenticated HTML shell, work result, photo or API response.
 if(request.mode==='navigate' && url.pathname.replace(/\/$/,'')==='/work'){
  event.respondWith(fetch(request,{cache:'no-store'}).catch(async()=>{
   const cache=await caches.open(CACHE);
   return (await cache.match(OFFLINE))||new Response('Mất mạng. Hãy kết nối lại để mở Công việc ngoài Vườn.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});
  }));
  return;
 }
 if(ASSETS.includes(url.pathname)){
  event.respondWith(caches.open(CACHE).then(async cache=>(await cache.match(url.pathname))||fetch(request)));
 }
});
