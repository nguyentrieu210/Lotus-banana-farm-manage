<script setup>
import {onMounted,onUnmounted,ref} from 'vue'
const installEvent=ref(null)
const installed=ref(false)
const offline=ref(false)
const showHelp=ref(false)
function capture(event){event.preventDefault();installEvent.value=event}
function completed(){installed.value=true;installEvent.value=null}
function sync(){offline.value=!navigator.onLine}
async function install(){
 if(!installEvent.value){showHelp.value=!showHelp.value;return}
 const event=installEvent.value
 installEvent.value=null
 await event.prompt()
}
onMounted(()=>{
 installed.value=window.matchMedia('(display-mode: standalone)').matches||window.navigator.standalone===true
 sync()
 window.addEventListener('beforeinstallprompt',capture)
 window.addEventListener('appinstalled',completed)
 window.addEventListener('online',sync)
 window.addEventListener('offline',sync)
})
onUnmounted(()=>{
 window.removeEventListener('beforeinstallprompt',capture)
 window.removeEventListener('appinstalled',completed)
 window.removeEventListener('online',sync)
 window.removeEventListener('offline',sync)
})
</script>
<template>
 <div class="warehouse-install-bar">
  <div><strong>Kho Lotus</strong><span v-if="offline" role="alert">Ngoại tuyến — không thể nhập, xuất hoặc duyệt phiếu.</span><span v-else>Giao diện Kho trên điện thoại</span></div>
  <button v-if="!installed" type="button" @click="install">+ Thêm ra màn hình chính</button>
 </div>
 <p v-if="showHelp" class="warehouse-install-help" role="note">iPhone: mở trang bằng Safari, bấm Chia sẻ → Thêm vào màn hình chính. Android: mở bằng Chrome, chọn Cài đặt ứng dụng hoặc Thêm vào màn hình chính. PWA cần HTTPS, trừ khi chạy localhost.</p>
</template>
