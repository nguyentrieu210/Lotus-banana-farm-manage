<script setup>
import {computed,ref,watch} from 'vue'
import LotusChart from '../LotusChart.vue'
import UiSelect from '../ui/select/Select.vue'
import {OTHER,SPLITS,dimensionsFor,pivotChart,stageOf} from '../../bunch-pivot.js'
// One chart with its own choices: what it is cut by, what kind of chart, and what splits it. A column asks the page for its detail.
const props=defineProps({cube:{type:Array,required:true},stage:{type:String,required:true},dim:{type:String,default:'z'},kind:{type:String,default:'bar'},split:{type:String,default:''},metric:{type:String,default:''},baseline:{type:Object,default:()=>({})}})
const emit=defineEmits(['open'])
const by=ref(props.dim),type=ref(props.kind),parts=ref(props.split)
const kinds=computed(()=>[{id:'bar',label:'Cột'},{id:'hbar',label:'Thanh ngang'},{id:'line',label:'Đường'},{id:'area',label:'Miền'},...(props.metric?[]:[{id:'donut',label:'Tròn'}])])
const dims=computed(()=>dimensionsFor(props.stage))
const dimension=computed(()=>dims.value.find(d=>d.id===by.value)||dims.value[0])
const canSplit=computed(()=>!props.metric&&type.value!=='donut')
const splits=computed(()=>SPLITS.filter(s=>s.id!==by.value))
watch(by,value=>{if(parts.value===value)parts.value=''})
const result=computed(()=>pivotChart(props.cube,{stage:props.stage,dim:by.value,split:canSplit.value?parts.value:'',metric:props.metric,baseline:props.baseline,sorted:type.value==='donut'}))
const title=computed(()=>(props.metric==='kg_per'?'Kg mỗi buồng':stageOf(props.stage).label)+' theo '+dimension.value.label.toLowerCase())
const unit=computed(()=>props.metric==='kg_per'?'kg/buồng':stageOf(props.stage).unit)
function select(event){const value=result.value.keys[event.index];if(value!==undefined&&value!==OTHER)emit('open',{stage:props.stage,dim:by.value,value})}
</script>

<template>
 <LotusChart show-values :kind="type" :title="title" :unit="unit" :decimals="metric?2:0" :categories="result.names" :series="result.series" :stacked="result.stacked" :point-colors="result.pointColors" :max-series="6" clickable :empty="'Chưa có số trong phần đang lọc.'" @select="select">
  <template #controls>
   <div class="pivot-chart__controls">
    <UiSelect v-model="by" aria-label="Xem theo"><option v-for="d in dims" :key="d.id" :value="d.id">{{d.label}}</option></UiSelect>
    <UiSelect v-model="type" aria-label="Kiểu biểu đồ"><option v-for="k in kinds" :key="k.id" :value="k.id">{{k.label}}</option></UiSelect>
    <UiSelect v-if="canSplit" v-model="parts" aria-label="Tách theo"><option v-for="s in splits" :key="s.id" :value="s.id">{{s.id?'Tách '+s.label.toLowerCase():'Không tách'}}</option></UiSelect>
   </div>
  </template>
 </LotusChart>
</template>
