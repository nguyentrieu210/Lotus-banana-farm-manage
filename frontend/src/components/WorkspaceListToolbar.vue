<script setup>
import {Button as UiButton} from './ui/button'
import {Input as UiInput} from './ui/input'
defineProps({modelValue:String,searchable:{type:Boolean,default:true},placeholder:{type:String,default:'Tìm kiếm…'},busy:Boolean})
defineEmits(['update:modelValue','refresh'])
</script>
<template><div class="workspace-list-toolbar"><div v-if="$slots.filters" class="workspace-list-filters"><slot name="filters"/></div><label v-if="searchable" class="workspace-list-search"><span class="sr-only">Tìm kiếm</span><UiInput :model-value="modelValue" :placeholder="placeholder" @update:model-value="$emit('update:modelValue',$event)" type="search"/></label><UiButton class="workspace-list-refresh" variant="outline" :disabled="busy" @click="$emit('refresh')">{{busy?'Đang tải…':'Làm mới'}}</UiButton><div class="workspace-list-actions"><slot/></div></div></template>