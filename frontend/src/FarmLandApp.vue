<script setup>
import LotusField from './components/form/LotusField.vue'
import {FormField} from './components/ui/form-field'
// /lotus/farms — Vườn & lô: every lot of the permitted farms with area, plots, trees, density and data gaps,
// the zones of a farm, a map coloured by zone / variety / density / flowering month, the Excel round-trip,
// and one lot's page (?block=). Data: lotus_farm.farm_land; map: lotus_farm.field.map_block_data.
import {computed,defineAsyncComponent,onMounted,ref,watch} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import LotusIcon from './components/LotusIcon.vue'
import WorkspaceModal from './components/WorkspaceModal.vue'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import UiSelect from './components/ui/select/Select.vue'
import LandBlockDetail from './components/land/LandBlockDetail.vue'
import DataTable from './components/DataTable.vue'
import ColumnVisibilityMenu from './components/ColumnVisibilityMenu.vue'
import {loadColumnLayout,saveColumnLayout,normalizeColumnLayout,changeColumnVisibility,displayedColumns,moveColumn,pinColumn,columnId} from './grid-visibility'
import {buildXlsx,exportExcelFile} from './excel-export'
import {COLOR_MODES} from './map-land'
import {useNoticeToast} from './use-toast'
import {call} from './api'
import {useSession} from './store'
import './land.css'

defineProps({embedded:Boolean,navigationKey:String})
const PlotMap=defineAsyncComponent(()=>import('./components/CareMap.vue'))
const route=useRoute(),router=useRouter(),session=useSession()
const data=ref(null),busy=ref(false),error=ref(''),notice=ref(''),view=ref('list'),mapData=ref(null),colorBy=ref('zone')
const search=ref(''),zone=ref(''),variety=ref(''),gap=ref(''),sort=ref(['block_code',1]),picked=ref(new Set()),gridVisible=ref(null)
const bulkOpen=ref(false),bulk=ref({farm_zone:'',variety:''}),importOpen=ref(false),preview=ref(null),saving=ref(false)
const farm=computed(()=>String(route.query.farm||''))
const block=computed(()=>String(route.query.block||''))
const num=(v,d=0)=>v==null||v===''?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:d})
const vnDate=v=>v?String(v).slice(8,10)+'/'+String(v).slice(5,7)+'/'+String(v).slice(0,4):''
const columns=[['block_code','Lô'],['farm_zone','Khu'],['area_ha','Diện tích (ha)'],['plots','Thửa'],['variety_label','Giống'],['lotus_tree_count','Số cây'],['density','Cây/ha'],['planting','Ngày trồng'],['lotus_estimated_flowering_date','Trổ dự kiến'],['lotus_estimated_sucker_selection_date','Chọn chồi vụ sau']]
const zones=computed(()=>[...new Set((data.value?.blocks||[]).map(b=>b.farm_zone).filter(Boolean))].sort())
const rows=computed(()=>{
 const needle=search.value.trim().toLowerCase(),[key,dir]=sort.value
 return (data.value?.blocks||[]).filter(b=>(!zone.value||b.farm_zone===zone.value)&&(!variety.value||(variety.value==='-'?!b.variety:b.variety===variety.value))
  &&(!gap.value||b.gaps.includes(gap.value))&&(!needle||[b.block_code,b.block_name,b.farm_zone,b.variety_label].join(' ').toLowerCase().includes(needle)))
  .slice().sort((a,b)=>{const x=key==='planting'?(a.planting_date):a[key],y=key==='planting'?(b.planting_date):b[key]
   if(x==null||x==='')return 1;if(y==null||y==='')return -1;return (typeof x==='number'?x-y:String(x).localeCompare(String(y),'vi',{numeric:true}))*dir})
})
const shownTotals=computed(()=>({area:rows.value.reduce((s,b)=>s+Number(b.area_ha||0),0),trees:rows.value.reduce((s,b)=>s+Number(b.lotus_tree_count||0),0)}))
const s=computed(()=>data.value?.summary)
const visibleLandRows=computed(()=>gridVisible.value??rows.value)
const allPicked=computed(()=>visibleLandRows.value.length>0&&visibleLandRows.value.every(b=>picked.value.has(b.name)))
async function load(){busy.value=true;error.value=''
 try{data.value=await call('lotus_farm.farm_land.overview',{farm:farm.value||undefined});picked.value=new Set();if(view.value==='map')await loadMap()}
 catch(e){error.value=e.message}finally{busy.value=false}}
async function loadMap(){if(!farm.value){mapData.value=null;return}
 try{mapData.value=await call('lotus_farm.field.map_block_data',{farm:farm.value,include_draft:1})}catch(e){error.value=e.message}}
function setFarm(value){router.push({path:'/farms',query:value?{farm:value}:{}})}
function openBlock(name){const b=(data.value?.blocks||[]).find(x=>x.name===name);router.push({path:'/farms',query:{farm:b?.farm||farm.value||undefined,block:name}})}
function sortBy(key){sort.value=[key,sort.value[0]===key?-sort.value[1]:1]}
function togglePick(name){const next=new Set(picked.value);next.has(name)?next.delete(name):next.add(name);picked.value=next}
function togglePickAll(){const next=new Set(picked.value);for(const b of visibleLandRows.value)allPicked.value?next.delete(b.name):next.add(b.name);picked.value=next}

// The grid works on stable Farm Block IDs; a sort or Excel-column filter never changes the target of an edit.
const gridRows=computed(()=>rows.value.map(b=>({...b,
 __picked:picked.value.has(b.name),
 planting:b.planting_date||'',
 gaps_label:(b.gaps||[]).map(g=>data.value?.gap_labels?.[g]?.replace('Chưa có ','')||g).join(', ')
})))
function renderLandPick(params){
 const input=document.createElement('input')
 input.type='checkbox'
 input.checked=!!params.data?.__picked
 input.setAttribute('aria-label','Chọn lô '+(params.data?.block_code||''))
 input.addEventListener('click',e=>e.stopPropagation())
 input.addEventListener('change',e=>{e.stopPropagation();togglePick(params.data.name)})
 return input
}
const gridColumns=computed(()=>[
 ...(data.value?.can_edit?[{field:'__picked',headerName:'Chọn',minWidth:80,maxWidth:85,sortable:false,hideOnMobile:true,columnChooserLocked:true,suppressExport:true,cellRenderer:renderLandPick}]:[]),
 ...columns.map(([field,headerName])=>({
  field,headerName,minWidth:field==='block_code'?100:field==='variety_label'?130:120,
  valueFormatter:p=>{
   const b=p.data||{},v=p.value
   if(['area_ha'].includes(field))return num(v,2)
   if(['lotus_tree_count','density','plots'].includes(field))return num(v)
   if(field==='planting')return v?vnDate(v):'—'
   if(field==='lotus_estimated_flowering_date'||field==='lotus_estimated_sucker_selection_date')return vnDate(v)||'—'
   if(field==='block_code')return (v||'—')+(!farm.value&&b.farm?' · '+b.farm:'')
   return v||'—'
  },
  ...(field==='planting'?{valueGetter:p=>p.data?.planting||''}:{})
 })),
 {field:'gaps_label',headerName:'Thiếu thông tin',minWidth:180}
])
const landLayout=ref(loadColumnLayout('lotus-farm-land',gridColumns.value))
const normalizedLandLayout=computed(()=>normalizeColumnLayout(gridColumns.value,landLayout.value))
const shownLandColumns=computed(()=>displayedColumns(gridColumns.value,normalizedLandLayout.value).filter(col=>!col.columnChooserLocked))
function updateLandLayout(next){landLayout.value=saveColumnLayout('lotus-farm-land',gridColumns.value,next)}
function toggleLandColumn(id){updateLandLayout({...normalizedLandLayout.value,hidden:changeColumnVisibility(gridColumns.value,normalizedLandLayout.value.hidden,id)})}
function moveLandColumn(id,direction){updateLandLayout(moveColumn(gridColumns.value,normalizedLandLayout.value,id,direction))}
function pinLandColumn(id){updateLandLayout(pinColumn(gridColumns.value,normalizedLandLayout.value,id))}
watch(rows,()=>{gridVisible.value=null})

async function applyBulk(){
 const values=Object.fromEntries(Object.entries(bulk.value).filter(([,v])=>v))
 if(!Object.keys(values).length)return
 saving.value=true;let done=0
 try{for(const b of data.value.blocks.filter(x=>picked.value.has(x.name))){await call('lotus_farm.farm_land.save_block',{name:b.name,modified:b.modified,values},true);done++}
  notice.value='Đã cập nhật '+done+' lô.';bulkOpen.value=false;await load()}
 catch(e){error.value='Đã lưu '+done+' lô, dừng ở lỗi: '+e.message;await load()}finally{saving.value=false}}
function exportExcel(){if(farm.value)location.href='/api/method/lotus_farm.farm_land.export_blocks?'+new URLSearchParams({farm:farm.value})}
function exportVisibleLand(){
 const cols=shownLandColumns.value.filter(col=>col.field!=='__picked')
 const records=visibleLandRows.value
 if(!records.length)return
 exportExcelFile(buildXlsx(cols,records),'Danh-sach-lo-dang-hien')
}

async function readFile(event){const file=event.target.files?.[0];if(!file)return;saving.value=true;preview.value=null;error.value=''
 try{const content=await new Promise((ok,fail)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=fail;r.readAsDataURL(file)})
  preview.value=await call('lotus_farm.farm_land.preview_blocks',{farm:farm.value,content},true)}
 catch(e){error.value=e.message}finally{saving.value=false;event.target.value=''}}
async function commitImport(){saving.value=true
 try{const r=await call('lotus_farm.farm_land.commit_blocks',{farm:farm.value,token:preview.value.token},true)
  notice.value='Đã cập nhật '+r.saved+' lô từ Excel.'+(r.skipped.length?' Bỏ qua '+r.skipped.join(', ')+' vì vừa có người sửa.':'');importOpen.value=false;preview.value=null;await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
const changeText=c=>(c.old==null||c.old===''?'(trống)':c.old)+' → '+c.new
watch(farm,load)
watch(view,v=>{if(v==='map'&&!mapData.value)loadMap()})
watch(farm,()=>{mapData.value=null;if(view.value==='map')loadMap()})
onMounted(load)
useNoticeToast(notice)
</script>

<template>
<section class="land lotus-ui">
 <LandBlockDetail v-if="block" :block="block" :today="session.today" :editable="data?.editable||[]" :varieties="data?.varieties||[]"
  @back="router.push({path:'/farms',query:farm?{farm}:{}})" @changed="load" @notice="notice=$event" @error="error=$event"/>
 <template v-else>
  <header class="land-head">
   <h2>Vườn & lô</h2>
   <div class="land-farms" role="tablist" aria-label="Chọn vườn">
    <button type="button" role="tab" :aria-selected="!farm?'true':'false'" :class="{on:!farm}" @click="setFarm('')">Tất cả vườn</button>
    <button v-for="f in data?.farms||[]" :key="f.name" type="button" role="tab" :aria-selected="farm===f.name?'true':'false'" :class="{on:farm===f.name}" @click="setFarm(f.name)">{{f.farm_name||f.name}}</button>
   </div>
   <span class="land-spacer"></span>
   <div class="land-views" role="group" aria-label="Kiểu xem"><button type="button" :class="{on:view==='list'}" :aria-pressed="view==='list'" @click="view='list'"><LotusIcon name="list"/>Danh sách</button><button type="button" :class="{on:view==='map'}" :aria-pressed="view==='map'" @click="view='map'"><LotusIcon name="map"/>Bản đồ</button></div>
   <UiButton variant="outline" :disabled="!farm" :title="farm?'':'Chọn một vườn để xuất mẫu nhập'" @click="exportExcel"><LotusIcon name="download"/>Xuất mẫu Excel</UiButton>
   <UiButton v-if="data?.can_edit" variant="outline" :disabled="!farm" :title="farm?'':'Chọn một vườn để nhập'" @click="preview=null;importOpen=true"><LotusIcon name="upload"/>Nhập Excel</UiButton>
  </header>
  <p v-if="error" class="stock-error" role="alert">{{error}}</p>

  <div v-if="s" class="land-stats">
   <div><span>Diện tích</span><strong>{{num(s.area_ha,2)}} ha</strong><small>{{s.blocks}} lô · {{s.plots}} thửa</small></div>
   <div><span>Số cây gốc đã chốt</span><strong>{{num(s.trees)}}</strong><small>có số cây {{s.counted_blocks}}/{{s.blocks}} lô · {{num(s.counted_area_ha,2)}} ha</small></div>
   <div><span>Mật độ bình quân</span><strong>{{s.trees_per_ha?num(s.trees_per_ha)+' cây/ha':'—'}}</strong><small>trên lô có số cây gốc đã chốt</small></div>
   <button type="button" class="land-gaps" @click="gap=gap?'':'trees'"><span>Lô thiếu dữ liệu</span><strong>{{s.gaps.trees}}</strong><small>chưa có số cây · {{s.gaps.variety}} chưa có giống · {{s.gaps.planting}} chưa có ngày trồng · {{s.gaps.map}} chưa có ranh</small></button>
  </div>

  <section v-if="data?.zones?.length&&view==='list'" class="land-zones" aria-label="Theo khu">
   <button v-for="z in data.zones" :key="z.zone" type="button" class="land-zone" :class="{on:zone===z.zone}" :style="{'--zone':'var(--lotus-map-zone-'+String(z.zone).toLowerCase()+')'}" @click="zone=zone===z.zone?'':z.zone">
    <b>Khu {{z.zone}}</b><span>{{z.blocks}} lô · {{num(z.area_ha,2)}} ha</span><small>{{z.trees?num(z.trees)+' cây · '+num(z.trees_per_ha)+'/ha':'chưa có số cây'}}</small>
   </button>
  </section>

  <template v-if="view==='list'">
   <div class="land-filters">
    <UiInput v-model="search" type="search" placeholder="Tìm mã lô, tên, giống…" aria-label="Tìm lô" class="land-search"/>
    <UiSelect v-model="zone" aria-label="Lọc khu" class="land-narrow"><option value="">Mọi khu</option><option v-for="z in zones" :key="z" :value="z">Khu {{z}}</option></UiSelect>
    <UiSelect v-model="variety" aria-label="Lọc giống" class="land-narrow"><option value="">Mọi giống</option><option v-for="v in data?.varieties||[]" :key="v" :value="v">{{v}}</option><option value="-">Chưa có giống</option></UiSelect>
    <UiSelect v-model="gap" aria-label="Lọc dữ liệu thiếu" class="land-narrow"><option value="">Mọi lô</option><option v-for="(label,key) in data?.gap_labels||{}" :key="key" :value="key">{{label}}</option></UiSelect>
    <span class="land-spacer"></span>
    <div class="land-filter-actions">
     <UiButton v-if="data?.can_edit&&rows.length" variant="outline" size="sm" @click="togglePickAll">{{allPicked?'Bỏ chọn lô đang hiện':'Chọn lô đang hiện'}}</UiButton>
     <span class="land-count">{{rows.length}} lô · {{num(shownTotals.area,2)}} ha · {{num(shownTotals.trees)}} cây</span>
     <ColumnVisibilityMenu :columns="gridColumns" :layout="normalizedLandLayout" @toggle="toggleLandColumn" @reset="updateLandLayout({})" @all="updateLandLayout({...normalizedLandLayout,hidden:[]})" @move="moveLandColumn" @pin="pinLandColumn"/>
     <UiButton variant="outline" size="sm" :disabled="busy||!visibleLandRows.length" @click="exportVisibleLand"><LotusIcon name="download"/>Xuất bảng Excel</UiButton>
     <UiButton v-if="data?.can_edit&&picked.size" variant="outline" size="sm" @click="bulk={farm_zone:'',variety:''};bulkOpen=true">Sửa {{picked.size}} lô đã chọn</UiButton>
    </div>
   </div>
   <div class="land-table" :aria-busy="busy">
    <DataTable :rows="gridRows" :columns="gridColumns" :exportable="false" :columns-menu="false" :column-layout="normalizedLandLayout" row-key="name" storage-key="lotus-farm-land" :loading="busy"
      interactive empty="Không có lô phù hợp bộ lọc." @open="row=>openBlock(row.name)"
      @visible-rows="list=>gridVisible=list"/>
   </div>
  </template>

  <section v-else class="land-map">
   <p v-if="!farm" class="land-empty">Chọn một vườn ở trên để xem bản đồ lô.</p>
   <PlotMap v-else :collection="mapData" :farm="farm" :user="session.user" :color-by="colorBy" :varieties="data?.varieties||[]" @open="openBlock" @reset="loadMap">
    <template #filters><UiSelect v-model="colorBy" aria-label="Tô màu lô" class="land-colorby"><option v-for="[value,label] in COLOR_MODES" :key="value" :value="value">{{label}}</option></UiSelect></template>
   </PlotMap>
  </section>
 </template>

 <WorkspaceModal v-model="bulkOpen" :title="'Sửa '+picked.size+' lô'" :busy="saving" width="520px">
  <form class="land-form" @submit.prevent="applyBulk"><p class="land-note">Chỉ đổi các ô có nhập; ô trống giữ nguyên.</p>
   <FormField label="Khu" v-slot="f"><UiInput v-bind="f" v-model="bulk.farm_zone" placeholder="VD: A" maxlength="20"/></FormField>
   <FormField label="Giống" v-slot="f"><UiSelect v-bind="f" v-model="bulk.variety"><option value="">Giữ nguyên</option><option v-for="v in data?.varieties||[]" :key="v" :value="v">{{v}}</option></UiSelect></FormField>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="bulkOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!(bulk.farm_zone||bulk.variety)">{{saving?'Đang lưu…':'Lưu'}}</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal v-model="importOpen" title="Nhập lô từ Excel" :busy="saving" width="980px">
  <div class="land-form">
   <ol class="land-steps"><li>Bấm <b>Xuất Excel</b> để tải danh sách lô hiện tại.</li><li>Sửa các cột cần đổi (để trống ô nào thì giữ nguyên ô đó). Đổi số cây thì ghi cả <b>Nguồn số cây</b>.</li><li>Chọn file đã sửa để xem trước, rồi bấm Cập nhật.</li></ol>
   <LotusField label="File Excel đã sửa" type="file" accept=".xlsx" :disabled="saving" @change="readFile"/>
   <template v-if="preview">
    <p><b>{{preview.ready}}</b> lô sẽ cập nhật · {{preview.unchanged}} lô không đổi · <span :class="{'land-bad':preview.errors}">{{preview.errors}} dòng lỗi</span></p>
    <div class="land-table land-preview"><DataTable :exportable="false" :columns-menu="false" :rows="preview.rows.filter(r=>r.changes.length||r.errors.length||r.warnings.length)" :columns="landPreviewColumns" row-key="line" storage-key="land-import-preview" /></div>
    <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="importOpen=false">Hủy</UiButton><UiButton type="button" :disabled="saving||!preview.ready" @click="commitImport">{{saving?'Đang cập nhật…':'Cập nhật '+preview.ready+' lô'}}</UiButton></div>
   </template>
  </div>
 </WorkspaceModal>
</section>
</template>
