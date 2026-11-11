<script setup>
import LotusIcon from '../../LotusIcon.vue'
// Events in time order (spec 004, FR-036): the life of a lot, the history of a document.
// items: [{title, time?, text?, tone?: 'success'|'warning'|'danger'|'info'|'primary', icon?}]
defineProps({items:{type:Array,required:true},label:{type:String,default:'Dòng thời gian'}})
</script>
<template>
 <ol class="lotus-timeline" :aria-label="label">
  <li v-for="(item,index) in items" :key="index" class="lotus-timeline__item" :class="item.tone?'lotus-timeline__item--'+item.tone:''">
   <span class="lotus-timeline__dot" aria-hidden="true"><LotusIcon :name="item.icon||'dot'"/></span>
   <div><div class="lotus-timeline__head"><span class="lotus-timeline__title">{{item.title}}</span><time v-if="item.time" class="lotus-timeline__time">{{item.time}}</time></div><p v-if="item.text" class="lotus-timeline__text">{{item.text}}</p><slot name="item" :item="item"/></div>
  </li>
 </ol>
</template>
