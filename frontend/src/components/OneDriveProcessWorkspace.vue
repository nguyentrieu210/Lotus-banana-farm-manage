<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {call,upload} from '../api'
import DataTable from './DataTable.vue'
import WorkspaceTabs from './WorkspaceTabs.vue'
import WorkspaceModal from './WorkspaceModal.vue'
import SearchSelect from './SearchSelect.vue'
import {Button as UiButton} from './ui/button'
import {Input as UiInput} from './ui/input'
import {FormField} from './ui/form-field'
import {DatePicker} from './ui/date-picker'
import {Pagination} from './ui/pagination'

const props=defineProps({payload:{type:Object,default:()=>({})},farm:{type:String,default:''},zone:{type:String,default:''},block:{type:String,default:''},cycle:{type:String,default:''},company:{type:String,default:''},fromDate:String,loading:Boolean,forecastOnly:Boolean})
const emit=defineEmits(['reload','edit','navigate'])
const tab=ref(props.forecastOnly?'forecast':'workflow'),search=ref(''),busy=ref(false),error=ref(''),notice=ref(''),preview=ref(null),fileUrl=ref(''),configOpen=ref(false),detail=ref(null),forecast=ref(null),scenario=ref(false)
const preset=ref(''),condition=ref(''),effective=ref(''),until=ref(''),colorFrom=ref(''),colorTo=ref(''),adoption=ref('')
const reference=ref(''),referenceSearch=ref(''),referenceRows=ref(null),referenceStart=ref(0)
const referenceLabels={tsSXKD:'Hệ số gốc',tsSXKD6:'Hệ số đánh giá vườn',tsRaHoa:'Phân bổ cắt bắp / thu hoạch',tsKHTH_R:'Thông số riêng theo thửa nguồn',tsKHTH_C:'Thông số chung theo tuổi cây',tsPC_C:'Phẩm cấp theo tháng',tsPC_R:'Phẩm cấp riêng',dmKHTH_C:'Tuổi và số vụ',ts_NMSoi:'Định mức phụ phẩm sợi'}
const referenceOptions=computed(()=>(props.payload.library?.references||[]).map(r=>({value:r.table,label:`${referenceLabels[r.table]||r.table} · ${fmt(r.row_count,0)} dòng`})))
let forecastRequest=0,uploadRequest=0
const scopeKey=computed(()=>[props.company,props.farm,props.zone,props.block,props.cycle,props.fromDate].join('|'))
const tabs=[{id:'workflow',label:'Quy trình'},{id:'handover',label:'Bàn giao'},{id:'selection',label:'Chọn chồi'},{id:'color',label:'Màu dây'},{id:'forecast',label:'Dự thu OneDrive'},{id:'parameters',label:'Thông số'},{id:'sources',label:'Nguồn'}]
const shownTabs=computed(()=>props.forecastOnly?tabs.filter(r=>['forecast','parameters'].includes(r.id)):tabs)
const fmt=(n,d=2)=>n==null?'—':Number(n).toLocaleString('vi-VN',{maximumFractionDigits:d})
const col=(field,headerName,more={})=>({field,headerName,...more})
const qty=(field,label)=>col(field,label,{valueFormatter:({value})=>fmt(value)})
const farmCol=col('farm','Vườn'),zoneCol=col('farm_zone','Khu')
const workflowCols=[col('title','Công đoạn',{minWidth:250}),col('evidence','Nguồn OneDrive',{minWidth:240}),qty('count','Số hồ sơ')]
const handoverCols=[farmCol,zoneCol,col('source_event_date','Ngày chặt cây cũ'),col('equivalent_selection_date','Mốc chọn chồi tương đương'),qty('source_cut_qty','Cây cũ đã chặt')]
const monthCols=[farmCol,zoneCol,col('month','Kỳ chọn chồi'),qty('cohort_count','Đợt theo ngày'),qty('source_cut_qty','Cây cũ tham chiếu')]
const actualCols=[farmCol,col('farm_block','Lô'),col('selection_date','Ngày chọn thực tế'),qty('selected_sucker_qty','Chồi đã kiểm đếm')]
const colorCols=[farmCol,col('color_code','Mã màu'),col('color_label','Màu dây',{minWidth:180}),col('injection_from','Chích từ'),col('injection_to','Chích đến'),col('valid_from','Cắt bắp từ'),col('valid_to','Cắt bắp đến'),col('harvest_from','Dự thu từ'),col('harvest_to','Dự thu đến')]
const parameterCols=[col('enterprise','Đơn vị nguồn'),col('source_farm','Vườn nguồn'),col('year_band','Năm vụ'),qty('density','Cây/ha'),col('cut_rate','CB/cây',{valueFormatter:({value})=>fmt(value*100)+'%'}),col('harvest_rate','TH/CB',{valueFormatter:({value})=>fmt(value*100)+'%'}),col('processed_rate','SC/TH',{valueFormatter:({value})=>fmt(value*100)+'%'}),qty('gross_bunch_kg','Kg nguyên buồng'),qty('processed_bunch_kg','Kg sơ chế/buồng')]
const adoptionCols=[farmCol,qty('version','Bản'),col('approval_state','Trạng thái',{valueFormatter:({value})=>value==='Approved'?'Đã duyệt':'Nháp'}),col('source_label','Bộ nguồn',{minWidth:260}),col('condition_class','Đánh giá'),col('valid_from','Từ'),col('valid_to','Đến')]
const forecastCols=[farmCol,zoneCol,col('month','Tháng'),qty('cut_bunches','Buồng cắt bắp'),qty('harvest_bunches','Buồng thu'),qty('gross_kg','Kg nguyên buồng'),qty('processed_kg','Kg sơ chế'),...['A456','A789','B456','B789','CL','CP','CNB13','CNB18'].map(g=>qty('grade_'+g+'_kg',g+' (kg)'))]
const filter=rows=>(rows||[]).filter(row=>!search.value||Object.values(row).join(' ').toLocaleLowerCase('vi').includes(search.value.toLocaleLowerCase('vi')))
const totals=computed(()=>{
 const result=new Map()
 for(const r of props.payload.handovers||[]){const key=r.farm+' / '+r.farm_zone;const old=result.get(key)||{scope:key,cohorts:0,qty:0};old.cohorts++;old.qty+=Number(r.source_cut_qty);result.set(key,old)}
 return [...result.values()]
})
const presets=computed(()=>(props.payload.library?.defaults||[]).map(r=>({value:r.key,label:`${r.enterprise} / ${r.source_farm} / năm ${r.year_band} · ${fmt(r.cut_rate*100)}% · ${fmt(r.processed_bunch_kg)} kg`})))
const adopted=computed(()=>(props.payload.adoptions||[]).filter(r=>r.approval_state==='Approved'&&(!props.farm||r.farm===props.farm)))
const adoptionOptions=computed(()=>adopted.value.map(r=>({value:r.name,label:`${r.farm} · bản ${r.version} · ${r.valid_from}`})))
const chosenPreset=computed(()=>(props.payload.library?.defaults||[]).find(r=>r.key===preset.value))
watch(scopeKey,()=>{forecastRequest++;uploadRequest++;preview.value=null;fileUrl.value='';forecast.value=null;error.value='';notice.value='';adoption.value='';detail.value=null;configOpen.value=false})
watch(()=>props.payload,()=>{if(tab.value==='forecast')loadForecast()})
watch(tab,value=>{search.value='';error.value='';if(value==='forecast')loadForecast()})
async function run(fn){busy.value=true;error.value='';notice.value='';try{return await fn()}catch(e){error.value=e.message;return null}finally{busy.value=false}}
async function chooseFile(event){
 const file=event.target.files?.[0];if(!file)return
 preview.value=null;fileUrl.value=''
 if(!props.farm){error.value='Chọn vườn trước khi nhập nhật ký.';return}
 const request=++uploadRequest,requestFarm=props.farm
 await run(async()=>{const stored=await upload(file);if(request!==uploadRequest)return;const result=await call('lotus_farm.onedrive_workspace.preview_handover',{farm:requestFarm,file_url:stored.file_url});if(request!==uploadRequest)return;fileUrl.value=stored.file_url;preview.value=result})
 event.target.value=''
}
async function commitImport(){
 if(!preview.value||preview.value.conflicts?.length)return
 await run(async()=>{const r=await call('lotus_farm.onedrive_workspace.import_handover',{farm:props.farm,file_url:fileUrl.value,source_sha256:preview.value.source_sha256},true);preview.value=null;notice.value=`Đã nhập ${r.created} đợt; ${r.existing} đợt đã có. Tổng ${fmt(r.total_cut_qty,0)} cây cũ đã chặt.`;emit('reload')})
}
function openConfig(row=null){
 if(row){emit('edit','Lotus Process Adoption',row.name);return}
 if(!props.farm){error.value='Chọn vườn cần áp dụng bộ thông số.';return}
 preset.value='';condition.value='';effective.value=props.fromDate||new Date().toLocaleDateString('en-CA');until.value='';configOpen.value=true
}
async function createConfig(approve){
 if(!preset.value||!effective.value){error.value='Chọn bộ thông số nguồn và ngày hiệu lực.';return}
 const result=await run(()=>call('lotus_farm.onedrive_workspace.create_adoption',{farm:props.farm,preset_key:preset.value,condition_class:condition.value,valid_from:effective.value,valid_to:until.value||null,approve:approve?1:0},true))
 if(result){configOpen.value=false;notice.value=approve?'Đã áp dụng phiên bản mới.':'Đã lưu bản nháp.';emit('reload')}
}
async function createTags(){
 if(!adoption.value||!colorFrom.value||!colorTo.value){error.value='Chọn phiên bản và khoảng ngày phát hành màu dây.';return}
 await run(async()=>{const r=await call('lotus_farm.onedrive_workspace.generate_tags',{process_adoption:adoption.value,from_date:colorFrom.value,to_date:colorTo.value},true);notice.value=`Đã tạo ${r.created} đợt màu; ${r.existing} đợt đã có.`;emit('reload')})
}
async function loadForecast(){const request=++forecastRequest;await run(async()=>{const result=await call('lotus_farm.onedrive_workspace.forecast',{company:props.company||null,farm:props.farm||null,zone:props.zone||null,block:props.block||null,cycle:props.cycle||null,from_date:props.fromDate,include_handover:scenario.value?1:0});if(request===forecastRequest)forecast.value=result})}
async function loadReference(start=0){referenceStart.value=start;await run(async()=>{referenceRows.value=await call('lotus_farm.onedrive_workspace.reference_table',{table:reference.value,start,length:100,search:referenceSearch.value||null})})}
onMounted(()=>{if(props.forecastOnly)loadForecast()})
function workflowOpen(row){if(row.can_read)emit('navigate',row.route,{doctype:row.doctype})}
function newSelection(){emit('edit','Sucker Selection Batch',null,{farm:props.farm,farm_block:props.block||'',crop_cycle:props.cycle||'',selection_date:props.fromDate||''})}
function newPlan(){emit('edit','Plan Cohort',null,{farm:props.farm,farm_block:props.block||'',anchor:'Selection',anchor_date:props.fromDate||'',quantity_basis:'Selected Suckers',version:1,approval_state:'Draft'})}
</script>

<template>
 <section class="onedrive-process">
  <WorkspaceTabs v-model="tab" :items="shownTabs" label="Quy trình OneDrive"/>
  <div class="process-toolbar"><UiInput v-model="search" aria-label="Tìm trong quy trình" placeholder="Tìm…"/><UiButton variant="outline" :disabled="busy||loading" @click="emit('reload')">Làm mới</UiButton><UiButton v-if="forecastOnly" variant="outline" @click="emit('navigate','process')">Quy trình & bàn giao</UiButton></div>
  <p v-if="error" role="alert" class="error">{{error}}</p><p v-if="notice" role="status" class="notice">{{notice}}</p>
  <p v-for="warning in payload.warnings||[]" :key="warning" class="notice">{{warning}}</p>
  <DataTable v-if="tab==='workflow'" :rows="filter(payload.workflow)" :columns="workflowCols" :loading="loading" interactive @open="workflowOpen"/>
  <template v-else-if="tab==='handover'">
   <div class="process-toolbar"><FormField v-if="payload.can_import" label="Nhật ký chặt cây cũ (.xlsx)" v-slot="field"><UiInput v-bind="field" type="file" accept=".xlsx" :disabled="!farm||busy" @change="chooseFile"/></FormField><UiButton v-if="preview" :disabled="busy||!!preview.conflicts?.length" @click="commitImport">Nhập {{preview.new_count}} đợt đã đối soát</UiButton></div>
   <div v-if="preview" role="status"><p>{{preview.rows.length}} đợt · {{fmt(preview.total_cut_qty,0)}} cây cũ đã chặt · {{preview.existing_count}} đợt đã có</p><p v-for="w in preview.warnings" :key="w" class="notice">{{w}}</p><p v-if="preview.conflicts?.length" class="error">Có {{preview.conflicts.length}} đợt khác số lượng đã lưu. Kiểm tra bản nguồn trước khi nhập.</p></div>
   <DataTable :rows="totals" :columns="[col('scope','Vườn / khu'),qty('cohorts','Đợt'),qty('qty','Cây cũ đã chặt')]"/>
   <DataTable :rows="filter(payload.handovers)" :columns="handoverCols" :loading="loading" interactive @open="detail=$event"/>
  </template>
  <template v-else-if="tab==='selection'">
   <div class="process-toolbar"><UiButton :disabled="!farm" @click="newSelection">Ghi chọn chồi thực tế</UiButton><UiButton variant="outline" :disabled="!farm" @click="newPlan">Lập đợt kế hoạch theo lô</UiButton></div>
   <p class="notice">Mốc bàn giao giữ theo khu. Kỳ chọn chồi tiếp theo = ngày mốc gốc + 6 × n tháng. Số cây cũ tham chiếu chưa phải số chồi đã chọn.</p>
   <DataTable :rows="filter(payload.selection_months)" :columns="monthCols" :loading="loading"/>
   <DataTable :rows="filter(payload.observed_selections)" :columns="actualCols" interactive @open="emit('edit','Sucker Selection Batch',$event.name)"/>
  </template>
  <template v-else-if="tab==='color'">
   <div v-if="payload.can_configure" class="process-toolbar"><SearchSelect v-model="adoption" :options="adoptionOptions" label="Phiên bản chương trình"/><DatePicker v-model="colorFrom" label="Tạo lịch từ"/><DatePicker v-model="colorTo" label="Tạo lịch đến"/><UiButton :disabled="busy||!adoption" @click="createTags">Phát hành màu dây</UiButton></div>
   <p v-if="!adopted.length" class="notice">Chưa có phiên bản áp dụng được duyệt. Chọn bộ nguồn trong Thông số để tạo lịch màu.</p>
   <DataTable :rows="filter(payload.colors)" :columns="colorCols" :loading="loading"/>
  </template>
  <template v-else-if="tab==='parameters'">
   <div class="process-toolbar"><UiButton v-if="payload.can_configure" :disabled="!farm" @click="openConfig()">Thêm phiên bản áp dụng</UiButton><UiButton variant="outline" @click="emit('navigate','plan-norm')">Định mức vật tư & nhân công</UiButton></div>
   <DataTable :rows="filter(payload.adoptions)" :columns="adoptionCols" interactive @open="openConfig"/>
   <DataTable :rows="filter(payload.library?.defaults)" :columns="parameterCols"/>
   <div class="process-toolbar"><SearchSelect v-model="reference" :options="referenceOptions" label="Bảng thông số chi tiết" @change="loadReference()"/><UiInput v-model="referenceSearch" aria-label="Tìm thông số nguồn" placeholder="Tìm mã thửa, vườn, năm…" @keyup.enter="loadReference()"/><UiButton variant="outline" :disabled="!reference||busy" @click="loadReference()">Đọc thông số chi tiết</UiButton></div>
   <template v-if="referenceRows"><p class="notice">{{fmt(referenceRows.total,0)}} dòng tham chiếu nguồn · dữ liệu của đơn vị nguồn được giữ riêng.</p><DataTable :rows="referenceRows.rows" :columns="referenceRows.columns.map(field=>col(field,field==='_source_row'?'Dòng nguồn':field))"/><Pagination :start="referenceStart" :count="referenceRows.rows.length" :has-more="referenceRows.has_more" :page-size="100" @update:start="loadReference"/></template>
  </template>
  <template v-else-if="tab==='forecast'">
   <div class="process-toolbar"><UiButton :disabled="busy" @click="loadForecast">Tính 36 tháng</UiButton><label class="process-check"><input v-model="scenario" type="checkbox" @change="loadForecast"/> Mô phỏng riêng từ cây cũ bàn giao</label></div>
   <p v-if="!adopted.length" class="notice">Chưa có bộ hệ số đã duyệt cho phạm vi này. Áp dụng phiên bản tại Thông số trước khi tính.</p>
   <p v-for="issue in forecast?.issues||[]" :key="issue.farm+issue.message" class="notice">{{issue.farm}}: {{issue.message}}</p>
   <DataTable :rows="filter(forecast?.rows)" :columns="forecastCols" :loading="busy" empty="Chưa có đợt chọn chồi thực tế đủ dữ liệu để dự phóng"/>
   <template v-if="scenario"><p class="notice">{{forecast?.handover_assumption}}</p><DataTable :rows="filter(forecast?.handover_scenario)" :columns="forecastCols" :loading="busy" empty="Chưa có mô phỏng bàn giao đủ dữ liệu"/></template>
  </template>
  <template v-else-if="tab==='sources'">
   <DataTable :rows="payload.library?.sources||[]" :columns="[col('title','File nguồn',{minWidth:280}),col('modified_at','Ngày phiên bản'),col('sha256','SHA-256',{minWidth:250})]"/>
   <p class="notice">Chọn chồi: {{payload.selection_source?.file}} · {{payload.selection_source?.sheet}}!{{payload.selection_source?.range}} · EDATE(K6,6×n).</p>
   <ul><li v-for="item in payload.library?.limitations||[]" :key="item">{{item}}</li></ul>
  </template>
  <WorkspaceModal v-model="configOpen" title="Áp dụng bộ thông số OneDrive">
   <div class="process-form"><FormField label="Bộ hệ số nguồn" required><SearchSelect v-model="preset" :options="presets" label="Bộ hệ số nguồn"/></FormField><FormField label="Đánh giá vườn (để trống: dùng bộ gốc)"><SearchSelect v-model="condition" :options="[{value:'',label:'Theo bộ gốc'},...['Tốt','Trung bình','Xấu'].map(value=>({value,label:value}))]" label="Đánh giá vườn"/></FormField><FormField label="Hiệu lực từ" required><DatePicker v-model="effective" label="Hiệu lực từ"/></FormField><FormField label="Hiệu lực đến"><DatePicker v-model="until" label="Hiệu lực đến"/></FormField></div>
   <p v-if="chosenPreset">{{chosenPreset.source_farm}} · năm {{chosenPreset.year_band}} · {{fmt(chosenPreset.cut_rate*100)}}% cắt bắp · {{fmt(chosenPreset.gross_bunch_kg)}} kg nguyên buồng · {{fmt(chosenPreset.processed_bunch_kg)}} kg sơ chế</p>
   <p v-if="error" class="error" role="alert">{{error}}</p><div class="process-toolbar"><UiButton variant="outline" :disabled="busy" @click="createConfig(false)">Lưu nháp</UiButton><UiButton :disabled="busy||!preset" @click="createConfig(true)">Áp dụng bản mới</UiButton></div>
  </WorkspaceModal>
  <WorkspaceModal :model-value="!!detail" title="Chứng cứ đợt bàn giao" @update:model-value="!$event&&(detail=null)"><template v-if="detail"><p>{{detail.farm}} · khu {{detail.farm_zone}} · {{detail.source_event_date}} · {{fmt(detail.source_cut_qty,0)}} cây cũ đã chặt</p><p>Mốc chọn chồi tương đương: {{detail.equivalent_selection_date}}</p><a :href="detail.source_attachment" target="_blank" rel="noopener">Mở nhật ký gốc</a><DataTable :rows="JSON.parse(detail.source_cells||'[]')" :columns="[col('sheet','Sheet'),col('date_cell','Ô ngày'),col('quantity_cell','Ô số lượng')]"/></template></WorkspaceModal>
 </section>
</template>

<style scoped>
.onedrive-process{display:grid;gap:var(--lotus-space-3)}
.process-toolbar{display:flex;align-items:center;gap:var(--lotus-space-2);overflow-x:auto;flex-wrap:nowrap;padding:var(--lotus-space-1) 0}
.process-toolbar>*{flex:0 0 auto}.process-toolbar>input{max-width:18rem}.process-toolbar>.search-select{min-width:16rem}
.process-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--lotus-space-3)}
.process-check{display:flex;align-items:center;gap:var(--lotus-space-2);white-space:nowrap}
@media(max-width:640px){.process-form{grid-template-columns:1fr}}
</style>
