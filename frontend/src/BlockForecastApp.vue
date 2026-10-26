<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import {call} from './api'
import {Button as UiButton} from './components/ui/button'
import UiSelect from './components/ui/select/Select.vue'
import DataTable from './components/DataTable.vue'
import LotusField from './components/form/LotusField.vue'
import WorkspaceConfirm from './components/WorkspaceConfirm.vue'
import {useWorkspaceConfirm} from './use-workspace-confirm'
import './land.css'

defineProps({embedded:Boolean,navigationKey:String})
const route=useRoute(),router=useRouter()
const {open:confirmOpen,title:confirmTitle,message:confirmMessage,ask,finish:finishConfirm}=useWorkspaceConfirm()
const data=ref(null),busy=ref(false),error=ref(''),notice=ref('')
const tab=ref('forecast')
const farm=computed(()=>String(route.query.farm||data.value?.farm||''))
const zone=computed(()=>String(route.query.zone||''))
const block=computed(()=>String(route.query.block||''))
const careFrom=ref(new Date().toISOString().slice(0,10))
const careTo=ref(new Date().toISOString().slice(0,10))
const careBlock=ref('')
const careDate=ref('')
const careData=ref(null),careBusy=ref(false),careError=ref('')
const dateFmt=s=>s?String(s).slice(8,10)+'/'+String(s).slice(5,7)+'/'+String(s).slice(0,4):'—'
const fmt=(n,d=0)=>n==null?'—':Number(n).toLocaleString('vi-VN',{maximumFractionDigits:d})
const sum=(k,rows)=>(rows||[]).reduce((n,r)=>n+Number(r[k]||0),0)
const careDays=computed(()=>[...new Set((careData.value?.rows||[]).map(r=>r.date))].sort())
const columns=[
 {field:'farm_block',headerName:'Lô',minWidth:115},
 {field:'zone',headerName:'Khu',minWidth:80},
 {field:'crop_cycle',headerName:'Vụ cây',minWidth:120},
 {field:'cohort',headerName:'Đợt cây',minWidth:120},
 {field:'wave',headerName:'Đợt trổ',minWidth:105},
 {field:'tree_qty',headerName:'Cây dự kiến',minWidth:115,valueFormatter:p=>fmt(p.value)},
 {field:'flower_window_start',headerName:'Bắt đầu trổ',minWidth:135,valueFormatter:p=>dateFmt(p.value)},
 {field:'inject_date',headerName:'Chích bắp',minWidth:135,valueFormatter:p=>dateFmt(p.value)},
 {field:'cut_bud_date',headerName:'Cắt bắp',minWidth:135,valueFormatter:p=>dateFmt(p.value)},
 {field:'harvest_date',headerName:'Dự kiến thu',minWidth:135,valueFormatter:p=>dateFmt(p.value)},
 {field:'bunches_harvest',headerName:'Buồng thu',minWidth:115,valueFormatter:p=>fmt(p.value)},
 {field:'kg_pack',headerName:'Thành phẩm kg',minWidth:125,valueFormatter:p=>fmt(p.value)},
 {field:'source',headerName:'Nguồn',minWidth:205},
]
const monthColumns=[
 {field:'month',headerName:'Tháng thu'},
 {field:'bunches',headerName:'Buồng dự kiến',valueFormatter:p=>fmt(p.value)},
 {field:'packed_kg',headerName:'Thành phẩm (kg)',valueFormatter:p=>fmt(p.value)},
]
const careColumns=[
 {field:'date',headerName:'Ngày',valueFormatter:p=>dateFmt(p.value)},
 {field:'farm_block',headerName:'Lô'},
 {field:'work_code',headerName:'Mã công việc'},
 {field:'work_name',headerName:'Công việc'},
 {field:'planned_qty',headerName:'Khối lượng',valueFormatter:p=>fmt(p.value)},
 {field:'uom',headerName:'ĐVT'},
 {field:'required_workdays',headerName:'Số công',valueFormatter:p=>fmt(p.value,2)},
 {field:'blocking_issue',headerName:'Chưa đủ điều kiện',minWidth:280},
]
const materialColumns=[
 {field:'date',headerName:'Ngày',valueFormatter:p=>dateFmt(p.value)},
 {field:'farm_block',headerName:'Lô'},
 {field:'item',headerName:'Vật tư'},
 {field:'uom',headerName:'ĐVT'},
 {field:'quantity',headerName:'Dự trù',valueFormatter:p=>fmt(p.value,3)},
]
function changeScope(changes){careData.value=null;router.push({path:'/forecast',query:{...route.query,...changes}})}
async function load(){
 busy.value=true;error.value=''
 try{data.value=await call('lotus_farm.block_forecast.board',{farm:route.query.farm||undefined,zone:zone.value||undefined,block:block.value||undefined})}
 catch(e){error.value=e.message}finally{busy.value=false}
}
async function previewCare(){
 if(!farm.value)return
 careBusy.value=true;careError.value='';careData.value=null
 try{
  careData.value=await call('lotus_farm.block_forecast.preview_care_plan',{farm:farm.value,from_date:careFrom.value,to_date:careTo.value,block:careBlock.value||null})
  careDate.value=careDays.value.includes(careDate.value)?careDate.value:(careDays.value[0]||'')
 }catch(e){careError.value=e.message}finally{careBusy.value=false}
}
async function draft(){
 if(!careBlock.value||!careDate.value||careBusy.value)return
 const proceed=await ask('Tạo kế hoạch NHÁP ngày '+dateFmt(careDate.value)+' cho lô đã chọn? Không tự giao việc, xuất kho hay ghi lương.','Xác nhận kế hoạch nháp')
 if(!proceed)return
 careBusy.value=true;careError.value=''
 try{
  const day=await call('lotus_farm.block_forecast.preview_care_plan',{farm:farm.value,from_date:careDate.value,to_date:careDate.value,block:careBlock.value})
  if(!day.rows?.length||day.rows.some(r=>r.blocking_issue))throw Error('Ngày đã chọn còn thiếu mã công việc, năng suất hoặc định mức đã duyệt.')
  const saved=await call('lotus_farm.block_forecast.create_care_plan_draft',{farm:farm.value,block:careBlock.value,posting_date:careDate.value,fingerprint:day.fingerprint},true)
  notice.value='Đã tạo phiếu kế hoạch NHÁP '+saved.plan+' với '+saved.lines+' công việc. Chưa duyệt.'
  await previewCare()
 }catch(e){careError.value=e.message}finally{careBusy.value=false}
}
watch(()=>[route.query.farm,route.query.zone,route.query.block],load)
onMounted(load)
</script>

<template>
 <section class="land lotus-ui">
  <header class="land-head">
   <div><h2>Dự thu theo lô & vụ cây</h2><p class="land-note">Một nguồn số cây kiểm kê của lô và các đợt cây đã duyệt. Dự phóng không phải nguồn hàng đã phát hành.</p></div>
   <div class="land-actions">
    <UiButton variant="outline" @click="router.push({path:'/plan-norm',query:{farm}})">Quản lý đợt cây & định mức</UiButton>
    <UiButton variant="outline" @click="router.push({path:'/forecast-onedrive',query:{farm}})">Phiếu dự thu đã phát hành</UiButton>
   </div>
  </header>
  <p v-if="error" role="alert" class="land-bad">{{error}}</p>
  <p v-if="notice" role="status" class="notice">{{notice}}</p>
  <div class="land-filters">
   <UiSelect :model-value="farm" aria-label="Vườn" @update:model-value="changeScope({farm:$event||undefined,zone:undefined,block:undefined})">
    <option v-for="f in data?.farms||[]" :key="f.name" :value="f.name">{{f.farm_name||f.name}}</option>
   </UiSelect>
   <UiSelect :model-value="zone" aria-label="Khu" @update:model-value="changeScope({zone:$event||undefined,block:undefined})">
    <option value="">Tất cả khu</option><option v-for="z in data?.zone_list||[]" :key="z" :value="z">Khu {{z}}</option>
   </UiSelect>
   <UiSelect :model-value="block" aria-label="Lô" @update:model-value="changeScope({block:$event||undefined})">
    <option value="">Tất cả lô</option><option v-for="b in data?.blocks||[]" :key="b.name" :value="b.name">{{b.block_code||b.block_name||b.name}}</option>
   </UiSelect>
  </div>
  <nav class="workspace-tabs" aria-label="Dự thu và kế hoạch">
   <button :class="{active:tab==='forecast'}" type="button" @click="tab='forecast'">Dự thu 4 đợt</button>
   <button :class="{active:tab==='care'}" type="button" @click="tab='care'">Lịch chăm sóc theo lô</button>
  </nav>
  <template v-if="tab==='forecast'">
   <div class="land-stats">
    <div><span>Đợt trổ dự kiến</span><strong>{{fmt(data?.rows?.length||0)}}</strong></div>
    <div><span>Buồng dự kiến thu</span><strong>{{fmt(sum('bunches_harvest',data?.rows))}}</strong></div>
    <div><span>Kg thành phẩm dự kiến</span><strong>{{fmt(sum('kg_pack',data?.rows))}}</strong></div>
    <div><span>Đầu vào theo lô/vụ</span><strong>{{fmt(data?.source_count||0)}}</strong></div>
   </div>
   <section class="land-card">
    <h3>Thông số dự phóng Book2</h3>
    <p class="land-note">Trổ 4 đợt {{data?.params?.waves?.join(' / ')}}%; từ chọn chồi đến bắt đầu trổ {{data?.params?.sucker_to_flower_months}} tháng lịch; trổ → chích +5 ngày; chích → cắt bắp +16 ngày; cắt bắp → thu +65 ngày. Ngày đại diện mỗi đợt +14 ngày.</p>
   </section>
   <section class="land-card">
    <h3>Tổng hợp theo tháng thu</h3>
    <div class="land-table"><DataTable :rows="data?.months||[]" :columns="monthColumns" row-key="month" storage-key="block-forecast-months"/></div>
   </section>
   <section class="land-card">
    <h3>Dự thu theo từng lô, vụ và đợt trổ</h3>
    <div class="land-table"><DataTable :rows="data?.rows||[]" :columns="columns" row-key="key" storage-key="block-forecast-rows" empty="Chưa có số cây, ngày trổ hoặc đợt cây được duyệt."/></div>
    <p v-for="(w,i) in data?.warnings||[]" :key="i" class="land-note">{{w}}</p>
   </section>
  </template>
  <section v-else class="land-card">
   <h3>Xem lịch chăm sóc theo mốc dự thu</h3>
   <p class="land-note">Ngày việc và khối lượng là dự kiến. Công việc phun/bọc cần định mức được duyệt; chống đổ cần số cây khảo sát thực địa.</p>
   <div class="land-filters">
    <UiSelect v-model="careBlock" aria-label="Lô để lập kế hoạch">
     <option value="">Tất cả lô (chỉ xem)</option>
     <option v-for="b in data?.blocks||[]" :key="b.name" :value="b.name">{{b.block_code||b.name}}</option>
    </UiSelect>
    <LotusField label="Từ ngày" type="date" v-model="careFrom"/>
    <LotusField label="Đến ngày" type="date" v-model="careTo"/>
    <UiButton variant="outline" :disabled="careBusy" @click="previewCare">Xem lịch</UiButton>
   </div>
   <p v-if="careError" class="land-bad" role="alert">{{careError}}</p>
   <template v-if="careData">
    <p class="land-note">{{careData.total_count}} dòng lịch, {{careData.ready_count}} dòng đủ điều kiện lập nháp. Chưa giao việc hoặc xuất kho.</p>
    <div v-if="careBlock&&data?.can_create&&careDays.length" class="land-actions">
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
 </section>
</template>
