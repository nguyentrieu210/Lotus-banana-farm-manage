<script setup>
import {ref, onMounted, onBeforeUnmount} from 'vue'
import {Icon, Badge, Popup, Button, Cell, Empty} from 'vant'
import {call} from '../api'

const props=defineProps({app:{type:String,required:true}})
const show=ref(false),rows=ref([]),unread=ref(0),subscribed=ref(false)
const busy=ref(false),error=ref(''),message=ref('')
const supported=typeof window!=='undefined'&&window.isSecureContext&&
 'serviceWorker' in navigator&&'PushManager' in window&&'Notification' in window
const api=(name,args={},write=false)=>call('lotus_farm.push_notifications.'+name,args,write)
let polling
function appWorker(app){
 return '/api/method/lotus_farm.web.'+({warehouse:'warehouse_service_worker',buying:'buying_service_worker',work:'work_service_worker',hr:'hr_mobile_service_worker'}[app])
}
const appScope=app=>app==='hr'?'/hr-mobile':'/'+app
function decodeKey(raw){
 const padding='='.repeat((4-raw.length%4)%4)
 const bytes=atob(raw.replace(/-/g,'+').replace(/_/g,'/')+padding)
 return Uint8Array.from(bytes,c=>c.charCodeAt(0))
}
async function refresh(){
 try{
  const response=await api('inbox',{app:props.app})
  rows.value=response?.rows||[]
  unread.value=Number(response?.unread||0)
  const reg=supported?await navigator.serviceWorker.getRegistration(location.pathname):null
  subscribed.value=!!(await reg?.pushManager.getSubscription())
 }catch(e){if(show.value)error.value=e.message}
}
async function getWorker(){
 let worker=await navigator.serviceWorker.getRegistration(location.pathname)
 if(!worker)worker=await navigator.serviceWorker.register(appWorker(props.app),{
  scope:appScope(props.app),
  updateViaCache:'none'
 })
 await navigator.serviceWorker.ready
 return worker
}
async function enable(){
 error.value='';message.value=''
 if(!supported){error.value='Thiết bị/trình duyệt này chưa hỗ trợ thông báo đẩy. Hãy cài PWA qua HTTPS.';return}
 if(Notification.permission==='denied'){error.value='Thông báo đang bị chặn. Mở cài đặt ứng dụng trên điện thoại để cho phép.';return}
 busy.value=true
 try{
  const permission=await Notification.requestPermission()
  if(permission!=='granted')throw Error('Bạn chưa cho phép nhận thông báo.')
  const config=await api('config',{app:props.app})
  if(!config.enabled||!config.public_key)throw Error('Máy chủ chưa thiết lập thông báo.')
  const worker=await getWorker()
  const sub=await worker.pushManager.getSubscription()||await worker.pushManager.subscribe({
   userVisibleOnly:true,applicationServerKey:decodeKey(config.public_key)
  })
  await api('subscribe',{app:props.app,subscription:sub.toJSON()},true)
  subscribed.value=true;message.value='Đã bật thông báo trên điện thoại này.'
  await refresh()
 }catch(e){error.value=e?.message||'Không bật được thông báo.'}
 finally{busy.value=false}
}
async function disable(){
 busy.value=true;error.value='';message.value=''
 try{
  const worker=await navigator.serviceWorker.getRegistration(location.pathname)
  const sub=await worker?.pushManager.getSubscription()
  if(sub){await api('unsubscribe',{app:props.app,endpoint:sub.endpoint},true);await sub.unsubscribe()}
  subscribed.value=false
  message.value='Đã tắt thông báo trên ứng dụng này.'
 }catch(e){error.value=e.message}
 finally{busy.value=false}
}
async function sendTest(){
 busy.value=true;error.value='';message.value=''
 try{await api('test_push',{app:props.app},true);message.value='Đã yêu cầu gửi thông báo thử.';await refresh()}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
async function openAlert(item){
 try{
  await api('mark_read',{app:props.app,name:item.name},true)
  item.is_read=1;unread.value=Math.max(0,unread.value-1)
 }catch(e){error.value=e.message;return}
 const route=String(item.url||'')
 if((route===appScope(props.app)||route.startsWith(appScope(props.app)+'?')||route.startsWith(appScope(props.app)+'/')) && !route.startsWith('//')){
  show.value=false
  location.href=route
 }
}
function visibility(){if(document.visibilityState==='visible')refresh()}
onMounted(()=>{
 refresh()
 polling=setInterval(()=>{if(document.visibilityState==='visible'&&navigator.onLine)refresh()},60000)
 document.addEventListener('visibilitychange',visibility)
})
onBeforeUnmount(()=>{clearInterval(polling);document.removeEventListener('visibilitychange',visibility)})
</script>
<template>
 <div class="lotus-notification">
  <button type="button" class="lotus-notification-trigger" aria-label="Thông báo" @click="show=true;error='';message='';refresh()">
   <Badge :content="unread>99?'99+':unread" :show-zero="false" :max="99"><Icon name="bell" size="24"/></Badge>
  </button>
  <Popup v-model:show="show" position="bottom" round closeable teleport="body" :style="{height:'min(82dvh,660px)'}">
   <section class="lotus-notification-panel">
    <h2>Thông báo <small v-if="unread">({{unread}} chưa đọc)</small></h2>
    <p v-if="error" class="lotus-notification-error" role="alert">{{error}}</p>
    <p v-if="message" class="lotus-notification-ok" role="status">{{message}}</p>
    <div class="lotus-notification-controls">
     <Button :loading="busy" type="primary" size="small" @click="subscribed?disable():enable()">
      {{subscribed?'Tắt trên máy này':'Bật thông báo đẩy'}}
     </Button>
     <Button v-if="subscribed" :loading="busy" plain size="small" @click="sendTest">Gửi thử</Button>
     <Button icon="replay" plain size="small" @click="refresh">Làm mới</Button>
    </div>
    <p class="lotus-notification-help">Thông báo chỉ bật khi bạn cho phép. Trên iPhone, hãy thêm ứng dụng vào màn hình chính trước.</p>
    <div class="lotus-notification-items">
     <Empty v-if="!rows.length" description="Chưa có thông báo"/>
     <Cell v-for="item in rows" :key="item.name" is-link :class="{'lotus-notification-unread':!item.is_read}" @click="openAlert(item)">
      <template #title><strong>{{item.title}}</strong></template>
      <template #label><span>{{item.body}}</span><small>{{item.creation}}</small></template>
     </Cell>
    </div>
   </section>
  </Popup>
 </div>
</template>
