<script setup>
import {nextTick,onActivated,onBeforeUnmount,onDeactivated,onMounted,ref,watch} from 'vue'
import {Button as UiButton} from './ui/button'
import LotusIcon from './LotusIcon.vue'
import {dismissOnBackdrop} from '../dialogs'
// The one desktop dialog. Two ways to use it:
// - v-model + title: standard header ("Đóng") and padded body, teleported to <body>.
// - bare: renders in place with the caller's own header/markup and classes, driven like a native <dialog>
//   through a template ref (showModal(), close(), .open) — for existing forms whose CSS is scoped to their screen.
// Both: Esc and backdrop clicks are ignored while `busy`, and an open dialog closes when its KeepAlive screen is hidden.
defineOptions({inheritAttrs:false})
const props=defineProps({modelValue:{type:Boolean,default:undefined},title:{type:String,required:true},busy:Boolean,width:{type:String,default:'960px'},bare:Boolean})
const emit=defineEmits(['update:modelValue','cancel','close'])
const dialog=ref(null)
let inactive=false
const controlled=()=>props.modelValue!==undefined
async function sync(){await nextTick();if(!controlled()||!dialog.value||inactive)return;if(props.modelValue&&!dialog.value.open)dialog.value.showModal();else if(!props.modelValue&&dialog.value.open)dialog.value.close()}
function requestClose(){if(props.busy)return;if(controlled())emit('update:modelValue',false);else dialog.value?.close()}
function cancel(event){emit('cancel',event);const kept=event.defaultPrevented;event.preventDefault();if(!kept)requestClose()}
watch(()=>props.modelValue,sync)
onMounted(sync)
onActivated(()=>{inactive=false;sync()})
onDeactivated(()=>{inactive=true;dialog.value?.close()})
onBeforeUnmount(()=>{inactive=true;dialog.value?.close()})
function closed(event){emit('close',event);if(!inactive&&controlled()&&props.modelValue)emit('update:modelValue',false)}
defineExpose({showModal(){if(!dialog.value?.open)dialog.value?.showModal()},close(){dialog.value?.close()},get open(){return !!dialog.value?.open},get el(){return dialog.value}})
</script>
<template>
 <dialog v-if="bare" ref="dialog" v-bind="$attrs" class="workspace-modal workspace-modal--bare lotus-ui" :aria-label="$attrs['aria-label']||title" @close="closed" @cancel="cancel" @click="dismissOnBackdrop($event,busy)"><slot/></dialog>
 <Teleport v-else to="body"><dialog ref="dialog" v-bind="$attrs" class="workspace-modal lotus-ui" :style="{width:'min('+width+', calc(100vw - 24px))'}" :aria-label="title" @close="closed" @cancel="cancel" @click="dismissOnBackdrop($event,busy)">
  <header class="workspace-modal__header"><h2>{{title}}</h2><UiButton type="button" variant="outline" :disabled="busy" :aria-label="'Đóng '+title" @click="requestClose"><LotusIcon name="x"/>Đóng</UiButton></header>
  <div class="workspace-modal__body" :aria-busy="busy"><fieldset :disabled="busy"><slot/></fieldset></div>
 </dialog></Teleport>
</template>
