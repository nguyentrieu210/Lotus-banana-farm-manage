<script setup>
import LotusField from './components/form/LotusField.vue'
import {FormField} from './components/ui/form-field'
// /lotus/forecast — Dự thu theo nhật ký chặt mẹ lần 2: tiles, tonnes by harvest month, stage table
// (trổ buồng → chích bắp → cắt bắp → thu hoạch → đóng gói), zones, the journal with each wave's dates,
// the parameter versions and the Excel upload. Data: lotus_farm.cut_forecast. The previous forecast page
// (OneDrive, 36 tháng, VIP126) stays at /forecast-onedrive.
import {computed,onMounted,ref,watch} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import LotusIcon from './components/LotusIcon.vue'
import LotusChart from './components/LotusChart.vue'
import DataTable from './components/DataTable.vue'
import WorkspaceModal from './components/WorkspaceModal.vue'
import WorkspaceConfirm from './components/WorkspaceConfirm.vue'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import UiSelect from './components/ui/select/Select.vue'
import {useWorkspaceConfirm} from './use-workspace-confirm'
import {useNoticeToast} from './use-toast'
import {call} from './api'
import {useSession} from './store'
import './land.css'
import './cut-forecast.css'

defineProps({embedded:Boolean,navigationKey:String})
const TABS=[['overview','Tổng quan'],['journal','Nhật ký & lịch từng đợt'],['params','Thông số & lần nhập'],['care','Lịch chăm sóc theo lô']]
const route=useRoute(),router=useRouter(),session=useSession()
const {open:confirmOpen,title:confirmTitle,message:confirmMessage,ask,finish:finishConfirm}=useWorkspaceConfirm()
const data=ref(null),busy=ref(false),error=ref(''),notice=ref(''),tab=ref('overview')
const importOpen=ref(false),preview=ref(null),saving=ref(false),applyParams=ref(true),fileName=ref('')
const form=ref({}),formNote=ref(''),journalWave=ref(''),journalLimit=ref(200)
const scopeOpen=ref(false),scopeEntry=ref(null),scopeForm=ref({farm_block:'',crop_cycle:'',plan_cohort:''})
const careBlock=ref(''),careFrom=ref(new Date().toISOString().slice(0,10))
const careTo=ref(new Date().toISOString().slice(0,10))
const careData=ref(null),careBusy=ref(false),careError=ref('')
const blockOptions=computed(()=>(data.value?.blocks||[]).filter(x=>!zone.value||x.farm_zone===zone.value))
const cropOptions=computed(()=>(data.value?.cycles||[]).filter(x=>x.farm_block===scopeForm.value.farm_block))
const cohortOptions=computed(()=>(data.value?.cohorts||[]).filter(x=>x.farm_block===scopeForm.value.farm_block&&(!scopeForm.value.crop_cycle||!x.crop_cycle||x.crop_cycle===scopeForm.value.crop_cycle)))
const careDates=computed(()=>[...new Set((careData.value?.rows||[]).map(r=>r.date))].sort())
const farm=computed(()=>String(route.query.farm||data.value?.farm||''))
const zone=computed(()=>String(route.query.zone||''))
const num=(v,d=0)=>v==null||v===''?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:d})
const vnDate=v=>v?String(v).slice(8,10)+'/'+String(v).slice(5,7)+'/'+String(v).slice(0,4):'—'
const monthLabel=m=>m?m.slice(5,7)+'/'+m.slice(0,4):'—'
const thisMonth=computed(()=>String(session.today||new Date().toISOString()).slice(0,7))
const t=computed(()=>data.value?.totals)
const params=computed(()=>data.value?.params||[])
const waves=computed(()=>params.value.filter(([f])=>/^wave_\d_share$/.test(f)))
const harvestMonths=computed(()=>{const months=data.value?.months||[];const first=months.findIndex(m=>m.kg>0);return first<0?[]:months.slice(first).filter((m,i,all)=>i<=all.map(x=>x.kg>0).lastIndexOf(true))})
const stageMonths=computed(()=>(data.value?.months||[]).filter(m=>m.shoot||m.budcut||m.harvest))
const zoneMonthCols=computed(()=>harvestMonths.value.map(m=>m.month))
const journal=computed(()=>(data.value?.rows||[]).filter(r=>!journalWave.value||String(r.wave)===journalWave.value))
const waveTotal=computed(()=>waves.value.reduce((s,[f])=>s+Number(form.value[f]||0),0))
const scopeNote=computed(()=>{const x=t.value;if(!x)return '';return 'Khu '+x.zones.join(', ')+' · '+num(x.entries)+' dòng chặt từ '+vnDate(x.first_cut)+' đến '+vnDate(x.last_cut)+' · mỗi cây 1 lứa buồng'})
const pct=v=>v==null?'':Math.round(Number(v)*10000)/100
async function load(){busy.value=true;error.value=''
 try{data.value=await call('lotus_farm.cut_forecast.board',{farm:route.query.farm||undefined,zone:zone.value||undefined});resetForm()}
 catch(e){error.value=e.message}finally{busy.value=false}}
function resetForm(){const p=data.value?.profile;form.value=Object.fromEntries(params.value.map(([f,,,d])=>[f,p?p[f]:d]));formNote.value=''}
function setScope(next){careData.value=null;router.push({path:'/forecast',query:{...route.query,...next}})}
function openScope(row){
 const entry=(data.value?.cut_entries||[]).find(e=>e.name===row.entry)
 if(!entry||!data.value?.can_edit)return
 scopeEntry.value=entry
 scopeForm.value={farm_block:entry.farm_block||'',crop_cycle:entry.crop_cycle||'',plan_cohort:entry.plan_cohort||''}
 scopeOpen.value=true
}
async function saveEntryScope(){
 if(!scopeEntry.value||saving.value)return
 saving.value=true;error.value=''
 try{
  await call('lotus_farm.cut_forecast.assign_entry_scope',{
   farm:farm.value,entry:scopeEntry.value.name,modified:String(scopeEntry.value.modified),
   farm_block:scopeForm.value.farm_block||null,crop_cycle:scopeForm.value.crop_cycle||null,
   plan_cohort:scopeForm.value.plan_cohort||null},true)
  scopeOpen.value=false;careData.value=null;notice.value='Đã liên kết nhật ký với lô. Chưa giao việc.'
  await load()
 }catch(e){error.value=e.message}finally{saving.value=false}
}
async function loadCarePreview(){
 if(!farm.value)return
 careBusy.value=true;careError.value='';careData.value=null
 try{careData.value=await call('lotus_farm.cut_forecast.preview_care_plan',{
  farm:farm.value,from_date:careFrom.value,to_date:careTo.value,farm_block:careBlock.value||null})}
 catch(e){careError.value=e.message}finally{careBusy.value=false}
}
async function createCareDraft(date){
 if(!careBlock.value||careBusy.value)return
 const sure=await ask('Tạo kế hoạch NHÁP ngày '+vnDate(date)+' cho lô '+careBlock.value+' từ lịch dự kiến? Chưa giao việc, chưa cấp vật tư hoặc ghi lương.','Tạo kế hoạch nháp')
 if(!sure)return
 careBusy.value=true;careError.value=''
 try{
  // A single-day fingerprint is required; the broader preview cannot authorize a write.
  const day=await call('lotus_farm.cut_forecast.preview_care_plan',{
   farm:farm.value,from_date:date,to_date:date,farm_block:careBlock.value})
  if(!day.rows?.length||day.rows.some(r=>r.blocking_issue))throw Error('Ngày này còn thiếu mã công việc/năng suất/đơn vị, chưa thể tạo nháp an toàn.')
  const result=await call('lotus_farm.cut_forecast.create_care_plan_draft',{
   farm:farm.value,farm_block:careBlock.value,posting_date:date,fingerprint:day.fingerprint},true)
  notice.value='Đã tạo kế hoạch NHÁP '+result.plan+' ('+result.lines+' công việc); người quản lý cần duyệt riêng.'
  await loadCarePreview()
 }catch(e){careError.value=e.message}finally{careBusy.value=false}
}
function exportExcel(){if(farm.value)location.href='/api/method/lotus_farm.cut_forecast.export_forecast?'+new URLSearchParams({farm:farm.value,...(zone.value?{zone:zone.value}:{})})}
async function readFile(event){const file=event.target.files?.[0];if(!file)return;saving.value=true;preview.value=null;error.value='';fileName.value=file.name
 try{const content=await new Promise((ok,fail)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=fail;r.readAsDataURL(file)})
  preview.value=await call('lotus_farm.cut_forecast.preview_import',{farm:farm.value,content,file_name:file.name},true)
  applyParams.value=preview.value.param_changes.length>0&&!preview.value.param_errors.length}
 catch(e){error.value=e.message}finally{saving.value=false;event.target.value=''}}
async function commitImport(){saving.value=true
 try{const r=await call('lotus_farm.cut_forecast.commit_import',{farm:farm.value,token:preview.value.token,apply_params:applyParams.value?1:0},true)
  notice.value='Đã nhập '+num(r.saved)+' dòng ('+num(r.trees)+' cây).'+(r.profile?' Thông số trong file thành phiên bản '+r.profile+'.':'');importOpen.value=false;preview.value=null;await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
function formValue(field,kind){return kind==='rate'?pct(form.value[field]):form.value[field]}
function setForm(field,kind,value){form.value={...form.value,[field]:value===''?'':kind==='rate'?Number(value)/100:Number(value)}}
const book2Diffs=computed(()=>(data.value?.book2_reference?.comparisons||[]).filter(r=>r.changed))
const book2Cols=[{field:'label',headerName:'Thông số',minWidth:260},{field:'approved',headerName:'Đang duyệt',minWidth:130},{field:'excel',headerName:'Excel mới',minWidth:130}]
const book2ExtraCols=[{field:'code',headerName:'Mã thông số',minWidth:190},{field:'value',headerName:'Giá trị',minWidth:155,valueFormatter:p=>Array.isArray(p.value)?p.value.join(' / '):String(p.value??'')},{field:'unit',headerName:'Đơn vị',minWidth:120},{field:'status',headerName:'Mức tin cậy',minWidth:145},{field:'note',headerName:'Lưu ý khi dùng',minWidth:350}]
function prepareBook2(){
 const patch=data.value?.book2_reference?.profile_patch
 if(!patch||!data.value?.can_edit)return
 form.value={...form.value,...patch}
 tab.value='params'
 notice.value='Đã nạp giá trị Excel vào biểu mẫu CHƯA LƯU. Kiểm tra kỹ thông số giả định và bấm Lưu thành phiên bản mới nếu chấp thuận.'
}
async function saveProfile(){saving.value=true
 try{const r=await call('lotus_farm.cut_forecast.save_profile',{farm:farm.value,values:JSON.stringify(form.value),notes:formNote.value||null},true)
  notice.value='Đã lưu thông số phiên bản '+r.version+'. Dự thu đã tính lại.';await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
async function undo(batch){
 if(!await ask('Xóa '+num(batch.new_rows)+' dòng nhật ký mà lần nhập "'+batch.file_name+'" đã thêm? File gốc vẫn được giữ làm chứng cứ.','Hoàn tác lần nhập'))return
 saving.value=true
 try{const r=await call('lotus_farm.cut_forecast.undo_import',{farm:farm.value,batch:batch.name},true);notice.value='Đã xóa '+num(r.removed)+' dòng nhật ký.';await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}

const col=(field,headerName,fmt)=>({field,headerName,minWidth:120,...(fmt?{valueFormatter:p=>fmt(p.value,p.data)}:{})})
const quantity=(f,l,d=0)=>col(f,l,v=>num(v,d))
const dateCol=(f,l)=>col(f,l,v=>vnDate(String(v||'').slice(0,10)))
const monthCols=[col('month','Tháng',v=>monthLabel(v)+(v<thisMonth.value?' · đã qua':v===thisMonth.value?' · tháng này':'')),quantity('shoot','Trổ buồng (cây)'),quantity('inject','Chích bắp'),quantity('budcut','Cắt bắp'),quantity('harvest','Thu hoạch'),quantity('pack','Đóng gói'),quantity('tonnes','Tấn sơ chế',2)]
const monthTotals=computed(()=>t.value?[{month:'Tổng',shoot:t.value.shoot,inject:t.value.inject,budcut:t.value.budcut,harvest:t.value.harvest,pack:t.value.pack,tonnes:t.value.tonnes}]:[])
const zoneRows=computed(()=>(data.value?.zones||[]).map(z=>({...z,cut_range:vnDate(z.first_cut)+' – '+vnDate(z.last_cut)+' · '+z.entries+' dòng'})))
const zoneCols=[col('zone','Khu',v=>'Khu '+v),col('cut_range','Ngày chặt'),quantity('trees','Cây mẹ chặt 2'),quantity('shoot','Trổ buồng'),quantity('budcut','Cắt bắp'),quantity('harvest','Thu hoạch'),quantity('pack','Đóng gói'),quantity('tonnes','Tấn sơ chế',2)]
const matrixCols=computed(()=>[col('zone','Khu'),...zoneMonthCols.value.map(m=>col(m,monthLabel(m),v=>v?num(v,1):'—'))])
const matrixRows=computed(()=>(data.value?.zones||[]).map(z=>({zone:z.zone,...data.value?.zone_months?.[z.zone]})))
const careMaterialColumns=[
 col('date','Ngày',v=>vnDate(v)),col('farm_block','Lô'),
 col('item','Vật tư'),col('uom','ĐVT'),quantity('quantity','Nhu cầu dự kiến',3)
]
const careColumns=[
 col('date','Ngày',v=>vnDate(v)),col('farm_block','Lô'),col('crop_cycle','Vụ cây'),
 col('work_code','Mã công việc'),col('work_name','Tên công việc'),
 quantity('planned_qty','Khối lượng dự kiến'),col('uom','ĐVT'),
 quantity('required_workdays','Số công dự kiến',2),
 col('note','Mốc tính'),col('blocking_issue','Chưa đủ điều kiện')
]
const journalCols=[col('zone','Khu'),col('farm_block','Lô'),col('crop_cycle','Vụ'),dateCol('cut_date','Ngày chặt mẹ 2'),quantity('tree_qty','Cây mẹ'),col('wave','Đợt',(_,r)=>r.wave+' · '+pct(r.share)+'%'),quantity('shoot_qty','Số cây trổ'),col('shoot_from','Cửa sổ trổ',(_,r)=>vnDate(r.shoot_from)+' – '+vnDate(r.shoot_to)),dateCol('shoot_date','Trổ (đại diện)'),dateCol('inject_date','Chích bắp'),dateCol('budcut_date','Cắt bắp'),quantity('budcut_qty','Buồng cắt'),dateCol('harvest_date','Thu hoạch'),quantity('harvest_qty','Buồng thu'),quantity('pack_qty','Đóng gói'),quantity('kg','Kg sơ chế'),col('source_ref','Dòng nguồn')]
const profileCols=[col('version','Phiên bản',(_,r)=>r.version+(r.name===data.value?.profile?.name?' · đang dùng':'')),col('source','Nguồn',v=>v==='Excel'?'File Excel':'Web'),col('approved_by','Người duyệt'),dateCol('approved_at','Lúc'),col('days_to_first_shoot','Trổ đợt 1',v=>v+' ngày'),col('cut_rate','Cắt bắp',v=>pct(v)+'%'),col('harvest_rate','Thu',v=>pct(v)+'%'),col('pack_rate','Đóng gói',v=>pct(v)+'%'),quantity('kg_per_bunch','Kg/buồng',1),col('notes','Ghi chú')]
const importRows=computed(()=>(data.value?.imports||[]).map(b=>({...b,conflicts:b.conflict_rows+' / '+b.error_rows})))
const importCols=[col('file_name','File'),quantity('new_rows','Dòng mới'),quantity('existing_rows','Đã có'),col('conflicts','Xung đột / lỗi'),quantity('trees','Số cây'),col('imported_by','Người nhập'),dateCol('imported_at','Lúc'),col('undone_at','Trạng thái',v=>v?'Đã hoàn tác':'Đã nhập')]
const changeCols=[col('label','Thông số'),col('old','Đang dùng'),col('new','Trong file')]
const conflictRows=computed(()=>(preview.value?.rows||[]).filter(r=>r.state==='conflict'||r.state==='error').map(r=>({...r,problem:r.state==='conflict'?'Đã nhập '+num(r.old_qty)+' cây, file ghi '+num(r.tree_qty)+' cây — kiểm tra lại':(r.errors||[]).join('; ')})))
const conflictCols=[quantity('line','Dòng'),col('zone','Khu'),dateCol('cut_date','Ngày'),quantity('tree_qty','Số cây'),col('problem','Tình trạng')]

const STATE={new:'Mới',same:'Đã có',conflict:'Khác số cây',error:'Lỗi'}
watch(()=>[route.query.farm,route.query.zone],load)
onMounted(load)
useNoticeToast(notice)
</script>

<template>
<section class="cutfc lotus-ui">
 <header class="cutfc-head">
  <div class="cutfc-title"><h2>Dự thu</h2><span>Theo nhật ký chặt cây mẹ lần 2 · trổ buồng → chích bắp → cắt bắp → thu hoạch</span></div>
  <div v-if="(data?.farms||[]).length>1" class="land-farms" role="tablist" aria-label="Chọn vườn">
   <button v-for="f in data.farms" :key="f.name" type="button" role="tab" :aria-selected="farm===f.name?'true':'false'" :class="{on:farm===f.name}" @click="setScope({farm:f.name,zone:undefined})">{{f.farm_name||f.name}}</button>
  </div>
  <UiSelect v-if="data?.zone_list?.length" :model-value="zone" aria-label="Lọc khu" class="cutfc-narrow" @update:model-value="setScope({zone:$event||undefined})"><option value="">Mọi khu</option><option v-for="z in data.zone_list" :key="z" :value="z">Khu {{z}}</option></UiSelect>
  <span class="land-spacer"></span>
  <UiButton variant="outline" :disabled="!data?.profile" @click="exportExcel"><LotusIcon name="download"/>Xuất Excel</UiButton>
  <UiButton v-if="data?.can_edit" variant="outline" :disabled="!farm" @click="preview=null;importOpen=true"><LotusIcon name="upload"/>Nhập Excel</UiButton>
  <UiButton variant="ghost" @click="router.push({path:'/forecast-onedrive',query:farm?{farm}:{}})">Dự thu OneDrive</UiButton>
 </header>
 <p v-if="error" class="stock-error" role="alert">{{error}}</p>
 <p v-for="issue in data?.issues||[]" :key="issue" class="notice" role="status">{{issue}}</p>

 <nav class="workspace-tabs" aria-label="Dự thu"><button v-for="[id,label] in TABS" :key="id" type="button" :class="{active:tab===id,selected:tab===id}" :aria-current="tab===id?'page':undefined" @click="tab=id">{{label}}</button></nav>

 <template v-if="tab==='overview'">
  <div v-if="t" class="land-stats cutfc-stats">
   <div><span>Cây mẹ chặt lần 2</span><strong>{{num(t.trees)}}</strong><small>{{num(t.entries)}} dòng nhật ký · chồi cơ sở {{num(t.suckers)}}</small></div>
   <div><span>Buồng cắt bắp</span><strong>{{num(t.budcut)}}</strong><small>trổ {{num(t.shoot)}} · chích bắp {{num(t.inject)}}</small></div>
   <div><span>Buồng thu hoạch</span><strong>{{num(t.harvest)}}</strong><small>đóng gói {{num(t.pack)}} buồng</small></div>
   <div><span>Tấn sơ chế</span><strong>{{num(t.tonnes,1)}} tấn</strong><small>thu từ {{vnDate(t.first_harvest)}} đến {{vnDate(t.last_harvest)}}</small></div>
   <div><span>Tháng cao điểm</span><strong>{{monthLabel(t.peak_month)}}</strong><small>{{num(t.peak_tonnes,1)}} tấn sơ chế</small></div>
  </div>
  <p v-if="t" class="land-note">{{scopeNote}}. Thông số phiên bản {{data.profile?.version}}. Số liệu là dự báo theo giả định, không phải sản lượng chốt.</p>

  <div v-if="t" class="cutfc-charts">
   <LotusChart title="Tấn sơ chế theo tháng thu hoạch" :categories="harvestMonths.map(m=>monthLabel(m.month))" :series="[{name:'Tấn sơ chế',data:harvestMonths.map(m=>m.tonnes)}]" unit="tấn" :decimals="1"/>
   <LotusChart kind="line" title="Khối lượng việc theo tháng" :categories="stageMonths.map(m=>monthLabel(m.month))" :series="[{name:'Trổ buồng',data:stageMonths.map(m=>m.shoot)},{name:'Cắt bắp',data:stageMonths.map(m=>m.budcut)},{name:'Thu hoạch',data:stageMonths.map(m=>m.harvest)}]" unit="buồng"/>
  </div>

  <section v-if="t" class="land-card">
   <div class="land-card__head"><h3>Theo tháng</h3><small class="land-note">Mỗi giai đoạn tính vào tháng của ngày diễn ra giai đoạn đó. Đóng gói và tấn tính theo tháng thu.</small></div>
   <div class="land-table cutfc-table"><DataTable :rows="data.months||[]" :columns="monthCols" :pinned-bottom-rows="monthTotals" storage-key="cutfc-months"/></div>
  </section>

  <section v-if="t" class="land-card">
   <h3>Theo khu</h3>
   <div class="land-table cutfc-table"><DataTable row-key="zone" :rows="zoneRows" :columns="zoneCols" storage-key="cutfc-zones" interactive @open="z=>setScope({zone:zone===z.zone?undefined:z.zone})"/></div>
   <h3 class="cutfc-sub">Tấn sơ chế theo khu và tháng thu</h3>
   <div class="land-table cutfc-table"><DataTable row-key="zone" :rows="matrixRows" :columns="matrixCols" storage-key="cutfc-matrix"/></div>
  </section>
 </template>

 <section v-else-if="tab==='journal'" class="land-card">
  <div class="land-filters"><UiSelect v-model="journalWave" aria-label="Lọc đợt trổ" class="cutfc-narrow"><option value="">Mọi đợt trổ</option><option v-for="k in [1,2,3,4]" :key="k" :value="String(k)">Đợt {{k}}</option></UiSelect>
   <span class="land-spacer"></span><span class="land-count">{{num(journal.length)}} dòng (mỗi dòng chặt tách thành 4 đợt trổ)</span></div>
  <div class="land-table cutfc-table cutfc-journal"><DataTable :rows="journal.slice(0,journalLimit).map(r=>({...r,__grid_id:(r.entry||r.source_ref)+'-'+r.wave}))" row-key="__grid_id" :columns="journalCols" storage-key="cutfc-journal" interactive @open="openScope" empty="Chưa có nhật ký."/>
   <p v-if="!journal.length&&!busy" class="land-empty">Chưa có nhật ký chặt mẹ lần 2.</p></div>
  <UiButton v-if="journal.length>journalLimit" variant="outline" @click="journalLimit+=400">Xem thêm ({{num(journal.length-journalLimit)}} dòng)</UiButton>
  <p class="land-note">Bấm một dòng để đối chiếu lô/vụ/đợt cây. Các dòng chỉ có khu không tự phân bổ số cây.</p>
 </section>

 <section v-else-if="tab==='care'" class="land-card">
  <h3>Lịch chăm sóc dự kiến từ 4 đợt trổ</h3>
  <p class="land-note">Chỉ lấy các dòng nhật ký đã gắn lô; ngày và số buồng là dự kiến. Chưa sinh lịch nếu thông số chích → cắt bắp không đúng quy trình Book2 +16 ngày.</p>
  <div class="land-filters">
   <UiSelect v-model="careBlock" aria-label="Lọc lô lớn">
    <option value="">Mọi lô (chỉ xem)</option>
    <option v-for="b in blockOptions" :key="b.name" :value="b.name">{{b.block_code||b.name}} · Khu {{b.farm_zone}}</option>
   </UiSelect>
   <LotusField label="Từ ngày" type="date" v-model="careFrom"/>
   <LotusField label="Đến ngày" type="date" v-model="careTo"/>
   <UiButton variant="outline" :disabled="careBusy||!farm" @click="loadCarePreview">{{careBusy?'Đang tính…':'Xem lịch'}}</UiButton>
  </div>
  <p v-if="careError" class="land-bad" role="alert">{{careError}}</p>
  <template v-if="careData">
   <p class="land-note">{{num(careData.total_count)}} dòng việc · {{num(careData.ready_count)}} dòng đủ điều kiện tạo nháp · {{num(careData.unmapped_count)}} dòng nguồn chưa gắn lô · Bộ hệ số #{{careData.profile_version}}</p>
   <p v-for="w in careData.warnings||[]" :key="w" class="land-note">{{w}}</p>
   <div v-if="careBlock&&data?.can_edit&&careDates.length" class="land-actions">
    <UiButton v-for="d in careDates" :key="d" variant="outline" :disabled="careBusy" @click="createCareDraft(d)">Tạo nháp {{vnDate(d)}}</UiButton>
   </div>
   <div class="land-table cutfc-table"><DataTable :rows="careData.rows||[]" :columns="careColumns" row-key="schedule_key" storage-key="care-plan-book2" empty="Không có lịch trong khoảng đã chọn."/></div>
   <details v-if="careData.materials?.length" class="land-card"><summary>Vật tư dự kiến từ định mức đã duyệt ({{num(careData.materials.length)}} dòng)</summary>
    <p class="land-note">Chỉ tính nhu cầu, KHÔNG tạo yêu cầu mua, không giữ hoặc xuất tồn kho. Việc phun/bọc thiếu định mức đã duyệt không thể tạo kế hoạch nháp.</p>
    <div class="land-table cutfc-table"><DataTable :rows="careData.materials" :columns="careMaterialColumns" storage-key="care-plan-book2-materials"/></div>
   </details>
  </template>
 </section>

 <template v-else>
  <section v-if="data?.book2_reference" class="land-card">
   <div class="land-card__head"><h3>Đối chiếu thông số Excel mới (26/10/2026)</h3>
    <UiButton v-if="data?.can_edit" type="button" variant="outline" :disabled="saving" @click="prepareBook2">Nạp vào biểu mẫu (chưa lưu)</UiButton>
   </div>
   <p class="land-note"><b>Nguồn:</b> {{data.book2_reference.source_file}} · {{data.book2_reference.different_count}} thông số khác bản đang duyệt.</p>
   <p class="land-note">{{data.book2_reference.warning}}</p>
   <details v-if="book2Diffs.length" open><summary>Thông số cần xem lại ({{book2Diffs.length}})</summary>
    <div class="land-table cutfc-table"><DataTable :rows="book2Diffs" :columns="book2Cols" row-key="field" storage-key="book2-forecast-diff"/></div>
   </details>
   <details><summary>Thông số Excel bổ sung chưa tự áp dụng ({{data.book2_reference.extras.length}})</summary>
    <div class="land-table cutfc-table"><DataTable :rows="data.book2_reference.extras" :columns="book2ExtraCols" row-key="code" storage-key="book2-forecast-extra"/></div>
   </details>
  </section>
  <section class="land-card">
   <div class="land-card__head"><h3>Thông số dự thu <small v-if="data?.profile">· đang dùng phiên bản {{data.profile.version}} ({{data.profile.source==='Excel'?'từ file Excel':'sửa trên web'}}, {{vnDate(String(data.profile.approved_at||'').slice(0,10))}})</small></h3></div>
   <p class="land-note">Đợt cuối nhận phần cây còn lại, nên tổng 4 tỷ lệ phải bằng 100%. Lưu là tạo phiên bản mới; các phiên bản cũ được giữ lại để đối chiếu.</p>
   <form class="land-form--grid cutfc-params" @submit.prevent="saveProfile">
    <label v-for="[field,label,kind] in params" :key="field">{{label}}<span class="cutfc-input"><UiInput type="number" :step="kind==='days'?1:kind==='rate'?0.01:0.1" min="0" :disabled="!data?.can_edit||saving" :model-value="formValue(field,kind)" @update:model-value="setForm(field,kind,$event)"/><em>{{kind==='days'?'ngày':kind==='rate'?'%':kind==='kg'?'kg':'chồi'}}</em></span></label>
    <p class="land-form__full" :class="Math.abs(waveTotal-1)>1e-6?'land-bad':'land-note'">Tổng 4 đợt trổ: {{num(waveTotal*100,2)}}%</p>
    <FormField v-if="data?.can_edit" class="land-form__full" label="Ghi chú thay đổi" v-slot="f"><UiInput v-bind="f" v-model="formNote" placeholder="VD: đổi mốc trổ đợt 1 thành 180 ngày theo khảo sát khu A"/></FormField>
    <div v-if="data?.can_edit" class="land-actions land-form__full"><UiButton type="button" variant="outline" :disabled="saving" @click="resetForm">Đặt lại</UiButton><UiButton type="submit" :disabled="saving||Math.abs(waveTotal-1)>1e-6">{{saving?'Đang lưu…':'Lưu thành phiên bản mới'}}</UiButton></div>
   </form>
  </section>
  <section class="land-card">
   <h3>Các phiên bản thông số</h3>
   <div class="land-table cutfc-table"><DataTable :rows="data?.profiles||[]" :columns="profileCols" row-key="name" storage-key="cutfc-profiles"/>
    <p v-if="!(data?.profiles||[]).length" class="land-empty">Chưa có phiên bản nào. Nhập file Excel dự thu hoặc lưu thông số ở trên.</p></div>
  </section>
  <section class="land-card">
   <h3>Các lần nhập file</h3>
   <div class="land-table cutfc-table"><DataTable :rows="importRows" :columns="importCols" row-key="name" storage-key="cutfc-imports"/><div v-for="b in importRows" :key="b.name" class="land-actions"><a v-if="b.source_file" :href="b.source_file" target="_blank" rel="noopener">Mở file {{b.file_name}}</a><UiButton v-if="!b.undone_at&&data?.can_edit&&b.new_rows" variant="ghost" size="sm" :disabled="saving" @click="undo(b)">Hoàn tác {{b.file_name}}</UiButton></div>
    <p v-if="!(data?.imports||[]).length" class="land-empty">Chưa nhập file nào.</p></div>
  </section>
 </template>

 <WorkspaceModal v-model="scopeOpen" title="Gắn nhật ký chặt mẹ với lô lớn" :busy="saving" width="620px">
  <p class="land-note">Dòng {{scopeEntry?.name}} · Khu {{scopeEntry?.zone}} · {{num(scopeEntry?.tree_qty)}} cây. Không tự chia cây theo diện tích.</p>
  <div class="land-form">
   <label>Lô lớn
    <UiSelect v-model="scopeForm.farm_block" :disabled="saving" @update:model-value="scopeForm.crop_cycle='';scopeForm.plan_cohort=''">
     <option value="">Chưa xác định lô</option>
     <option v-for="b in blockOptions.filter(b=>b.farm_zone===scopeEntry?.zone)" :key="b.name" :value="b.name">{{b.block_code||b.name}} · {{b.block_name}}</option>
    </UiSelect>
   </label>
   <label>Vụ cây (nếu có)
    <UiSelect v-model="scopeForm.crop_cycle" :disabled="saving||!scopeForm.farm_block" @update:model-value="scopeForm.plan_cohort=''">
     <option value="">Chưa xác định vụ</option>
     <option v-for="c in cropOptions" :key="c.name" :value="c.name">{{c.name}} · Vụ {{c.cycle_no}}</option>
    </UiSelect>
   </label>
   <label>Đợt cây (nếu có)
    <UiSelect v-model="scopeForm.plan_cohort" :disabled="saving||!scopeForm.farm_block">
     <option value="">Chưa xác định đợt</option>
     <option v-for="c in cohortOptions" :key="c.name" :value="c.name">{{c.cohort_code}} · {{c.cohort_name}}</option>
    </UiSelect>
   </label>
   <div class="land-actions"><UiButton variant="outline" :disabled="saving" @click="scopeOpen=false">Hủy</UiButton>
    <UiButton :disabled="saving" @click="saveEntryScope">Lưu liên kết lô/vụ</UiButton></div>
  </div>
 </WorkspaceModal>
 <WorkspaceModal v-model="importOpen" title="Nhập file dự thu" :busy="saving" width="980px">
  <div class="land-form">
   <ol class="land-steps"><li>Chọn file Excel dự thu có sheet <b>NHẬT KÝ GỐC</b> (Khu | Ngày chặt mẹ lần 2 | Số cây | Dòng trên file nguồn) và sheet <b>THÔNG SỐ</b>.</li><li>Xem trước: dòng mới được thêm, dòng đã nhập trước đây bỏ qua, dòng khác số cây so với lần trước được báo để kiểm tra.</li><li>Bấm Nhập. File gốc được lưu lại làm chứng cứ.</li></ol>
   <LotusField label="File Excel" type="file" accept=".xlsx" :disabled="saving" @change="readFile"/>
   <template v-if="preview">
    <p><b>{{num(preview.new)}}</b> dòng mới ({{num(preview.new_trees)}} cây) · {{num(preview.same)}} dòng đã có · <span :class="{'land-bad':preview.conflict}">{{num(preview.conflict)}} dòng khác số cây</span> · <span :class="{'land-bad':preview.errors}">{{num(preview.errors)}} dòng lỗi</span></p>
    <p v-if="preview.file_totals" class="land-note">Theo thông số trong file: {{num(preview.file_totals.trees)}} cây → {{num(preview.file_totals.pack)}} buồng đóng gói → <b>{{num(preview.file_totals.tonnes,1)}} tấn sơ chế</b>.</p>
    <div v-if="preview.param_errors.length" class="land-bad"><div v-for="e in preview.param_errors" :key="e">Thông số trong file: {{e}}</div></div>
    <template v-else-if="preview.param_changes.length">
     <LotusField v-model="applyParams" type="checkbox" :label="'Dùng thông số trong file làm phiên bản mới'+(preview.has_profile?' (thay phiên bản đang dùng)':'')"/>
     <div class="land-table land-preview"><DataTable :rows="preview.param_changes||[]" :columns="changeCols" row-key="field" storage-key="cutfc-preview-changes"/></div>
    </template>
    <div v-if="preview.rows.some(r=>r.state!=='new'&&r.state!=='same')" class="land-table land-preview"><DataTable :rows="conflictRows" :columns="conflictCols" row-key="line" storage-key="cutfc-preview-conflicts"/></div>
    <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="importOpen=false">Hủy</UiButton><UiButton type="button" :disabled="saving||(!preview.new&&!(applyParams&&preview.param_changes.length))" @click="commitImport">{{saving?'Đang nhập…':'Nhập '+num(preview.new)+' dòng'+(applyParams&&preview.param_changes.length?' và thông số':'')}}</UiButton></div>
   </template>
  </div>
 </WorkspaceModal>
 <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" @answer="finishConfirm"/>
</section>
</template>