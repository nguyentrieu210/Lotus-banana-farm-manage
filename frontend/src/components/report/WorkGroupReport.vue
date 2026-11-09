<script setup>
import {computed,ref,watch} from 'vue'
import {useRoute} from 'vue-router'
import {call} from '../../api'
import {Button as UiButton} from '../ui/button'
import ModalForm from '../form/ModalForm.vue'
import PivotFilter from './PivotFilter.vue'
import {buildXlsx,exportExcelFile} from '../../excel-export'
import {formatDate} from '../../format'
import {unitLabel} from '../../units'
import './report.css'
// Chăm sóc vườn and BVTV: what the phiếu reported over a period, one card per việc; a card opens its lines. BVTV also shows quarantine and sâu bệnh.
const props=defineProps({method:{type:String,required:true},filename:{type:String,required:true},empty:{type:String,required:true},protection:Boolean})
const route=useRoute()
const filters=ref({})
const fields=[{id:'year',label:'Năm'},{id:'month',label:'Tháng'},{id:'week',label:'Tuần'},{id:'day',label:'Ngày'},{id:'zone',label:'Khu'},{id:'block',label:'Lô'},{id:'team',label:'Tổ'},{id:'work',label:'Công việc'}]
const data=ref(null),busy=ref(false),error=ref(''),card=ref(null),disease=ref(null)
const farm=computed(()=>String(route.query.farm||''))
const num=(n,d=2)=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:d})
const dm=s=>s?String(s).slice(8,10)+'/'+String(s).slice(5,7):''
const unit=u=>unitLabel(u)||u||''
async function load(){
 busy.value=true;error.value=''
 try{data.value=await call('lotus_farm.work_report.'+props.method,{farm:farm.value||undefined,filters:Object.keys(filters.value).length?JSON.stringify(filters.value):undefined})}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
watch([farm,filters],load,{immediate:true})
const cards=computed(()=>data.value?.cards||[])
const materialText=m=>m.map(x=>x.name+' '+num(x.qty)+' '+unit(x.uom)).join(', ')
const allRows=computed(()=>cards.value.flatMap(c=>c.rows))
function exportExcel(){
 const columns=[{field:'date',headerName:'Ngày',valueFormatter:p=>formatDate(p.value)},{field:'work_name',headerName:'Công việc'},{field:'block_code',headerName:'Lô'},{field:'team_name',headerName:'Tổ'},{field:'qty',headerName:'Khối lượng'},{field:'unit',headerName:'Đơn vị'},{field:'workdays',headerName:'Công'},{field:'material',headerName:'Vật tư'},{field:'notes',headerName:'Ghi chú'}]
 exportExcelFile(buildXlsx(columns,allRows.value.map(r=>({...r,unit:unit(r.uom),material:r.materials.map(m=>m.name+' '+m.qty+' '+unit(m.uom)+(m.dose?' ('+m.dose+')':'')).join('; ')}))),props.filename)
}
</script>

<template>
 <section class="bunch-report lotus-ui" :aria-busy="busy">
  <PivotFilter v-model="filters" :fields="fields" :options="data?.options||{}"><UiButton type="button" variant="outline" :disabled="!allRows.length" @click="exportExcel">Xuất Excel</UiButton></PivotFilter>
  <p v-if="error" role="alert" class="lotus-list-page__error">{{error}}</p>
  <template v-if="data">
   <div class="bunch-report__works">
    <div><span>Lượt báo cáo</span><strong>{{num(data.entries)}}</strong></div>
    <div><span>Số lô đã làm</span><strong>{{num(data.lots)}}</strong></div>
    <div><span>Tổng công</span><strong>{{num(data.workdays,1)}}</strong></div>
    <template v-if="protection"><div><span>Lô đang cách ly</span><strong>{{num(data.quarantine.length)}}</strong></div><div><span>Loại sâu bệnh ghi nhận</span><strong>{{num(data.diseases.length)}}</strong></div></template>
   </div>

   <section v-if="protection&&data.quarantine.length" class="bunch-report__panel">
    <h3>Đang cách ly, chưa được thu</h3>
    <ul class="bunch-report__rows"><li v-for="q in data.quarantine" :key="q.block"><strong>{{q.code}}</strong><span>Cách ly đến {{dm(q.until)}}</span><em>{{q.days?'còn '+q.days+' ngày':'hết hôm nay'}}</em></li></ul>
   </section>

   <p v-if="!cards.length" class="lotus-form-note">{{empty}}</p>
   <div class="bunch-report__teams">
    <button v-for="c in cards" :key="c.work" type="button" class="bunch-report__team" @click="card=c">
     <strong>{{c.name}}</strong>
     <span>{{num(c.qty)}} {{unit(c.uom)}} · {{c.lots}} lô · {{num(c.workdays,1)}} công</span>
     <span v-if="c.materials.length">{{materialText(c.materials)}}</span>
    </button>
   </div>

   <section v-if="protection" class="bunch-report__panel">
    <h3>Sâu bệnh ghi nhận</h3>
    <p v-if="!data.diseases.length" class="lotus-form-note">Chưa ghi nhận sâu bệnh trong phần đang lọc.</p>
    <ul v-else class="bunch-report__rows"><li v-for="d in data.diseases" :key="d.disease"><button type="button" @click="disease=d"><strong>{{d.disease}}</strong><span>{{d.lots}} lô</span><em>{{num(d.plants,0)}} cây</em></button></li></ul>
   </section>
  </template>

  <ModalForm :model-value="!!card" :title="card?card.name:'Công việc'" width="640px" readonly @update:model-value="v=>!v&&(card=null)">
   <ul v-if="card" class="bunch-report__rows">
    <li v-for="r in card.rows" :key="r.name"><strong>{{r.block_code}} · {{r.team_name}}</strong><span>{{formatDate(r.date)}} · {{num(r.workdays,1)}} công<template v-if="r.materials.length"> · {{r.materials.map(m=>m.name+' '+num(m.qty)+' '+unit(m.uom)+(m.dose?' ('+m.dose+')':'')).join(', ')}}</template></span><em>{{num(r.qty)}} {{unit(r.uom)}}</em></li>
   </ul>
  </ModalForm>
  <ModalForm :model-value="!!disease" :title="disease?disease.disease:'Sâu bệnh'" width="560px" readonly @update:model-value="v=>!v&&(disease=null)">
   <ul v-if="disease" class="bunch-report__rows"><li v-for="r in disease.rows" :key="r.name"><strong>{{r.block_code}}</strong><span>{{formatDate(r.date)}}<template v-if="r.severity"> · {{r.severity}}</template><template v-if="r.action"> · {{r.action}}</template></span><em>{{num(r.plants,0)}} cây</em></li></ul>
  </ModalForm>
 </section>
</template>
