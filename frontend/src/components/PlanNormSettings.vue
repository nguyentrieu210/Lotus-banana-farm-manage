<script setup>
import {computed,nextTick,ref,watch} from 'vue'
import {unitLabel} from '../units'
import {dismissOnBackdrop} from '../dialogs'
import SchemaForm from './SchemaForm.vue'
import HarvestProfileSettings from './HarvestProfileSettings.vue'
import {Button as UiButton} from './ui/button'
import WorkspaceTabs from './WorkspaceTabs.vue'
import {Input as UiInput} from './ui/input'
import UiSelect from './ui/select/Select.vue'
import {consoleAPI} from '../api'
import {cleanFields} from '../domain'
import {simulate,ANCHORS} from '../plan-norm-engine'
import '../plan-norm-settings.css'

const props=defineProps({
  farm:{type:String,default:''},block:{type:String,default:''},
  payload:{type:Object,default:()=>({})},loading:Boolean,
})
const emit=defineEmits(['reload'])
const tab=ref('cycle'),dialog=ref(null),editor=ref(null),schema=ref(null),saving=ref(false),error=ref(''),notice=ref('')
const from=ref(new Date().toISOString().slice(0,7)),drafts=ref(false),ratoons=ref(true),splits=ref([20,60,20])
const search=ref(''),showWarnings=ref(true),selectedMonth=ref('')
const descriptions={
  cycle:'Quản lý mốc sinh trưởng và từng đợt cây trong một lô. Dự kiến không phải ngày thực tế.',
  schedule:'Đặt công việc phải làm trước hoặc sau mốc nào. Quy tắc duyệt mới được dùng trong tính thử.',
  norm:'Năng suất lao động, giá khoán và lượng vật tư cần cho từng công việc.',
  preview:'Xem 36 tháng trước khi giao việc. Chỉ là số ước tính; không tạo phiếu hoặc xuất kho.',
}
const groups=[
  {id:'cycle',label:'Chu kỳ cây'},
  {id:'schedule',label:'Lịch công việc'},
  {id:'norm',label:'Định mức'},
  {id:'preview',label:'Thử tính 36 tháng'},
]
const perm=doctype=>props.payload?.permissions?.[doctype]||{}
const profileRows=computed(()=>(props.payload.profiles||[]).filter(p=>!p.farm||p.farm===props.farm))
const cohorts=computed(()=>(props.payload.cohorts||[]).filter(r=>!props.block||r.farm_block===props.block).sort((a,b)=>String(a.farm_block).localeCompare(String(b.farm_block))||String(a.cohort_code).localeCompare(String(b.cohort_code))||Number(b.version)-Number(a.version)))
const types=computed(()=>(props.payload.works||[]).filter(x=>!search.value||String(x.work_name||'').toLowerCase().includes(search.value.toLowerCase())))
const quantityLabels={Trees:'Cây','Selected Suckers':'Chồi đã chọn',Bunches:'Buồng',Area:'Diện tích (ha)'}
const workNames=computed(()=>Object.fromEntries((props.payload.works||[]).map(w=>[w.name,w.work_name])))
const blockNames=computed(()=>Object.fromEntries((props.payload.blocks||[]).map(b=>[b.name,b.block_name||b.name])))
const simulationData=computed(()=>({...props.payload,cohorts:cohorts.value,blocks:(props.payload.blocks||[]).filter(b=>!props.block||b.name===props.block)}))
const summary=computed(()=>{
  if(!props.payload?.farm)return null
  try{return simulate(simulationData.value,{from:from.value+'-01',months:36,includeDraft:drafts.value,repeatRatoons:ratoons.value,flowerShares:splits.value.map(Number)})}
  catch(e){return {error:e.message,monthly:[],warnings:[]}}
})
const filteredMonths=computed(()=>summary.value?.monthly?.filter(m=>!selectedMonth.value||m.month===selectedMonth.value)||[])
const activeMonth=computed(()=>selectedMonth.value||'')
const visibleEvents=computed(()=>summary.value?.events?.filter(e=>!activeMonth.value||e.date.startsWith(activeMonth.value))||[])
const visibleHarvests=computed(()=>summary.value?.harvests?.filter(e=>!activeMonth.value||e.month===activeMonth.value)||[])
const sum=(key,rows)=>rows.reduce((a,r)=>a+Number(r[key]||0),0)
const fmt=(v,d=1)=>v==null?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:d})
const monthsPeak=computed(()=>Math.max(1,...(summary.value?.monthly||[]).map(m=>Number(m.packed_kg||0))))
watch(()=>[props.farm,props.block],()=>{selectedMonth.value='';notice.value='';error.value=''})
function targetRows(type){
 return ({'Harvest Profile':profileRows.value,'Plan Cohort':cohorts.value,'Work Schedule Rule':props.payload.rules||[],
  'Material Norm Profile':props.payload.norms||[],'Work Type':types.value})[type]||[]
}
function state(row){return row.approval_state==='Approved'?'Đã duyệt':'Nháp'}
async function open(type,row=null){
  if(!props.farm){error.value='Chọn vườn trước khi cấu hình';return}
  error.value='';notice.value=''
  try{
    schema.value=await consoleAPI('schema',{doctype:type})
    editor.value=row?await consoleAPI('detail',{doctype:type,name:row.name}):{
      doctype:type, farm:props.farm,
      ...(props.block&&['Plan Cohort','Harvest Profile'].includes(type)?{farm_block:props.block}:{}),
      version:1,approval_state:'Draft',
      ...(type==='Plan Cohort'?{anchor:'Planting',quantity_basis:'Bunches',planned_qty:null}:{}),
      ...(type==='Material Norm Profile'?{lines:[{basis_qty:1,frequency:1,conversion_factor:1}]}:{}),
      ...(type==='Harvest Profile'?{active:1}:{}),
      ...(type==='Work Schedule Rule'?{anchor:'Planting',quantity_basis:'Bunches',offset_days:0,repeat_days:0}:{}),
    }
    await nextTick();dialog.value?.showModal()
  }catch(e){error.value=e.message}
}
const isApproved=computed(()=>editor.value?.approval_state==='Approved')
const canWrite=computed(()=>!!schema.value?.permissions?.[editor.value?.name?'write':'create']&&!isApproved.value)
async function save(){
 if(!editor.value||!schema.value||!canWrite.value)return
 saving.value=true;error.value=''
 try{
   const d=editor.value
   await consoleAPI('save',{doctype:d.doctype,name:d.name,base_modified:d.modified,values:cleanFields(schema.value,d)},true)
   dialog.value.close()
   notice.value='Đã lưu cấu hình. Thay đổi chỉ ảnh hưởng kế hoạch mới theo ngày hiệu lực.'
   editor.value=null;schema.value=null;emit('reload')
 }catch(e){error.value=e.message}finally{saving.value=false}
}
async function newVersion(){
 if(!editor.value||!schema.value)return
 const old=editor.value
 const others=targetRows(old.doctype).filter(r=>r.cohort_code&&old.cohort_code?r.cohort_code===old.cohort_code&&r.farm_block===old.farm_block:
   (r.profile_name||r.rule_name)===(old.profile_name||old.rule_name))
 const max=Math.max(Number(old.version)||1,...others.map(r=>Number(r.version)||1))
 const model={...cleanFields(schema.value,old),doctype:old.doctype,version:max+1,approval_state:'Draft'}
 if(old.doctype==='Plan Cohort')model.supersedes=old.name
 if(old.doctype==='Harvest Profile')model.active=0
 if('valid_from' in model)model.valid_from=''
 if('valid_to' in model)model.valid_to=''
 editor.value=model
}
const modalTitle=computed(()=>({
 'Harvest Profile':'Bộ hệ số sinh trưởng','Plan Cohort':'Đợt cây','Work Schedule Rule':'Lịch công việc',
 'Material Norm Profile':'Định mức vật tư','Work Type':'Năng suất & giá khoán'})[editor.value?.doctype]||'Cấu hình')
function toggleMonth(id){selectedMonth.value=selectedMonth.value===id?'':id}
</script>
<template>
 <section class="plan-norm-screen" aria-label="Cấu hình kế hoạch và định mức">
  <header class="pn-header">
   <div><p class="pn-eyebrow">THIẾT LẬP VẬN HÀNH</p><h2>Kế hoạch & định mức</h2>
    <p>Thiết lập một lần, kiểm tra lịch và khối lượng trước khi lập kế hoạch tuần/ngày.</p></div>
   <UiButton variant="outline" type="button" :disabled="loading||!farm" @click="emit('reload')">Làm mới</UiButton>
  </header>
  <p v-if="!farm" class="pn-notice" role="status">Chọn một vườn ở phía trên để xem cấu hình.</p>
  <template v-else>
   <WorkspaceTabs v-model="tab" :items="groups" label="Các phần cấu hình"/>
   <p class="pn-description">{{descriptions[tab]}}</p>
   <p v-if="error&&!dialog?.open" class="pn-error" role="alert">{{error}}</p>
   <p v-if="notice" class="pn-success" role="status">{{notice}}</p>

   <template v-if="tab==='cycle'">
    <div class="pn-section">
     <div class="pn-section-head"><div><h3>Bộ hệ số sinh trưởng</h3><p>Dùng chung theo vườn/giống; chỉ đặt riêng khi lô có khác biệt.</p></div>
      <UiButton v-if="perm('Harvest Profile').create" type="button" @click="open('Harvest Profile')">+ Thêm bộ hệ số</UiButton></div>
     <div class="pn-cards">
      <button v-for="r in profileRows" :key="r.name" class="pn-item" type="button" @click="open('Harvest Profile',r)">
       <span><strong>{{r.profile_name}}</strong><small>{{r.farm_block?(blockNames[r.farm_block]||r.farm_block):'Áp dụng toàn vườn'}} · Phiên bản {{r.version}}</small></span>
       <span class="pn-state" :class="{approved:r.approval_state==='Approved'}">{{state(r)}}</span>
      </button>
      <p v-if="!profileRows.length" class="pn-empty">Chưa có bộ hệ số đọc được. Chưa thể tạo lịch thu tự động.</p>
     </div>
    </div>
    <div class="pn-section">
     <div class="pn-section-head"><div><h3>Các đợt cây trong cùng một lô</h3><p>Mỗi đợt có ngày và số lượng riêng. Đây là dự kiến, không thay cho phiếu hiện trường.</p></div>
      <UiButton v-if="perm('Plan Cohort').create" type="button" @click="open('Plan Cohort')">+ Thêm đợt cây</UiButton></div>
     <div class="pn-cards">
      <button v-for="r in cohorts" :key="r.name" type="button" class="pn-item" @click="open('Plan Cohort',r)">
       <span><strong>{{blockNames[r.farm_block]||r.farm_block}} · {{r.cohort_name}}</strong>
        <small>{{ANCHORS[r.anchor]||r.anchor}} {{r.anchor_date}} · {{fmt(r.planned_qty,0)}} {{r.quantity_basis==='Bunches'?'buồng':r.quantity_basis==='Trees'?'cây':'chồi'}} · bản {{r.version}}</small></span>
       <span class="pn-state" :class="{approved:r.approval_state==='Approved'}">{{state(r)}}</span>
      </button>
      <p v-if="!cohorts.length" class="pn-empty">Chưa có đợt dự kiến nào. Hãy tạo theo từng lô trước khi tính lịch.</p>
     </div>
    </div>
   </template>

   <div v-else-if="tab==='schedule'" class="pn-section">
    <div class="pn-section-head"><div><h3>Quy tắc sinh lịch</h3>
      <p>Ví dụ: cắt bắp vào ngày trổ + 17 ngày. Có thể đặt số ngày âm để làm trước mốc.</p></div>
     <UiButton v-if="perm('Work Schedule Rule').create" type="button" @click="open('Work Schedule Rule')">+ Thêm quy tắc</UiButton>
    </div>
    <div class="pn-table-scroll"><table class="pn-table"><thead><tr><th>Công việc</th><th>Tính từ</th><th>Chênh lệch</th><th>Lặp lại</th><th>Đơn vị tính</th><th>Trạng thái</th></tr></thead>
      <tbody><tr v-for="r in payload.rules||[]" :key="r.name" tabindex="0" role="button" @click="open('Work Schedule Rule',r)" @keydown.enter="open('Work Schedule Rule',r)">
       <td><strong>{{workNames[r.work_type]||r.rule_name}}</strong><small>{{r.rule_name}} · bản {{r.version}}</small></td>
       <td>{{ANCHORS[r.anchor]||r.anchor}}</td><td>{{Number(r.offset_days)>0?'+':''}}{{r.offset_days}} ngày</td>
       <td>{{Number(r.repeat_days)>0?'Mỗi '+r.repeat_days+' ngày':'Một lần'}}</td><td>{{quantityLabels[r.quantity_basis]||r.quantity_basis}}</td><td><span class="pn-state" :class="{approved:r.approval_state==='Approved'}">{{state(r)}}</span></td></tr>
       <tr v-if="!payload.rules?.length"><td colspan="6">Chưa có quy tắc công việc của vườn.</td></tr></tbody></table></div>
   </div>

   <template v-else-if="tab==='norm'">
    <div class="pn-section">
     <div class="pn-section-head"><div><h3>Công việc, năng suất và đơn giá</h3><p>Số lượng hoàn thành trong một công; giá khoán tính trên đơn vị công việc.</p></div>
      <UiInput v-model="search" aria-label="Tìm công việc" placeholder="Tìm công việc..."/>
     </div>
     <div class="pn-cards">
      <button v-for="r in types" :key="r.name" type="button" class="pn-item" @click="open('Work Type',r)">
       <span><strong>{{r.work_name}}</strong><small>Năng suất: {{fmt(r.productivity_per_workday)}} {{unitLabel(r.uom)}}/công · Giá khoán: {{fmt(r.piecework_rate,0)}} đ/{{unitLabel(r.uom)}}</small></span>
       <span class="pn-chevron">Sửa ↗</span>
      </button>
     </div>
    </div>
    <div class="pn-section">
     <div class="pn-section-head"><div><h3>Bộ định mức vật tư</h3><p>Chỉ bản đã duyệt, đúng ngày hiệu lực mới được tính vào nhu cầu vật tư.</p></div>
      <UiButton v-if="perm('Material Norm Profile').create" type="button" @click="open('Material Norm Profile')">+ Thêm bộ định mức</UiButton>
     </div>
     <div class="pn-cards">
      <button v-for="r in payload.norms||[]" :key="r.name" type="button" class="pn-item" @click="open('Material Norm Profile',r)">
       <span><strong>{{workNames[r.work_type]||r.profile_name}}</strong><small>{{r.profile_name}} · {{r.valid_from}} → {{r.valid_to||'chưa có'}} · bản {{r.version}}</small></span>
       <span class="pn-state" :class="{approved:r.approval_state==='Approved'}">{{state(r)}}</span></button>
      <p v-if="!payload.norms?.length" class="pn-empty">Chưa có định mức vật tư.</p>
     </div>
    </div>
   </template>

   <template v-else-if="tab==='preview'">
    <div class="pn-section pn-preview">
      <div class="pn-section-head"><div><h3>Xem trước 36 tháng</h3><p>Không tạo công việc thật hoặc giữ sản lượng bán.</p></div></div>
      <div class="pn-controls">
       <label>Từ tháng<input type="month" v-model="from"/></label>
       <label>Trổ đợt 1 (%)<input type="number" min="0" max="100" step="1" v-model.number="splits[0]"/></label>
       <label>Trổ đợt 2 (%)<input type="number" min="0" max="100" step="1" v-model.number="splits[1]"/></label>
       <label>Trổ đợt 3 (%)<input type="number" min="0" max="100" step="1" v-model.number="splits[2]"/></label>
       <label class="pn-check"><input type="checkbox" v-model="drafts"/> Bao gồm bản nháp để thử</label>
       <label class="pn-check"><input type="checkbox" v-model="ratoons"/> Hiện vụ chồi tương lai</label>
      </div>
      <p class="pn-hint">20%–60%–20% là kịch bản thử có thể chỉnh tại đây; chưa được lưu thành tỷ lệ kỹ thuật chính thức. Chỉ phân 3 đợt cho số BUỒNG dự kiến chưa có mốc trổ thật.</p>
      <p v-if="summary?.error" class="pn-error" role="alert">{{summary.error}}</p>
      <template v-else>
       <div class="pn-stats">
        <div><small>Công việc dự kiến</small><strong>{{fmt(summary?.events?.length||0,0)}}</strong></div>
        <div><small>Số công dự kiến</small><strong>{{fmt(sum('required_workdays',summary?.events||[]))}}</strong></div>
        <div><small>Chi phí khoán biết trước</small><strong>{{fmt(sum('piecework_cost',summary?.events||[]),0)}} đ</strong></div>
        <div><small>Kg đóng gói dự kiến</small><strong>{{fmt(sum('packed_kg',summary?.harvests||[]),0)}} kg</strong></div>
       </div>
       <div class="pn-chart" aria-label="Biểu đồ 36 tháng dự kiến">
        <button v-for="m in summary.monthly" :key="m.month" type="button" :title="m.month+': '+fmt(m.packed_kg,0)+' kg'" :class="{selected:selectedMonth===m.month}" @click="toggleMonth(m.month)">
         <span class="pn-chart-bar" :style="{height:Math.max(2,Math.round(m.packed_kg/monthsPeak*100))+'%'}"></span>
         <small>{{m.month.slice(2)}}</small>
        </button>
       </div>
       <div class="pn-section-head"><h3>{{selectedMonth?'Tháng '+selectedMonth:'Tổng hợp 36 tháng'}}</h3><UiButton v-if="selectedMonth" variant="outline" type="button" @click="selectedMonth=''">Xem tất cả</UiButton></div>
       <div class="pn-table-scroll"><table class="pn-table">
        <thead><tr><th>Tháng</th><th>Công việc</th><th>Công lao động</th><th>Chi phí khoán</th><th>Buồng dự kiến</th><th>Kg buồng</th><th>Kg đóng gói</th></tr></thead>
        <tbody><tr v-for="m in filteredMonths" :key="m.month" @click="toggleMonth(m.month)" tabindex="0" role="button" @keydown.enter="toggleMonth(m.month)">
         <td><strong>{{m.month}}</strong></td><td>{{m.tasks}}</td><td>{{fmt(m.workdays)}}</td><td>{{fmt(m.piecework_cost,0)}}</td><td>{{fmt(m.bunches,0)}}</td><td>{{fmt(m.gross_kg,0)}}</td><td>{{fmt(m.packed_kg,0)}}</td></tr></tbody></table></div>
       <details class="pn-details"><summary>Công việc đến hạn ({{visibleEvents.length}})</summary>
         <div class="pn-table-scroll"><table class="pn-table"><thead><tr><th>Ngày</th><th>Lô</th><th>Đợt</th><th>Công việc</th><th>Khối lượng</th><th>Số công</th></tr></thead>
          <tbody><tr v-for="e in visibleEvents" :key="e.key"><td>{{e.date}}</td><td>{{blockNames[e.farm_block]||e.farm_block}}</td><td>{{e.cohort}}</td><td>{{e.work_type}}</td><td>{{fmt(e.qty)}} {{unitLabel(e.uom)}}</td><td>{{fmt(e.required_workdays)}}</td></tr></tbody></table></div></details>
       <details class="pn-details"><summary>Đợt thu hoạch dự kiến ({{visibleHarvests.length}})</summary>
         <div class="pn-table-scroll"><table class="pn-table"><thead><tr><th>Ngày</th><th>Lô</th><th>Đợt</th><th>Số buồng</th><th>Kg buồng</th><th>Kg đóng gói</th></tr></thead>
          <tbody><tr v-for="h in visibleHarvests" :key="h.cohort+h.date+h.wave"><td>{{h.date}}</td><td>{{blockNames[h.farm_block]||h.farm_block}}</td><td>{{h.cohort}}</td><td>{{fmt(h.bunches,0)}}</td><td>{{fmt(h.gross_kg,0)}}</td><td>{{fmt(h.packed_kg,0)}}</td></tr></tbody></table></div></details>
       <details class="pn-details"><summary>Vật tư cần dùng ({{summary.materials.length}} dòng tính)</summary>
         <div class="pn-table-scroll"><table class="pn-table"><thead><tr><th>Ngày</th><th>Mã vật tư</th><th>Số lượng</th><th>Đơn vị</th></tr></thead><tbody>
          <tr v-for="(m,i) in summary.materials" :key="i"><td>{{m.date}}</td><td>{{m.item}}</td><td>{{fmt(m.quantity,3)}}</td><td>{{unitLabel(m.uom)}}</td></tr></tbody></table></div></details>
       <div v-if="summary.warnings?.length" class="pn-warning">
        <button type="button" @click="showWarnings=!showWarnings">⚠ Có {{summary.warnings.length}} vấn đề cần kiểm tra {{showWarnings?'⌃':'⌄'}}</button>
        <ul v-if="showWarnings"><li v-for="w in summary.warnings" :key="w">{{w}}</li></ul>
       </div>
       <p class="pn-hint">{{summary.rule}} Công nhật chưa có đơn giá sẽ không được tính thành tiền. Vụ chồi tương lai chỉ hiện mốc để tham khảo, chưa nhân sản lượng chưa có căn cứ.</p>
      </template>
    </div>
   </template>
  </template>
  <Teleport to="body"><dialog ref="dialog" class="pn-dialog" :aria-label="modalTitle" @click="dismissOnBackdrop($event,saving)" @cancel="saving&&$event.preventDefault()">
    <form v-if="editor&&schema" @submit.prevent="save">
      <header><div><h2>{{modalTitle}}</h2><small>{{editor.name?'Xem hoặc cập nhật bản ghi':'Tạo cấu hình mới'}} · {{farm}}</small></div>
       <UiButton type="button" variant="outline" :disabled="saving" @click="dialog.close()">Đóng ✕</UiButton></header>
      <p v-if="error" class="pn-error" role="alert">{{error}}</p>
      <p v-if="isApproved" class="pn-hint">Bản đã duyệt được giữ nguyên lịch sử. Muốn đổi thì tạo phiên bản mới.</p>
      <HarvestProfileSettings v-if="editor.doctype==='Harvest Profile'" :schema="schema" :model="editor" :scope="{farm}" :readonly="!canWrite||saving"/>
      <SchemaForm v-else :schema="schema" :model="editor" :scope="{farm}" :readonly="!canWrite||saving"/>
      <footer><UiButton v-if="isApproved&&perm(editor.doctype).create" variant="outline" type="button" @click="newVersion">Tạo phiên bản mới</UiButton>
       <UiButton v-if="canWrite" type="submit" :disabled="saving">{{saving?'Đang lưu…':'Lưu cấu hình'}}</UiButton></footer>
    </form>
   </dialog></Teleport>
 </section>
</template>
