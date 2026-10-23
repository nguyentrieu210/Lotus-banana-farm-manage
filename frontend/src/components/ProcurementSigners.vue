<script setup>
import ProcurementField from './ProcurementField.vue'
import {watch} from 'vue'
const props=defineProps({mobile:Boolean,options:Object,modelValue:{type:Object,default:()=>({})}})
const emit=defineEmits(['update:modelValue'])
watch(()=>props.options,opts=>{const next={...props.modelValue};for(const s of opts?.steps?.slice(1)||[]){const choices=opts.candidates?.[s.key]||[];if(!choices.some(c=>c.user===next[s.key]))next[s.key]=choices.length===1?choices[0].user:opts.remembered?.[s.key]||''}emit('update:modelValue',next)},{immediate:true})
</script>
<template><fieldset class="procurement-signers"><legend>Người ký duyệt</legend><ProcurementField v-for="step in options?.steps?.slice(1)||[]" :key="step.key" :mobile="mobile" :label="step.title" :options="(options.candidates?.[step.key]||[]).map(c=>({value:c.user,label:c.name}))" :model-value="modelValue[step.key]||''" required @update:model-value="emit('update:modelValue',{...modelValue,[step.key]:$event})"/><p v-for="step in (options?.steps?.slice(1)||[]).filter(s=>!options.candidates?.[s.key]?.length)" :key="step.key" role="status">{{options.diagnostics?.[step.key]?.message}}</p></fieldset></template>
