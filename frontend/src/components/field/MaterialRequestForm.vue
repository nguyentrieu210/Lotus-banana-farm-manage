<script setup>
import {computed,onMounted,reactive,ref,watch} from 'vue'
import {call} from '../../api'
import ModalForm from '../form/ModalForm.vue'
import FormGrid from '../form/FormGrid.vue'
import FormSection from '../form/FormSection.vue'
import LotusField from '../form/LotusField.vue'
import {Button as UiButton} from '../ui/button'
import {unitLabel} from '../../units'
import {splitByArea,sumQty,buildLines,linesProblem,requestValues,materialsFromLines,isWholeUnit,eventFor,draftKey,keepLocal,readLocal,dropLocal,qtyText,shortDate,detailLines,stockFor,warningText} from '../../issue-request-model.js'
// Lập / sửa một yêu cầu cấp vật tư (lotus_farm.issue_request): một việc, một kho cấp, một ngày cần, nhiều lô; mỗi dòng là
// một vật tư cho một lô, theo đơn vị tồn kho. Số mỗi lô gõ tay, hoặc "Tổng — chia theo diện tích". Đội trưởng và quản lý
// vườn lưu và duyệt luôn (quyết định của chủ vườn 11/11/2026); ai không duyệt được thì gửi duyệt. Số đang gõ được giữ
// trên máy đến khi máy chủ nhận. Dùng chung cho máy tính và /work (mobile).
const props=defineProps({farm:{type:String,required:true},crew:{type:String,required:true},name:String,copyFrom:String,prefill:Object,mobile:Boolean})
const emit=defineEmits(['close','saved'])
const api=(method,args={},write=false)=>call('lotus_farm.issue_request.'+method,args,write)
const data=ref(null),loading=ref(true),busy=ref(false),error=ref(''),restored=ref(false),asking=ref(null),ready=ref(false)
const pick=ref(''),stock=ref({})
const form=reactive({name:'',modified:'',team:'',work_type:'',needed:'',warehouse:'',receiver:'',note:'',picked:{},assignments:{},materials:[],pending:null})
const key=computed(()=>draftKey(props.farm,props.crew,props.name||(props.copyFrom?'copy-'+props.copyFrom:'')))
const commands={}

const blocks=computed(()=>(data.value?.blocks||[]).map(b=>({...b,code:b.block_code||b.code||b.name,zone:b.zone||'',area:Number(b.area_ha)||0})))
const byName=computed(()=>Object.fromEntries(blocks.value.map(b=>[b.name,b])))
const zoneGroups=computed(()=>{const by={};for(const b of blocks.value)(by[b.zone]||(by[b.zone]=[])).push(b);return Object.keys(by).sort().map(zone=>({zone,blocks:by[zone]}))})
const pickedBlocks=computed(()=>blocks.value.filter(b=>form.picked[b.name]))
const wholeCrew=computed(()=>data.value?.whole_crew!==false)
const teamOptions=computed(()=>[...(wholeCrew.value?[{value:'',label:'Cả đội'}]:[]),...(data.value?.teams||[]).map(t=>({value:t.name,label:t.team_name||t.name}))])
const workOptions=computed(()=>(data.value?.works||[]).map(w=>({value:w.name,label:w.work_name||w.name})))
const warehouseOptions=computed(()=>(data.value?.warehouses||[]).map(w=>({value:w.name,label:w.warehouse_name||w.label||w.name})))
const receiverOptions=computed(()=>(data.value?.receivers||[]).map(r=>({value:r.value||r.name,label:r.label||r.employee_name||r.name})))
const canApprove=computed(()=>!!(data.value?.can_approve??data.value?.rights?.approve))
const approverText=computed(()=>{
 const d=data.value
 if(!d)return ''
 if(canApprove.value)return 'Bạn lưu và duyệt luôn; Kho thấy yêu cầu ngay sau khi duyệt.'
 if(d.approver_label)return d.approver_label+' sẽ duyệt yêu cầu này.'
 return ''
})
const today=computed(()=>data.value?.today||'')
const quarantine=b=>b.quarantine_until&&(!today.value||b.quarantine_until>=today.value)?'cách ly đến '+shortDate(b.quarantine_until):''

// Gợi ý (US4): lô đang có phiếu giao việc này cho tổ, lô đến hạn theo vòng chăm sóc, và số của lần trước.
const openTickets=computed(()=>(data.value?.open_assignments||[]).filter(a=>a.work_type===form.work_type&&(!form.team||a.work_team===form.team)&&byName.value[a.farm_block]))
const dueBlocks=computed(()=>(data.value?.due_blocks||[]).filter(d=>d.work_type===form.work_type&&byName.value[d.farm_block]))
const last=computed(()=>(data.value?.last||[]).find(l=>l.work_type===form.work_type)||null)
const lastDose=computed(()=>{const i=last.value?.items?.[0];return i&&Number(i.per_ha)>0?qtyText(i.per_ha)+' '+unitLabel(i.uom)+'/ha'+(last.value.items.length>1?'…':''):''})
function pickTickets(){for(const a of openTickets.value){form.picked[a.farm_block]=true;form.assignments[a.farm_block]=a.name}}
function pickDue(){for(const d of dueBlocks.value)form.picked[d.farm_block]=true}
function pickZone(zone,on){for(const b of blocks.value.filter(x=>x.zone===zone))form.picked[b.name]=on}
function useLast(){
 for(const item of last.value?.items||[]){
  let m=form.materials.find(x=>x.item_code===item.item_code)
  if(!m){m=newMaterial({value:item.item_code,label:item.item_name,uom:item.uom||item.stock_uom,whole:item.whole});form.materials.push(m)}
  m.notes=item.notes||m.notes
  const whole=isWholeUnit(m.uom,m.whole)
  if(Number(item.per_ha)>0){m.mode='each';m.each=null;for(const b of pickedBlocks.value)if(b.area){const q=Number(item.per_ha)*b.area;m.qty[b.name]=whole?Math.round(q):Math.round(q*1000)/1000}}
  else if(Number(item.per_block)>0){m.mode='each';m.each=Number(item.per_block);refill(m)}
 }
}

function newMaterial(option){return {item_code:option.value||option.item_code||option.name,item_name:option.label||option.item_name||option.value,uom:option.uom||option.stock_uom||'',whole:option.whole??option.must_be_whole_number,pack_uom:option.pack_uom||'',pack_factor:Number(option.pack_factor)||0,mode:'each',each:null,total:null,notes:'',qty:{}}}
async function searchItems(search){
 const rows=await api('item_options',{search})
 return (rows||[]).map(r=>({value:r.value||r.item_code||r.name,label:r.label||r.item_name||r.name,uom:r.stock_uom||r.uom,whole:r.whole??r.must_be_whole_number,pack_uom:r.pack_uom,pack_factor:r.pack_factor}))
}
function addItem(option){
 if(!option?.value)return
 if(!form.materials.some(m=>m.item_code===option.value))form.materials.push(newMaterial(option))
 pick.value=''
}
function removeItem(index){form.materials.splice(index,1)}
const split=m=>splitByArea(m.total,pickedBlocks.value.map(b=>({key:b.name,area:b.area})),isWholeUnit(m.uom,m.whole))
// Fill the lô of one vật tư from its "mỗi lô" or "tổng" number; each lô can still be changed by hand afterwards.
function refill(m){
 if(m.mode==='total'){if(m.total==null||m.total==='')return;const r=split(m);m.qty={};for(const b of pickedBlocks.value)m.qty[b.name]=r.qty[b.name]||0}
 else if(m.each!=null&&m.each!==''){for(const b of pickedBlocks.value)m.qty[b.name]=Number(m.each)}
}
const splitNote=m=>{
 if(m.mode!=='total'||!m.total)return ''
 const r=split(m),code=n=>byName.value[n]?.code||n,parts=[]
 if(r.missing.length)parts.push('Lô '+r.missing.map(code).join(', ')+' chưa có diện tích: không chia được cho lô này, nhập tay nếu cần.')
 if(r.dropped.length)parts.push('Lô '+r.dropped.map(code).join(', ')+' nhận 0 '+unitLabel(m.uom)+' sau khi làm tròn: không có dòng cho lô này.')
 return parts.join(' ')
}
const materialTotal=m=>sumQty(Object.fromEntries(pickedBlocks.value.map(b=>[b.name,m.qty[b.name]])))
const packText=(m,q)=>m.pack_uom&&m.pack_factor>0&&q?' ≈ '+qtyText(q/m.pack_factor)+' '+unitLabel(m.pack_uom):''
watch(()=>pickedBlocks.value.map(b=>b.name).join(','),()=>{for(const m of form.materials)refill(m)})

// Stock "có thể cấp lúc này" of the chosen kho: quantities only, no money.
let stockAsk=0
async function loadStock(){
 const codes=form.materials.map(m=>m.item_code)
 if(!form.warehouse||!codes.length){stock.value={};return}
 const mine=++stockAsk
 try{
  const r=await api('stock',{farm:props.farm,items:JSON.stringify(codes),warehouse:form.warehouse})
  if(mine!==stockAsk)return
  const rows=Array.isArray(r)?r:Array.isArray(r?.rows)?r.rows:Object.entries(r||{}).map(([item_code,v])=>({item_code,...v}))
  stock.value=Object.fromEntries(rows.map(s=>[s.item_code,s]))
 }catch{if(mine===stockAsk)stock.value={}}
}
watch(()=>[form.warehouse,form.materials.map(m=>m.item_code).join(',')],loadStock)

function fill(values){
 Object.assign(form,{team:values.team??form.team,work_type:values.work_type||form.work_type,needed:values.needed??form.needed,warehouse:values.warehouse||form.warehouse,receiver:values.receiver??form.receiver,note:values.note??form.note})
}
async function boot(){
 loading.value=true;error.value=''
 try{
  data.value=await api('form_data',{farm:props.farm,crew:props.crew})
  const d=data.value,teams=d.teams||[]
  fill({team:d.whole_crew===false&&teams.length===1?teams[0].name:'',needed:d.today||'',warehouse:d.warehouse||'',receiver:d.receiver||''})
  const source=props.name||props.copyFrom
  if(source){
   const doc=await api('detail',{name:source})
   fill({team:doc.team||'',work_type:doc.work_type,needed:props.name?doc.needed:form.needed,warehouse:doc.warehouse,receiver:doc.receiver||'',note:doc.note||''})
   form.picked={};form.assignments={}
   for(const l of detailLines(doc)){form.picked[l.farm_block]=true;if(l.assignment&&props.name)form.assignments[l.farm_block]=l.assignment}
   form.materials=materialsFromLines(detailLines(doc))
   if(props.name){form.name=doc.name;form.modified=doc.modified}
  }
  const p=props.prefill
  if(p){fill(p);for(const b of p.blocks||[])form.picked[b]=true;Object.assign(form.assignments,p.assignments||{})}
  const kept=readLocal(key.value)
  if(kept){Object.assign(form,kept);restored.value=true}
 }catch(e){error.value=e.message}
 finally{loading.value=false;baseline=JSON.stringify(form);ready.value=true}
}
onMounted(boot)
// Only what the user changed is kept on the device: opening and closing the form leaves nothing behind.
let baseline=''
watch(form,value=>{if(!ready.value||loading.value)return;const text=JSON.stringify(value);if(text!==baseline)keepLocal(key.value,JSON.parse(text))},{deep:true})
async function forget(){dropLocal(key.value);restored.value=false;ready.value=false;Object.assign(form,{name:'',modified:'',team:'',work_type:'',needed:'',warehouse:'',receiver:'',note:'',picked:{},assignments:{},materials:[],pending:null});await boot()}

async function write(method,args){
 commands[method]=eventFor(commands[method],args)
 const r=await api(method,{...args,client_event_id:commands[method].id},true)
 delete commands[method]
 return r?.detail||r
}
function finish(doc,message){dropLocal(key.value);ready.value=false;emit('saved',{doc,message})}
async function submit(sendIt){
 if(busy.value)return
 error.value='';asking.value=null
 if(!form.work_type||!form.warehouse||!form.needed){error.value='Chọn việc, kho cấp và ngày cần.';return}
 const lines=buildLines(form.materials,pickedBlocks.value.map(b=>b.name),form.assignments)
 const problem=linesProblem(lines)
 if(problem){error.value=problem;return}
 const body={farm:props.farm,crew:props.crew,values:requestValues(form,lines),name:form.name||null,modified:form.modified||null,send:0}
 form.pending=eventFor(form.pending,body)
 busy.value=true
 try{
  const r=await api('save',{...body,client_event_id:form.pending.id},true)
  const doc=r?.detail||r,warnings=r?.warnings||doc?.warnings||[]
  form.pending=null;form.name=doc.name;form.modified=doc.modified
  if(!sendIt){finish(doc,'Đã lưu nháp '+doc.name+'.');return}
  if(warnings.length){asking.value={doc,warnings};return}
  await forward(doc)
 }catch(e){error.value=e.message}
 finally{busy.value=false}
}
// After saving as a draft (whose warnings were confirmed): the đội trưởng or quản lý vườn approves their own draft at once
// (approve works on the creator's draft, owner decision 11/11/2026); anyone else sends it for approval.
async function forward(doc){
 const args={name:doc.name,modified:doc.modified}
 if(canApprove.value&&doc.actions?.approve!==false){
  const done=await write('approve',args)
  finish(done,'Đã duyệt yêu cầu '+done.name+'. Kho thấy ngay ở "Cấp theo yêu cầu".')
 }else finish(await write('send',args),'Đã gửi yêu cầu '+doc.name+'. Chờ duyệt.')
}
async function sendAnyway(){
 const doc=asking.value?.doc
 if(!doc||busy.value)return
 busy.value=true;error.value=''
 try{asking.value=null;await forward(doc)}catch(e){error.value=e.message}finally{busy.value=false}
}
const title=computed(()=>props.name?'Sửa yêu cầu '+props.name:'Đề nghị cấp vật tư')
const submitLabel=computed(()=>canApprove.value?'Lưu và duyệt':'Gửi duyệt')
defineExpose({submit,form})
</script>

<template>
 <ModalForm :model-value="true" :title="title" width="860px" :busy="busy" :error="error" :submit-label="submitLabel" :submit-disabled="loading||!data" class="issue-form" :class="{'issue-form--mobile':mobile}"
  @update:model-value="v=>!v&&emit('close')" @submit="submit(true)">
  <p v-if="loading" class="lotus-form-note" role="status">Đang tải…</p>
  <template v-if="data">
   <div v-if="restored" class="issue-form__restored" role="status"><span>Đã mở lại số đang nhập dở trên máy này.</span><UiButton type="button" size="sm" variant="ghost" @click="forget">Bỏ, nhập lại</UiButton></div>
   <FormSection title="Việc và kho">
    <FormGrid :columns="mobile?1:4">
     <LotusField v-model="form.work_type" label="Việc" :options="workOptions" required :mobile="mobile"/>
     <LotusField v-model="form.team" label="Tổ nhận" type="select" :searchable="false" :options="teamOptions" :empty-option="wholeCrew?null:'Chọn tổ'" :mobile="mobile"/>
     <LotusField v-model="form.needed" label="Ngày cần" type="date" required :mobile="mobile"/>
     <LotusField v-model="form.warehouse" label="Kho cấp" type="select" :searchable="false" :options="warehouseOptions" empty-option="Chọn kho" required :mobile="mobile"/>
    </FormGrid>
    <p v-if="approverText" class="lotus-form-note issue-form__approver">{{approverText}}</p>
   </FormSection>

   <FormSection title="Lô">
    <div v-if="openTickets.length||dueBlocks.length" class="issue-form__chips">
     <UiButton v-if="openTickets.length" type="button" size="sm" variant="outline" @click="pickTickets">Lô đang giao việc này cho tổ ({{openTickets.length}})</UiButton>
     <UiButton v-if="dueBlocks.length" type="button" size="sm" variant="outline" @click="pickDue">Lô đến hạn theo vòng chăm sóc ({{dueBlocks.length}})</UiButton>
    </div>
    <p v-if="!blocks.length" class="lotus-form-note">Đội chưa có lô đang hoạt động.</p>
    <div v-for="g in zoneGroups" :key="g.zone" class="issue-form__zone">
     <header><strong>Khu {{g.zone}}</strong><UiButton type="button" size="sm" variant="ghost" @click="pickZone(g.zone,true)">Chọn cả khu</UiButton><UiButton type="button" size="sm" variant="ghost" @click="pickZone(g.zone,false)">Bỏ chọn</UiButton></header>
     <div class="issue-form__lots">
      <div v-for="b in g.blocks" :key="b.name" class="issue-form__lot">
       <LotusField v-model="form.picked[b.name]" type="checkbox" :label="'Lô '+b.code" :mobile="mobile"/>
       <span>{{b.area?qtyText(b.area)+' ha':'chưa có diện tích'}}</span>
       <span v-if="quarantine(b)" class="issue-form__chip is-warning">{{quarantine(b)}}</span>
       <span v-if="form.assignments[b.name]" class="issue-form__chip">theo phiếu giao việc</span>
      </div>
     </div>
    </div>
    <p class="lotus-form-note">Đã chọn {{pickedBlocks.length}} lô.</p>
   </FormSection>

   <FormSection title="Vật tư">
    <div class="issue-form__add">
     <LotusField v-model="pick" label="Thêm vật tư" :fetch-options="searchItems" placeholder="Gõ tên hoặc mã vật tư…" @select="addItem"/>
     <UiButton v-if="last" type="button" variant="outline" @click="useLast">Lấy như lần trước ({{last.request||last.name}}<template v-if="last.date"> · {{shortDate(last.date)}}</template><template v-if="lastDose">, {{lastDose}}</template>)</UiButton>
    </div>
    <p v-if="!form.materials.length" class="lotus-form-note">Chưa có vật tư nào.</p>
    <article v-for="(m,index) in form.materials" :key="m.item_code" class="issue-form__item">
     <header>
      <strong>{{m.item_name}}</strong><span>{{unitLabel(m.uom)}}</span>
      <UiButton type="button" size="sm" variant="ghost" :aria-label="'Bỏ '+m.item_name" @click="removeItem(index)">Bỏ</UiButton>
     </header>
     <FormGrid :columns="mobile?1:3">
      <LotusField v-model="m.mode" :label="'Cách nhập · '+m.item_name" type="select" :searchable="false" :empty-option="null" :options="[{value:'each',label:'Mỗi lô'},{value:'total',label:'Tổng — chia theo diện tích'}]" :mobile="mobile" @update:model-value="refill(m)"/>
      <LotusField v-if="m.mode==='each'" v-model="m.each" :label="'Mỗi lô ('+unitLabel(m.uom)+') · '+m.item_name" type="number" min="0" :mobile="mobile" @update:model-value="refill(m)"/>
      <LotusField v-else v-model="m.total" :label="'Tổng ('+unitLabel(m.uom)+') · '+m.item_name" type="number" min="0" :mobile="mobile" @update:model-value="refill(m)"/>
      <LotusField v-model="m.notes" :label="'Liều, ghi chú · '+m.item_name" maxlength="140" placeholder="VD: 0,5 lít/ha" :mobile="mobile"/>
     </FormGrid>
     <p v-if="splitNote(m)" class="issue-form__warn">{{splitNote(m)}}</p>
     <div v-if="pickedBlocks.length" class="issue-form__qty">
      <LotusField v-for="b in pickedBlocks" :key="b.name" v-model="m.qty[b.name]" :label="'Lô '+b.code" :aria-label="m.item_name+' · '+b.code" type="number" min="0" :mobile="mobile"/>
     </div>
     <p class="lotus-form-note">Cộng {{qtyText(materialTotal(m))}} {{unitLabel(m.uom)}}{{packText(m,materialTotal(m))}}<template v-if="stockFor(stock,m.item_code)"> · Kho còn {{qtyText(stockFor(stock,m.item_code).available)}} {{unitLabel(m.uom)}} có thể cấp<template v-if="stockFor(stock,m.item_code).waiting"> · đã duyệt chờ cấp cho yêu cầu khác {{qtyText(stockFor(stock,m.item_code).waiting)}}</template></template></p>
     <p v-if="stockFor(stock,m.item_code)&&materialTotal(m)>stockFor(stock,m.item_code).available" class="issue-form__warn">Kho không đủ hàng lúc này. Vẫn gửi được; Kho sẽ cấp khi có hàng hoặc đổi kho cấp.</p>
    </article>
   </FormSection>

   <FormSection title="Người nhận và lý do">
    <FormGrid :columns="mobile?1:2">
     <LotusField v-model="form.receiver" label="Người nhận vật tư" :options="receiverOptions" :mobile="mobile"/>
     <LotusField v-model="form.note" label="Lý do" type="textarea" maxlength="500" placeholder="Phun đợt 2 tháng 11…" :mobile="mobile"/>
    </FormGrid>
   </FormSection>

   <div v-if="asking" class="lotus-delete-confirm" role="alert">
    <p v-for="(w,i) in asking.warnings" :key="i">{{warningText(w)}}</p>
    <p>Yêu cầu đã lưu nháp {{asking.doc.name}}. Vẫn {{canApprove?'duyệt':'gửi duyệt'}}?</p>
    <div class="lotus-delete-confirm__actions"><UiButton type="button" variant="outline" @click="asking=null">Sửa lại</UiButton><UiButton type="button" :disabled="busy" @click="sendAnyway">{{canApprove?'Vẫn duyệt':'Vẫn gửi duyệt'}}</UiButton></div>
   </div>
  </template>
  <template #actions><UiButton type="button" variant="outline" :disabled="busy||loading||!data" @click="submit(false)">Lưu nháp</UiButton></template>
 </ModalForm>
</template>

<style>
.issue-form__restored{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;padding:8px 12px;border-radius:var(--lotus-radius-md);background:var(--lotus-surface-muted,var(--lotus-surface));border:1px solid var(--lotus-border);font-size:var(--lotus-text-sm)}
.issue-form__approver{margin-top:8px}
.issue-form__chips{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}
.issue-form__zone{display:grid;gap:6px;margin-top:8px}
.issue-form__zone header{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.issue-form__zone header>*{flex:0 0 auto;width:auto}
.issue-form__lots{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px 12px}
.issue-form--mobile .issue-form__lots{grid-template-columns:repeat(2,minmax(0,1fr))}
.issue-form__lot{display:grid;gap:2px;padding:6px 8px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);min-width:0}
.issue-form__lot span{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.issue-form__chip{justify-self:start;padding:0 6px;border-radius:var(--lotus-radius-md);background:var(--lotus-surface);border:1px solid var(--lotus-border)}
.issue-form__chip.is-warning{color:var(--lotus-warning);border-color:var(--lotus-warning)}
.issue-form__add{display:flex;gap:8px;align-items:end;flex-wrap:wrap}
.issue-form__add>*:first-child{flex:1 1 260px}
.issue-form__item{display:grid;gap:8px;margin-top:10px;padding:10px 12px;border:1px solid var(--lotus-border);border-left:4px solid var(--lotus-primary);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.issue-form__item header{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.issue-form__item header strong{color:var(--lotus-text-strong)}
.issue-form__item header span{color:var(--lotus-muted);font-size:var(--lotus-text-sm);margin-right:auto}
.issue-form__qty{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:6px 10px}
.issue-form--mobile .issue-form__qty{grid-template-columns:repeat(2,minmax(0,1fr))}
.issue-form__warn{margin:0;color:var(--lotus-warning);font-size:var(--lotus-text-sm)}
</style>
