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
