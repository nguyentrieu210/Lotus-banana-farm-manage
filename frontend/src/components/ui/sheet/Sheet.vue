<script setup>
import {DialogRoot,DialogPortal,DialogOverlay,DialogContent,DialogTitle,DialogDescription,DialogClose} from 'reka-ui'
import LotusIcon from '../../LotusIcon.vue'
// Side panel for record details and advanced filters. Focus trap, Esc and return focus come from reka Dialog.
defineProps({open:Boolean,title:{type:String,required:true},description:String,side:{type:String,default:'right'},width:{type:String,default:'420px'}})
const emit=defineEmits(['update:open'])
</script>
<template>
 <DialogRoot :open="open" @update:open="emit('update:open',$event)">
  <DialogPortal>
   <DialogOverlay class="lotus-sheet-overlay"/>
   <DialogContent class="lotus-sheet" :data-side="side" :style="{width:'min('+width+', 100vw)'}">
    <header class="lotus-sheet__header">
     <div><DialogTitle class="lotus-sheet__title">{{title}}</DialogTitle><DialogDescription v-if="description" class="lotus-sheet__description">{{description}}</DialogDescription></div>
     <DialogClose class="lotus-sheet__close" :aria-label="'Đóng '+title"><LotusIcon name="x"/></DialogClose>
    </header>
    <div class="lotus-sheet__body"><slot/></div>
    <footer v-if="$slots.footer" class="lotus-sheet__footer"><slot name="footer"/></footer>
   </DialogContent>
  </DialogPortal>
 </DialogRoot>
</template>
<style>
.lotus-sheet-overlay{position:fixed;inset:0;z-index:2147481000;background:var(--lotus-backdrop);backdrop-filter:blur(2px)}
.lotus-sheet{position:fixed;top:0;bottom:0;z-index:2147481001;display:flex;flex-direction:column;background:var(--lotus-surface);color:var(--lotus-text);box-shadow:var(--lotus-shadow-lg);font-family:var(--lotus-font);outline:none}
.lotus-sheet[data-side=right]{right:0;border-left:1px solid var(--lotus-border)}
.lotus-sheet[data-side=left]{left:0;border-right:1px solid var(--lotus-border)}
.lotus-sheet[data-state=open][data-side=right]{animation:lotus-sheet-right 220ms var(--lotus-ease)}
.lotus-sheet[data-state=open][data-side=left]{animation:lotus-sheet-left 220ms var(--lotus-ease)}
.lotus-sheet__header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:16px 20px;border-bottom:1px solid var(--lotus-border)}
.lotus-sheet__title{margin:0;font-size:18px;font-weight:650;line-height:1.35}
.lotus-sheet__description{margin:4px 0 0;font-size:var(--lotus-text-md);color:var(--lotus-muted)}
.lotus-sheet__close{display:grid;place-items:center;width:32px;height:32px;border:0;border-radius:var(--lotus-radius-md);background:transparent;color:var(--lotus-muted);cursor:pointer}
.lotus-sheet__close:hover{background:var(--lotus-hover)}
.lotus-sheet__body{flex:1;overflow:auto;padding:16px 20px}
.lotus-sheet__footer{display:flex;justify-content:flex-end;gap:8px;padding:12px 20px;border-top:1px solid var(--lotus-border)}
@keyframes lotus-sheet-right{from{transform:translateX(24px);opacity:0}to{transform:none;opacity:1}}
@keyframes lotus-sheet-left{from{transform:translateX(-24px);opacity:0}to{transform:none;opacity:1}}
@media (prefers-reduced-motion:reduce){.lotus-sheet[data-state=open]{animation:none!important}}
</style>
