<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import CareMap from '../CareMap.vue'
import ReportCards from './ReportCards.vue'
import {formatDate} from '../../format'
import {legendFor} from '../../map-land.js'
// Báo cáo theo người xem (lotus_farm.field_reports): Sáng nay (what to deal with first), Tuần (work, ribbons, harvest,
// xưởng, forecast against harvest and a map of the lô), Tháng (harvest and its rates, money per lô, materials). One
// card per question; a card opens its rows, which export to Excel.
const props=defineProps({farm:{type:String,required:true},mobile:Boolean,user:String})
const emit=defineEmits(['payable'])
const tabs=[{id:'morning',label:'Sáng nay'},{id:'week',label:'Tuần'},{id:'month',label:'Tháng'}]
const tab=ref('morning'),data=ref(null),busy=ref(false),error=ref(''),map=ref(null)
const iso=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')
const weekDay=ref(iso(new Date())),month=ref(iso(new Date()).slice(0,7))
let asked=0
async function load(){
 const mine=++asked
 busy.value=true;error.value=''
 try{
  const args=tab.value==='week'?{farm:props.farm,week:weekDay.value}:tab.value==='month'?{farm:props.farm,month:month.value}:{farm:props.farm}
  const result=await call('lotus_farm.field_reports.'+tab.value,args)
  if(mine===asked)data.value=result
  if(tab.value==='week'&&!map.value)map.value=await call('lotus_farm.field.map_block_data',{farm:props.farm}).catch(()=>null)
 }catch(e){if(mine===asked){error.value=e.message;data.value=null}}
 finally{if(mine===asked)busy.value=false}
}
watch(()=>[props.farm,tab.value,weekDay.value,month.value],()=>{data.value=null;load()},{immediate:true})
// The lô of the map take the state of the week: held, late with care work, harvested, fine.
const statusMap=computed(()=>{
 if(!map.value||!data.value?.lots)return null
 const by=Object.fromEntries(data.value.lots.map(l=>[l.block,l.status]))
 return {...map.value,features:(map.value.features||[]).map(f=>({...f,properties:{...f.properties,status:by[f.properties.block]||'ok'}}))}
})
const legend=legendFor('status')
const heading=computed(()=>!data.value?'':tab.value==='morning'?'Báo cáo ngày '+formatDate(data.value.date)+' và việc hôm nay':
 tab.value==='week'?'Tuần '+data.value.week.split('-W')[1]+': '+formatDate(data.value.from)+' – '+formatDate(data.value.to):'Tháng '+data.value.month.slice(5)+'/'+data.value.month.slice(0,4))
</script>

<template>
 <section class="field-reports" :class="{'field-reports--mobile':mobile}" :aria-busy="busy">
  <div class="field-reports__tabs" role="tablist">
   <button v-for="t in tabs" :key="t.id" type="button" role="tab" :aria-selected="tab===t.id" :class="{active:tab===t.id}" @click="tab=t.id">{{t.label}}</button>
  </div>
  <div class="field-reports__tools">
   <LotusField v-if="tab==='week'" v-model="weekDay" label="Tuần có ngày" type="date" :mobile="mobile"/>
   <LotusField v-if="tab==='month'" v-model="month" label="Tháng" type="month" :mobile="mobile"/>
   <strong v-if="heading" class="field-reports__heading">{{heading}}</strong>
  </div>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="busy&&!data" class="lotus-form-note" role="status">Đang tải…</p>
  <ReportCards v-if="data" :cards="data.cards" :mobile="mobile" :storage-key="'field-report-'+tab"/>
  <template v-if="tab==='week'&&statusMap">
   <h3 class="field-reports__title">Tình trạng lô trong tuần</h3>
   <ul class="field-reports__legend"><li v-for="l in legend" :key="l.label"><i :style="{background:l.color}" aria-hidden="true"></i>{{l.label}}</li></ul>
   <CareMap class="field-reports__map" :collection="statusMap" :farm="farm" :user="user||''" color-by="status" compact/>
  </template>
  <p v-if="tab==='month'&&data" class="lotus-form-note">Tiền khoán theo từng người của tháng: <a href="#" @click.prevent="emit('payable',month)">mở Tiền khoán theo người</a>.</p>
 </section>
</template>

<style>
.field-reports{display:grid;gap:12px;min-width:0}
.field-reports__tabs{display:flex;gap:6px;flex-wrap:wrap;border-bottom:1px solid var(--lotus-border);padding-bottom:8px}
.field-reports__tabs button{padding:8px 14px;border:1px solid transparent;border-radius:var(--lotus-radius-md);background:none;font:inherit;color:inherit;cursor:pointer}
.field-reports__tabs button.active{font-weight:600;background:var(--lotus-soft);border-color:var(--lotus-border)}
.field-reports__tools{display:flex;gap:12px;align-items:end;flex-wrap:wrap}
.field-reports__tools>*:first-child{min-width:180px}
.field-reports__heading{font-size:var(--lotus-text-md);color:var(--lotus-text-strong);padding-bottom:6px}
.field-reports__title{margin:4px 0 0;font-size:var(--lotus-text-sm);font-weight:600;color:var(--lotus-muted)}
.field-reports__legend{list-style:none;margin:0;padding:0;display:flex;gap:12px;flex-wrap:wrap;font-size:var(--lotus-text-sm)}
.field-reports__legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:4px;vertical-align:-1px}
.field-reports__map{min-height:420px}
</style>
