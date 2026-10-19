import {call} from './api'

/* Do not leave a logged-out account's push endpoint on a shared phone. */
export async function revokeDevicePush(app){
 if(!('serviceWorker' in navigator))return
 try{
  const reg=await navigator.serviceWorker.getRegistration(location.pathname)
  const sub=await reg?.pushManager?.getSubscription()
  if(!sub)return
  try{await call('lotus_farm.push_notifications.unsubscribe',{app,endpoint:sub.endpoint},true)}catch{}
  await sub.unsubscribe()
 }catch{}
}

/* One sign-out for every PWA: drop this device's push endpoint, end the Frappe session, return to the app's login. */
export async function logoutPwa(app,{csrf='',home}){
 await revokeDevicePush(app)
 const response=await fetch('/api/method/logout',{method:'POST',credentials:'same-origin',headers:{'X-Frappe-CSRF-Token':csrf}})
 if(!response.ok)throw Error('Máy chủ chưa xử lý đăng xuất.')
 window.location.replace('/login?redirect-to='+home)
}
