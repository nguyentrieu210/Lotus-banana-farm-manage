<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import ListPage from '../ListPage.vue'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import ModalForm from '../form/ModalForm.vue'
import {Button as UiButton} from '../ui/button'
import WorkTicket from './WorkTicket.vue'
import {formatDate} from '../../format'
import {payModes,payShort,groups,capBases,states,money,amountText} from '../../field-work-model.js'
// Giao việc theo lô for one đội: one phiếu per lô × việc × tổ. How the việc is paid, its price and its cap come from
// the catalogue and are shown read-only. The đội trưởng (or quản lý vườn) gives work; tổ trưởng see their tổ's phiếu.
// Tapping a phiếu opens it (báo xong, duyệt, trả lại, đổi tổ, huỷ, nghiệm thu). Shared by desktop and /work.
const props=defineProps({farm:{type:String,required:true},crew:{type:String,required:true},setup:{type:Object,required:true},mobile:Boolean})
const emit=defineEmits(['changed'])
const api=(name,args={},write=false)=>call('lotus_farm.field_report.'+name,args,write)
const rows=ref([]),loading=ref(false),error=ref(''),notice=ref('')
const stateFilter=ref('open'),teamFilter=ref(''),detail=ref(null)
const form=ref(null),formBusy=ref(false),formError=ref('')

const canAssign=computed(()=>(props.setup.supervised_crews||[]).includes(props.crew))
const crewDoc=computed(()=>props.setup.crews.find(c=>c.name===props.crew))
const zones=computed(()=>crewDoc.value?.zones||[])
const crewBlocks=computed(()=>props.setup.blocks.filter(b=>zones.value.includes(b.zone)))
const teams=computed(()=>props.setup.teams.filter(t=>t.lotus_parent_team===props.crew&&t.active))
const teamOptions=computed(()=>teams.value.map(t=>({value:t.name,label:t.team_name+(t.leader_name?' · '+t.leader_name:'')})))
const works=computed(()=>Object.fromEntries(props.setup.works.map(w=>[w.name,w])))
const workOptions=computed(()=>props.setup.works.map(w=>({value:w.name,label:w.work_name+' · '+payShort[w.pay_mode]+(w.pay_mode!=='Daywork'&&!w.rate?' (chưa có giá)':'')})))
const stateOptions=[{value:'open',label:'Đang làm'},{value:'Reported',label:'Chờ duyệt'},{value:'Approved',label:'Chờ nghiệm thu'},{value:'Locked',label:'Đã khoá'},{value:'Cancelled',label:'Đã huỷ'},{value:'',label:'Tất cả'}]
const teamFilterOptions=computed(()=>[{value:'',label:'Tất cả tổ'},...teamOptions.value])
const columns=[
 {field:'block_code',headerName:'Lô',minWidth:70},
 {field:'work_name',headerName:'Công việc',minWidth:180},
 {field:'team_name',headerName:'Tổ',minWidth:100},
 {field:'pay_mode',headerName:'Cách trả',valueGetter:p=>payShort[p.data.pay_mode]||'',minWidth:100},
 {field:'display',headerName:'Trạng thái',valueGetter:p=>states[p.data.display]||p.data.display,minWidth:130},
 {field:'assigned_on',headerName:'Ngày giao',valueFormatter:p=>formatDate(p.value),minWidth:100},
 {field:'due_date',headerName:'Hạn',valueFormatter:p=>formatDate(p.value),minWidth:100},
 {field:'progress',headerName:'Đã báo',valueGetter:p=>(p.data.progress?.days||0)+' ngày · '+amountText(p.data.progress?.qty),minWidth:140},
 {field:'amount',headerName:'Tiền khoán',valueFormatter:p=>p.value?money(p.value):'',minWidth:120},
]
async function load(){
 if(!props.farm||!props.crew)return
 loading.value=true;error.value=''
 try{rows.value=await api('assignments',{farm:props.farm,crew:props.crew,state:stateFilter.value||null,team:teamFilter.value||null})}
 catch(e){error.value=e.message}
 finally{loading.value=false}
}
watch(()=>[props.farm,props.crew,stateFilter.value,teamFilter.value],load,{immediate:true})

const chosen=computed(()=>works.value[form.value?.work_type])
const taken=computed(()=>new Set(rows.value.filter(r=>['Open','Reported','Approved','Failed'].includes(r.state)&&r.work_type===form.value?.work_type).map(r=>r.farm_block)))
const zoneGroups=computed(()=>zones.value.map(z=>({zone:z,blocks:crewBlocks.value.filter(b=>b.zone===z)})).filter(g=>g.blocks.length))
const pickedList=computed(()=>Object.entries(form.value?.picked||{}).filter(([b,on])=>on&&!taken.value.has(b)).map(([b])=>b))
function newAssignment(){formError.value='';form.value={work_type:'',team:teams.value.length===1?teams.value[0].name:'',due_date:'',picked:{}};if(stateFilter.value!=='open')stateFilter.value='open'}
function pickZone(zone,on){for(const b of crewBlocks.value.filter(x=>x.zone===zone))if(!taken.value.has(b.name))form.value.picked[b.name]=on}
async function submitAssignment(){
 const f=form.value
 if(!f.work_type||!f.team||!pickedList.value.length){formError.value='Chọn công việc, tổ và ít nhất một lô.';return}
 formBusy.value=true;formError.value=''
 try{const r=await api('assign',{farm:props.farm,crew:props.crew,work_type:f.work_type,team:f.team,blocks:JSON.stringify(pickedList.value),due_date:f.due_date||null},true)
  form.value=null;notice.value='Đã giao '+r.created.length+' lô.';emit('changed');await load()}
 catch(e){formError.value=e.message}
 finally{formBusy.value=false}
}
</script>

<template>
 <section class="field-assign" :class="{'field-assign--mobile':mobile}" :aria-busy="loading">
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="field-report__notice" role="status">{{notice}}</p>
  <p v-if="!teams.length" class="field-report__warning" role="status">Đội chưa có tổ. Xếp tổ ở Đội, tổ &amp; lô trước khi giao.</p>
  <ListPage v-if="!mobile" :rows="rows" :columns="columns" :loading="loading" :searchable="false" row-key="name" storage-key="field-work-tickets" title="Phiếu giao việc" interactive @open="r=>detail=r.name" @refresh="load">
   <template #filters><LotusField v-model="stateFilter" type="select" :searchable="false" aria-label="Trạng thái" :options="stateOptions" empty-option="Tất cả"/><LotusField v-model="teamFilter" type="select" :searchable="false" aria-label="Tổ" :options="teamFilterOptions" empty-option="Tất cả tổ"/></template>
   <template v-if="canAssign" #actions><UiButton type="button" :disabled="!teams.length" @click="newAssignment">Giao việc</UiButton></template>
   <template #before><p class="lotus-form-note">Mỗi lô một phiếu. Cách trả đi theo loại việc trong danh mục. Bấm một phiếu để xem, duyệt, trả lại, đổi tổ hoặc huỷ.</p></template>
  </ListPage>
  <template v-else>
   <div class="field-assign__bar">
    <LotusField v-model="stateFilter" type="select" :searchable="false" label="Trạng thái" :options="stateOptions" empty-option="Tất cả" mobile/>
    <UiButton v-if="canAssign" type="button" :disabled="!teams.length" @click="newAssignment">Giao việc</UiButton>
   </div>
   <p v-if="!rows.length&&!loading" class="lotus-form-note">Chưa có phiếu giao.</p>
   <button v-for="r in rows" :key="r.name" type="button" class="mobile-list-card field-assign__card" @click="detail=r.name">
    <strong>{{r.block_code}} · {{r.work_name}}</strong>
    <span>{{r.team_name}} · {{payShort[r.pay_mode]}} · {{states[r.display]||r.display}}{{r.due_date?' · hạn '+formatDate(r.due_date):''}}</span>
    <span v-if="r.progress?.days">{{r.progress.days}} ngày · {{amountText(r.progress.qty)}}{{r.amount?' · '+money(r.amount):''}}</span>
   </button>
  </template>

  <ModalForm :model-value="!!form" title="Giao việc theo lô" width="760px" submit-label="Giao việc" :busy="formBusy" :error="formError" @update:model-value="v=>!v&&(form=null)" @submit="submitAssignment">
   <template v-if="form">
    <FormGrid :columns="mobile?1:3">
     <LotusField v-model="form.work_type" label="Công việc" :options="workOptions" required :mobile="mobile"/>
     <LotusField v-model="form.team" label="Tổ nhận" type="select" :searchable="false" :options="teamOptions" required :mobile="mobile"/>
     <LotusField v-model="form.due_date" label="Hạn xong" type="date" :mobile="mobile"/>
    </FormGrid>
    <p v-if="chosen" class="field-assign__mode">{{groups[chosen.group]}} · <b>{{payModes[chosen.pay_mode]}}</b><template v-if="chosen.rate"> · {{money(chosen.rate)}}</template> · trần: {{capBases[chosen.cap_basis]}}<template v-if="chosen.requires_material"> · bắt buộc ghi vật tư</template>. Cách trả đi theo việc, không đổi trên phiếu.</p>
    <div v-for="g in zoneGroups" :key="g.zone" class="field-assign__zone">
     <header><strong>Khu {{g.zone}}</strong><UiButton type="button" size="sm" variant="ghost" @click="pickZone(g.zone,true)">Chọn cả khu</UiButton><UiButton type="button" size="sm" variant="ghost" @click="pickZone(g.zone,false)">Bỏ chọn</UiButton></header>
     <div class="field-assign__lots">
      <div v-for="b in g.blocks" :key="b.name" class="field-assign__lot">
       <LotusField v-model="form.picked[b.name]" type="checkbox" :label="b.block_code" :disabled="taken.has(b.name)" :mobile="mobile"/>
       <span>{{taken.has(b.name)?'đang có phiếu việc này':amountText(b.area_ha)+' ha · '+amountText(b.trees)+' cây'}}{{b.quarantine_until?' · cách ly':''}}</span>
      </div>
     </div>
    </div>
    <p class="lotus-form-note">Đã chọn {{pickedList.length}} lô — mỗi lô thành một phiếu.</p>
   </template>
  </ModalForm>

  <ModalForm :model-value="!!detail" title="Phiếu giao việc" width="880px" :readonly="true" @update:model-value="v=>!v&&(detail=null)">
   <WorkTicket v-if="detail" :name="detail" :setup="setup" :mobile="mobile" @changed="load"/>
  </ModalForm>
 </section>
</template>

<style>
.field-assign{display:grid;gap:12px;min-width:0}
.field-assign__bar{display:flex;gap:8px;align-items:end;flex-wrap:wrap}
.field-assign__bar>*:first-child{flex:1 1 180px}
.field-assign__card{display:grid;gap:4px;width:100%;text-align:left;font:inherit;cursor:pointer}
.field-assign__card span{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.field-assign__mode{margin:4px 0 0;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.field-assign__zone{display:grid;gap:8px;margin-top:12px}
.field-assign__zone header{display:flex;align-items:center;justify-content:flex-start;gap:8px;flex-wrap:wrap}
.field-assign__zone header>*{flex:0 0 auto;width:auto}
.field-assign__lots{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px 12px}
.field-assign__lot{display:grid;gap:2px;padding:6px 8px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);min-width:0}
.field-assign__lot span{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.field-assign--mobile .field-assign__lots{grid-template-columns:repeat(2,minmax(0,1fr))}
</style>
