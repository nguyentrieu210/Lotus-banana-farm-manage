<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import {call} from './api'
import {Button as UiButton} from './components/ui/button'
import UiSelect from './components/ui/select/Select.vue'
import DataTable from './components/DataTable.vue'
import LotusField from './components/form/LotusField.vue'
import ForecastProfiles from './components/ForecastProfiles.vue'
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
 {field:'qty_basis',headerName:'Nguồn số lượng',minWidth:120,valueFormatter:p=>({'Trees':'Số cây','Selected Suckers':'Chồi đã chọn','Bunches':'Buồng trổ'})[p.value]||p.value},
 {field:'tree_qty',headerName:'Khối lượng cơ sở',minWidth:135,valueFormatter:p=>fmt(p.value)},
 {field:'count_status',headerName:'Cơ sở số cây',minWidth:175,valueFormatter:p=>p.value==='Planning Baseline'?'Số cây gốc đã chốt':p.value==='Census Confirmed'?'Số cây thực địa':p.value==='Cohort Approved'?'Đợt cây đã duyệt':p.value},
 {field:'parameter_status',headerName:'Thông số',minWidth:185,valueFormatter:p=>p.value==='Approved'?'Đã duyệt':'Kịch bản chưa duyệt'},
 {field:'profile',headerName:'Phiên bản thông số',minWidth:150},
 {field:'flower_window_start',headerName:'Bắt đầu trổ',minWidth:135,valueFormatter:p=>dateFmt(p.value)},
 {field:'flower_window_end',headerName:'Kết thúc trổ',minWidth:135,valueFormatter:p=>dateFmt(p.value)},
 {field:'inject_date',headerName:'Chích bắp',minWidth:135,valueFormatter:p=>dateFmt(p.value)},
 {field:'cut_bud_date',headerName:'Cắt bắp',minWidth:135,valueFormatter:p=>dateFmt(p.value)},
 {field:'harvest_date',headerName:'Thu từ',minWidth:135,valueFormatter:p=>dateFmt(p.value)},
 {field:'harvest_window_end',headerName:'Thu đến',minWidth:135,valueFormatter:p=>dateFmt(p.value)},
 {field:'bunches_harvest',headerName:'Buồng thu',minWidth:115,valueFormatter:p=>fmt(p.value)},
 {field:'kg_pack',headerName:'Thành phẩm kg',minWidth:125,valueFormatter:p=>fmt(p.value)},
 {field:'carton_equivalent',headerName:'Thùng tương đương',minWidth:135,valueFormatter:p=>fmt(p.value,2)},
 {field:'container_equivalent',headerName:'Cont 40ft tương đương',minWidth:150,valueFormatter:p=>fmt(p.value,3)},
 {field:'source',headerName:'Nguồn',minWidth:205},
]
const monthColumns=[
 {field:'month',headerName:'Tháng thu'},
 {field:'bunches',headerName:'Buồng dự kiến',valueFormatter:p=>fmt(p.value)},
 {field:'packed_kg',headerName:'Thành phẩm (kg)',valueFormatter:p=>fmt(p.value)},
]
const profileColumns=[
 {field:'name',headerName:'Mã bộ thông số'}, {field:'version',headerName:'Phiên bản'},
 {field:'farm_block',headerName:'Lô (trống: toàn vườn)'},
 {field:'valid_from',headerName:'Hiệu lực từ',valueFormatter:p=>dateFmt(p.value)},
 {field:'valid_to',headerName:'Đến ngày',valueFormatter:p=>dateFmt(p.value)},
 {field:'approved_by',headerName:'Người duyệt'}
]
const actualColumns=[
 {field:'farm_block',headerName:'Lô'},
 {field:'crop_cycle',headerName:'Vụ'},
 {field:'operation_date',headerName:'Ngày thực tế',valueFormatter:p=>dateFmt(p.value)},
 {field:'operation_type',headerName:'Công đoạn'},
 {field:'net_bunch_qty',headerName:'Số buồng thực tế',valueFormatter:p=>fmt(p.value)}
]
const paramNames=[
 ['wave_1_share','Trổ đợt 1','%'],['wave_2_share','Trổ đợt 2','%'],
 ['wave_3_share','Trổ đợt 3','%'],['wave_4_share','Trổ đợt 4','%'],
 ['wave_window_days','Số ngày/cửa sổ','ngày'],['wave_step_days','Cách đợt','ngày'],
 ['sucker_to_flower_months','Chọn chồi → trổ','tháng'],['shoot_to_inject_days','Trổ → chích','ngày'],
 ['inject_to_cut_days','Chích → cắt','ngày'],['cut_to_harvest_days','Cắt → thu','ngày'],
 ['flowering_rate','Tỷ lệ trổ hữu hiệu','%'],['cut_rate_per_tree','Cắt bắp / cây','%'],
 ['cut_rate_per_flowered_bunch','Cắt bắp / buồng đã trổ','%'],
 ['harvest_rate','Thu / cắt','%'],['pack_rate','Đóng gói / thu','%'],
 ['kg_cycle_1','Kg/buồng vụ 1','kg'],['kg_cycle_2','Kg/buồng vụ 2','kg'],
 ['kg_cycle_3','Kg/buồng vụ 3+','kg'],['kg_per_carton','Kg/thùng','kg'],
 ['cartons_per_container','Thùng/cont','thùng'],
 ['census_sucker_yield','Chồi hữu hiệu (chỉ tham chiếu)','%']
]
const paramRows=computed(()=>paramNames.map(([code,name,unit])=>({
 code,name,value:(data.value?.params||{})[code],unit,
 label:unit==='%'?fmt(100*Number((data.value?.params||{})[code]||0),2)+'%':
 fmt((data.value?.params||{})[code],2)+' '+unit
})))
const paramColumns=[{field:'name',headerName:'Thông số',minWidth:210},
 {field:'label',headerName:'Giá trị Book2 mặc định',minWidth:190}]
const careColumns=[
 {field:'date',headerName:'Ngày',valueFormatter:p=>dateFmt(p.value)},
 {field:'farm_block',headerName:'Lô'},
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
 {field:'farm_block',headerName:'Lô'},
 {field:'item',headerName:'Vật tư'},
 {field:'uom',headerName:'ĐVT'},
 {field:'quantity',headerName:'Dự trù',valueFormatter:p=>fmt(p.value,3)},
]
function changeScope(changes){careData.value=null;router.push({path:'/forecast',query:{...route.query,...changes}})}
function invalidateScope(){careData.value=null;careBlock.value='';careDate.value='';load()}
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
  if(!day.rows?.some(r=>!r.blocking_issue))throw Error('Ngày này chưa có công việc đủ điều kiện tạo nháp; hãy kiểm tra phần cảnh báo.')
  const saved=await call('lotus_farm.block_forecast.create_care_plan_draft',{farm:farm.value,block:careBlock.value,posting_date:careDate.value,fingerprint:day.fingerprint},true)
  notice.value='Đã tạo phiếu kế hoạch NHÁP '+saved.plan+' với '+saved.lines+' công việc; '+(saved.skipped_codes?.length||0)+' mã chưa đủ điều kiện được bỏ qua. Chưa duyệt.'
  await previewCare()
 }catch(e){careError.value=e.message}finally{careBusy.value=false}
}
watch(()=>[route.query.farm,route.query.zone,route.query.block],invalidateScope)
onMounted(load)
</script>

<template>
 <section class="land lotus-ui block-forecast">
  <header class="land-head">
   <div class="land-actions">
    <UiButton variant="outline" @click="router.push({path:'/plan-norm',query:{farm}})">Quản lý đợt cây & định mức</UiButton>
    <a href="/app/harvest-forecast" class="btn">Phiếu dự thu (ERPNext)</a>
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
   <button :class="{active:tab==='profiles'}" type="button" @click="tab='profiles'">Bộ thông số</button>
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
    <p class="land-note">Đây là giá trị Book2 tham chiếu. Mỗi lô/vụ chỉ dùng bộ thông số Approved có hiệu lực; chưa duyệt thì vẫn xem mô phỏng nhưng không được lập phiếu công việc.</p>
    <div class="land-table"><DataTable :rows="paramRows" :columns="paramColumns" row-key="code" storage-key="forecast-profile-values"/></div>
    <p class="land-note">Sản lượng mỗi đợt chia ra các ngày trong cửa sổ 30 ngày để tính nhu cầu công việc và tháng thu; không dồn toàn bộ vào ngày đầu.</p>
    <h3>Bộ thông số đã duyệt</h3>
    <div class="land-table"><DataTable :rows="data?.profiles||[]" :columns="profileColumns" row-key="name" storage-key="forecast-approved-profiles" empty="Chưa có bộ thông số dự thu nào được duyệt."/></div>
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
   <section class="land-card">
    <h3>Số trổ, chích và cắt bắp đã ghi nhận thực tế</h3>
    <p class="land-note">Chỉ lấy chứng từ Bunch Operation đã nộp (docstatus=1); trình bày riêng để kiểm tra sai lệch, không cộng lần hai với dự thu. Chưa tự phân bổ thao tác thực tế vào một đợt trổ nếu chưa có mã đợt liên kết chắc chắn.</p>
    <div class="land-table"><DataTable :rows="data?.actuals||[]" :columns="actualColumns" row-key="name" storage-key="forecast-observed-milestones" empty="Chưa có bản ghi trổ/chích/cắt bắp đã duyệt."/></div>
   </section>
  </template>
  <ForecastProfiles v-else-if="tab==='profiles'" :farm="farm" :blocks="data?.blocks||[]" @changed="careData=null;load()"/>
  <section v-else class="land-card">
   <h3>Xem lịch chăm sóc theo mốc dự thu</h3>
   <p class="land-note">Nhu cầu công được rải theo từng ngày trong cửa sổ trổ 30 ngày. Chỉ được tạo phiếu nháp khi bộ hệ số và số cây/đợt đã duyệt; phun/bọc cần định mức, chống đổ cần khảo sát.</p>
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
    <p class="land-note">Tổng {{fmt(careData.estimated_workdays,2)}} công dự tính; dự phòng vắng {{fmt((careData.absence_reserve_reference||0)*100)}}% → {{fmt(careData.staffed_workdays_reference,2)}} công định biên. Giá công nhật Book2 {{fmt(careData.daywork_rate_reference)}} đ/công; chi phí tham chiếu {{fmt(careData.daywork_cost_reference)}} đ. Đây KHÔNG phải lương đã duyệt hoặc chi phí kế toán.</p>
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
<style>
.block-forecast .land-filters{flex-wrap:nowrap;overflow-x:auto}
.block-forecast .land-filters>*{flex:0 0 180px;min-width:0}
.block-forecast .land-filters>button{flex:0 0 auto}
</style>
