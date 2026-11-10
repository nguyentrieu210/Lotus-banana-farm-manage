<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import ModalForm from '../form/ModalForm.vue'
import ReasonDialog from '../form/ReasonDialog.vue'
import {Button as UiButton} from '../ui/button'
import LotCards from './LotCards.vue'
import LotEntryModal from './LotEntryModal.vue'
import CrewStatus from './CrewStatus.vue'
import PaperPhotoReview from './PaperPhotoReview.vue'
import {useReasonDialog} from '../../use-reason-dialog'
import {formatDate} from '../../format'
import {stateLabels,stateTone,stageLabels,amountText} from '../../lot-entry-model.js'
// Hôm nay: the báo cáo ngày of one tổ (lotus_farm.lot_report). Lô cards, one dialog per lô, then Gửi; the đội trưởng sees
// every tổ of the đội, confirms a sent day, reopens one with a reason, or corrects a confirmed line with a reason.
const props=defineProps({farm:{type:String,required:true},crew:{type:String,required:true},setup:{type:Object,required:true},mobile:Boolean,initialTeam:String})
const day=defineModel('date',{type:String,required:true})
const api=(name,args={},write=false)=>call('lotus_farm.lot_report.'+name,args,write)
const supervisor=computed(()=>(props.setup.supervised_crews||[]).includes(props.crew))
const teams=computed(()=>(props.setup.teams||[]).filter(t=>t.lotus_parent_team===props.crew&&(supervisor.value||(props.setup.my_teams||[]).includes(t.name))))
const teamOptions=computed(()=>teams.value.map(t=>({value:t.name,label:t.team_name})))
const team=ref(props.initialTeam||'')
const data=ref(null),busy=ref(false),error=ref(''),notice=ref(''),opened=ref(null),asking=ref(''),acting=ref(false),statusKey=ref(0)
const amending=ref(null),amendForm=ref({}),amendBusy=ref(false),amendError=ref('')
const reason=useReasonDialog()
watch(teams,list=>{if(!list.some(t=>t.name===team.value))team.value=list[0]?.name||''},{immediate:true})

async function load(){
 if(!props.farm||!team.value||!day.value){data.value=null;return}
 busy.value=true;error.value=''
 try{data.value=await api('today',{farm:props.farm,team:team.value,date:day.value})}
 catch(e){error.value=e.message;data.value=null}
 finally{busy.value=false}
}
watch(()=>[props.farm,team.value,day.value],load,{immediate:true})
const report=computed(()=>data.value?.report||null)
const lines=computed(()=>(data.value?.lots||[]).flatMap(l=>l.lines))
const editable=computed(()=>!!data.value?.rights?.write&&(!report.value||['Draft','Reopened'].includes(report.value.state)))
// The report is created only when someone starts entering or sends: looking at a day writes nothing.
async function ensureReport(){
 if(report.value)return report.value
 data.value.report=await api('open_report',{farm:props.farm,team:team.value,date:day.value},true)
 return data.value.report
}
const counts=computed(()=>({lots:new Set(lines.value.map(l=>l.farm_block)).size,lines:lines.value.length}))
const canSend=computed(()=>editable.value)
const canConfirm=computed(()=>!!data.value?.rights?.confirm&&report.value?.state==='Sent')
const canReopen=computed(()=>!!data.value?.rights?.confirm&&['Sent','Confirmed'].includes(report.value?.state))

async function openLot(lot){
 error.value=''
 if(editable.value&&!report.value){try{await ensureReport()}catch(e){error.value=e.message;return}}
 opened.value=lot
}
async function saved(){notice.value='Đã lưu lô '+opened.value.code+'.';opened.value=null;await load();statusKey.value++}
async function act(kind){
 acting.value=true;error.value='';notice.value=''
 try{
  if(kind==='send'){const r=await ensureReport();await api('send',{report:r.name,expected_modified:r.modified},true);notice.value='Đã gửi báo cáo. Chờ đội trưởng xác nhận.'}
  else if(kind==='confirm'){await api('confirm',{report:report.value.name,expected_modified:report.value.modified},true);notice.value='Đã xác nhận báo cáo của tổ.'}
  asking.value='';await load();statusKey.value++
 }catch(e){error.value=e.message}
 finally{acting.value=false}
}
async function reopen(){
 const text=await reason.ask('Mở lại báo cáo '+formatDate(day.value)+' của '+(data.value?.team_name||'tổ'),'Lý do mở lại')
 if(!text)return
 acting.value=true;error.value=''
 try{await api('reopen',{report:report.value.name,reason:text},true);notice.value='Đã mở lại. Tổ sửa xong thì gửi lại.';await load();statusKey.value++}
 catch(e){error.value=e.message}
 finally{acting.value=false}
}
function amend(line){
 amendError.value=''
 amending.value=line
 amendForm.value={qty:line.qty,weight_kg:line.weight_kg||null,area_ha:line.area_ha||null,reason:''}
}
async function submitAmend(){
 const f=amendForm.value,line=amending.value
 if(!String(f.reason||'').trim()){amendError.value='Ghi lý do sửa.';return}
 amendBusy.value=true;amendError.value=''
 try{
  const values=line.stage==='Sucker Select'?{area_ha:f.area_ha}:line.stage==='Harvest'?{qty:f.qty,weight_kg:f.weight_kg}:{qty:f.qty}
  await api('amend',{entry:line.name,values,reason:f.reason},true)
  amending.value=null;opened.value=null;notice.value='Đã sửa. Dòng cũ được giữ trong lịch sử.';await load()
 }catch(e){amendError.value=e.message}
 finally{amendBusy.value=false}
}
function pickTeam(name){team.value=name}
async function paperChanged(text){if(text)notice.value=text;await load()}
</script>

<template>
 <section class="lot-today" :class="{'lot-today--mobile':mobile}" :aria-busy="busy">
  <FormGrid :columns="mobile?1:3">
   <LotusField v-model="day" label="Ngày" type="date" :mobile="mobile"/>
   <LotusField v-if="teamOptions.length>1" v-model="team" label="Tổ" type="select" :searchable="false" :options="teamOptions" :mobile="mobile"/>
  </FormGrid>
  <CrewStatus v-if="supervisor&&!mobile" :key="statusKey+day" :farm="farm" :crew="crew" :date="day" :current="team" compact @pick="pickTeam"/>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="field-report__notice" role="status">{{notice}}</p>
  <p v-if="!teamOptions.length" class="lotus-form-note">Tài khoản chưa là tổ trưởng của tổ nào trong đội này.</p>

  <template v-if="data">
   <div class="lot-today__bar" :class="'is-'+(stateTone[report?.state]||'neutral')">
    <div>
     <strong>{{data.team_name}} · {{formatDate(day)}}</strong>
     <span v-if="report">{{stateLabels[report.state]}} · {{counts.lines}} việc ở {{counts.lots}} lô<template v-if="report.on_behalf"> · nhập hộ</template><template v-if="report.entered_name"> · {{report.entered_name}}</template></span>
     <span v-else>Chưa có báo cáo ngày này.</span>
     <span v-if="report?.reopen_reason&&report.state==='Reopened'">Lý do mở lại: {{report.reopen_reason}}</span>
    </div>
    <div class="lot-today__actions">
     <UiButton v-if="canSend" type="button" :disabled="acting" @click="asking='send'">Gửi báo cáo</UiButton>
     <UiButton v-if="canConfirm" type="button" :disabled="acting" @click="asking='confirm'">Xác nhận</UiButton>
     <UiButton v-if="canReopen" type="button" variant="outline" :disabled="acting" @click="reopen">Mở lại</UiButton>
    </div>
   </div>
   <div v-if="asking" class="lotus-delete-confirm lot-today__ask" role="alert">
    <p v-if="asking==='send'">Gửi báo cáo {{formatDate(day)}} của {{data.team_name}}: {{counts.lines}} việc ở {{counts.lots}} lô? Đã gửi thì chỉ đội trưởng mở lại mới sửa được.<template v-if="!counts.lines"> Báo cáo đang trống: tổ không làm việc nào ngày này.</template></p>
    <p v-else>Xác nhận báo cáo {{formatDate(day)}} của {{data.team_name}}? Số đã xác nhận đi vào sổ lô, dự thu và tiền khoán; muốn sửa phải ghi lý do.</p>
    <div class="lotus-delete-confirm__actions"><UiButton type="button" variant="outline" @click="asking=''">Chưa</UiButton><UiButton type="button" :disabled="acting" @click="act(asking)">{{asking==='send'?'Gửi':'Xác nhận'}}</UiButton></div>
   </div>
   <PaperPhotoReview v-if="team&&(data.rights?.write||data.paper)" :data="data" :farm="farm" :team="team" :date="day" :editable="editable" :mobile="mobile" @changed="paperChanged" @open-lot="openLot"/>
   <LotCards :lots="data.lots" :works="data.works" :editable="editable" :mobile="mobile" @open="openLot"/>
  </template>

  <LotEntryModal v-if="opened&&data" :report="report||{name:'',state:'Sent'}" :lot="opened" :data="data" :mobile="mobile" @close="opened=null" @saved="saved" @amend="amend"/>
  <ModalForm :model-value="!!amending" :title="amending?'Sửa có lý do · '+(stageLabels[amending.stage]||'dòng đã xác nhận'):''" width="520px" :busy="amendBusy" :error="amendError"
   submit-label="Sửa" @update:model-value="v=>!v&&(amending=null)" @submit="submitAmend">
   <FormGrid v-if="amending" :columns="1">
    <LotusField v-if="amending.stage==='Sucker Select'" v-model="amendForm.area_ha" label="Diện tích đã chọn chồi (ha)" type="number" :mobile="mobile"/>
    <LotusField v-else v-model="amendForm.qty" label="Số đúng" type="number" :mobile="mobile" hint="Nhập 0 nếu dòng này nhập nhầm."/>
    <LotusField v-if="amending.stage==='Harvest'" v-model="amendForm.weight_kg" label="Khối lượng thu (kg)" type="number" :mobile="mobile"/>
    <LotusField v-model="amendForm.reason" label="Lý do sửa" type="textarea" required maxlength="140" :mobile="mobile"/>
    <p class="lotus-form-note">Số cũ {{amountText(amending.qty)}}<template v-if="amending.weight_kg"> · {{amountText(amending.weight_kg)}} kg</template> được giữ trong lịch sử.</p>
   </FormGrid>
  </ModalForm>
  <ReasonDialog :dialog="reason" submit-label="Mở lại"/>
 </section>
</template>

<style>
.lot-today{display:grid;gap:12px;min-width:0}
.lot-today__bar{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;border:1px solid var(--lotus-border);border-left-width:4px;border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.lot-today__bar>div:first-child{display:grid;gap:2px}
.lot-today__bar strong{font-weight:600;color:var(--lotus-text-strong)}
.lot-today__bar span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.lot-today__bar.is-success{border-left-color:var(--lotus-success)}
.lot-today__bar.is-info{border-left-color:var(--lotus-primary)}
.lot-today__bar.is-warning,.lot-today__bar.is-neutral{border-left-color:var(--lotus-warning)}
.lot-today__actions{display:flex;gap:8px;flex-wrap:wrap}
.lot-today--mobile .lot-today__actions{width:100%}
.lot-today--mobile .lot-today__actions>*{flex:1 1 auto}
</style>
