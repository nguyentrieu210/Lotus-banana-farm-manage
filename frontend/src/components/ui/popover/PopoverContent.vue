<script setup>
import {PopoverPortal,PopoverContent} from 'reka-ui'
// `to`: pass the enclosing <dialog> when the popover lives inside a modal (see ../portal-target.js).
defineProps({align:{type:String,default:'start'},side:{type:String,default:'bottom'},sideOffset:{type:Number,default:6},to:{type:null,default:'body'}})
</script>
<template><PopoverPortal :to="to"><PopoverContent class="lotus-popover" :align="align" :side="side" :side-offset="sideOffset" :collision-padding="8"><slot/></PopoverContent></PopoverPortal></template>
<style>
.lotus-popover{z-index:2147482000;max-width:calc(100vw - 16px);padding:12px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-lg);background:var(--lotus-surface);color:var(--lotus-text);box-shadow:var(--lotus-shadow-lg);font-family:var(--lotus-font);font-size:var(--lotus-text-md)}
.lotus-popover[data-state=open]{animation:lotus-popover-in var(--lotus-motion) var(--lotus-ease)}
@keyframes lotus-popover-in{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
</style>
