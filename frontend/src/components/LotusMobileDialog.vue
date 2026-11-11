<script setup>
import {ref,nextTick,onMounted,onUnmounted,useId,getCurrentInstance} from 'vue'
import {Dialog} from 'vant'
const emit=defineEmits(['cancel'])
const visible=ref(false),body=ref(null),titleId=useId()+'-title',host=ref('')
const instance=getCurrentInstance()
// Screen modifiers whose phone rules must keep reaching the dialog once it is teleported out of the screen.
const HOST_CLASSES=['procurement-workspace--mobile']
let returnFocus
// Name the dialog after its first heading so screen readers announce it.
function labelDialog(){const heading=body.value?.querySelector('h1,h2,h3'),dialog=body.value?.closest('[role="dialog"]');if(!heading||!dialog)return;heading.id||=titleId;dialog.setAttribute('aria-labelledby',heading.id)}
// The teleport leaves its anchor where the dialog is declared: read the screen's modifiers from there.
function hostClasses(){const anchor=instance?.vnode?.el,from=anchor?.parentElement||anchor?.parentNode;return HOST_CLASSES.filter(name=>from?.closest?.('.'+name)).join(' ')}
async function showModal(){returnFocus=document.activeElement;host.value=hostClasses();visible.value=true;await nextTick();labelDialog()}
function close(){visible.value=false;returnFocus?.focus?.()}
function escape(event){if(visible.value&&event.key==='Escape'){event.preventDefault();emit('cancel',event)}}
onMounted(()=>document.addEventListener('keydown',escape))
onUnmounted(()=>document.removeEventListener('keydown',escape))
defineExpose({showModal,close,get open(){return visible.value}})
</script>
<!-- teleport: a confirmation opened from inside a sheet or the header (Chờ tôi ký) must sit above every open popup;
     left in place it stays in the header's stacking context, under the sheet, and the person cannot tap it.
     Outside .lotus-pwa-shell, the class lotus-pwa-dialog carries the shell's form rules (mobile-ui.css): 16px inputs so
     an iPhone does not zoom, border-box, focus ring, wrapping buttons. -->
<template><Dialog v-model:show="visible" teleport="body" :class="['lotus-pwa-dialog',host]" :show-confirm-button="false" :close-on-popstate="false" :close-on-click-overlay="false"><div ref="body" class="lotus-pwa-dialog-body"><slot/></div></Dialog></template>
<style>.lotus-pwa-dialog-body{display:contents}.lotus-pwa-dialog{font-family:var(--lotus-font);color:var(--lotus-pwa-ink);line-height:1.5}</style>
