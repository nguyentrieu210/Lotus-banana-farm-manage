<script setup>
import {computed,onMounted,onBeforeUnmount,ref,watch,nextTick} from 'vue'
import {init as initChart,use as useEcharts} from 'echarts/core'
import {BarChart,LineChart,PieChart} from 'echarts/charts'
import {GridComponent,TooltipComponent,LegendComponent} from 'echarts/components'
import {CanvasRenderer} from 'echarts/renderers'
import {Button as UiButton} from './ui/button'
import DataTable from './DataTable.vue'
import {uiMode} from '../ui-mode'
useEcharts([BarChart,LineChart,PieChart,GridComponent,TooltipComponent,LegendComponent,CanvasRenderer])
// Report chart: one value axis, at most 3 series in the fixed --lotus-chart-1..3 order, table view always available.
const props=defineProps({
 title:{type:String,required:true},
 kind:{type:String,default:'bar',validator:v=>['bar','line','hbar','area','donut'].includes(v)},
 categories:{type:Array,default:()=>[]},
 series:{type:Array,default:()=>[]},
 unit:{type:String,default:''},
 decimals:{type:Number,default:0},
 empty:{type:String,default:'Chưa có dữ liệu trong kỳ này.'},
 height:{type:Number,default:260},
 clickable:Boolean,
 stacked:Boolean,
 maxSeries:{type:Number,default:3},
 showValues:Boolean,
 pointColors:{type:Array,default:null},
})
const emit=defineEmits(['select'])
const target=ref(null),showTable=ref(false),noCanvas=ref(false)
let chart=null,observer=null
const shown=computed(()=>props.series.slice(0,props.maxSeries))
const hasData=computed(()=>props.categories.length>0&&shown.value.some(s=>s.data.some(v=>v!=null&&Number(v)!==0)))
const number=v=>v==null||Number.isNaN(Number(v))?'—':new Intl.NumberFormat('vi-VN',{maximumFractionDigits:props.decimals}).format(Number(v))
const withUnit=v=>number(v)+(props.unit&&v!=null?' '+props.unit:'')
const tableRows=computed(()=>props.categories.map((label,i)=>({label,...Object.fromEntries(shown.value.map((s,k)=>['series_'+k,s.data[i]]))})))
const tableCols=computed(()=>[{field:'label',headerName:'Thời kỳ'},...shown.value.map((s,k)=>({field:'series_'+k,headerName:s.name+(props.unit?' ('+props.unit+')':''),valueFormatter:p=>number(p.value)}))])
const summary=computed(()=>shown.value.map(s=>s.name+': tổng '+withUnit(s.data.reduce((n,v)=>n+Number(v||0),0))).join('; '))
function render(){
 if(!target.value||!hasData.value||noCanvas.value){chart?.dispose();chart=null;return}
 // Without a usable canvas (old browser, test DOM) the numbers stay readable as a table.
 if(!chart){
  if(!document.createElement('canvas').getContext?.('2d')){noCanvas.value=true;return}
  chart=initChart(target.value,undefined,{renderer:'canvas'})
  chart.on('click',e=>{if(props.clickable)emit('select',{index:e.dataIndex,name:e.name})})
 }
 // Canvas needs concrete colours: read the theme tokens at render time.
 const css=getComputedStyle(target.value),token=name=>css.getPropertyValue(name).trim()
 // Chart tokens (spec 004) per mode: axis text, grid lines, the 8 categorical steps checked against each surface.
 const ink=token('--lotus-chart-axis')||token('--lotus-muted'),line=token('--lotus-chart-grid')||token('--lotus-border'),surface=token('--lotus-surface')
 const colors=[1,2,3,4,5,6,7,8].map(i=>token('--lotus-chart-'+i)).filter(Boolean),other=token('--lotus-chart-other')
 // Numbers on the marks when asked for; a zero prints nothing, so empty columns stay clean.
 const valueLabel=position=>props.showValues?{show:true,position,fontSize:11,color:position==='inside'?'#fff':token('--lotus-text'),...(position==='inside'?{textBorderColor:'rgba(0,0,0,.6)',textBorderWidth:2}:{}),formatter:p=>Number(p.value)?number(p.value):''}:undefined
 const palette=shown.value.map((s,i)=>s.other?other:colors[i]||other)
 const horizontal=props.kind==='hbar',isLine=props.kind==='line'||props.kind==='area'
 const categoryAxis={type:'category',data:props.categories,axisLine:{lineStyle:{color:line}},axisTick:{show:false},axisLabel:{color:ink,fontSize:11,hideOverlap:true}}
 const valueAxis={type:'value',splitLine:{lineStyle:{color:line,type:[3,3]}},axisLabel:{color:ink,fontSize:11,formatter:v=>number(v)}}
 if(props.kind==='donut'){
  const values=props.categories.map((name,i)=>({name,value:Number(shown.value[0].data[i]||0),itemStyle:{color:props.pointColors?.[i]||(name==='Khác'?other:colors[i%colors.length])}})).filter(d=>d.value)
  chart.setOption({animationDuration:200,backgroundColor:'transparent',
   tooltip:{trigger:'item',valueFormatter:withUnit,backgroundColor:surface,borderColor:line,textStyle:{color:token('--lotus-text'),fontSize:12}},
   series:[{type:'pie',radius:['46%','70%'],data:values,itemStyle:{borderColor:surface,borderWidth:2},label:{show:true,color:token('--lotus-text'),fontSize:11,formatter:p=>p.name+'\n'+number(p.value)+' · '+Math.round(p.percent)+'%'},labelLine:{length:8,length2:6}}]},true)
  return
 }
 chart.setOption({
  animationDuration:200,backgroundColor:'transparent',color:palette,
  tooltip:{trigger:'axis',axisPointer:{type:isLine?'line':'shadow'},valueFormatter:withUnit,backgroundColor:surface,borderColor:line,textStyle:{color:token('--lotus-text'),fontSize:12}},
  legend:shown.value.length>1?{top:0,left:0,icon:'roundRect',itemWidth:10,itemHeight:10,textStyle:{color:ink,fontSize:12}}:undefined,
  grid:{top:(shown.value.length>1?34:16)+(props.showValues&&!horizontal?12:0),right:props.showValues&&horizontal?56:16,bottom:8,left:8},
  xAxis:horizontal?valueAxis:categoryAxis,yAxis:horizontal?{...categoryAxis,inverse:true}:valueAxis,
  series:shown.value.map(s=>isLine
   ?{name:s.name,type:'line',data:s.data,label:valueLabel('top'),connectNulls:false,lineStyle:{width:2},symbol:'circle',showSymbol:props.showValues||s.data.filter(v=>v!=null).length<=14,symbolSize:props.showValues?(v=>Number(v)?8:0):8,areaStyle:props.kind==='area'?{opacity:.1}:undefined,itemStyle:{borderColor:surface,borderWidth:2}}
   :{name:s.name,type:'bar',data:props.pointColors?s.data.map((value,i)=>({value,itemStyle:props.pointColors[i]?{color:props.pointColors[i]}:undefined})):s.data,label:valueLabel(props.stacked?'inside':horizontal?'right':'top'),stack:props.stacked?'total':undefined,barMaxWidth:horizontal?18:28,barGap:'12%',cursor:props.clickable?'pointer':'default',itemStyle:{borderRadius:horizontal?[0,4,4,0]:[4,4,0,0],borderColor:surface,borderWidth:1}})
 },true)
}
onMounted(async()=>{await nextTick();render();if(typeof ResizeObserver!=='undefined'&&target.value){observer=new ResizeObserver(()=>chart?.resize());observer.observe(target.value)}})
// Light, dark and outdoor repaint the canvas with that mode's tokens.
watch(()=>[props.categories,props.series,props.kind,uiMode.value],()=>nextTick(render),{deep:true})
onBeforeUnmount(()=>{observer?.disconnect();chart?.dispose();chart=null})
</script>
<template>
<section class="lotus-chart-card" :aria-label="title">
 <header class="lotus-chart-head"><div><h3>{{title}}</h3><small v-if="unit" class="lotus-chart-unit">Đơn vị: {{unit}}</small></div><UiButton v-if="hasData&&!noCanvas" variant="ghost" size="sm" :aria-pressed="showTable?'true':'false'" @click="showTable=!showTable">{{showTable?'Xem biểu đồ':'Xem bảng số liệu'}}</UiButton></header>
 <slot name="controls"/>
 <p v-if="!hasData" class="lotus-chart-empty">{{empty}}</p>
 <template v-else>
  <div v-show="!showTable&&!noCanvas" ref="target" class="lotus-chart-canvas" :style="{height:height+'px'}" role="img" :aria-label="title+'. '+summary"/>
  <div v-if="showTable||noCanvas" class="lotus-chart-table"><DataTable :rows="tableRows" :columns="tableCols" storage-key="chart-data-table" empty="Không có dữ liệu để hiển thị."/></div>
 </template>
</section>
</template>