<script setup>
// Chi tiết đơn mua (spec 003, US3), dùng trong Mua hàng trên máy tính và ở chế độ điện thoại: trạng thái,
// cảnh báo dòng sẽ bị chặn khi duyệt, chữ ký, chứng từ liên quan, và mọi thao tác: sửa, gửi duyệt, duyệt, trả lại,
// xóa nháp, in, đã gửi NCC, NCC xác nhận, đổi hẹn, đóng phần chưa giao, hủy, nhận hàng. Máy chủ kiểm tra lại tất cả.
import {computed,ref,watch} from 'vue'
import LotusField from '../form/LotusField.vue'
import LotusSignatureTimeline from '../LotusSignatureTimeline.vue'
import ProcurementSigners from '../ProcurementSigners.vue'
import PurchaseProgress from '../PurchaseProgress.vue'
import LotusMobileButton from '../LotusMobileButton.vue'
import {Button} from '../ui/button'
import {lotusMethod,procurementApi} from './use-procurement'
import {money,confirmText} from '../../use-signing'

const props=defineProps({detail:{type:Object,required:true},chain:{type:Object,default:null},mobile:Boolean,company:String,saving:Boolean,
 ask:{type:Function,required:true},callFn:Function})
const emit=defineEmits(['changed','deleted','edit','receive','open','notice','error'])
const method=(module,name,args={},write=false)=>props.callFn?props.callFn('lotus_farm.'+module+'.'+name,args,write):lotusMethod(module,name,args,write)
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const link=computed(()=>props.mobile?'a':Button)
const d=computed(()=>props.detail)
const mode=ref(''),reason=ref(''),newDate=ref(''),signers=ref({}),approvers=ref(null),working=ref(false)
const busy=computed(()=>props.saving||working.value)
const draft=computed(()=>d.value.docstatus===0)
const editable=computed(()=>d.value.can_write&&['Nháp','Bị trả lại'].includes(d.value.status))
const steps=computed(()=>d.value.signing?.steps||[])
const current=computed(()=>steps.value.findIndex(s=>s.state!=='Đã ký'&&s.state!=='Trả lại'))
const facts=computed(()=>[d.value.status+(d.value.overdue?' · quá hẹn giao':''),d.value.supplier_name||d.value.supplier,d.value.amount!=null?money(d.value.amount,d.value.currency):'',
 d.value.expected_date?'Hẹn giao '+String(d.value.revised_delivery_date||d.value.expected_date).split('-').reverse().join('/'):''].filter(Boolean).join(' · '))

watch(()=>[d.value.name,d.value.modified],async()=>{
 mode.value='';reason.value='';newDate.value=d.value.revised_delivery_date||d.value.expected_date||''
 signers.value=d.value.signing?.approver?{APPROVE:d.value.signing.approver}:{}
 if(d.value.can_request_approval&&!approvers.value){try{approvers.value=await method('purchasing','approver_options',{company:props.company||d.value.company})}catch(e){emit('error',e.message)}}
},{immediate:true})

async function run(work,message){
 if(busy.value)return
 working.value=true;emit('error','')
 try{
  await work()
  const fresh=await method('purchasing','detail',{name:d.value.name})
  const related=props.callFn?await props.callFn('lotus_farm.procurement.chain',{name:d.value.name}):await procurementApi('chain',{name:d.value.name})
  mode.value='';reason.value=''
  emit('changed',fresh,related);if(message)emit('notice',message)
  window.dispatchEvent(new CustomEvent('lotus-signing-changed'))
 }catch(e){emit('error',e.message||String(e))}
 finally{working.value=false}
}
const base=()=>({name:d.value.name,modified:d.value.modified})
const act=(name,args,message)=>run(()=>method('purchasing',name,{...base(),...args},true),message)
const send=()=>act('request_approval',{approver:signers.value.APPROVE},'Đã gửi '+d.value.name+' cho người duyệt.')
async function approve(){
 if(!await props.ask(confirmText({chain_label:'Đơn mua hàng',name:d.value.name,amount:d.value.amount,currency:d.value.currency,step_title:'Người duyệt mua'})))return
 await act('approve_order',{},'Đã duyệt đơn '+d.value.name+'.')
}
const sendBack=()=>act('reject_order',{reason:reason.value.trim()},'Đã trả lại đơn '+d.value.name+' để sửa.')
const reschedule=()=>act('reschedule_order',{expected_date:newDate.value,reason:reason.value.trim()},'Đã cập nhật ngày giao mới.')
async function closeRest(){if(await props.ask('Đóng phần chưa giao của đơn '+d.value.name+'? Phần đã nhận giữ nguyên.'))await act('close_order',{reason:reason.value.trim()},'Đã đóng phần chưa giao.')}
async function cancel(){if(await props.ask('Hủy đơn '+d.value.name+'? Các dòng đề xuất liên quan trở về Chờ mua.'))await act('cancel_order',{reason:reason.value.trim()},'Đã hủy đơn '+d.value.name+'.')}
async function remove(){
 if(!await props.ask('Xóa đơn nháp '+d.value.name+'?'))return
 if(busy.value)return
 working.value=true;emit('error','')
 try{await method('warehouse_buying_lite','delete_draft',base(),true);emit('notice','Đã xóa đơn nháp '+d.value.name+'.');emit('deleted',d.value.name)}
 catch(e){emit('error',e.message||String(e))}
 finally{working.value=false}
}
function toggle(next){mode.value=mode.value===next?'':next;reason.value=''}
</script>

<template>
 <section class="order-detail" :aria-label="'Đơn mua '+d.name">
  <p class="lotus-form-note">{{facts}}</p>
  <p v-if="d.reject_reason&&draft" role="status">Bị trả lại: {{d.reject_reason}}</p>
  <p v-if="d.close_reason" role="status">Đã đóng phần chưa giao: {{d.close_reason}}</p>
  <p v-if="d.cancel_reason" role="status">Đã hủy: {{d.cancel_reason}}</p>
  <p v-if="d.revised_delivery_reason" class="lotus-form-note">Đổi hẹn giao: {{d.revised_delivery_reason}}</p>
  <ul v-if="d.warnings?.length" class="order-detail__warnings" role="alert" aria-label="Dòng sẽ bị chặn khi duyệt">
   <li v-for="w in d.warnings" :key="w.line+w.code">{{w.message}}</li>
  </ul>
  <LotusSignatureTimeline v-if="steps.length" :steps="steps" :current="d.status==='Bị trả lại'?-1:current" title="Chữ ký trên đơn mua"/>
  <ProcurementSigners v-if="d.can_request_approval" v-model="signers" :mobile="mobile" :options="approvers"/>
  <PurchaseProgress v-if="chain" :progress="{...chain,lines:chain.progress}" :mobile="mobile" navigate @open="(row,type)=>emit('open',row,type)"/>
  <p v-for="r in chain?.funding||[]" :key="r.name" class="lotus-form-note">{{r.name}} · {{r.status}} · Chi hộ {{money(r.amount)}} · Còn hoàn {{money(r.remaining)}}</p>

  <div v-if="mode==='return'" class="order-detail__form">
   <LotusField v-model="reason" :mobile="mobile" label="Lý do trả lại đơn" type="textarea" placeholder="Nêu lý do để người lập sửa lại…"/>
   <component :is="button" type="button" variant="destructive" :disabled="busy||reason.trim().length<3" @click="sendBack">Trả lại đơn</component>
  </div>
  <div v-if="mode==='reschedule'" class="order-detail__form">
   <LotusField v-model="newDate" :mobile="mobile" type="date" label="Ngày giao hẹn lại"/>
   <LotusField v-model="reason" :mobile="mobile" label="Lý do đổi hẹn"/>
   <component :is="button" type="button" :disabled="busy||!newDate||reason.trim().length<3" @click="reschedule">Đổi hẹn giao</component>
  </div>
  <div v-if="mode==='close'" class="order-detail__form">
   <LotusField v-model="reason" :mobile="mobile" label="Lý do đóng phần chưa giao" type="textarea"/>
   <component :is="button" type="button" :disabled="busy||reason.trim().length<3" @click="closeRest">Đóng phần chưa giao</component>
  </div>
  <div v-if="mode==='cancel'" class="order-detail__form">
   <LotusField v-model="reason" :mobile="mobile" label="Lý do hủy đơn" type="textarea"/>
   <component :is="button" type="button" variant="destructive" :disabled="busy||reason.trim().length<3" @click="cancel">Hủy đơn mua</component>
  </div>

  <div class="procurement-actions order-detail__actions">
   <component :is="button" v-if="editable" type="button" variant="outline" :disabled="busy" @click="emit('edit')">Sửa đơn</component>
   <component :is="button" v-if="d.can_request_approval" type="button" :disabled="busy||!signers.APPROVE||d.warnings?.some(w=>w.code!=='held')" @click="send">Gửi duyệt đơn</component>
   <component :is="button" v-if="d.can_approve" type="button" :disabled="busy" @click="approve">Duyệt đơn</component>
   <component :is="button" v-if="d.can_approve" type="button" variant="outline" :disabled="busy" @click="toggle('return')">Trả lại</component>
   <component :is="button" v-if="d.can_receive&&d.docstatus===1&&!['Đã đóng','Đã nhận đủ'].includes(d.status)" type="button" :disabled="busy" @click="emit('receive')">Nhận / nghiệm thu từng phần</component>
   <component :is="button" v-if="d.can_manage&&!d.sent_at" type="button" variant="outline" :disabled="busy" @click="act('mark_order_sent',{},'Đã ghi nhận gửi đơn cho nhà cung cấp.')">Đã gửi NCC</component>
   <component :is="button" v-if="d.can_manage&&d.sent_at&&!d.supplier_confirmed_at" type="button" variant="outline" :disabled="busy" @click="act('confirm_supplier_order',{},'Đã ghi nhận NCC xác nhận.')">NCC đã xác nhận</component>
   <component :is="button" v-if="d.can_manage" type="button" variant="outline" :disabled="busy" @click="toggle('reschedule')">Đổi hẹn giao</component>
   <component :is="button" v-if="d.can_close" type="button" variant="outline" :disabled="busy" @click="toggle('close')">Đóng phần chưa giao</component>
   <component :is="button" v-if="d.can_cancel" type="button" variant="outline" :disabled="busy" @click="toggle('cancel')">Hủy đơn</component>
   <component :is="button" v-if="d.can_delete" type="button" variant="outline" :disabled="busy" @click="remove">Xóa nháp</component>
   <component :is="link" as="a" variant="outline" :href="d.print_url" target="_blank" rel="noopener">In đơn mua</component>
   <component :is="link" v-if="d.signed_copy" as="a" variant="outline" :href="d.signed_copy.url" target="_blank" rel="noopener">Tải bản PDF đã ký</component>
  </div>
 </section>
</template>

<style>
.order-detail{display:grid;gap:var(--lotus-space-3,12px)}
.order-detail__form{display:grid;gap:var(--lotus-space-2,8px);padding:var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px)}
.order-detail__warnings{margin:0;padding:var(--lotus-space-2,8px) var(--lotus-space-3,12px) var(--lotus-space-2,8px) var(--lotus-space-6,28px);border:1px solid var(--lotus-warning-200,var(--lotus-border));border-radius:var(--lotus-radius-md,8px);background:var(--lotus-warning-soft);color:var(--lotus-warning-800,var(--lotus-text))}
</style>
