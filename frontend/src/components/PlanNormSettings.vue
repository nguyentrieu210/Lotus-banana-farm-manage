<script setup>
import LotusField from './form/LotusField.vue'
import {computed,nextTick,ref,watch} from 'vue'
import WorkspaceModal from './WorkspaceModal.vue'
import DataTable from './DataTable.vue'
import {unitLabel} from '../units'
import {dismissOnBackdrop} from '../dialogs'
import SchemaForm from './SchemaForm.vue'
import {Button as UiButton} from './ui/button'
import WorkspaceTabs from './WorkspaceTabs.vue'
import {Input as UiInput} from './ui/input'
import UiSelect from './ui/select/Select.vue'
import {consoleAPI} from '../api'
import {cleanFields} from '../domain'
import {ANCHORS} from '../plan-norm-engine'
import {useRouter} from 'vue-router'
const router=useRouter()
import '../plan-norm-settings.css'

const ruleColumns=[
 {field:'rule_name',headerName:'Công việc',valueGetter:p=>(workNames[p.data.work_type]||p.data.rule_name)+' · bản '+p.data.version},
 {field:'anchor',headerName:'Tính từ',valueGetter:p=>ANCHORS[p.data.anchor]||p.data.anchor},
 {field:'offset_days',headerName:'Chênh lệch',valueGetter:p=>(Number(p.data.offset_months)?p.data.offset_months+' tháng lịch + ':'')+(Number(p.data.offset_days)>0?'+':'')+p.data.offset_days+' ngày'},
 {field:'repeat_months',headerName:'Lặp lại',valueGetter:p=>Number(p.data.repeat_months)>0?'Mỗi '+p.data.repeat_months+' tháng lịch':Number(p.data.repeat_days)>0?'Mỗi '+p.data.repeat_days+' ngày':'Một lần'},
 {field:'quantity_basis',headerName:'Đơn vị tính',valueGetter:p=>quantityLabels[p.data.quantity_basis]||p.data.quantity_basis},
 {field:'approval_state',headerName:'Trạng thái',valueGetter:p=>state(p.data)}
]
const book2WorkColumns=[
 {field:'code',headerName:'Mã Book2',minWidth:105},
 {field:'group',headerName:'Nhóm',minWidth:140},
 {field:'title',headerName:'Công việc',minWidth:240},
 {field:'unit',headerName:'Đơn vị',minWidth:95},
 {field:'timing',headerName:'Tần suất / thời điểm',minWidth:245},
 {field:'matched',headerName:'Danh mục ERP',minWidth:170,valueFormatter:p=>p.value?'Đã đối chiếu mã':'Chưa có mã'},
 {field:'productivity',headerName:'Năng suất/công',minWidth:130,valueFormatter:p=>p.value>0?fmt(p.value):'Chưa nghiệm thu'}
]
const props=defineProps({
  farm:{type:String,default:''},block:{type:String,default:''},
  payload:{type:Object,default:()=>({})},loading:Boolean,
})
const emit=defineEmits(['reload'])
const tab=ref('cycle'),dialog=ref(null),editor=ref(null),schema=ref(null),saving=ref(false),error=ref(''),notice=ref('')
const search=ref('')
const descriptions={
  cycle:'Quản lý mốc sinh trưởng và từng đợt cây trong một lô. Dự kiến không phải ngày thực tế.',
  schedule:'Đặt công việc phải làm trước hoặc sau mốc nào. Quy tắc duyệt mới được dùng trong tính thử.',
  norm:'Năng suất lao động, giá khoán và lượng vật tư cần cho từng công việc.',
  book2:'Đối chiếu 43 mã công việc Book2 với danh mục đang có; không tự sửa đơn giá, định mức hay phác đồ.',
}
const groups=[
  {id:'cycle',label:'Chu kỳ cây'},
  {id:'schedule',label:'Lịch công việc'},
  {id:'norm',label:'Định mức'},
  {id:'book2',label:'Đối chiếu Book2'},
]
const perm=doctype=>props.payload?.permissions?.[doctype]||{}
const book2=computed(()=>props.payload?.book2_plan_reference||null)
const cohorts=computed(()=>(props.payload.cohorts||[]).filter(r=>!props.block||r.farm_block===props.block).sort((a,b)=>String(a.farm_block).localeCompare(String(b.farm_block))||String(a.cohort_code).localeCompare(String(b.cohort_code))||Number(b.version)-Number(a.version)))
const types=computed(()=>(props.payload.works||[]).filter(x=>!search.value||String(x.work_name||'').toLowerCase().includes(search.value.toLowerCase())))
const quantityLabels={Trees:'Cây','Selected Suckers':'Chồi đã chọn',Bunches:'Buồng',Area:'Diện tích (ha)'}
const workNames=computed(()=>Object.fromEntries((props.payload.works||[]).map(w=>[w.name,w.work_name])))
const blockNames=computed(()=>Object.fromEntries((props.payload.blocks||[]).map(b=>[b.name,b.block_name||b.name])))
const fmt=(v,d=1)=>v==null?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:d})
watch(()=>[props.farm,props.block],()=>{notice.value='';error.value=''})
function targetRows(type){
 return ({'Plan Cohort':cohorts.value,'Work Schedule Rule':props.payload.rules||[],
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
    <UiButton variant="outline" @click="router.push({path:'/forecast',query:{farm,tab:'profiles'}})">Thông số dự thu</UiButton>
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
    <div class="pn-table-scroll"><DataTable :rows="payload.rules||[]" :columns="ruleColumns" row-key="name" storage-key="plan-norm-rules" interactive @open="open('Work Schedule Rule',$event)" empty="Chưa có quy tắc công việc của vườn." /></div>
   </div>

   <template v-else-if="tab==='norm'">
    <div class="pn-section">
     <div class="pn-section-head"><div><h3>Công việc, năng suất và đơn giá</h3><p>Số lượng hoàn thành trong một công; giá khoán tính trên đơn vị công việc.</p></div>
      <UiInput v-model="search" aria-label="Tìm công việc" placeholder="Tìm công việc..."/>
      <UiButton v-if="perm('Work Type').create" type="button" @click="open('Work Type')">+ Thêm công việc</UiButton>
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

   <template v-else-if="tab==='book2'">
    <section class="pn-section">
     <div class="pn-section-head"><div><h3>Danh mục 43 công việc theo Excel Book2</h3><p>Nguồn: {{book2?.source}} / {{book2?.sheet}}. Bảng này chỉ để đối chiếu, không tạo việc hoặc ghi giá tự động.</p></div></div>
     <p class="pn-hint">{{book2?.warning}}</p>
     <p class="pn-hint">Đã có mã trong danh mục: {{(book2?.works?.length||0)-(book2?.missing_codes?.length||0)}} / {{book2?.works?.length||0}}. Chưa có mã: {{book2?.missing_codes?.length||0}}. Chưa đủ năng suất: {{book2?.missing_productivity?.length||0}}.</p>
     <div class="pn-table-scroll"><DataTable :rows="book2?.works||[]" :columns="book2WorkColumns" row-key="code" storage-key="book2-43-work-catalogue" empty="Chưa có tham chiếu Book2."/></div>
     <p class="pn-hint">Công việc theo chích bắp, thu hoạch, lịch 2 lần/tháng hoặc 2 tháng/lần phải được kỹ thuật và quản lý xác nhận mốc trước khi tạo Work Schedule Rule đã duyệt.</p>
    </section>
   </template>

  </template>
  <Teleport to="body"><WorkspaceModal :title="modalTitle" :busy="saving" ref="dialog" class="pn-dialog" :aria-label="modalTitle" @cancel="saving&&$event.preventDefault()">
    <form v-if="editor&&schema" @submit.prevent="save">
      
      <p v-if="error" class="pn-error" role="alert">{{error}}</p>
      <p v-if="isApproved" class="pn-hint">Bản đã duyệt được giữ nguyên lịch sử. Muốn đổi thì tạo phiên bản mới.</p>
      <HarvestProfileSettings v-if="editor.doctype==='Harvest Profile'" :schema="schema" :model="editor" :scope="{farm}" :readonly="!canWrite||saving"/>
      <SchemaForm v-else :schema="schema" :model="editor" :scope="{farm}" :readonly="!canWrite||saving"/>
      <footer><UiButton v-if="isApproved&&perm(editor.doctype).create" variant="outline" type="button" @click="newVersion">Tạo phiên bản mới</UiButton>
       <UiButton v-if="canWrite" type="submit" :disabled="saving">{{saving?'Đang lưu…':'Lưu cấu hình'}}</UiButton></footer>
    </form>
   </WorkspaceModal></Teleport>
 </section>
</template>
