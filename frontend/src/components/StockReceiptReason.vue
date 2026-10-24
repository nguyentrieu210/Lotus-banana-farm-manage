<script setup>
import {computed,onMounted,ref} from 'vue'
import {call} from '../api'
import ProcurementField from './ProcurementField.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import {Button} from './ui/button'
const props=defineProps({reason:String,supplier:String,mobile:Boolean})
const emit=defineEmits(['update:reason','update:supplier'])
const options=ref(null),busy=ref(false),error=ref('')
const button=computed(()=>props.mobile?LotusMobileButton:Button)
let pending
function load(){
 if(pending)return pending
 busy.value=true;error.value=''
 pending=(async()=>{try{
  const result=await call('lotus_farm.finance.stock.receipt_options')
  if(!Array.isArray(result?.reasons))throw Error('Chưa tải được danh mục lý do nhập kho.')
  options.value=result
 }catch(e){error.value=e.message}finally{busy.value=false;pending=null}})()
 return pending
}
async function validate(lines=[]){
 if(!options.value)await load()
 if(!options.value)return error.value||'Chưa tải được lý do nhập kho. Bấm Thử lại.'
 const selected=options.value.reasons.find(r=>r.value===props.reason)
 if((options.value.enabled||props.reason)&&!selected)return 'Chọn lý do nhập kho.'
 if(selected?.supplier&&!props.supplier)return 'Chọn nhà cung cấp cho hàng mua ngoài.'
 if(selected?.lot&&lines.some(r=>!String(r.area||'').trim()))return 'Nhập lô thu hồi vật tư cho từng dòng.'
 return ''
}
onMounted(load)
defineExpose({validate})
</script>
<template>
 <p v-if="busy" role="status">Đang tải lý do nhập kho…</p>
 <template v-if="error"><p role="alert" :class="mobile?'mobile-message danger':'stock-alert'">{{error}}</p><component :is="button" type="button" :disabled="busy" @click="load">Thử lại lý do nhập kho</component></template>
 <div v-if="options" :class="mobile?'mobile-form-fields':'stock-form-grid'">
  <ProcurementField :mobile="mobile" label="Lý do nhập kho" :model-value="reason" :options="mobile?[{value:'',label:'Chọn lý do…'},...options.reasons]:options.reasons" :searchable="false" :required="options.enabled" @update:model-value="emit('update:reason',$event)"/>
  <ProcurementField v-if="options.reasons.find(r=>r.value===reason)?.supplier" :mobile="mobile" label="Nhà cung cấp" :model-value="supplier" :options="(options.suppliers||[]).map(r=>({value:r.name,label:r.supplier_name||r.name}))" required @update:model-value="emit('update:supplier',$event)"/>
 </div>
</template>
