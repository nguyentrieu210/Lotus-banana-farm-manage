<script setup>
import {computed,onMounted,ref} from 'vue'
import {call} from '../api'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileInput from './LotusMobileInput.vue'
import LotusMobileCheck from './LotusMobileCheck.vue'
import LotusMobileFeedback from './LotusMobileFeedback.vue'
import MobileLinkField from './MobileLinkField.vue'
import {unitLabel} from '../units'
import {formatDate} from '../format'
import {blockList,crewTeam,isOverdue,newEventId,qtyText} from '../issue-request-model.js'
// Kho điện thoại › "Cấp theo yêu cầu" (spec 005, US5): chọn một yêu cầu cấp vật tư đã duyệt, sửa số thực cấp (mặc định
// phần còn lại), chọn người nhận, lưu phiếu nháp (lotus_farm.warehouse.create_draft, chế độ Request), kiểm lại số và tồn
// đang có rồi ghi sổ (submit_document) — cùng đường với máy tính.
const props=defineProps({company:{type:String,required:true},rows:{type:Array,default:()=>[]},employees:{type:Array,default:()=>[]},initial:String,online:{type:Boolean,default:true},today:String})
const emit=defineEmits(['done','busy'])
const api=(name,args={},write=false)=>call('lotus_farm.warehouse.'+name,args,write)
const step=ref('list'),request=ref(''),lines=ref([]),header=ref(null),receiver=ref(''),source=ref(''),draft=ref(null),confirmed=ref(false)
const busy=ref(false),error=ref('')
let eventId=''
const sorted=computed(()=>[...props.rows].sort((a,b)=>String(a.needed||a.schedule_date||'9999').localeCompare(String(b.needed||b.schedule_date||'9999'))))
const employeeOptions=computed(()=>props.employees.map(e=>({value:e.value,label:e.label})))
async function choose(name){
 busy.value=true;error.value='';request.value=name
 try{
  const r=await api('issue_lines',{company:props.company,mode:'Request',name})
  header.value=r.header||null
  lines.value=(r.rows||[]).map(row=>({...row,qty:row.remaining_qty}))
  source.value=r.header?.warehouse||r.rows?.[0]?.warehouse||''
  receiver.value=r.header?.receiver||r.header?.receiver_employee||''
  eventId=newEventId();step.value='lines'
 }catch(e){error.value=e.message}
 finally{busy.value=false}
}
onMounted(()=>{if(props.initial)choose(props.initial)})
async function save(){
 if(busy.value||!props.online)return
 const chosen=lines.value.filter(l=>Number(l.qty)>0)
 if(!chosen.length){error.value='Nhập số thực cấp lớn hơn 0 cho ít nhất một dòng.';return}
 if(chosen.some(l=>Number(l.qty)>Number(l.remaining_qty)+1e-9)){error.value='Số cấp không được vượt phần còn lại của yêu cầu.';return}
 if(!receiver.value){error.value='Chọn người nhận vật tư.';return}
 busy.value=true;error.value='';emit('busy',true)
 try{
  const result=await api('create_draft',{company:props.company,kind:'issue',posting_date:props.today,source:source.value,issue_mode:'Request',issue_purpose:'Production',
   receiver_employee:receiver.value,notes:'',client_event_id:eventId,
   lines:chosen.map(l=>({item:l.item,qty:Number(l.qty),uom:l.uom||l.stock_uom,area:l.area,material_request:l.material_request,material_request_item:l.material_request_item}))},true)
  draft.value=await api('document',{doctype:result.doctype,name:result.name})
  confirmed.value=false;step.value='review'
 }catch(e){error.value=e.message}
 finally{busy.value=false;emit('busy',false)}
}
async function post(){
 if(busy.value||!confirmed.value||!draft.value||!props.online)return
 busy.value=true;error.value='';emit('busy',true)
 try{
  await api('submit_document',{doctype:draft.value.doctype,name:draft.value.name,modified:draft.value.modified},true)
  emit('done','Đã ghi sổ phiếu '+draft.value.name+' theo yêu cầu '+request.value+'.')
 }catch(e){error.value=e.message}
 finally{busy.value=false;emit('busy',false)}
}
function back(){if(step.value==='lines'){step.value='list';return true}return false}
defineExpose({back,step})
</script>

<template>
 <section class="mobile-issue-request">
  <LotusMobileFeedback v-if="error" kind="error">{{error}}</LotusMobileFeedback>
  <template v-if="step==='list'">
   <p v-if="!sorted.length" class="mobile-empty">Không có yêu cầu đã duyệt nào còn chờ cấp.</p>
   <LotusMobileButton v-for="r in sorted" :key="r.name" type="button" class="mobile-list-card clickable" :class="{'is-late':isOverdue({...r,state:r.state||'waiting'},today)}" :disabled="busy" @click="choose(r.name)">
    <strong>{{r.name}} · {{crewTeam(r)}}</strong>
    <small><template v-if="r.work_name">{{r.work_name}} · </template>cần {{formatDate(r.needed||r.schedule_date)}}<template v-if="isOverdue({...r,state:r.state||'waiting'},today)"> · Quá hạn chưa cấp</template></small>
    <small v-if="blockList(r)">Lô {{blockList(r)}}</small>
   </LotusMobileButton>
  </template>

  <form v-else-if="step==='lines'" @submit.prevent="save">
   <fieldset class="mobile-form-fields" :disabled="busy">
    <p class="mobile-subtle">{{request}}<template v-if="header"> · {{crewTeam(header)}}<template v-if="header.work_name"> · {{header.work_name}}</template></template></p>
    <MobileLinkField label="Người nhận hàng" v-model="receiver" :options="employeeOptions" placeholder="Gõ tên người nhận…" required/>
    <div v-for="(l,i) in lines" :key="l.material_request_item||i" class="mobile-line">
     <div class="mobile-line-title"><strong>{{l.item_name}}</strong><span>Lô {{l.area}}</span></div>
     <LotusMobileInput :label="'Số thực cấp ('+unitLabel(l.stock_uom||l.uom)+')'" :aria-label="'Số thực cấp '+l.item_name+' '+l.area" v-model="l.qty" type="number" min="0" :max="l.remaining_qty" step="any" inputmode="decimal" :hint="'Còn '+qtyText(l.remaining_qty)+' '+unitLabel(l.stock_uom||l.uom)"/>
    </div>
    <LotusMobileButton type="submit" class="mobile-submit" :disabled="busy||!online">{{busy?'Đang lưu…':'Lưu phiếu →'}}</LotusMobileButton>
   </fieldset>
  </form>

  <template v-else-if="step==='review'&&draft">
   <div class="mobile-summary"><span>Số phiếu <b>{{draft.name}}</b></span><span>Ngày <b>{{draft.posting_date}}</b></span></div>
   <div v-for="(r,i) in draft.items||[]" :key="i" class="mobile-list-card"><strong>{{r.item_name}}</strong><div class="mobile-inline"><span>Lô {{r.area}}</span><b>{{qtyText(r.qty)}} {{unitLabel(r.uom)}}</b></div><small v-if="r.actual_qty!=null">Tồn đang có: {{qtyText(r.actual_qty)}} {{unitLabel(r.stock_uom||r.uom)}}</small></div>
   <div class="mobile-confirm"><p>Phiếu mới chỉ là nháp. Bấm ghi sổ để trừ tồn kho.</p><LotusMobileCheck v-model="confirmed" :disabled="busy">Đã kiểm tra đúng hàng, số lượng và tồn đang có</LotusMobileCheck><LotusMobileButton class="mobile-submit" type="button" :disabled="!online||busy||!confirmed" @click="post">Ghi sổ phiếu</LotusMobileButton></div>
  </template>
 </section>
</template>

<style>
.mobile-issue-request{display:grid;gap:10px}
.mobile-issue-request .is-late{border-left:4px solid var(--lotus-danger)}
</style>
