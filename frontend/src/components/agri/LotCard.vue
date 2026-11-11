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

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-lotcard{--lot-accent:var(--lotus-border-strong);position:relative;display:grid;gap:8px;width:100%;min-width:0;padding:12px 14px 12px 16px;border:1px solid var(--lotus-border);border-radius:var(--lotus-card-radius);background:var(--lotus-surface);box-shadow:var(--lotus-shadow-xs);color:var(--lotus-text);font:inherit;text-align:left;overflow:hidden;transition:box-shadow var(--lotus-motion) var(--lotus-ease),border-color var(--lotus-motion) var(--lotus-ease)}
.lotus-lotcard::before{content:"";position:absolute;inset:0 auto 0 0;width:4px;background:var(--lot-accent)}
button.lotus-lotcard{cursor:pointer}
button.lotus-lotcard:hover{border-color:var(--lotus-border-strong);box-shadow:var(--lotus-shadow-md)}
button.lotus-lotcard:focus-visible{outline:none;box-shadow:var(--lotus-focus)}
.lotus-lotcard__head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;min-width:0}
.lotus-lotcard__name{display:flex;align-items:baseline;gap:6px;min-width:0}
.lotus-lotcard__code{color:var(--lotus-text-strong);font-size:var(--lotus-text-lg);font-weight:var(--lotus-weight-bold);letter-spacing:-.01em;white-space:nowrap}
.lotus-lotcard__zone{color:var(--lotus-muted);font-size:var(--lotus-text-sm);white-space:nowrap}
.lotus-lotcard__line{display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;min-width:0;color:var(--lotus-text-secondary);font-size:var(--lotus-text-md);line-height:var(--lotus-leading-snug)}
.lotus-lotcard__line .lotus-icon{width:15px;height:15px;color:var(--lotus-muted)}
.lotus-lotcard__todo{color:var(--lotus-primary-text);font-weight:var(--lotus-weight-semibold)}
.lotus-lotcard__ribbons{display:flex;flex-wrap:wrap;gap:4px}
.lotus-lotcard__facts{display:flex;flex-wrap:wrap;gap:2px 12px;color:var(--lotus-muted);font-size:var(--lotus-text-sm);font-variant-numeric:tabular-nums}
.lotus-lotcard[data-state="entered"]{--lot-accent:var(--lotus-info-300)}
.lotus-lotcard[data-state="sent"]{--lot-accent:var(--lotus-lot-sent)}
.lotus-lotcard[data-state="confirmed"]{--lot-accent:var(--lotus-lot-confirmed)}
.lotus-lotcard[data-state="due"]{--lot-accent:var(--lotus-warning-400)}
.lotus-lotcard[data-state="overdue"],.lotus-lotcard[data-state="quarantine"]{--lot-accent:var(--lotus-tone-danger-solid)}
.lotus-lotcard[data-state="empty"]{--lot-accent:var(--lotus-border-strong)}
.lotus-lotcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;align-items:start}
</style>
