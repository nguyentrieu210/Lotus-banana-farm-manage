const FILES=__LOTUS_ASSETS__,CACHE='lotus-vue-shell-'+__LOTUS_VERSION__
const SHELLS={'/lotus/kho':'stock.html','/lotus/cham-cong':'timekeeping.html','/lotus/giao-viec':'assign.html'}
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(FILES))))
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('lotus-vue-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())))
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url)
 if(event.request.method!=='GET'||url.origin!==location.origin)return
 if(event.request.mode==='navigate'&&(url.pathname==='/lotus'||url.pathname.startsWith('/lotus/'))&&!['/lotus/in-phieu','/lotus/in-cong'].includes(url.pathname.replace(/\/$/,''))){
  event.respondWith(fetch(event.request).catch(()=>caches.open(CACHE).then(cache=>cache.match('/assets/lotus_farm/frontend/'+(SHELLS[url.pathname.replace(/\/$/,'')]||'index.html')))))
 }else if(FILES.includes(url.pathname)){
  event.respondWith(caches.open(CACHE).then(async cache=>(await cache.match(url.pathname))||fetch(event.request)))
 }
 // API, login, private photos and ERP documents are always handled by the network.
})
