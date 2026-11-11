<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import ModalForm from '../form/ModalForm.vue'
import DataTable from '../DataTable.vue'
import {Button as UiButton} from '../ui/button'
import {formatDate} from '../../format'
// Vòng chăm sóc of one đội (lotus_farm.care_cycle.due): per việc, how many lô are late, due in the period, given to a tổ.
// A việc opens its lô in a dialog; the đội trưởng ticks lô and gives them to one tổ at once (one phiếu per lô).
// The lô × việc table is behind a button. Shared by desktop and /work.
const props=defineProps({farm:{type:String,required:true},crew:{type:String,required:true},mobile:Boolean})
const emit=defineEmits(['assigned'])
const horizon=ref('week'),data=ref(null),busy=ref(false),error=ref(''),notice=ref('')
const opened=ref(null),picked=ref({}),team=ref(''),dueDate=ref(''),saving=ref(false),formError=ref(''),showMatrix=ref(false)
const iso=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')
function until(){if(horizon.value==='week')return undefined;const d=new Date();d.setDate(d.getDate()+Number(horizon.value));return iso(d)}
const horizonOptions=[{value:'week',label:'Tuần này'},{value:'13',label:'Hai tuần tới'},{value:'27',label:'Bốn tuần tới'}]
let asked=0
async function load(){
 const mine=++asked
 busy.value=true;error.value=''
 try{const result=await call('lotus_farm.care_cycle.due',{farm:props.farm,crew:props.crew,to_date:until()});if(mine===asked)data.value=result}
 catch(e){if(mine===asked){error.value=e.message;data.value=null}}
 finally{if(mine===asked)busy.value=false}
}
watch(()=>[props.farm,props.crew,horizon.value],load,{immediate:true})

const statusText=r=>r.status==='overdue'?'Quá hạn '+r.overdue_days+' ngày':r.status==='due'?'Đến hạn '+formatDate(r.due_date):'Hạn '+formatDate(r.due_date)
const lastText=r=>r.last_done?'xong lần trước '+formatDate(r.last_done):'chưa làm lần nào'
const cards=computed(()=>data.value?.summary||[])
const canAssign=computed(()=>!!data.value?.can_assign)
const teamOptions=computed(()=>(data.value?.teams||[]).map(t=>({value:t.name,label:t.team_name})))
const lots=computed(()=>opened.value?(data.value?.rows||[]).filter(r=>r.work_type===opened.value.work_type&&(r.status!=='later'||r.assignment)):[])
const free=computed(()=>lots.value.filter(r=>!r.assignment))
const chosen=computed(()=>free.value.filter(r=>picked.value[r.farm_block]).map(r=>r.farm_block))
function open(card){
 opened.value=card;formError.value='';notice.value='';picked.value={}
 team.value=teamOptions.value.length===1?teamOptions.value[0].value:'';dueDate.value=data.value?.until||''
}
function pickAll(on){picked.value=on?Object.fromEntries(free.value.map(r=>[r.farm_block,true])):{}}
// The lô of the dialog by khu, late first within a khu, so a whole khu can be ticked at once.
const groups=computed(()=>{
 const by={}
 for(const r of lots.value)(by[r.zone]||(by[r.zone]=[])).push(r)
 return Object.keys(by).sort().map(zone=>({zone,rows:by[zone].sort((a,b)=>a.due_date.localeCompare(b.due_date)||natural(a,b)),free:by[zone].filter(r=>!r.assignment).length}))
})
function pickZone(zone,on){for(const r of free.value.filter(x=>x.zone===zone))picked.value[r.farm_block]=on}
async function give(){
 if(!team.value||!chosen.value.length){formError.value='Chọn tổ và ít nhất một lô.';return}
 saving.value=true;formError.value=''
 try{
  const result=await call('lotus_farm.care_cycle.assign',{farm:props.farm,crew:props.crew,work_type:opened.value.work_type,team:team.value,
   blocks:JSON.stringify(chosen.value),due_date:dueDate.value||null},true)
  const name=teamOptions.value.find(t=>t.value===team.value)?.label||''
  notice.value='Đã giao '+opened.value.work_name.toLowerCase()+' '+result.created.length+' lô cho '+name+'.'
  opened.value=null;emit('assigned');await load()
 }catch(e){formError.value=e.message}
 finally{saving.value=false}
}

const cellText=c=>(c.status==='overdue'?'Quá '+c.overdue_days+' ngày':(c.status==='due'?'Đến hạn ':'')+formatDate(c.due_date))+(c.team_name?' · '+c.team_name:'')
const natural=(a,b)=>String(a.zone).localeCompare(String(b.zone))||String(a.code).length-String(b.code).length||String(a.code).localeCompare(String(b.code))
const matrixRows=computed(()=>{
 const by={}
 for(const r of data.value?.rows||[]){const row=by[r.farm_block]||(by[r.farm_block]={key:r.farm_block,code:r.code,zone:r.zone});row[r.work_type]=r}
 return Object.values(by).sort(natural)
})
const matrixColumns=computed(()=>[{field:'code',headerName:'Lô',pinned:'left',minWidth:70},
 ...cards.value.map(s=>({field:s.work_type,headerName:s.work_name,minWidth:160,sortable:false,valueGetter:p=>p.data?.[s.work_type]?cellText(p.data[s.work_type]):''}))])
</script>

<template>
 <section class="care-due" :class="{'care-due--mobile':mobile}" :aria-busy="busy">
  <div class="care-due__tools">
   <LotusField v-model="horizon" label="Đến hạn trong" type="select" :searchable="false" :options="horizonOptions" :empty-option="null" :mobile="mobile"/>
   <UiButton v-if="!mobile&&data?.rows?.length" type="button" variant="outline" @click="showMatrix=true">Bảng lô × việc</UiButton>
  </div>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="stock-success" role="status">{{notice}}</p>
  <p v-if="data&&!data.has_rules" class="lotus-form-note">Chưa có vòng chăm sóc nào. Quản lý vườn đặt vòng cho từng việc ở <a href="/lotus/cong-viec?field_view=cycles">Vòng chăm sóc</a>.</p>
  <p v-else-if="data&&!cards.length" class="lotus-form-note">Chưa có việc nào có vòng cho các lô của đội.</p>
  <div class="care-due__cards">
   <button v-for="c in cards" :key="c.work_type" type="button" class="care-due__card" :class="{'is-late':c.overdue,'is-due':!c.overdue&&c.due}" @click="open(c)">
    <strong>{{c.work_name}}</strong>
    <span><b v-if="c.overdue" class="care-due__late">{{c.overdue}} lô quá hạn</b><template v-if="c.overdue&&c.due"> · </template><template v-if="c.due">{{c.due}} lô đến hạn</template><template v-if="!c.overdue&&!c.due">Chưa lô nào đến hạn</template></span>
    <span>{{c.given}} lô đã giao · {{c.to_give}} lô chưa giao</span>
   </button>
  </div>

  <ModalForm :model-value="!!opened" :title="opened?(canAssign?'Giao ':'')+opened.work_name:''" width="760px" submit-label="Giao cho tổ" :busy="saving" :error="formError"
   :readonly="!canAssign" :submit-disabled="!chosen.length" @update:model-value="v=>!v&&(opened=null)" @submit="give">
   <template v-if="opened">
    <FormGrid v-if="canAssign" :columns="mobile?1:2">
     <LotusField v-model="team" label="Tổ nhận" type="select" :searchable="false" :options="teamOptions" required :mobile="mobile"/>
     <LotusField v-model="dueDate" label="Hạn xong" type="date" :mobile="mobile"/>
    </FormGrid>
    <div v-if="canAssign&&free.length" class="care-due__pick">
     <UiButton type="button" size="sm" variant="ghost" @click="pickAll(true)">Chọn hết lô chưa giao</UiButton>
     <UiButton type="button" size="sm" variant="ghost" @click="pickAll(false)">Bỏ chọn</UiButton>
    </div>
    <p v-if="!lots.length" class="lotus-form-note">Không có lô nào đến hạn việc này trong khoảng đã chọn.</p>
    <div v-for="g in groups" :key="g.zone" class="care-due__zone">
     <header><strong>Khu {{g.zone}}</strong>
      <template v-if="canAssign&&g.free"><UiButton type="button" size="sm" variant="ghost" @click="pickZone(g.zone,true)">Chọn cả khu</UiButton>
       <UiButton type="button" size="sm" variant="ghost" @click="pickZone(g.zone,false)">Bỏ chọn khu</UiButton></template></header>
     <ul class="care-due__lots">
      <li v-for="r in g.rows" :key="r.farm_block" :class="{'is-late':r.status==='overdue','is-given':!!r.assignment}">
       <LotusField v-if="canAssign&&!r.assignment" v-model="picked[r.farm_block]" type="checkbox" :label="'Lô '+r.code" :mobile="mobile"/>
       <strong v-else>Lô {{r.code}}</strong>
       <span>{{statusText(r)}} · {{lastText(r)}}<template v-if="r.assignment"> · đã giao {{r.team_name}}</template></span>
      </li>
     </ul>
    </div>
    <p v-if="canAssign" class="lotus-form-note">Đã chọn {{chosen.length}} lô: mỗi lô thành một phiếu của tổ, tổ báo xong cả lô thì lô sang vòng sau.</p>
   </template>
  </ModalForm>

  <ModalForm :model-value="showMatrix" title="Bảng lô × việc" width="1100px" readonly @update:model-value="v=>showMatrix=v">
   <DataTable :rows="matrixRows" :columns="matrixColumns" row-key="key" storage-key="care-due-matrix" :totals="false" :selection-enabled="false" :paginate="false"
    export-title="Vòng chăm sóc lô × việc"/>
  </ModalForm>
 </section>
</template>

<style>
.care-due{display:grid;gap:12px;min-width:0}
.care-due__tools{display:flex;gap:12px;align-items:end;flex-wrap:wrap}
.care-due__tools>*:first-child{min-width:180px}
.care-due__cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
.care-due--mobile .care-due__cards{grid-template-columns:1fr}
/* Spec 004: kit card look — token radius, shadow and tone accent. */
.care-due__card{display:grid;gap:4px;padding:12px 14px;text-align:left;font:inherit;color:inherit;border:1px solid var(--lotus-border);border-left:4px solid var(--lotus-tone-info-solid);border-radius:var(--lotus-card-radius);background:var(--lotus-surface);box-shadow:var(--lotus-shadow-xs);cursor:pointer;transition:box-shadow var(--lotus-motion) var(--lotus-ease),border-color var(--lotus-motion) var(--lotus-ease)}
.care-due__card:hover{border-color:var(--lotus-border-strong);box-shadow:var(--lotus-shadow-md)}
.care-due__card:focus-visible{outline:none;box-shadow:var(--lotus-focus)}
.care-due__card.is-due{border-left-color:var(--lotus-warning-400)}
.care-due__card.is-late{border-left-color:var(--lotus-tone-danger-solid)}
.care-due__card strong{color:var(--lotus-text-strong);font-size:var(--lotus-text-base)}
.care-due__card span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.care-due__late{color:var(--lotus-tone-danger-text);font-weight:var(--lotus-weight-bold)}
.care-due__pick{display:flex;gap:8px;flex-wrap:wrap}
.care-due__zone{display:grid;gap:6px;margin-top:8px}
.care-due__zone header{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.care-due__zone header>*{flex:0 0 auto;width:auto}
.care-due__lots{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:6px}
.care-due--mobile .care-due__lots{grid-template-columns:1fr}
.care-due__lots li{display:grid;gap:2px;padding:8px 10px;border:1px solid var(--lotus-border);border-left:3px solid var(--lotus-warning-400);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.care-due__lots li.is-late{border-left-color:var(--lotus-tone-danger-solid)}
.care-due__lots li.is-given{border-left-color:var(--lotus-tone-success-solid);background:var(--lotus-soft)}
.care-due__lots li span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
</style>
