/* Same-origin worker shared by the three separately installed Lotus PWA scopes. */
self.addEventListener('push',event=>{
 let payload={};
 try {payload=event.data?.json()||{}}catch{return}
 const raw=String(payload.url||'');
 let url;
 try {url=new URL(raw,self.location.origin)}catch{return}
 if(url.origin!==self.location.origin ||
    !['/warehouse','/buying','/work','/hr-mobile'].some(prefix=>url.pathname===prefix))return;
 event.waitUntil(self.registration.showNotification(String(payload.title||'Lotus').slice(0,130),{
  body:String(payload.body||'').slice(0,500),tag:String(payload.tag||'lotus'),
  icon:'/assets/lotus_farm/images/lotus-agritech.jpg',
  data:{url:url.pathname+url.search},
 }));
});
self.addEventListener('notificationclick',event=>{
 event.notification.close();
 const target=new URL(event.notification.data?.url||'/warehouse',self.location.origin);
 if(target.origin!==self.location.origin)return;
 event.waitUntil((async()=>{
  const windows=await self.clients.matchAll({type:'window',includeUncontrolled:true});
  const existing=windows.find(client=>{
   try{return new URL(client.url).pathname===target.pathname}catch{return false}
  });
  if(existing){await existing.navigate(target.href);return existing.focus()}
  return self.clients.openWindow(target.href);
 })());
});
