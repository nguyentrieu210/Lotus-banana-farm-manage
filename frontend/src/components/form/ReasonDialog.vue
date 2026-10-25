<script setup>
import ModalForm from './ModalForm.vue'
import LotusField from './LotusField.vue'
// Pair with useReasonDialog(): <ReasonDialog :dialog="reason"/>.
const props=defineProps({dialog:{type:Object,required:true},submitLabel:{type:String,default:'Xác nhận'}})
function answer(){const value=String(props.dialog.text.value||'').trim();if(value)props.dialog.finish(value)}
</script>
<template>
 <ModalForm :model-value="dialog.open.value" :title="dialog.title.value" width="520px" :submit-label="submitLabel" :submit-disabled="!String(dialog.text.value||'').trim()" @update:model-value="value=>!value&&dialog.finish(null)" @submit="answer">
  <LotusField v-model="dialog.text.value" :label="dialog.label.value" type="textarea" required maxlength="500" autofocus/>
 </ModalForm>
</template>
