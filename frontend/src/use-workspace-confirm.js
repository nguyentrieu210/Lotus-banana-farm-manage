import {ref} from 'vue'
import {useConfirmCore} from './use-confirm-core'
// Desktop counterpart of useMobileConfirm: ask() resolves true/false, tell() shows a message with one button.
export function useWorkspaceConfirm(){
 const open=ref(false),title=ref('Xác nhận'),alertOnly=ref(false)
 const core=useConfirmCore({onShow:()=>{open.value=true},onHide:()=>{open.value=false}})
 function show(text,heading,single){if(core.pending.value)return Promise.resolve(false);title.value=heading;alertOnly.value=single;return core.ask(text)}
 const ask=(text,heading='Xác nhận')=>show(text,heading,false)
 const tell=(text,heading='Thông báo')=>show(text,heading,true)
 return {open,title,alertOnly,message:core.message,ask,tell,finish:core.finish}
}
