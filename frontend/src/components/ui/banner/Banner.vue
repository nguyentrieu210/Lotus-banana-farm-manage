<script setup>
import {computed,ref} from 'vue'
import LotusIcon from '../../LotusIcon.vue'
// In-page message in four tones plus neutral (spec 004, User Story 3): a locked period, missing data, offline, success.
// Danger messages are read out at once (role=alert); the others politely (role=status).
const props=defineProps({tone:{type:String,default:'info'},title:String,icon:String,dismissible:Boolean})
const emit=defineEmits(['dismiss'])
const open=ref(true)
const ICONS={info:'info',success:'check-circle',warning:'alert',danger:'alert',neutral:'info'}
const iconName=computed(()=>props.icon||ICONS[props.tone]||'info')
function dismiss(){open.value=false;emit('dismiss')}
</script>
<template>
 <div v-if="open" class="lotus-banner" :class="'lotus-banner--'+tone" :role="tone==='danger'?'alert':'status'">
  <LotusIcon :name="iconName"/>
  <div class="lotus-banner__body"><strong v-if="title" class="lotus-banner__title">{{title}}</strong><div v-if="$slots.default"><slot/></div><div v-if="$slots.actions" class="lotus-banner__actions"><slot name="actions"/></div></div>
  <button v-if="dismissible" type="button" class="lotus-banner__close" aria-label="Đóng thông báo" @click="dismiss"><LotusIcon name="x"/></button>
 </div>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-banner{--b-bg:var(--lotus-tone-info-soft);--b-fg:var(--lotus-tone-info-text);--b-bd:var(--lotus-tone-info-border);--b-accent:var(--lotus-tone-info-solid);
 display:flex;align-items:flex-start;gap:10px;min-width:0;padding:10px 12px;border:1px solid var(--b-bd);border-left:4px solid var(--b-accent);border-radius:var(--lotus-radius-md);
 background:var(--b-bg);color:var(--lotus-text);font-size:var(--lotus-text-md);line-height:var(--lotus-leading)}
.lotus-banner>.lotus-icon{flex:none;margin-top:1px;color:var(--b-fg)}
.lotus-banner__body{display:grid;flex:1;gap:2px;min-width:0}
.lotus-banner__title{color:var(--b-fg);font-weight:var(--lotus-weight-semibold)}
.lotus-banner__actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.lotus-banner__close{flex:none;display:grid;place-items:center;width:28px;height:28px;margin:-4px -4px -4px 0;border:0;border-radius:var(--lotus-radius-sm);background:transparent;color:var(--lotus-muted);cursor:pointer}
.lotus-banner__close:hover{background:var(--lotus-hover)}
.lotus-banner--success{--b-bg:var(--lotus-tone-success-soft);--b-fg:var(--lotus-tone-success-text);--b-bd:var(--lotus-tone-success-border);--b-accent:var(--lotus-tone-success-solid)}
.lotus-banner--warning{--b-bg:var(--lotus-tone-warning-soft);--b-fg:var(--lotus-tone-warning-text);--b-bd:var(--lotus-tone-warning-border);--b-accent:var(--lotus-warning-500)}
.lotus-banner--danger{--b-bg:var(--lotus-tone-danger-soft);--b-fg:var(--lotus-tone-danger-text);--b-bd:var(--lotus-tone-danger-border);--b-accent:var(--lotus-tone-danger-solid)}
.lotus-banner--neutral{--b-bg:var(--lotus-soft);--b-fg:var(--lotus-text-strong);--b-bd:var(--lotus-border);--b-accent:var(--lotus-border-strong)}
</style>
