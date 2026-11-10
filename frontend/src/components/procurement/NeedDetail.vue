<script setup>
// Chi tiết đề xuất mua (spec 003, US2), dùng trong Mua hàng trên máy tính và ở chế độ điện thoại:
// giai đoạn, lý do, chữ ký, tiến độ từng dòng, và mọi thao tác: ký gửi, trả lại, chuyển người ký, sửa, xóa nháp,
// in / tải bản đã ký, đóng phần chưa mua, hủy, lập đơn. Máy chủ kiểm tra lại quyền, trạng thái và phiên bản.
import {computed,ref,watch} from 'vue'
import LotusField from '../form/LotusField.vue'
import LotusSignatureTimeline from '../LotusSignatureTimeline.vue'
import ProcurementSigners from '../ProcurementSigners.vue'
import PurchaseProgress from '../PurchaseProgress.vue'
import LotusMobileButton from '../LotusMobileButton.vue'
import {Button} from '../ui/button'
import {lotusMethod} from './use-procurement'
import {money,confirmText} from '../../use-signing'

const props=defineProps({detail:{type:Object,required:true},mobile:Boolean,company:String,canOrder:Boolean,saving:Boolean,
 ask:{type:Function,required:true},callFn:Function})
const emit=defineEmits(['changed','deleted','edit','order','open','notice','error','busy'])
const api=(name,args={},write=false)=>props.callFn?props.callFn('lotus_farm.purchase_proposal.'+name,args,write):lotusMethod('purchase_proposal',name,args,write)
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const link=computed(()=>props.mobile?'a':Button)
const d=computed(()=>props.detail)
const mode=ref(''),reason=ref(''),target=ref(''),withQuotes=ref(false),signReason=ref(''),signers=ref({}),signerOptions=ref(null),working=ref(false)
const busy=computed(()=>props.saving||working.value)
const waitingStep=computed(()=>(d.value.signatures||[])[d.value.step]||null)
const reassignOptions=computed(()=>((signerOptions.value?.candidates||{})[waitingStep.value?.action]||[]).filter(c=>c.user!==waitingStep.value?.assignee).map(c=>({value:c.user,label:c.name+(c.designation?' · '+c.designation:'')})))
const signLabel=computed(()=>d.value.step===0?'Ký và gửi phụ trách bộ phận':d.value.step===3?'Ký phê duyệt (Giám đốc)':'Ký xác nhận: '+(d.value.step_title||''))
const signersMissing=computed(()=>d.value.needs_signers&&(signerOptions.value?.steps||[]).slice(1).some(s=>!signers.value[s.key]))
const facts=computed(()=>[d.value.stage,d.value.department,d.value.reason].filter(Boolean).join(' · '))

async function loadSigners(){
 if(!(d.value.needs_signers||d.value.can_reassign))return
 try{signerOptions.value=await api('signer_options',{company:props.company||d.value.company,name:d.value.name})}catch(e){emit('error',e.message)}
}
watch(()=>[d.value.name,d.value.modified],()=>{mode.value='';reason.value='';target.value='';withQuotes.value=false;signReason.value='';signers.value={...(d.value.signers||{})};loadSigners()},{immediate:true})

async function run(work,message){
 if(busy.value)return
 working.value=true;emit('busy',true);emit('error','')
 try{const result=await work();mode.value='';reason.value='';if(message)emit('notice',message);return result}
 catch(e){emit('error',e.message||String(e))}
 finally{working.value=false;emit('busy',false)}
}
const base=()=>({name:d.value.name,modified:d.value.modified})
async function sign(){
 const total=d.value.total||null
 if(!await props.ask(confirmText({chain_label:'Phiếu đề xuất mua vật tư',name:d.value.name,amount:total,step_title:d.value.step_title})))return
 const result=await run(()=>api('sign',{...base(),signers:d.value.needs_signers?signers.value:undefined,reason:d.value.needs_reason?signReason.value.trim():undefined},true),'Đã ký '+d.value.name+'.')
 if(result){emit('changed',result);window.dispatchEvent(new CustomEvent('lotus-signing-changed'))}
}
async function apply(method,args,message){const result=await run(()=>api(method,{...base(),...args},true),message);if(result){emit('changed',result);window.dispatchEvent(new CustomEvent('lotus-signing-changed'))}}
const sendBack=()=>apply('return_proposal',{reason:reason.value.trim()},'Đã trả lại '+d.value.name+' cho người đề xuất.')
const reassign=()=>apply('reassign_signer',{step:waitingStep.value.action,user:target.value,reason:reason.value.trim()},'Đã chuyển người ký.')
const closeRest=()=>apply('close_remainder',{reason:reason.value.trim()},'Đã đóng phần chưa mua của '+d.value.name+'.')
const cancel=()=>apply('cancel_proposal',{reason:reason.value.trim(),cancel_quotes:withQuotes.value?1:0},'Đã hủy đề xuất '+d.value.name+'.')
async function remove(){
 if(!await props.ask('Xóa đề xuất nháp '+d.value.name+'?'))return
 const result=await run(()=>api('delete_proposal',base(),true),'Đã xóa nháp '+d.value.name+'.')
 if(result)emit('deleted',d.value.name)
}
function toggle(next){mode.value=mode.value===next?'':next;reason.value='';target.value=''}
</script>

<template>
 <section class="need-detail" :aria-label="'Đề xuất mua '+d.name">
  <p class="lotus-form-note">{{facts}}<template v-if="d.total"> · {{money(d.total)}}</template></p>
  <p v-if="d.policy_notice||d.return_reason" role="status">{{d.policy_notice||('Bị trả lại'+(d.returned_by?' bởi '+d.returned_by:'')+': '+d.return_reason)}}</p>
  <p v-if="d.closed" role="status">Đã đóng phần chưa mua{{d.closed_by?' bởi '+d.closed_by:''}}: {{d.close_reason}}</p>
  <p v-if="d.docstatus===2&&d.cancel_reason" role="status">Đã hủy: {{d.cancel_reason}}</p>
  <LotusSignatureTimeline :steps="d.signatures" :current="d.step??-1" title="Các bước ký"/>
  <ProcurementSigners v-if="d.needs_signers&&d.can_sign" v-model="signers" :mobile="mobile" :options="signerOptions"/>
  <LotusField v-if="d.needs_reason&&d.can_sign" v-model="signReason" :mobile="mobile" label="Lý do đề xuất mua" type="textarea" required placeholder="Phiếu nhập từ Excel chưa có lý do. Ghi lý do trước khi ký gửi."/>
  <PurchaseProgress v-if="d.progress" :progress="d.progress" :mobile="mobile" navigate @open="(row,type)=>emit('open',row,type)"/>

  <div v-if="mode==='return'" class="need-detail__form">
   <LotusField v-model="reason" :mobile="mobile" label="Lý do trả lại đề xuất" type="textarea" placeholder="Nêu rõ cần sửa gì…"/>
   <component :is="button" type="button" variant="destructive" :disabled="busy||reason.trim().length<3" @click="sendBack">Trả lại người đề xuất</component>
  </div>
  <div v-if="mode==='reassign'" class="need-detail__form">
   <LotusField v-model="target" :mobile="mobile" :label="'Chuyển bước “'+(d.step_title||'')+'” cho'" :options="reassignOptions" placeholder="Chọn người đủ quyền ký bước này…"/>
   <LotusField v-model="reason" :mobile="mobile" label="Lý do chuyển" placeholder="Ví dụ: người ký đang nghỉ phép"/>
   <component :is="button" type="button" :disabled="busy||!target||reason.trim().length<3" @click="reassign">Chuyển người ký</component>
  </div>
  <div v-if="mode==='close'" class="need-detail__form">
   <LotusField v-model="reason" :mobile="mobile" label="Lý do đóng phần chưa mua" type="textarea" placeholder="Ví dụ: đủ hàng trong kho, không mua nữa"/>
   <component :is="button" type="button" :disabled="busy||reason.trim().length<3" @click="closeRest">Đóng phần chưa mua</component>
  </div>
  <div v-if="mode==='cancel'" class="need-detail__form">
   <LotusField v-model="reason" :mobile="mobile" label="Lý do hủy đề xuất" type="textarea"/>
   <LotusField v-model="withQuotes" :mobile="mobile" type="checkbox" label="Hủy kèm các báo giá chỉ dùng cho đề xuất này"/>
   <component :is="button" type="button" variant="destructive" :disabled="busy||reason.trim().length<3" @click="cancel">Hủy đề xuất</component>
  </div>

  <div class="procurement-actions need-detail__actions">
   <component :is="button" v-if="d.can_sign" type="button" :disabled="busy||signersMissing||(d.needs_reason&&signReason.trim().length<3)" @click="sign">{{signLabel}}</component>
   <component :is="button" v-if="d.edit" type="button" variant="outline" :disabled="busy" @click="emit('edit')">{{d.edit==='prices'?'Bổ sung giá / nhà cung cấp':'Sửa đề xuất'}}</component>
   <component :is="button" v-if="d.can_return" type="button" variant="outline" :disabled="busy" @click="toggle('return')">Trả lại</component>
   <component :is="button" v-if="d.can_reassign" type="button" variant="outline" :disabled="busy" @click="toggle('reassign')">Chuyển người ký</component>
   <component :is="button" v-if="d.docstatus===1&&!d.closed&&canOrder" type="button" :disabled="busy" @click="emit('order')">Lập đơn từ đề xuất</component>
   <component :is="button" v-if="d.can_close" type="button" variant="outline" :disabled="busy" @click="toggle('close')">Đóng phần chưa mua</component>
   <component :is="button" v-if="d.can_cancel" type="button" variant="outline" :disabled="busy" @click="toggle('cancel')">Hủy đề xuất</component>
   <component :is="button" v-if="d.can_delete" type="button" variant="outline" :disabled="busy" @click="remove">Xóa nháp</component>
   <component :is="link" as="a" variant="outline" :href="d.print_url" target="_blank" rel="noopener">In đề xuất</component>
   <component :is="link" v-if="d.signed_copy" as="a" variant="outline" :href="d.signed_copy.url" target="_blank" rel="noopener">Tải bản PDF đã ký</component>
  </div>
 </section>
</template>

<style>
.need-detail{display:grid;gap:var(--lotus-space-3,12px)}
.need-detail__form{display:grid;gap:var(--lotus-space-2,8px);padding:var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px)}
</style>
