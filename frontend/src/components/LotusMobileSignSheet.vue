<script setup>
// Tấm ký trên điện thoại (spec 003, US1): bản in, các bước ký, rồi Ký / Trả lại / Chuyển người ký.
// Same server calls as the desktop sheet (use-signing.js); the server checks whose turn it is.
import {computed,ref,watch} from 'vue'
import {Popup} from 'vant'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileInput from './LotusMobileInput.vue'
import LotusMobileSelect from './LotusMobileSelect.vue'
import LotusMobileDialog from './LotusMobileDialog.vue'
import LotusSignatureTimeline from './LotusSignatureTimeline.vue'
import {useMobileConfirm} from '../use-mobile-confirm'
import * as signing from '../use-signing'

const props=defineProps({show:Boolean,row:{type:Object,default:null},online:{type:Boolean,default:true},callFn:Function})
const emit=defineEmits(['update:show','done'])
const status=ref(null),busy=ref(false),error=ref(''),mode=ref(''),reason=ref(''),target=ref(''),options=ref([])
const confirm=useMobileConfirm()
const current=computed(()=>status.value&&!status.value.returned?(status.value.current??-1):-1)
const step=computed(()=>status.value?.steps?.[current.value]||null)
const facts=computed(()=>{const r=props.row||{};return [r.creator_name,r.amount!=null&&r.amount!==''?signing.money(r.amount,r.currency):'',r.posting_date?signing.shortDate(r.posting_date):''].filter(Boolean).join(' · ')})

async function load(){
 if(!props.row)return
 busy.value=true;error.value='';mode.value='';reason.value='';target.value=''
 try{status.value=await signing.chainStatus(props.row,props.callFn)}
 catch(e){error.value=e.message||String(e)}
 finally{busy.value=false}
}
watch(()=>[props.show,props.row?.name],([open])=>{if(open)load()},{immediate:true})
async function act(work,message){
 busy.value=true;error.value=''
 try{const result=await work();emit('done',{row:props.row,message,result});emit('update:show',false)}
 catch(e){error.value=e.message||String(e)}
 finally{busy.value=false}
}
async function sign(){
 if(!await confirm.ask(signing.confirmText({...props.row,step_title:step.value?.title||props.row?.step_title})))return
 await act(()=>signing.signDocument(props.row,props.callFn),'Đã ký '+props.row.name+'.')
}
const sendBack=()=>act(()=>signing.returnDocument(props.row,reason.value,props.callFn),'Đã trả lại '+props.row.name+'.')
async function openReassign(){
 mode.value='reassign';error.value=''
 try{
  const found=await signing.signerOptions(status.value.chain,undefined,props.callFn)
  options.value=(found?.candidates?.[step.value?.key]||[]).filter(c=>c.user!==step.value?.assignee).map(c=>({value:c.user,label:c.name}))
 }catch(e){error.value=e.message||String(e)}
}
const reassign=()=>act(()=>signing.reassignStep(props.row,step.value.key,target.value,reason.value,props.callFn),'Đã chuyển bước '+(step.value?.title||'')+'.')
</script>

<template>
 <Popup :show="show" position="bottom" round closeable teleport="body" class="lotus-sign-sheet" :style="{height:'min(94dvh,900px)'}" @update:show="emit('update:show',$event)">
  <section v-if="row" class="lotus-sign-sheet__body" :aria-label="'Ký '+row.name">
   <h2>{{row.chain_label||row.doctype}} · {{row.name}}</h2>
   <p v-if="facts" class="lotus-sign-sheet__facts">{{facts}}</p>
   <p v-if="error" class="lotus-sign-sheet__error" role="alert">{{error}}</p>
   <iframe v-if="row.print_url" class="lotus-sign-sheet__preview" :src="row.print_url" :title="'Bản in '+row.name"></iframe>
   <a v-if="row.print_url" class="lotus-sign-sheet__link" :href="row.print_url" target="_blank" rel="noopener">Mở bản in toàn màn hình</a>
   <LotusSignatureTimeline v-if="status?.round" :steps="status.steps" :current="current" title="Các bước ký"/>
   <template v-if="status?.can_sign">
    <LotusMobileButton variant="primary" :disabled="busy||!online" @click="sign">Ký: {{step?.title}}</LotusMobileButton>
    <div class="lotus-sign-sheet__row">
     <LotusMobileButton v-if="status.can_return" :disabled="busy" @click="mode=mode==='return'?'':'return';reason=''">Trả lại</LotusMobileButton>
     <LotusMobileButton v-if="status.can_reassign" :disabled="busy" @click="mode==='reassign'?mode='':openReassign()">Chuyển người ký</LotusMobileButton>
    </div>
   </template>
   <p v-else-if="status" class="lotus-sign-sheet__facts">Chứng từ này không còn chờ bạn ký.</p>
   <template v-if="mode==='return'">
    <LotusMobileInput v-model="reason" label="Lý do trả lại" type="textarea" :rows="3" maxlength="500" placeholder="Nêu rõ cần sửa gì…"/>
    <LotusMobileButton variant="danger" :disabled="busy||!online||reason.trim().length<3" @click="sendBack">Trả lại người lập</LotusMobileButton>
   </template>
   <template v-if="mode==='reassign'">
    <LotusMobileSelect v-model="target" label="Người ký thay" :options="options" placeholder="Chọn người đủ quyền…"/>
    <LotusMobileInput v-model="reason" label="Lý do chuyển" maxlength="300" placeholder="Ví dụ: người ký đang nghỉ phép"/>
    <LotusMobileButton variant="primary" :disabled="busy||!online||!target||reason.trim().length<3" @click="reassign">Chuyển người ký</LotusMobileButton>
   </template>
  </section>
 </Popup>
 <LotusMobileDialog :ref="el=>confirm.dialog.value=el" @cancel="confirm.finish(false)">
  <h3>Ký chứng từ</h3><p>{{confirm.message.value}}</p>
  <LotusMobileButton @click="confirm.finish(false)">Quay lại</LotusMobileButton>
  <LotusMobileButton variant="primary" @click="confirm.finish(true)">Ký</LotusMobileButton>
 </LotusMobileDialog>
</template>

<style>
.lotus-sign-sheet__body{display:grid;gap:var(--lotus-space-3,12px);padding:var(--lotus-space-4,16px) var(--lotus-space-4,16px) max(24px,env(safe-area-inset-bottom))}
.lotus-sign-sheet__body h2{margin:0 32px 0 0;font-size:18px}
.lotus-sign-sheet__facts{margin:0;color:var(--lotus-muted)}
.lotus-sign-sheet__error{margin:0;color:var(--lotus-danger)}
.lotus-sign-sheet__preview{width:100%;height:46dvh;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px);background:white}
.lotus-sign-sheet__link{color:var(--lotus-primary-text,var(--lotus-primary));font-size:14px}
.lotus-sign-sheet__row{display:grid;grid-template-columns:1fr 1fr;gap:var(--lotus-space-2,8px)}
</style>
