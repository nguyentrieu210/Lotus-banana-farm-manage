<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../api'
import {Button as UiButton} from './ui/button'
import UiSelect from './ui/select/Select.vue'
import DataTable from './DataTable.vue'
import LotusField from './form/LotusField.vue'
import WorkspaceConfirm from './WorkspaceConfirm.vue'
import {useWorkspaceConfirm} from '../use-workspace-confirm'
import '../land.css'
// Lịch chăm sóc theo lô: the work the forecast dates call for. It only proposes; a draft plan is created on request and nothing is assigned or issued.
const props=defineProps({farm:{type:String,required:true},blocks:{type:Array,default:()=>[]}})
const notice=ref('')
const {open:confirmOpen,title:confirmTitle,message:confirmMessage,ask,finish:finishConfirm}=useWorkspaceConfirm()
const careFrom=ref(new Date().toISOString().slice(0,10))
const careTo=ref(new Date().toISOString().slice(0,10))
const careBlock=ref('')
const careDate=ref('')
const careData=ref(null),careBusy=ref(false),careError=ref('')
const dateFmt=s=>s?String(s).slice(8,10)+'/'+String(s).slice(5,7)+'/'+String(s).slice(0,4):'—'
const fmt=(n,d=0)=>n==null?'—':Number(n).toLocaleString('vi-VN',{maximumFractionDigits:d})
const careDays=computed(()=>[...new Set((careData.value?.rows||[]).map(r=>r.date))].sort())
const careColumns=[
 {field:'date',headerName:'Ngày',valueFormatter:p=>dateFmt(p.value)},
 {field:'farm_block_label',headerName:'Lô'},
 {field:'work_code',headerName:'Mã công việc'},
 {field:'work_name',headerName:'Công việc'},
 {field:'planned_qty',headerName:'Khối lượng',valueFormatter:p=>fmt(p.value)},
 {field:'uom',headerName:'ĐVT'},
 {field:'required_workdays',headerName:'Số công',valueFormatter:p=>fmt(p.value,2)},
 {field:'staffed_workdays',headerName:'Công định biên có dự phòng',valueFormatter:p=>fmt(p.value,2)},
 {field:'daywork_cost_estimate',headerName:'Công nhật tham chiếu',valueFormatter:p=>fmt(p.value)},
 {field:'blocking_issue',headerName:'Chưa đủ điều kiện',minWidth:280},
]
const materialColumns=[
 {field:'date',headerName:'Ngày',valueFormatter:p=>dateFmt(p.value)},
 {field:'farm_block_label',headerName:'Lô'},
 {field:'item',headerName:'Vật tư'},
 {field:'uom',headerName:'ĐVT'},
 {field:'quantity',headerName:'Dự trù',valueFormatter:p=>fmt(p.value,3)},
]
async function previewCare(){
 if(!props.farm)return
 careBusy.value=true;careError.value='';careData.value=null
 try{
  careData.value=await call('lotus_farm.block_forecast.preview_care_plan',{farm:props.farm,from_date:careFrom.value,to_date:careTo.value,block:careBlock.value||null})
  careDate.value=careDays.value.includes(careDate.value)?careDate.value:(careDays.value[0]||'')
 }catch(e){careError.value=e.message}finally{careBusy.value=false}
}
async function draft(){
 if(!careBlock.value||!careDate.value||careBusy.value)return
 const proceed=await ask('Tạo kế hoạch NHÁP ngày '+dateFmt(careDate.value)+' cho lô đã chọn? Không tự giao việc, xuất kho hay ghi lương.','Xác nhận kế hoạch nháp')
 if(!proceed)return
 careBusy.value=true;careError.value=''
 try{
  const day=await call('lotus_farm.block_forecast.preview_care_plan',{farm:props.farm,from_date:careDate.value,to_date:careDate.value,block:careBlock.value})
  if(!day.rows?.some(r=>!r.blocking_issue))throw Error('Ngày này chưa có công việc đủ điều kiện tạo nháp; hãy kiểm tra phần cảnh báo.')
  const saved=await call('lotus_farm.block_forecast.create_care_plan_draft',{farm:props.farm,block:careBlock.value,posting_date:careDate.value,fingerprint:day.fingerprint},true)
  notice.value='Đã tạo phiếu kế hoạch NHÁP '+saved.plan+' với '+saved.lines+' công việc; '+(saved.skipped_codes?.length||0)+' mã chưa đủ điều kiện được bỏ qua. Chưa duyệt.'
  await previewCare()
 }catch(e){careError.value=e.message}finally{careBusy.value=false}
}
watch(()=>props.farm,()=>{careData.value=null;careBlock.value='';careDate.value=''})
</script>

<template>
 <p v-if="notice" role="status" class="notice">{{notice}}</p>
 <section class="land-card">
   <h3>Xem lịch chăm sóc theo mốc dự thu</h3>
   <p class="land-note">Nhu cầu công được rải theo từng ngày trong cửa sổ trổ 30 ngày. Chỉ được tạo phiếu nháp khi bộ hệ số và số cây/đợt đã duyệt; phun/bọc cần định mức, chống đổ cần khảo sát.</p>
   <div class="land-filters">
    <UiSelect v-model="careBlock" aria-label="Lô để lập kế hoạch">
     <option value="">Tất cả lô (chỉ xem)</option>
     <option v-for="b in blocks" :key="b.name" :value="b.name">{{b.block_name||b.block_code||b.name}}</option>
    </UiSelect>
    <LotusField label="Từ ngày" type="date" v-model="careFrom"/>
    <LotusField label="Đến ngày" type="date" v-model="careTo"/>
    <UiButton variant="outline" :disabled="careBusy" @click="previewCare">Xem lịch</UiButton>
   </div>
   <p v-if="careError" class="land-bad" role="alert">{{careError}}</p>
   <template v-if="careData">
    <p class="land-note">{{careData.total_count}} dòng lịch, {{careData.ready_count}} dòng đủ điều kiện lập nháp. Chưa giao việc hoặc xuất kho.</p>
    <p class="land-note">Tổng {{fmt(careData.estimated_workdays,2)}} công dự tính; dự phòng vắng {{fmt((careData.absence_reserve_reference||0)*100)}}% → {{fmt(careData.staffed_workdays_reference,2)}} công định biên. Giá công nhật Book2 {{fmt(careData.daywork_rate_reference)}} đ/công; chi phí tham chiếu {{fmt(careData.daywork_cost_reference)}} đ. Đây KHÔNG phải lương đã duyệt hoặc chi phí kế toán.</p>
    <div v-if="careBlock&&careData.can_create&&careDays.length" class="land-actions">
     <UiSelect v-model="careDate" aria-label="Ngày lập kế hoạch nháp" :disabled="careBusy">
      <option v-for="d in careDays" :key="d" :value="d">{{dateFmt(d)}}</option>
     </UiSelect>
     <UiButton variant="outline" :disabled="careBusy||!careDate" @click="draft">Tạo kế hoạch nháp</UiButton>
    </div>
    <div class="land-table"><DataTable :rows="careData.rows||[]" :columns="careColumns" row-key="schedule_key" storage-key="block-forecast-care"/></div>
    <details v-if="careData.materials?.length"><summary>Vật tư dự kiến theo định mức đã duyệt</summary>
     <div class="land-table"><DataTable :rows="careData.materials" :columns="materialColumns" storage-key="block-forecast-materials"/></div>
    </details>
    <p v-for="(w,i) in careData.warnings||[]" :key="i" class="land-note">{{w}}</p>
   </template>
  </section>
 <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" @answer="finishConfirm"/>
</template>
