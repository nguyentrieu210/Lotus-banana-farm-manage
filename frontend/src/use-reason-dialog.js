import {ref} from 'vue'
// Ask for a short reason in a dialog instead of window.prompt: `await reason.ask('Đảo bút toán')` resolves the text, or null when cancelled.
export function useReasonDialog(){
 const open=ref(false),title=ref(''),label=ref('Lý do'),text=ref('')
 let resolve=null
 function ask(heading,fieldLabel='Lý do'){
  if(resolve)return Promise.resolve(null)
  title.value=heading;label.value=fieldLabel;text.value='';open.value=true
  return new Promise(done=>{resolve=done})
 }
 function finish(value){open.value=false;const done=resolve;resolve=null;done?.(value)}
 return {open,title,label,text,ask,finish}
}
