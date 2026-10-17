<script setup>
import {NavBar,Icon} from 'vant'
defineProps({title:{type:String,required:true},back:Boolean,disabled:Boolean,logo:{type:Boolean,default:true}})
const emit=defineEmits(['back'])
</script>
<template>
 <header class="lotus-pwa-header">
  <NavBar :border="false">
   <template #left>
    <div class="lotus-pwa-header-title">
     <button v-if="back" class="lotus-pwa-back" type="button" aria-label="Quay lại" :disabled="disabled" @click="emit('back')"><Icon name="arrow-left"/></button>
     <span v-if="logo" class="lotus-pwa-logo-frame"><img :src="'/assets/lotus_farm/images/lotus-agritech-header-v2.png'" alt="Lotus Agritech" class="lotus-pwa-logo"/></span>
     <strong>{{title}}</strong>
    </div>
   </template>
   <template #right><slot name="right"/></template>
  </NavBar>
 </header>
</template>
