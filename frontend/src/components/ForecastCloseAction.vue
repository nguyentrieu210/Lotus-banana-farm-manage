<script setup>
import {computed,onBeforeUnmount,ref,watch} from 'vue'
import {call} from '../api'
import WorkspaceModal from './WorkspaceModal.vue'
import {Button as UiButton} from './ui/button'
import {Textarea as UiTextarea} from './ui/textarea'
import {FormField} from './ui/form-field'

const props=defineProps({forecast:Object,canClose:Boolean,disabled:Boolean})
const emit=defineEmits(['closed','busy'])
const opened=ref(false),reason=ref(''),busy=ref(false),error=ref('')
const eligible=computed(()=>props.canClose&&props.forecast?.name&&props.forecast?.supply_state==='Released')
let request=0
watch(()=>[props.forecast?.name,props.forecast?.supply_state],()=>{request++;opened.value=false;reason.value='';error.value='';if(busy.value){busy.value=false;emit('busy',false)}})
onBeforeUnmount(()=>{request++;if(busy.value)emit('busy',false)})
function open(){reason.value='';error.value='';opened.value=true}
async function close(){
 if(!eligible.value||!reason.value.trim()||busy.value)return
 const version=++request,forecast=props.forecast.name,base_modified=props.forecast.modified
 busy.value=true;error.value='';emit('busy',true)
 let result=null
 try{result=await call('lotus_farm.onedrive_supply.close_forecast',{forecast,reason:reason.value.trim(),base_modified},true)}
 catch(e){if(version===request)error.value=e.message}
 finally{if(version===request){busy.value=false;emit('busy',false)}}
 if(version===request&&result){opened.value=false;emit('closed',result)}
}
</script>

<template>
 <UiButton v-if="eligible" variant="outline" :disabled="disabled||busy" @click="open">Kết thúc dự thu</UiButton>
 <WorkspaceModal v-model="opened" title="Kết thúc dự thu" width="560px" :busy="busy">
  <p>{{forecast?.name}} · Phần nguồn cung còn lại sẽ ngừng nhận giữ hàng mới.</p>
  <FormField label="Lý do kết thúc" required v-slot="field"><UiTextarea v-bind="field" v-model="reason" rows="3"/></FormField>
  <p v-if="error" role="alert" class="error">{{error}}</p>
  <div class="forecast-close-actions"><UiButton variant="outline" :disabled="busy" @click="opened=false">Không thực hiện</UiButton><UiButton :disabled="busy||!reason.trim()" :loading="busy" @click="close">Xác nhận kết thúc</UiButton></div>
 </WorkspaceModal>
</template>

<style scoped>
.forecast-close-actions{display:flex;justify-content:flex-end;gap:var(--lotus-space-2);margin-top:var(--lotus-space-3)}
</style>
