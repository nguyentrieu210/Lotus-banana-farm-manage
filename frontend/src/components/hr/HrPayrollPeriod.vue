<script setup>
import WorkspaceListToolbar from '../WorkspaceListToolbar.vue'
import {computed,onMounted,ref,watch} from 'vue'
import LotusIcon from '../LotusIcon.vue'
import {unitLabel} from '../../units'
import DataTable from '../DataTable.vue'
import MonthPicker from '../MonthPicker.vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import WorkspaceConfirm from '../WorkspaceConfirm.vue'
import SignerPicker from '../SignerPicker.vue'
import LotusSignatureTimeline from '../LotusSignatureTimeline.vue'
import {Button as UiButton} from '../ui/button'
import {Textarea as UiTextarea} from '../ui/textarea'
import {FormField} from '../ui/form-field'
import {useWorkspaceConfirm} from '../../use-workspace-confirm'
import ModalForm from '../form/ModalForm.vue'
import LotusField from '../form/LotusField.vue'
import {call} from '../../api'
// /lotus/nhan-su › Kỳ công & bảng lương: the month runs in four steps — complete attendance, send the frozen
// sheet to the named HR person and director (the director's signature closes the period), HRMS salary slips
// from the hourly structure, then submit and post to ERPNext accounting.
const props=defineProps({company:String,today:String})
const emit=defineEmits(['notice','error'])
const {open:confirmOpen,title:confirmTitle,message:confirmMessage,alertOnly:confirmAlert,ask:askConfirm,finish:finishConfirm}=useWorkspaceConfirm()
const hrApi=(name,args)=>call('lotus_farm.hr_workspace.'+name,args)
const periodApi=(name,args,write=false)=>call('lotus_farm.hr_period.'+name,args,write)
const payrollApi=(name,args,write=false)=>call('lotus_farm.hr_payroll.'+name,args,write)
const lastMonth=()=>{const d=new Date((props.today||new Date().toISOString().slice(0,10))+'T00:00:00');d.setDate(1);d.setMonth(d.getMonth()-1);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')}
const month=ref(lastMonth()),busy=ref(false),saving=ref(false),view=ref('sheet')
const readiness=ref(null),period=ref(null),sheet=ref(null),run=ref(null),reopenOpen=ref(false),reopenReason=ref('')
const sendOpen=ref(false),signerOptions=ref(null),signers=ref({})
const signing=computed(()=>period.value?.signing&&!period.value.signing.returned&&!period.value.signing.done?period.value.signing:null)
const signedCount=computed(()=>(period.value?.signing?.steps||[]).filter(s=>s.state==='Đã ký').length)
const signersMissing=computed(()=>(signerOptions.value?.steps||[]).slice(1).filter(s=>!signers.value[s.key]).length)
const bases={Monthly:'Lương tháng',Daywork:'Công nhật',Piecework:'Khoán sản lượng',Mixed:'Hỗn hợp'}
const money=n=>Number(n||0).toLocaleString('vi-VN',{style:'currency',currency:sheet.value?.currency||'VND'})
const num=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:2})
const label=v=>v?'Tháng '+v.slice(5)+'/'+v.slice(0,4):''
const exportLink=computed(()=>'/api/method/lotus_farm.hr_period.export_payroll?'+new URLSearchParams({company:props.company,month:month.value}))
const closed=computed(()=>period.value?.status==='Closed')
const drafts=computed(()=>(run.value?.slips||[]).filter(s=>s.docstatus===0).length)
const posted=computed(()=>(run.value?.slips||[]).length>0&&!drafts.value&&(run.value?.journal_entries||[]).length>0)
const issues=computed(()=>[...(sheet.value?.issues||[]),...(readiness.value?.employees_without_salary||[]).filter(x=>!(sheet.value?.issues||[]).some(i=>i.employee===x.name)).map(x=>({employee:x.name,employee_name:x.employee_name,issue:x.issue}))])
const steps=computed(()=>{
 const blockers=period.value?.blockers||[]
 const attendanceDone=closed.value||!blockers.length
 return [
  {id:'attendance',title:'Chấm công đủ',state:attendanceDone?'done':'current',text:closed.value?'Đã khóa cùng kỳ':blockers.length?blockers.length+' việc cần xử lý':'Không còn vướng mắc'},
  {id:'close',title:'Ký duyệt & khóa kỳ',state:closed.value?'done':attendanceDone?'current':'todo',text:closed.value?'Khóa lúc '+String(period.value?.closed_at||'').slice(0,16):period.value?.future?'Chờ hết tháng':signing.value?'Chờ '+(signing.value.steps[signing.value.current]?.name||'')+' ký ('+signedCount.value+'/'+signing.value.steps.length+')':period.value?.signing?.returned?'Bị trả lại: '+(period.value.signing.steps.find(s=>s.state==='Trả lại')?.note||''):'Chưa gửi duyệt'},
  {id:'slips',title:'Phiếu lương HRMS',state:run.value?.entry?'done':closed.value?'current':'todo',text:!run.value?.structure?'Chưa cài đặt cấu trúc lương':run.value?.entry?(run.value.slips.length+' phiếu · '+run.value.entry.name):'Chưa tạo'},
  {id:'post',title:'Duyệt & hạch toán',state:posted.value?'done':run.value?.entry?'current':'todo',text:posted.value?'Đã hạch toán '+run.value.journal_entries.join(', '):drafts.value?drafts.value+' phiếu nháp':'Chưa hạch toán'},
 ]
})
const tabs=computed(()=>[['sheet','Bảng lương',sheet.value?.employees?.length||0],['rates','Phụ cấp & đơn giá công',rates.value?.missing_daily_rate||0],['slips','Phiếu lương HRMS',run.value?.slips?.length||0],['crews','Phải trả đội khoán',sheet.value?.crews?.length||0],['issues','Cần kiểm tra',issues.value.length]])
let version=0
async function load(){if(!props.company)return;const id=++version;busy.value=true
 try{const args={company:props.company,month:month.value};const [r,p,s,h]=await Promise.all([hrApi('payroll_readiness',args),periodApi('period_status',args),periodApi('payroll_sheet',args),payrollApi('payroll_run',args)])
  const q=await call('lotus_farm.work_allowance.pay_rates',{company:props.company}).catch(()=>null)
  if(id===version){readiness.value=r;period.value=p;sheet.value=s;run.value=h;rates.value=q}}
 catch(e){emit('error',e.message)}finally{if(id===version)busy.value=false}}
const asks={setup_payroll:()=>'Tạo thành phần lương, tài khoản và cấu trúc lương giờ công trong HRMS?',
 create_payroll:m=>'Tạo bảng lương HRMS và phiếu lương nháp cho '+label(m)+'?',
 post_payroll:m=>'Duyệt toàn bộ phiếu lương '+label(m)+' và hạch toán? Bút toán: Nợ chi phí lương / Có phải trả người lao động, bảo hiểm phải nộp.'}
async function step(action){
 if(!await askConfirm(asks[action](month.value)))return
 saving.value=true
 try{const r=await payrollApi(action,action==='setup_payroll'?{company:props.company}:{company:props.company,month:month.value},true)
  emit('notice',{setup_payroll:'Đã cài đặt cấu trúc '+r.structure+'.',create_payroll:'Đã tạo bảng lương '+r.name+' ('+r.employees+' nhân viên).',post_payroll:'Đã duyệt phiếu lương và hạch toán '+(r.journal_entries||[]).join(', ')+'.'}[action])
  if(action==='create_payroll')view.value='slips'
  await load()}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
async function openSend(){saving.value=true
 try{signerOptions.value=await periodApi('period_signers',{company:props.company});signers.value=Object.fromEntries((period.value?.signing?.steps||[]).slice(1).filter(s=>s.assignee).map(s=>[s.key,s.assignee]));sendOpen.value=true}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
async function send(){saving.value=true
 try{await periodApi('send_period',{company:props.company,month:month.value,signers:signers.value},true);sendOpen.value=false;emit('notice','Đã ký người lập và gửi duyệt '+label(month.value)+'. Người ký tiếp theo đã được báo.');await load()}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
async function signHere(){
 const last=signing.value.current===signing.value.steps.length-1
 if(!await askConfirm('Ký '+signing.value.steps[signing.value.current].title+' cho bảng công '+label(month.value)+'?'+(last?' Chữ ký này khóa kỳ công.':'')))return
 saving.value=true
 try{await periodApi('sign_period',{company:props.company,month:month.value},true);emit('notice','Đã ký bảng công '+label(month.value)+'.');await load()}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
async function reopen(){saving.value=true
 try{await periodApi('reopen_period',{company:props.company,month:month.value,reason:reopenReason.value},true);reopenOpen.value=false;reopenReason.value='';emit('notice','Đã mở lại kỳ '+label(month.value)+'.');await load()}
 catch(e){emit('error',e.message)}finally{saving.value=false}}

// Phụ cấp công việc and the common đơn giá công nhật, each by effective date (lotus_farm.work_allowance).
const rates=ref(null),rateForm=ref(null),rateError=ref('')
const rateKinds=[{value:'Allowance',label:'Phụ cấp công việc (đ/ngày)'},{value:'Daywork',label:'Đơn giá công nhật chung (đ/công)'},{value:'MinimumHourly',label:'Lương tối thiểu theo giờ (bù khoán)'}]
const rateRows=computed(()=>Object.entries(rates.value?.rates||{}).flatMap(([kind,r])=>r.history.map(h=>({...h,kind,label:r.label}))))
function newRate(){rateError.value='';rateForm.value={kind:'Allowance',rate:null,valid_from:props.today||'',notes:''}}
async function saveRate(){saving.value=true;rateError.value=''
 try{await call('lotus_farm.work_allowance.save_pay_rate',{company:props.company,...rateForm.value},true);rateForm.value=null;emit('notice','Đã lưu mức mới.');await load()}
 catch(e){rateError.value=e.message}finally{saving.value=false}}
async function fillRates(){
 const r=rates.value?.rates?.Daywork
 if(!await askConfirm('Ghi đơn giá công '+money(r?.current)+' cho '+rates.value.missing_daily_rate+' công nhân chưa có đơn giá?'))return
 saving.value=true
 try{const x=await call('lotus_farm.work_allowance.fill_daily_rates',{company:props.company},true);emit('notice','Đã ghi đơn giá công cho '+x.updated+' người.');await load()}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
const pcol=(field,headerName,format)=>({field,headerName,minWidth:130,...(format?{valueFormatter:p=>format(p.value,p.data)}:{})})
const pmoney=(field,label)=>pcol(field,label,v=>money(v))
const pnum=(field,label)=>pcol(field,label,v=>num(v))
const rateCols=[pcol('label','Loại'),pmoney('rate','Mức'),pcol('valid_from','Áp dụng từ'),pcol('notes','Ghi chú')]
// By công: no hour or overtime columns. Sheets frozen before phụ cấp existed read their missing keys as zero.
const sheetCols=[
 pcol('employee_name','Nhân viên',(_,r)=>r.employee_name+' · '+r.employee),
 pcol('group','Tổ / bộ phận',(_,r)=>r.group||r.department||''),pcol('payment_basis','Cơ chế',v=>bases[v]||'Chưa chọn'),
 pnum('workdays','Công'),pcol('daily_rate','Đơn giá công / lương CB',(_,r)=>r.payment_basis==='Daywork'?money(r.daily_rate):money(r.base)),
 pcol('wage','Tiền công',(_,r)=>money(r.wage??r.gross)+(r.khoan_sessions?' (trừ '+r.khoan_sessions+' buổi khoán)':'')),
 pmoney('piece','Tiền khoán'),pmoney('topup','Bù lương tối thiểu'),pmoney('allowance','Phụ cấp'),pmoney('employee_insurance','BH người LĐ'),
 pcol('pit','Thuế TNCN',(_,r)=>r.pit?money(r.pit)+(r.pit_method==='flat'?' (10%)':''):r.pit_method==='commitment'?'Cam kết 08':''),
 pmoney('advance','Tạm ứng'),pcol('take_home','Thực lĩnh',(_,r)=>money(r.take_home??r.net)),
 pcol('issues','Ghi chú',(_,r)=>(r.via_crew?'Trả qua đội khoán; ':'')+(r.issues||[]).join('; '))
]
function slipLink(params){const a=document.createElement('a');a.href='/app/salary-slip/'+encodeURIComponent(params.data.name);a.target='_blank';a.rel='noopener';a.textContent=params.data.name;return a}
const slipCols=[
 {field:'name',headerName:'Phiếu lương',minWidth:220,cellRenderer:slipLink},
 pcol('employee_name','Nhân viên'),pmoney('gross_pay','Thu nhập HRMS'),pmoney('total_deduction','Khấu trừ'),
 pmoney('net_pay','Thực lĩnh'),pmoney('difference','Lệch bảng Lotus'),
 pcol('docstatus','Trạng thái',(_,r)=>r.docstatus===1?(r.journal_entry?'Đã hạch toán':'Đã duyệt'):'Nháp')
]
const crewCols=[pcol('team_name','Đội'),pcol('foreman','Đầu câu'),pcol('work_name','Công việc'),pcol('completed_qty','Khối lượng',(_,r)=>num(r.completed_qty)+' '+unitLabel(r.uom)),
 pmoney('unit_rate','Đơn giá'),pmoney('amount','Thành tiền'),pnum('workdays','Tổng công')]
const issueCols=[pcol('employee_name','Nhân viên',(_,r)=>r.employee_name+' · '+r.employee),pcol('issue','Vấn đề')]

onMounted(load)
watch(()=>props.company,load)
const hasUnsavedChanges=computed(()=>sendOpen.value||(reopenOpen.value&&!!reopenReason.value.trim()))
function discardChanges(){sendOpen.value=false;reopenOpen.value=false;reopenReason.value='';signers.value={}}
defineExpose({load,hasUnsavedChanges,isSaving:saving,discardChanges})
</script>
<template>
<div class="hr-pay">
 <WorkspaceListToolbar :searchable="false" :busy="busy" :refresh-disabled="saving" @refresh="load">
  <template #filters><MonthPicker v-model="month" :max="today?.slice(0,7)" label="Tháng công" :disabled="busy||saving" @change="load"/></template>
  <UiButton v-if="period" as="a" variant="outline" :href="period.print_url" target="_blank" rel="noopener"><LotusIcon name="printer"/>In bảng lương</UiButton>
  <UiButton as="a" variant="outline" :href="exportLink"><LotusIcon name="download"/>Xuất bảng lương Excel</UiButton>
 </WorkspaceListToolbar>

 <ol class="hr-steps" aria-label="Các bước chốt lương">
  <li v-for="(s,i) in steps" :key="s.id" :class="'is-'+s.state">
   <span class="hr-steps__mark" aria-hidden="true"><LotusIcon v-if="s.state==='done'" name="tick"/><template v-else>{{i+1}}</template></span>
   <div class="hr-steps__body"><strong>{{s.title}}</strong><small>{{s.text}}</small>
    <div class="hr-steps__actions">
     <template v-if="s.id==='close'">
      <UiButton v-if="!closed&&period?.can_send" size="sm" :disabled="saving||busy||period?.future||(period?.blockers||[]).length>0" @click="openSend"><LotusIcon name="lock"/>Gửi duyệt khóa kỳ</UiButton>
      <UiButton v-if="signing?.can_sign" size="sm" :disabled="saving||busy" @click="signHere">Ký: {{signing.steps[signing.current].title}}</UiButton>
      <a v-if="period?.signing" class="hr-steps__link" :href="period.print_url" target="_blank" rel="noopener">Xem bảng lương ký duyệt ↗</a>
      <UiButton v-if="closed" size="sm" variant="outline" :disabled="saving||busy" @click="reopenReason='';reopenOpen=true">Mở lại kỳ</UiButton>
     </template>
     <a v-if="run?.finance?.enabled&&(s.id==='slips'||s.id==='post')" class="hr-steps__link" :href="run.finance.url">Ghi sổ lương ở Tài chính – Kế toán ↗</a>
     <template v-if="s.id==='slips'&&!run?.finance?.enabled">
      <UiButton v-if="run&&!run.structure" size="sm" :disabled="saving||busy" @click="step('setup_payroll')"><LotusIcon name="settings"/>Cài đặt lương HRMS</UiButton>
      <UiButton v-else-if="run&&!run.entry" size="sm" :disabled="saving||busy||!closed" @click="step('create_payroll')"><LotusIcon name="document"/>Tạo phiếu lương HRMS</UiButton>
      <a v-else-if="run?.entry" class="hr-steps__link" :href="'/app/payroll-entry/'+encodeURIComponent(run.entry.name)" target="_blank" rel="noopener">Mở {{run.entry.name}} ↗</a>
     </template>
     <template v-if="s.id==='post'&&!run?.finance?.enabled">
      <UiButton v-if="drafts" size="sm" :disabled="saving||busy" @click="step('post_payroll')"><LotusIcon name="wallet"/>Duyệt &amp; hạch toán</UiButton>
      <a v-for="j in run?.journal_entries||[]" :key="j" class="hr-steps__link" :href="'/app/journal-entry/'+encodeURIComponent(j)" target="_blank" rel="noopener">Bút toán {{j}} ↗</a>
     </template>
    </div>
   </div>
  </li>
 </ol>

 <LotusSignatureTimeline v-if="period?.signing?.round" :steps="period.signing.steps"
  :current="period.signing.returned?-1:(period.signing.current??-1)" title="Chữ ký duyệt bảng công"/>

 <section v-if="!closed&&period?.blockers?.length" class="tk-card hr-pay__blockers" aria-label="Việc cần xử lý trước khi khóa">
  <header class="tk-card__head"><h3>Cần xử lý trước khi khóa kỳ</h3></header>
  <ul><li v-for="b in period.blockers" :key="b.code"><strong>{{b.label}}</strong>: {{b.count}}<small v-if="b.employees"> · {{b.employees.slice(0,8).map(e=>e.employee_name).join(', ')}}{{b.employees.length>8?'…':''}}</small></li></ul>
  <a class="hr-steps__link" href="/lotus/cham-cong">Mở Chấm công để xử lý ↗</a>
 </section>

 <div v-if="sheet" class="hr-pay__stats">
  <div><span>Nhân viên</span><strong>{{sheet.totals.employees}}</strong></div>
  <div><span>Tổng thu nhập</span><strong>{{money(sheet.totals.gross)}}</strong><small v-if="sheet.totals.allowance">Phụ cấp {{money(sheet.totals.allowance)}}</small></div>
  <div><span>BH người lao động</span><strong>{{money(sheet.totals.employee_insurance)}}</strong></div>
  <div><span>Thuế TNCN khấu trừ</span><strong>{{money(sheet.totals.pit||0)}}</strong></div>
  <div><span>Thực lĩnh</span><strong>{{money(sheet.totals.take_home??sheet.totals.net)}}</strong><small v-if="sheet.totals.advance">Đã trừ tạm ứng {{money(sheet.totals.advance)}}</small></div>
  <div><span>BH doanh nghiệp đóng</span><strong>{{money(sheet.totals.employer_insurance)}}</strong><small v-if="sheet.totals.union_fee">KPCĐ {{money(sheet.totals.union_fee)}}</small></div>
  <div><span>Phải trả đội khoán</span><strong>{{money(sheet.totals.crew_amount)}}</strong></div>
 </div>

 <nav class="tk-subnav" aria-label="Chi tiết bảng lương"><button v-for="[id,text,count] in tabs" :key="id" type="button" :class="{active:view===id}" :aria-current="view===id?'page':undefined" @click="view=id">{{text}}<span class="hr-pay__count">{{count}}</span></button></nav>

 <section v-if="view==='sheet'&&sheet" class="tk-card hr-pay__table" aria-label="Bảng lương nhân sự">
  <header class="tk-card__head"><h3>Bảng lương {{label(sheet.month)}}</h3><span class="tk-pill" :class="sheet.draft?'is-draft':'is-approved'">{{sheet.draft?'Bản nháp':'Đã chốt'}}</span><span class="tk-hint">Tiền công = công × đơn giá công (lương tháng: lương CB ÷ 26 × công) · phụ cấp không tính thuế · thực lĩnh đã trừ tạm ứng</span></header>
  <div class="hr-pay__scroll"><DataTable :rows="sheet.employees" :columns="sheetCols" row-key="employee" storage-key="payroll-sheet" empty="Chưa có nhân viên trong tháng."/>
   <p v-if="!sheet.employees.length" class="tk-empty">Chưa có nhân viên trong tháng này.</p></div>
 </section>

 <section v-if="view==='rates'&&rates" class="tk-card hr-pay__table" aria-label="Phụ cấp và đơn giá công">
  <header class="tk-card__head"><h3>Phụ cấp &amp; đơn giá công</h3><span class="tk-hint">Phụ cấp hiện tại {{money(rates.rates.Allowance?.current)}}/ngày (một buổi nửa mức) · đơn giá công nhật chung {{money(rates.rates.Daywork?.current)}}/công</span>
   <UiButton v-if="rates.can_edit" size="sm" variant="outline" :disabled="saving||busy" @click="newRate">Đổi mức</UiButton>
   <UiButton v-if="rates.can_edit&&rates.missing_daily_rate" size="sm" :disabled="saving||busy||!rates.rates.Daywork?.current" @click="fillRates">Ghi đơn giá chung cho {{rates.missing_daily_rate}} công nhân chưa có</UiButton></header>
  <div class="hr-pay__scroll"><DataTable :rows="rateRows" :columns="rateCols" row-key="name" storage-key="payroll-rates" empty="Chưa đặt mức."/></div>
 </section>

 <section v-if="view==='slips'&&run" class="tk-card hr-pay__table" aria-label="Phiếu lương HRMS">
  <header class="tk-card__head"><h3>Phiếu lương HRMS</h3><span class="tk-hint">Thuế TNCN chưa tự tính: kế toán nhập Additional Salary (Income Tax) trước khi duyệt.</span></header>
  <div class="hr-pay__scroll"><DataTable v-if="run.slips.length" :rows="run.slips" :columns="slipCols" row-key="name" storage-key="payroll-slips"/>
   <p v-else class="tk-empty">{{run.structure?'Chưa có phiếu lương HRMS cho tháng này.':'Cài đặt lương HRMS ở bước 3 trước.'}}</p></div>
 </section>

 <section v-if="view==='crews'&&sheet" class="tk-card hr-pay__table" aria-label="Phải trả đội khoán">
  <header class="tk-card__head"><h3>Phải trả đội khoán</h3><span class="tk-hint">Tiền khoán trả cho tổ trưởng/đội, không lên phiếu lương cá nhân.</span></header>
  <div class="hr-pay__scroll"><DataTable v-if="sheet.crews.length" :rows="sheet.crews" :columns="crewCols" storage-key="payroll-crews"/>
   <p v-else class="tk-empty">Chưa có phiếu khoán đã duyệt trong tháng.</p></div>
 </section>

 <section v-if="view==='issues'" class="tk-card hr-pay__table" aria-label="Cần kiểm tra">
  <header class="tk-card__head"><h3>Cần kiểm tra</h3></header>
  <div class="hr-pay__scroll"><DataTable v-if="issues.length" :rows="issues" :columns="issueCols" row-key="employee" storage-key="payroll-issues"/>
   <p v-else class="tk-empty">Không có vấn đề cần kiểm tra.</p></div>
 </section>

 <WorkspaceModal v-model="sendOpen" :title="'Gửi duyệt khóa kỳ '+label(month)" :busy="saving">
  <form @submit.prevent="send"><p class="tk-hint">Bảng công và bảng lương được chốt tại thời điểm gửi. Bạn ký người lập; Phụ trách nhân sự rồi Giám đốc ký trên trang bảng lương. Chữ ký Giám đốc khóa kỳ công.</p>
   <SignerPicker v-model="signers" :options="signerOptions" :disabled="saving"/>
   <div class="hr-form-footer"><UiButton type="button" variant="outline" :disabled="saving" @click="sendOpen=false">Quay lại</UiButton><UiButton type="submit" :disabled="saving||signersMissing>0">Ký và gửi duyệt</UiButton></div></form>
 </WorkspaceModal>
 <WorkspaceModal v-model="reopenOpen" :title="'Mở lại kỳ công '+label(month)" :busy="saving">
  <form @submit.prevent="reopen"><FormField label="Lý do mở lại" required hint="Lý do được lưu trong lịch sử kỳ công." v-slot="f"><UiTextarea v-bind="f" v-model="reopenReason" minlength="5" maxlength="500"/></FormField>
   <div class="hr-form-footer"><UiButton type="button" variant="outline" :disabled="saving" @click="reopenOpen=false">Quay lại</UiButton><UiButton type="submit" :disabled="saving">Mở lại kỳ</UiButton></div></form>
 </WorkspaceModal>
 <ModalForm :model-value="!!rateForm" title="Đổi mức phụ cấp / đơn giá công" width="520px" :busy="saving" :error="rateError" submit-label="Lưu mức" @update:model-value="v=>!v&&(rateForm=null)" @submit="saveRate">
  <template v-if="rateForm">
   <LotusField v-model="rateForm.kind" label="Loại" type="select" :searchable="false" :options="rateKinds" required/>
   <LotusField v-model="rateForm.rate" label="Mức mới (đ)" type="money" required/>
   <LotusField v-model="rateForm.valid_from" label="Áp dụng từ ngày" type="date" required hint="Ngày đã chấm trước ngày này giữ mức cũ."/>
   <LotusField v-model="rateForm.notes" label="Ghi chú" type="textarea" maxlength="500"/>
  </template>
 </ModalForm>
 <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" :alert-only="confirmAlert" @answer="finishConfirm"/>
</div>
</template>