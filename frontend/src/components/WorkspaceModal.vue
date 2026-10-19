<script setup>
import {nextTick,onActivated,onBeforeUnmount,onDeactivated,onMounted,ref,watch} from 'vue'
import {Button as UiButton} from './ui/button'
import {dismissOnBackdrop} from '../dialogs'
const props=defineProps({modelValue:Boolean,title:{type:String,required:true},busy:Boolean,width:{type:String,default:'960px'}})
const emit=defineEmits(['update:modelValue'])
const dialog=ref(null)
let inactive=false
async function sync(){await nextTick();if(!dialog.value||inactive)return;if(props.modelValue&&!dialog.value.open)dialog.value.showModal();else if(!props.modelValue&&dialog.value.open)dialog.value.close()}
function close(){if(!props.busy)emit('update:modelValue',false)}
watch(()=>props.modelValue,sync)
onMounted(sync)
onActivated(()=>{inactive=false;sync()})
onDeactivated(()=>{inactive=true;dialog.value?.close()})
onBeforeUnmount(()=>{inactive=true;dialog.value?.close()})
function closed(){if(!inactive&&props.modelValue)emit('update:modelValue',false)}
</script>
<template><Teleport to="body"><dialog ref="dialog" class="workspace-modal lotus-ui" :style="{width:'min('+width+', calc(100vw - 24px))'}" :aria-label="title" @close="closed" @cancel.prevent="close" @click="dismissOnBackdrop($event,busy)">
 <header class="workspace-modal__header"><h2>{{title}}</h2><UiButton type="button" variant="outline" :disabled="busy" :aria-label="'Đóng '+title" @click="close">Đóng ✕</UiButton></header>
 <div class="workspace-modal__body" :aria-busy="busy"><fieldset :disabled="busy"><slot/></fieldset></div>
</dialog></Teleport></template>
