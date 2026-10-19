import {onUnmounted,ref} from 'vue'
// Shared core of the in-app confirm dialogs (phone: useMobileConfirm, desktop: useWorkspaceConfirm).
// One question at a time: ask() returns a promise that finish(true|false) resolves; a second ask() while
// one is open resolves false so double taps never stack dialogs. onShow/onHide drive the actual dialog.
export function useConfirmCore({onShow=()=>{},onHide=()=>{}}={}){
 const message=ref(''),pending=ref(false)
 let resolver
 function ask(text){
  if(pending.value)return Promise.resolve(false)
  message.value=text;pending.value=true
  return new Promise(resolve=>{resolver=resolve;onShow()})
 }
 function finish(value){onHide();pending.value=false;const resolve=resolver;resolver=null;resolve?.(!!value)}
 onUnmounted(()=>finish(false))
 return {message,pending,ask,finish}
}
