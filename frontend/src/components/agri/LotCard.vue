<script setup>
import {computed} from 'vue'
import LotusIcon from '../LotusIcon.vue'
import {StatusChip} from '../ui/status-chip'
import RibbonChip from './RibbonChip.vue'
import QuarantineBadge from './QuarantineBadge.vue'
import {LOT_STATES} from '../../lot-states.js'
// One lot (FR-029): the same card on Hôm nay, Màu dây and Vòng chăm sóc, on desktop and phone.
// lot: {code, zone, state, stateLabel?, status?, line?, todo?, ribbons:[{code,label?,week?,count?}], quarantineUntil?, facts:[text]}
// state picks the left accent and the chip; status (a raw document state) wins for the chip when given.
const props=defineProps({lot:{type:Object,required:true},today:{type:String,required:true},interactive:{type:Boolean,default:true},maxRibbons:{type:Number,default:4}})
const emit=defineEmits(['open'])
const meta=computed(()=>LOT_STATES[props.lot.state]||LOT_STATES.empty)
const ribbons=computed(()=>(props.lot.ribbons||[]).slice(0,props.maxRibbons))
const more=computed(()=>Math.max(0,(props.lot.ribbons||[]).length-props.maxRibbons))
const chipTone={empty:'neutral',entered:'info',sent:'info',confirmed:'success',ok:'success',due:'warning',overdue:'danger',quarantine:'danger'}
</script>
<template>
 <component :is="interactive?'button':'article'" class="lotus-lotcard" :data-state="lot.state||'empty'" :type="interactive?'button':undefined" :aria-label="interactive?'Lô '+lot.code+(lot.zone?' khu '+lot.zone:'')+': '+(lot.stateLabel||meta.label):undefined" @click="interactive&&emit('open',lot)">
  <div class="lotus-lotcard__head">
   <span class="lotus-lotcard__name"><span class="lotus-lotcard__code">Lô {{lot.code}}</span><span v-if="lot.zone" class="lotus-lotcard__zone">khu {{lot.zone}}</span></span>
   <StatusChip v-if="lot.status" :status="lot.status" :label="lot.stateLabel" size="sm"/>
   <StatusChip v-else :label="lot.stateLabel||meta.label" :tone="chipTone[lot.state]||'neutral'" :icon="meta.icon" size="sm"/>
  </div>
  <div v-if="lot.todo||lot.line" class="lotus-lotcard__line"><template v-if="lot.todo"><LotusIcon name="edit"/><span class="lotus-lotcard__todo">{{lot.todo}}</span></template><span v-if="lot.line">{{lot.line}}</span></div>
  <div v-if="ribbons.length" class="lotus-lotcard__ribbons"><RibbonChip v-for="r in ribbons" :key="r.code+'-'+(r.week||'')" :code="r.code" :label="r.label" :week="r.week" :count="r.count??null"/><span v-if="more" class="lotus-chip lotus-chip--bare lotus-chip--sm">+{{more}}</span></div>
  <div v-if="lot.quarantineUntil||lot.facts?.length" class="lotus-lotcard__facts"><QuarantineBadge v-if="lot.quarantineUntil" :until="lot.quarantineUntil" :today="today"/><span v-for="fact in lot.facts||[]" :key="fact">{{fact}}</span></div>
  <slot/>
 </component>
</template>
