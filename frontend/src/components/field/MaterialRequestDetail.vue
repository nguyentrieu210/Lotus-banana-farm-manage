<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import FormSection from '../form/FormSection.vue'
import ReasonDialog from '../form/ReasonDialog.vue'
import {Button as UiButton} from '../ui/button'
import {useReasonDialog} from '../../use-reason-dialog'
import {unitLabel} from '../../units'
import {formatDate,formatDateTime} from '../../format'
import {stateLabel,stateTone,stateKey,isOverdue,lowered,eventFor,qtyText,crewTeam,detailLines,stockFor,warningText} from '../../issue-request-model.js'
// Một yêu cầu cấp vật tư: đầu phiếu, từng vật tư theo lô (đề nghị · đã cấp · Kho đang lập phiếu · còn), tồn ở kho,
// phiếu xuất, lịch sử, và các nút máy chủ cho phép người này (`actions`): duyệt, giảm số rồi duyệt, trả lại, rút lại,
// gửi, sửa, xóa nháp, đóng phần còn lại, mở lại, hủy, lập lại. Lý do hỏi qua ReasonDialog.
const props=defineProps({name:{type:String,required:true},mobile:Boolean})
const emit=defineEmits(['changed','edit','copy','deleted'])
const api=(method,args={},write=false)=>call('lotus_farm.issue_request.'+method,args,write)
const reason=useReasonDialog()
const doc=ref(null),busy=ref(false),error=ref(''),notice=ref(''),asking=ref(''),lowering=ref(null),lowerReason=ref('')
const commands={}
async function load(){busy.value=true;error.value='';try{doc.value=await api('detail',{name:props.name})}catch(e){error.value=e.message}finally{busy.value=false}}
watch(()=>props.name,load,{immediate:true})

const actions=computed(()=>doc.value?.actions||{})
const key=computed(()=>stateKey(doc.value?.state))
const overdue=computed(()=>isOverdue(doc.value,doc.value?.today))
const issued=l=>Number(l.posted??l.issued_qty??0)
const holding=l=>Number(l.draft??l.draft_qty??0)
const left=l=>l.remaining!=null?Number(l.remaining):Math.max(0,Number(l.qty||0)-issued(l)-holding(l))
const items=computed(()=>{
 const by=new Map()
 for(const l of detailLines(doc.value)){
  if(!by.has(l.item_code))by.set(l.item_code,{item_code:l.item_code,item_name:l.item_name||l.item_code,uom:l.stock_uom||l.uom||'',lines:[]})
  by.get(l.item_code).lines.push(l)
 }
 return [...by.values()]
})
const stockOf=code=>stockFor(doc.value?.stock,code)
const sum=(rows,f)=>rows.reduce((n,l)=>n+f(l),0)
const facts=computed(()=>{
 const d=doc.value
 if(!d)return []
 return [
  ['Đội / tổ',crewTeam(d)],['Việc',d.work_name||d.work_type],['Kho cấp',d.warehouse_name||d.warehouse],['Ngày cần',formatDate(d.needed)],
  ['Người nhận',d.receiver_name||d.receiver||'—'],['Người lập',d.owner_name||d.owner],
  ['Người duyệt',d.approved_by_name||d.approver_name||'—'],
 ].filter(([,v])=>v)
})
const history=computed(()=>(doc.value?.history||[]).map(h=>({at:h.at||h.time||h.creation,who:h.by_name||h.user_name||h.by||h.user||h.owner||'',text:h.text||h.content||''})))

async function write(method,args={},message){
 if(busy.value)return null
 busy.value=true;error.value='';notice.value=''
 try{
  const body={name:props.name,modified:doc.value.modified,...args}
  commands[method]=eventFor(commands[method],body)
  const r=await call('lotus_farm.issue_request.'+method,{...body,client_event_id:commands[method].id},true)
  delete commands[method]
  notice.value=message
  if(method==='delete_draft'){emit('deleted',props.name);return r}
  const next=r?.detail||r
  // Writes answer with detail(); a Quản lý kho without a farm role gets only {name, state, state_code} after closing.
  if(next?.name===props.name&&Array.isArray(next.items))doc.value=next
  else if(next?.state_code)doc.value={...doc.value,state:next.state,state_code:next.state_code,actions:{}}
  else await load()
  emit('changed',doc.value)
  return r
 }catch(e){error.value=e.message;return null}
 finally{busy.value=false;asking.value=''}
}
const approve=()=>write('approve',{},'Đã duyệt. Kho thấy yêu cầu ở "Cấp theo yêu cầu".')
const send=()=>write('send',{},'Đã gửi duyệt.')
const withdraw=()=>write('withdraw',{},'Đã rút lại. Yêu cầu về Nháp.')
const remove=()=>write('delete_draft',{},'Đã xóa nháp.')
async function giveBack(){const text=await reason.ask('Trả lại yêu cầu '+props.name,'Cần sửa gì');if(text)await write('return_request',{reason:text},'Đã trả lại cho người lập.')}
async function close(){const text=await reason.ask('Đóng phần còn lại của '+props.name,'Lý do đóng');if(text)await write('close',{reason:text},'Đã đóng phần còn lại. Kho không cấp tiếp yêu cầu này.')}
async function reopen(){const text=await reason.ask('Mở lại '+props.name,'Lý do mở lại');if(text)await write('reopen',{reason:text},'Đã mở lại. Kho cấp tiếp được phần còn lại.')}
async function cancel(){const text=await reason.ask('Hủy yêu cầu '+props.name,'Lý do hủy');if(text)await write('cancel',{reason:text},'Đã hủy yêu cầu.')}
function startLower(){lowering.value=Object.fromEntries(detailLines(doc.value).map(l=>[l.name,Number(l.qty)]));lowerReason.value='';error.value=''}
async function approveLowered(){
 const result=lowered(detailLines(doc.value),lowering.value)
 if(result.error){error.value=result.error;return}
 if(!result.lines.length){error.value='Chưa giảm dòng nào. Bấm Duyệt nếu giữ nguyên số.';return}
 if(!String(lowerReason.value||'').trim()){error.value='Ghi lý do giảm số.';return}
 const r=await write('approve',{lines:result.lines,reason:lowerReason.value.trim()},'Đã giảm số và duyệt. Số cũ và lý do được giữ trong lịch sử.')
 if(r)lowering.value=null
}
defineExpose({reload:load})
</script>

<template>
 <section class="issue-detail" :class="{'issue-detail--mobile':mobile}" :aria-busy="busy">
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="field-report__notice" role="status">{{notice}}</p>
  <template v-if="doc">
   <header class="issue-detail__head">
    <strong>{{doc.title||doc.name}}</strong>
    <div class="issue-detail__tags">
     <span class="issue-state" :class="'is-'+stateTone(doc.state)">{{stateLabel(doc.state)}}</span>
     <span v-if="overdue" class="issue-state is-danger">Quá hạn chưa cấp</span>
     <span class="issue-detail__name">{{doc.name}}</span>
    </div>
   </header>
   <dl class="issue-detail__facts"><div v-for="[label,value] in facts" :key="label"><dt>{{label}}</dt><dd>{{value}}</dd></div></dl>
   <p v-if="doc.note" class="lotus-form-note">Lý do: {{doc.note}}</p>
   <p v-if="doc.return_reason&&key==='returned'" class="issue-detail__warn">Bị trả lại: {{doc.return_reason}}</p>
   <p v-if="doc.close_reason&&key==='closed'" class="issue-detail__warn">Lý do đóng: {{doc.close_reason}}</p>
   <p v-for="(w,i) in doc.warnings||[]" :key="i" class="issue-detail__warn">{{warningText(w)}}</p>

   <div class="issue-detail__actions">
    <UiButton v-if="actions.approve&&!lowering" type="button" :disabled="busy" @click="asking='approve'">Duyệt</UiButton>
    <UiButton v-if="actions.lower&&!lowering" type="button" variant="outline" :disabled="busy" @click="startLower">Giảm số rồi duyệt</UiButton>
    <UiButton v-if="actions.return" type="button" variant="outline" :disabled="busy" @click="giveBack">Trả lại</UiButton>
    <UiButton v-if="actions.send" type="button" :disabled="busy" @click="send">Gửi duyệt</UiButton>
    <UiButton v-if="actions.edit" type="button" variant="outline" :disabled="busy" @click="emit('edit',doc.name)">Sửa</UiButton>
    <UiButton v-if="actions.withdraw" type="button" variant="outline" :disabled="busy" @click="withdraw">Rút lại</UiButton>
    <UiButton v-if="actions.close" type="button" variant="outline" :disabled="busy" @click="close">Đóng phần còn lại</UiButton>
    <UiButton v-if="actions.reopen" type="button" variant="outline" :disabled="busy" @click="reopen">Mở lại</UiButton>
    <UiButton v-if="actions.cancel" type="button" variant="ghost" :disabled="busy" @click="cancel">Hủy yêu cầu</UiButton>
    <UiButton v-if="actions.delete" type="button" variant="ghost" :disabled="busy" @click="asking='delete'">Xóa nháp</UiButton>
    <UiButton v-if="actions.copy" type="button" variant="ghost" :disabled="busy" @click="emit('copy',doc.name)">Lập lại từ yêu cầu này</UiButton>
    <a v-if="actions.print!==false&&doc.print_url" class="issue-detail__print" :href="doc.print_url" target="_blank" rel="noopener">In phiếu</a>
   </div>
   <div v-if="asking" class="lotus-delete-confirm" role="alert">
    <p v-if="asking==='approve'">Duyệt yêu cầu {{doc.name}}? Đã duyệt thì không sửa được; Kho thấy ngay để cấp.</p>
    <p v-else>Xóa nháp {{doc.name}}? Không lấy lại được.</p>
    <div class="lotus-delete-confirm__actions"><UiButton type="button" variant="outline" @click="asking=''">Chưa</UiButton><UiButton type="button" :disabled="busy" @click="asking==='approve'?approve():remove()">{{asking==='approve'?'Duyệt':'Xóa nháp'}}</UiButton></div>
   </div>

   <FormSection v-if="lowering" title="Giảm số rồi duyệt" description="Chỉ được giảm hoặc để 0 để bỏ dòng. Muốn tăng thì Trả lại.">
    <div class="issue-detail__lower">
     <LotusField v-for="l in detailLines(doc)" :key="l.name" v-model="lowering[l.name]" :label="(l.item_name||l.item_code)+' · '+(l.block_code||l.farm_block)" type="number" min="0" :max="l.qty" :hint="'Đề nghị '+qtyText(l.qty)+' '+unitLabel(l.stock_uom||l.uom)" :mobile="mobile"/>
    </div>
    <FormGrid :columns="1"><LotusField v-model="lowerReason" label="Lý do giảm số" type="textarea" required maxlength="500" :mobile="mobile"/></FormGrid>
    <div class="issue-detail__actions"><UiButton type="button" :disabled="busy" @click="approveLowered">Duyệt với số mới</UiButton><UiButton type="button" variant="ghost" @click="lowering=null">Thôi</UiButton></div>
   </FormSection>

   <FormSection title="Vật tư theo lô">
    <article v-for="it in items" :key="it.item_code" class="issue-detail__item">
     <header><strong>{{it.item_name}}</strong><span>Đề nghị {{qtyText(sum(it.lines,l=>Number(l.qty||0)))}} · đã cấp {{qtyText(sum(it.lines,issued))}} · còn {{qtyText(sum(it.lines,left))}} {{unitLabel(it.uom)}}</span></header>
     <p v-if="stockOf(it.item_code)" class="lotus-form-note">Kho còn {{qtyText(stockOf(it.item_code).available)}} {{unitLabel(it.uom)}} có thể cấp<template v-if="stockOf(it.item_code).waiting"> · đã duyệt chờ cấp cho yêu cầu khác {{qtyText(stockOf(it.item_code).waiting)}} {{unitLabel(it.uom)}}</template></p>
     <ul class="issue-detail__lots">
      <li v-for="l in it.lines" :key="l.name">
       <strong>Lô {{l.block_code||l.farm_block}}</strong>
       <span>Đề nghị {{qtyText(l.qty)}} · Đã cấp {{qtyText(issued(l))}}<template v-if="holding(l)"> · Kho đang lập phiếu {{qtyText(holding(l))}}</template> · Còn {{qtyText(left(l))}} {{unitLabel(it.uom)}}</span>
       <small v-if="l.notes">{{l.notes}}</small>
       <small v-if="l.old_qty!=null&&Number(l.old_qty)!==Number(l.qty)">Số trước khi duyệt: {{qtyText(l.old_qty)}}</small>
      </li>
     </ul>
    </article>
   </FormSection>

   <FormSection v-if="(doc.issues||[]).length" title="Phiếu xuất">
    <ul class="issue-detail__list">
     <li v-for="s in doc.issues" :key="s.name"><strong>{{s.name}}</strong><span>{{formatDate(s.posting_date)}}<template v-if="s.receiver_name||s.lotus_receiver"> · {{s.receiver_name||s.lotus_receiver}}</template><template v-if="s.qty!=null"> · {{qtyText(s.qty)}}</template> · {{Number(s.docstatus)===1?'đã ghi sổ':Number(s.docstatus)===2?'đã hủy':'Kho đang lập phiếu'}}</span></li>
    </ul>
   </FormSection>

   <FormSection v-if="history.length" title="Lịch sử">
    <ul class="issue-detail__list">
     <li v-for="(h,i) in history" :key="i"><strong>{{formatDateTime(h.at)}}<template v-if="h.who"> · {{h.who}}</template></strong><span>{{h.text}}</span></li>
    </ul>
   </FormSection>
  </template>
  <p v-else-if="busy" class="lotus-form-note" role="status">Đang tải yêu cầu…</p>
  <ReasonDialog :dialog="reason"/>
 </section>
</template>

<style>
.issue-detail{display:grid;gap:12px;min-width:0}
.issue-detail__head{display:grid;gap:4px}
.issue-detail__head strong{font-size:var(--lotus-text-md);color:var(--lotus-text-strong)}
.issue-detail__tags{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.issue-detail__name{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.issue-state{display:inline-block;padding:1px 8px;border-radius:var(--lotus-radius-md);border:1px solid var(--lotus-border);font-size:var(--lotus-text-sm);font-weight:600;color:var(--lotus-muted)}
.issue-state.is-warning{color:var(--lotus-warning);border-color:var(--lotus-warning)}
.issue-state.is-danger{color:var(--lotus-danger);border-color:var(--lotus-danger)}
.issue-state.is-info{color:var(--lotus-primary);border-color:var(--lotus-primary)}
.issue-state.is-success{color:var(--lotus-success);border-color:var(--lotus-success)}
.issue-detail__facts{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:6px 16px;margin:0}
.issue-detail__facts dt{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.issue-detail__facts dd{margin:0;font-weight:500}
.issue-detail__warn{margin:0;color:var(--lotus-danger);font-size:var(--lotus-text-sm)}
.issue-detail__actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.issue-detail__print{color:var(--lotus-primary);font-weight:600;font-size:var(--lotus-text-sm)}
.issue-detail__lower{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px 12px}
.issue-detail--mobile .issue-detail__lower,.issue-detail--mobile .issue-detail__facts{grid-template-columns:1fr}
.issue-detail__item{display:grid;gap:6px;padding:10px 12px;margin-bottom:8px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.issue-detail__item header{display:grid;gap:2px}
.issue-detail__item header strong{color:var(--lotus-text-strong)}
.issue-detail__item header span{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.issue-detail__lots,.issue-detail__list{list-style:none;margin:0;padding:0;display:grid;gap:4px}
.issue-detail__lots li,.issue-detail__list li{display:grid;gap:2px;padding:6px 0;border-bottom:1px solid var(--lotus-border);font-size:var(--lotus-text-sm)}
.issue-detail__lots small,.issue-detail__list span{color:var(--lotus-muted)}
</style>
