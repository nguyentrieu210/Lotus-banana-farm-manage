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
