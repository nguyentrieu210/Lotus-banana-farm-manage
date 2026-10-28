<script setup>
import {Button as UiButton} from './ui/button'
import {Input as UiInput} from './ui/input'
import LotusIcon from './LotusIcon.vue'
// List toolbar, same on every screen: row 1 = actions (Thêm mới… first, on the left); row 2 = filters · search · Làm mới,
// aligned on the bottom edge of the controls so labelled and unlabelled filters line up. Rows wrap instead of scrolling sideways.
// #tools sits at the right end of row 2: the list's table tools (Cột hiển thị · Xuất Excel) live there instead of on a row of their own.
defineProps({modelValue:String,searchable:{type:Boolean,default:true},placeholder:{type:String,default:'Tìm kiếm…'},busy:Boolean,refreshable:{type:Boolean,default:true},refreshDisabled:Boolean})
defineEmits(['update:modelValue','refresh'])
</script>
<template>
 <div class="workspace-list-toolbar">
  <div v-if="$slots.default" class="workspace-list-actions"><slot/></div>
  <div class="workspace-list-row">
   <div v-if="$slots.filters" class="workspace-list-filters"><slot name="filters"/></div>
   <label v-if="searchable" class="workspace-list-search"><span class="sr-only">Tìm kiếm</span><UiInput :model-value="modelValue" :placeholder="placeholder" type="search" @update:model-value="$emit('update:modelValue',$event)"/></label>
   <UiButton v-if="refreshable" class="workspace-list-refresh" variant="outline" :disabled="busy||refreshDisabled" @click="$emit('refresh')"><LotusIcon name="refresh"/>{{busy?'Đang tải…':'Làm mới'}}</UiButton>
   <div v-if="$slots.tools" class="workspace-list-tools"><slot name="tools"/></div>
  </div>
 </div>
</template>
