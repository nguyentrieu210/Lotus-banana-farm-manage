<script setup>
import {computed,onMounted,ref} from 'vue'
import {call} from '../api'
import LotusField from './form/LotusField.vue'
import FormGrid from './form/FormGrid.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import {Button} from './ui/button'
// fixed: the reason is decided by the screen (Mua nhanh = Purchase), so only the supplier is asked.
const props=defineProps({reason:String,supplier:String,mobile:Boolean,fixed:Boolean})
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
 if(!selected)return 'Chọn lý do nhập kho.'
 if(selected.supplier&&!props.supplier)return 'Chọn nhà cung cấp cho hàng mua ngoài.'
 if(selected.supplier&&lines.some(r=>!(Number(r.rate)>0)))return 'Nhập giá mua cho từng dòng hàng mua.'
 if(selected?.lot&&lines.some(r=>!String(r.area||'').trim()))return 'Nhập lô thu hồi vật tư cho từng dòng.'
 return ''
}
onMounted(load)
defineExpose({validate})
</script>
<template>
 <p v-if="busy" role="status">Đang tải lý do nhập kho…</p>
 <template v-if="error"><p role="alert" :class="mobile?'mobile-message danger':'stock-alert'">{{error}}</p><component :is="button" type="button" :disabled="busy" @click="load">Thử lại lý do nhập kho</component></template>
 <component :is="mobile?'div':FormGrid" v-if="options" :class="mobile?'mobile-form-fields':undefined">
  <LotusField v-if="!fixed" :mobile="mobile" label="Lý do nhập kho" :model-value="reason" :options="mobile?[{value:'',label:'Chọn lý do…'},...options.reasons]:options.reasons" :searchable="false" required @update:model-value="emit('update:reason',$event)"/>
  <LotusField v-if="options.reasons.find(r=>r.value===reason)?.supplier" :mobile="mobile" label="Nhà cung cấp" :model-value="supplier" :options="(options.suppliers||[]).map(r=>({value:r.name,label:r.supplier_name||r.name}))" required @update:model-value="emit('update:supplier',$event)"/>
 </component>
 <p v-if="!fixed&&options?.reasons.find(r=>r.value===reason)?.supplier" class="lotus-form-note">Hàng mua cần giá cho từng dòng. Đã có đơn mua thì dùng <b>Nhận hàng theo đơn mua</b> để đơn và đề nghị được cập nhật.</p>
</template>
