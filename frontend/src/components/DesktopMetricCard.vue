<script setup>
defineProps({label:{type:String,required:true},value:{type:[String,Number],default:'—'},unit:{type:String,default:''},description:{type:String,default:''},warning:{type:Boolean,default:false}})
</script>
<template>
<article class="lotus-metric-card" :class="{'lotus-metric-card--warning':warning}">
  <span class="lotus-metric-card__label">{{label}}</span>
  <strong class="lotus-metric-card__number">{{value}} <span v-if="unit">{{unit}}</span></strong>
  <small class="lotus-metric-card__description">{{description}}</small>
</article>
</template>
