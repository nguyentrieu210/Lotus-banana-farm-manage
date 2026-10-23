<script setup>
import {computed,onBeforeUnmount,onMounted,ref} from 'vue'
import {useRouter} from 'vue-router'
import {call} from '../../api'
import {useSession} from '../../store'
import {useWorkspaceConfirm} from '../../use-workspace-confirm'
import {budgetFields,factorFields,formatMonth,formatNumber,resizeRows,newPlan,compareResults,resultCsv} from '../../financial-planning'
import DataTable from '../DataTable.vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import WorkspaceConfirm from '../WorkspaceConfirm.vue'
import {Button} from '../ui/button'
import {Input} from '../ui/input'
import {FormField} from '../ui/form-field'
import {Combobox} from '../ui/combobox'
import {Textarea} from '../ui/textarea'
import '../../financial-planning.css'

const emit=defineEmits(['notice'])
const API='lotus_farm.finance.planning.'
const session=useSession(),router=useRouter()
const overview=ref(null),current=ref(null),values=ref(null),result=ref(null),calculated=ref(''),saved=ref('')
const busy=ref(false),saving=ref(false),error=ref(''),editor=ref(''),form=ref({}),formError=ref(''),proposal=ref(null),view=ref('budget'),query=ref('')
const {open:confirmOpen,title:confirmTitle,message:confirmMessage,ask,finish}=useWorkspaceConfirm()
let requestKey=crypto.randomUUID(),previewVersion=0
const json=value=>JSON.stringify(value)
const clone=value=>JSON.parse(json(value))
const dirty=computed(()=>!!values.value&&json(values.value)!==saved.value)
const fresh=computed(()=>!!result.value&&calculated.value===json(values.value))
const locked=computed(()=>current.value?.state==='Approved')
const canWrite=computed(()=>!!overview.value?.can_write&&!locked.value)
const planOptions=computed(()=>(overview.value?.plans||[]).map(r=>({value:r.name,label:r.title,subtitle:formatMonth(r.start_month)+' · '+(r.farm||'Toàn công ty')+' · '+(r.state==='Approved'?'Đã duyệt':'Nháp')})))
const farmOptions=computed(()=>[{value:'',label:'Toàn công ty'},...(overview.value?.farms||[]).map(r=>({value:r.name,label:r.farm_name||r.name}))])
const rows=computed(()=>(values.value?.rows||[]).filter(r=>!query.value||formatMonth(r.month).includes(query.value)))
const totals=computed(()=>fresh.value?result.value.scenario.totals:null)
const comparison=computed(()=>fresh.value?compareResults(result.value):[])
const col=(field,headerName,extra={})=>({field,headerName,minWidth:145,type:'numericColumn',valueFormatter:p=>formatNumber(p.value,field.endsWith('_kg')?3:0),...extra})
const monthCol={field:'month',headerName:'Tháng',pinned:'left',minWidth:115,valueFormatter:p=>formatMonth(p.value)}
const budgetColumns=[monthCol,...budgetFields.map(([field,label])=>col(field,label))]
const resultColumns=[monthCol,col('gross_kg','Thu hoạch (kg)'),col('sales_kg','Thành phẩm bán (kg)'),col('revenue','Doanh thu (đ)'),col('operating_cost','Chi phí hoạt động (đ)'),col('depreciation','Khấu hao (đ)'),col('interest','Lãi vay (đ)'),col('tax','Thuế dự kiến (đ)'),col('profit','Lợi nhuận (đ)'),col('opening_cash','Tiền đầu tháng (đ)'),col('cash_in','Thu (đ)'),col('cash_out','Chi (đ)'),col('closing_cash','Tiền cuối tháng (đ)',{cellClass:p=>p.value<0?'fp-negative':''}),col('funding_gap','Thiếu vốn (đ)')]
const comparisonColumns=[{field:'label',headerName:'Chỉ tiêu',minWidth:285,flex:2},col('base','Cơ sở'),col('scenario','Kịch bản'),col('difference','Chênh lệch')]
const sourceColumns=[{field:'name',headerName:'Phiếu dự thu',minWidth:180},monthCol,{field:'farm',headerName:'Vườn',minWidth:150},{field:'farm_block',headerName:'Lô',minWidth:130},col('gross_kg','Thu hoạch (kg)'),col('sales_kg','Thành phẩm (kg)')]
const snapshot=computed(()=>current.value?.source_snapshot||{})
async function task(fn){busy.value=true;error.value='';try{return await fn()}catch(e){error.value=e.message||String(e)}finally{busy.value=false}}
async function mutate(fn,message){saving.value=true;error.value='';try{const doc=await fn();accept(doc);await loadOverview();if(message)emit('notice',message);return doc}catch(e){error.value=e.message||String(e)}finally{saving.value=false}}
function accept(doc){current.value=doc;values.value=clone(doc.values);result.value=doc.result;saved.value=json(values.value);calculated.value=saved.value;proposal.value=null;editor.value='';requestKey=crypto.randomUUID();previewVersion++}
async function loadOverview(){overview.value=await call(API+'overview')}
async function choose(name){if(!name||busy.value||saving.value||name===current.value?.name)return;if(dirty.value&&!await ask('Bỏ các thay đổi chưa lưu để mở kế hoạch khác?'))return;await task(async()=>accept(await call(API+'detail',{name})))}
async function reload(){if(dirty.value&&!await ask('Tải lại bản đã lưu và bỏ các thay đổi chưa lưu?'))return;await task(async()=>{await loadOverview();accept(await call(API+'detail',{name:current.value.name}))})}
async function calculate(){if(locked.value)return;const version=++previewVersion,args=json(values.value);await task(async()=>{const output=await call(API+'preview',{values:args},true);if(version===previewVersion&&args===json(values.value)){result.value=output;calculated.value=args}})}
function openSettings(create=false){form.value=clone(create?newPlan(session.today||new Date().toISOString().slice(0,10)):values.value);if(create)requestKey=crypto.randomUUID();formError.value='';editor.value=create?'create':'settings'}
async function settingsSubmit(){
 const next={...form.value,month_count:Number(form.value.month_count),collection_delay:Number(form.value.collection_delay),payment_delay:Number(form.value.payment_delay)}
 next.rows=resizeRows(next)
 if(!next.rows.length){formError.value='Chọn tháng bắt đầu và số tháng từ 1 đến 36.';return}
 if(editor.value==='create'){
  saving.value=true;formError.value=''
  try{const doc=await call(API+'save',{values:json(next),request_key:requestKey},true);accept(doc);await loadOverview();emit('notice','Đã tạo kế hoạch tài chính.')}
  catch(e){formError.value=e.message||String(e)}finally{saving.value=false}
 }else{
  if(values.value.rows.some(r=>!next.rows.some(n=>n.month===r.month)&&budgetFields.some(([f])=>Number(r[f])))&&!await ask('Đổi kỳ sẽ bỏ ngân sách các tháng ngoài khoảng mới. Tiếp tục?'))return
  values.value=next;editor.value='';await calculate()
 }
}
function editMonth(row){if(!canWrite.value)return;form.value=clone(row);formError.value='';editor.value='month'}
async function monthSubmit(){
 const row={month:form.value.month,...Object.fromEntries(budgetFields.map(([key])=>[key,Number(form.value[key]||0)]))}
 if(budgetFields.some(([f])=>!Number.isFinite(row[f])||row[f]<0)){formError.value='Nhập số không âm cho sản lượng và ngân sách.';return}
 if(row.sales_kg>row.gross_kg){formError.value='Kg thành phẩm bán không được vượt kg thu hoạch.';return}
 values.value.rows=values.value.rows.map(r=>r.month===row.month?row:r);editor.value='';await calculate()
}
async function copyMonth(){
 if(!await ask('Áp dụng ngân sách tháng '+formatMonth(form.value.month)+' cho các tháng còn lại? Sản lượng từng tháng giữ nguyên.'))return
 const keys=budgetFields.map(([f])=>f).filter(f=>!['gross_kg','sales_kg'].includes(f))
 if(keys.some(f=>!Number.isFinite(Number(form.value[f]))||Number(form.value[f])<0)){formError.value='Ngân sách phải là số không âm.';return}
 values.value.rows=values.value.rows.map(row=>({...row,...Object.fromEntries(keys.map(f=>[f,Number(form.value[f]||0)]))}));editor.value='';await calculate()
}
async function save(){await mutate(()=>call(API+'save',{name:current.value.name,modified:current.value.modified,values:json(values.value)},true),'Đã lưu kế hoạch tài chính.')}
async function approve(){if(!await ask('Duyệt và khóa kế hoạch này? Muốn thay đổi sau đó cần nhân bản phương án mới.','Duyệt kế hoạch'))return;await mutate(()=>call(API+'approve',{name:current.value.name,modified:current.value.modified},true),'Đã duyệt kế hoạch tài chính.')}
async function duplicate(){if(dirty.value&&!await ask('Nhân bản bản đã lưu? Các thay đổi chưa lưu sẽ được bỏ.'))return;await mutate(()=>call(API+'duplicate',{name:current.value.name,request_key:requestKey},true),'Đã nhân bản thành phương án mới.')}
async function importPreview(){await task(async()=>{proposal.value=await call(API+'forecast_preview',{name:current.value.name});editor.value='import'})}
async function applyForecast(){await mutate(()=>call(API+'apply_forecast',{name:current.value.name,modified:current.value.modified,fingerprint:proposal.value.fingerprint},true),'Đã thay sản lượng từ dự thu đã phát hành.')}
function exportCsv(){const blob=new Blob([resultCsv(result.value.scenario)],{type:'text/csv;charset=utf-8;'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=current.value.name+'-du-phong.csv';link.click();URL.revokeObjectURL(url)}
const stopGuard=router.beforeEach(async(to,from)=>{if(from.path==='/tai-chinh'&&from.query.tab==='planning'&&(to.path!==from.path||to.query.tab!=='planning')&&dirty.value)return await ask('Kế hoạch còn thay đổi chưa lưu. Rời trang và bỏ thay đổi?');return true})
onBeforeUnmount(()=>{stopGuard();previewVersion++})
onMounted(()=>task(async()=>{await loadOverview();if(overview.value.plans.length)accept(await call(API+'detail',{name:overview.value.plans[0].name}))}))
</script>

<template>
 <section class="fp" aria-label="Kế hoạch tài chính">
  <p v-if="error" class="stock-error" role="alert">{{error}}</p>
  <div class="fp-toolbar">
   <Combobox :model-value="current?.name||''" :options="planOptions" aria-label="Chọn kế hoạch" placeholder="Tìm kế hoạch…" :disabled="busy||saving" @update:model-value="choose"/>
   <span v-if="current" class="fp-state">{{locked?'Đã duyệt':'Nháp'}}{{dirty?' · Chưa lưu':''}}</span>
   <Button v-if="current" variant="outline" :disabled="busy||saving" @click="reload">Làm mới</Button>
   <Button v-if="overview?.can_write" variant="outline" :disabled="busy||saving||dirty" @click="openSettings(true)">Tạo kế hoạch</Button>
   <Button v-if="current&&overview?.can_write" variant="outline" :disabled="busy||saving" @click="duplicate">Nhân bản</Button>
   <Button v-if="current&&canWrite" :disabled="busy||saving||!dirty" @click="save">{{saving?'Đang lưu…':'Lưu kế hoạch'}}</Button>
   <Button v-if="current&&canWrite&&overview?.can_approve" variant="outline" :disabled="busy||saving||dirty" @click="approve">Duyệt kế hoạch</Button>
  </div>
  <p v-if="busy" role="status">Đang tải kế hoạch…</p>
  <p v-if="!current&&!busy" class="land-empty">Chưa có kế hoạch tài chính. Tạo kế hoạch để nhập sản lượng và ngân sách theo tháng.</p>
  <template v-if="values">
   <div class="fp-toolbar">
    <nav class="land-views" aria-label="Nội dung kế hoạch"><button v-for="[id,label] in [['budget','Sản lượng & ngân sách'],['projection','Dự phóng & dòng tiền'],['sources','Nguồn dự thu']]" :key="id" type="button" :class="{on:view===id}" :aria-current="view===id?'page':undefined" @click="view=id">{{label}}</button></nav>
    <Button v-if="canWrite" variant="outline" :disabled="busy||saving" @click="openSettings()">Giả định & kỳ kế hoạch</Button>
    <Button v-if="canWrite&&overview?.can_forecast" variant="outline" :disabled="busy||saving||dirty" @click="importPreview">Lấy sản lượng dự thu</Button>
    <Button variant="outline" :disabled="busy||saving||!fresh" @click="exportCsv">Xuất CSV</Button>
   </div>
   <p v-if="!fresh" class="land-warn" role="status">Dữ liệu đã thay đổi. Bấm Tính dự phóng để cập nhật kết quả.</p>
   <div v-if="totals" class="land-stats fp-stats">
    <div><span>Thành phẩm bán (kg)</span><strong>{{formatNumber(totals.sales_kg,3)}}</strong></div>
    <div><span>Doanh thu dự kiến</span><strong>{{formatNumber(totals.revenue)}} đ</strong></div>
    <div><span>Lợi nhuận kế hoạch</span><strong :class="{'fp-negative':totals.profit<0}">{{formatNumber(totals.profit)}} đ</strong></div>
    <div><span>Tiền cuối kỳ</span><strong :class="{'fp-negative':totals.closing_cash<0}">{{formatNumber(totals.closing_cash)}} đ</strong></div>
    <div><span>Thiếu vốn cao nhất</span><strong :class="{'fp-negative':totals.funding_gap>0}">{{formatNumber(totals.funding_gap)}} đ</strong></div>
   </div>
   <p v-for="warning in fresh?result.scenario.warnings:[]" :key="warning" class="land-warn">{{warning}}</p>
   <template v-if="view==='budget'">
    <div class="fp-toolbar"><FormField label="Tìm tháng" v-slot="field"><Input v-bind="field" v-model="query" placeholder="mm/yyyy"/></FormField><Button variant="outline" :disabled="busy||saving||locked" @click="calculate">Tính dự phóng</Button></div>
    <DataTable :rows="rows" :columns="budgetColumns" row-key="month" storage-key="financial-plan-budget" :interactive="canWrite" @open="editMonth" empty="Không có tháng phù hợp."/>
   </template>
   <template v-else-if="view==='projection'">
    <div class="fp-toolbar fp-factors"><FormField v-for="[key,label] in factorFields" :key="key" :label="label" v-slot="field"><Input v-bind="field" v-model.number="values[key]" type="number" min="0" max="300" step="0.1" :disabled="!canWrite"/></FormField><Button variant="outline" :disabled="busy||saving||locked" @click="calculate">Tính dự phóng</Button></div>
    <template v-if="fresh"><DataTable :rows="comparison" :columns="comparisonColumns" row-key="key" storage-key="financial-plan-comparison"/><DataTable :rows="result.scenario.rows" :columns="resultColumns" row-key="month" storage-key="financial-plan-projection"/></template>
    <details class="fp-assumptions"><summary>Quy tắc tính và thời điểm thu / chi</summary><p>Giá chưa VAT. Thành phẩm khai báo được bán trong tháng; ngân sách sản xuất tính vào chi phí tháng đó. Chưa mô phỏng tồn kho và dở dang. Cơ sở dùng tỷ lệ 100%; kịch bản đổi sản lượng, giá bán và đơn giá đóng gói / vận chuyển, giữ ngân sách cố định.</p><p>Thu doanh thu chậm {{values.collection_delay}} tháng, trả chi phí hoạt động chậm {{values.payment_delay}} tháng. Lãi vay, thuế, đầu tư và trả gốc chi trong tháng khai báo. Khấu hao không chi tiền; vốn vào không tính doanh thu. Công nợ trước kỳ nhập vào thu / chi khác. Thuế là ngân sách do người lập nhập.</p></details>
   </template>
   <template v-else>
    <p v-if="!snapshot.sources?.length" class="land-empty">Chưa lấy sản lượng từ dự thu. Sản lượng đang nhập thủ công.</p>
    <template v-else><p class="fp-provenance">Lấy nguồn lúc {{snapshot.imported_at}} · {{snapshot.imported_by}}. Sản lượng hiện tại có thể đã được điều chỉnh trong ngân sách.</p><p v-for="warning in snapshot.warnings" :key="warning" class="land-warn">{{warning}}</p><DataTable :rows="snapshot.sources" :columns="sourceColumns" row-key="name" storage-key="financial-plan-sources"/></template>
   </template>
  </template>

  <WorkspaceModal :model-value="['create','settings'].includes(editor)" :title="editor==='create'?'Tạo kế hoạch tài chính':'Giả định & kỳ kế hoạch'" :busy="saving" width="760px" @update:model-value="v=>!v&&!saving&&(editor='')">
   <form class="fp-form" @submit.prevent="settingsSubmit">
    <p v-if="formError" class="stock-error" role="alert">{{formError}}</p>
    <FormField label="Tên kế hoạch" required v-slot="field"><Input v-bind="field" v-model="form.title" maxlength="140"/></FormField>
    <FormField label="Vườn" v-slot="field"><Combobox v-bind="field" v-model="form.farm" :options="farmOptions"/></FormField>
    <div class="fp-fields"><FormField label="Tháng bắt đầu" required v-slot="field"><Input v-bind="field" v-model="form.start_month" type="month"/></FormField><FormField label="Số tháng" required v-slot="field"><Input v-bind="field" v-model.number="form.month_count" type="number" min="1" max="36" step="1"/></FormField><FormField label="Tiền đầu kỳ (đ)" v-slot="field"><Input v-bind="field" v-model.number="form.opening_cash" type="number" step="1"/></FormField><FormField label="Chậm thu doanh thu (tháng)" v-slot="field"><Input v-bind="field" v-model.number="form.collection_delay" type="number" min="0" max="12" step="1"/></FormField><FormField label="Chậm trả chi phí hoạt động (tháng)" v-slot="field"><Input v-bind="field" v-model.number="form.payment_delay" type="number" min="0" max="12" step="1"/></FormField></div>
    <FormField label="Ghi chú giả định" v-slot="field"><Textarea v-bind="field" v-model="form.notes" rows="3" maxlength="4000"/></FormField>
    <div class="fp-toolbar"><Button type="button" variant="outline" :disabled="saving" @click="editor=''">Hủy</Button><Button type="submit" :disabled="saving">{{saving?'Đang lưu…':editor==='create'?'Tạo kế hoạch':'Áp dụng giả định'}}</Button></div>
   </form>
  </WorkspaceModal>
  <WorkspaceModal :model-value="editor==='month'" :title="'Ngân sách tháng '+formatMonth(form.month)" width="860px" @update:model-value="v=>!v&&(editor='')">
   <form class="fp-form" @submit.prevent="monthSubmit">
    <p v-if="formError" class="stock-error" role="alert">{{formError}}</p>
    <fieldset v-for="[group,label] in [['production','Sản lượng & giá bán'],['cost','Ngân sách chi phí'],['cash','Đầu tư, vốn & thu chi khác']]" :key="group"><legend>{{label}}</legend><div class="fp-fields"><FormField v-for="[key,text] in budgetFields.filter(f=>f[2]===group)" :key="key" :label="text" v-slot="field"><Input v-bind="field" v-model.number="form[key]" type="number" min="0" :step="key.endsWith('_kg')?'0.001':'1'"/></FormField></div></fieldset>
    <div class="fp-toolbar"><Button type="button" variant="outline" @click="copyMonth">Chép ngân sách sang các tháng</Button><Button type="button" variant="outline" @click="editor=''">Hủy</Button><Button type="submit">Áp dụng tháng</Button></div>
   </form>
  </WorkspaceModal>
  <WorkspaceModal :model-value="editor==='import'" title="Lấy sản lượng dự thu" :busy="saving" width="1000px" @update:model-value="v=>!v&&!saving&&(editor='')">
   <template v-if="proposal"><p>Thay sản lượng tất cả tháng trong kế hoạch bằng {{proposal.sources.length}} dự thu đã phát hành. Tháng không có nguồn về 0; giá bán và ngân sách giữ nguyên.</p><p v-for="warning in proposal.warnings" :key="warning" class="land-warn">{{warning}}</p><DataTable :rows="proposal.sources" :columns="sourceColumns" row-key="name" storage-key="financial-plan-import" empty="Không có dự thu đã phát hành trong phạm vi kế hoạch."/><div class="fp-toolbar"><Button variant="outline" :disabled="saving" @click="editor=''">Hủy</Button><Button :disabled="saving||!proposal.sources.length" @click="applyForecast">Thay sản lượng các tháng</Button></div></template>
  </WorkspaceModal>
  <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" @answer="finish"/>
 </section>
</template>
