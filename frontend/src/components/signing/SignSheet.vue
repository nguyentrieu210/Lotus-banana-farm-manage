<script setup>
// Tấm ký chung trên máy tính (spec 003, US1): xem bản in của chứng từ, các chữ ký đã có, rồi Ký / Trả lại /
// Chuyển người ký. Server kiểm tra người đến lượt và đi qua đúng logic của từng loại chứng từ.
import {computed,ref,watch} from 'vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import WorkspaceConfirm from '../WorkspaceConfirm.vue'
import LotusSignatureTimeline from '../LotusSignatureTimeline.vue'
import LotusField from '../form/LotusField.vue'
import {Button as UiButton} from '../ui/button'
import {useWorkspaceConfirm} from '../../use-workspace-confirm'
import * as signing from '../../use-signing'

const props=defineProps({modelValue:Boolean,row:{type:Object,default:null},company:{type:String,default:''},callFn:Function})
const emit=defineEmits(['update:modelValue','done'])
const status=ref(null),busy=ref(false),error=ref(''),mode=ref(''),reason=ref(''),target=ref(''),options=ref([])
const confirm=useWorkspaceConfirm()
const call=(...args)=>props.callFn?props.callFn(...args):undefined
const title=computed(()=>props.row?[props.row.chain_label||props.row.doctype,props.row.name].join(' · '):'Ký chứng từ')
const current=computed(()=>status.value&&!status.value.returned?(status.value.current??-1):-1)
const step=computed(()=>status.value?.steps?.[current.value]||null)
const facts=computed(()=>{
 const r=props.row||{}
 return [r.creator_name?'Người lập: '+r.creator_name:'',r.amount!=null&&r.amount!==''?'Số tiền: '+signing.money(r.amount,r.currency):'',
  r.posting_date?'Ngày: '+signing.shortDate(r.posting_date):'',step.value?'Bước: '+step.value.title:''].filter(Boolean)
})

async function load(){
 if(!props.row)return
 busy.value=true;error.value='';mode.value='';reason.value='';target.value=''
 try{status.value=await signing.chainStatus(props.row,props.callFn&&call)}
 catch(e){error.value=e.message||String(e)}
 finally{busy.value=false}
}
watch(()=>[props.modelValue,props.row?.name],([open])=>{if(open)load()},{immediate:true})

async function act(work,message){
 busy.value=true;error.value=''
 try{const result=await work();emit('done',{row:props.row,message,result});emit('update:modelValue',false)}
 catch(e){error.value=e.message||String(e)}
 finally{busy.value=false}
}
async function sign(){
 if(!await confirm.ask(signing.confirmText({...props.row,step_title:step.value?.title||props.row?.step_title}),'Ký chứng từ'))return
 await act(()=>signing.signDocument(props.row,props.callFn&&call),'Đã ký '+props.row.name+'.')
}
const sendBack=()=>act(()=>signing.returnDocument(props.row,reason.value,props.callFn&&call),'Đã trả lại '+props.row.name+'.')
async function openReassign(){
 mode.value='reassign';error.value=''
 try{
  const found=await signing.signerOptions(status.value.chain,props.company||undefined,props.callFn&&call)
  options.value=(found?.candidates?.[step.value?.key]||[]).filter(c=>c.user!==step.value?.assignee).map(c=>({value:c.user,label:c.name+(c.designation?' · '+c.designation:'')}))
 }catch(e){error.value=e.message||String(e)}
}
const reassign=()=>act(()=>signing.reassignStep(props.row,step.value.key,target.value,reason.value,props.callFn&&call),'Đã chuyển bước '+(step.value?.title||'')+'.')
</script>

<template>
 <WorkspaceModal :model-value="modelValue" :title="title" :busy="busy" width="1100px" @update:model-value="emit('update:modelValue',$event)">
  <div v-if="row" class="sign-sheet">
   <p v-if="facts.length" class="sign-sheet__facts">{{facts.join(' · ')}}</p>
   <p v-if="error" class="sign-sheet__error" role="alert">{{error}}</p>
   <div class="sign-sheet__body">
    <iframe v-if="row.print_url" class="sign-sheet__preview" :src="row.print_url" :title="'Bản in '+row.name"></iframe>
    <aside class="sign-sheet__side">
     <LotusSignatureTimeline v-if="status?.round" :steps="status.steps" :current="current" title="Các bước ký"/>
     <template v-if="status?.can_sign">
      <UiButton type="button" class="sign-sheet__primary" :disabled="busy" @click="sign">Ký: {{step?.title}}</UiButton>
      <div class="sign-sheet__row">
       <UiButton v-if="status.can_return" type="button" variant="outline" :disabled="busy" @click="mode=mode==='return'?'':'return';reason=''">Trả lại</UiButton>
       <UiButton v-if="status.can_reassign" type="button" variant="outline" :disabled="busy" @click="mode==='reassign'?mode='':openReassign()">Chuyển người ký</UiButton>
      </div>
     </template>
     <p v-else-if="status" class="sign-sheet__hint">Chứng từ này không còn chờ bạn ký.</p>
     <div v-if="mode==='return'" class="sign-sheet__form">
      <LotusField v-model="reason" label="Lý do trả lại" type="textarea" rows="3" maxlength="500" placeholder="Nêu rõ cần sửa gì…"/>
      <UiButton type="button" variant="destructive" :disabled="busy||reason.trim().length<3" @click="sendBack">Trả lại người lập</UiButton>
     </div>
     <div v-if="mode==='reassign'" class="sign-sheet__form">
      <LotusField v-model="target" label="Người ký thay" :options="options" placeholder="Chọn người đủ quyền ký bước này…"/>
      <LotusField v-model="reason" label="Lý do chuyển" maxlength="300" placeholder="Ví dụ: người ký đang nghỉ phép"/>
      <UiButton type="button" :disabled="busy||!target||reason.trim().length<3" @click="reassign">Chuyển người ký</UiButton>
     </div>
     <a v-if="row.desktop_url" class="sign-sheet__open" :href="row.desktop_url">Mở chứng từ</a>
    </aside>
   </div>
  </div>
 </WorkspaceModal>
 <WorkspaceConfirm :open="confirm.open.value" :title="confirm.title.value" :message="confirm.message.value" confirm-label="Ký" cancel-label="Quay lại" @answer="confirm.finish"/>
</template>

<style>
.sign-sheet{display:grid;gap:var(--lotus-space-3,12px)}
.sign-sheet__facts{margin:0;color:var(--lotus-muted)}
.sign-sheet__error{margin:0;color:var(--lotus-danger)}
.sign-sheet__body{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:var(--lotus-space-4,16px);min-height:60vh}
.sign-sheet__preview{width:100%;min-height:60vh;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px);background:white}
.sign-sheet__side{display:grid;align-content:start;gap:var(--lotus-space-3,12px)}
.sign-sheet__row{display:flex;gap:var(--lotus-space-2,8px);flex-wrap:wrap}
.sign-sheet__form{display:grid;gap:var(--lotus-space-2,8px)}
.sign-sheet__hint{margin:0;color:var(--lotus-muted)}
.sign-sheet__open{color:var(--lotus-primary-text,var(--lotus-primary))}
@media (max-width:900px){.sign-sheet__body{grid-template-columns:1fr}}
</style>
