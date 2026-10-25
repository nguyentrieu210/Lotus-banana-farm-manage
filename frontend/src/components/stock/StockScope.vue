<script setup>
import {computed} from 'vue'
import LotusField from '../form/LotusField.vue'
import {DateRangePicker} from '../ui/date-picker'
// Kho list scope in the toolbar: warehouse, company (only when the user has several) and an optional date range.
const props=defineProps({warehouse:String,company:String,warehouses:{type:Array,default:()=>[]},companies:{type:Array,default:()=>[]},from:String,to:String,dates:Boolean,disabled:Boolean,allWarehouses:{type:Boolean,default:true}})
const emit=defineEmits(['update:warehouse','update:company','update:from','update:to'])
const warehouseOptions=computed(()=>props.warehouses.map(w=>({value:w.name,label:w.warehouse_name||w.name})))
const companyOptions=computed(()=>props.companies.map(c=>({value:c.name,label:c.name})))
</script>
<template>
 <LotusField class="stock-scope-select" type="select" aria-label="Kho" :model-value="warehouse||''" :options="warehouseOptions" :empty-option="allWarehouses?'Tất cả kho được phân quyền':'Chọn kho'" :disabled="disabled||!company" @update:model-value="emit('update:warehouse',$event)"/>
 <LotusField v-if="companies.length>1" class="stock-scope-select" type="select" aria-label="Công ty" :model-value="company||''" :options="companyOptions" :empty-option="null" :disabled="disabled" @update:model-value="emit('update:company',$event)"/>
 <DateRangePicker v-if="dates" :from="from||''" :to="to||''" :disabled="disabled" @update:from="emit('update:from',$event)" @update:to="emit('update:to',$event)"/>
</template>
