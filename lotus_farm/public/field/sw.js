const CACHE='lotus-field-shell-2';
const FILES=['./index.html','./app.js','./app.css','./manifest.webmanifest','/assets/lotus_farm/images/lotus-agritech.jpg'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(FILES))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('lotus-field-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 // Authentication, APIs, photos and ERP pages are never cached by this worker.
 if(event.request.method!=='GET'||url.origin!==location.origin||!FILES.some(f=>new URL(f,self.registration.scope).pathname===url.pathname))return;
 event.respondWith(fetch(event.request).then(response=>{if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));}return response;}).catch(()=>caches.match(event.request)));
});
