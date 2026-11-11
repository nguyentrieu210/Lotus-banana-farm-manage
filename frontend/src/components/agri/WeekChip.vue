<script setup>
import {computed} from 'vue'
import {isoWeek,sameWeek,weekRange} from '../../agri-format.js'
// An ISO week (FR-032): "T46", marked when it is this week or a harvest week. Give year+week or a date.
const props=defineProps({year:Number,week:Number,date:String,today:String,harvest:Boolean,long:Boolean})
const value=computed(()=>props.date?isoWeek(props.date):props.year&&props.week?{year:props.year,week:props.week}:null)
const current=computed(()=>!!props.today&&sameWeek(isoWeek(props.today),value.value))
</script>
<template>
 <span v-if="value" class="lotus-week" :class="{'lotus-week--current':current,'lotus-week--harvest':harvest&&!current}" :title="'Tuần '+value.week+'/'+value.year+': '+weekRange(value)" :aria-label="'Tuần '+value.week+' năm '+value.year+(current?', tuần này':'')+(harvest?', tuần thu':'')">{{long?'Tuần '+value.week:'T'+value.week}}</span>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-week{display:inline-flex;align-items:baseline;gap:3px;padding:2px 7px;border-radius:var(--lotus-radius-sm);background:var(--lotus-sunken);color:var(--lotus-text-secondary);font-size:var(--lotus-text-sm);font-weight:var(--lotus-weight-semibold);font-variant-numeric:tabular-nums;white-space:nowrap}
.lotus-week--current{background:var(--lotus-tone-primary-soft);color:var(--lotus-tone-primary-text);box-shadow:inset 0 0 0 1px var(--lotus-tone-primary-border)}
.lotus-week--harvest{background:var(--lotus-tone-success-soft);color:var(--lotus-tone-success-text)}
</style>
