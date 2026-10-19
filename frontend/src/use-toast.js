import {reactive,watch} from 'vue'
// App-wide toasts rendered by components/ui/toast/Toaster.vue (reka-ui Toast).
// toast.success('Đã lưu') · toast.error(msg) · toast({title,description,tone,duration,action:{label,run}})
const state=reactive({items:[]})
let seq=0
export function toast(input){
 const item={tone:'info',duration:5000,...(typeof input==='string'?{title:input}:input),id:++seq,open:true}
 // an action (e.g. Hoàn tác) needs time to be noticed
 if(item.action&&item.duration<8000)item.duration=8000
 state.items.push(item)
 if(state.items.length>4)state.items.splice(0,state.items.length-4)
 return item.id
}
toast.success=(title,options={})=>toast({...options,title,tone:'success'})
toast.error=(title,options={})=>toast({...options,title,tone:'error',duration:options.duration??8000})
toast.info=(title,options={})=>toast({...options,title,tone:'info'})
export function dismissToast(id){const index=state.items.findIndex(item=>item.id===id);if(index>=0)state.items.splice(index,1)}
export function useToastState(){return state}
// Bridge for screens that already set a success ref (notice/message): show it as a toast, then clear the ref.
export function useNoticeToast(source){
 watch(source,text=>{if(!text)return;toast.success(String(text));source.value=''},{flush:'post'})
}
