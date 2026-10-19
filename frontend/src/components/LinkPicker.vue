<script setup>
import {Combobox} from './ui/combobox'
// Kept for existing callers (StockApp, SchemaForm). Typed text stays the value: Frappe validates Link fields.
defineOptions({inheritAttrs:false})
defineProps({modelValue:{type:String,default:''},displayValue:{type:String,default:''},options:{type:Array,default:()=>[]},fetchOptions:Function,hideValues:Boolean,disabled:Boolean,readonly:Boolean,required:Boolean,placeholder:{type:String,default:'Chọn hoặc tìm…'}})
const emit=defineEmits(['update:modelValue','select','change'])
</script>
<template><Combobox v-bind="$attrs" class="link-picker" allow-custom :model-value="modelValue" :display-value="displayValue" :options="options" :fetch-options="fetchOptions" :hide-values="hideValues" :disabled="disabled" :readonly="readonly" :required="required" :placeholder="placeholder" @update:model-value="emit('update:modelValue',$event)" @select="emit('select',$event)" @change="emit('change',$event)"/></template>
