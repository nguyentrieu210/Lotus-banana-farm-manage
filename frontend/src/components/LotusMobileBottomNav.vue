<script setup>
import {Tabbar,TabbarItem} from 'vant'
defineProps({items:{type:Array,required:true},active:{type:String,required:true},hidden:Boolean,disabled:Boolean,label:{type:String,default:'Điều hướng Lotus'}})
const emit=defineEmits(['navigate'])
</script>
<template>
 <nav v-if="!hidden" class="lotus-pwa-bottom" :aria-label="label" :inert="disabled">
  <Tabbar :model-value="active" :fixed="true" :border="true" safe-area-inset-bottom>
   <TabbarItem v-for="item in items" :key="item.name||item.id" :name="item.name||item.id" :icon="item.icon" :aria-label="item.label" :title="item.label" @click="!disabled&&emit('navigate',item.name||item.id)"><span class="lotus-sr-only">{{item.label}}</span></TabbarItem>
  </Tabbar>
 </nav>
</template>
