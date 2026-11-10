<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import ModalForm from '../form/ModalForm.vue'
import LineItemsEditor from '../form/LineItemsEditor.vue'
import {Button as UiButton} from '../ui/button'
import {formatDate} from '../../format'
import {unitLabel} from '../../units'
import {workSchema,blankLine,linesFromLot,payloadLines,fingerprint,defaultPeople,peopleCount,colourChoices,saveDraft,loadDraft,clearDraft,
 stageLabels,groupLabels,stateLabels,severities,rejectStages,AFTER_CUT,amountText,swatch} from '../../lot-entry-model.js'
// Every việc of one lô for one tổ and day, in one dialog (lotus_farm.lot_report.save_lot): việc vườn, phun bón with
// materials, kiểm tra sâu bệnh, bunch stages and thu hoạch. Lines already sent or confirmed are shown, not edited.
// What is typed is kept on the phone until the server has it, so a lost signal loses nothing.
const props=defineProps({report:{type:Object,required:true},lot:{type:Object,required:true},data:{type:Object,required:true},mobile:Boolean})
const emit=defineEmits(['close','saved','amend'])
const canAmend=computed(()=>!!props.data.rights?.confirm)
const lines=ref([]),locked=ref([]),baseline=ref(''),saving=ref(false),error=ref(''),rowErrors=ref([]),askDrop=ref(false),restored=ref(false)
const openPeople=ref(''),openNotes=ref('')
const editable=computed(()=>props.data.rights?.write&&['Draft','Reopened'].includes(props.report.state))
const works=computed(()=>Object.fromEntries((props.data.works||[]).map(w=>[w.name,w])))
const workOptions=computed(()=>[...(props.data.works||[])].sort((a,b)=>String(a.group).localeCompare(String(b.group))||String(a.label).localeCompare(String(b.label)))
 .map(w=>({value:w.name,label:w.label+' · '+(groupLabels[w.group]||'')})))
const quick=computed(()=>{
 const given=(props.lot.assignments||[]).filter(a=>a.kind==='Round'&&works.value[a.work_type]).map(a=>works.value[a.work_type])
 const bunch=['Bud Injection','Cut Bud','Bag','Harvest','Reject'].map(s=>(props.data.works||[]).find(w=>w.stage===s)).filter(Boolean)
 const seen=new Set();return [...given,...bunch].filter(w=>!seen.has(w.name)&&seen.add(w.name))
})
const reasonOptions=computed(()=>(props.data.reasons||[]).map(r=>({value:r.name,label:r.reason_name})))
const diseaseOptions=computed(()=>(props.data.diseases||[]).map(d=>({value:d.name,label:d.disease_name})))
const severityOptions=severities.map(s=>({value:s,label:s}))
const present=computed(()=>[...(props.data.present||[])])
const title=computed(()=>'Lô '+props.lot.code+' · '+formatDate(props.data.date))
const dirty=computed(()=>fingerprint(lines.value)!==baseline.value)

function fill(){
 const parts=linesFromLot(props.lot)
 lines.value=parts.editable;locked.value=parts.locked;baseline.value=fingerprint(lines.value)
 const draft=editable.value?loadDraft(props.report.name,props.lot.block,props.report.modified||''):null
 if(draft?.lines&&JSON.stringify(payloadLines(draft.lines))!==baseline.value){lines.value=draft.lines;restored.value=true}
 rowErrors.value=[];error.value=''
}
onMounted(fill)
let timer=null
watch(lines,()=>{if(!editable.value)return;clearTimeout(timer);timer=setTimeout(()=>dirty.value?saveDraft(props.report.name,props.lot.block,lines.value,props.report.modified||''):clearDraft(props.report.name,props.lot.block),400)},{deep:true})

const schema=line=>workSchema(works.value[line.work_type])
const label=line=>works.value[line.work_type]?.label||'Chọn việc'
const unit=line=>unitLabel(works.value[line.work_type]?.uom)||works.value[line.work_type]?.uom||''
// One line per việc and lô, except bao, thu and hủy, which can take several colours or reasons.
const SEVERAL=['Bag','Harvest','Reject']
const hint=ref('')
function add(work){
 hint.value=''
 if(!SEVERAL.includes(work?.stage)){
  if(lines.value.some(l=>l.work_type===work.name)){hint.value=work.label+' đã có ở lô này: sửa số ở dòng đó.';return null}
  if(locked.value.some(l=>l.work_type===work.name)){hint.value=work.label+' của lô này đã gửi. Cần sửa thì nhờ đội trưởng.';return null}
 }
 const l=blankLine(work);l.people=defaultPeople(present.value);lines.value.push(l);return l
}
function addPicked(name){if(name)add(works.value[name])}
function remove(line){lines.value.splice(lines.value.indexOf(line),1)}
function toggle(line,employee,session){
 const p=line.people[employee]||(line.people[employee]={morning:0,afternoon:0})
 p[session]=p[session]?0:1
}
function wholeTeam(line,on){line.people=on?defaultPeople(present.value):{}}
const errorsOf=index=>rowErrors.value.filter(e=>e.index===index).map(e=>e.message)
const generalErrors=computed(()=>rowErrors.value.filter(e=>e.index==null).map(e=>e.message))
const itemOptions=search=>call('lotus_farm.field_report.item_options',{search}).then(rows=>rows.map(r=>({value:r.name,label:r.item_name+' ('+(unitLabel(r.stock_uom)||r.stock_uom)+')'+(r.lotus_phi_days?' · cách ly '+r.lotus_phi_days+' ngày':'')})))
const materialColumns=[
 {field:'item_code',label:'Thuốc / phân / vật tư',fetchOptions:itemOptions,required:true,width:'minmax(200px,1.6fr)'},
 {field:'qty',label:'Số lượng',type:'number',width:'110px',props:{min:0}},
 {field:'dose',label:'Liều dùng',width:'minmax(120px,1fr)'},
 {field:'stock_entry',label:'Phiếu xuất kho',width:'minmax(120px,1fr)'},
]

function requestClose(open){if(open||saving.value)return;if(dirty.value&&editable.value){askDrop.value=true;return};emit('close')}
function dropChanges(){clearDraft(props.report.name,props.lot.block);emit('close')}
async function save(){
 if(saving.value||!editable.value)return
 saving.value=true;error.value='';rowErrors.value=[];askDrop.value=false
 try{
  const result=await call('lotus_farm.lot_report.save_lot',{report:props.report.name,block:props.lot.block,lines:payloadLines(lines.value),expected_modified:props.report.modified},true)
  if(result.errors?.length){rowErrors.value=result.errors;return}
  clearDraft(props.report.name,props.lot.block)
  emit('saved',result)
 }catch(e){error.value=e.message}
 finally{saving.value=false}
}
</script>

<template>
 <ModalForm class="lot-entry-modal" :model-value="true" :title="title" width="860px" :busy="saving" :error="error" :readonly="!editable"
  submit-label="Lưu lô này" :submit-disabled="!dirty" @update:model-value="requestClose" @submit="save">
  <div class="lot-entry__facts">
   <span>Khu {{lot.zone}}</span><span v-if="lot.area_ha">{{amountText(lot.area_ha)}} ha</span><span v-if="lot.trees">{{amountText(lot.trees)}} cây</span><span>Vụ {{lot.cycle||'—'}}</span>
   <span v-if="data.ribbon" class="lot-entry__ribbon"><i :style="{background:swatch(data.ribbon.code)}" aria-hidden="true"></i>Màu dây hôm nay: <b>{{data.ribbon.label}}</b></span>
   <strong v-if="lot.quarantine_until" class="lot-entry__held">Đang cách ly thuốc đến {{formatDate(lot.quarantine_until)}}: chưa được thu hoạch</strong>
  </div>
  <p v-if="restored" class="lotus-form-note lot-entry__restored" role="status">Đã khôi phục số đang nhập dở trên máy này. Kiểm lại rồi bấm Lưu.</p>
  <p v-if="!editable" class="lotus-form-note">{{data.rights?.write?'Báo cáo '+(stateLabels[report.state]||'').toLowerCase()+'. Nhờ đội trưởng mở lại nếu cần sửa.':'Bạn chỉ xem được báo cáo của tổ này.'}}</p>
  <ul v-if="generalErrors.length" class="lot-entry__errors" role="alert"><li v-for="(m,i) in generalErrors" :key="i">{{m}}</li></ul>

  <p v-if="hint" class="lotus-form-note lot-entry__restored" role="status">{{hint}}</p>
  <div v-if="editable" class="lot-entry__quick">
   <UiButton v-for="w in quick" :key="w.name" type="button" size="sm" variant="outline" @click="add(w)">+ {{w.label}}</UiButton>
   <div class="lot-entry__pick"><LotusField :model-value="''" aria-label="Thêm việc khác" :options="workOptions" placeholder="+ Việc khác…" :mobile="mobile" @update:model-value="addPicked"/></div>
  </div>

  <article v-for="(line,index) in lines" :key="line.key" class="lot-entry__line" :class="{'is-error':errorsOf(index).length}">
   <header>
    <strong>{{label(line)}}</strong>
    <span v-if="schema(line).stage">{{stageLabels[schema(line).stage]}}</span>
    <UiButton v-if="editable" type="button" size="sm" variant="ghost" @click="remove(line)">Bỏ việc này</UiButton>
   </header>
   <p v-if="line.machine_read&&line.review_flags" class="lot-entry__flag" role="alert">Máy đọc từ ảnh, cần kiểm: {{line.review_flags}}</p>
   <ul v-if="errorsOf(index).length" class="lot-entry__errors" role="alert"><li v-for="(m,i) in errorsOf(index)" :key="i">{{m}}</li></ul>
   <FormGrid :columns="mobile?1:3">
    <template v-if="schema(line).kind==='disease'">
     <LotusField v-model="line.disease" label="Bệnh" type="select" :searchable="false" :options="diseaseOptions" required :mobile="mobile" :disabled="!editable"/>
     <LotusField v-model="line.qty" label="Số cây bị" type="number" inputmode="numeric" required :mobile="mobile" :disabled="!editable"/>
     <LotusField v-model="line.severity" label="Mức độ" type="select" :searchable="false" :options="severityOptions" required :mobile="mobile" :disabled="!editable"/>
    </template>
    <template v-else-if="schema(line).kind==='sucker'">
     <LotusField v-model="line.area_ha" label="Diện tích đã chọn chồi (ha)" type="number" inputmode="decimal" required :mobile="mobile" :disabled="!editable"
      :hint="lot.area_ha?'Lô '+amountText(lot.area_ha)+' ha · số chồi ước tính theo số cây':''"/>
    </template>
    <template v-else>
     <LotusField v-model="line.qty" :label="schema(line).qtyLabel+(schema(line).kind==='field'&&unit(line)?' ('+unit(line)+')':'')" type="number"
      :inputmode="schema(line).whole?'numeric':'decimal'" :required="schema(line).kind==='bunch'" :mobile="mobile" :disabled="!editable"/>
     <div v-if="schema(line).autoColour" class="lot-entry__fact"><span>Màu dây</span><strong>{{data.ribbon?.label||'Chưa có lịch màu dây'}}</strong></div>
     <LotusField v-if="schema(line).pickColour" v-model="line.bunch_tag" label="Màu dây" type="select" :searchable="false" required
      :options="colourChoices(lot,schema(line).stage,line.bunch_tag)" :mobile="mobile" :disabled="!editable"
      :hint="!colourChoices(lot,schema(line).stage,line.bunch_tag).length?'Lô này chưa có buồng cắt bắp còn lại.':''"/>
     <LotusField v-if="schema(line).kg" v-model="line.weight_kg" label="Khối lượng thu (kg)" type="number" inputmode="decimal" required :mobile="mobile" :disabled="!editable"/>
     <template v-if="schema(line).reason">
      <LotusField v-model="line.reject_stage" label="Hủy trước hay sau cắt bắp" type="select" :searchable="false" :options="rejectStages" required :mobile="mobile" :disabled="!editable"/>
      <LotusField v-model="line.reason" label="Lý do" type="select" :searchable="false" :options="reasonOptions" required :mobile="mobile" :disabled="!editable"/>
      <LotusField v-if="line.reject_stage===AFTER_CUT" v-model="line.bunch_tag" label="Màu dây" type="select" :searchable="false" required
       :options="colourChoices(lot,'Reject',line.bunch_tag)" :mobile="mobile" :disabled="!editable"/>
     </template>
    </template>
    <LotusField v-if="schema(line).done" v-model="line.done" type="checkbox" label="Đã làm xong cả lô" :mobile="mobile" :disabled="!editable"/>
   </FormGrid>
   <LineItemsEditor v-if="schema(line).materials" v-model="line.materials" :columns="materialColumns" :new-row="()=>({item_code:'',qty:null,dose:'',stock_entry:''})"
    :min="0" :max="6" :mobile="mobile" :readonly="!editable" :title="schema(line).materialsRequired?'Vật tư đã dùng (bắt buộc, ghi cả liều)':'Vật tư đã dùng'"
    add-label="Thêm vật tư" empty-text="Thuốc có thời gian cách ly sẽ chặn thu hoạch lô đến hết hạn."/>
   <div class="lot-entry__people">
    <UiButton type="button" size="sm" variant="ghost" :aria-expanded="openPeople===line.key" @click="openPeople=openPeople===line.key?'':line.key">
     Người làm: {{peopleCount(line.people)}} buổi {{openPeople===line.key?'▲':'▼'}}
    </UiButton>
    <UiButton type="button" size="sm" variant="ghost" @click="openNotes=openNotes===line.key?'':line.key">{{line.notes?'Ghi chú ✓':'Ghi chú'}}</UiButton>
   </div>
   <div v-if="openPeople===line.key" class="lot-entry__people-list">
    <div v-if="editable" class="lot-entry__people-tools">
     <UiButton type="button" size="sm" variant="outline" @click="wholeTeam(line,true)">Cả tổ có mặt</UiButton>
     <UiButton type="button" size="sm" variant="ghost" @click="wholeTeam(line,false)">Bỏ hết</UiButton>
    </div>
    <p v-if="!present.length" class="lotus-form-note">Máy chấm công chưa có ai của đội có mặt ngày này.</p>
    <ul>
     <li v-for="p in present" :key="p.employee">
      <span><b>{{p.employee_name}}</b><small>{{p.own?'Trong tổ':'Tổ khác'}}</small></span>
      <UiButton v-for="s in ['morning','afternoon']" :key="s" type="button" size="sm" variant="outline" class="lot-entry__toggle"
       :class="{'is-on':line.people[p.employee]?.[s]}" :disabled="!editable||!p[s]" :aria-pressed="!!line.people[p.employee]?.[s]"
       :title="!p[s]?'Máy chấm công không có lượt buổi này':''" @click="toggle(line,p.employee,s)">{{s==='morning'?'Sáng':'Chiều'}}</UiButton>
     </li>
    </ul>
   </div>
   <LotusField v-if="openNotes===line.key" v-model="line.notes" type="textarea" label="Ghi chú (nhận xét, đề xuất)" maxlength="1000" :mobile="mobile" :disabled="!editable"/>
  </article>
  <p v-if="editable&&!lines.length" class="lotus-form-note">Chưa có việc nào ở lô này hôm nay. Bấm một nút ở trên để thêm.</p>

  <section v-if="locked.length" class="lot-entry__locked">
   <h3>Đã gửi hoặc đã xác nhận</h3>
   <ul><li v-for="l in locked" :key="l.name">{{works[l.work_type]?.label||l.work_type}}<template v-if="l.stage==='Sucker Select'"> · {{amountText(l.area_ha)}} ha</template><template v-else> · {{amountText(l.qty)}}</template><template v-if="l.weight_kg"> · {{amountText(l.weight_kg)}} kg</template> · {{stateLabels[l.state]||l.state}}
    <UiButton v-if="canAmend&&l.state==='Confirmed'" type="button" size="sm" variant="ghost" @click="emit('amend',l)">Sửa có lý do</UiButton></li></ul>
  </section>
  <div v-if="askDrop" class="lotus-delete-confirm" role="alert">
   <p>Số vừa nhập chưa được lưu. Bỏ các thay đổi này?</p>
   <div class="lotus-delete-confirm__actions"><UiButton type="button" variant="outline" @click="askDrop=false">Tiếp tục nhập</UiButton><UiButton type="button" variant="destructive" @click="dropChanges">Bỏ thay đổi</UiButton></div>
  </div>
 </ModalForm>
</template>

<style>
.lot-entry__facts{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.lot-entry__ribbon{display:inline-flex;align-items:center;gap:6px}
.lot-entry__ribbon i{display:inline-block;width:12px;height:12px;border-radius:50%;border:1px solid var(--lotus-border)}
.lot-entry__held{color:var(--lotus-danger)}
.lot-entry__restored{color:var(--lotus-warning)}
.lot-entry__quick{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.lot-entry__pick{min-width:200px;flex:1 1 200px}
.lot-entry__line{display:grid;gap:8px;padding:10px 12px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.lot-entry__line.is-error{border-color:var(--lotus-danger)}
.lot-entry__line header{display:flex;align-items:center;gap:8px}
.lot-entry__line header strong{font-weight:600;color:var(--lotus-text-strong)}
.lot-entry__line header span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.lot-entry__line header button{margin-left:auto}
.lot-entry__flag{margin:0;color:var(--lotus-warning);font-size:var(--lotus-text-sm)}
.lot-entry__fact{display:grid;gap:4px;font-size:var(--lotus-text-sm)}
.lot-entry__fact span{color:var(--lotus-muted)}
.lot-entry__people{display:flex;gap:6px;flex-wrap:wrap}
.lot-entry__people-list ul{list-style:none;margin:0;padding:0;display:grid;gap:4px;max-height:280px;overflow:auto}
.lot-entry__people-list li{display:flex;align-items:center;gap:6px;padding:3px 0;border-bottom:1px solid var(--lotus-border)}
.lot-entry__people-list li>span{flex:1 1 auto;display:grid;min-width:0}
.lot-entry__people-list small{color:var(--lotus-muted)}
.lot-entry__people-tools{display:flex;gap:6px;margin-bottom:6px}
.lot-entry__toggle{min-width:60px}
.lot-entry__toggle.is-on{border-color:var(--lotus-primary);background:var(--lotus-primary-subtle);color:var(--lotus-primary-text);font-weight:600}
.lot-entry__errors{margin:0;padding-left:18px;color:var(--lotus-danger);font-size:var(--lotus-text-sm)}
.lot-entry__locked h3{margin:0 0 4px;font-size:var(--lotus-text-sm);color:var(--lotus-muted);font-weight:600}
.lot-entry__locked ul{margin:0;padding-left:18px;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.lot-entry-modal .lotus-pwa-field.van-cell{padding:6px 10px}
</style>
