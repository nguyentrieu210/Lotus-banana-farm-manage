<script setup>
import {computed,onMounted,onBeforeUnmount,ref} from 'vue'
import {Popup,Button,Icon} from 'vant'
import {canUsePush,enableMobilePush} from '../mobile-push-subscription'

const props=defineProps({app:{type:String,required:true},title:{type:String,required:true}})
const visible=ref(false),step=ref('install'),installPrompt=ref(null),installed=ref(false)
const installing=ref(false),subscribing=ref(false),pushDone=ref(false)
const error=ref(''),info=ref('')
const isIOS=typeof navigator!=='undefined'&&/iphone|ipad|ipod/i.test(navigator.userAgent)
const appTitle=computed(()=>({warehouse:'Kho Lotus',buying:'Mua hàng Lotus',work:'Công việc ngoài vườn'})[props.app]||props.title)
const storageKey=computed(()=>'lotus-pwa-setup-v1:'+props.app)
const installKey=computed(()=>'lotus-pwa-installed:'+props.app)
const featureText=computed(()=>({
 warehouse:'Tạo phiếu nhập, xuất kho và theo dõi hàng đang về.',
 buying:'Lập đơn mua, theo dõi nhà cung cấp và duyệt đơn theo quyền.',
 work:'Nhận việc tại vườn, ghi kết quả và xem tiến độ.'
})[props.app]||'Sử dụng ứng dụng trên điện thoại.')
const manualInstall=computed(()=>isIOS?
 'Mở bằng Safari, bấm Chia sẻ rồi chọn “Thêm vào Màn hình chính”.':
 'Mở bằng Chrome, vào menu ⋮ rồi chọn “Cài ứng dụng” hoặc “Thêm vào màn hình chính”.')
function save(key,value){try{localStorage.setItem(key,value)}catch{}}
function load(key){try{return localStorage.getItem(key)}catch{return null}}
function runningAsApp(){
 return window.matchMedia?.('(display-mode: standalone)').matches||navigator.standalone===true
}
function onBeforeInstall(event){
 event.preventDefault()
 installPrompt.value=event
}
function onInstalled(){
 installed.value=true
 save(installKey.value,'1')
 installPrompt.value=null
 if(visible.value&&step.value==='install'){error.value='';info.value='Đã cài ứng dụng.';step.value='push'}
}
async function checkPushStatus(){
 if(!canUsePush())return
 try{
  const registration=await navigator.serviceWorker.getRegistration(location.pathname)
  pushDone.value=!!(await registration?.pushManager.getSubscription())
 }catch{}
}
function openSetup(){
 error.value='';info.value=''
 installed.value=!!(runningAsApp()||load(installKey.value)==='1')
 pushDone.value=false
 checkPushStatus()
 step.value=installed.value?'push':'install'
 visible.value=true
}
function goNext(){error.value='';info.value='';step.value=step.value==='install'?'push':'guide'}
function finish(){
 save(storageKey.value,'done')
 visible.value=false
}
async function install(){
 error.value='';info.value=''
 if(!installPrompt.value){
  info.value=manualInstall.value
  return
 }
 installing.value=true
 try {
  const event=installPrompt.value
  installPrompt.value=null
  await event.prompt()
  const choice=await event.userChoice
  if(choice?.outcome==='accepted'){info.value='Đã nhận yêu cầu cài đặt. Khi cài xong, bạn có thể bật thông báo.'}
  else info.value='Bạn có thể cài ứng dụng sau từ tab Tôi.'
 }catch(e){error.value=e?.message||'Không thể mở yêu cầu cài ứng dụng.'}
 finally{installing.value=false}
}
async function enablePush(){
 error.value='';info.value=''
 if(isIOS&&!runningAsApp()){error.value='Trên iPhone, hãy cài ứng dụng vào màn hình chính và mở từ biểu tượng trước khi bật thông báo.';return}
 subscribing.value=true
 try{
  await enableMobilePush(props.app)
  pushDone.value=true
  info.value='Đã bật thông báo cho ứng dụng này.'
 }catch(e){error.value=e?.message||'Không bật được thông báo.'}
 finally{subscribing.value=false}
}
onMounted(()=>{
 window.addEventListener('beforeinstallprompt',onBeforeInstall)
 window.addEventListener('appinstalled',onInstalled)
 window.addEventListener('lotus:open-setup',openSetup)
 if(!load(storageKey.value))openSetup()
})
onBeforeUnmount(()=>{
 window.removeEventListener('beforeinstallprompt',onBeforeInstall)
 window.removeEventListener('appinstalled',onInstalled)
 window.removeEventListener('lotus:open-setup',openSetup)
})
</script>

<template>
 <Popup v-model:show="visible" position="bottom" round teleport="body" :close-on-click-overlay="false"
  class="lotus-pwa-setup" :style="{maxHeight:'min(90dvh,680px)'}" @closed="save(storageKey,'done')">
  <section class="lotus-pwa-setup-content" aria-label="Thiết lập ứng dụng">
   <div class="lotus-pwa-setup-heading">
    <div class="lotus-pwa-setup-brand">
     <img :src="'/assets/lotus_farm/images/lotus-agritech-header-v2.png'" alt="Lotus Agritech"/>
     <p>Thiết lập lần đầu</p>
    </div>
    <button type="button" class="lotus-pwa-setup-close" aria-label="Bỏ qua thiết lập" @click="finish"><Icon name="cross" size="20"/></button>
   </div>
   <div class="lotus-pwa-setup-progress" aria-label="Bước thiết lập">
    <span :class="{active:step==='install'}"></span><span :class="{active:step==='push'}"></span><span :class="{active:step==='guide'}"></span>
   </div>
   <template v-if="step==='install'">
    <div class="lotus-pwa-setup-hero"><Icon name="apps-o" size="36"/></div>
    <h2>Cài {{appTitle}} lên điện thoại</h2>
    <p>Mở ứng dụng trực tiếp từ màn hình chính, không cần tìm lại đường link.</p>
    <p class="lotus-pwa-setup-hint">Ứng dụng vẫn dùng được trên trình duyệt nếu chưa cài.</p>
    <Button v-if="!installed" type="primary" block :loading="installing" @click="install">Cài ứng dụng</Button>
    <p v-else class="lotus-pwa-setup-success"><Icon name="checked"/> Đã cài ứng dụng</p>
    <Button plain block @click="goNext">{{installed?'Tiếp theo':'Để sau, tiếp tục'}}</Button>
   </template>
   <template v-else-if="step==='push'">
    <div class="lotus-pwa-setup-hero"><Icon name="bell" size="36"/></div>
    <h2>Bật thông báo đẩy</h2>
    <p>Nhận tin khi có việc cần xử lý trong {{appTitle}}.</p>
    <p class="lotus-pwa-setup-hint">Chỉ bật khi bạn đồng ý. Có thể tắt trong mục Thông báo.</p>
    <Button v-if="!pushDone" type="primary" block :loading="subscribing" @click="enablePush">Bật thông báo</Button>
    <p v-else class="lotus-pwa-setup-success"><Icon name="checked"/> Đã cho phép thông báo</p>
    <Button plain block @click="goNext">{{pushDone?'Tiếp theo':'Để sau, tiếp tục'}}</Button>
   </template>
   <template v-else>
    <div class="lotus-pwa-setup-hero"><Icon name="passed" size="36"/></div>
    <h2>Sẵn sàng sử dụng</h2>
    <p>{{featureText}}</p>
    <p class="lotus-pwa-setup-hint">Vào Trang chủ để bắt đầu, mục Tôi để xem tài khoản. Bạn có thể vào lại hướng dẫn từ mục Tôi.</p>
    <Button type="primary" block @click="finish">Bắt đầu sử dụng</Button>
   </template>
   <p v-if="info" class="lotus-pwa-setup-info" role="status">{{info}}</p>
   <p v-if="error" class="lotus-pwa-setup-error" role="alert">{{error}}</p>
   <button type="button" class="lotus-pwa-setup-skip" @click="finish">Bỏ qua thiết lập</button>
  </section>
 </Popup>
</template>
