<script setup>
import {Combobox} from './ui/combobox'
// Kept for existing callers (FarmWorkApp); the picker itself is ui/combobox.
defineProps({modelValue:{type:[String,Number],default:''},options:{type:Array,default:()=>[]},placeholder:{type:String,default:'Chọn…'},label:{type:String,required:true},disabled:Boolean})
const emit=defineEmits(['update:modelValue','change'])
</script>
<template><Combobox class="search-select" :model-value="modelValue" :options="options" :placeholder="placeholder" :label="label" :disabled="disabled" hide-values @update:model-value="emit('update:modelValue',$event)" @change="emit('change',$event)"/></template>
