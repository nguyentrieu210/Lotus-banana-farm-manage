importScripts('/assets/lotus_farm/lotus-push-worker.js?v=2');
/* Independent static shell; never cache ERP/user/financial records. */
const CACHE='lotus-field-proposal-__FIELD_PROPOSAL_VERSION__';
const ASSETS=__FIELD_PROPOSAL_ASSETS__;
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
 event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('lotus-field-proposal-')&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
 const req=event.request,url=new URL(req.url);
 if(req.method!=='GET'||url.origin!==self.location.origin)return;
 if(url.pathname.startsWith('/api/')||url.pathname.startsWith('/private/')||url.pathname.startsWith('/files/')||url.pathname==='/login'||url.pathname==='/logout')return;
 if(req.mode==='navigate'&&url.pathname.replace(/\/$/,'')==='/field-proposals'){
  event.respondWith(fetch(req,{cache:'no-store'}).catch(()=>new Response('Mất mạng. Kết nối lại để gửi đề xuất.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}})));
  return;
 }
 if(ASSETS.includes(url.pathname))event.respondWith(caches.open(CACHE).then(async cache=>(await cache.match(url.pathname))||fetch(req)));
});
