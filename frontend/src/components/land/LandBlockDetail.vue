<script setup>
// One lot: overview (facts, plots, map, planned dates), work & materials, yield & losses, disease & bunch
// care, and the change history. Each tab loads its section of lotus_farm.farm_land.block_detail on open.
import {computed,defineAsyncComponent,reactive,ref,watch} from 'vue'
import {useRouter} from 'vue-router'
import LotusIcon from '../LotusIcon.vue'
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
   <table v-if="info.plots.length" class="land-mini"><thead><tr><th>Mã thửa</th><th>Tên</th><th class="num">Diện tích (ha)</th><th>Trạng thái</th><th></th></tr></thead>
    <tbody><tr v-for="p in info.plots" :key="p.name"><td><b>{{p.plot_code}}</b></td><td>{{p.plot_name}}</td><td class="num">{{num(p.area_ha,3)}}</td><td>{{p.active?'Đang dùng':'Ngừng'}}</td>
     <td class="land-row-actions"><UiButton variant="link" size="sm" @click="router.push('/plots/'+encodeURIComponent(p.name))">Lịch sử thửa ↗</UiButton><UiButton v-if="info.can_edit" variant="link" size="sm" @click="openPlot(p)">Sửa</UiButton></td></tr></tbody></table>
   <p v-else class="land-empty">Lô chưa chia thửa.</p>
   <p v-if="info.plots.length&&Math.abs(plotsArea-Number(b.area_ha||0))>0.05" class="land-warn">Tổng diện tích thửa {{num(plotsArea,2)}} ha khác diện tích lô {{num(b.area_ha,2)}} ha.</p>
  </div>
 </section>

 <section v-if="tab==='work'&&section.work" class="land-grid">
  <div class="land-card land-card--wide"><h3>Công việc đã làm</h3>
   <table v-if="section.work.work?.length" class="land-mini"><thead><tr><th>Công việc</th><th class="num">Khối lượng</th><th class="num">Công</th><th class="num">Số ngày</th><th>Gần nhất</th></tr></thead>
    <tbody><tr v-for="w in section.work.work" :key="w.work"><td>{{w.work}}</td><td class="num">{{num(w.qty,2)}} {{w.uom}}</td><td class="num">{{num(w.workdays,2)}}</td><td class="num">{{w.days}}</td><td>{{vnDate(w.last)}}</td></tr></tbody></table>
   <p v-else class="land-empty">{{section.work.work===null?'Bạn chưa có quyền xem kết quả công việc.':'Chưa có kết quả công việc đã duyệt của lô trong khoảng ngày này.'}}</p></div>
  <div class="land-card"><h3>Nhân công theo đội</h3>
   <table v-if="section.work.teams?.length" class="land-mini"><tbody><tr v-for="t in section.work.teams" :key="t.team"><td>{{t.team}}</td><td class="num">{{num(t.workdays,2)}} công</td></tr></tbody></table>
   <p v-else class="land-empty">Chưa bố trí nhân công cho lô.</p></div>
  <div class="land-card"><h3>Vật tư: định mức và đã dùng</h3>
   <table v-if="section.work.materials?.length" class="land-mini"><thead><tr><th>Vật tư</th><th class="num">Định mức</th><th class="num">Đã dùng</th><th class="num">Chênh</th></tr></thead>
    <tbody><tr v-for="m in section.work.materials" :key="m.item"><td>{{m.item_name}}<small> · {{m.uom}}</small></td><td class="num">{{num(m.required,2)}}</td><td class="num">{{num(m.consumed,2)}}</td><td class="num" :class="{'land-bad':m.required&&m.consumed>m.required*1.05}">{{m.required?num(m.consumed-m.required,2):'—'}}</td></tr></tbody></table>
   <p v-else class="land-empty">Chưa có nhu cầu hay sử dụng vật tư của lô.</p></div>
 </section>

 <section v-if="tab==='yield'&&section.yield" class="land-grid">
  <div class="land-card"><h3>Thu hoạch trong khoảng</h3>
   <template v-if="section.yield.harvest"><dl class="land-dl"><div><dt>Buồng</dt><dd>{{num(section.yield.harvest.bunches)}}</dd></div><div><dt>Khối lượng cân</dt><dd>{{num(section.yield.harvest.gross_kg)}} kg</dd></div><div><dt>Đạt bán</dt><dd>{{num(section.yield.harvest.saleable_kg)}} kg</dd></div></dl>
    <p v-if="!section.yield.harvest.rows.length" class="land-empty">Chưa có lượt thu hoạch đã duyệt.</p></template>
   <p v-else class="land-empty">Bạn chưa có quyền xem thu hoạch.</p></div>
  <div class="land-card"><h3>Dự thu</h3>
   <table v-if="section.yield.forecasts?.length" class="land-mini"><thead><tr><th>Kỳ</th><th class="num">Buồng</th><th class="num">Đạt bán (kg)</th><th>Trạng thái</th></tr></thead>
    <tbody><tr v-for="f in section.yield.forecasts" :key="f.name"><td>{{vnDate(f.period_start_date)}} – {{vnDate(f.period_end_date)}}</td><td class="num">{{num(f.expected_harvest_bunch_qty)}}</td><td class="num">{{num(f.saleable_forecast_kg)}}</td><td>{{f.supply_state||'—'}}</td></tr></tbody></table>
   <p v-else class="land-empty">Chưa có dự thu cho lô.</p></div>
  <div class="land-card"><header class="land-card__head"><h3>Hủy buồng theo nguyên nhân</h3><UiButton variant="link" size="sm" @click="go('losses')">Hủy & tổn thất ↗</UiButton></header>
   <table v-if="section.yield.cancellations?.length" class="land-mini"><tbody><tr v-for="c in section.yield.cancellations" :key="c.reason"><td>{{c.reason}}</td><td class="num">{{num(c.bunches)}} buồng</td></tr></tbody></table>
   <p v-else class="land-empty">Không có buồng hủy trong khoảng ngày này.</p></div>
  <div class="land-card"><header class="land-card__head"><h3>Đo trái gần nhất</h3><UiButton variant="link" size="sm" @click="go('measurements')">Đo trái ↗</UiButton></header>
   <table v-if="section.yield.measurements?.length" class="land-mini"><thead><tr><th>Ngày</th><th class="num">Mẫu</th><th class="num">Dài TB</th><th class="num">Đường kính TB</th></tr></thead>
    <tbody><tr v-for="(m,i) in section.yield.measurements" :key="i"><td>{{vnDate(m.posting_date)}}</td><td class="num">{{m.sample_count}}</td><td class="num">{{num(m.average_length,1)}} {{m.uom}}</td><td class="num">{{num(m.average_diameter,1)}}</td></tr></tbody></table>
   <p v-else class="land-empty">Chưa có lần đo trái của lô.</p></div>
 </section>

 <section v-if="tab==='care'&&section.care" class="land-grid">
  <div class="land-card"><h3>Bệnh ghi nhận</h3>
   <table v-if="section.care.diseases?.length" class="land-mini"><thead><tr><th>Bệnh</th><th class="num">Lần</th><th class="num">Cây bị</th><th>Mức gần nhất</th><th>Gần nhất</th></tr></thead>
    <tbody><tr v-for="d in section.care.diseases" :key="d.disease"><td>{{d.disease}}</td><td class="num">{{d.observations}}</td><td class="num">{{num(d.plants)}}</td><td>{{d.severity||'—'}}</td><td>{{vnDate(d.last)}}</td></tr></tbody></table>
   <p v-else class="land-empty">Không có ghi nhận bệnh trong khoảng ngày này.</p></div>
  <div class="land-card"><h3>Chăm sóc buồng theo tuần</h3>
   <table v-if="section.care.operations?.length" class="land-mini"><thead><tr><th>Tuần từ</th><th>Thao tác</th><th class="num">Buồng</th></tr></thead>
    <tbody><tr v-for="o in section.care.operations" :key="o.week+o.operation"><td>{{vnDate(o.week)}}</td><td>{{OPERATIONS[o.operation]||o.operation}}</td><td class="num">{{num(o.bunches)}}</td></tr></tbody></table>
   <p v-else class="land-empty">Chưa có thao tác buồng trong khoảng ngày này.</p></div>
  <div class="land-card land-card--wide"><h3>Trồng / trồng dặm</h3>
   <table v-if="section.care.planting?.length" class="land-mini"><thead><tr><th>Ngày</th><th>Loại</th><th class="num">Số cây</th><th class="num">Diện tích</th><th>Ghi chú</th></tr></thead>
    <tbody><tr v-for="(p,i) in section.care.planting" :key="i"><td>{{vnDate(p.posting_date)}}</td><td>{{PLANTING[p.event_type]||p.event_type}}</td><td class="num">{{num(p.plant_qty)}}</td><td class="num">{{num(p.area_ha,2)}} ha</td><td>{{p.notes}}</td></tr></tbody></table>
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
