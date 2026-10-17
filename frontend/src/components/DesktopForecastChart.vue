<script setup>
import {computed,onMounted,onBeforeUnmount,ref,watch,nextTick} from 'vue'
import {init as initChart,use as useEcharts} from 'echarts/core'
import {BarChart,LineChart} from 'echarts/charts'
import {GridComponent,TooltipComponent,LegendComponent,DataZoomComponent} from 'echarts/components'
import {CanvasRenderer} from 'echarts/renderers'
useEcharts([BarChart,LineChart,GridComponent,TooltipComponent,LegendComponent,DataZoomComponent,CanvasRenderer])
const props=defineProps({months:{type:Array,default:()=>[]},dark:{type:Boolean,default:false}})
const target=ref(null)
let chart=null
let observer=null
const total=computed(()=>props.months.reduce((n,x)=>n+Number(x.gross_kg||0),0))
const format=n=>new Intl.NumberFormat('vi-VN',{maximumFractionDigits:1}).format(Number(n||0)/1000)
function render(){
 if(!target.value)return
 if(!chart)chart=initChart(target.value,undefined,{renderer:'canvas'})
 const foreground=props.dark?'#e8edf6':'#556374'
 const grid=props.dark?'#343d4d':'#e9edf2'
 chart.setOption({
   animationDuration:240,
   backgroundColor:'transparent',
   color:['#b8401b','#278871','#6e93ad'],
   tooltip:{trigger:'axis',valueFormatter:v=>format(v)+' tấn'},
   legend:{top:0,right:0,textStyle:{color:foreground,fontSize:11},data:['Dự thu buồng','Thành phẩm','Đã thu thực tế']},
   grid:{top:40,right:12,left:18,bottom:48,containLabel:true},
   xAxis:{type:'category',data:props.months.map(m=>m.month.slice(5)+'/'+m.month.slice(2,4)),axisLine:{lineStyle:{color:grid}},axisLabel:{color:foreground,fontSize:10}},
   yAxis:{type:'value',name:'kg',nameTextStyle:{color:foreground},splitLine:{lineStyle:{color:grid}},axisLabel:{color:foreground,formatter:v=>format(v)+' t'}},
   series:[
    {name:'Dự thu buồng',type:'bar',barMaxWidth:28,data:props.months.map(m=>m.gross_kg||0),itemStyle:{borderRadius:[3,3,0,0]}},
    {name:'Thành phẩm',type:'line',smooth:true,symbolSize:5,data:props.months.map(m=>m.packed_kg||0)},
    {name:'Đã thu thực tế',type:'line',smooth:true,showSymbol:false,lineStyle:{type:'dashed'},data:props.months.map(m=>m.actual_gross_kg||0)},
   ]
 },true)
}
onMounted(async()=>{await nextTick();render();if(typeof ResizeObserver!=='undefined'){observer=new ResizeObserver(()=>chart?.resize());observer.observe(target.value)}})
watch(()=>[props.months,props.dark],()=>nextTick(render),{deep:true})
onBeforeUnmount(()=>{observer?.disconnect();chart?.dispose();chart=null})
</script>
<template>
<div class="lotus-forecast-chart">
 <div ref="target" class="lotus-forecast-chart__canvas" role="img" :aria-label="'Biểu đồ dự thu và thành phẩm '+months.length+' tháng; tổng dự thu '+format(total)+' tấn'"/>
 <p class="lotus-forecast-chart__summary">Tổng dự thu trong kỳ: <strong>{{format(total)}} tấn buồng</strong>. Di chuột vào từng tháng để xem chi tiết.</p>
</div>
</template>
