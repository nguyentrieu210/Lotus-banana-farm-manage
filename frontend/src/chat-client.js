import {computed,onBeforeUnmount,onMounted,ref,watch} from 'vue'
import {io} from 'socket.io-client'
import {call} from './api'

export const chatAPI=(name,args={},write=false)=>call('lotus_farm.chat.'+name,args,write)
export function useChatConnection(getUser){
 const rooms=ref([]),unread=ref(0),connected=ref(false),error=ref(''),loading=ref(false),event=ref(null)
 let socket,timer,debounce,version=0,pending=false,lastSync=0,started=false
 const valid=()=>getUser()&&getUser()!=='Guest'
 async function refresh(){
  if(!valid()||pending||navigator.onLine===false)return
  const generation=version;pending=true;loading.value=!rooms.value.length
  try{
   const result=await chatAPI('inbox')
   if(generation!==version)return
   rooms.value=result.rooms||[];unread.value=result.unread||0;error.value='';lastSync=Date.now()
   event.value={kind:'sync',at:Date.now()}
   if(!socket&&result.site&&import.meta.env.MODE!=='test'){
    socket=io(window.location.origin+'/'+result.site,{path:'/socket.io',withCredentials:true,transports:['websocket','polling']})
    socket.on('connect',()=>{if(generation===version){connected.value=true;refresh()}})
    socket.on('disconnect',()=>{connected.value=false})
    socket.on('connect_error',()=>{connected.value=false})
    socket.on('lotus_chat',value=>{
     if(generation!==version)return
     event.value={...value,at:Date.now()}
     if(value.kind!=='typing'){clearTimeout(debounce);debounce=setTimeout(refresh,150)}
    })
   }
  }catch(e){if(generation===version)error.value=e.message||'Chưa kết nối được chat.'}
  finally{if(generation===version){pending=false;loading.value=false}}
 }
 function reset(){
  version++;pending=false;socket?.disconnect();socket=null;connected.value=false
  rooms.value=[];unread.value=0;error.value='';event.value=null
  if(started)refresh()
 }
 function visible(){if(!document.hidden)refresh()}
 watch(getUser,reset,{flush:'sync'})
 onMounted(()=>{
  started=true;refresh()
  timer=setInterval(()=>{if(!document.hidden&&Date.now()-lastSync>(connected.value?30000:5000))refresh()},5000)
  window.addEventListener('online',visible);document.addEventListener('visibilitychange',visible)
 })
 onBeforeUnmount(()=>{
  started=false;version++;socket?.disconnect();clearInterval(timer);clearTimeout(debounce)
  window.removeEventListener('online',visible);document.removeEventListener('visibilitychange',visible)
 })
 return {rooms,unread,connected,error,loading,event,refresh,total:computed(()=>rooms.value.length)}
}
