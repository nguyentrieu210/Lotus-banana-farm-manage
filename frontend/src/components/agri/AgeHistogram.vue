<script setup>
import {computed,ref} from 'vue'
import '../../lotus-kit-chart.css'
import {formatNumber} from '../../agri-format.js'
import {niceScale} from '../../chart-scale.js'
import RibbonDot from './RibbonDot.vue'
// Bunches still on the plants by age in weeks since cutting (FR-035). Ages inside the harvest window are amber
// and named in the legend. bins: [{age (weeks), count, ripe?, ribbon? (code of the batch at that age)}]
const props=defineProps({bins:{type:Array,required:true},unit:{type:String,default:'buồng'},label:{type:String,default:'Buồng trên cây theo tuổi'},height:{type:Number,default:220}})
const W=640,M={top:14,right:10,bottom:44,left:48}
const plotW=W-M.left-M.right
const plotH=computed(()=>props.height-M.top-M.bottom)
const scale=computed(()=>niceScale(Math.max(0,...props.bins.map(b=>Number(b.count)||0)),4))
const band=computed(()=>plotW/Math.max(1,props.bins.length))
const barW=computed(()=>Math.max(8,band.value*0.68))
const x=i=>M.left+band.value*(i+0.5)
const y=v=>M.top+plotH.value*(1-Number(v)/scale.value.max)
const base=computed(()=>M.top+plotH.value)
const ripeTotal=computed(()=>props.bins.filter(b=>b.ripe).reduce((s,b)=>s+(Number(b.count)||0),0))
const active=ref(-1)
const describe=b=>b.age+' tuần tuổi: '+formatNumber(b.count)+' '+props.unit+(b.ripe?', đến tuổi thu':'')
</script>
<template>
 <figure class="lotus-chart" style="margin:0">
  <div class="lotus-chart__plot">
   <svg :viewBox="`0 0 ${W} ${height}`" role="img" :aria-label="label+': '+bins.map(describe).join('; ')">
    <g aria-hidden="true"><g v-for="t in scale.ticks" :key="t"><line class="lotus-chart__grid" :x1="M.left" :x2="W-M.right" :y1="y(t)" :y2="y(t)"/><text class="lotus-chart__axis" :x="M.left-8" :y="y(t)+4" text-anchor="end">{{formatNumber(t)}}</text></g></g>
    <g v-for="(b,i) in bins" :key="b.age" class="lotus-chart__col" tabindex="0" :aria-label="describe(b)" @mouseenter="active=i" @mouseleave="active=-1" @focus="active=i" @blur="active=-1">
     <rect class="lotus-chart__hit" :x="M.left+band*i" :y="M.top" :width="band" :height="plotH"/>
     <rect class="lotus-chart__bar" :class="b.ripe?'lotus-chart__bar--ripe':'lotus-chart__bar--muted'" :x="x(i)-barW/2" :y="y(b.count||0)" :width="barW" :height="Math.max(0,base-y(b.count||0))" rx="2"/>
     <text v-if="active===i" class="lotus-chart__axis lotus-chart__axis--strong" :x="x(i)" :y="y(b.count||0)-5" text-anchor="middle">{{formatNumber(b.count)}}</text>
    </g>
    <g aria-hidden="true">
     <line class="lotus-chart__base" :x1="M.left" :x2="W-M.right" :y1="base" :y2="base"/>
     <text v-for="(b,i) in bins" :key="'x'+i" class="lotus-chart__axis" :class="{'lotus-chart__axis--strong':b.ripe}" :x="x(i)" :y="base+16" text-anchor="middle">{{b.age}}</text>
     <text class="lotus-chart__axis" :x="M.left+plotW/2" :y="height-4" text-anchor="middle">Tuần tuổi (từ ngày cắt bắp)</text>
    </g>
   </svg>
   <div class="lotus-weekstrip__mark" style="justify-content:space-around;padding:0 10px 0 48px;height:12px" aria-hidden="true"><span v-for="(b,i) in bins" :key="'r'+i" style="flex:1;display:flex;justify-content:center"><RibbonDot v-if="b.ribbon" :code="b.ribbon" decorative/></span></div>
  </div>
  <ul class="lotus-chart__legend" aria-hidden="true">
   <li class="lotus-chart__key"><i style="--key:var(--lotus-seq-3)"/>Đang nuôi</li>
   <li class="lotus-chart__key"><i style="--key:var(--lotus-warning-400)"/>Đến tuổi thu <b class="lotus-num">{{formatNumber(ripeTotal)}}</b>&nbsp;{{unit}}</li>
  </ul>
  <figcaption class="lotus-sr-only">{{label}}</figcaption>
 </figure>
</template>
