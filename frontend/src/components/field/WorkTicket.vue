<script setup>
import {computed,ref,watch} from 'vue'
import {call,upload} from '../../api'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import FormSection from '../form/FormSection.vue'
import ReasonDialog from '../form/ReasonDialog.vue'
import WorkspaceSummaryStrip from '../WorkspaceSummaryStrip.vue'
import {Button as UiButton} from '../ui/button'
import {useReasonDialog} from '../../use-reason-dialog'
import {formatDate} from '../../format'
import {unitLabel} from '../../units'
import {payModes,states,capBases,money,amountText,unitText,previewAmount} from '../../field-work-model.js'
// One phiếu giao việc: its facts (fixed when it was given), every day's report, the inspection, the khoán shares once
// it is locked, and the actions the server allows this user (báo xong, duyệt, trả lại, đổi tổ, huỷ, nghiệm thu).
const props=defineProps({name:{type:String,required:true},setup:{type:Object,required:true},mobile:Boolean})
const emit=defineEmits(['changed','report'])
const api=(n,args={},write=false)=>call('lotus_farm.field_report.'+n,args,write)
const reason=useReasonDialog()
const t=ref(null),busy=ref(false),error=ref(''),notice=ref('')
const inspecting=ref(null),team=ref('')
async function load(){busy.value=true;error.value='';try{t.value=await api('ticket',{name:props.name});team.value=t.value.work_team}catch(e){error.value=e.message}finally{busy.value=false}}
watch(()=>props.name,load,{immediate:true})

const unit=computed(()=>t.value?unitText(unitLabel(t.value.uom)||t.value.uom,t.value.basis):'')
const teamOptions=computed(()=>props.setup.teams.filter(x=>x.lotus_parent_team===t.value?.crew&&x.active).map(x=>({value:x.name,label:x.team_name})))
const summary=computed(()=>t.value?[
 {label:'Trạng thái',value:states[t.value.display]||t.value.display},
 {label:'Cách trả',value:payModes[t.value.pay_mode]||'—'},
 {label:'Đã báo',value:amountText(t.value.progress?.qty)+' '+unit.value},
 {label:'Số ngày / buổi',value:(t.value.progress?.days||0)+' / '+(t.value.progress?.sessions||0)},
 {label:t.value.state==='Locked'?'Tiền khoán':'Tạm tính',value:t.value.pay_mode==='Daywork'?'Công nhật':money(t.value.state==='Locked'?t.value.amount:previewAmount(t.value,t.value.progress?.qty))},
]:[])
async function act(method,args={},message){
 busy.value=true;error.value='';notice.value=''
 try{t.value=await api(method,{name:props.name,expected_modified:t.value.modified,...args},true);notice.value=message;emit('changed')}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
const reportDone=()=>act('report_done',{},'Đã báo xong. Chờ đội trưởng duyệt.')
const approve=()=>act('approve',{},t.value.pay_mode==='Lot'?'Đã duyệt. Chờ kỹ thuật vườn nghiệm thu.':'Đã duyệt và khoá phiếu.')
async function giveBack(){const text=await reason.ask('Trả lại phiếu cho tổ làm tiếp','Cần làm / sửa gì');if(text)await act('return_ticket',{reason:text},'Đã trả lại phiếu.')}
async function cancel(){const text=await reason.ask('Huỷ phiếu '+t.value.block_code+' · '+t.value.work_name,'Lý do huỷ');if(text)await act('cancel_assignment',{reason:text},'Đã huỷ phiếu.')}
async function moveTeam(){
 if(team.value===t.value.work_team)return
 const text=await reason.ask('Đổi tổ cho phiếu '+t.value.block_code,'Lý do đổi tổ')
 if(text)await act('reassign',{team:team.value,reason:text},'Đã đổi tổ.')
 else team.value=t.value.work_team
}
async function openInspection(){
 busy.value=true;error.value=''
 try{const plan=await api('inspection_plan',{name:props.name});inspecting.value={...plan,passed_count:null,notes:'',photo:null}}
 catch(e){error.value=e.message}finally{busy.value=false}
}
async function submitInspection(){
 const f=inspecting.value
 let photo=null
 if(f.photo instanceof File){busy.value=true;try{photo=(await upload(f.photo)).file_url}catch(e){error.value=e.message;busy.value=false;return}busy.value=false}
 await act('inspect',{sample_size:f.sample_size,passed_count:f.passed_count,notes:f.notes,photo},'Đã ghi nghiệm thu.')
 if(!error.value)inspecting.value=null
}
const shares=computed(()=>t.value?.shares||[])
defineExpose({reload:load})
</script>

<template>
 <section class="work-ticket" :aria-busy="busy">
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="field-report__notice" role="status">{{notice}}</p>
  <template v-if="t">
   <header class="work-ticket__head">
    <strong>{{t.block_code}} · {{t.work_name}}</strong>
    <span>{{t.team_name}} · giao {{formatDate(t.assigned_on)}}<template v-if="t.due_date"> · hạn {{formatDate(t.due_date)}}</template>
     <template v-if="t.rate"> · {{money(t.rate)}}/{{unit}}</template> · trần: {{capBases[t.cap_basis]||'—'}}</span>
    <span v-if="t.quarantine_until" class="work-ticket__warn">Lô đang cách ly thu hoạch đến {{formatDate(t.quarantine_until)}}</span>
    <span v-if="t.return_reason&&t.state==='Open'" class="work-ticket__warn">Bị trả lại: {{t.return_reason}}</span>
   </header>
   <WorkspaceSummaryStrip :items="summary"/>

   <div class="work-ticket__actions">
    <UiButton v-if="t.actions.report" type="button" @click="emit('report',t)">Báo cáo hôm nay</UiButton>
    <UiButton v-if="t.actions.report&&t.entries.length" type="button" variant="outline" :disabled="busy" @click="reportDone">Báo xong lô</UiButton>
    <UiButton v-if="t.actions.approve" type="button" :disabled="busy" @click="approve">Duyệt</UiButton>
    <UiButton v-if="t.actions.return" type="button" variant="outline" :disabled="busy" @click="giveBack">Trả lại</UiButton>
    <UiButton v-if="t.actions.inspect&&!inspecting" type="button" :disabled="busy" @click="openInspection">Nghiệm thu</UiButton>
    <UiButton v-if="t.actions.cancel" type="button" variant="ghost" :disabled="busy" @click="cancel">Huỷ phiếu</UiButton>
   </div>
   <FormGrid v-if="t.actions.cancel&&['Open','Failed'].includes(t.state)" :columns="mobile?1:3">
    <LotusField v-model="team" label="Tổ nhận" type="select" :searchable="false" :options="teamOptions" :mobile="mobile" @update:model-value="moveTeam"/>
   </FormGrid>

   <FormSection v-if="inspecting" title="Nghiệm thu" :description="'Cách chọn mẫu do hệ thống đưa ra: '+inspecting.plan+' Mức đạt '+inspecting.pass_mark+'%.'">
    <FormGrid :columns="mobile?1:3">
     <LotusField v-model="inspecting.sample_size" label="Số cây mẫu" type="number" required :mobile="mobile"/>
     <LotusField v-model="inspecting.passed_count" label="Số cây đạt" type="number" required :mobile="mobile"
      :hint="inspecting.passed_count!=null&&inspecting.sample_size?'Điểm '+Math.round(inspecting.passed_count*1000/inspecting.sample_size)/10+'%':''"/>
     <LotusField v-model="inspecting.photo" label="Ảnh (khi không đạt)" type="file" accept="image/*" :mobile="mobile"/>
     <LotusField v-model="inspecting.notes" label="Ghi chú" type="textarea" maxlength="1000" :mobile="mobile"/>
    </FormGrid>
    <div class="work-ticket__actions"><UiButton type="button" :disabled="busy||inspecting.passed_count==null" @click="submitInspection">Lưu nghiệm thu</UiButton><UiButton type="button" variant="ghost" @click="inspecting=null">Thôi</UiButton></div>
   </FormSection>

   <FormSection title="Báo cáo theo ngày">
    <p v-if="!t.entries.length" class="lotus-form-note">Chưa có báo cáo ngày nào.</p>
    <ul class="work-ticket__entries">
     <li v-for="e in t.entries" :key="e.name">
      <strong>{{formatDate(e.posting_date)}}</strong>
      <span>{{amountText(e.qty)}} {{unit}}<template v-if="e.ribbon"> · màu {{e.ribbon}}</template> · {{e.people.length}} người, {{e.people.reduce((n,p)=>n+(p.morning?1:0)+(p.afternoon?1:0),0)}} buổi{{e.done?' · báo xong':''}}</span>
      <small v-if="e.materials.length">Vật tư: {{e.materials.map(m=>m.item_code+' '+amountText(m.qty)+(m.dose?' ('+m.dose+')':'')).join(', ')}}</small>
      <small v-if="e.over_cut" class="work-ticket__warn">Vượt số đã cắt bắp cùng màu</small>
      <small v-if="e.under_norm" class="work-ticket__warn">Chưa đạt năng suất tối thiểu</small>
      <small v-if="e.notes">{{e.notes}}</small>
     </li>
    </ul>
   </FormSection>

   <FormSection v-if="t.inspection_doc" title="Kết quả nghiệm thu">
    <p class="lotus-form-note">{{formatDate(t.inspection_doc.inspected_on)}} · {{t.inspection_doc.passed_count}}/{{t.inspection_doc.sample_size}} cây đạt · {{t.inspection_doc.score}}% (mức {{t.inspection_doc.pass_mark}}%) · <b>{{t.inspection_doc.result==='Pass'?'Đạt':'Không đạt'}}</b><template v-if="t.inspection_doc.notes"> · {{t.inspection_doc.notes}}</template></p>
    <a v-if="t.inspection_doc.photo" :href="t.inspection_doc.photo" target="_blank" rel="noopener">Xem ảnh</a>
   </FormSection>

   <FormSection v-if="shares.length" title="Chia tiền khoán theo buổi">
    <ul class="work-ticket__entries"><li v-for="s in shares" :key="s.employee"><strong>{{s.employee_name}}</strong><span>{{money(s.amount)}}</span></li></ul>
   </FormSection>
  </template>
  <p v-else-if="busy" class="lotus-form-note" role="status">Đang tải phiếu…</p>
  <ReasonDialog :dialog="reason"/>
 </section>
</template>

<style>
.work-ticket{display:grid;gap:12px;min-width:0}
.work-ticket__head{display:grid;gap:2px;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.work-ticket__head strong{font-size:var(--lotus-text-md);color:var(--lotus-text-strong)}
.work-ticket__warn{color:var(--lotus-danger)}
.work-ticket__actions{display:flex;gap:8px;flex-wrap:wrap}
.work-ticket__entries{list-style:none;margin:0;padding:0;display:grid;gap:6px}
.work-ticket__entries li{display:grid;gap:2px;padding:6px 0;border-bottom:1px solid var(--lotus-border);font-size:var(--lotus-text-sm)}
.work-ticket__entries small{color:var(--lotus-muted)}
</style>
