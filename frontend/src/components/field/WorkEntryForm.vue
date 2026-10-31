<script setup>
import {computed,reactive,ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import FormSection from '../form/FormSection.vue'
import LineItemsEditor from '../form/LineItemsEditor.vue'
import {Button as UiButton} from '../ui/button'
import {unitLabel} from '../../units'
import {groupSchema,peopleRows,sessionCount,entryPayload,previewAmount,ribbonLeft,payModes,capBases,money,amountText,unitText} from '../../field-work-model.js'
// A day's report on one phiếu giao (lotus_farm.field_report.save_entry): who worked which buổi (only people the time
// clock shows present, not already on another phiếu), how much, and the fields of the work group: ribbon colour for
// bunch work, materials (and pre-harvest interval) for spraying and fertilising, Xong lô. Shared by desktop and /work.
const props=defineProps({ticket:{type:Object,required:true},day:{type:String,required:true},context:{type:Object,required:true},mobile:Boolean})
const emit=defineEmits(['saved','busy-change'])
const api=(name,args={},write=false)=>call('lotus_farm.field_report.'+name,args,write)
const schema=computed(()=>groupSchema(props.ticket))
const people=ref([]),search=ref(''),busy=ref(false),error=ref('')
const form=reactive({qty:null,bunch_tag:null,done:false,notes:'',materials:[]})
function reset(){
 const e=props.ticket.entry
 people.value=peopleRows(props.context.present,props.ticket,e)
 Object.assign(form,{qty:e?.qty??null,bunch_tag:e?.bunch_tag||(schema.value.ribbonChoice?null:props.context.ribbon?.name||null),
  done:!!e?.done,notes:e?.notes||'',materials:(e?.materials||[]).map(m=>({...m}))})
 error.value=''
}
watch(()=>[props.ticket,props.context],reset,{immediate:true})
watch(busy,v=>emit('busy-change',v))

const members=computed(()=>people.value.filter(p=>p.member))
const shown=computed(()=>{const q=search.value.trim().toLowerCase();return people.value.filter(p=>p.member||p.morning||p.afternoon||(q&&String(p.employee_name).toLowerCase().includes(q)))})
const sessions=computed(()=>sessionCount(people.value))
const unit=computed(()=>unitText(unitLabel(props.ticket.uom)||props.ticket.uom,props.ticket.basis))
const ribbonOptions=computed(()=>(props.context.ribbon_options||[]).map(t=>({value:t.name,label:t.label+' · tuần '+t.week})))
const left=computed(()=>{
 if(props.ticket.cap_basis==='CutBud')return ribbonLeft(props.ticket,form.bunch_tag,{cut:props.context.bunch_cut,done:props.context.bunch_done})
 return props.ticket.cap_left==null?null:Number(props.ticket.cap_left)
})
const over=computed(()=>left.value!=null&&Number(form.qty||0)>left.value+1e-6)
const others=computed(()=>Number(props.ticket.progress?.qty||0)-Number(props.ticket.entry?.qty||0))
const preview=computed(()=>previewAmount(props.ticket,others.value+Number(form.qty||0)))
const moneyHint=computed(()=>{
 if(props.ticket.pay_mode==='Daywork')return 'Công nhật: tiền theo máy chấm công.'
 if(props.ticket.pay_mode==='Lot')return 'Cả lô '+money(preview.value)+' khi nghiệm thu đạt, chia theo buổi cho người làm.'
 return 'Tạm tính phiếu '+money(preview.value)+' ('+amountText(others.value+Number(form.qty||0))+' '+unit.value+'), chia theo buổi khi đội trưởng duyệt.'
})
function toggle(row,session){
 if(!row['can_'+session])return
 row[session]=row[session]?0:1
}
function wholeTeam(on){for(const p of members.value){p.morning=on&&p.can_morning?1:0;p.afternoon=on&&p.can_afternoon?1:0}}
const itemOptions=search=>api('item_options',{search}).then(rows=>rows.map(r=>({value:r.name,label:r.item_name+' ('+(unitLabel(r.stock_uom)||r.stock_uom)+')'+(r.lotus_phi_days?' · cách ly '+r.lotus_phi_days+' ngày':'')})))
const materialColumns=[
 {field:'item_code',label:'Thuốc / phân / vật tư',fetchOptions:itemOptions,required:true,width:'minmax(200px,1.6fr)'},
 {field:'qty',label:'Số lượng',type:'number',width:'110px',props:{min:0}},
 {field:'dose',label:'Liều / định lượng',width:'minmax(120px,1fr)'},
 {field:'stock_entry',label:'Phiếu xuất kho',width:'minmax(120px,1fr)'},
]
async function save(){
 error.value=''
 if(!sessions.value){error.value='Chọn ít nhất một người làm, sáng hoặc chiều.';return null}
 if(schema.value.ribbonChoice&&!form.bunch_tag){error.value='Chọn màu dây của lứa buồng đang làm.';return null}
 if(schema.value.materialsRequired&&!form.materials.some(m=>m.item_code)){error.value='Việc này phải ghi vật tư đã dùng.';return null}
 busy.value=true
 try{const r=await api('save_entry',entryPayload(props.ticket,props.day,form,people.value),true);emit('saved',r);return r}
 catch(e){error.value=e.message;return null}
 finally{busy.value=false}
}
defineExpose({save,busy,error})
</script>

<template>
 <div class="work-entry" :class="{'work-entry--mobile':mobile}" :aria-busy="busy">
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <div class="work-entry__head">
   <strong>{{ticket.block_code}} · {{ticket.work_name}}</strong>
   <span>{{ticket.team_name}} · {{payModes[ticket.pay_mode]}}<template v-if="ticket.rate"> · {{money(ticket.rate)}}/{{unit}}</template></span>
   <span v-if="left!=null">Còn được báo: <b>{{amountText(left)}} {{unit}}</b> ({{capBases[ticket.cap_basis]}})</span>
   <span v-if="ticket.state==='Failed'" class="work-entry__warn">Nghiệm thu không đạt – làm lại rồi báo xong lần nữa.</span>
  </div>

  <FormSection title="Người làm hôm nay" :description="'Chỉ hiện người máy chấm công có lượt. Mỗi buổi chỉ ghi vào một phiếu. Đã chọn '+sessions+' buổi.'">
   <div class="work-entry__tools">
    <UiButton type="button" size="sm" variant="outline" :disabled="!members.length" @click="wholeTeam(true)">Chọn cả tổ</UiButton>
    <UiButton type="button" size="sm" variant="ghost" @click="wholeTeam(false)">Bỏ chọn tổ</UiButton>
    <LotusField v-model="search" aria-label="Tìm người ngoài tổ" placeholder="Tìm người ngoài tổ…" :mobile="mobile"/>
   </div>
   <p v-if="!people.length" class="lotus-form-note">Máy chấm công chưa có ai có mặt ngày này.</p>
   <ul class="work-entry__people">
    <li v-for="p in shown" :key="p.employee">
     <span class="work-entry__name"><b>{{p.employee_name}}</b><small>{{p.member?'Trong tổ':'Ngoài tổ'}}</small></span>
     <UiButton v-for="s in ['morning','afternoon']" :key="s" type="button" size="sm" variant="outline" class="work-entry__toggle"
      :class="{'is-on':p[s]}" :disabled="!p['can_'+s]" :aria-pressed="!!p[s]" :aria-label="(s==='morning'?'Sáng ':'Chiều ')+p.employee_name"
      :title="p['taken_'+s]?'Buổi này đã ghi ở phiếu khác':!p['can_'+s]?'Máy chấm công không có lượt buổi này':''" @click="toggle(p,s)">
      {{s==='morning'?'Sáng':'Chiều'}}{{p['taken_'+s]?' · phiếu khác':''}}
     </UiButton>
    </li>
   </ul>
  </FormSection>

  <FormSection title="Kết quả hôm nay">
   <FormGrid :columns="mobile?1:3">
    <LotusField v-model="form.qty" :label="schema.qtyLabel+' ('+unit+')'" type="number" :mobile="mobile" :error="over?'Vượt mức còn được báo':''" :hint="left!=null?'Tối đa '+amountText(left):''"/>
    <LotusField v-if="schema.ribbonChoice" v-model="form.bunch_tag" label="Màu dây của lứa buồng" type="select" :searchable="false" :options="ribbonOptions" required :mobile="mobile"/>
    <div v-else-if="schema.ribbon" class="work-entry__fact"><span>Màu dây cắt bắp tuần này</span><strong>{{context.ribbon?.label||'Chưa có lịch màu'}}</strong></div>
    <LotusField v-model="form.done" type="checkbox" label="Đã làm xong cả lô (báo xong)" :mobile="mobile"/>
   </FormGrid>
   <LineItemsEditor v-if="schema.materials" v-model="form.materials" :columns="materialColumns" :new-row="()=>({item_code:'',qty:null,dose:'',stock_entry:''})" :min="0" :max="6" :mobile="mobile"
    :title="schema.materialsRequired?'Vật tư đã dùng (bắt buộc)':'Vật tư đã dùng'" add-label="Thêm vật tư" empty-text="Chưa ghi vật tư. Thuốc có thời gian cách ly sẽ chặn thu hoạch lô đến hết hạn."/>
   <LotusField v-model="form.notes" type="textarea" label="Ghi chú (nhận xét, đề xuất, lý do)" maxlength="1000" :mobile="mobile"/>
   <p class="lotus-form-note">{{moneyHint}}</p>
  </FormSection>
  <div v-if="mobile" class="work-entry__save"><UiButton type="button" :disabled="busy" @click="save">{{busy?'Đang lưu…':'Lưu báo cáo'}}</UiButton></div>
 </div>
</template>

<style>
.work-entry{display:grid;gap:14px;min-width:0}
.work-entry__head{display:grid;gap:2px;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.work-entry__head strong{font-size:var(--lotus-text-md);color:var(--lotus-text-strong)}
.work-entry__warn{color:var(--lotus-danger)}
.work-entry__tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.work-entry__tools>.lotus-field{flex:1 1 180px}
.work-entry__people{list-style:none;margin:0;padding:0;display:grid;gap:4px;max-height:360px;overflow:auto}
.work-entry__people li{display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid var(--lotus-border)}
.work-entry__name{flex:1 1 auto;display:grid;min-width:0}
.work-entry__name b{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.work-entry__name small{color:var(--lotus-muted)}
.work-entry__toggle{min-width:64px}
.work-entry__toggle.is-on{border-color:var(--lotus-primary);background:var(--lotus-primary-subtle);color:var(--lotus-primary-text);font-weight:600}
.work-entry__fact{display:grid;gap:4px;font-size:var(--lotus-text-sm)}
.work-entry__fact span{color:var(--lotus-muted)}
.work-entry__save{position:sticky;bottom:0;padding:8px 0;background:var(--lotus-surface)}
.work-entry--mobile .work-entry__people{max-height:none}
</style>
