<script setup>
import {computed} from 'vue'
import ProcurementField from './ProcurementField.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import {Button} from './ui/button'
const props=defineProps({modelValue:{type:Object,required:true},saving:Boolean,online:{type:Boolean,default:true},mobile:{type:Boolean,default:true},extended:Boolean,options:{type:Object,default:()=>({})}})
const emit=defineEmits(['update:modelValue','submit'])
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const opts=rows=>(rows||[]).map(r=>({value:r.name,label:r.name}))
function patch(value){emit('update:modelValue',{...props.modelValue,...value})}
</script>
<template>
 <form class="lotus-supplier-form" @submit.prevent="emit('submit')"><fieldset class="mobile-form-fields" :disabled="saving">
 <div class="procurement-fields">
  <ProcurementField :mobile="mobile" label="Tên nhà cung cấp" :model-value="modelValue.name" :disabled="!!modelValue.supplier_id" required maxlength="140" @update:model-value="patch({name:$event})"/>
  <template v-if="extended">
   <ProcurementField :mobile="mobile" v-model="modelValue.type" label="Loại NCC" :options="[{value:'Company',label:'Doanh nghiệp'},{value:'Individual',label:'Cá nhân'},{value:'Partnership',label:'Hợp danh'}]" :searchable="false" required/>
   <ProcurementField :mobile="mobile" v-model="modelValue.group" label="Nhóm NCC" :options="opts(options.supplier_groups)" required/>
   <ProcurementField :mobile="mobile" v-model="modelValue.tax_id" label="Mã số thuế"/>
  </template>
  <ProcurementField :mobile="mobile" label="Người liên hệ" :model-value="modelValue.contact" maxlength="140" placeholder="Tên người phụ trách" @update:model-value="patch({contact:$event})"/>
  <ProcurementField :mobile="mobile" label="Số điện thoại" :model-value="modelValue.phone" type="tel" maxlength="60" placeholder="Số điện thoại NCC" @update:model-value="patch({phone:$event})"/>
  <template v-if="extended">
   <ProcurementField :mobile="mobile" v-model="modelValue.email" label="Email" type="email"/>
   <ProcurementField :mobile="mobile" v-model="modelValue.address_line1" label="Địa chỉ"/>
   <ProcurementField :mobile="mobile" v-model="modelValue.address_line2" label="Địa chỉ bổ sung"/>
   <ProcurementField :mobile="mobile" v-model="modelValue.city" label="Tỉnh / thành phố" :required="!!modelValue.address_line1"/>
   <ProcurementField :mobile="mobile" v-model="modelValue.country" label="Quốc gia" :options="opts(options.countries)" required/>
   <ProcurementField :mobile="mobile" v-model="modelValue.payment_terms" label="Điều khoản thanh toán" :options="[{value:'',label:'Chưa đặt'},...opts(options.payment_terms)]"/>
   <ProcurementField :mobile="mobile" :model-value="String(modelValue.disabled||0)" label="Trạng thái" :options="[{value:'0',label:'Đang dùng'},{value:'1',label:'Ngừng dùng'}]" :searchable="false" @update:model-value="patch({disabled:Number($event)})"/>
  </template>
  <ProcurementField :mobile="mobile" label="Ghi chú" :model-value="modelValue.notes" type="textarea" :rows="3" maxlength="500" placeholder="Điều kiện giao hàng, lưu ý…" @update:model-value="patch({notes:$event})"/>
  <template v-if="extended&&options.can_bank">
   <ProcurementField :mobile="mobile" v-model="modelValue.bank" label="Ngân hàng NCC" :options="opts(options.banks)" :required="!!modelValue.bank_account_no"/>
   <ProcurementField :mobile="mobile" v-model="modelValue.bank_account_no" label="Số tài khoản NCC"/>
   <ProcurementField :mobile="mobile" v-model="modelValue.bank_account_name" label="Chủ tài khoản NCC"/>
  </template>
 </div>
 <component :is="button" type="submit" class="mobile-submit" :disabled="saving||!online">Lưu nhà cung cấp</component>
 </fieldset></form>
</template>
