<script setup>
import {ToastProvider,ToastRoot,ToastTitle,ToastDescription,ToastAction,ToastClose,ToastViewport} from 'reka-ui'
import LotusIcon from '../../LotusIcon.vue'
import {useToastState,dismissToast} from '../../../use-toast'
const state=useToastState()
function act(item){item.action?.run?.();dismissToast(item.id)}
</script>
<template>
 <ToastProvider label="Thông báo" swipe-direction="right">
  <ToastRoot v-for="item in state.items" :key="item.id" :open="item.open" :duration="item.duration" :type="item.tone==='error'?'foreground':'background'"
   class="lotus-toast" :data-tone="item.tone" @update:open="open=>!open&&dismissToast(item.id)">
   <div class="lotus-toast__body">
    <ToastTitle class="lotus-toast__title">{{item.title}}</ToastTitle>
    <ToastDescription v-if="item.description" class="lotus-toast__description">{{item.description}}</ToastDescription>
   </div>
   <ToastAction v-if="item.action" :alt-text="item.action.label" as-child><button type="button" class="lotus-toast__action" @click="act(item)">{{item.action.label}}</button></ToastAction>
   <ToastClose class="lotus-toast__close" aria-label="Đóng thông báo"><LotusIcon name="x"/></ToastClose>
  </ToastRoot>
  <ToastViewport class="lotus-toast-viewport" label="Thông báo ({hotkey})"/>
 </ToastProvider>
</template>
<style>
.lotus-toast-viewport{position:fixed;right:16px;bottom:16px;z-index:2147483000;display:flex;flex-direction:column;gap:var(--lotus-space-2);width:min(380px,calc(100vw - 32px));margin:0;padding:0;list-style:none;outline:none}
.lotus-toast{display:flex;align-items:flex-start;gap:var(--lotus-space-3);padding:12px 12px 12px 14px;border:1px solid var(--lotus-border);border-left:4px solid var(--lotus-info);border-radius:var(--lotus-radius-lg);background:var(--lotus-surface);color:var(--lotus-text);box-shadow:var(--lotus-shadow-lg);font-family:var(--lotus-font)}
.lotus-toast[data-tone=success]{border-left-color:var(--lotus-success)}
.lotus-toast[data-tone=error]{border-left-color:var(--lotus-danger)}
.lotus-toast__body{flex:1;min-width:0}
.lotus-toast__title{font-size:var(--lotus-text-base);font-weight:600;line-height:1.45}
.lotus-toast__description{margin-top:2px;font-size:var(--lotus-text-md);color:var(--lotus-muted);line-height:1.45}
.lotus-toast__action{flex-shrink:0;min-height:32px;padding:0 10px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);color:var(--lotus-primary-text);font:inherit;font-size:var(--lotus-text-md);font-weight:600;cursor:pointer}
.lotus-toast__close{flex-shrink:0;display:grid;place-items:center;width:28px;height:28px;border:0;border-radius:var(--lotus-radius-sm);background:transparent;color:var(--lotus-muted);cursor:pointer}
.lotus-toast__close .lotus-icon{width:16px;height:16px}
.lotus-toast :is(.lotus-toast__action,.lotus-toast__close):hover{background:var(--lotus-hover)}
.lotus-toast[data-state=open]{animation:lotus-toast-in var(--lotus-motion) var(--lotus-ease)}
.lotus-toast[data-state=closed]{animation:lotus-toast-out var(--lotus-motion) ease-in forwards}
.lotus-toast[data-swipe=move]{transform:translateX(var(--reka-toast-swipe-move-x))}
.lotus-toast[data-swipe=end]{animation:lotus-toast-out var(--lotus-motion) ease-out forwards}
@keyframes lotus-toast-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes lotus-toast-out{to{opacity:0;transform:translateX(24px)}}
</style>
