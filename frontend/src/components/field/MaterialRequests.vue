<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {call} from '../../api'
import ModalForm from '../form/ModalForm.vue'
import LotusField from '../form/LotusField.vue'
import {Button as UiButton} from '../ui/button'
import MaterialRequestForm from './MaterialRequestForm.vue'
import MaterialRequestDetail from './MaterialRequestDetail.vue'
import {formatDate} from '../../format'
import {unitLabel} from '../../units'
import {COUNT_CARDS,STATE_LABELS,countRequests,inGroup,stateKey,stateLabel,stateTone,isOverdue,blockList,crewTeam,qtyText} from '../../issue-request-model.js'
// Yêu cầu cấp vật tư của một đội (lotus_farm.issue_request.requests), dạng thẻ:
//  - compact + view="approve": một thẻ "N yêu cầu vật tư chờ bạn duyệt" (Hôm nay, tab Xác nhận); ẩn khi không có.
//  - compact: thẻ đếm (Chờ bạn duyệt · Chờ duyệt · Trả lại · Chờ cấp · Đang cấp · Đã cấp 7 ngày), nút "Đề nghị cấp vật tư".
//  - đầy đủ: lọc tổ, trạng thái, khoảng ngày cần, tìm trên một hàng, rồi lưới thẻ.
// Bấm thẻ đếm mở hộp danh sách; bấm một yêu cầu mở hộp chi tiết. Ai được lập/duyệt do máy chủ trả về.
const props=defineProps({farm:{type:String,required:true},crew:{type:String,required:true},setup:Object,view:{type:String,default:'open'},team:String,assignment:String,compact:Boolean,mobile:Boolean,initialRequest:String,showAll:Boolean,prefill:Object})
const emit=defineEmits(['all','changed'])
const data=ref(null),busy=ref(false),error=ref(''),notice=ref('')
const teamFilter=ref(props.team||''),stateFilter=ref(''),from=ref(''),to=ref(''),search=ref('')
const group=ref(null),detail=ref(null),formState=ref(null)
let asked=0
async function load(){
 if(!props.farm||!props.crew)return
 const mine=++asked
 busy.value=true;error.value=''
 try{
  const r=await call('lotus_farm.issue_request.requests',{farm:props.farm,crew:props.crew,team:teamFilter.value||null,view:props.view,assignment:props.assignment||null,from_date:from.value||null,to_date:to.value||null})
  if(mine===asked)data.value=Array.isArray(r)?{rows:r}:r
 }catch(e){if(mine===asked){error.value=e.message;data.value=null}}
 finally{if(mine===asked)busy.value=false}
}
watch(()=>[props.farm,props.crew,props.view,props.assignment,teamFilter.value,from.value,to.value],load,{immediate:true})
onMounted(()=>{if(props.initialRequest)detail.value=props.initialRequest})

const rows=computed(()=>data.value?.rows||[])
const today=computed(()=>data.value?.today||'')
const counts=computed(()=>countRequests(rows.value,data.value?.counts))
const supervises=computed(()=>(props.setup?.supervised_crews||[]).includes(props.crew)||!!props.setup?.manager)
const canCreate=computed(()=>!!(data.value?.can_create??supervises.value))
const teamOptions=computed(()=>[{value:'',label:'Tất cả tổ'},...(props.setup?.teams||[]).filter(t=>t.lotus_parent_team===props.crew&&t.active!==0).map(t=>({value:t.name,label:t.team_name}))])
const stateOptions=[{value:'',label:'Mọi trạng thái'},...Object.entries(STATE_LABELS).map(([value,label])=>({value,label}))]
const sortKey=r=>(isOverdue(r,today.value)?'0':'1')+(r.needed||r.schedule_date||'9999')
const filtered=computed(()=>{
 const q=search.value.trim().toLowerCase()
 return rows.value.filter(r=>(!stateFilter.value||stateKey(r)===stateFilter.value)&&(!q||JSON.stringify(r).toLowerCase().includes(q))).sort((a,b)=>sortKey(a).localeCompare(sortKey(b)))
})
const groupRows=computed(()=>group.value==null?[]:rows.value.filter(r=>!group.value.key||inGroup(r,group.value.key)).sort((a,b)=>sortKey(a).localeCompare(sortKey(b))))
// In the approve view the server lists only what this user may approve.
const approveCount=computed(()=>data.value?.counts?.approve??rows.value.filter(r=>stateKey(r)==='sent').length)
const visibleCards=computed(()=>COUNT_CARDS.filter(c=>c.key!=='approve'||counts.value.approve))

function openGroup(card){group.value=card||{key:'',label:'Tất cả yêu cầu'}}
function openDetail(name){group.value=null;detail.value=name}
function openForm(prefill=null){notice.value='';formState.value={prefill}}
function edit(name){detail.value=null;formState.value={name}}
function copy(name){detail.value=null;formState.value={copyFrom:name}}
async function saved({doc,message}){formState.value=null;notice.value=message;emit('changed');await load();if(doc?.name&&!props.compact)detail.value=doc.name}
async function changed(){emit('changed');await load()}
async function deleted(){detail.value=null;notice.value='Đã xóa nháp.';await changed()}
defineExpose({openForm,openDetail,reload:load})
</script>

<template>
 <section class="issue-requests" :class="{'issue-requests--mobile':mobile,'issue-requests--compact':compact}" :aria-busy="busy">
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="field-report__notice" role="status">{{notice}}</p>

  <template v-if="compact&&view==='approve'">
   <button v-if="approveCount" type="button" class="issue-count is-warning issue-requests__approve" @click="openGroup({key:'',label:'Chờ bạn duyệt'})">
    <strong>{{approveCount}} yêu cầu vật tư chờ bạn duyệt</strong><span>Bấm để xem và duyệt</span>
   </button>
  </template>

  <template v-else-if="compact">
   <div class="issue-requests__bar">
    <UiButton v-if="canCreate" type="button" @click="openForm()">Đề nghị cấp vật tư</UiButton>
    <UiButton v-if="showAll" type="button" variant="ghost" @click="emit('all')">Xem tất cả</UiButton>
    <UiButton v-else-if="rows.length" type="button" variant="ghost" @click="openGroup(null)">Xem tất cả</UiButton>
   </div>
   <div class="issue-requests__counts">
    <button v-for="c in visibleCards" :key="c.key" type="button" class="issue-count" :class="{'is-warning':c.key==='approve'&&counts[c.key],'is-empty':!counts[c.key]}" :disabled="!counts[c.key]" @click="openGroup(c)">
     <strong>{{counts[c.key]}}</strong><span>{{c.label}}</span>
    </button>
   </div>
  </template>

  <template v-else>
   <div v-if="assignment" class="issue-requests__bar"><UiButton v-if="canCreate" type="button" @click="openForm(prefill)">Đề nghị cấp vật tư</UiButton></div>
   <div v-else class="issue-requests__filters">
    <LotusField v-if="teamOptions.length>2" v-model="teamFilter" type="select" :searchable="false" aria-label="Tổ" label="Tổ" :options="teamOptions" :empty-option="null" :mobile="mobile"/>
    <LotusField v-model="stateFilter" type="select" :searchable="false" aria-label="Trạng thái" label="Trạng thái" :options="stateOptions" :empty-option="null" :mobile="mobile"/>
    <LotusField v-if="!mobile" v-model="from" type="date" label="Cần từ ngày" aria-label="Cần từ ngày"/>
    <LotusField v-if="!mobile" v-model="to" type="date" label="Đến ngày" aria-label="Đến ngày"/>
    <LotusField v-if="!mobile" v-model="search" label="Tìm" aria-label="Tìm" placeholder="Số, lô, vật tư…"/>
    <UiButton v-if="canCreate" type="button" @click="openForm()">Đề nghị cấp vật tư</UiButton>
   </div>
   <p v-if="!filtered.length&&!busy" class="lotus-form-note">Chưa có yêu cầu cấp vật tư nào.</p>
   <div class="issue-requests__cards">
    <button v-for="r in filtered" :key="r.name" type="button" class="issue-card" :class="['is-'+stateTone(r.state),{'is-late':isOverdue(r,today)}]" @click="openDetail(r.name)">
     <strong>{{r.title||r.name}}</strong>
     <span><b class="issue-card__state">{{stateLabel(r.state)}}</b><template v-if="isOverdue(r,today)"> · <b class="issue-card__late">Quá hạn chưa cấp</b></template> · cần {{formatDate(r.needed||r.schedule_date)}}</span>
     <span>{{r.name}} · {{crewTeam(r)}}<template v-if="r.work_name"> · {{r.work_name}}</template></span>
     <span v-if="blockList(r)">Lô {{blockList(r)}}</span>
     <span v-if="assignment&&r.totals">Đề nghị {{qtyText(r.totals.required)}} · đã cấp {{qtyText(r.totals.posted)}}<template v-if="Number(r.totals.draft)"> · Kho đang lập phiếu {{qtyText(r.totals.draft)}}</template> · còn {{qtyText(Math.max(0,r.totals.required-r.totals.posted-r.totals.draft))}}</span>
     <span>{{r.warehouse_name||r.warehouse}}<template v-if="r.open_lines!=null"> · còn {{r.open_lines}} dòng</template><template v-if="r.approver_name"> · duyệt: {{r.approver_name}}</template></span>
    </button>
   </div>
  </template>

  <ModalForm :model-value="!!group" :title="group?.label||''" width="760px" readonly @update:model-value="v=>!v&&(group=null)">
   <p v-if="!groupRows.length" class="lotus-form-note">Không có yêu cầu nào.</p>
   <div class="issue-requests__cards issue-requests__cards--list">
    <button v-for="r in groupRows" :key="r.name" type="button" class="issue-card" :class="['is-'+stateTone(r.state),{'is-late':isOverdue(r,today)}]" @click="openDetail(r.name)">
     <strong>{{r.title||r.name}}</strong>
     <span><b class="issue-card__state">{{stateLabel(r.state)}}</b><template v-if="isOverdue(r,today)"> · <b class="issue-card__late">Quá hạn chưa cấp</b></template> · cần {{formatDate(r.needed||r.schedule_date)}}</span>
     <span>{{r.name}} · {{crewTeam(r)}}<template v-if="r.work_name"> · {{r.work_name}}</template><template v-if="blockList(r)"> · lô {{blockList(r)}}</template></span>
    </button>
   </div>
  </ModalForm>
  <ModalForm :model-value="!!detail" title="Yêu cầu cấp vật tư" width="880px" readonly @update:model-value="v=>!v&&(detail=null)">
   <MaterialRequestDetail v-if="detail" :name="detail" :mobile="mobile" @changed="changed" @edit="edit" @copy="copy" @deleted="deleted"/>
  </ModalForm>
  <MaterialRequestForm v-if="formState" :farm="farm" :crew="crew" :name="formState.name" :copy-from="formState.copyFrom" :prefill="formState.prefill" :mobile="mobile" @close="formState=null" @saved="saved"/>
 </section>
</template>

<style>
.issue-requests{display:grid;gap:10px;min-width:0}
.issue-requests__bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.issue-requests__filters{display:flex;gap:8px;align-items:end;flex-wrap:nowrap;overflow-x:auto}
.issue-requests__filters>*{flex:0 0 auto;min-width:140px}
.issue-requests--mobile .issue-requests__filters{flex-wrap:wrap}
.issue-requests--mobile .issue-requests__filters>*{flex:1 1 100%}
.issue-requests__counts{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px}
.issue-requests--mobile .issue-requests__counts{grid-template-columns:repeat(2,minmax(0,1fr))}
.issue-count{display:grid;gap:2px;padding:10px 12px;text-align:left;font:inherit;color:inherit;border:1px solid var(--lotus-border);border-left:4px solid var(--lotus-info);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);cursor:pointer}
.issue-count strong{font-size:var(--lotus-text-md);color:var(--lotus-text-strong)}
.issue-count span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.issue-count.is-warning{border-left-color:var(--lotus-warning)}
.issue-count.is-empty{opacity:.6;cursor:default}
.issue-requests__approve{width:100%}
.issue-requests__cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px}
.issue-requests--mobile .issue-requests__cards,.issue-requests__cards--list{grid-template-columns:1fr}
.issue-card{display:grid;gap:3px;padding:10px 12px;text-align:left;font:inherit;color:inherit;border:1px solid var(--lotus-border);border-left:4px solid var(--lotus-info);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);cursor:pointer;min-width:0}
.issue-card strong{color:var(--lotus-text-strong)}
.issue-card span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.issue-card.is-warning{border-left-color:var(--lotus-warning)}
.issue-card.is-success{border-left-color:var(--lotus-success)}
.issue-card.is-danger,.issue-card.is-late{border-left-color:var(--lotus-danger)}
.issue-card.is-neutral{border-left-color:var(--lotus-border)}
.issue-card__state{font-weight:600}
.issue-card__late{color:var(--lotus-danger)}
</style>
