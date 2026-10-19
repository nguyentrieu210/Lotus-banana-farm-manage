<script setup>
import {ref} from 'vue'
defineProps({items:{type:Array,default:()=>[]},modelValue:String,label:{type:String,default:'Phân hệ'}})
const emit=defineEmits(['update:modelValue']);const nav=ref(null)
// WAI-ARIA tabs: one tab stop, arrows/Home/End move and activate.
function move(e){const b=[...nav.value.querySelectorAll('[role=tab]')],i=b.indexOf(e.target);let n;if(e.key==='ArrowRight')n=(i+1)%b.length;else if(e.key==='ArrowLeft')n=(i+b.length-1)%b.length;else if(e.key==='Home')n=0;else if(e.key==='End')n=b.length-1;else return;e.preventDefault();b[n]?.focus();b[n]?.click()}
</script>
<template><div ref="nav" class="workspace-tabs" role="tablist" :aria-label="label" @keydown="move"><button v-for="item in items" :key="item.id" type="button" role="tab" :class="{selected:modelValue===item.id}" :aria-selected="modelValue===item.id?'true':'false'" :tabindex="modelValue===item.id?0:-1" @click="emit('update:modelValue',item.id)">{{item.label}}</button></div></template>
