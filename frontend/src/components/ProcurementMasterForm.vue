<script setup>
import '../procurement.css'
import {computed,onMounted,ref,watch} from 'vue'
import {call} from '../api'
import {newKey,purchaseKinds,purchaseRequest} from '../procurement'
import ProcurementField from './ProcurementField.vue'
import MobileSupplierForm from './MobileSupplierForm.vue'
import {Button} from './ui/button'
import LotusMobileButton from './LotusMobileButton.vue'
const props=defineProps({company:String,kind:String,name:String,mobile:Boolean})
const emit=defineEmits(['saved','dirty'])
const data=ref(null),options=ref({}),error=ref(''),saving=ref(false),ready=ref(false)
let snapshot=''
watch(data,()=>{if(snapshot)emit('dirty',JSON.stringify(data.value)!==snapshot)},{deep:true})
const key=newKey(),button=computed(()=>props.mobile?LotusMobileButton:Button)
const api=(m,args={},write=false)=>purchaseRequest(call,'lotus_farm.procurement_masters.'+m,args,write)
const opts=rows=>(rows||[]).map(r=>({value:r.name,label:r.name}))
onMounted(async()=>{try{
 options.value=await api('options',{company:props.company})
 const d=props.name?await api('detail',{company:props.company,kind:props.kind,name:props.name}):null
 data.value=props.kind==='suppliers'?{type:'Company',group:options.value.supplier_groups?.[0]?.name||'',country:'Vietnam',name:'',contact:'',phone:'',notes:'',...d,...(d?{name:d.supplier_name}:{})}:
  {item_code:'',item_name:'',kind:'Material',uom:options.value.uoms?.find(r=>r.name==='Kg')?.name||options.value.uoms?.find(r=>r.name==='Nos')?.name||'',group:options.value.item_groups?.[0]?.name||'',conversions:[],...d}
 snapshot=JSON.stringify(data.value);ready.value=true
}catch(e){error.value=e.message}})
function dirty(){if(ready.value)emit('dirty',true)}
async function save(){if(saving.value)return;saving.value=true;error.value='';try{
 const values={...data.value}
 if(props.kind==='suppliers'){values.supplier_name=data.value.name;if(!options.value.can_bank){delete values.bank_account_no;delete values.bank;delete values.bank_account_name}}
 const result=await api('save',{company:props.company,kind:props.kind,name:props.name||null,modified:data.value.modified,values,client_key:key},true)
 emit('dirty',false);emit('saved',result)
}catch(e){error.value=e.message}finally{saving.value=false}}
defineExpose({isSaving:()=>saving.value})
</script>
<template><p v-if="error" role="alert" class="procurement-error">{{error}}</p><div v-if="data" @input="dirty" @change="dirty">
 <MobileSupplierForm v-if="kind==='suppliers'" v-model="data" :mobile="mobile" extended :options="options" :saving="saving||data.can_write===false" @submit="save"/>
 <form v-else @submit.prevent="save"><fieldset :disabled="saving||data.can_write===false"><div class="procurement-fields">
  <ProcurementField v-model="data.item_code" :mobile="mobile" label="Mã hàng" :disabled="!!name" required/>
  <ProcurementField v-model="data.item_name" :mobile="mobile" label="Tên hàng" required/>
  <ProcurementField v-model="data.kind" :mobile="mobile" label="Loại mua" :options="purchaseKinds" :searchable="false" :disabled="!!name" required/>
  <ProcurementField v-model="data.group" :mobile="mobile" label="Nhóm hàng" :options="opts(options.item_groups)" required/>
  <ProcurementField v-model="data.uom" :mobile="mobile" label="Đơn vị gốc" :options="opts(options.uoms)" :disabled="!!name" required/>
  <ProcurementField v-if="data.kind==='Asset'" v-model="data.asset_category" :mobile="mobile" label="Nhóm tài sản" :options="opts(options.asset_categories)" :disabled="!!name" required/>
  <ProcurementField v-model="data.description" :mobile="mobile" label="Mô tả" type="textarea"/>
  <ProcurementField :model-value="String(data.disabled||0)" :mobile="mobile" label="Trạng thái" :options="[{value:'0',label:'Đang dùng'},{value:'1',label:'Ngừng dùng'}]" :searchable="false" @update:model-value="data.disabled=Number($event)"/>
 </div><section v-for="(r,i) in data.conversions" :key="i" class="procurement-actions">
  <ProcurementField v-model="r.uom" :mobile="mobile" label="Đơn vị quy đổi" :options="opts(options.uoms)" required/>
  <ProcurementField v-model="r.conversion_factor" :mobile="mobile" label="Hệ số về đơn vị gốc" type="number" min="0.000001" step="any" required/>
  <component :is="button" type="button" @click="data.conversions.splice(i,1);emit('dirty',true)">Bỏ quy đổi</component>
 </section><div class="procurement-actions"><component :is="button" type="button" @click="data.conversions.push({uom:'',conversion_factor:1});emit('dirty',true)">Thêm quy đổi</component><component :is="button" type="submit" :disabled="saving">Lưu hàng mua</component></div></fieldset></form>
</div></template>
