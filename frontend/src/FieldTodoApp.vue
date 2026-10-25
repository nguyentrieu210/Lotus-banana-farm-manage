<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {call} from './api'
import MobileLinkField from './components/MobileLinkField.vue'
import LotusMobileInput from './components/LotusMobileInput.vue'
import LotusMobileButton from './components/LotusMobileButton.vue'
import LotusMobileFeedback from './components/LotusMobileFeedback.vue'
import './field-todo.css'

const props=defineProps({
 farm:{type:String,required:true},
 date:{type:String,default:''},
 canAssign:{type:Boolean,default:false},
 canCapture:{type:Boolean,default:false},
 user:{type:String,default:''}
})
const busy=ref(false),error=ref(''),message=ref('')
const catalog=ref({groups:[],sections:[],works:[],blocks:[],teams:[]})
const rows=ref([])
const page=ref('board'),selected=ref(null),group=ref(''),state=ref('open'),search=ref('')
const reportQty=ref(''),reportNote=ref(''),reviewNote=ref(''),reassignTeam=ref('')
const form=ref(null)
const fmt=v=>Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
const groups=computed(()=>catalog.value.groups||[])
const groupOptions=computed(()=>[{value:'',label:'Tất cả nhóm'},...groups.value.map(g=>({value:g.code,label:g.name+' ('+g.count+')'}))])
const filtered=computed(()=>rows.value.filter(t=>{
 if(group.value&&t.group_code!==group.value)return false
 if(state.value==='open'&&t.status==='Accepted')return false
 if(state.value==='accepted'&&t.status!=='Accepted')return false
 const q=String(search.value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase()
 return !q||[t.work_name,t.block_code,t.team_name,t.section].join(' ').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes(q)
}))
const stages=computed(()=>groups.value.map(g=>({value:g.code,label:g.name})))
const sections=computed(()=>catalog.value.sections.filter(s=>s[2]===form.value?.group_code).map(s=>({value:s[0],label:s[1]})))
const works=computed(()=>(catalog.value.works||[]).filter(w=>w.section_code===form.value?.section_code).map(w=>({value:w.name,label:w.work_name})))
const blocks=computed(()=>(catalog.value.blocks||[]).map(b=>({value:b.name,label:'Lô '+(b.block_code||b.block_name||b.name)})))
const teams=computed(()=>(catalog.value.teams||[]).map(t=>({value:t.name,label:t.team_name||t.team_code})))
const canReview=computed(()=>!!catalog.value.can_review)
const statusText=s=>({Open:'Chưa làm',Doing:'Đang làm',Reported:'Chờ nghiệm thu',Accepted:'Đã nghiệm thu',Rework:'Cần làm lại'})[s]||s
const isDirty=()=>page.value==='create'&&!!form.value&&Boolean(form.value.work_type||form.value.work_team||form.value.farm_block||form.value.description)
defineExpose({isDirty,refresh})
async function refresh(){
 if(!props.farm)return
 busy.value=true;error.value=''
 try{
  const [c,b]=await Promise.all([
   call('lotus_farm.field_todo.catalog',{farm:props.farm}),
   call('lotus_farm.field_todo.board',{farm:props.farm,include_closed:1})
  ])
  catalog.value=c;rows.value=b.rows||[]
  if(selected.value)selected.value=rows.value.find(r=>r.name===selected.value.name)||selected.value
 }catch(e){error.value=e.message||'Không tải được bảng giao việc.'}
 finally{busy.value=false}
}
watch(()=>props.farm,()=>{page.value='board';selected.value=null;refresh()})
onMounted(refresh)
function newTask(){
 const d=props.date||new Date().toISOString().slice(0,10)
 form.value={farm_block:'',work_team:'',group_code:'0103',section_code:'',work_type:'',
  tracking_mode:'Completion',start_date:d,due_date:d,target_qty:'',
  quantity_unit:'',description:'',request_key:crypto.randomUUID()}
 error.value='';message.value='';page.value='create'
}
async function create(){
 const f=form.value
 if(!f||busy.value)return
 if(!f.work_type||!f.work_team||!f.farm_block||!f.start_date||!f.due_date){
  error.value='Chọn đủ công việc, lô, tổ và thời hạn.';return
 }
 if(f.tracking_mode==='Quantity'&&(!f.quantity_unit.trim()||f.target_qty!==''&&(!Number.isFinite(Number(f.target_qty))||Number(f.target_qty)<0))){
  error.value='Nhập đơn vị và số lượng dự kiến hợp lệ.';return
 }
 busy.value=true;error.value=''
 try{
  await call('lotus_farm.field_todo.create',{farm:props.farm,...f,
    target_qty:f.tracking_mode==='Quantity'&&f.target_qty!==''?Number(f.target_qty):null},true)
  page.value='board';form.value=null
  await refresh();message.value='Đã giao việc cho tổ.'
 }catch(e){error.value=e.message||'Không giao được việc.'}
 finally{busy.value=false}
}
function detail(t){selected.value=t;reportQty.value='';reportNote.value='';reviewNote.value='';reassignTeam.value=t.work_team;error.value='';message.value='';page.value='detail'}
async function action(a){
 if(!selected.value||busy.value)return
 if(a==='report'&&selected.value.tracking_mode==='Quantity'&&(!reportQty.value||!Number.isFinite(Number(reportQty.value))||Number(reportQty.value)<=0)){
  error.value='Nhập số lượng hoàn thành hợp lệ.';return
 }
 if(a==='rework'&&!reviewNote.value.trim()){error.value='Nhập lý do cần làm lại.';return}
 busy.value=true;error.value=''
 try{
  const result=await call('lotus_farm.field_todo.update',{name:selected.value.name,
   action:a,expected_modified:selected.value.modified,
   reported_qty:a==='report'&&selected.value.tracking_mode==='Quantity'?Number(reportQty.value):null,
   note:a==='report'?reportNote.value:reviewNote.value,
   ...(a==='reassign'?{work_team:reassignTeam.value}:{})},true)
  selected.value={...selected.value,...result}
  await refresh()
  message.value=({start:'Đã bắt đầu công việc.',report:'Đã báo xong, chờ nghiệm thu.',
   accept:'Đã nghiệm thu hoàn thành.',rework:'Đã trả lại công việc.',reassign:'Đã đổi tổ phụ trách.'})[a]
  if(a==='accept')page.value='board'
 }catch(e){error.value=e.message||'Không cập nhật được công việc.'}
 finally{busy.value=false}
}
</script>

<template>
 <section class="field-todo">
  <LotusMobileFeedback v-if="error" kind="error">{{error}}</LotusMobileFeedback>
  <LotusMobileFeedback v-if="message" kind="success">{{message}}</LotusMobileFeedback>
  <LotusMobileFeedback v-if="busy" kind="loading">Đang xử lý...</LotusMobileFeedback>

  <template v-if="page==='board'">
   <div class="field-todo-toolbar">
    <strong>Bảng giao việc</strong>
    <LotusMobileButton v-if="canAssign&&catalog.can_assign" type="button" :disabled="busy" @click="newTask">+ Giao việc</LotusMobileButton>
   </div>
   <LotusMobileInput v-model="search" placeholder="Tìm công việc, tổ hoặc lô"/>
   <MobileLinkField v-model="group" :options="groupOptions" :searchable="false" placeholder="Chọn nhóm"/>
   <div class="field-todo-tabs" role="group" aria-label="Lọc tình trạng">
    <LotusMobileButton type="button" :class="{active:state==='open'}" @click="state='open'">Chưa nghiệm thu</LotusMobileButton>
    <LotusMobileButton type="button" :class="{active:state==='accepted'}" @click="state='accepted'">Đã nghiệm thu</LotusMobileButton>
    <LotusMobileButton type="button" :class="{active:state==='all'}" @click="state='all'">Tất cả</LotusMobileButton>
   </div>
   <p class="field-todo-meta">{{filtered.length}} việc · {{groups.length}} nhóm</p>
   <LotusMobileButton v-for="task in filtered" :key="task.name" type="button" class="field-todo-row" @click="detail(task)">
    <span class="field-todo-line"><strong>{{task.work_name}}</strong><small>{{statusText(task.status)}}</small></span>
    <span class="field-todo-secondary">{{task.group_name}} · {{task.section}}</span>
    <span class="field-todo-secondary">Lô {{task.block_code}} · {{task.team_name}}</span>
    <span class="field-todo-secondary">{{task.start_date}} → {{task.due_date}} · {{task.tracking_mode==='Quantity'?'Theo số lượng':'Báo hoàn thành'}}</span>
   </LotusMobileButton>
   <p v-if="!filtered.length&&!busy" class="mobile-empty">Chưa có việc phù hợp.</p>
  </template>

  <template v-else-if="page==='create'&&form">
   <div class="field-todo-toolbar"><strong>Giao việc mới</strong><LotusMobileButton type="button" @click="page='board'">Đóng</LotusMobileButton></div>
   <form class="field-todo-form" @submit.prevent="create">
    <MobileLinkField label="Nhóm công việc" v-model="form.group_code" :options="stages" :searchable="false" @update:modelValue="form.section_code='';form.work_type=''"/>
    <MobileLinkField label="Hạng mục" v-model="form.section_code" :options="sections" searchable placeholder="Chọn hạng mục" @update:modelValue="form.work_type=''"/>
    <MobileLinkField label="Công việc" v-model="form.work_type" :options="works" searchable placeholder="Gõ tìm công việc" required/>
    <MobileLinkField label="Lô lớn" v-model="form.farm_block" :options="blocks" searchable placeholder="Chọn lô" required/>
    <MobileLinkField label="Tổ phụ trách" v-model="form.work_team" :options="teams" searchable placeholder="Chọn tổ" required/>
    <LotusMobileInput v-model="form.start_date" type="date" label="Ngày bắt đầu" required/>
    <LotusMobileInput v-model="form.due_date" type="date" label="Hạn hoàn thành" required/>
    <div class="mobile-field"><label>Cách báo cáo</label>
     <div class="field-todo-tabs">
      <LotusMobileButton type="button" :class="{active:form.tracking_mode==='Completion'}" @click="form.tracking_mode='Completion'">Báo hoàn thành</LotusMobileButton>
      <LotusMobileButton type="button" :class="{active:form.tracking_mode==='Quantity'}" @click="form.tracking_mode='Quantity'">Theo số lượng</LotusMobileButton>
     </div>
    </div>
    <template v-if="form.tracking_mode==='Quantity'">
     <LotusMobileInput v-model="form.quantity_unit" label="Đơn vị" placeholder="Buồng, cây, bắp..." required/>
     <LotusMobileInput v-model="form.target_qty" type="number" min="0" step="any" label="Số lượng dự kiến (không bắt buộc)"/>
    </template>
    <LotusMobileInput v-model="form.description" type="textarea" label="Phạm vi và yêu cầu hoàn thành" placeholder="Nêu rõ cần làm xong đến đâu" rows="3"/>
    <LotusMobileButton type="submit" class="mobile-submit" :disabled="busy">Giao việc</LotusMobileButton>
   </form>
  </template>

  <template v-else-if="page==='detail'&&selected">
   <div class="field-todo-toolbar"><strong>{{selected.work_name}}</strong><LotusMobileButton @click="page='board'">Quay lại</LotusMobileButton></div>
   <div class="mobile-list-card field-todo-detail">
    <p><b>{{statusText(selected.status)}}</b> · {{selected.group_name}} / {{selected.section}}</p>
    <p>Lô <b>{{selected.block_code}}</b> · {{selected.team_name}}</p>
    <p>Bắt đầu <b>{{selected.start_date}}</b> · Hạn <b>{{selected.due_date}}</b></p>
    <p v-if="selected.description">{{selected.description}}</p>
    <p v-if="selected.tracking_mode==='Quantity'">Theo số lượng: {{!selected.target_qty?'Chưa giao mức':fmt(selected.target_qty)}} {{selected.quantity_unit}}</p>
    <p v-else>Báo xong toàn bộ phạm vi đã giao, không cần nhập khối lượng.</p>
    <p v-if="selected.reported_by">Đã báo xong: {{selected.reported_by}} <span v-if="selected.tracking_mode==='Quantity'">· {{fmt(selected.reported_qty)}} {{selected.quantity_unit}}</span></p>
    <p v-if="selected.report_note">Ghi chú: {{selected.report_note}}</p>
    <p v-if="selected.review_note">Ý kiến nghiệm thu: {{selected.review_note}}</p>
   </div>
   <div v-if="canAssign&&['Open','Doing','Rework'].includes(selected.status)&&teams.length>1" class="field-todo-form">
    <MobileLinkField label="Điều chuyển sang tổ khác" v-model="reassignTeam" :options="teams" searchable placeholder="Chọn tổ"/>
    <LotusMobileButton :disabled="busy||!reassignTeam||reassignTeam===selected.work_team" @click="action('reassign')">Đổi tổ phụ trách</LotusMobileButton>
   </div>
   <LotusMobileButton v-if="canAssign&&['Open','Rework'].includes(selected.status)" class="mobile-add" :disabled="busy" @click="action('start')">Bắt đầu làm</LotusMobileButton>
   <div v-if="canCapture&&['Open','Doing','Rework'].includes(selected.status)" class="field-todo-form">
    <LotusMobileInput v-if="selected.tracking_mode==='Quantity'" v-model="reportQty" type="number" min="0" step="any" :label="'Số lượng hoàn thành ('+selected.quantity_unit+')'" required/>
    <LotusMobileInput v-model="reportNote" type="textarea" label="Ghi chú khi báo xong" rows="2"/>
    <LotusMobileButton class="mobile-submit" :disabled="busy" @click="action('report')">Báo hoàn thành</LotusMobileButton>
   </div>
   <div v-if="canReview&&selected.status==='Reported'" class="field-todo-form">
    <LotusMobileInput v-model="reviewNote" type="textarea" label="Ý kiến nghiệm thu / lý do làm lại" rows="2"/>
    <div class="field-todo-tabs">
     <LotusMobileButton :disabled="busy" @click="action('accept')">Nghiệm thu đạt</LotusMobileButton>
     <LotusMobileButton :disabled="busy" @click="action('rework')">Yêu cầu làm lại</LotusMobileButton>
    </div>
   </div>
  </template>
 </section>
</template>
