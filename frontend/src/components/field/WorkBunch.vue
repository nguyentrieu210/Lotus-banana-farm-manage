<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import ListPage from '../ListPage.vue'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import ModalForm from '../form/ModalForm.vue'
import {Button as UiButton} from '../ui/button'
import WorkBunchSheet from './WorkBunchSheet.vue'
import BunchStockCards from '../report/BunchStockCards.vue'
import {amountText} from '../../field-work-model.js'
import {formatDate} from '../../format'
import {confirmable,eventLabels,HARVEST,kindLabels,kindOf,stageLabels,stateLabels} from '../../bunch-sheet-model.js'
// Chăm sóc buồng of one đội and day: what was entered, a dialog per việc to enter it, and the đội trưởng's confirmation. A line the
// confirmer entered waits for someone else. A confirmed line is corrected with a reason: voided and written again (number 0: only voided).
const props=defineProps({farm:{type:String,required:true},crew:{type:String,required:true},setup:{type:Object,required:true},mobile:Boolean})
const day=defineModel('date',{type:String,required:true})
const api=(name,args={},write=false)=>call('lotus_farm.bunch_posting.'+name,args,write)
const sheet=ref(null),busy=ref(false),saving=ref(false),error=ref(''),notice=ref(''),rowErrors=ref([])
const entry=ref(null),fix=ref(null),fixBusy=ref(false),fixError=ref('')
const status=ref(null),statusOpen=ref(false),warnings=ref([]),stockOpen=ref(false)
async function load(){
 if(!props.farm||!props.crew||!day.value)return
 busy.value=true;error.value=''
 try{sheet.value=await api('day_sheet',{farm:props.farm,crew:props.crew,date:day.value});await loadStatus()}
 catch(e){error.value=e.message;sheet.value=null}
 finally{busy.value=false}
}
// The list a đội trưởng needs in the morning is about the day before the one on screen.
function dayBefore(value){const d=new Date(value+'T00:00:00Z');d.setUTCDate(d.getUTCDate()-1);return d.toISOString().slice(0,10)}
async function loadStatus(){status.value=sheet.value?.rights?.supervisor?await api('day_status',{farm:props.farm,crew:props.crew,date:dayBefore(day.value)}):null}
watch(()=>[props.farm,props.crew,day.value],()=>{notice.value='';rowErrors.value=[];warnings.value=[];entry.value=null;load()},{immediate:true})
const checks=computed(()=>(status.value?.not_reported.length||0)+(status.value?.anomalies.length||0))

const supervises=computed(()=>!!sheet.value?.rights?.supervisor)
const canEnter=computed(()=>(sheet.value?.teams||[]).length>0)
const detail=r=>[r.ribbon,r.event_type==='Reject'?stageLabels[r.reject_stage]:'',r.reason_name].filter(Boolean).join(' · ')
const rows=computed(()=>(sheet.value?.rows||[]).map(r=>({...r,label:eventLabels[r.event_type]||r.event_type,detail:detail(r)})))
const suckers=computed(()=>sheet.value?.suckers||[])
const ready=computed(()=>confirmable(sheet.value,sheet.value?.user))
const summary=computed(()=>{
 const totals={}
 for(const r of rows.value)totals[r.label]=(totals[r.label]||0)+Number(r.qty||0)
 return Object.entries(totals).map(([label,qty])=>label+' '+amountText(qty)).join(' · ')
})
const columns=[
 {field:'block_code',headerName:'Lô',minWidth:70},
 {field:'label',headerName:'Việc',minWidth:110},
 {field:'detail',headerName:'Màu dây, lý do',minWidth:160},
 {field:'qty',headerName:'Số buồng',valueFormatter:p=>amountText(p.value),minWidth:90},
 {field:'weight_kg',headerName:'Kg',valueFormatter:p=>p.value?amountText(p.value):'',minWidth:80},
 {field:'team_name',headerName:'Tổ',minWidth:100},
 {field:'entered_name',headerName:'Người nhập',minWidth:140},
 {field:'state',headerName:'Trạng thái',valueGetter:p=>stateLabels[p.data.state]||p.data.state,minWidth:120},
]
const editable=r=>r.state==='Draft'?!!kindOf(r):r.state==='Confirmed'&&supervises.value
function openRow(r){
 if(r.state==='Draft'){if(kindOf(r))entry.value={kind:kindOf(r),team:r.work_team};return}
 if(supervises.value){fixError.value='';fix.value={row:r,qty:r.qty,weight_kg:r.weight_kg,reason:''}}
}
async function entrySaved(){entry.value=null;notice.value='Đã lưu. Số chờ đội trưởng xác nhận.';rowErrors.value=[];await load()}
async function confirmDay(){
 if(!ready.value||saving.value)return
 saving.value=true;error.value='';notice.value='';rowErrors.value=[];warnings.value=[]
 try{
  const result=await api('confirm_day',{farm:props.farm,crew:props.crew,date:day.value},true)
  rowErrors.value=result.errors;warnings.value=result.warnings||[]
  const parts=[]
  if(result.confirmed)parts.push(result.confirmed+' dòng')
  if(result.suckers)parts.push(result.suckers+' lô chọn chồi')
  notice.value=parts.length?'Đã xác nhận '+parts.join(' và ')+'.':''
  await load()
 }catch(e){error.value=e.message}
 finally{saving.value=false}
}
async function submitFix(){
 const f=fix.value
 if(!String(f.reason||'').trim()){fixError.value='Ghi lý do sửa.';return}
 fixBusy.value=true;fixError.value=''
 try{
  const values={qty:f.qty};if(f.row.event_type===HARVEST)values.weight_kg=f.weight_kg
  await api('amend',{event:f.row.name,values,reason:f.reason},true)
  notice.value='Đã sửa '+f.row.block_code+'. Dòng cũ được giữ trong lịch sử.'
  fix.value=null;await load()
 }catch(e){fixError.value=e.message}
 finally{fixBusy.value=false}
}
</script>

<template>
 <section class="work-bunch" :class="{'work-bunch--mobile':mobile}" :aria-busy="busy">
  <FormGrid :columns="mobile?1:3"><LotusField v-model="day" label="Ngày" type="date" :mobile="mobile"/></FormGrid>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="field-report__notice" role="status">{{notice}}</p>
  <ul v-if="rowErrors.length" class="work-bunch__errors" role="alert"><li v-for="(e,i) in rowErrors" :key="i"><strong v-if="e.block">{{e.block}}:</strong> {{e.message}}</li></ul>
  <ul v-if="warnings.length" class="work-bunch__errors" role="status"><li v-for="(w,i) in warnings" :key="i"><strong>{{w.block}}:</strong> {{w.message}}</li></ul>
  <template v-if="sheet">
   <button v-if="checks" type="button" class="work-bunch__checks" @click="statusOpen=true"><strong>Cần kiểm tra</strong><span>{{status.not_reported.length}} lô chưa báo · {{status.anomalies.length}} số bất thường</span></button>
   <p v-if="!canEnter&&!supervises" class="lotus-form-note">Tài khoản chưa được xếp làm tổ trưởng của tổ nào trong đội này.</p>
   <div v-if="canEnter" class="work-bunch__kinds">
    <UiButton v-for="(label,kind) in kindLabels" :key="kind" type="button" variant="outline" @click="entry={kind,team:sheet.teams[0]?.name}">{{label}}</UiButton>
   </div>
   <p v-if="summary" class="lotus-form-note">{{summary}}</p>
   <p v-if="!rows.length&&!suckers.length" class="lotus-form-note">Ngày này chưa có số nào. Bấm một việc ở trên để nhập.</p>
   <div v-if="supervises" class="work-bunch__actions"><UiButton type="button" :disabled="!ready||saving" @click="confirmDay">{{saving?'Đang xác nhận…':'Xác nhận '+ready+' dòng'}}</UiButton><UiButton type="button" variant="outline" @click="stockOpen=true">Tồn theo màu dây</UiButton></div>

   <ul v-if="suckers.length" class="work-bunch__locked">
    <li v-for="e in suckers" :key="e.name">{{e.block_code}} · Chọn chồi {{amountText(e.qty)}} ha, ước tính {{amountText(e.estimate)}} chồi · {{e.team_name}} · {{e.entered_name}}</li>
   </ul>

   <ListPage v-if="!mobile&&rows.length" :rows="rows" :columns="columns" :loading="busy" :searchable="false" row-key="name" storage-key="field-bunch-day" title="Số đã nhập trong ngày" interactive @open="openRow" @refresh="load"/>
   <div v-else-if="rows.length" class="work-bunch__cards">
    <article v-for="r in rows" :key="r.name" class="work-bunch__card" :class="{'is-confirmed':r.state==='Confirmed'}">
     <strong>{{r.block_code}} · {{r.label}} · {{amountText(r.qty)}} buồng<template v-if="r.weight_kg"> · {{amountText(r.weight_kg)}} kg</template></strong>
     <span v-if="r.detail">{{r.detail}}</span>
     <span>{{r.team_name}} · {{r.entered_name}} · {{stateLabels[r.state]}}</span>
     <UiButton v-if="editable(r)" type="button" size="sm" variant="ghost" @click="openRow(r)">{{r.state==='Confirmed'?'Sửa có lý do':'Sửa'}}</UiButton>
    </article>
   </div>
  </template>

  <ModalForm :model-value="stockOpen" title="Tồn theo màu dây" width="720px" readonly @update:model-value="v=>stockOpen=v"><BunchStockCards v-if="stockOpen" :farm="farm"/></ModalForm>

  <ModalForm class="work-bunch-modal" :model-value="statusOpen" :title="status?'Cần kiểm tra · '+formatDate(status.date):'Cần kiểm tra'" width="560px" readonly @update:model-value="v=>statusOpen=v">
   <template v-if="status">
    <h3 class="work-bunch__section">Lô có phiếu mà chưa có số</h3>
    <ul v-if="status.not_reported.length" class="work-bunch__locked"><li v-for="r in status.not_reported" :key="r.block">{{r.block}} · {{r.team}}</li></ul>
    <p v-else class="lotus-form-note">Không có.</p>
    <h3 class="work-bunch__section">Số bất thường</h3>
    <ul v-if="status.anomalies.length" class="work-bunch__locked"><li v-for="(a,i) in status.anomalies" :key="i"><strong>{{a.block}}:</strong> {{a.message}}</li></ul>
    <p v-else class="lotus-form-note">Không có.</p>
   </template>
  </ModalForm>

  <WorkBunchSheet v-if="entry&&sheet" :key="entry.kind+entry.team" :farm="farm" :crew="crew" :date="day" :sheet="sheet" :kind="entry.kind" :initial-team="entry.team" :mobile="mobile" @close="entry=null" @saved="entrySaved"/>

  <ModalForm class="work-bunch-modal" :model-value="!!fix" :title="fix?'Sửa số '+fix.row.block_code+' · '+fix.row.label:'Sửa số'" width="520px" :busy="fixBusy" :error="fixError" submit-label="Lưu sửa đổi" @update:model-value="v=>!v&&(fix=null)" @submit="submitFix">
   <FormGrid v-if="fix" :columns="1">
    <LotusField v-model="fix.qty" label="Số đúng" type="number" inputmode="numeric" hint="Nhập 0 nếu dòng này nhập nhầm." :mobile="mobile"/>
    <LotusField v-if="fix.row.event_type===HARVEST" v-model="fix.weight_kg" label="Khối lượng (kg)" type="number" inputmode="decimal" :mobile="mobile"/>
    <LotusField v-model="fix.reason" label="Lý do sửa" required :mobile="mobile"/>
   </FormGrid>
  </ModalForm>
 </section>
</template>

<style>
.work-bunch{display:grid;gap:12px;min-width:0}
.work-bunch__kinds{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;max-width:720px}
.work-bunch--mobile .work-bunch__kinds{grid-template-columns:repeat(2,minmax(0,1fr));max-width:none}
.work-bunch__actions{display:flex;gap:8px;flex-wrap:wrap}
.work-bunch__checks{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;width:100%;padding:10px 12px;border:1px solid var(--lotus-warning);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);color:var(--lotus-text);font:inherit;text-align:left;cursor:pointer}
.work-bunch__checks span{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.work-bunch__section{margin:0;font-size:var(--lotus-text-sm);font-weight:600}
.work-bunch__cards{display:grid;gap:8px}
.work-bunch__card{display:grid;gap:2px;justify-items:start;padding:10px 12px;border:1px solid var(--lotus-border);border-left-width:4px;border-left-color:var(--lotus-warning);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.work-bunch__card.is-confirmed{border-left-color:var(--lotus-success)}
.work-bunch__card strong{color:var(--lotus-text-strong);font-weight:600}
.work-bunch__card span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
</style>
