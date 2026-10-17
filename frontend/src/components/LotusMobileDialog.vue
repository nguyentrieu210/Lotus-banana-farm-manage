<script setup>
import {ref,onMounted,onUnmounted} from 'vue'
import {Dialog} from 'vant'
const emit=defineEmits(['cancel'])
const visible=ref(false)
let returnFocus
function showModal(){returnFocus=document.activeElement;visible.value=true}
function close(){visible.value=false;returnFocus?.focus?.()}
function escape(event){if(visible.value&&event.key==='Escape'){event.preventDefault();emit('cancel',event)}}
onMounted(()=>document.addEventListener('keydown',escape))
onUnmounted(()=>document.removeEventListener('keydown',escape))
defineExpose({showModal,close,get open(){return visible.value}})
</script>
<template><Dialog v-model:show="visible" :show-confirm-button="false" :close-on-popstate="false" :close-on-click-overlay="false"><slot/></Dialog></template>
