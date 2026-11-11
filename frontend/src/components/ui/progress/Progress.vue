<script setup>
import {computed} from 'vue'
// Progress bar (spec 004, User Story 3 and the table progress cell): value of max, a label and the value as text.
// inline: bar and value on one line (table cells, lot cards).
const props=defineProps({value:{type:Number,default:0},max:{type:Number,default:100},label:String,valueText:String,tone:{type:String,default:'primary'},inline:Boolean})
const pct=computed(()=>{const m=Number(props.max)||0;return m>0?Math.max(0,Math.min(100,Number(props.value||0)/m*100)):0})
const shown=computed(()=>props.valueText??Math.round(pct.value)+'%')
</script>
<template>
 <div class="lotus-progress" :class="['lotus-progress--'+tone,{'lotus-progress--inline':inline}]" role="progressbar" :aria-valuenow="Math.round(pct)" aria-valuemin="0" aria-valuemax="100" :aria-valuetext="shown" :aria-label="label||undefined">
  <template v-if="inline"><div class="lotus-progress__track"><div class="lotus-progress__bar" :style="{width:pct+'%'}"/></div><div class="lotus-progress__meta"><strong>{{shown}}</strong></div></template>
  <template v-else><div class="lotus-progress__meta"><span>{{label}}</span><strong>{{shown}}</strong></div><div class="lotus-progress__track"><div class="lotus-progress__bar" :style="{width:pct+'%'}"/></div></template>
 </div>
</template>
