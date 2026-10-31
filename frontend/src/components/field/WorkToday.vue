<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import ModalForm from '../form/ModalForm.vue'
import WorkspaceSummaryStrip from '../WorkspaceSummaryStrip.vue'
import {Button as UiButton} from '../ui/button'
import WorkEntryForm from './WorkEntryForm.vue'
import WorkTicket from './WorkTicket.vue'
import {formatDate} from '../../format'
import {unitLabel} from '../../units'
import {payShort,states,stateTone,groups,money,amountText,unitText} from '../../field-work-model.js'
// Hôm nay: the phiếu giao of the tổ (all tổ for the đội trưởng) that can be reported on a day, today's report on each,
// and what is left under each cap. Tap a phiếu to report the day; "Chi tiết" opens the phiếu with its actions.
const props=defineProps({farm:{type:String,required:true},crew:{type:String,required:true},setup:{type:Object,required:true},mobile:Boolean})
const day=defineModel('date',{type:String,required:true})
const api=(name,args={},write=false)=>call('lotus_farm.field_report.'+name,args,write)
const data=ref(null),busy=ref(false),error=ref(''),notice=ref('')
const reporting=ref(null),entryRef=ref(null),entryBusy=ref(false),detail=ref(null),group=ref('')
async function load(){
 if(!props.farm||!props.crew||!day.value)return
 busy.value=true;error.value=''
 try{data.value=await api('today',{farm:props.farm,crew:props.crew,date:day.value})}
 catch(e){error.value=e.message;data.value=null}
 finally{busy.value=false}
}
watch(()=>[props.farm,props.crew,day.value],load,{immediate:true})
const tickets=computed(()=>(data.value?.tickets||[]).filter(t=>!group.value||t.work_group===group.value))
const groupOptions=[{value:'',label:'Tất cả nhóm việc'},...Object.entries(groups).map(([value,label])=>({value,label}))]
const summary=computed(()=>{
 const all=data.value?.tickets||[]
 return [
  {label:'Phiếu đang làm',value:all.length},
  {label:'Đã báo hôm nay',value:all.filter(t=>t.entry).length},
  {label:'Chờ duyệt',value:all.filter(t=>t.state==='Reported').length},
  {label:'Người có mặt',value:(data.value?.present||[]).length},
 ]
})
const unit=t=>unitText(unitLabel(t.uom)||t.uom,t.basis)
function report(t){if(!t.can_report)return;detail.value=null;reporting.value=t}
async function saveEntry(){const r=await entryRef.value?.save();if(r){notice.value='Đã lưu báo cáo '+r.block_code+' · '+r.work_name+'.';reporting.value=null;await load()}}
function saved(){if(props.mobile){notice.value='Đã lưu báo cáo.';reporting.value=null;load()}}
</script>

<template>
 <section class="work-today" :class="{'work-today--mobile':mobile}" :aria-busy="busy">
  <template v-if="!(mobile&&reporting)">
  <FormGrid :columns="mobile?1:3">
   <LotusField v-model="day" label="Ngày" type="date" :mobile="mobile"/>
   <LotusField v-model="group" label="Nhóm việc" type="select" :searchable="false" :options="groupOptions" :mobile="mobile"/>
  </FormGrid>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="field-report__notice" role="status">{{notice}}</p>
  <WorkspaceSummaryStrip v-if="data&&!mobile" :items="summary"/>
  <p v-else-if="data" class="lotus-form-note">{{summary.map(s=>s.label+': '+s.value).join(' · ')}}</p>
  <p v-if="data&&!tickets.length" class="lotus-form-note">Không có phiếu nào đang làm. Đội trưởng giao việc ở mục Giao việc theo lô.</p>
  <div class="work-today__cards">
   <article v-for="t in tickets" :key="t.name" class="work-today__card" :class="'is-'+(stateTone[t.display]||'neutral')">
    <button type="button" class="work-today__main" :disabled="!t.can_report" @click="report(t)">
     <strong>{{t.block_code}} · {{t.work_name}}</strong>
     <span>{{t.team_name}} · {{payShort[t.pay_mode]}}<template v-if="t.rate"> · {{money(t.rate)}}/{{unit(t)}}</template></span>
     <span>{{states[t.display]||t.display}}<template v-if="t.due_date"> · hạn {{formatDate(t.due_date)}}</template> · đã báo {{amountText(t.progress?.qty)}} {{unit(t)}}</span>
     <span v-if="t.cap_left!=null">Còn được báo {{amountText(t.cap_left)}} {{unit(t)}}</span>
     <em v-if="t.entry">Hôm nay: {{amountText(t.entry.qty)}} {{unit(t)}} · {{t.entry.people.length}} người{{t.entry.done?' · báo xong':''}}</em>
     <em v-else-if="t.can_report" class="work-today__todo">Chưa báo hôm nay – bấm để báo</em>
    </button>
    <UiButton type="button" size="sm" variant="ghost" @click="detail=t.name">Chi tiết</UiButton>
   </article>
  </div>
  </template>

  <ModalForm v-if="!mobile" :model-value="!!reporting" :title="reporting?'Báo cáo '+formatDate(day)+' · '+reporting.block_code+' · '+reporting.work_name:''" width="880px"
   :busy="entryBusy" submit-label="Lưu báo cáo" @update:model-value="v=>!v&&(reporting=null)" @submit="saveEntry">
   <WorkEntryForm v-if="reporting&&data" ref="entryRef" :ticket="reporting" :day="day" :context="data" @busy-change="entryBusy=$event"/>
  </ModalForm>
  <section v-else-if="reporting&&data" class="work-today__sheet">
   <UiButton type="button" variant="ghost" size="sm" @click="reporting=null">‹ Quay lại danh sách</UiButton>
   <WorkEntryForm :ticket="reporting" :day="day" :context="data" mobile @saved="saved"/>
  </section>

  <ModalForm :model-value="!!detail" title="Phiếu giao việc" width="880px" :readonly="true" @update:model-value="v=>!v&&(detail=null)">
   <WorkTicket v-if="detail" :name="detail" :setup="setup" :mobile="mobile" @changed="load" @report="t=>{const row=(data?.tickets||[]).find(x=>x.name===t.name);if(row)report(row)}"/>
  </ModalForm>
 </section>
</template>

<style>
.work-today{display:grid;gap:12px;min-width:0}
.work-today__cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}
.work-today__card{display:flex;align-items:flex-start;gap:6px;padding:10px 12px;border:1px solid var(--lotus-border);border-left-width:4px;border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.work-today__card.is-danger{border-left-color:var(--lotus-danger)}
.work-today__card.is-warning{border-left-color:var(--lotus-warning)}
.work-today__card.is-success{border-left-color:var(--lotus-success)}
.work-today__card.is-info{border-left-color:var(--lotus-primary)}
.work-today__main{flex:1 1 auto;display:grid;gap:2px;min-width:0;text-align:left;font:inherit;background:none;border:0;padding:0;cursor:pointer;color:inherit}
.work-today__main:disabled{cursor:default}
.work-today__main strong{color:var(--lotus-text-strong);font-weight:600}
.work-today__main span,.work-today__main em{font-size:var(--lotus-text-sm);color:var(--lotus-muted);font-style:normal}
.work-today__todo{color:var(--lotus-primary-text)!important}
.work-today__sheet{display:grid;gap:8px}
.work-today--mobile .work-today__cards{grid-template-columns:1fr}
</style>
