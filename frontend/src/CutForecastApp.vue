<script setup>
// /lotus/forecast — Dự thu theo nhật ký chặt mẹ lần 2: tiles, tonnes by harvest month, stage table
// (trổ buồng → chích bắp → cắt bắp → thu hoạch → đóng gói), zones, the journal with each wave's dates,
// the parameter versions and the Excel upload. Data: lotus_farm.cut_forecast. The previous forecast page
// (OneDrive, 36 tháng, VIP126) stays at /forecast-onedrive.
import {computed,onMounted,ref,watch} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import LotusIcon from './components/LotusIcon.vue'
import LotusChart from './components/LotusChart.vue'
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
const TABS=[['overview','Tổng quan'],['journal','Nhật ký & lịch từng đợt'],['params','Thông số & lần nhập']]
const route=useRoute(),router=useRouter(),session=useSession()
const {open:confirmOpen,title:confirmTitle,message:confirmMessage,ask,finish:finishConfirm}=useWorkspaceConfirm()
const data=ref(null),busy=ref(false),error=ref(''),notice=ref(''),tab=ref('overview')
const importOpen=ref(false),preview=ref(null),saving=ref(false),applyParams=ref(true),fileName=ref('')
const form=ref({}),formNote=ref(''),journalWave=ref(''),journalLimit=ref(200)
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
function setScope(next){router.push({path:'/forecast',query:{...route.query,...next}})}
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
async function saveProfile(){saving.value=true
 try{const r=await call('lotus_farm.cut_forecast.save_profile',{farm:farm.value,values:JSON.stringify(form.value),notes:formNote.value||null},true)
  notice.value='Đã lưu thông số phiên bản '+r.version+'. Dự thu đã tính lại.';await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
async function undo(batch){
 if(!await ask('Xóa '+num(batch.new_rows)+' dòng nhật ký mà lần nhập "'+batch.file_name+'" đã thêm? File gốc vẫn được giữ làm chứng cứ.','Hoàn tác lần nhập'))return
 saving.value=true
 try{const r=await call('lotus_farm.cut_forecast.undo_import',{farm:farm.value,batch:batch.name},true);notice.value='Đã xóa '+num(r.removed)+' dòng nhật ký.';await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
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
   <div class="land-table cutfc-table"><table><thead><tr><th>Tháng</th><th class="num">Trổ buồng (cây)</th><th class="num">Chích bắp</th><th class="num">Cắt bắp</th><th class="num">Thu hoạch</th><th class="num">Đóng gói</th><th class="num">Tấn sơ chế</th></tr></thead>
    <tbody><tr v-for="m in data.months" :key="m.month" :class="{past:m.month<thisMonth,now:m.month===thisMonth}"><td><b>{{monthLabel(m.month)}}</b><small v-if="m.month<thisMonth">đã qua</small><small v-else-if="m.month===thisMonth">tháng này</small></td>
     <td class="num">{{num(m.shoot)}}</td><td class="num">{{num(m.inject)}}</td><td class="num">{{num(m.budcut)}}</td><td class="num">{{num(m.harvest)}}</td><td class="num">{{num(m.pack)}}</td><td class="num"><b>{{num(m.tonnes,2)}}</b></td></tr></tbody>
    <tfoot><tr><th>Tổng</th><th class="num">{{num(t.shoot)}}</th><th class="num">{{num(t.inject)}}</th><th class="num">{{num(t.budcut)}}</th><th class="num">{{num(t.harvest)}}</th><th class="num">{{num(t.pack)}}</th><th class="num">{{num(t.tonnes,2)}}</th></tr></tfoot></table></div>
  </section>

  <section v-if="t" class="land-card">
   <h3>Theo khu</h3>
   <div class="land-table cutfc-table"><table><thead><tr><th>Khu</th><th>Ngày chặt</th><th class="num">Cây mẹ chặt 2</th><th class="num">Trổ buồng</th><th class="num">Cắt bắp</th><th class="num">Thu hoạch</th><th class="num">Đóng gói</th><th class="num">Tấn sơ chế</th></tr></thead>
    <tbody><tr v-for="z in data.zones" :key="z.zone" class="clickable" @click="setScope({zone:zone===z.zone?undefined:z.zone})"><td><b>Khu {{z.zone}}</b></td><td>{{vnDate(z.first_cut)}} – {{vnDate(z.last_cut)}}<small>{{z.entries}} dòng</small></td>
     <td class="num">{{num(z.trees)}}</td><td class="num">{{num(z.shoot)}}</td><td class="num">{{num(z.budcut)}}</td><td class="num">{{num(z.harvest)}}</td><td class="num">{{num(z.pack)}}</td><td class="num"><b>{{num(z.tonnes,2)}}</b></td></tr></tbody></table></div>
   <h3 class="cutfc-sub">Tấn sơ chế theo khu và tháng thu</h3>
   <div class="land-table cutfc-table"><table><thead><tr><th>Khu</th><th v-for="m in zoneMonthCols" :key="m" class="num">{{monthLabel(m)}}</th></tr></thead>
    <tbody><tr v-for="z in data.zones" :key="z.zone"><td><b>{{z.zone}}</b></td><td v-for="m in zoneMonthCols" :key="m" class="num">{{data.zone_months[z.zone]?.[m]?num(data.zone_months[z.zone][m],1):'—'}}</td></tr></tbody></table></div>
  </section>
 </template>

 <section v-else-if="tab==='journal'" class="land-card">
  <div class="land-filters"><UiSelect v-model="journalWave" aria-label="Lọc đợt trổ" class="cutfc-narrow"><option value="">Mọi đợt trổ</option><option v-for="k in [1,2,3,4]" :key="k" :value="String(k)">Đợt {{k}}</option></UiSelect>
   <span class="land-spacer"></span><span class="land-count">{{num(journal.length)}} dòng (mỗi dòng chặt tách thành 4 đợt trổ)</span></div>
  <div class="land-table cutfc-table cutfc-journal"><table><thead><tr><th>Khu</th><th>Ngày chặt mẹ 2</th><th class="num">Cây mẹ</th><th class="num">Đợt</th><th class="num">Số cây trổ</th><th>Cửa sổ trổ</th><th>Trổ (đại diện)</th><th>Chích bắp</th><th>Cắt bắp</th><th class="num">Buồng cắt</th><th>Thu hoạch</th><th class="num">Buồng thu</th><th class="num">Đóng gói</th><th class="num">Kg sơ chế</th><th>Dòng nguồn</th></tr></thead>
   <tbody><tr v-for="r in journal.slice(0,journalLimit)" :key="(r.entry||r.source_ref)+r.wave"><td>{{r.zone}}</td><td>{{vnDate(r.cut_date)}}</td><td class="num">{{num(r.tree_qty)}}</td><td class="num">{{r.wave}} <small>{{pct(r.share)}}%</small></td><td class="num">{{num(r.shoot_qty)}}</td>
    <td>{{vnDate(r.shoot_from)}} – {{vnDate(r.shoot_to)}}</td><td>{{vnDate(r.shoot_date)}}</td><td>{{vnDate(r.inject_date)}}</td><td>{{vnDate(r.budcut_date)}}</td><td class="num">{{num(r.budcut_qty)}}</td><td>{{vnDate(r.harvest_date)}}</td><td class="num">{{num(r.harvest_qty)}}</td><td class="num">{{num(r.pack_qty)}}</td><td class="num">{{num(r.kg)}}</td><td><small>{{r.source_ref}}</small></td></tr></tbody></table>
   <p v-if="!journal.length&&!busy" class="land-empty">Chưa có nhật ký chặt mẹ lần 2.</p></div>
  <UiButton v-if="journal.length>journalLimit" variant="outline" @click="journalLimit+=400">Xem thêm ({{num(journal.length-journalLimit)}} dòng)</UiButton>
 </section>

 <template v-else>
  <section class="land-card">
   <div class="land-card__head"><h3>Thông số dự thu <small v-if="data?.profile">· đang dùng phiên bản {{data.profile.version}} ({{data.profile.source==='Excel'?'từ file Excel':'sửa trên web'}}, {{vnDate(String(data.profile.approved_at||'').slice(0,10))}})</small></h3></div>
   <p class="land-note">Đợt cuối nhận phần cây còn lại, nên tổng 4 tỷ lệ phải bằng 100%. Lưu là tạo phiên bản mới; các phiên bản cũ được giữ lại để đối chiếu.</p>
   <form class="land-form--grid cutfc-params" @submit.prevent="saveProfile">
    <label v-for="[field,label,kind] in params" :key="field">{{label}}<span class="cutfc-input"><UiInput type="number" :step="kind==='days'?1:kind==='rate'?0.01:0.1" min="0" :disabled="!data?.can_edit||saving" :model-value="formValue(field,kind)" @update:model-value="setForm(field,kind,$event)"/><em>{{kind==='days'?'ngày':kind==='rate'?'%':kind==='kg'?'kg':'chồi'}}</em></span></label>
    <p class="land-form__full" :class="Math.abs(waveTotal-1)>1e-6?'land-bad':'land-note'">Tổng 4 đợt trổ: {{num(waveTotal*100,2)}}%</p>
    <label v-if="data?.can_edit" class="land-form__full">Ghi chú thay đổi<UiInput v-model="formNote" placeholder="VD: đổi mốc trổ đợt 1 thành 180 ngày theo khảo sát khu A"/></label>
    <div v-if="data?.can_edit" class="land-actions land-form__full"><UiButton type="button" variant="outline" :disabled="saving" @click="resetForm">Đặt lại</UiButton><UiButton type="submit" :disabled="saving||Math.abs(waveTotal-1)>1e-6">{{saving?'Đang lưu…':'Lưu thành phiên bản mới'}}</UiButton></div>
   </form>
  </section>
  <section class="land-card">
   <h3>Các phiên bản thông số</h3>
   <div class="land-table cutfc-table"><table><thead><tr><th>Phiên bản</th><th>Nguồn</th><th>Người duyệt</th><th>Lúc</th><th class="num">Trổ đợt 1</th><th class="num">Cắt bắp</th><th class="num">Thu</th><th class="num">Đóng gói</th><th class="num">Kg/buồng</th><th>Ghi chú</th></tr></thead>
    <tbody><tr v-for="p in data?.profiles||[]" :key="p.name"><td><b>{{p.version}}</b><small v-if="p.name===data.profile?.name">đang dùng</small></td><td>{{p.source==='Excel'?'File Excel':'Web'}}</td><td>{{p.approved_by||'—'}}</td><td>{{vnDate(String(p.approved_at||'').slice(0,10))}}</td>
     <td class="num">{{p.days_to_first_shoot}} ngày</td><td class="num">{{pct(p.cut_rate)}}%</td><td class="num">{{pct(p.harvest_rate)}}%</td><td class="num">{{pct(p.pack_rate)}}%</td><td class="num">{{num(p.kg_per_bunch,1)}}</td><td>{{p.notes||''}}</td></tr></tbody></table>
    <p v-if="!(data?.profiles||[]).length" class="land-empty">Chưa có phiên bản nào. Nhập file Excel dự thu hoặc lưu thông số ở trên.</p></div>
  </section>
  <section class="land-card">
   <h3>Các lần nhập file</h3>
   <div class="land-table cutfc-table"><table><thead><tr><th>File</th><th class="num">Dòng mới</th><th class="num">Đã có</th><th class="num">Xung đột / lỗi</th><th class="num">Số cây</th><th>Người nhập</th><th>Lúc</th><th></th></tr></thead>
    <tbody><tr v-for="b in data?.imports||[]" :key="b.name" :class="{inactive:b.undone_at}"><td><a v-if="b.source_file" :href="b.source_file" target="_blank" rel="noopener">{{b.file_name}}</a><template v-else>{{b.file_name}}</template><small>SHA-256 {{String(b.sha256||'').slice(0,12)}}…</small></td>
     <td class="num">{{num(b.new_rows)}}</td><td class="num">{{num(b.existing_rows)}}</td><td class="num">{{num(b.conflict_rows)}} / {{num(b.error_rows)}}</td><td class="num">{{num(b.trees)}}</td><td>{{b.imported_by}}</td><td>{{vnDate(String(b.imported_at||'').slice(0,10))}}</td>
     <td class="land-row-actions"><small v-if="b.undone_at">đã hoàn tác</small><UiButton v-else-if="data.can_edit&&b.new_rows" size="sm" variant="ghost" :disabled="saving" @click="undo(b)">Hoàn tác</UiButton></td></tr></tbody></table>
    <p v-if="!(data?.imports||[]).length" class="land-empty">Chưa nhập file nào.</p></div>
  </section>
 </template>

 <WorkspaceModal v-model="importOpen" title="Nhập file dự thu" :busy="saving" width="980px">
  <div class="land-form">
   <ol class="land-steps"><li>Chọn file Excel dự thu có sheet <b>NHẬT KÝ GỐC</b> (Khu | Ngày chặt mẹ lần 2 | Số cây | Dòng trên file nguồn) và sheet <b>THÔNG SỐ</b>.</li><li>Xem trước: dòng mới được thêm, dòng đã nhập trước đây bỏ qua, dòng khác số cây so với lần trước được báo để kiểm tra.</li><li>Bấm Nhập. File gốc được lưu lại làm chứng cứ.</li></ol>
   <label class="land-file">File Excel<input type="file" accept=".xlsx" :disabled="saving" @change="readFile"></label>
   <template v-if="preview">
    <p><b>{{num(preview.new)}}</b> dòng mới ({{num(preview.new_trees)}} cây) · {{num(preview.same)}} dòng đã có · <span :class="{'land-bad':preview.conflict}">{{num(preview.conflict)}} dòng khác số cây</span> · <span :class="{'land-bad':preview.errors}">{{num(preview.errors)}} dòng lỗi</span></p>
    <p v-if="preview.file_totals" class="land-note">Theo thông số trong file: {{num(preview.file_totals.trees)}} cây → {{num(preview.file_totals.pack)}} buồng đóng gói → <b>{{num(preview.file_totals.tonnes,1)}} tấn sơ chế</b>.</p>
    <div v-if="preview.param_errors.length" class="land-bad"><div v-for="e in preview.param_errors" :key="e">Thông số trong file: {{e}}</div></div>
    <template v-else-if="preview.param_changes.length">
     <label class="cutfc-check"><input v-model="applyParams" type="checkbox">Dùng thông số trong file làm phiên bản mới{{preview.has_profile?' (thay phiên bản đang dùng)':''}}</label>
     <div class="land-table land-preview"><table><thead><tr><th>Thông số</th><th class="num">Đang dùng</th><th class="num">Trong file</th></tr></thead>
      <tbody><tr v-for="c in preview.param_changes" :key="c.field"><td>{{c.label}}</td><td class="num">{{c.old??'—'}}</td><td class="num"><b>{{c.new}}</b></td></tr></tbody></table></div>
    </template>
    <div v-if="preview.rows.some(r=>r.state!=='new'&&r.state!=='same')" class="land-table land-preview"><table><thead><tr><th>Dòng</th><th>Khu</th><th>Ngày</th><th class="num">Số cây</th><th>Tình trạng</th></tr></thead>
     <tbody><tr v-for="r in preview.rows.filter(r=>r.state==='conflict'||r.state==='error')" :key="r.line" :class="{bad:r.state==='error'}"><td>{{r.line}}</td><td>{{r.zone||''}}</td><td>{{vnDate(r.cut_date)}}</td><td class="num">{{r.tree_qty!=null?num(r.tree_qty):''}}</td>
      <td><span v-if="r.state==='conflict'" class="land-warn">Đã nhập {{num(r.old_qty)}} cây, file ghi {{num(r.tree_qty)}} cây — giữ số cũ, kiểm tra lại</span><div v-for="e in r.errors||[]" :key="e" class="land-bad">{{e}}</div></td></tr></tbody></table></div>
    <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="importOpen=false">Hủy</UiButton><UiButton type="button" :disabled="saving||(!preview.new&&!(applyParams&&preview.param_changes.length))" @click="commitImport">{{saving?'Đang nhập…':'Nhập '+num(preview.new)+' dòng'+(applyParams&&preview.param_changes.length?' và thông số':'')}}</UiButton></div>
   </template>
  </div>
 </WorkspaceModal>
 <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" @answer="finishConfirm"/>
</section>
</template>
