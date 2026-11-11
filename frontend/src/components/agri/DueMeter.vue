<script setup>
import {computed} from 'vue'
import LotusIcon from '../LotusIcon.vue'
import {dueState} from '../../ui-status.js'
import {shortDate} from '../../agri-format.js'
// How far a care round is from its due date (FR-033): "Còn 3 ngày", "Đến hạn hôm nay", "Quá 2 ngày", the date,
// and a bar filled by the share of the cycle already used. cycle = days between two rounds.
const props=defineProps({due:{type:String,required:true},today:{type:String,required:true},cycle:{type:Number,default:0},soon:{type:Number,default:2},label:String})
const state=computed(()=>dueState(props.due,props.today,{soon:props.soon}))
const pct=computed(()=>{
 const s=state.value
 if(!s)return 0
 if(s.kind==='overdue')return 100
 if(!props.cycle)return s.kind==='due'?100:0
 return Math.max(0,Math.min(100,(props.cycle-s.days)/props.cycle*100))
})
</script>
<template>
 <div v-if="state" class="lotus-due" :data-state="state.kind">
  <span class="lotus-due__label"><LotusIcon :name="state.icon"/>{{label?label+': ':''}}{{state.label}}<span class="lotus-due__date">{{shortDate(due)}}</span></span>
  <div class="lotus-due__track" aria-hidden="true"><div class="lotus-due__fill" :style="{width:pct+'%'}"/></div>
 </div>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-due{--due-fill:var(--lotus-tone-success-solid);--due-fg:var(--lotus-text-secondary);display:grid;gap:4px;min-width:0}
.lotus-due__label{display:flex;align-items:center;gap:4px;color:var(--due-fg);font-size:var(--lotus-text-sm);font-weight:var(--lotus-weight-semibold);font-variant-numeric:tabular-nums}
.lotus-due__label .lotus-icon{width:14px;height:14px}
.lotus-due__date{margin-left:auto;color:var(--lotus-muted);font-weight:var(--lotus-weight-regular)}
.lotus-due__track{height:5px;overflow:hidden;border-radius:var(--lotus-radius-full);background:var(--lotus-sunken)}
.lotus-due__fill{height:100%;border-radius:inherit;background:var(--due-fill)}
.lotus-due[data-state="due"]{--due-fill:var(--lotus-warning-400);--due-fg:var(--lotus-tone-warning-text)}
.lotus-due[data-state="overdue"]{--due-fill:var(--lotus-tone-danger-solid);--due-fg:var(--lotus-tone-danger-text)}
</style>
