import {onUnmounted,ref} from 'vue'
// Desktop counterpart of useMobileConfirm: ask() resolves true/false, tell() shows a message with one button.
export function useWorkspaceConfirm(){
 const open=ref(false),message=ref(''),title=ref('Xác nhận'),alertOnly=ref(false)
 let resolver
 function show(text,heading,single){
  if(open.value)return Promise.resolve(false)
  message.value=text;title.value=heading;alertOnly.value=single;open.value=true
  return new Promise(resolve=>{resolver=resolve})
 }
 const ask=(text,heading='Xác nhận')=>show(text,heading,false)
 const tell=(text,heading='Thông báo')=>show(text,heading,true)
 function finish(value){open.value=false;const resolve=resolver;resolver=null;resolve?.(!!value)}
 onUnmounted(()=>finish(false))
 return {open,message,title,alertOnly,ask,tell,finish}
}
