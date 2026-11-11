<script setup>
// Phiếu đề xuất mua vật tư (online) inside the Mua hàng PWA: list, form following the farm's Excel
// columns, and the four-step signing (proposer → department → accounting/purchasing → director).
// A fully priced proposal under 20 triệu only needs proposer → department (lotus_farm.proposal_rules.chain_for_lines).
// The proposer names the three later signers when sending; each is notified on their turn.
import {computed,onMounted,ref,watch} from 'vue'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileInput from './LotusMobileInput.vue'
import LotusMobileSelect from './LotusMobileSelect.vue'
import LotusMobileFeedback from './LotusMobileFeedback.vue'
import MobileLinkField from './MobileLinkField.vue'
import SignerPicker from './SignerPicker.vue'
import LotusSignatureTimeline from './LotusSignatureTimeline.vue'
import PurchaseProgress from './PurchaseProgress.vue'
import LotusMobileDialog from './LotusMobileDialog.vue'
import LotusMobileCheck from './LotusMobileCheck.vue'
import {call} from '../api'
import {unitLabel} from '../units'
import {useMobileConfirm} from '../use-mobile-confirm'
import {PROPOSAL_STAGES,stateTone} from '../purchase-status'
import {confirmText} from '../use-signing'
import {sharePdf} from '../purchase-document'
import '../purchase-mobile-shared.css'
import '../purchase-proposal-mobile.css'

const props=defineProps({company:{type:String,default:''},online:{type:Boolean,default:true},today:{type:String,default:''},startNew:Boolean})
const emit=defineEmits(['notice','error','title','open-document'])
const api=(name,args={},write=false)=>call('lotus_farm.purchase_proposal.'+name,args,write)
const mode=ref('list'),scope=ref('todo'),rows=ref([]),form=ref(null),detail=ref(null),busy=ref(false),saving=ref(false),returnReason=ref(''),setup=ref(null)
const signerOptions=ref(null),signers=ref({}),reassignTo=ref(''),reassignReason=ref('')
const signersMissing=computed(()=>(signerOptions.value?.steps||[]).slice(1).filter(s=>!signers.value[s.key]).map(s=>s.title))
const waitingStep=computed(()=>detail.value&&detail.value.step>0?detail.value.signatures[detail.value.step]:null)
const reassignOptions=computed(()=>(signerOptions.value?.candidates?.[waitingStep.value?.action]||[]).filter(c=>c.user!==waitingStep.value?.assignee).map(c=>({value:c.user,label:c.name,subtitle:c.designation||c.user})))
// Bảng đề xuất (spec 003, FR-026): three views, each stage with its count; the server computes the stage.
const counts=ref({})
const scopes=computed(()=>[['todo','Chờ tôi ký'+(scope.value==='todo'&&rows.value.length?' ('+rows.value.length+')':'')],['mine','Của tôi'],['all','Tất cả']])
const stage=ref('')
const stageOptions=computed(()=>[{value:'',label:'Mọi giai đoạn'},...PROPOSAL_STAGES.map(value=>({value,label:value+' ('+(counts.value[value]||0)+')'}))])
const visibleRows=computed(()=>rows.value.filter(row=>scope.value==='todo'||!stage.value||row.stage===stage.value))
const confirm=useMobileConfirm()
const closeReason=ref(''),cancelReason=ref(''),cancelQuotes=ref(false),signReason=ref(''),panel=ref('')
const money=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:0})+' đ'
const number=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
const vnDate=v=>v?String(v).slice(8,10)+'/'+String(v).slice(5,7)+'/'+String(v).slice(0,4):''
const itemOptions=computed(()=>(setup.value?.items||[]).map(i=>({value:i.name,label:i.item_name,subtitle:i.name})))
const warehouseOptions=computed(()=>(setup.value?.warehouses||[]).map(w=>({value:w.name,label:w.warehouse_name||w.name})))
const pricesOnly=computed(()=>form.value?.edit==='prices')
const total=computed(()=>(form.value?.items||[]).reduce((s,r)=>s+Number(r.qty||0)*Number(r.rate||0),0))
const tone=stateTone
function unitsFor(code){const item=(setup.value?.items||[]).find(i=>i.name===code);if(!item)return []
 return [item.stock_uom,...(setup.value?.conversions||[]).filter(c=>c.parent===code&&c.uom!==item.stock_uom).map(c=>c.uom)].map(u=>({value:u,label:unitLabel(u)}))}
const fail=e=>{emit('error',e.message||String(e))}

async function load(){if(!props.company)return;busy.value=true
 try{const result=await api('proposals',{company:props.company,view:scope.value});rows.value=result.rows||[];counts.value=result.counts||{}}catch(e){fail(e)}finally{busy.value=false}}
async function ensureSetup(){if(!setup.value)setup.value=await api('form_data',{company:props.company})}
const SMALL_LIMIT=20000000
const smallProposal=computed(()=>{const items=form.value?.items||[];return items.length>0&&items.every(r=>Number(r.rate)>0)&&total.value<SMALL_LIMIT})
let signerChain=''
// While writing, the signers follow the proposal's value; a sent proposal keeps the chain it was sent with.
async function ensureSigners(chosen,name){
 const want=name?'doc:'+name:smallProposal.value?'small':'full'
 if(!signerOptions.value||signerChain!==want){signerOptions.value=await api('signer_options',{company:props.company,...(name?{name}:{amount:smallProposal.value?total.value:SMALL_LIMIT,priced:1})});signerChain=want}
 if(chosen)signers.value={...chosen}
}
watch(smallProposal,()=>{if(form.value?.edit==='all')ensureSigners().catch(fail)})
function blankLine(previous){return {key:Math.random().toString(36).slice(2),item_code:'',uom:'',qty:'',rate:'',stock:null,lotus_specification:'',
 // A new line repeats the needed date and purpose of the line above, as most Excel rows do.
 schedule_date:previous?.schedule_date||props.today,lotus_purpose:previous?.lotus_purpose||'',lotus_supplier_hint:'',lotus_notes:''}}
async function newProposal(){busy.value=true
 try{await ensureSetup();await ensureSigners({});form.value={name:null,modified:null,edit:'all',reason:'',department:setup.value.department||'',warehouse:setup.value.warehouses?.[0]?.name||'',items:[blankLine()]};formSnapshot=JSON.stringify(form.value);mode.value='form';emit('title','Lập đề xuất mua')}
 catch(e){fail(e)}finally{busy.value=false}}
async function open(name){busy.value=true
 try{detail.value=await api('detail',{name});returnReason.value='';reassignTo.value='';reassignReason.value='';closeReason.value='';cancelReason.value='';cancelQuotes.value=false;signReason.value='';panel.value=''
  if(detail.value.needs_signers&&detail.value.can_sign||detail.value.can_reassign)await ensureSigners(detail.value.signers,detail.value.name)
  mode.value='detail';emit('title',detail.value.name)}catch(e){fail(e)}finally{busy.value=false}}
async function edit(){busy.value=true
 try{await ensureSetup();const d=detail.value;if(d.edit==='all')await ensureSigners(d.signers);form.value={name:d.name,modified:d.modified,edit:d.edit,reason:d.reason,department:d.department,warehouse:d.warehouse||d.items[0]?.warehouse||'',
  items:d.items.map(r=>({key:r.name,...r}))};formSnapshot=JSON.stringify(form.value);mode.value='form';emit('title','Sửa '+d.name)}catch(e){fail(e)}finally{busy.value=false}}
async function refreshStock(line){
 if(!line.item_code||!form.value.warehouse){line.stock=null;return}
 try{line.stock=(await api('stock_on_hand',{item:line.item_code,warehouse:form.value.warehouse,uom:line.uom})).qty}catch{line.stock=null}}
function chooseItem(line,code){line.item_code=code;const units=unitsFor(code);line.uom=units[0]?.value||'';refreshStock(line)}
function addLine(){form.value.items.push(blankLine(form.value.items.at(-1)))}
function removeLine(index){if(form.value.items.length>1)form.value.items.splice(index,1)}
watch(()=>form.value?.warehouse,()=>{for(const line of form.value?.items||[])refreshStock(line)})
function payload(){const f=form.value
 return {reason:f.reason,department:f.department,warehouse:f.warehouse,items:f.items.map(r=>({item_code:r.item_code,uom:r.uom,qty:r.qty,rate:r.rate||0,warehouse:f.warehouse,
  schedule_date:r.schedule_date,lotus_specification:r.lotus_specification,lotus_supplier_hint:r.lotus_supplier_hint,lotus_purpose:r.lotus_purpose,lotus_notes:r.lotus_notes}))}}
async function save(andSign=false){
 if(saving.value)return
 if(andSign&&!await confirm.ask(confirmText({chain_label:'Phiếu đề xuất mua vật tư',name:form.value.name||'phiếu mới',amount:total.value||null,step_title:'Người đề xuất'})))return
 saving.value=true
 try{
  let result=await api('save_proposal',{company:props.company,values:payload(),name:form.value.name,modified:form.value.modified},true)
  if(andSign)result=await api('sign',{name:result.name,modified:result.modified,signers:signers.value},true)
  detail.value=result;mode.value='detail';emit('title',result.name)
  emit('notice',andSign?'Đã ký và gửi '+result.name+' cho '+(result.waiting_for||result.step_title||'người duyệt')+'.':'Đã lưu nháp '+result.name+'.')
 }catch(e){fail(e)}finally{saving.value=false}}
async function act(action){
 if(saving.value)return
 // FR-012: the confirmation names what is signed before anything is written.
 if(action==='sign'&&!await confirm.ask(confirmText({chain_label:'Phiếu đề xuất mua vật tư',name:detail.value.name,amount:detail.value.total||null,step_title:detail.value.step_title})))return
 if(action==='delete'&&!await confirm.ask('Xóa phiếu nháp '+detail.value.name+'?'))return
 saving.value=true
 try{
  const d=detail.value
  if(action==='close'){detail.value=await api('close_remainder',{name:d.name,modified:d.modified,reason:closeReason.value.trim()},true);panel.value='';emit('notice','Đã đóng phần chưa mua của '+d.name+'.')}
  if(action==='cancel'){detail.value=await api('cancel_proposal',{name:d.name,modified:d.modified,reason:cancelReason.value.trim(),cancel_quotes:cancelQuotes.value?1:0},true);panel.value='';emit('notice','Đã hủy đề xuất '+d.name+'.')}
  if(action==='sign'){detail.value=await api('sign',{name:d.name,modified:d.modified,signers:d.needs_signers?signers.value:undefined,reason:d.needs_reason?signReason.value.trim():undefined},true)
   emit('notice',detail.value.docstatus===1?'Đã phê duyệt '+d.name+'. Phiếu chuyển sang Mua hàng để lập đơn.':'Đã ký. Đã báo '+(detail.value.waiting_for||detail.value.step_title)+' ký tiếp.')}
  if(action==='reassign'){detail.value=await api('reassign_signer',{name:d.name,modified:d.modified,step:waitingStep.value.action,user:reassignTo.value,reason:reassignReason.value.trim()},true);reassignTo.value='';reassignReason.value='';emit('notice','Đã chuyển bước '+d.step_title+' cho '+detail.value.waiting_for+'.')}
  if(action==='return'){detail.value=await api('return_proposal',{name:d.name,modified:d.modified,reason:returnReason.value},true);emit('notice','Đã trả lại '+d.name+' cho người đề xuất.')}
  if(action==='delete'){await api('delete_proposal',{name:d.name,modified:d.modified},true);emit('notice','Đã xóa nháp '+d.name+'.');back();return}
 }catch(e){fail(e)}finally{saving.value=false}}
async function share(){
 const d=detail.value
 try{const result=await sharePdf(d.signed_copy?.url||'/api/method/lotus_farm.www.lotus_material_proposal_print.download_pdf?'+new URLSearchParams({name:d.name}),'de-xuat-mua-'+d.name,'Đề xuất mua '+d.name);if(result==='downloaded')emit('notice','Đã tải PDF '+d.name+'.')}
 catch(e){fail(e)}
}
// Returns true while the proposal screen handles the back button itself.
// Unsaved lines are not dropped silently: leaving the form asks first (the host apps also check hasChanges()).
let formSnapshot=''
const hasChanges=()=>mode.value==='form'&&!!form.value&&JSON.stringify(form.value)!==formSnapshot
function leaveForm(){if(form.value?.name){open(form.value.name);return}
 mode.value='list';form.value=null;detail.value=null;emit('title','Đề xuất mua vật tư');load()}
function back(){
 if(mode.value==='form'){if(hasChanges())confirm.ask('Bỏ thay đổi chưa lưu của đề xuất?').then(ok=>{if(ok)leaveForm()});else leaveForm();return true}
 if(mode.value!=='list'){mode.value='list';form.value=null;detail.value=null;emit('title','Đề xuất mua vật tư');load();return true}
 return false
}
watch(scope,load)
watch(()=>props.company,()=>{setup.value=null;load()})
onMounted(()=>{emit('title','Đề xuất mua vật tư');load();if(props.startNew)newProposal()})
defineExpose({back,newProposal,open,hasChanges})
</script>

<template>
<section class="pp">
 <template v-if="mode==='list'">
  <div class="pp-scopes" role="tablist" aria-label="Lọc đề xuất mua"><button v-for="[id,label] in scopes" :key="id" type="button" role="tab" :aria-selected="scope===id?'true':'false'" :class="{active:scope===id}" @click="scope=id">{{label}}</button></div>
  <LotusMobileButton class="buy-primary" :disabled="busy||!online" @click="newProposal">+ Lập đề xuất mua vật tư</LotusMobileButton>
  <LotusMobileSelect v-if="scope!=='todo'" v-model="stage" label="Giai đoạn" :options="stageOptions"/>
  <LotusMobileFeedback v-if="busy" kind="loading">Đang tải đề xuất…</LotusMobileFeedback>
  <LotusMobileButton v-for="r in visibleRows" :key="r.name" class="buy-card pp-card" @click="open(r.name)">
   <div class="buy-line"><strong>{{r.name}}</strong><span class="buy-order-status" :class="'buy-order-status--'+tone(r.stage)">{{r.stage}}</span></div>
   <small>{{r.proposer}}{{r.department?' · '+r.department:''}} · {{vnDate(r.date)}}{{r.waiting_me?' · chờ bạn ký':''}}</small>
   <p class="pp-reason">{{r.reason||'Chưa ghi lý do'}}</p>
   <div class="buy-line"><span>{{r.lines}} vật tư · cần {{vnDate(r.needed)}}</span><b>{{r.total?money(r.total):'Chưa có giá'}}</b></div>
  </LotusMobileButton>
  <p v-if="!visibleRows.length&&!busy" class="mobile-empty">{{scope==='todo'?'Không có đề xuất nào chờ bạn ký.':'Chưa có đề xuất mua phù hợp.'}}</p>
 </template>

 <template v-if="mode==='form'&&form">
  <p v-if="pricesOnly" class="pp-hint">Bước Kế toán / Mua hàng: chỉ cập nhật đơn giá dự kiến, nhà cung cấp đề xuất và ghi chú.</p>
  <div class="buy-card">
   <LotusMobileInput :model-value="setup?.proposer||''" label="1. Họ tên người đề xuất" disabled/>
   <LotusMobileInput v-model="form.department" label="2. Bộ phận" placeholder="VD: Đội khu A + B + C" :disabled="pricesOnly"/>
   <LotusMobileInput v-model="form.reason" label="3. Lý do đề xuất mua" type="textarea" :rows="2" maxlength="1000" placeholder="VD: Chăm sóc vườn, buồng khu A + B + C" required :disabled="pricesOnly"/>
   <div class="buy-field"><label>Kho nhận hàng</label><MobileLinkField :model-value="form.warehouse" :options="warehouseOptions" :searchable="false" aria-label="Kho nhận hàng" required :disabled="pricesOnly" @update:modelValue="form.warehouse=$event"/></div>
  </div>
  <div v-for="(line,index) in form.items" :key="line.key" class="buy-card pp-line">
   <div class="buy-line"><strong>Dòng {{index+1}}</strong><button v-if="!pricesOnly&&form.items.length>1" type="button" class="pp-remove" :aria-label="'Bỏ dòng '+(index+1)" @click="removeLine(index)">Bỏ dòng</button></div>
   <div class="buy-field"><label>Tên vật tư, nhiên liệu</label><MobileLinkField :model-value="line.item_code" :options="itemOptions" :searchable="true" placeholder="Gõ tên hoặc mã vật tư…" :aria-label="'Vật tư dòng '+(index+1)" required :disabled="pricesOnly" @update:modelValue="chooseItem(line,$event)"/></div>
   <LotusMobileInput v-model="line.lotus_specification" label="Quy cách / thông số kỹ thuật" placeholder="VD: cuộn 1 kg" maxlength="140" :disabled="pricesOnly"/>
   <div class="pp-pair">
    <div class="buy-field"><label>ĐVT</label><MobileLinkField :model-value="line.uom" :options="unitsFor(line.item_code)" :searchable="false" :aria-label="'Đơn vị dòng '+(index+1)" :disabled="pricesOnly||!line.item_code" @update:modelValue="line.uom=$event;refreshStock(line)"/></div>
    <div class="buy-field"><label>SL tồn kho hiện tại</label><p class="pp-stock">{{line.stock===null||line.stock===undefined?'—':number(line.stock)}}</p></div>
   </div>
   <div class="pp-pair">
    <LotusMobileInput v-model="line.qty" label="SL đề xuất mua" type="number" min="0" step="any" required :disabled="pricesOnly"/>
    <LotusMobileInput v-model="line.rate" label="Đơn giá dự kiến (đồng)" type="money"/>
   </div>
   <LotusMobileInput v-model="line.schedule_date" label="Thời gian cần hàng" type="date" :min="today" required :disabled="pricesOnly"/>
   <LotusMobileInput v-model="line.lotus_supplier_hint" label="Nhà cung cấp đề xuất" maxlength="140" placeholder="Không bắt buộc"/>
   <LotusMobileInput v-model="line.lotus_purpose" label="Mục đích sử dụng" maxlength="140" placeholder="VD: Bón, tưới khu A + B + C" :disabled="pricesOnly"/>
   <LotusMobileInput v-model="line.lotus_notes" label="Ghi chú" maxlength="500"/>
   <p v-if="Number(line.rate)>0" class="pp-amount">Thành tiền: <b>{{money(Number(line.qty||0)*Number(line.rate||0))}}</b></p>
  </div>
  <LotusMobileButton v-if="!pricesOnly" class="buy-outline" @click="addLine">+ Thêm vật tư</LotusMobileButton>
  <div class="buy-card pp-total"><span>Cộng {{form.items.length}} dòng</span><b>{{total?money(total):'Chưa có giá dự kiến'}}</b></div>
  <SignerPicker v-if="!pricesOnly" v-model="signers" :options="signerOptions" :disabled="saving"/>
  <LotusMobileButton class="buy-outline" :disabled="saving||!online" @click="save(false)">{{saving?'Đang lưu…':'Lưu nháp'}}</LotusMobileButton>
  <LotusMobileButton v-if="!pricesOnly" class="buy-primary" :disabled="saving||!online||signersMissing.length>0" @click="save(true)">Ký và gửi phụ trách bộ phận</LotusMobileButton>
  <p v-if="!pricesOnly&&signersMissing.length" class="buy-muted">Chọn người ký: {{signersMissing.join(', ')}} để gửi.</p>
 </template>

 <template v-if="mode==='detail'&&detail">
  <div class="buy-card">
   <div class="buy-line"><strong>{{detail.name}}</strong><span class="buy-order-status" :class="'buy-order-status--'+tone(detail.stage)">{{detail.stage}}</span></div>
   <small>{{detail.proposer}}{{detail.department?' · '+detail.department:''}} · {{vnDate(detail.date)}}</small>
   <p class="pp-reason">{{detail.reason}}</p>
   <small>Kho nhận: {{detail.warehouse||'—'}}</small>
  </div>
  <LotusMobileFeedback v-if="detail.state==='Trả lại'&&detail.return_reason" kind="warning">Bị trả lại: {{detail.return_reason}}</LotusMobileFeedback>
  <LotusMobileFeedback v-if="detail.policy_notice" kind="warning">{{detail.policy_notice}}</LotusMobileFeedback>
  <LotusMobileFeedback v-if="detail.closed" kind="info">Đã đóng phần chưa mua{{detail.closed_by?' bởi '+detail.closed_by:''}}: {{detail.close_reason}}</LotusMobileFeedback>
  <LotusMobileFeedback v-if="detail.docstatus===2&&detail.cancel_reason" kind="warning">Đã hủy: {{detail.cancel_reason}}</LotusMobileFeedback>
  <PurchaseProgress v-if="detail.progress" :progress="detail.progress" mobile navigate @open="(row,type)=>emit('open-document',row,type)"/>
  <LotusSignatureTimeline :steps="detail.signatures" :current="detail.state==='Trả lại'?-1:detail.step" title="Các bước ký"/>
  <div v-for="(r,i) in detail.items" :key="r.name" class="buy-card pp-item">
   <div class="buy-line"><strong>{{i+1}}. {{r.item_name}}</strong><b>{{number(r.qty)}} {{unitLabel(r.uom)}}</b></div>
   <small v-if="r.lotus_specification">{{r.lotus_specification}}</small>
   <small>Tồn {{r.stock===null?'—':number(r.stock)}} · cần {{vnDate(r.schedule_date)}}{{r.lotus_supplier_hint?' · NCC: '+r.lotus_supplier_hint:''}}</small>
   <small v-if="r.lotus_purpose">{{r.lotus_purpose}}</small>
   <div v-if="r.rate" class="buy-line"><span>{{money(r.rate)}} / {{unitLabel(r.uom)}}</span><b>{{money(r.amount)}}</b></div>
  </div>
  <div class="buy-card pp-total"><span>Cộng {{detail.items.length}} dòng</span><b>{{detail.total?money(detail.total):'Chưa có giá dự kiến'}}</b></div>
  <a class="buy-outline pp-print" :href="detail.print_url" target="_blank" rel="noopener">Xem / in phiếu đề xuất</a>
  <LotusMobileButton class="buy-outline" :disabled="saving||!online" @click="share">{{detail.signed_copy?'Chia sẻ bản PDF đã ký':'Chia sẻ PDF'}}</LotusMobileButton>
  <LotusMobileButton v-if="detail.edit" class="buy-outline" :disabled="saving" @click="edit">{{detail.edit==='prices'?'Cập nhật đơn giá / nhà cung cấp':'Sửa phiếu'}}</LotusMobileButton>
  <SignerPicker v-if="detail.needs_signers&&detail.can_sign" v-model="signers" :options="signerOptions" :disabled="saving"/>
  <LotusMobileInput v-if="detail.needs_reason&&detail.can_sign" v-model="signReason" label="Lý do đề xuất mua" type="textarea" :rows="2" maxlength="1000" required placeholder="Phiếu nhập từ Excel chưa có lý do. Ghi lý do trước khi ký gửi."/>
  <LotusMobileButton v-if="detail.can_sign" class="buy-primary" :disabled="saving||!online||detail.needs_signers&&signersMissing.length>0||detail.needs_reason&&signReason.trim().length<3" @click="act('sign')">{{detail.step===0?'Ký và gửi phụ trách bộ phận':detail.step===3?'Ký phê duyệt (Giám đốc)':'Ký xác nhận: '+detail.step_title}}</LotusMobileButton>
  <div v-if="detail.can_reassign&&reassignOptions.length" class="buy-card">
   <div class="buy-field"><label>Chuyển bước “{{detail.step_title}}” cho người khác</label><MobileLinkField :model-value="reassignTo" :options="reassignOptions" :searchable="true" placeholder="Chọn người ký thay…" aria-label="Người ký thay" @update:modelValue="reassignTo=$event"/></div>
   <LotusMobileInput v-model="reassignReason" label="Lý do chuyển" maxlength="300" placeholder="Ví dụ: người ký đang nghỉ phép"/>
   <LotusMobileButton class="buy-outline" :disabled="saving||!online||!reassignTo||reassignReason.trim().length<3" @click="act('reassign')">Chuyển người ký</LotusMobileButton>
  </div>
  <div v-if="detail.can_return" class="buy-card">
   <LotusMobileInput v-model="returnReason" label="Lý do trả lại" type="textarea" :rows="2" maxlength="500" placeholder="Nêu rõ cần sửa gì…"/>
   <LotusMobileButton class="buy-danger" :disabled="saving||!online||returnReason.trim().length<3" @click="act('return')">Trả lại người đề xuất</LotusMobileButton>
  </div>
  <LotusMobileButton v-if="detail.can_delete" class="buy-danger" :disabled="saving" @click="act('delete')">Xóa phiếu nháp</LotusMobileButton>
  <LotusMobileButton v-if="detail.can_close" class="buy-outline" :disabled="saving" @click="panel=panel==='close'?'':'close'">Đóng phần chưa mua</LotusMobileButton>
  <div v-if="panel==='close'" class="buy-card">
   <LotusMobileInput v-model="closeReason" label="Lý do đóng phần chưa mua" type="textarea" :rows="2" maxlength="500" placeholder="Ví dụ: đủ hàng trong kho, không mua nữa"/>
   <LotusMobileButton class="buy-primary" :disabled="saving||!online||closeReason.trim().length<3" @click="act('close')">Xác nhận đóng phần chưa mua</LotusMobileButton>
  </div>
  <LotusMobileButton v-if="detail.can_cancel" class="buy-danger" :disabled="saving" @click="panel=panel==='cancel'?'':'cancel'">Hủy đề xuất</LotusMobileButton>
  <div v-if="panel==='cancel'" class="buy-card">
   <LotusMobileInput v-model="cancelReason" label="Lý do hủy đề xuất" type="textarea" :rows="2" maxlength="500"/>
   <LotusMobileCheck v-model="cancelQuotes">Hủy kèm các báo giá chỉ dùng cho đề xuất này</LotusMobileCheck>
   <LotusMobileButton class="buy-danger" :disabled="saving||!online||cancelReason.trim().length<3" @click="act('cancel')">Xác nhận hủy đề xuất</LotusMobileButton>
  </div>
  <p v-if="!detail.can_sign&&detail.docstatus===0&&detail.step" class="buy-muted">Đang chờ {{detail.waiting_for||detail.step_title}} ({{detail.step_title}}) ký.</p>
 </template>
</section>
<LotusMobileDialog :ref="el=>confirm.dialog.value=el" @cancel="confirm.finish(false)">
 <h3>Xác nhận</h3><p>{{confirm.message.value}}</p>
 <LotusMobileButton @click="confirm.finish(false)">Quay lại</LotusMobileButton>
 <LotusMobileButton variant="primary" @click="confirm.finish(true)">Đồng ý</LotusMobileButton>
</LotusMobileDialog>
</template>
