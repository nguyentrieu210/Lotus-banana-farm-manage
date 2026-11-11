<script setup>
import {onBeforeUnmount,onMounted,ref} from 'vue'
import LotusIcon from './LotusIcon.vue'
// Network state for the phone PWAs (spec 004, FR-026): a fixed bar while offline ("Đang ngoại tuyến", with the number
// of entries waiting to be sent), a short "Đã có mạng" when the connection comes back, then nothing.
const props=defineProps({queued:{type:Number,default:0},online:{type:Boolean,default:undefined}})
const net=ref(typeof navigator==='undefined'||navigator.onLine!==false)
const back=ref(false)
let timer=null
function update(){
 const now=typeof navigator==='undefined'||navigator.onLine!==false
 if(now&&!net.value){back.value=true;clearTimeout(timer);timer=setTimeout(()=>back.value=false,3000)}
 net.value=now
}
onMounted(()=>{window.addEventListener('online',update);window.addEventListener('offline',update)})
onBeforeUnmount(()=>{window.removeEventListener('online',update);window.removeEventListener('offline',update);clearTimeout(timer)})
const isOnline=()=>props.online===undefined?net.value:props.online
</script>
<template>
 <div v-if="!isOnline()" class="lotus-netbar" role="status"><LotusIcon name="wifi-off"/><span class="lotus-netbar__text">Đang ngoại tuyến · sẽ gửi khi có mạng</span><span v-if="queued" class="lotus-netbar__queue">{{queued}} chờ gửi</span></div>
 <div v-else-if="back" class="lotus-netbar lotus-netbar--online" role="status"><LotusIcon name="wifi"/>Đã có mạng</div>
</template>
