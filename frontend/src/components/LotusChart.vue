<script setup>
import {computed,onMounted,onBeforeUnmount,ref,watch,nextTick} from 'vue'
import {init as initChart,use as useEcharts} from 'echarts/core'
import {BarChart,LineChart} from 'echarts/charts'
import {GridComponent,TooltipComponent,LegendComponent} from 'echarts/components'
import {CanvasRenderer} from 'echarts/renderers'
import {Button as UiButton} from './ui/button'
import {dark} from '../workspace'
useEcharts([BarChart,LineChart,GridComponent,TooltipComponent,LegendComponent,CanvasRenderer])
// Report chart: one value axis, at most 3 series in the fixed --lotus-chart-1..3 order, table view always available.
const props=defineProps({
 title:{type:String,required:true},
 kind:{type:String,default:'bar',validator:v=>['bar','line','hbar'].includes(v)},
 categories:{type:Array,default:()=>[]},
 series:{type:Array,default:()=>[]},
 unit:{type:String,default:''},
 decimals:{type:Number,default:0},
 empty:{type:String,default:'Chưa có dữ liệu trong kỳ này.'},
 height:{type:Number,default:260},
})
const target=ref(null),showTable=ref(false),noCanvas=ref(false)
let chart=null,observer=null
const shown=computed(()=>props.series.slice(0,3))
const hasData=computed(()=>props.categories.length>0&&shown.value.some(s=>s.data.some(v=>v!=null&&Number(v)!==0)))
const number=v=>v==null||Number.isNaN(Number(v))?'—':new Intl.NumberFormat('vi-VN',{maximumFractionDigits:props.decimals}).format(Number(v))
const withUnit=v=>number(v)+(props.unit&&v!=null?' '+props.unit:'')
const summary=computed(()=>shown.value.map(s=>s.name+': tổng '+withUnit(s.data.reduce((n,v)=>n+Number(v||0),0))).join('; '))
function render(){
 if(!target.value||!hasData.value||noCanvas.value){chart?.dispose();chart=null;return}
 // Without a usable canvas (old browser, test DOM) the numbers stay readable as a table.
 if(!chart){
  if(!document.createElement('canvas').getContext?.('2d')){noCanvas.value=true;return}
  chart=initChart(target.value,undefined,{renderer:'canvas'})
 }
 // Canvas needs concrete colours: read the theme tokens at render time.
 const css=getComputedStyle(target.value),token=name=>css.getPropertyValue(name).trim()
 const ink=token('--lotus-muted'),line=token('--lotus-border'),surface=token('--lotus-surface')
 const colors=[1,2,3].map(i=>token('--lotus-chart-'+i))
 const horizontal=props.kind==='hbar',isLine=props.kind==='line'
 const categoryAxis={type:'category',data:props.categories,axisLine:{lineStyle:{color:line}},axisTick:{show:false},axisLabel:{color:ink,fontSize:11,hideOverlap:true}}
 const valueAxis={type:'value',splitLine:{lineStyle:{color:line,type:[3,3]}},axisLabel:{color:ink,fontSize:11,formatter:v=>number(v)}}
 chart.setOption({
  animationDuration:200,backgroundColor:'transparent',color:colors,
  tooltip:{trigger:'axis',axisPointer:{type:isLine?'line':'shadow'},valueFormatter:withUnit,backgroundColor:surface,borderColor:line,textStyle:{color:token('--lotus-text'),fontSize:12}},
  legend:shown.value.length>1?{top:0,left:0,icon:'roundRect',itemWidth:10,itemHeight:10,textStyle:{color:ink,fontSize:12}}:undefined,
  grid:{top:shown.value.length>1?34:16,right:16,bottom:8,left:8},
  xAxis:horizontal?valueAxis:categoryAxis,yAxis:horizontal?{...categoryAxis,inverse:true}:valueAxis,
  series:shown.value.map(s=>isLine
   ?{name:s.name,type:'line',data:s.data,connectNulls:false,lineStyle:{width:2},symbol:'circle',symbolSize:8,showSymbol:s.data.length<=14,itemStyle:{borderColor:surface,borderWidth:2}}
   :{name:s.name,type:'bar',data:s.data,barMaxWidth:horizontal?18:28,barGap:'12%',itemStyle:{borderRadius:horizontal?[0,4,4,0]:[4,4,0,0],borderColor:surface,borderWidth:1}})
 },true)
}
onMounted(async()=>{await nextTick();render();if(typeof ResizeObserver!=='undefined'&&target.value){observer=new ResizeObserver(()=>chart?.resize());observer.observe(target.value)}})
watch(()=>[props.categories,props.series,props.kind,dark.value],()=>nextTick(render),{deep:true})
onBeforeUnmount(()=>{observer?.disconnect();chart?.dispose();chart=null})
</script>
<template>
<section class="lotus-chart-card" :aria-label="title">
 <header class="lotus-chart-head"><div><h3>{{title}}</h3><small v-if="unit" class="lotus-chart-unit">Đơn vị: {{unit}}</small></div><UiButton v-if="hasData&&!noCanvas" variant="ghost" size="sm" :aria-pressed="showTable?'true':'false'" @click="showTable=!showTable">{{showTable?'Xem biểu đồ':'Xem bảng số liệu'}}</UiButton></header>
 <p v-if="!hasData" class="lotus-chart-empty">{{empty}}</p>
 <template v-else>
  <div v-show="!showTable&&!noCanvas" ref="target" class="lotus-chart-canvas" :style="{height:height+'px'}" role="img" :aria-label="title+'. '+summary"/>
  <div v-if="showTable||noCanvas" class="lotus-chart-table"><table><thead><tr><th scope="col"></th><th v-for="s in shown" :key="s.name" scope="col">{{s.name}}{{unit?' ('+unit+')':''}}</th></tr></thead>
   <tbody><tr v-for="(label,i) in categories" :key="label+i"><th scope="row">{{label}}</th><td v-for="s in shown" :key="s.name">{{number(s.data[i])}}</td></tr></tbody></table></div>
 </template>
</section>
</template>
