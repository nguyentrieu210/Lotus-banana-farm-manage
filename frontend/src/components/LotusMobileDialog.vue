<script setup>
import {ref,nextTick,onMounted,onUnmounted,useId} from 'vue'
import {Dialog} from 'vant'
const emit=defineEmits(['cancel'])
const visible=ref(false),body=ref(null),titleId=useId()+'-title'
let returnFocus
// Name the dialog after its first heading so screen readers announce it.
function labelDialog(){const heading=body.value?.querySelector('h1,h2,h3'),dialog=body.value?.closest('[role="dialog"]');if(!heading||!dialog)return;heading.id||=titleId;dialog.setAttribute('aria-labelledby',heading.id)}
async function showModal(){returnFocus=document.activeElement;visible.value=true;await nextTick();labelDialog()}
function close(){visible.value=false;returnFocus?.focus?.()}
function escape(event){if(visible.value&&event.key==='Escape'){event.preventDefault();emit('cancel',event)}}
onMounted(()=>document.addEventListener('keydown',escape))
onUnmounted(()=>document.removeEventListener('keydown',escape))
defineExpose({showModal,close,get open(){return visible.value}})
</script>
<template><Dialog v-model:show="visible" :show-confirm-button="false" :close-on-popstate="false" :close-on-click-overlay="false"><div ref="body" class="lotus-pwa-dialog-body"><slot/></div></Dialog></template>
<style>.lotus-pwa-dialog-body{display:contents}</style>
