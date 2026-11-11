<script setup>
import {StatusChip} from '../ui/status-chip'
import RibbonChip from './RibbonChip.vue'
import {formatNumber,shortDate} from '../../agri-format.js'
// A packhouse shift (ca xưởng, FR-036): bunches in, kg packed, boxes out, and where the bunches came from
// (lot and ribbon batch). shift: {date, name, team?, bunches?, kg?, boxes?, status?, statusLabel?, lines?:[text], sources:[{lot, ribbon, count}]}
// interactive: the card is a button that emits open (a list of shifts opening one in a dialog).
defineProps({shift:{type:Object,required:true},interactive:Boolean})
const emit=defineEmits(['open'])
const figure=v=>v===null||v===undefined||v===''?'—':formatNumber(v)
</script>
<template>
 <component :is="interactive?'button':'article'" class="lotus-shift" :type="interactive?'button':undefined" @click="interactive&&emit('open')">
  <span class="lotus-shift__head"><span class="lotus-shift__title"><strong>Ca {{shift.name}} · {{shortDate(shift.date)}}</strong><small v-if="shift.team">{{shift.team}}</small></span><StatusChip v-if="shift.status" :status="shift.status" :label="shift.statusLabel" size="sm"/></span>
  <dl class="lotus-shift__figures">
   <div><dt>Buồng vào</dt><dd>{{figure(shift.bunches)}}</dd></div>
   <div><dt>Thành phẩm (kg)</dt><dd>{{figure(shift.kg)}}</dd></div>
   <div><dt>Thùng</dt><dd>{{figure(shift.boxes)}}</dd></div>
  </dl>
  <span v-for="line in shift.lines||[]" :key="line" class="lotus-shift__line">{{line}}</span>
  <span v-if="shift.sources?.length" class="lotus-shift__sources" aria-label="Nguồn buồng"><RibbonChip v-for="s in shift.sources" :key="s.lot+s.ribbon" :code="s.ribbon" :label="'Lô '+s.lot" :count="s.count"/></span>
 </component>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-shift{display:grid;gap:12px;min-width:0;padding:var(--lotus-card-padding);border:1px solid var(--lotus-border);border-radius:var(--lotus-card-radius);background:var(--lotus-surface);box-shadow:var(--lotus-shadow-xs)}
.lotus-shift__head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
.lotus-shift__title{display:grid;gap:2px}
.lotus-shift__title strong{color:var(--lotus-text-strong);font-size:var(--lotus-text-base)}
.lotus-shift__title small{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.lotus-shift__figures{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:0}
.lotus-shift__figures>div{display:grid;gap:1px;padding:8px 10px;border-radius:var(--lotus-radius-md);background:var(--lotus-soft)}
.lotus-shift__figures dt{color:var(--lotus-muted);font-size:var(--lotus-text-xs)}
.lotus-shift__figures dd{margin:0;color:var(--lotus-text-strong);font-size:var(--lotus-text-lg);font-weight:var(--lotus-weight-bold);font-variant-numeric:tabular-nums}
.lotus-shift__sources{display:flex;flex-wrap:wrap;gap:4px}
.lotus-shift__line{color:var(--lotus-text-secondary);font-size:var(--lotus-text-sm);font-variant-numeric:tabular-nums}
button.lotus-shift{width:100%;color:var(--lotus-text);font:inherit;text-align:left;cursor:pointer;transition:box-shadow var(--lotus-motion) var(--lotus-ease),border-color var(--lotus-motion) var(--lotus-ease)}
button.lotus-shift:hover{border-color:var(--lotus-border-strong);box-shadow:var(--lotus-shadow-md)}
button.lotus-shift:focus-visible{outline:none;box-shadow:var(--lotus-focus)}
</style>
