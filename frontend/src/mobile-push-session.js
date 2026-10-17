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
