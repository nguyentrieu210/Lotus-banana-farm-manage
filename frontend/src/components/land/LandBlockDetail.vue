<script setup>
// One lot: overview (facts, plots, map, planned dates), work & materials, yield & losses, disease & bunch
// care, and the change history. Each tab loads its section of lotus_farm.farm_land.block_detail on open.
import {computed,defineAsyncComponent,reactive,ref,watch} from 'vue'
import {useRouter} from 'vue-router'
import LotusIcon from '../LotusIcon.vue'
import DataTable from '../DataTable.vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import {Button as UiButton} from '../ui/button'
import {Input as UiInput} from '../ui/input'
import UiSelect from '../ui/select/Select.vue'
import {call} from '../../api'
import {useSession} from '../../store'

const props=defineProps({block:{type:String,required:true},today:String,editable:{type:Array,default:()=>[]},varieties:{type:Array,default:()=>[]}})
const emit=defineEmits(['back','changed','notice','error'])
const PlotMap=defineAsyncComponent(()=>import('../CareMap.vue'))
const router=useRouter(),session=useSession()
const TABS=[['overview','Tổng quan'],['work','Công việc & vật tư'],['yield','Sản lượng & tổn thất'],['care','Bệnh & chăm sóc buồng'],['history','Lịch sử thay đổi']]
const tab=ref('overview'),info=ref(null),section=reactive({}),busy=ref(false),saving=ref(false)
const back90=d=>{const x=new Date((d||new Date().toISOString().slice(0,10))+'T00:00:00Z');x.setUTCDate(x.getUTCDate()-89);return x.toISOString().slice(0,10)}
const range=reactive({from:back90(props.today),to:props.today||new Date().toISOString().slice(0,10)})
const editOpen=ref(false),form=reactive({}),plotOpen=ref(false),plot=reactive({})
const b=computed(()=>info.value?.block||{})
const num=(v,d=0)=>v==null||v===''?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:d})
const vnDate=v=>v?String(v).slice(8,10)+'/'+String(v).slice(5,7)+'/'+String(v).slice(0,4):''
const collection=computed(()=>info.value?.geometry?{type:'FeatureCollection',features:[{type:'Feature',geometry:info.value.geometry.geojson,properties:{block:b.value.name,code:b.value.block_code,zone:b.value.farm_zone,area_ha:b.value.area_ha,approval_state:info.value.geometry.approval_state}}]}:null)
const OPERATIONS={Shooting:'Trổ buồng','Cut Bud':'Cắt bắp',Spray:'Phun buồng',Bag:'Bao buồng',Care:'Chăm sóc buồng',Inspection:'Kiểm tra buồng'}
const PLANTING={Planting:'Trồng mới',Replanting:'Trồng dặm'}
async function loadOverview(){busy.value=true
 try{info.value=await call('lotus_farm.farm_land.block_detail',{block:props.block,section:'overview'})}catch(e){emit('error',e.message)}finally{busy.value=false}}
async function loadSection(name){if(['overview','history'].includes(name))return;busy.value=true
 try{section[name]=await call('lotus_farm.farm_land.block_detail',{block:props.block,section:name,from_date:range.from,to_date:range.to})}catch(e){emit('error',e.message)}finally{busy.value=false}}
function go(path,extra={}){router.push({path:'/'+path,query:{farm:b.value.farm,block:props.block,...extra}})}
function openEdit(){for(const k of Object.keys(form))delete form[k];for(const f of props.editable)form[f.field]=b.value[f.field]??'';form.lotus_tree_count_source='';editOpen.value=true}
async function saveEdit(){saving.value=true
 try{info.value=await call('lotus_farm.farm_land.save_block',{name:b.value.name,modified:b.value.modified,values:{...form}},true);editOpen.value=false;emit('notice','Đã lưu lô '+b.value.block_code+'.');emit('changed')}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
function openPlot(p=null){Object.assign(plot,{name:p?.name||null,modified:p?.modified||null,plot_code:p?.plot_code||'',plot_name:p?.plot_name||'',area_ha:p?.area_ha??'',active:p?p.active:1});plotOpen.value=true}
async function savePlot(){saving.value=true
 try{const {name,modified,...values}=plot;info.value=await call('lotus_farm.farm_land.save_plot',{block:props.block,name,modified,values},true);plotOpen.value=false;emit('notice','Đã lưu thửa '+values.plot_code+'.');emit('changed')}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
const plotsArea=computed(()=>(info.value?.plots||[]).reduce((s,p)=>s+Number(p.area_ha||0),0))
const kindOf=f=>({float:'number',int:'number',date:'date'})[f.kind]||'text'
watch(()=>props.block,()=>{info.value=null;for(const k of Object.keys(section))delete section[k];tab.value='overview';loadOverview()},{immediate:true})
watch(tab,name=>{if(!section[name])loadSection(name)})
function applyRange(){for(const k of Object.keys(section))delete section[k];loadSection(tab.value)}

const dcol=(field,headerName,formatter)=>({field,headerName,minWidth:115,...(formatter?{valueFormatter:p=>formatter(p.value,p.data)}:{})})
const dnum=(field,headerName,precision=0)=>dcol(field,headerName,v=>num(v,precision))
const ddate=(field,headerName)=>dcol(field,headerName,v=>vnDate(v))
function plotActions(params){
 const parent=document.createElement('div')
 for(const [name,act] of [['Lịch sử thửa',()=>router.push('/plots/'+encodeURIComponent(params.data.name))],...(info.value?.can_edit?[['Sửa',()=>openPlot(params.data)]]:[])]){
  const btn=document.createElement('button');btn.type='button';btn.textContent=name;btn.className='land-text-link'
  btn.addEventListener('click',e=>{e.stopPropagation();act()});parent.appendChild(btn)
 }
 return parent
}
const plotsCols=[dcol('plot_code','Mã thửa'),dcol('plot_name','Tên'),dnum('area_ha','Diện tích (ha)',3),dcol('active','Trạng thái',v=>v?'Đang dùng':'Ngừng'),{field:'name',colId:'actions',headerName:'Thao tác',cellRenderer:plotActions,minWidth:180,sortable:false,hideOnMobile:true}]
const worksCols=[dcol('work','Công việc'),dcol('qty','Khối lượng',(v,r)=>num(v,2)+' '+(r.uom||'')),dnum('workdays','Công',2),dnum('days','Số ngày'),ddate('last','Gần nhất')]
const teamsCols=[dcol('team','Đội'),dcol('workdays','Tổng công',v=>num(v,2)+' công')]
const materialsCols=[dcol('item_name','Vật tư',(_,r)=>r.item_name+' · '+r.uom),dnum('required','Định mức',2),dnum('consumed','Đã dùng',2),dcol('variance','Chênh',(_,r)=>r.required?num(r.consumed-r.required,2):'—')]
const forecastCols=[dcol('period_start_date','Kỳ',(_,r)=>vnDate(r.period_start_date)+' – '+vnDate(r.period_end_date)),dnum('expected_harvest_bunch_qty','Buồng'),dnum('saleable_forecast_kg','Đạt bán (kg)'),dcol('supply_state','Trạng thái')]
const cancelledCols=[dcol('reason','Nguyên nhân'),dcol('bunches','Số buồng',v=>num(v)+' buồng')]
const measuredCols=[ddate('posting_date','Ngày'),dnum('sample_count','Mẫu'),dcol('average_length','Dài TB',(v,r)=>num(v,1)+' '+r.uom),dnum('average_diameter','Đường kính TB',1)]
const diseaseCols=[dcol('disease','Bệnh'),dnum('observations','Lần'),dnum('plants','Cây bị'),dcol('severity','Mức gần nhất'),ddate('last','Gần nhất')]
const operationsCols=[ddate('week','Tuần từ'),dcol('operation','Thao tác',v=>OPERATIONS[v]||v),dnum('bunches','Buồng')]
const plantingCols=[ddate('posting_date','Ngày'),dcol('event_type','Loại',v=>PLANTING[v]||v),dnum('plant_qty','Số cây'),dcol('area_ha','Diện tích',v=>num(v,2)+' ha'),dcol('notes','Ghi chú')]

</script>

<template>
<article class="land-block" :aria-busy="busy">
 <header class="land-block__head">
  <UiButton variant="ghost" size="sm" @click="emit('back')">‹ Danh sách lô</UiButton>
  <div class="land-block__title"><h2>Lô {{b.block_code||'…'}}</h2><span>{{b.farm_name}} · Khu {{b.farm_zone||'—'}}<template v-if="b.block_name&&b.block_name!==b.block_code"> · {{b.block_name}}</template></span></div>
  <span v-if="b.active===0" class="land-gap">Ngừng sử dụng</span>
  <span class="land-spacer"></span>
  <UiButton v-if="info?.can_edit" variant="outline" @click="openEdit"><LotusIcon name="edit"/>Sửa lô</UiButton>
 </header>
 <div class="land-stats land-stats--block">
  <div><span>Diện tích</span><strong>{{num(b.area_ha,2)}} ha</strong><small>{{(info?.plots||[]).length}} thửa · {{num(plotsArea,2)}} ha</small></div>
  <div><span>Số cây kiểm kê</span><strong>{{b.lotus_tree_count?num(b.lotus_tree_count):'Chưa đếm'}}</strong><small>{{b.lotus_tree_count_source||'—'}}</small></div>
  <div><span>Mật độ</span><strong>{{b.density?num(b.density)+' cây/ha':'—'}}</strong><small>{{b.planting_density?'thiết kế '+num(b.planting_density)+' cây/ha':'chưa có mật độ thiết kế'}}</small></div>
  <div><span>Giống</span><strong>{{b.variety||'Chưa có'}}</strong><small>{{b.planting_date?'trồng '+vnDate(b.planting_date):b.lotus_inferred_planting_date?'trồng ~'+vnDate(b.lotus_inferred_planting_date)+' (suy ngược)':'chưa có ngày trồng'}}</small></div>
 </div>
 <nav class="workspace-tabs" aria-label="Thông tin lô"><button v-for="[id,label] in TABS" :key="id" type="button" :class="{active:tab===id}" :aria-current="tab===id?'page':undefined" @click="tab=id">{{label}}</button></nav>
 <div v-if="!['overview','history'].includes(tab)" class="land-filters"><label>Từ<UiInput v-model="range.from" type="date" :max="range.to"/></label><label>Đến<UiInput v-model="range.to" type="date" :min="range.from"/></label><UiButton variant="outline" @click="applyRange"><LotusIcon name="refresh"/>Xem</UiButton></div>

 <section v-if="tab==='overview'&&info" class="land-grid">
  <div class="land-card">
   <h3>Thông tin lô</h3>
   <dl class="land-dl">
    <div><dt>Mã / tên</dt><dd>{{b.block_code}} · {{b.block_name||'—'}}</dd></div><div><dt>Khu · khu tưới</dt><dd>{{b.farm_zone||'—'}} · {{b.irrigation_zone||'—'}}</dd></div>
    <div><dt>Ngày chọn chồi dự kiến</dt><dd>{{vnDate(b.lotus_estimated_sucker_selection_date)||'—'}}</dd></div><div><dt>Ngày trổ dự kiến</dt><dd>{{vnDate(b.lotus_estimated_flowering_date)||'—'}}</dd></div>
    <div class="land-dl__full"><dt>Căn cứ ước lượng</dt><dd><details v-if="b.lotus_estimation_basis&&b.lotus_estimation_basis.length>140"><summary>{{b.lotus_estimation_basis.slice(0,140)}}…</summary>{{b.lotus_estimation_basis}}</details><template v-else>{{b.lotus_estimation_basis||'—'}}</template></dd></div><div><dt>Ghi chú</dt><dd>{{b.notes||'—'}}</dd></div>
   </dl>
   <div class="land-links"><UiButton variant="link" @click="go('map')">Bản đồ chăm sóc ↗</UiButton><UiButton variant="link" @click="go('work')">Tiến độ công việc ↗</UiButton><UiButton variant="link" @click="go('forecast')">Dự thu ↗</UiButton></div>
  </div>
  <div class="land-card land-card--map"><h3>Ranh giới</h3>
   <PlotMap v-if="collection" compact :collection="collection" :farm="b.farm" :user="session.user" @open="()=>{}"/>
   <p v-else class="land-empty">Lô chưa có ranh giới. Nhập ranh từ Lotus Map hoặc vẽ trên Bản đồ chăm sóc.</p>
   <small v-if="info.geometry?.approval_state==='Draft'" class="land-note">Ranh bản nháp (phiên bản {{info.geometry.version}}), chưa duyệt.</small>
  </div>
  <div class="land-card land-card--wide"><header class="land-card__head"><h3>Thửa trong lô</h3><UiButton v-if="info.can_edit" variant="outline" size="sm" @click="openPlot()"><LotusIcon name="plus"/>Thêm thửa</UiButton></header>
   <DataTable v-if="info.plots.length" :rows="info.plots" :columns="plotsCols" row-key="name" storage-key="lot-plot-list"/>
   <p v-else class="land-empty">Lô chưa chia thửa.</p>
   <p v-if="info.plots.length&&Math.abs(plotsArea-Number(b.area_ha||0))>0.05" class="land-warn">Tổng diện tích thửa {{num(plotsArea,2)}} ha khác diện tích lô {{num(b.area_ha,2)}} ha.</p>
  </div>
 </section>

 <section v-if="tab==='work'&&section.work" class="land-grid">
  <div class="land-card land-card--wide"><h3>Công việc đã làm</h3>
   <DataTable v-if="section.work.work?.length" :rows="section.work.work" :columns="worksCols" row-key="work" storage-key="lot-work"/>
   <p v-else class="land-empty">{{section.work.work===null?'Bạn chưa có quyền xem kết quả công việc.':'Chưa có kết quả công việc đã duyệt của lô trong khoảng ngày này.'}}</p></div>
  <div class="land-card"><h3>Nhân công theo đội</h3>
   <DataTable v-if="section.work.teams?.length" :rows="section.work.teams" :columns="teamsCols" row-key="team" storage-key="lot-teams"/>
   <p v-else class="land-empty">Chưa bố trí nhân công cho lô.</p></div>
  <div class="land-card"><h3>Vật tư: định mức và đã dùng</h3>
   <DataTable v-if="section.work.materials?.length" :rows="section.work.materials" :columns="materialsCols" row-key="item" storage-key="lot-materials"/>
   <p v-else class="land-empty">Chưa có nhu cầu hay sử dụng vật tư của lô.</p></div>
 </section>

 <section v-if="tab==='yield'&&section.yield" class="land-grid">
  <div class="land-card"><h3>Thu hoạch trong khoảng</h3>
   <template v-if="section.yield.harvest"><dl class="land-dl"><div><dt>Buồng</dt><dd>{{num(section.yield.harvest.bunches)}}</dd></div><div><dt>Khối lượng cân</dt><dd>{{num(section.yield.harvest.gross_kg)}} kg</dd></div><div><dt>Đạt bán</dt><dd>{{num(section.yield.harvest.saleable_kg)}} kg</dd></div></dl>
    <p v-if="!section.yield.harvest.rows.length" class="land-empty">Chưa có lượt thu hoạch đã duyệt.</p></template>
   <p v-else class="land-empty">Bạn chưa có quyền xem thu hoạch.</p></div>
  <div class="land-card"><h3>Dự thu</h3>
   <DataTable v-if="section.yield.forecasts?.length" :rows="section.yield.forecasts" :columns="forecastCols" row-key="name" storage-key="lot-forecast"/>
   <p v-else class="land-empty">Chưa có dự thu cho lô.</p></div>
  <div class="land-card"><header class="land-card__head"><h3>Hủy buồng theo nguyên nhân</h3><UiButton variant="link" size="sm" @click="go('losses')">Hủy & tổn thất ↗</UiButton></header>
   <DataTable v-if="section.yield.cancellations?.length" :rows="section.yield.cancellations" :columns="cancelledCols" row-key="reason" storage-key="lot-cancellations"/>
   <p v-else class="land-empty">Không có buồng hủy trong khoảng ngày này.</p></div>
  <div class="land-card"><header class="land-card__head"><h3>Đo trái gần nhất</h3><UiButton variant="link" size="sm" @click="go('measurements')">Đo trái ↗</UiButton></header>
   <DataTable v-if="section.yield.measurements?.length" :rows="section.yield.measurements" :columns="measuredCols" storage-key="lot-measurements"/>
   <p v-else class="land-empty">Chưa có lần đo trái của lô.</p></div>
 </section>

 <section v-if="tab==='care'&&section.care" class="land-grid">
  <div class="land-card"><h3>Bệnh ghi nhận</h3>
   <DataTable v-if="section.care.diseases?.length" :rows="section.care.diseases" :columns="diseaseCols" row-key="disease" storage-key="lot-diseases"/>
   <p v-else class="land-empty">Không có ghi nhận bệnh trong khoảng ngày này.</p></div>
  <div class="land-card"><h3>Chăm sóc buồng theo tuần</h3>
   <DataTable v-if="section.care.operations?.length" :rows="section.care.operations" :columns="operationsCols" storage-key="lot-operations"/>
   <p v-else class="land-empty">Chưa có thao tác buồng trong khoảng ngày này.</p></div>
  <div class="land-card land-card--wide"><h3>Trồng / trồng dặm</h3>
   <DataTable v-if="section.care.planting?.length" :rows="section.care.planting" :columns="plantingCols" storage-key="lot-planting"/>
   <p v-else class="land-empty">Chưa có lần trồng hay trồng dặm trong khoảng ngày này.</p></div>
 </section>

 <section v-if="tab==='history'&&info" class="land-card">
  <h3>Lịch sử thay đổi</h3>
  <ol v-if="info.history.length" class="land-history"><li v-for="(h,i) in info.history" :key="i"><b>{{h.by}}</b> · {{vnDate(h.at)}} {{String(h.at).slice(11,16)}}<ul><li v-for="(c,j) in h.changes" :key="j">{{c.field}}: {{c.old===null||c.old===''?'(trống)':c.old}} → {{c.new===null||c.new===''?'(trống)':c.new}}</li></ul></li></ol>
  <p v-else class="land-empty">Chưa có thay đổi nào được ghi lại.</p>
 </section>

 <WorkspaceModal v-model="editOpen" :title="'Sửa lô '+b.block_code" :busy="saving" width="720px">
  <form class="land-form land-form--grid" @submit.prevent="saveEdit">
   <label v-for="f in editable.filter(f=>f.field!=='lotus_tree_count_source')" :key="f.field">{{f.label}}
    <UiSelect v-if="f.field==='variety'" v-model="form.variety"><option value="">Chưa có</option><option v-for="v in varieties" :key="v" :value="v">{{v}}</option><option v-if="form.variety&&!varieties.includes(form.variety)" :value="form.variety">{{form.variety}}</option></UiSelect>
    <UiSelect v-else-if="f.field==='active'" v-model.number="form.active"><option :value="1">Đang dùng</option><option :value="0">Ngừng</option></UiSelect>
    <UiInput v-else v-model="form[f.field]" :type="kindOf(f)" :step="f.kind==='float'?'any':undefined" min="0"/></label>
   <label v-if="String(form.lotus_tree_count??'')!==String(b.lotus_tree_count??'')" class="land-form__full">Nguồn số cây (bắt buộc khi đổi số cây)<UiInput v-model="form.lotus_tree_count_source" required placeholder="VD: Đếm 20/10/2026 · tổ trưởng khu A"/></label>
   <div class="land-actions land-form__full"><UiButton type="button" variant="outline" :disabled="saving" @click="editOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving">{{saving?'Đang lưu…':'Lưu lô'}}</UiButton></div>
  </form>
 </WorkspaceModal>
 <WorkspaceModal v-model="plotOpen" :title="plot.name?'Sửa thửa '+plot.plot_code:'Thêm thửa vào lô '+b.block_code" :busy="saving" width="520px">
  <form class="land-form" @submit.prevent="savePlot">
   <label>Mã thửa<UiInput v-model="plot.plot_code" required maxlength="140"/></label>
   <label>Tên thửa<UiInput v-model="plot.plot_name" maxlength="140"/></label>
   <label>Diện tích (ha)<UiInput v-model="plot.area_ha" type="number" step="any" min="0"/></label>
   <label>Trạng thái<UiSelect v-model.number="plot.active"><option :value="1">Đang dùng</option><option :value="0">Ngừng</option></UiSelect></label>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="plotOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!plot.plot_code">{{saving?'Đang lưu…':'Lưu thửa'}}</UiButton></div>
  </form>
 </WorkspaceModal>
</article>
</template>