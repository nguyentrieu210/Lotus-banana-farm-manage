importScripts('/assets/lotus_farm/lotus-push-worker.js?v=2');
const CACHE='lotus-warehouse-shell-'+__WAREHOUSE_VERSION__;
const ASSETS=__WAREHOUSE_ASSETS__;
const OFFLINE='/assets/lotus_farm/warehouse-offline.html';
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>event.waitUntil(
 caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('lotus-warehouse-shell-')&&key!==CACHE).map(key=>caches.delete(key))))
 .then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 const request=event.request;
 const url=new URL(request.url);
 if(request.method!=='GET'||url.origin!==self.location.origin)return;
 // Sensitive endpoints, login, private files and operational stock pages never go into cache.
 if(url.pathname.startsWith('/api/')||url.pathname.startsWith('/private/')||url.pathname.startsWith('/files/')||url.pathname==='/login')return;
 if(request.mode==='navigate'&&url.pathname.replace(/\/$/,'')==='/warehouse'){
   event.respondWith(fetch(request).catch(async()=>{
      const cache=await caches.open(CACHE);
      return (await cache.match(OFFLINE))||new Response('Không có mạng. Kết nối lại để quản lý kho.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});
   }));
 }else if(ASSETS.includes(url.pathname)){
   event.respondWith(caches.open(CACHE).then(async cache=>(await cache.match(url.pathname))||fetch(request)));
 }
});
