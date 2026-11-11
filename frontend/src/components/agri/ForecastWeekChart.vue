<script setup>
import {computed,ref} from 'vue'
import {isoWeek,sameWeek,weekRange,formatNumber,formatDelta} from '../../agri-format.js'
import {niceScale,linePath,bandPath} from '../../chart-scale.js'
// Weekly harvest (FR-035): actual bunches as bars, the forecast as a dashed line with its range as a band, this week
// marked. Inline SVG, no chart library, so it also loads fast on phones. Only the numbers given are drawn: a week with
// no actual has no bar (never a 0 bar). weeks: [{year, week, forecast?, actual?, low?, high?}] in time order.
const props=defineProps({weeks:{type:Array,required:true},today:String,unit:{type:String,default:'buồng'},label:{type:String,default:'Dự thu và thực tế theo tuần'},height:{type:Number,default:240}})
const W=720,M={top:18,right:14,bottom:30,left:54}
const plotW=W-M.left-M.right
const plotH=computed(()=>props.height-M.top-M.bottom)
const has=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))
const scale=computed(()=>niceScale(Math.max(0,...props.weeks.flatMap(w=>[w.forecast,w.actual,w.high].filter(has).map(Number))),4))
const band=computed(()=>plotW/Math.max(1,props.weeks.length))
const barW=computed(()=>Math.max(6,Math.min(30,band.value*0.56)))
const x=i=>M.left+band.value*(i+0.5)
const y=v=>M.top+plotH.value*(1-Number(v)/scale.value.max)
const base=computed(()=>M.top+plotH.value)
const nowIndex=computed(()=>props.today?props.weeks.findIndex(w=>sameWeek(w,isoWeek(props.today))):-1)
const forecastPoints=computed(()=>props.weeks.map((w,i)=>has(w.forecast)?[x(i),y(w.forecast)]:null))
const line=computed(()=>linePath(forecastPoints.value))
const area=computed(()=>bandPath(props.weeks.map((w,i)=>has(w.high)?[x(i),y(w.high)]:null),props.weeks.map((w,i)=>has(w.low)?[x(i),y(w.low)]:null)))
const showEvery=computed(()=>props.weeks.length>18?3:props.weeks.length>12?2:1)
const active=ref(-1)
const unitText=v=>formatNumber(v)+' '+props.unit
function gap(w){if(!has(w.actual)||!has(w.forecast)||!Number(w.forecast))return null;const d=Number(w.actual)-Number(w.forecast);return formatDelta(d)+' ('+formatDelta(d/Number(w.forecast)*100,{digits:1})+'%)'}
function describe(w){return ['Tuần '+w.week+'/'+w.year+' ('+weekRange(w)+')',has(w.forecast)?'dự thu '+unitText(w.forecast):'chưa có dự thu',has(w.actual)?'thực tế '+unitText(w.actual):'chưa có thực tế',gap(w)?'lệch '+gap(w):''].filter(Boolean).join(', ')}
const tip=computed(()=>{
 const i=active.value,w=props.weeks[i]
 if(!w)return null
 const top=Math.min(...[w.forecast,w.actual,w.high].filter(has).map(v=>y(v)),base.value)
 return {w,left:Math.min(86,Math.max(14,x(i)/W*100)),top:Math.max(8,top/props.height*100-2)}
})
const summary=computed(()=>{
 const withActual=props.weeks.filter(w=>has(w.actual)),withForecast=props.weeks.filter(w=>has(w.forecast))
 return props.label+': '+props.weeks.length+' tuần, '+withForecast.length+' tuần có dự thu, '+withActual.length+' tuần có thực tế.'
})
</script>
<template>
 <figure class="lotus-chart" style="margin:0">
  <div class="lotus-chart__plot">
   <svg :viewBox="`0 0 ${W} ${height}`" role="img" :aria-label="summary">
    <g aria-hidden="true">
     <g v-for="t in scale.ticks" :key="t"><line class="lotus-chart__grid" :x1="M.left" :x2="W-M.right" :y1="y(t)" :y2="y(t)"/><text class="lotus-chart__axis" :x="M.left-8" :y="y(t)+4" text-anchor="end">{{formatNumber(t)}}</text></g>
     <rect v-if="nowIndex>=0" :x="M.left+band*nowIndex" :y="M.top" :width="band" :height="plotH" class="lotus-chart__band" style="opacity:.35"/>
     <path v-if="area" class="lotus-chart__band" :d="area"/>
    </g>
    <g v-for="(w,i) in weeks" :key="w.year+'-'+w.week" class="lotus-chart__col" tabindex="0" :aria-label="describe(w)" @mouseenter="active=i" @mouseleave="active=-1" @focus="active=i" @blur="active=-1">
     <rect class="lotus-chart__hit" :x="M.left+band*i" :y="M.top" :width="band" :height="plotH"/>
     <rect v-if="has(w.actual)" class="lotus-chart__bar" :x="x(i)-barW/2" :y="y(w.actual)" :width="barW" :height="Math.max(0,base-y(w.actual))" rx="2"/>
    </g>
    <g aria-hidden="true">
     <line class="lotus-chart__base" :x1="M.left" :x2="W-M.right" :y1="base" :y2="base"/>
     <path v-if="line" class="lotus-chart__line" :d="line"/>
     <circle v-for="(p,i) in forecastPoints" v-show="p" :key="'p'+i" class="lotus-chart__point" :cx="p?.[0]" :cy="p?.[1]" r="3"/>
     <template v-if="nowIndex>=0"><line class="lotus-chart__now" :x1="x(nowIndex)" :x2="x(nowIndex)" :y1="M.top-6" :y2="base"/><text class="lotus-chart__now-label" :x="x(nowIndex)" :y="M.top-8" text-anchor="middle">Tuần này</text></template>
     <text v-for="(w,i) in weeks" v-show="i%showEvery===0||i===nowIndex" :key="'x'+i" class="lotus-chart__axis" :class="{'lotus-chart__axis--strong':i===nowIndex}" :x="x(i)" :y="base+18" text-anchor="middle">T{{w.week}}</text>
    </g>
   </svg>
   <div v-if="tip" class="lotus-chart__tip" :style="{left:tip.left+'%',top:tip.top+'%'}" aria-hidden="true">
    <strong>Tuần {{tip.w.week}} · {{weekRange(tip.w)}}</strong>
    <span>Dự thu<b>{{has(tip.w.forecast)?unitText(tip.w.forecast):'—'}}</b></span>
    <span v-if="has(tip.w.low)&&has(tip.w.high)">Khoảng<b>{{formatNumber(tip.w.low)}} – {{formatNumber(tip.w.high)}}</b></span>
    <span>Thực tế<b>{{has(tip.w.actual)?unitText(tip.w.actual):'—'}}</b></span>
    <span v-if="gap(tip.w)">Lệch<b>{{gap(tip.w)}}</b></span>
   </div>
  </div>
  <ul class="lotus-chart__legend" aria-hidden="true">
   <li class="lotus-chart__key"><i style="--key:var(--lotus-chart-actual)"/>Thực tế</li>
   <li class="lotus-chart__key"><i class="is-line" style="--key:var(--lotus-chart-forecast)"/>Dự thu</li>
   <li v-if="area" class="lotus-chart__key"><i class="is-band" style="--key:var(--lotus-chart-forecast-band)"/>Khoảng dự thu</li>
   <li class="lotus-chart__key">Đơn vị: {{unit}}</li>
  </ul>
  <figcaption class="lotus-sr-only">{{label}}</figcaption>
 </figure>
</template>
