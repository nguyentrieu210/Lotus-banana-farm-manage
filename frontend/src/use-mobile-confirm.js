import {nextTick,ref} from 'vue'
import {useConfirmCore} from './use-confirm-core'
// Phone PWAs: drives a LotusMobileDialog ref.
export function useMobileConfirm(){
 const dialog=ref(null)
 const core=useConfirmCore({onShow:()=>nextTick(()=>dialog.value?.showModal()),onHide:()=>dialog.value?.close()})
 return {dialog,...core}
}
