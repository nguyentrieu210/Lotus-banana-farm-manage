<script setup>
import {computed,ref,watch} from 'vue'
import {useRoute} from 'vue-router'
import {call} from '../../api'
import ModalForm from '../form/ModalForm.vue'
import PivotFilter from './PivotFilter.vue'
import {formatDate} from '../../format'
import './report.css'
// Xưởng đóng gói: the shifts recorded over a period, one card per day; a card opens its shifts.
defineProps({embedded:Boolean,navigationKey:String})
const route=useRoute()
const filters=ref({})
const fields=[{id:'year',label:'Năm'},{id:'month',label:'Tháng'},{id:'week',label:'Tuần'},{id:'day',label:'Ngày'}]
const data=ref(null),busy=ref(false),error=ref(''),day=ref(null)
const farm=computed(()=>String(route.query.farm||''))
const num=(n,d=0)=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:d})
const pct=v=>v==null?'—':num(v,1)+'%'
async function load(){
 busy.value=true;error.value=''
 try{data.value=await call('lotus_farm.work_report.packhouse',{farm:farm.value||undefined,filters:Object.keys(filters.value).length?JSON.stringify(filters.value):undefined})}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
watch([farm,filters],load,{immediate:true})
const totals=computed(()=>data.value?.totals||{})
</script>

<template>
 <section class="bunch-report lotus-ui" :aria-busy="busy">
  <PivotFilter v-model="filters" :fields="fields" :options="data?.options||{}"/>
  <p v-if="error" role="alert" class="lotus-list-page__error">{{error}}</p>
  <template v-if="data">
   <div class="bunch-report__works">
    <div><span>Đầu vào</span><strong>{{num(totals.input_kg)}} kg</strong></div>
    <div><span>Thành phẩm</span><strong>{{num(totals.finished_kg)}} kg</strong></div>
    <div><span>Phụ phẩm</span><strong>{{num(totals.secondary_kg)}} kg</strong></div>
    <div><span>Hao hụt</span><strong>{{num(totals.loss_kg)}} kg</strong></div>
    <div><span>Số thùng</span><strong>{{num(totals.cartons)}}</strong></div>
    <div><span>Tỷ lệ đóng gói</span><strong>{{pct(totals.packout)}}</strong></div>
   </div>
   <p v-if="!data.days.length" class="lotus-form-note">Chưa có ca đóng gói trong phần đang lọc. Số sẽ có từ khi xưởng bắt đầu chạy ở mục Sau thu hoạch.</p>
   <div class="bunch-report__teams">
    <button v-for="d in data.days" :key="d.date" type="button" class="bunch-report__team" @click="day=d">
     <strong>{{formatDate(d.date)}}</strong>
     <span>Vào {{num(d.input_kg)}} kg · thành phẩm {{num(d.finished_kg)}} kg</span>
     <span>{{num(d.cartons)}} thùng · đóng gói {{pct(d.packout)}}</span>
    </button>
   </div>
  </template>
  <ModalForm :model-value="!!day" :title="day?'Ca ngày '+formatDate(day.date):'Ca đóng gói'" width="560px" readonly @update:model-value="v=>!v&&(day=null)">
   <ul v-if="day" class="bunch-report__rows"><li v-for="s in day.shifts" :key="s.name"><strong>{{s.code||s.name}}</strong><span>Vào {{num(s.input_kg)}} kg · phụ phẩm {{num(s.secondary_kg)}} kg · hao hụt {{num(s.loss_kg)}} kg · {{num(s.labor,1)}} người</span><em>{{num(s.finished_kg)}} kg</em></li></ul>
  </ModalForm>
 </section>
</template>
