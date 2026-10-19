<script setup>
import LotusIcon from './LotusIcon.vue'
// icon: a LotusIcon name; pass icon="" to hide it. Put next steps (Thêm…, Xóa bộ lọc) in the actions slot.
defineProps({title:{type:String,default:'Chưa có dữ liệu'},description:{type:String,default:''},icon:{type:String,default:'list'}})
</script>
<template>
<div class="lotus-empty-state" role="status">
  <div v-if="icon" class="lotus-empty-state__icon" aria-hidden="true"><LotusIcon :name="icon"/></div>
  <strong>{{title}}</strong>
  <p v-if="description">{{description}}</p>
  <div v-if="$slots.actions" class="lotus-empty-state__actions"><slot name="actions"/></div>
</div>
</template>
