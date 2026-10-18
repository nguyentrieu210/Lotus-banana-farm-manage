import {call} from './api'

const workers={
 warehouse:'/api/method/lotus_farm.web.warehouse_service_worker',
 buying:'/api/method/lotus_farm.web.buying_service_worker',
 work:'/api/method/lotus_farm.web.work_service_worker',
 hr:'/api/method/lotus_farm.web.hr_mobile_service_worker'
}
export function canUsePush(){
 return typeof window!=='undefined'&&window.isSecureContext&&
  'serviceWorker' in navigator&&'PushManager' in window&&'Notification' in window
}
function decodeKey(raw){
 const padded=raw+'='.repeat((4-raw.length%4)%4)
 return Uint8Array.from(atob(padded.replace(/-/g,'+').replace(/_/g,'/')),x=>x.charCodeAt(0))
}
/* Only call this after an explicit click: browsers require user activation for permission. */
export async function enableMobilePush(app){
 if(!workers[app])throw Error('Ứng dụng chưa hỗ trợ thông báo.')
 if(!canUsePush())throw Error('Trình duyệt chưa hỗ trợ thông báo. Hãy mở ứng dụng qua HTTPS; trên iPhone hãy cài vào màn hình chính.')
 if(Notification.permission==='denied')throw Error('Thông báo đã bị chặn. Hãy mở cài đặt của ứng dụng và cấp lại quyền.')
 const permission=Notification.permission==='granted'?'granted':await Notification.requestPermission()
 if(permission!=='granted')throw Error('Bạn chưa cho phép nhận thông báo.')
 const config=await call('lotus_farm.push_notifications.config',{app})
 if(!config?.enabled||!config?.public_key)throw Error('Máy chủ chưa thiết lập thông báo đẩy.')
 let registration=await navigator.serviceWorker.getRegistration(location.pathname)
 if(!registration)registration=await navigator.serviceWorker.register(workers[app],{scope:app==='hr'?'/hr-mobile':'/'+app,updateViaCache:'none'})
 await navigator.serviceWorker.ready
 const sub=await registration.pushManager.getSubscription()||
  await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:decodeKey(config.public_key)})
 await call('lotus_farm.push_notifications.subscribe',{app,subscription:sub.toJSON()},true)
 return true
}
