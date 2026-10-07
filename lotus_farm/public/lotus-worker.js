const FILES=__LOTUS_ASSETS__,CACHE='lotus-vue-shell-'+__LOTUS_VERSION__,SHELL='/assets/lotus_farm/frontend/index.html'
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(FILES))))
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('lotus-vue-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())))
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url)
 if(event.request.method!=='GET'||url.origin!==location.origin)return
 if(event.request.mode==='navigate'&&(url.pathname==='/lotus'||url.pathname.startsWith('/lotus/'))){
  event.respondWith(fetch(event.request).catch(()=>caches.open(CACHE).then(cache=>cache.match(SHELL))))
 }else if(FILES.includes(url.pathname)){
  event.respondWith(caches.open(CACHE).then(async cache=>(await cache.match(url.pathname))||fetch(event.request)))
 }
 // API, login, private photos and ERP documents are always handled by the network.
})
