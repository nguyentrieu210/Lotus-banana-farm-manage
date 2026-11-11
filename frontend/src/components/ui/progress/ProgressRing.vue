<script setup>
import {computed} from 'vue'
// Progress ring for a share at a glance (lots reported today, harvest of the week against the forecast).
const props=defineProps({value:{type:Number,default:0},max:{type:Number,default:100},size:{type:Number,default:48},stroke:{type:Number,default:5},tone:{type:String,default:'primary'},label:{type:String,required:true},valueText:String})
const pct=computed(()=>{const m=Number(props.max)||0;return m>0?Math.max(0,Math.min(100,Number(props.value||0)/m*100)):0})
const r=computed(()=>(props.size-props.stroke)/2)
const length=computed(()=>2*Math.PI*r.value)
const shown=computed(()=>props.valueText??Math.round(pct.value)+'%')
</script>
<template>
 <span class="lotus-ring" :class="'lotus-ring--'+tone" role="progressbar" :aria-label="label" :aria-valuenow="Math.round(pct)" aria-valuemin="0" aria-valuemax="100" :aria-valuetext="shown">
  <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" aria-hidden="true"><circle class="lotus-ring__track" :cx="size/2" :cy="size/2" :r="r" :stroke-width="stroke"/><circle class="lotus-ring__bar" :cx="size/2" :cy="size/2" :r="r" :stroke-width="stroke" :stroke-dasharray="length" :stroke-dashoffset="length*(1-pct/100)"/></svg>
  <span class="lotus-ring__text" aria-hidden="true">{{shown}}</span>
 </span>
</template>
