<script setup>
import LotusMobileInput from './LotusMobileInput.vue'
import LotusMobileButton from './LotusMobileButton.vue'
const props=defineProps({modelValue:{type:Object,required:true},saving:Boolean,online:{type:Boolean,default:true}})
const emit=defineEmits(['update:modelValue','submit'])
function patch(value){emit('update:modelValue',{...props.modelValue,...value})}
</script>
<template>
 <form class="lotus-supplier-form" @submit.prevent="emit('submit')"><fieldset class="mobile-form-fields" :disabled="saving">
  <LotusMobileInput label="Tên nhà cung cấp" :model-value="modelValue.name" :disabled="!!modelValue.supplier_id" required maxlength="140" @update:modelValue="patch({name:$event})"/>
  <LotusMobileInput label="Người liên hệ" :model-value="modelValue.contact" maxlength="140" placeholder="Tên người phụ trách" @update:modelValue="patch({contact:$event})"/>
  <LotusMobileInput label="Số điện thoại" :model-value="modelValue.phone" type="tel" maxlength="60" placeholder="Số điện thoại NCC" @update:modelValue="patch({phone:$event})"/>
  <LotusMobileInput label="Ghi chú" :model-value="modelValue.notes" type="textarea" :rows="3" maxlength="500" placeholder="Điều kiện giao hàng, lưu ý…" @update:modelValue="patch({notes:$event})"/>
  <LotusMobileButton type="submit" class="mobile-submit" :loading="saving" :disabled="saving||!online">Lưu nhà cung cấp</LotusMobileButton>
 </fieldset></form>
</template>
