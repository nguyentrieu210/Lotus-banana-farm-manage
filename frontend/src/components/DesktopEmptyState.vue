<script setup>
defineProps({title:{type:String,default:'Chưa có dữ liệu'},description:{type:String,default:''},icon:{type:String,default:'○'}})
</script>
<template>
<div class="lotus-empty-state" role="status">
  <div class="lotus-empty-state__icon" aria-hidden="true">{{icon}}</div>
  <strong>{{title}}</strong>
  <p v-if="description">{{description}}</p>
  <div v-if="$slots.actions" class="lotus-empty-state__actions"><slot name="actions"/></div>
</div>
</template>
