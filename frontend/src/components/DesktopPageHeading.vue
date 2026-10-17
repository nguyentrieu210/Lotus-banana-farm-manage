<script setup>
defineProps({title:{type:String,required:true},description:{type:String,default:''},eyebrow:{type:String,default:''}})
</script>
<template>
<header class="lotus-page-heading">
  <div class="lotus-page-heading__text">
    <p v-if="eyebrow" class="lotus-page-heading__eyebrow">{{eyebrow}}</p>
    <h1>{{title}}</h1>
    <p v-if="description" class="lotus-page-heading__description">{{description}}</p>
  </div>
  <div v-if="$slots.actions" class="lotus-page-heading__actions"><slot name="actions"/></div>
</header>
</template>
