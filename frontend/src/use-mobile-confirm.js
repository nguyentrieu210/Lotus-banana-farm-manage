import {nextTick,onUnmounted,ref} from 'vue'
export function useMobileConfirm(){
 const dialog=ref(null),message=ref(''),pending=ref(false)
 let resolver
 function ask(text){
  if(pending.value)return Promise.resolve(false)
  message.value=text;pending.value=true
  return new Promise(resolve=>{resolver=resolve;nextTick(()=>dialog.value?.showModal())})
 }
 function finish(value){dialog.value?.close();pending.value=false;const resolve=resolver;resolver=null;resolve?.(!!value)}
 onUnmounted(()=>finish(false))
 return {dialog,message,pending,ask,finish}
}
