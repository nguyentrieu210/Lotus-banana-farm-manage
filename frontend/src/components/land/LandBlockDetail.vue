<script setup>
// One lot: overview (facts, map, planned dates), work & materials, yield & losses, disease & bunch care (the three
// read from the confirmed sổ lô), and the change history. Each tab loads its section of
// lotus_farm.farm_land.block_detail on open.
import {computed,defineAsyncComponent,reactive,ref,watch} from 'vue'
import {useRouter} from 'vue-router'
import LotusIcon from '../LotusIcon.vue'
import DataTable from '../DataTable.vue'
import ModalForm from '../form/ModalForm.vue'
import FormGrid from '../form/FormGrid.vue'
import LotusField from '../form/LotusField.vue'
import {DateRangePicker} from '../ui/date-picker'
import {Button as UiButton} from '../ui/button'
import {call} from '../../api'
import {stageLabels} from '../../lot-entry-model'
const activeOptions=[{value:1,label:'Đang dùng'},{value:0,label:'Ngừng'}]
import {useSession} from '../../store'

const props=defineProps({block:{type:String,required:true},today:String,editable:{type:Array,default:()=>[]},varieties:{type:Array,default:()=>[]}})
const emit=defineEmits(['back','changed','notice','error'])
const CareMap=defineAsyncComponent(()=>import('../CareMap.vue'))
const router=useRouter(),session=useSession()
const TABS=[['overview','Tổng quan'],['work','Công việc & vật tư'],['yield','Sản lượng & tổn thất'],['care','Bệnh & chăm sóc buồng'],['history','Lịch sử thay đổi']]
const tab=ref('overview'),info=ref(null),section=reactive({}),busy=ref(false),saving=ref(false)
const back90=d=>{const x=new Date((d||new Date().toISOString().slice(0,10))+'T00:00:00Z');x.setUTCDate(x.getUTCDate()-89);return x.toISOString().slice(0,10)}
const range=reactive({from:back90(props.today),to:props.today||new Date().toISOString().slice(0,10)})
const editOpen=ref(false),form=reactive({})
const b=computed(()=>info.value?.block||{})
const num=(v,d=0)=>v==null||v===''?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:d})
const vnDate=v=>v?String(v).slice(8,10)+'/'+String(v).slice(5,7)+'/'+String(v).slice(0,4):''
const collection=computed(()=>info.value?.geometry?{type:'FeatureCollection',features:[{type:'Feature',geometry:info.value.geometry.geojson,properties:{block:b.value.name,code:b.value.block_code,zone:b.value.farm_zone,area_ha:b.value.area_ha,approval_state:info.value.geometry.approval_state}}]}:null)
async function loadOverview(){busy.value=true
 try{info.value=await call('lotus_farm.farm_land.block_detail',{block:props.block,section:'overview'})}catch(e){emit('error',e.message)}finally{busy.value=false}}
async function loadSection(name){if(['overview','history'].includes(name))return;busy.value=true
 try{section[name]=await call('lotus_farm.farm_land.block_detail',{block:props.block,section:name,from_date:range.from,to_date:range.to})}catch(e){emit('error',e.message)}finally{busy.value=false}}
function go(path,extra={}){router.push({path:'/'+path,query:{farm:b.value.farm,block:props.block,...extra}})}
function openEdit(){for(const k of Object.keys(form))delete form[k];for(const f of props.editable)form[f.field]=b.value[f.field]??'';form.lotus_tree_count_source='';editOpen.value=true}
async function saveEdit(){saving.value=true
 try{info.value=await call('lotus_farm.farm_land.save_block',{name:b.value.name,modified:b.value.modified,values:{...form}},true);editOpen.value=false;emit('notice','Đã lưu lô '+b.value.block_code+'.');emit('changed')}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
const kindOf=f=>({float:'number',int:'number',date:'date'})[f.kind]||'text'
watch(()=>props.block,()=>{info.value=null;for(const k of Object.keys(section))delete section[k];tab.value='overview';loadOverview()},{immediate:true})
watch(tab,name=>{if(!section[name])loadSection(name)})
function applyRange(){for(const k of Object.keys(section))delete section[k];loadSection(tab.value)}

const dcol=(field,headerName,formatter)=>({field,headerName,minWidth:115,...(formatter?{valueFormatter:p=>formatter(p.value,p.data)}:{})})
const dnum=(field,headerName,precision=0)=>dcol(field,headerName,v=>num(v,precision))
const ddate=(field,headerName)=>dcol(field,headerName,v=>vnDate(v))
// A section the server answers with null is one the user may not read.
const NO_ACCESS='Bạn chưa có quyền xem sổ lô.'
const none=(rows,text)=>rows===null?NO_ACCESS:text
const worksCols=[dcol('work','Công việc'),dcol('qty','Khối lượng',(v,r)=>num(v,2)+' '+(r.uom||'')),dnum('workdays','Công',2),dnum('days','Số ngày'),ddate('last','Gần nhất')]
const teamsCols=[dcol('team','Tổ'),dcol('workdays','Tổng công',v=>num(v,2)+' công')]
const materialsCols=[dcol('item_name','Vật tư',(_,r)=>r.item_name+' · '+r.uom),dnum('used','Đã dùng',2)]
const forecastCols=[dcol('month','Tháng thu'),dnum('bunches','Buồng dự kiến'),dnum('packed_kg','Thành phẩm (kg)')]
const cancelledCols=[dcol('reason','Nguyên nhân'),dcol('bunches','Số buồng',v=>num(v)+' buồng')]
const diseaseCols=[dcol('disease','Bệnh'),dnum('observations','Lần'),dnum('plants','Cây bị'),dcol('severity','Mức gần nhất'),ddate('last','Gần nhất')]
const operationsCols=[ddate('week','Tuần từ'),dcol('stage','Công đoạn',v=>stageLabels[v]||v),dnum('qty','Số lượng')]

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
  <div><span>Diện tích</span><strong>{{num(b.area_ha,2)}} ha</strong></div>
  <div><span>Số cây gốc đã chốt</span><strong>{{b.lotus_tree_count?num(b.lotus_tree_count):'Chưa có số cây'}}</strong><small>{{b.lotus_tree_count_source||'—'}}</small></div>
  <div><span>Mật độ</span><strong>{{b.density?num(b.density)+' cây/ha':'—'}}</strong><small>{{b.planting_density?'thiết kế '+num(b.planting_density)+' cây/ha':'chưa có mật độ thiết kế'}}</small></div>
  <div><span>Giống</span><strong>{{b.variety||'Chưa có'}}</strong><small>{{b.planting_date?'trồng '+vnDate(b.planting_date):b.lotus_inferred_planting_date?'trồng ~'+vnDate(b.lotus_inferred_planting_date)+' (suy ngược)':'chưa có ngày trồng'}}</small></div>
 </div>
 <nav class="workspace-tabs" aria-label="Thông tin lô"><button v-for="[id,label] in TABS" :key="id" type="button" :class="{active:tab===id}" :aria-current="tab===id?'page':undefined" @click="tab=id">{{label}}</button></nav>
 <div v-if="!['overview','history'].includes(tab)" class="land-filters"><DateRangePicker v-model:from="range.from" v-model:to="range.to"/><UiButton variant="outline" @click="applyRange"><LotusIcon name="refresh"/>Xem</UiButton></div>

 <section v-if="tab==='overview'&&info" class="land-grid">
  <div class="land-card">
   <h3>Thông tin lô</h3>
   <dl class="land-dl">
    <div><dt>Mã / tên</dt><dd>{{b.block_code}} · {{b.block_name||'—'}}</dd></div><div><dt>Khu · khu tưới</dt><dd>{{b.farm_zone||'—'}} · {{b.irrigation_zone||'—'}}</dd></div>
    <div><dt>Ngày chọn chồi dự kiến</dt><dd>{{vnDate(b.lotus_estimated_sucker_selection_date)||'—'}}</dd></div><div><dt>Ngày trổ dự kiến</dt><dd>{{vnDate(b.lotus_estimated_flowering_date)||'—'}}</dd></div>
    <div class="land-dl__full"><dt>Căn cứ ước lượng</dt><dd><details v-if="b.lotus_estimation_basis&&b.lotus_estimation_basis.length>140"><summary>{{b.lotus_estimation_basis.slice(0,140)}}…</summary>{{b.lotus_estimation_basis}}</details><template v-else>{{b.lotus_estimation_basis||'—'}}</template></dd></div><div><dt>Ghi chú</dt><dd>{{b.notes||'—'}}</dd></div>
   </dl>
   <div class="land-links"><UiButton variant="link" @click="go('map')">Bản đồ chăm sóc ↗</UiButton><UiButton variant="link" @click="go('cong-viec')">Việc hằng ngày ↗</UiButton><UiButton variant="link" @click="go('forecast')">Dự thu ↗</UiButton></div>
  </div>
  <div class="land-card land-card--map"><h3>Ranh giới</h3>
   <CareMap v-if="collection" compact :collection="collection" :farm="b.farm" :user="session.user" @open="()=>{}"/>
   <p v-else class="land-empty">Lô chưa có ranh giới. Nhập ranh từ Lotus Map hoặc vẽ trên Bản đồ chăm sóc.</p>
   <small v-if="info.geometry?.approval_state==='Draft'" class="land-note">Ranh bản nháp (phiên bản {{info.geometry.version}}), chưa duyệt.</small>
  </div>
 </section>

 <section v-if="tab==='work'&&section.work" class="land-grid">
  <div class="land-card land-card--wide"><h3>Công việc đã làm</h3>
   <DataTable v-if="section.work.work?.length" :rows="section.work.work" :columns="worksCols" row-key="work" storage-key="lot-work"/>
   <p v-else class="land-empty">{{none(section.work.work,'Chưa có việc đã xác nhận của lô trong khoảng ngày này.')}}</p></div>
  <div class="land-card"><h3>Công theo tổ</h3>
   <DataTable v-if="section.work.teams?.length" :rows="section.work.teams" :columns="teamsCols" row-key="team" storage-key="lot-teams"/>
   <p v-else class="land-empty">{{none(section.work.teams,'Chưa có công ghi cho lô trong khoảng ngày này.')}}</p></div>
  <div class="land-card"><h3>Vật tư đã dùng</h3>
   <DataTable v-if="section.work.materials?.length" :rows="section.work.materials" :columns="materialsCols" row-key="item" storage-key="lot-materials"/>
   <p v-else class="land-empty">{{none(section.work.materials,'Chưa có vật tư báo dùng cho lô trong khoảng ngày này.')}}</p></div>
 </section>

 <section v-if="tab==='yield'&&section.yield" class="land-grid">
  <div class="land-card"><h3>Thu hoạch trong khoảng</h3>
   <template v-if="section.yield.harvest"><dl class="land-dl"><div><dt>Buồng</dt><dd>{{num(section.yield.harvest.bunches)}}</dd></div><div><dt>Khối lượng cân</dt><dd>{{num(section.yield.harvest.kg)}} kg</dd></div></dl>
    <p v-if="!section.yield.harvest.lines" class="land-empty">Chưa có dòng thu hoạch đã xác nhận.</p></template>
   <p v-else class="land-empty">{{NO_ACCESS}}</p></div>
  <div class="land-card"><h3>Dự thu</h3>
   <DataTable v-if="section.yield.forecasts?.length" :rows="section.yield.forecasts" :columns="forecastCols" row-key="month" storage-key="lot-forecast-36"/>
   <p v-else class="land-empty">Chưa có dự thu cho lô.</p></div>
  <div class="land-card"><header class="land-card__head"><h3>Hủy buồng theo nguyên nhân</h3></header>
   <DataTable v-if="section.yield.cancellations?.length" :rows="section.yield.cancellations" :columns="cancelledCols" row-key="reason" storage-key="lot-cancellations"/>
   <p v-else class="land-empty">{{none(section.yield.cancellations,'Không có buồng hủy trong khoảng ngày này.')}}</p></div>
 </section>

 <section v-if="tab==='care'&&section.care" class="land-grid">
  <div class="land-card"><h3>Bệnh ghi nhận</h3>
   <DataTable v-if="section.care.diseases?.length" :rows="section.care.diseases" :columns="diseaseCols" row-key="disease" storage-key="lot-diseases"/>
   <p v-else class="land-empty">{{none(section.care.diseases,'Không có ghi nhận bệnh trong khoảng ngày này.')}}</p></div>
  <div class="land-card"><h3>Chăm sóc buồng theo tuần</h3>
   <DataTable v-if="section.care.operations?.length" :rows="section.care.operations" :columns="operationsCols" storage-key="lot-operations"/>
   <p v-else class="land-empty">{{none(section.care.operations,'Chưa có việc chăm sóc buồng trong khoảng ngày này.')}}</p></div>
 </section>

 <section v-if="tab==='history'&&info" class="land-card">
  <h3>Lịch sử thay đổi</h3>
  <ol v-if="info.history.length" class="land-history"><li v-for="(h,i) in info.history" :key="i"><b>{{h.by}}</b> · {{vnDate(h.at)}} {{String(h.at).slice(11,16)}}<ul><li v-for="(c,j) in h.changes" :key="j">{{c.field}}: {{c.old===null||c.old===''?'(trống)':c.old}} → {{c.new===null||c.new===''?'(trống)':c.new}}</li></ul></li></ol>
  <p v-else class="land-empty">Chưa có thay đổi nào được ghi lại.</p>
 </section>

 <ModalForm v-model="editOpen" :title="'Sửa lô '+b.block_code" :busy="saving" width="860px" submit-label="Lưu lô" @submit="saveEdit">
  <FormGrid>
   <template v-for="f in editable.filter(f=>f.field!=='lotus_tree_count_source')" :key="f.field">
    <LotusField v-if="f.field==='variety'" v-model="form.variety" :label="f.label" :options="[...varieties,...(form.variety&&!varieties.includes(form.variety)?[form.variety]:[])]" :searchable="false" empty-option="Chưa có"/>
    <LotusField v-else-if="f.field==='active'" :model-value="form.active" :label="f.label" :options="activeOptions" :searchable="false" :empty-option="null" @update:model-value="value=>form.active=Number(value)"/>
    <LotusField v-else v-model="form[f.field]" :label="f.label" :type="kindOf(f)" :step="f.kind==='float'?'any':undefined" min="0"/>
   </template>
   <LotusField v-if="String(form.lotus_tree_count??'')!==String(b.lotus_tree_count??'')" v-model="form.lotus_tree_count_source" label="Nguồn số cây (bắt buộc khi đổi số cây)" wide required placeholder="VD: Bộ số cây đợt trước chốt 26/10/2026"/>
  </FormGrid>
 </ModalForm>
</article>
</template>
