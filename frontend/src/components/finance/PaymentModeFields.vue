<script setup>
import LotusField from '../form/LotusField.vue'
// "Hình thức · Ngày · Số ủy nhiệm chi / giao dịch" used by every payment and receipt voucher. Place inside a FormGrid.
defineProps({mode:String,date:String,reference:String,modes:{type:Array,default:()=>[{value:'cash',label:'Tiền mặt'},{value:'bank',label:'Chuyển khoản'}]},dateLabel:{type:String,default:'Ngày chi'},referenceLabel:{type:String,default:'Số ủy nhiệm chi / giao dịch'},referenceRequired:{type:Boolean,default:true}})
const emit=defineEmits(['update:mode','update:date','update:reference'])
</script>
<template>
 <LotusField :model-value="mode" label="Hình thức" :options="modes" :searchable="false" :empty-option="null" @update:model-value="emit('update:mode',$event)"/>
 <LotusField :model-value="date" :label="dateLabel" type="date" required @update:model-value="emit('update:date',$event)"/>
 <LotusField v-if="mode==='bank'" :model-value="reference" :label="referenceLabel" :required="referenceRequired" @update:model-value="emit('update:reference',$event)"/>
</template>
