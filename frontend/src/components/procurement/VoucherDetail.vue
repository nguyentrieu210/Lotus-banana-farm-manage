<script setup>
// Chi tiết phiếu chi (spec 003, US6): nội dung chi, chuỗi ký, và các thao tác — ký (có hộp xác nhận), trả lại có lý do,
// hủy phiếu chưa ghi sổ, đảo phiếu đã ghi sổ (chỉ kế toán trưởng), in, tải bản PDF đã ký, đính kèm chứng từ.
import {computed,ref,watch} from 'vue'
import LotusField from '../form/LotusField.vue'
import LotusMobileButton from '../LotusMobileButton.vue'
import LotusSignatureTimeline from '../LotusSignatureTimeline.vue'
import StockEvidence from '../stock/StockEvidence.vue'
import {Button} from '../ui/button'
import {lotusMethod} from './use-procurement'
import {money,shortDate,confirmText} from '../../use-signing'

const props=defineProps({doctype:{type:String,default:'Payment Entry'},name:{type:String,required:true},mobile:Boolean,ask:{type:Function,required:true},callFn:Function})
const emit=defineEmits(['changed','deleted','open','notice','error','loaded'])
const call=(module,name,args={},write=false)=>props.callFn?props.callFn('lotus_farm.'+module+'.'+name,args,write):lotusMethod(module,name,args,write)
const d=ref(null),working=ref(false),mode=ref(''),reason=ref('')
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const link=computed(()=>props.mobile?'a':Button)
const steps=computed(()=>d.value?.signing?.steps||[])
const state=computed(()=>!d.value?'':d.value.docstatus===2?'Đã đảo':d.value.docstatus===1?'Đã chi':d.value.signing?.returned?'Bị trả lại':d.value.signing?.started?'Đang ký':'Nháp')
const facts=computed(()=>d.value?[d.value.kind,state.value,d.value.party_name,money(d.value.amount),d.value.mode==='cash'?'Tiền mặt':'Chuyển khoản'+(d.value.reference?' '+d.value.reference:''),shortDate(d.value.posting_date)].filter(Boolean).join(' · '):'')
const base=()=>({doctype:d.value.doctype,name:d.value.name})
async function load(){
 mode.value='';reason.value=''
 try{d.value=await call('procurement','voucher',{doctype:props.doctype,name:props.name});emit('loaded',d.value)}catch(e){d.value=null;emit('error',e.message||String(e))}
}
watch(()=>[props.doctype,props.name],load,{immediate:true})
async function run(work,message,{gone=false}={}){
 if(working.value)return
 working.value=true;emit('error','')
 try{
  await work()
  if(gone){emit('notice',message);emit('deleted',props.name)}
  else{await load();emit('changed',d.value);emit('notice',message)}
  window.dispatchEvent(new CustomEvent('lotus-signing-changed'))
 }catch(e){emit('error',e.message||String(e))}finally{working.value=false}
}
async function sign(){
 const step=steps.value[d.value.signing.current]
 if(!await props.ask(confirmText({chain_label:'Phiếu chi',name:d.value.name,amount:d.value.amount,currency:'VND',step_title:step?.title||''})))return
 await run(()=>call('finance.payments','sign_payment',base(),true),'Đã ký phiếu chi '+d.value.name+'.')
}
const sendBack=()=>run(()=>call('finance.payments','return_payment',{...base(),reason:reason.value.trim()},true),'Đã trả lại phiếu chi để sửa.')
async function cancelDraft(){
 if(!await props.ask('Hủy phiếu chi chưa ghi sổ '+d.value.name+'? Số tiền đang giữ cho phiếu được giải phóng.'))return
 await run(()=>call('finance.payments','cancel_draft',{...base(),reason:reason.value.trim()},true),'Đã hủy phiếu chi chưa ghi sổ.',{gone:true})
}
async function reverse(){
 if(!await props.ask('Đảo phiếu chi '+d.value.name+'? Công nợ nhà cung cấp tăng lại đúng số đã chi.'))return
 await run(()=>call('finance.posting','reverse',{posting:d.value.posting,reason:reason.value.trim()},true),'Đã đảo phiếu chi '+d.value.name+'.')
}
function toggle(next){mode.value=mode.value===next?'':next;reason.value=''}
</script>

<template>
 <section v-if="d" class="voucher-detail" :aria-label="'Phiếu chi '+d.name">
  <p class="lotus-form-note">{{facts}}</p>
  <p v-if="d.remark" class="lotus-form-note">{{d.remark}}</p>
  <ul class="voucher-detail__lines" aria-label="Nội dung chi">
   <li v-for="(line,index) in d.lines" :key="index"><span>{{line.label}}</span><b>{{money(line.amount)}}</b></li>
   <li v-if="d.unallocated>0.5"><span>Tạm ứng (chưa gắn hóa đơn)</span><b>{{money(d.unallocated)}}</b></li>
  </ul>
  <LotusSignatureTimeline v-if="steps.length" :steps="steps" :current="d.signing.returned?-1:(d.signing.current??-1)" title="Chữ ký trên phiếu chi"/>
  <StockEvidence :doctype="d.doctype" :name="d.name" :mobile="mobile" :readonly="d.docstatus===2" title="Chứng từ chi (ủy nhiệm chi, biên nhận)"/>
  <div v-if="mode" class="voucher-detail__form">
   <LotusField v-model="reason" :mobile="mobile" type="textarea" :label="mode==='return'?'Lý do trả lại phiếu chi':mode==='cancel'?'Lý do hủy phiếu chưa ghi sổ':'Lý do đảo phiếu chi'"/>
   <component :is="button" v-if="mode==='return'" type="button" variant="destructive" :disabled="working||reason.trim().length<3" @click="sendBack">Trả lại phiếu chi</component>
   <component :is="button" v-if="mode==='cancel'" type="button" variant="destructive" :disabled="working||reason.trim().length<3" @click="cancelDraft">Hủy phiếu chưa ghi sổ</component>
   <component :is="button" v-if="mode==='reverse'" type="button" variant="destructive" :disabled="working||reason.trim().length<5" @click="reverse">Đảo phiếu chi</component>
  </div>
  <div class="procurement-actions">
   <component :is="button" v-if="d.signing?.can_sign&&d.docstatus===0" type="button" :disabled="working" @click="sign">Ký duyệt</component>
   <component :is="button" v-if="d.signing?.can_return" type="button" variant="outline" :disabled="working" @click="toggle('return')">Trả lại</component>
   <component :is="button" v-if="d.can_cancel_draft" type="button" variant="outline" :disabled="working" @click="toggle('cancel')">Hủy phiếu nháp</component>
   <component :is="button" v-if="d.can_reverse&&d.posting" type="button" variant="outline" :disabled="working" @click="toggle('reverse')">Đảo phiếu chi</component>
   <component :is="button" v-for="r in d.references||[]" :key="r.name" type="button" variant="outline" @click="emit('open',r,r.type)">{{r.type==='orders'?'Đơn mua':'Hóa đơn'}} {{r.name}}</component>
   <component :is="link" as="a" variant="outline" :href="d.print_url" target="_blank" rel="noopener">{{d.mode==='cash'?'In phiếu chi':'In giấy đề nghị chi'}}</component>
   <component :is="link" v-if="d.signed_copy" as="a" variant="outline" :href="d.signed_copy.url" target="_blank" rel="noopener">Tải bản PDF đã ký</component>
  </div>
 </section>
</template>

<style>
.voucher-detail{display:grid;gap:var(--lotus-space-3,12px);min-width:0}
.voucher-detail__lines{display:grid;gap:var(--lotus-space-2,8px);margin:0;padding:0;list-style:none}
.voucher-detail__lines li{display:flex;justify-content:space-between;gap:var(--lotus-space-3,12px);padding:var(--lotus-space-2,8px) var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px)}
.voucher-detail__form{display:grid;gap:var(--lotus-space-2,8px);padding:var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px)}
</style>
