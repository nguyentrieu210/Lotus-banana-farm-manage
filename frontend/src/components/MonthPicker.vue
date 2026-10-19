<script setup>
import {computed} from 'vue'
import UiSelect from './ui/select/Select.vue'
// Month choice in Vietnamese ("Tháng 09/2026"); v-model is 'YYYY-MM'. Lists `count` months back from `max`.
const props=defineProps({modelValue:{type:String,default:''},max:{type:String,default:''},count:{type:Number,default:24},disabled:Boolean,label:{type:String,default:'Tháng'}})
const emit=defineEmits(['update:modelValue','change'])
const shift=(month,step)=>{const [y,m]=month.split('-').map(Number),d=new Date(y,m-1+step,1);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')}
const options=computed(()=>{
 const last=props.max||new Date().toISOString().slice(0,7)
 const list=Array.from({length:props.count},(_,i)=>shift(last,-i))
 if(props.modelValue&&!list.includes(props.modelValue))list.unshift(props.modelValue)
 return list.map(value=>({value,label:'Tháng '+value.slice(5)+'/'+value.slice(0,4)}))
})
function choose(value){emit('update:modelValue',value);emit('change',value)}
</script>
<template><UiSelect :model-value="modelValue" :aria-label="label" :disabled="disabled" @update:model-value="choose"><option v-for="o in options" :key="o.value" :value="o.value">{{o.label}}</option></UiSelect></template>
