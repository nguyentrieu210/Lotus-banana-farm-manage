<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import ModalForm from '../form/ModalForm.vue'
import {Button as UiButton} from '../ui/button'
import {formatDate} from '../../format'
// Vòng chăm sóc (lotus_farm.care_cycle): one việc every N days, for the farm or one khu, from a day. Each change is a new
// version waiting for approval; the approved ones are kept. One card per cycle; it opens its versions in a dialog.
const props=defineProps({farm:{type:String,required:true},mobile:Boolean})
const data=ref(null),busy=ref(false),error=ref(''),notice=ref('')
const opened=ref(''),form=ref(null),saving=ref(false),formError=ref(''),acting=ref('')
async function load(){
 busy.value=true;error.value=''
 try{data.value=await call('lotus_farm.care_cycle.rule_list',{farm:props.farm})}
 catch(e){error.value=e.message;data.value=null}
 finally{busy.value=false}
}
watch(()=>props.farm,load,{immediate:true})

const works=computed(()=>Object.fromEntries((data.value?.works||[]).map(w=>[w.name,w])))
const workOptions=computed(()=>(data.value?.works||[]).map(w=>({value:w.name,label:w.work_name})))
const zoneOptions=computed(()=>[{value:'',label:'Cả vườn'},...(data.value?.zones||[]).map(z=>({value:z,label:'Khu '+z}))])
const scopeText=r=>r.farm_zone?'khu '+r.farm_zone:'cả vườn'
const periodText=r=>'từ '+formatDate(r.valid_from)+(r.valid_to?' đến '+formatDate(r.valid_to):'')
// One card per cycle: the version in force (or the newest approved), and a draft waiting if there is one.
const cycles=computed(()=>{
 const by={}
 for(const r of data.value?.rules||[])(by[r.rule_name]||(by[r.rule_name]=[])).push(r)
 return Object.entries(by).map(([name,versions])=>{
  versions.sort((a,b)=>b.version-a.version)
  const current=versions.find(v=>v.in_force)||versions.find(v=>v.approval_state==='Approved')||null
  return {name,versions,current,draft:versions.find(v=>v.approval_state!=='Approved')||null,work:(current||versions[0]).work_type}
 }).sort((a,b)=>Number(!a.current)-Number(!b.current)||a.name.localeCompare(b.name))
})
const openedCycle=computed(()=>cycles.value.find(c=>c.name===opened.value)||null)
const today=()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}

function newCycle(){formError.value='';form.value={rule_name:'',work_type:'',farm_zone:'',repeat_days:null,valid_from:today(),valid_to:'',notes:'',fixed:false}}
function newVersion(cycle){
 const base=cycle.current||cycle.versions[0]
 formError.value='';opened.value=''
 form.value={rule_name:cycle.name,work_type:base.work_type,farm_zone:base.farm_zone||'',repeat_days:base.repeat_days,valid_from:today(),valid_to:'',notes:'',fixed:true}
}
async function save(){
 const f=form.value
 if(!f.work_type||!Number(f.repeat_days)||!f.valid_from){formError.value='Chọn việc, số ngày của vòng và ngày bắt đầu áp dụng.';return}
 saving.value=true;formError.value=''
 try{
  const saved=await call('lotus_farm.care_cycle.save_rule',{farm:props.farm,work_type:f.work_type,repeat_days:Number(f.repeat_days),valid_from:f.valid_from,
   valid_to:f.valid_to||null,farm_zone:f.farm_zone||null,rule_name:f.fixed?f.rule_name:(f.rule_name||null),notes:f.notes||null},true)
  notice.value='Đã lưu "'+saved.rule_name+'" phiên bản '+saved.version+': chờ duyệt.';form.value=null;await load()
 }catch(e){formError.value=e.message}
 finally{saving.value=false}
}
async function act(method,name,message){
 acting.value=name;error.value=''
 try{await call('lotus_farm.care_cycle.'+method,{name},true);notice.value=message;await load()}
 catch(e){error.value=e.message}
 finally{acting.value=''}
}
</script>

<template>
 <section class="care-cycles" :class="{'care-cycles--mobile':mobile}" :aria-busy="busy">
  <div class="care-cycles__tools">
   <p class="lotus-form-note">Lô đến hạn = ngày báo xong cả lô gần nhất + số ngày của vòng. Lô chưa làm lần nào đến hạn từ ngày áp dụng. Luật của khu được dùng trước luật cả vườn.</p>
   <UiButton v-if="data?.can_edit" type="button" @click="newCycle">Đặt vòng mới</UiButton>
  </div>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="stock-success" role="status">{{notice}}</p>
  <p v-if="data&&!cycles.length" class="lotus-form-note">Chưa có vòng chăm sóc nào.</p>
  <div class="care-cycles__cards">
   <button v-for="c in cycles" :key="c.name" type="button" class="care-cycles__card" :class="{'is-off':!c.current}" @click="opened=c.name">
    <strong>{{c.name}}</strong>
    <span v-if="c.current">{{c.current.repeat_days}} ngày một lần · {{scopeText(c.current)}} · {{periodText(c.current)}}</span>
    <span v-else>Chưa có phiên bản đã duyệt</span>
    <em v-if="c.draft">Chờ duyệt: {{c.draft.repeat_days}} ngày · {{periodText(c.draft)}}</em>
   </button>
  </div>

  <ModalForm :model-value="!!openedCycle" :title="openedCycle?.name||''" width="760px" readonly @update:model-value="v=>!v&&(opened='')">
   <template v-if="openedCycle">
    <p class="lotus-form-note">Việc: {{works[openedCycle.work]?.work_name||openedCycle.work}}. Phiên bản đã duyệt không sửa được; đổi vòng thì tạo phiên bản mới.</p>
    <ul class="care-cycles__versions">
     <li v-for="v in openedCycle.versions" :key="v.name" :class="{'is-current':v.in_force}">
      <div><strong>Phiên bản {{v.version}} · {{v.repeat_days}} ngày</strong>
       <span>{{scopeText(v)}} · {{periodText(v)}} · {{v.approval_state==='Approved'?(v.in_force?'Đang áp dụng':'Đã duyệt'):'Chờ duyệt'}}</span>
       <span v-if="v.notes">{{v.notes}}</span></div>
      <div v-if="data.can_edit&&v.approval_state!=='Approved'" class="care-cycles__actions">
       <UiButton type="button" size="sm" :disabled="!!acting" @click="act('approve_rule',v.name,'Đã duyệt phiên bản '+v.version+' của '+openedCycle.name+'.')">Duyệt</UiButton>
       <UiButton type="button" size="sm" variant="outline" :disabled="!!acting" @click="act('delete_rule',v.name,'Đã xóa bản chờ duyệt.')">Xóa</UiButton>
      </div>
     </li>
    </ul>
    <UiButton v-if="data.can_edit&&!openedCycle.draft" type="button" variant="outline" @click="newVersion(openedCycle)">Tạo phiên bản mới</UiButton>
   </template>
  </ModalForm>

  <ModalForm :model-value="!!form" :title="form?.fixed?'Phiên bản mới: '+form.rule_name:'Đặt vòng chăm sóc'" width="720px" submit-label="Lưu, chờ duyệt"
   :busy="saving" :error="formError" @update:model-value="v=>!v&&(form=null)" @submit="save">
   <template v-if="form">
    <FormGrid :columns="mobile?1:2">
     <LotusField v-model="form.work_type" label="Việc" :options="workOptions" required :disabled="form.fixed" :mobile="mobile"/>
     <LotusField v-model="form.farm_zone" label="Áp dụng cho" type="select" :searchable="false" :options="zoneOptions" :empty-option="null" :disabled="form.fixed" :mobile="mobile"/>
     <LotusField v-model="form.repeat_days" label="Làm lại sau (ngày)" type="number" inputmode="numeric" required :mobile="mobile"/>
     <LotusField v-if="!form.fixed" v-model="form.rule_name" label="Tên vòng" placeholder="Để trống: tên việc và khu" :mobile="mobile"/>
     <LotusField v-model="form.valid_from" label="Áp dụng từ ngày" type="date" required :mobile="mobile"/>
     <LotusField v-model="form.valid_to" label="Đến ngày (bỏ trống nếu không hết hạn)" type="date" :mobile="mobile"/>
    </FormGrid>
    <LotusField v-model="form.notes" label="Ghi chú" type="textarea" :mobile="mobile"/>
   </template>
  </ModalForm>
 </section>
</template>

<style>
.care-cycles{display:grid;gap:12px;min-width:0}
.care-cycles__tools{display:flex;gap:12px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}
.care-cycles__tools p{margin:0;flex:1 1 320px}
.care-cycles__cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px}
.care-cycles--mobile .care-cycles__cards{grid-template-columns:1fr}
.care-cycles__card{display:grid;gap:3px;padding:10px 12px;text-align:left;font:inherit;color:inherit;border:1px solid var(--lotus-border);border-left:4px solid var(--lotus-success);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);cursor:pointer}
.care-cycles__card.is-off{border-left-color:var(--lotus-border-strong)}
.care-cycles__card strong{color:var(--lotus-text-strong)}
.care-cycles__card span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.care-cycles__card em{font-size:var(--lotus-text-sm);font-style:normal;color:var(--lotus-warning)}
.care-cycles__versions{list-style:none;margin:0 0 12px;padding:0;display:grid;gap:6px}
.care-cycles__versions li{display:flex;gap:8px;justify-content:space-between;align-items:center;flex-wrap:wrap;padding:8px 10px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md)}
.care-cycles__versions li.is-current{border-color:var(--lotus-success)}
.care-cycles__versions li div:first-child{display:grid;gap:2px}
.care-cycles__versions span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.care-cycles__actions{display:flex;gap:6px}
</style>
