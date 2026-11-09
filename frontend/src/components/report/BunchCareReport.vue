<script setup>
import {computed,ref,watch} from 'vue'
import {useRoute} from 'vue-router'
import {call} from '../../api'
import {Button as UiButton} from '../ui/button'
import LotusChart from '../LotusChart.vue'
import DataTable from '../DataTable.vue'
import ModalForm from '../form/ModalForm.vue'
import UiSelect from '../ui/select/Select.vue'
import PivotFilter from './PivotFilter.vue'
import PivotChart from './PivotChart.vue'
import HeatGrid from './HeatGrid.vue'
import {crossFilter} from '../../pivot-filter.js'
import {DIMENSIONS,STAGES,categories,dimensionById,heat,label,lots,stageOf,table,total} from '../../bunch-pivot.js'
import './report.css'
// Báo cáo chăm sóc buồng: the công đoạn in the order the work is done, each with several charts that keep their own choices.
defineProps({embedded:Boolean,navigationKey:String})
const route=useRoute(),filters=ref({}),data=ref(null),error=ref(''),busy=ref(false),detail=ref(null),tableDim=ref('z')
const farm=computed(()=>String(route.query.farm||''))
const fields=[{id:'year',label:'Năm'},{id:'month',label:'Tháng'},{id:'week',label:'Tuần'},{id:'zone',label:'Khu'},{id:'block',label:'Lô'},{id:'team',label:'Tổ'},{id:'colour',label:'Màu dây'},{id:'lan',label:'Lần cắt'}]
const query=computed(()=>({...(farm.value?{farm:farm.value}:{}),...(Object.keys(filters.value).length?{filters:JSON.stringify(filters.value)}:{})}))
async function load(){
 busy.value=true;error.value=''
 try{data.value=await call('lotus_farm.bunch_report.sections',query.value)}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
watch(query,load,{immediate:true})

const num=(n,d=0)=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:d})
const cube=computed(()=>data.value?.cube||[])
const weeks=computed(()=>data.value?.dashboard?.weeks||[])
const baseline=computed(()=>({z:filters.value.zone?[]:data.value?.zones||[],w:weeks.value.map(w=>w.week)}))
const BASE={prop:['inject','số đã chích'],care:['inject','số đã chích'],bag:['cut','số đã cắt'],reject:['cut','số đã cắt'],harvest:['cut','số đã cắt']}
const chain=computed(()=>STAGES.map(s=>{
 const value=total(cube.value,s.id),base=BASE[s.id],whole=base?total(cube.value,base[0]):0
 return {...s,value,share:whole?Math.round(value/whole*100):null,of:base?.[1]||''}
}))
const stock=computed(()=>data.value?.stock||{left:0,due:0,overdue:0})
const injection=computed(()=>data.value?.injection||{waiting:0,late:[],late_total:0})
const rejects=computed(()=>data.value?.rejects||{rate:null,before:0,after:0})
const harvest=computed(()=>data.value?.harvest||{kg:0,kg_per:null})
const cutHeat=computed(()=>heat(cube.value,'cut',weeks.value.filter(w=>w.cut).map(w=>w.week)))
// Each công đoạn opens on the views that matter most for it; every chart can then be changed on its own.
const SECTIONS=[
 {n:1,id:'inject',charts:[{dim:'z'},{dim:'w',kind:'area'},{dim:'t',kind:'donut'}]},
 {n:2,id:'prop',charts:[{dim:'z'},{dim:'w',kind:'line'},{dim:'b',kind:'hbar'}]},
 {n:3,id:'care',charts:[{dim:'z'},{dim:'w',kind:'area'},{dim:'t',kind:'donut'}]},
 {n:4,id:'cut',charts:[{dim:'w',split:'l'},{dim:'c',kind:'donut'},{dim:'z'}]},
 {n:5,id:'bag',charts:[{dim:'c'},{dim:'w',kind:'line'},{dim:'z',kind:'donut'}]},
 {n:6,id:'reject',charts:[{dim:'r',kind:'donut'},{dim:'z'},{dim:'b',kind:'hbar'}]},
 {n:7,id:'left',charts:[{dim:'c',kind:'donut'},{dim:'z'},{dim:'b',kind:'hbar'}]},
 {n:8,id:'harvest',charts:[{dim:'w'},{dim:'z',kind:'donut'},{dim:'w',kind:'line',metric:'kg_per'}]},
]
function open({stage,dim,value}){
 if(dim==='b'){filters.value=crossFilter(filters.value,'block',value);return}
 detail.value={stage,dim,value,rows:lots(cube.value,stage,dim,value)}
}
const detailTitle=computed(()=>detail.value?label(detail.value.dim,detail.value.value)+' · '+stageOf(detail.value.stage).label:'Chi tiết')
const detailUnit=computed(()=>detail.value?stageOf(detail.value.stage).unit:'')
const detailMax=computed(()=>Math.max(1,...(detail.value?.rows||[]).map(r=>r.qty)))
const detailFilter=computed(()=>detail.value?dimensionById(detail.value.dim).filter:'')
function filterTo(){filters.value=crossFilter(filters.value,detailFilter.value,detail.value.value);detail.value=null}
const tableDimensions=DIMENSIONS.filter(d=>d.id!=='r')
const tableDimension=computed(()=>dimensionById(tableDim.value))
const pivotRows=computed(()=>table(cube.value,tableDim.value,categories(cube.value,tableDim.value,baseline.value[tableDim.value]||[])))
const pivotColumns=computed(()=>[{field:'name',headerName:tableDimension.value.label,minWidth:130},...STAGES.map(s=>({field:s.id,headerName:s.label,minWidth:105,valueFormatter:p=>num(p.value)}))])
function exportBook(){location.href='/api/method/lotus_farm.bunch_report.export_cut_book?'+new URLSearchParams(query.value)}
</script>

<template>
 <div class="bunch-report lotus-ui" :aria-busy="busy">
  <PivotFilter v-model="filters" :fields="fields" :options="data?.options||{}"/>
  <p v-if="error" role="alert" class="lotus-list-page__error">{{error}}</p>
  <template v-if="data">
   <ol class="stage-chain" aria-label="Các công đoạn từ trước đến sau">
    <li v-for="s in chain" :key="s.id"><span>{{s.label}}</span><strong>{{num(s.value)}}</strong><small v-if="s.share!=null">{{s.share}}% {{s.of}}</small></li>
   </ol>
   <div class="bi-row">
    <LotusChart show-values kind="hbar" title="Số lượng qua từng công đoạn" :categories="chain.map(s=>s.label)" :series="[{name:'Số lượng',data:chain.map(s=>s.value)}]" :height="280" empty="Chưa có số trong phần đang lọc."/>
    <LotusChart show-values kind="line" title="Chích, cắt, thu theo tuần" unit="buồng" :categories="weeks.map(w=>'T'+w.number)" :series="[{name:'Chích bắp',data:weeks.map(w=>w.inject)},{name:'Cắt bắp',data:weeks.map(w=>w.cut)},{name:'Thu hoạch',data:weeks.map(w=>w.harvest)}]" :height="280" empty="Chưa có số trong phần đang lọc."/>
   </div>

   <section v-for="s in SECTIONS" :key="s.id" class="bi-stage">
    <h2><b>{{s.n}}</b>{{stageOf(s.id).label}}<UiButton v-if="s.id==='cut'" type="button" variant="outline" size="sm" :disabled="!total(cube,'cut')" @click="exportBook">Xuất Excel theo mẫu sổ</UiButton></h2>
    <div v-if="s.id==='inject'" class="bi-facts bi-facts--row">
     <div><span>Chờ cắt</span><strong>{{num(injection.waiting)}}</strong></div>
     <div :class="{'is-alert':injection.late_total}"><span>Quá hạn cắt</span><strong><template v-if="injection.late_total">⚠ </template>{{num(injection.late_total)}}</strong><small v-if="injection.late.length">Trễ nhất: {{injection.late[0].code}}, {{injection.late[0].late_days}} ngày</small></div>
    </div>
    <div v-else-if="s.id==='reject'" class="bi-facts bi-facts--row">
     <div><span>Tỷ lệ hủy sau cắt</span><strong>{{rejects.rate==null?'—':num(rejects.rate,1)+'%'}}</strong></div>
     <div><span>Trước / sau cắt</span><strong>{{num(rejects.before)}} / {{num(rejects.after)}}</strong></div>
    </div>
    <div v-else-if="s.id==='left'" class="bi-facts bi-facts--row">
     <div><span>Tồn buồng</span><strong>{{num(stock.left)}}</strong></div>
     <div><span>Đến kỳ thu tuần này</span><strong>{{num(stock.due)}}</strong></div>
     <div :class="{'is-alert':stock.overdue}"><span>Quá hạn thu</span><strong><template v-if="stock.overdue">⚠ </template>{{num(stock.overdue)}}</strong></div>
    </div>
    <div v-else-if="s.id==='harvest'" class="bi-facts bi-facts--row">
     <div><span>Khối lượng</span><strong>{{num(harvest.kg)}} kg</strong></div>
     <div><span>Trung bình</span><strong>{{harvest.kg_per==null?'—':num(harvest.kg_per,2)+' kg/buồng'}}</strong></div>
    </div>
    <div class="bi-charts">
     <PivotChart v-for="(c,i) in s.charts" :key="s.id+i" :cube="cube" :stage="s.id" :dim="c.dim" :kind="c.kind||'bar'" :split="c.split||''" :metric="c.metric||''" :baseline="baseline" @open="open"/>
    </div>
    <HeatGrid v-if="s.id==='cut'" title="Cắt bắp theo lô và tuần" :grid="cutHeat" @open="value=>open({stage:'cut',dim:'w',value})"/>
   </section>

   <section class="bi-stage"><h2>Bảng tổng hợp<UiSelect v-model="tableDim" class="bi-table-dim" aria-label="Bảng theo"><option v-for="d in tableDimensions" :key="d.id" :value="d.id">Theo {{d.label.toLowerCase()}}</option></UiSelect></h2>
    <DataTable :key="tableDim" :rows="pivotRows" :columns="pivotColumns" row-key="key" storage-key="bunch-care-pivot" empty="Chưa có số trong phần đang lọc."/>
   </section>
  </template>

  <ModalForm :model-value="!!detail" :title="detailTitle" width="560px" readonly @update:model-value="v=>!v&&(detail=null)">
   <template v-if="detail">
    <p v-if="!detail.rows.length" class="lotus-form-note">Chưa có số của lô nào.</p>
    <ul v-else class="bi-lots"><li v-for="l in detail.rows" :key="l.code"><strong>{{l.code}}</strong><span class="bi-lots__track" aria-hidden="true"><i :style="{width:(l.qty/detailMax*100)+'%'}"></i></span><em>{{num(l.qty)}} {{detailUnit}}<template v-if="l.kg"> · {{num(l.kg)}} kg</template></em></li></ul>
    <div v-if="detailFilter"><UiButton type="button" variant="outline" size="sm" @click="filterTo">Lọc cả trang theo {{label(detail.dim,detail.value)}}</UiButton></div>
   </template>
  </ModalForm>
 </div>
</template>
