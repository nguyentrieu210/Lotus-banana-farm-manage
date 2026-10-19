<script setup>
import {TooltipProvider,TooltipRoot,TooltipTrigger,TooltipPortal,TooltipContent} from 'reka-ui'
// <Tooltip content="Thu gọn thanh bên"><UiButton size="icon" aria-label="Thu gọn thanh bên">…</UiButton></Tooltip>
// The trigger keeps its own aria-label; the tooltip is a visual hint for mouse and keyboard focus.
defineProps({content:{type:String,required:true},side:{type:String,default:'bottom'}})
</script>
<template><TooltipProvider :delay-duration="400"><TooltipRoot><TooltipTrigger as-child><slot/></TooltipTrigger><TooltipPortal><TooltipContent class="lotus-tooltip" :side="side" :side-offset="6">{{content}}</TooltipContent></TooltipPortal></TooltipRoot></TooltipProvider></template>
<style>
.lotus-tooltip{z-index:2147482500;max-width:260px;padding:5px 9px;border-radius:var(--lotus-radius-sm);background:var(--lotus-neutral-900);color:#fff;font-family:var(--lotus-font);font-size:var(--lotus-text-sm);line-height:1.4;box-shadow:var(--lotus-shadow-md)}
:root.dark .lotus-tooltip{background:var(--lotus-neutral-100);color:var(--lotus-neutral-900)}
.lotus-tooltip[data-state=delayed-open]{animation:lotus-tooltip-in var(--lotus-motion) var(--lotus-ease)}
@keyframes lotus-tooltip-in{from{opacity:0;transform:translateY(-2px)}to{opacity:1;transform:none}}
</style>
