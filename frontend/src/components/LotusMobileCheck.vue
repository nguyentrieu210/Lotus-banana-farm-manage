<script setup>
import {Checkbox} from 'vant'
defineProps({modelValue:Boolean,disabled:Boolean})
defineEmits(['update:modelValue'])
</script>
<template><Checkbox class="mobile-check" :model-value="modelValue" :disabled="disabled" @update:model-value="$emit('update:modelValue',$event)"><slot/></Checkbox></template>
