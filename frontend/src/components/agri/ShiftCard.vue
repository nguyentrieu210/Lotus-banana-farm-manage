<script setup>
import {StatusChip} from '../ui/status-chip'
import RibbonChip from './RibbonChip.vue'
import {formatNumber,shortDate} from '../../agri-format.js'
// A packhouse shift (ca xưởng, FR-036): bunches in, kg packed, boxes out, and where the bunches came from
// (lot and ribbon batch). shift: {date, name, team?, bunches?, kg?, boxes?, status?, statusLabel?, sources:[{lot, ribbon, count}]}
defineProps({shift:{type:Object,required:true}})
const figure=v=>v===null||v===undefined||v===''?'—':formatNumber(v)
</script>
<template>
 <article class="lotus-shift">
  <div class="lotus-shift__head"><div class="lotus-shift__title"><strong>Ca {{shift.name}} · {{shortDate(shift.date)}}</strong><small v-if="shift.team">{{shift.team}}</small></div><StatusChip v-if="shift.status" :status="shift.status" :label="shift.statusLabel" size="sm"/></div>
  <dl class="lotus-shift__figures">
   <div><dt>Buồng vào</dt><dd>{{figure(shift.bunches)}}</dd></div>
   <div><dt>Thành phẩm (kg)</dt><dd>{{figure(shift.kg)}}</dd></div>
   <div><dt>Thùng</dt><dd>{{figure(shift.boxes)}}</dd></div>
  </dl>
  <div v-if="shift.sources?.length" class="lotus-shift__sources" aria-label="Nguồn buồng"><RibbonChip v-for="s in shift.sources" :key="s.lot+s.ribbon" :code="s.ribbon" :label="'Lô '+s.lot" :count="s.count"/></div>
 </article>
</template>
