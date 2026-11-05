<script setup>
import {unitLabel} from '../units'
import {hrCatalogLabel} from '../hr-catalog-labels'
import '../procurement.css'
import {computed,onMounted,ref,watch} from 'vue'
import {call} from '../api'
import {newKey,purchaseKinds,purchaseRequest} from '../procurement'
import LotusField from './form/LotusField.vue'
import FormGrid from './form/FormGrid.vue'
import LineItemsEditor from './form/LineItemsEditor.vue'
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
const opts=rows=>(rows||[]).map(r=>({value:r.name,label:hrCatalogLabel(r.name)}))
onMounted(async()=>{try{
 options.value=await api('options',{company:props.company})
 const d=props.name?await api('detail',{company:props.company,kind:props.kind,name:props.name}):null
 data.value=props.kind==='suppliers'?{type:'Company',group:options.value.supplier_groups?.[0]?.name||'',country:'Vietnam',name:'',contact:'',phone:'',notes:'',...d,...(d?{name:d.supplier_name}:{})}:
  {item_code:'',item_name:'',kind:'Material',is_purchase_item:1,is_sales_item:0,uom:options.value.uoms?.find(r=>r.name==='Kg')?.name||options.value.uoms?.find(r=>r.name==='Nos')?.name||'',group:options.value.item_groups?.[0]?.name||'',conversions:[],...d}
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
<template><p v-if="error" role="alert" class="lotus-modal-form__error">{{error}}</p><div v-if="data" @input="dirty" @change="dirty">
 <MobileSupplierForm v-if="kind==='suppliers'" v-model="data" :mobile="mobile" extended :options="options" :saving="saving||data.can_write===false" @submit="save"/>
 <form v-else class="lotus-inline-form" @submit.prevent="save"><fieldset :disabled="saving||data.can_write===false">
  <FormGrid :columns="mobile?1:3">
   <LotusField v-model="data.item_code" :mobile="mobile" label="Mã hàng" :disabled="!!name" :placeholder="name?'':'Để trống: tự sinh '+({Material:'VT',Tool:'CC',Asset:'TS',Service:'DV'}[data.kind]||'VT')+'-00001…'"/>
   <LotusField v-model="data.item_name" :mobile="mobile" label="Tên hàng" required/>
   <LotusField v-model="data.kind" :mobile="mobile" label="Loại hàng" :options="purchaseKinds" :searchable="false" :disabled="!!data.used" required :hint="{Material:'Vào kho 152, xuất dùng tính chi phí lô / vườn.',Tool:'Vào kho 153, xuất dùng phân bổ chi phí.',Asset:'Không vào kho: nguyên giá 211, trích khấu hao.',Service:'VPP, sửa chữa, vận chuyển…: không theo dõi tồn, hóa đơn vào chi phí 642 (627 khi ghi cho vườn).'}[data.kind]"/>
   <LotusField v-model="data.group" :mobile="mobile" label="Nhóm hàng" :options="opts(options.item_groups)" required/>
   <LotusField v-model="data.uom" :mobile="mobile" label="Đơn vị gốc" :options="(options.uoms||[]).map(r=>({value:r.name,label:unitLabel(r.name)}))" :disabled="!!data.has_ledger" required :hint="data.has_ledger?'Đã nhập / xuất theo đơn vị này nên không đổi được; thêm đơn vị quy đổi bên dưới.':''"/>
   <LotusField v-if="data.kind==='Asset'" v-model="data.asset_category" :mobile="mobile" label="Nhóm tài sản" :options="opts(options.asset_categories)" :disabled="!!data.used" required/>
   <LotusField :model-value="String(data.disabled||0)" :mobile="mobile" label="Trạng thái" :options="[{value:'0',label:'Đang dùng'},{value:'1',label:'Ngừng dùng'}]" :searchable="false" :empty-option="null" @update:model-value="data.disabled=Number($event)"/>
   <LotusField :model-value="data.is_purchase_item!==0&&data.is_purchase_item!==false" :mobile="mobile" type="checkbox" label="Hàng mua" @update:model-value="data.is_purchase_item=$event?1:0"/>
   <LotusField :model-value="!!data.is_sales_item" :mobile="mobile" type="checkbox" label="Hàng bán" @update:model-value="data.is_sales_item=$event?1:0"/>
   <template v-if="['Material','Tool'].includes(data.kind)">
    <LotusField :model-value="!!data.has_batch_no" :mobile="mobile" type="checkbox" label="Quản lý theo lô" :disabled="!!data.has_ledger" :hint="data.has_ledger?'Đã có nhập xuất nên không đổi được.':''" @update:model-value="data.has_batch_no=$event?1:0"/>
    <LotusField v-if="data.has_batch_no" :model-value="!!data.has_expiry_date" :mobile="mobile" type="checkbox" label="Có hạn sử dụng" @update:model-value="data.has_expiry_date=$event?1:0"/>
    <LotusField v-if="data.has_batch_no&&data.has_expiry_date" v-model="data.shelf_life_in_days" :mobile="mobile" label="Hạn dùng (ngày)" type="number" min="0" step="1"/>
   </template>
   <LotusField v-model="data.lead_time_days" :mobile="mobile" label="Thời gian chờ hàng (ngày)" type="number" min="0" step="1"/>
   <LotusField v-model="data.description" :mobile="mobile" label="Mô tả" type="textarea" wide/>
  </FormGrid>
  <LineItemsEditor v-model="data.conversions" title="Đơn vị quy đổi" add-label="Thêm quy đổi" empty-text="Chưa có đơn vị quy đổi." :min="0" :mobile="mobile" :columns="[{field:'uom',label:'Đơn vị quy đổi',required:true,options:(options.uoms||[]).map(r=>({value:r.name,label:unitLabel(r.name)}))},{field:'conversion_factor',label:'Hệ số về đơn vị gốc',type:'number',required:true,props:{min:0.000001}}]" :new-row="()=>({uom:'',conversion_factor:1})" @update:model-value="emit('dirty',true)"/>
  <div class="lotus-inline-form__footer"><component :is="button" type="submit" :disabled="saving">{{saving?'Đang lưu…':'Lưu hàng mua'}}</component></div>
 </fieldset></form>
</div></template>
<style>
.lotus-inline-form>fieldset{display:grid;gap:16px;border:0;margin:0;padding:0;min-width:0}
.lotus-inline-form__footer{display:flex;justify-content:flex-end;gap:8px;padding-top:12px;border-top:1px solid var(--lotus-border)}
</style>
