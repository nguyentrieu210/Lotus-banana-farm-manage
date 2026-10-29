<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import ListPage from '../ListPage.vue'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import ModalForm from '../form/ModalForm.vue'
import ReasonDialog from '../form/ReasonDialog.vue'
import {Button as UiButton} from '../ui/button'
import {useReasonDialog} from '../../use-reason-dialog'
import {formatDate} from '../../format'
import {assignmentStates,amountText} from '../../field-report-model.js'
// Giao việc theo lô for one đội: phiếu giao việc vườn (lô, việc, tổ, hạn; one phiếu per lô) and the standing chăm
// buồng assignment of each lô to a tổ. The đội trưởng (or quản lý vườn) gives, changes and cancels; tổ trưởng see their
// tổ's phiếu. Shared by the desktop workspace and the /work phone app (`mobile`).
const props=defineProps({farm:{type:String,required:true},crew:{type:String,required:true},setup:{type:Object,required:true},mobile:Boolean})
const emit=defineEmits(['changed'])
const api=(name,args={},write=false)=>call('lotus_farm.field_report.'+name,args,write)
const reason=useReasonDialog()
const tab=ref('round'),rows=ref([]),bunch=ref([]),loading=ref(false),error=ref(''),notice=ref('')
const stateFilter=ref('Open'),teamFilter=ref('')
const form=ref(null),formBusy=ref(false),formError=ref('')
const action=ref(null)
const handover=ref(null)

const canAssign=computed(()=>(props.setup.supervised_crews||[]).includes(props.crew))
const crewDoc=computed(()=>props.setup.crews.find(c=>c.name===props.crew))
const zones=computed(()=>crewDoc.value?.zones||[])
const crewBlocks=computed(()=>props.setup.blocks.filter(b=>zones.value.includes(b.zone)))
const teams=computed(()=>props.setup.teams.filter(t=>t.lotus_parent_team===props.crew&&t.active))
const teamOptions=computed(()=>teams.value.map(t=>({value:t.name,label:t.team_name+(t.leader_name?' · '+t.leader_name:'')})))
const teamName=name=>props.setup.teams.find(t=>t.name===name)?.team_name||name||'—'
const fieldWorks=computed(()=>props.setup.works.filter(w=>w.section==='Field').map(w=>({value:w.name,label:w.work_name+(w.rate?'':' (chưa có giá khoán)')})))
const stateOptions=[{value:'Open',label:'Đang giao'},{value:'Done',label:'Đã xong'},{value:'Cancelled',label:'Đã huỷ'},{value:'',label:'Tất cả'}]
const teamFilterOptions=computed(()=>[{value:'',label:'Tất cả tổ'},...teamOptions.value])
const progressText=p=>p?.days?p.days+' ngày · '+amountText(p.workdays)+' công · '+amountText(p.qty):'—'

const columns=[
 {field:'block_code',headerName:'Lô',minWidth:70},
 {field:'work_name',headerName:'Công việc',minWidth:180},
 {field:'team_name',headerName:'Tổ',minWidth:110},
 {field:'display',headerName:'Trạng thái',valueGetter:p=>assignmentStates[p.data.display]||p.data.display,minWidth:120},
 {field:'assigned_on',headerName:'Ngày giao',valueFormatter:p=>formatDate(p.value),minWidth:105},
 {field:'due_date',headerName:'Hạn xong',valueFormatter:p=>formatDate(p.value),minWidth:105},
 {field:'progress',headerName:'Đã báo',valueGetter:p=>progressText(p.data.progress),minWidth:190},
 {field:'done_date',headerName:'Ngày xong',valueFormatter:p=>formatDate(p.value),minWidth:105},
 {field:'area_ha',headerName:'Diện tích (ha)',minWidth:105},
 {field:'cancel_reason',headerName:'Lý do huỷ',minWidth:150},
]

async function load(){
 if(!props.farm||!props.crew)return
 loading.value=true;error.value=''
 try{
  if(tab.value==='round')rows.value=await api('assignments',{farm:props.farm,crew:props.crew,kind:'Round',state:stateFilter.value||null,team:teamFilter.value||null})
  else bunch.value=await api('assignments',{farm:props.farm,crew:props.crew,kind:'Bunch',state:'Open'})
 }catch(e){error.value=e.message}
 finally{loading.value=false}
}
watch(()=>[props.farm,props.crew,tab.value,stateFilter.value,teamFilter.value],load,{immediate:true})

// ---- giao việc vườn
const taken=computed(()=>new Set(rows.value.filter(r=>r.state==='Open'&&r.work_type===form.value?.work_type).map(r=>r.farm_block)))
const zoneGroups=computed(()=>zones.value.map(z=>({zone:z,blocks:crewBlocks.value.filter(b=>b.zone===z)})).filter(g=>g.blocks.length))
function newAssignment(){
 formError.value=''
 form.value={work_type:'',team:teams.value.length===1?teams.value[0].name:'',due_date:'',picked:{}}
 if(stateFilter.value!=='Open'){stateFilter.value='Open'}
}
const pickedList=computed(()=>Object.entries(form.value?.picked||{}).filter(([b,on])=>on&&!taken.value.has(b)).map(([b])=>b))
function pickZone(zone,on){for(const b of crewBlocks.value.filter(x=>x.zone===zone))if(!taken.value.has(b.name))form.value.picked[b.name]=on}
async function submitAssignment(){
 const f=form.value
 if(!f.work_type||!f.team||!pickedList.value.length){formError.value='Chọn công việc, tổ và ít nhất một lô.';return}
 formBusy.value=true;formError.value=''
 try{
  const r=await api('assign',{farm:props.farm,crew:props.crew,work_type:f.work_type,team:f.team,blocks:JSON.stringify(pickedList.value),due_date:f.due_date||null},true)
  form.value=null;notice.value='Đã giao '+r.created.length+' lô.';emit('changed');await load()
 }catch(e){formError.value=e.message}
 finally{formBusy.value=false}
}

// ---- đổi tổ / huỷ phiếu
function openRow(row){if(canAssign.value&&row.state==='Open'){formError.value='';action.value={row,team:row.work_team}}}
async function changeTeam(){
 const a=action.value
 if(a.team===a.row.work_team){action.value=null;return}
 const text=await reason.ask('Đổi tổ cho lô '+a.row.block_code,'Lý do đổi tổ')
 if(!text)return
 await run(()=>api('reassign',{name:a.row.name,team:a.team,reason:text,expected_modified:a.row.modified},true),'Đã đổi tổ.')
}
async function cancelRow(){
 const a=action.value
 const text=await reason.ask('Huỷ phiếu giao lô '+a.row.block_code+' · '+a.row.work_name,'Lý do huỷ')
 if(!text)return
 await run(()=>api('cancel_assignment',{name:a.row.name,reason:text,expected_modified:a.row.modified},true),'Đã huỷ phiếu.')
}
async function run(fn,done){
 formBusy.value=true;formError.value=''
 try{await fn();action.value=null;handover.value=null;notice.value=done;emit('changed');await load()}
 catch(e){formError.value=e.message}
 finally{formBusy.value=false}
}

// ---- giao chăm buồng
const holder=computed(()=>Object.fromEntries(bunch.value.map(a=>[a.farm_block,a])))
const bunchRows=computed(()=>crewBlocks.value.map(b=>({...b,held:holder.value[b.name]||null})))
const bunchPicked=ref({})
const bunchList=computed(()=>Object.entries(bunchPicked.value).filter(([,on])=>on).map(([b])=>b))
function openHandover(){formError.value='';handover.value={team:'',from_date:props.setup.today||'',reason:''}}
const moving=computed(()=>handover.value?bunchList.value.filter(b=>holder.value[b]&&holder.value[b].work_team!==handover.value.team):[])
async function submitHandover(){
 const h=handover.value
 if(moving.value.length&&!h.reason.trim()){formError.value='Có lô đang giao cho tổ khác: ghi lý do đổi.';return}
 await run(()=>api('bunch_assign',{farm:props.farm,crew:props.crew,blocks:JSON.stringify(bunchList.value),team:h.team||null,from_date:h.from_date||null,reason:h.reason||null},true),
  h.team?'Đã giao chăm buồng cho '+teamName(h.team)+'.':'Đã bỏ giao chăm buồng.')
 bunchPicked.value={}
}
</script>

<template>
 <section class="field-assign" :class="{'field-assign--mobile':mobile}" :aria-busy="loading">
  <div class="field-assign__tabs" role="tablist">
   <UiButton type="button" role="tab" :aria-selected="tab==='round'" :variant="tab==='round'?'default':'outline'" size="sm" @click="tab='round'">Việc vườn theo lô</UiButton>
   <UiButton type="button" role="tab" :aria-selected="tab==='bunch'" :variant="tab==='bunch'?'default':'outline'" size="sm" @click="tab='bunch'">Chăm buồng</UiButton>
  </div>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="field-report__notice" role="status">{{notice}}</p>
  <p v-if="!teams.length" class="field-report__warning" role="status">Đội chưa có tổ. Xếp tổ ở Báo cáo ngày → Đội, tổ &amp; lô trước khi giao.</p>

  <template v-if="tab==='round'">
   <ListPage v-if="!mobile" :rows="rows" :columns="columns" :loading="loading" :searchable="false" row-key="name" storage-key="field-assignments" title="Phiếu giao việc" :interactive="canAssign" @open="openRow" @refresh="load">
    <template #filters><LotusField v-model="stateFilter" type="select" :searchable="false" aria-label="Trạng thái" :options="stateOptions" empty-option="Tất cả"/><LotusField v-model="teamFilter" type="select" :searchable="false" aria-label="Tổ" :options="teamFilterOptions" empty-option="Tất cả tổ"/></template>
    <template v-if="canAssign" #actions><UiButton type="button" :disabled="!teams.length" @click="newAssignment">Giao việc</UiButton></template>
    <template #before><p class="lotus-form-note">Mỗi lô một phiếu. Tổ báo trên phiếu ở Báo cáo ngày; đội trưởng xác nhận ngày báo Xong thì phiếu đóng và tiền khoán cả lô được tính. Bấm một phiếu đang giao để đổi tổ hoặc huỷ.</p></template>
   </ListPage>
   <template v-else>
    <div class="field-assign__bar">
     <LotusField v-model="stateFilter" type="select" :searchable="false" label="Trạng thái" :options="stateOptions" empty-option="Tất cả" mobile/>
     <UiButton v-if="canAssign" type="button" :disabled="!teams.length" @click="newAssignment">Giao việc</UiButton>
    </div>
    <p v-if="!rows.length&&!loading" class="lotus-form-note">Chưa có phiếu giao.</p>
    <button v-for="r in rows" :key="r.name" type="button" class="mobile-list-card field-assign__card" :disabled="!canAssign||r.state!=='Open'" @click="openRow(r)">
     <strong>{{r.block_code}} · {{r.work_name}}</strong>
     <span>{{r.team_name}} · {{assignmentStates[r.display]}}{{r.due_date?' · hạn '+formatDate(r.due_date):''}}</span>
     <span v-if="r.progress?.days">{{progressText(r.progress)}}</span>
    </button>
   </template>
  </template>

  <template v-else>
   <p class="lotus-form-note">Mỗi lô giao cố định cho một tổ chăm buồng đến khi đổi. Công khoán buồng (vặt râu, bao buồng, chống đổ) chỉ báo được trên lô của tổ mình.</p>
   <div v-if="canAssign" class="field-assign__bar"><UiButton type="button" :disabled="!bunchList.length||!teams.length" @click="openHandover">Giao {{bunchList.length||''}} lô cho tổ…</UiButton></div>
   <div class="field-assign__lots">
    <div v-for="b in bunchRows" :key="b.name" class="field-assign__lot">
     <LotusField v-if="canAssign" v-model="bunchPicked[b.name]" type="checkbox" :label="b.block_code" :mobile="mobile"/>
     <strong v-else>{{b.block_code}}</strong>
     <span>{{b.held?teamName(b.held.work_team)+' · từ '+formatDate(b.held.assigned_on):'Chưa giao'}}</span>
    </div>
   </div>
  </template>

  <ModalForm :model-value="!!form" title="Giao việc theo lô" width="760px" submit-label="Giao việc" :busy="formBusy" :error="formError" @update:model-value="v=>!v&&(form=null)" @submit="submitAssignment">
   <template v-if="form">
    <FormGrid :columns="mobile?1:3">
     <LotusField v-model="form.work_type" label="Công việc" :options="fieldWorks" required :mobile="mobile"/>
     <LotusField v-model="form.team" label="Tổ nhận" type="select" :searchable="false" :options="teamOptions" required :mobile="mobile"/>
     <LotusField v-model="form.due_date" label="Hạn xong" type="date" :mobile="mobile"/>
    </FormGrid>
    <div v-for="g in zoneGroups" :key="g.zone" class="field-assign__zone">
     <header><strong>Khu {{g.zone}}</strong><UiButton type="button" size="sm" variant="ghost" @click="pickZone(g.zone,true)">Chọn cả khu</UiButton><UiButton type="button" size="sm" variant="ghost" @click="pickZone(g.zone,false)">Bỏ chọn</UiButton></header>
     <div class="field-assign__lots">
      <div v-for="b in g.blocks" :key="b.name" class="field-assign__lot">
       <LotusField v-model="form.picked[b.name]" type="checkbox" :label="b.block_code" :disabled="taken.has(b.name)" :mobile="mobile"/>
       <span>{{taken.has(b.name)?'đang giao việc này':amountText(b.area_ha)+' ha · '+amountText(b.trees)+' cây'}}</span>
      </div>
     </div>
    </div>
    <p class="lotus-form-note">Đã chọn {{pickedList.length}} lô — mỗi lô thành một phiếu.</p>
   </template>
  </ModalForm>

  <ModalForm :model-value="!!action" :title="action?'Lô '+action.row.block_code+' · '+action.row.work_name:''" width="560px" :busy="formBusy" :error="formError" submit-label="Đổi tổ" @update:model-value="v=>!v&&(action=null)" @submit="changeTeam">
   <template v-if="action">
    <p class="lotus-form-note">{{assignmentStates[action.row.display]}} · giao {{formatDate(action.row.assigned_on)}}{{action.row.due_date?' · hạn '+formatDate(action.row.due_date):''}} · {{progressText(action.row.progress)}}</p>
    <LotusField v-model="action.team" label="Tổ nhận" type="select" :searchable="false" :options="teamOptions" :mobile="mobile"/>
    <UiButton type="button" variant="outline" :disabled="formBusy" @click="cancelRow">Huỷ phiếu này</UiButton>
   </template>
  </ModalForm>

  <ModalForm :model-value="!!handover" title="Giao chăm buồng" width="560px" submit-label="Lưu" :busy="formBusy" :error="formError" @update:model-value="v=>!v&&(handover=null)" @submit="submitHandover">
   <template v-if="handover">
    <p class="lotus-form-note">{{bunchList.length}} lô: {{bunchRows.filter(b=>bunchList.includes(b.name)).map(b=>b.block_code).join(', ')}}</p>
    <FormGrid :columns="1">
     <LotusField v-model="handover.team" label="Tổ chăm buồng" type="select" :searchable="false" :options="[{value:'',label:'Bỏ giao (không tổ nào)'},...teamOptions]" :mobile="mobile"/>
     <LotusField v-model="handover.from_date" label="Từ ngày" type="date" required :mobile="mobile"/>
     <LotusField v-if="moving.length" v-model="handover.reason" label="Lý do đổi tổ" type="textarea" required maxlength="500" :mobile="mobile" :hint="moving.length+' lô đang giao cho tổ khác'"/>
    </FormGrid>
   </template>
  </ModalForm>
  <ReasonDialog :dialog="reason"/>
 </section>
</template>

<style>
.field-assign{display:grid;gap:12px;min-width:0}
.field-assign__tabs,.field-assign__bar{display:flex;gap:8px;align-items:end;flex-wrap:wrap}
.field-assign__bar>*:first-child{flex:1 1 180px}
.field-assign__card{display:grid;gap:4px;width:100%;text-align:left;font:inherit;cursor:pointer}
.field-assign__card span{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.field-assign__zone{display:grid;gap:8px;margin-top:12px}
.field-assign__zone header{display:flex;align-items:center;justify-content:flex-start;gap:8px;flex-wrap:wrap}
.field-assign__zone header>*{flex:0 0 auto;width:auto}
.field-assign__lots{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px 12px}
.field-assign__lot{display:grid;gap:2px;padding:6px 8px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);min-width:0}
.field-assign__lot span{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.field-assign--mobile .field-assign__lots{grid-template-columns:repeat(2,minmax(0,1fr))}
</style>
