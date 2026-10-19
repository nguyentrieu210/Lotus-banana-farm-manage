<script setup>
import {cn} from '@/lib/utils'
import {useAttrs} from 'vue'
defineOptions({inheritAttrs:false})
defineProps({modelValue:{type:[String,Number],default:''}})
const emit=defineEmits(['update:modelValue'])
const attrs=useAttrs()
function change(event){emit('update:modelValue',event.target.value);if(typeof attrs.onChange==='function')attrs.onChange(event)}
</script>
<template><select v-bind="{...$attrs,onChange:undefined}" :value="modelValue" :class="cn('h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring aria-[invalid=true]:border-destructive aria-[invalid=true]:focus-visible:ring-destructive disabled:opacity-50',$attrs.class)" @change="change"><slot/></select></template>
