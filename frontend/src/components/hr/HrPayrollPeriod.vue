<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import LotusIcon from '../LotusIcon.vue'
import MonthPicker from '../MonthPicker.vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import WorkspaceConfirm from '../WorkspaceConfirm.vue'
import SignerPicker from '../SignerPicker.vue'
import LotusSignatureTimeline from '../LotusSignatureTimeline.vue'
import {Button as UiButton} from '../ui/button'
import {Textarea as UiTextarea} from '../ui/textarea'
import {FormField} from '../ui/form-field'
import {useWorkspaceConfirm} from '../../use-workspace-confirm'
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
const tabs=computed(()=>[['sheet','Bảng lương',sheet.value?.employees?.length||0],['slips','Phiếu lương HRMS',run.value?.slips?.length||0],['crews','Phải trả đội khoán',sheet.value?.crews?.length||0],['issues','Cần kiểm tra',issues.value.length]])
let version=0
async function load(){if(!props.company)return;const id=++version;busy.value=true
 try{const args={company:props.company,month:month.value};const [r,p,s,h]=await Promise.all([hrApi('payroll_readiness',args),periodApi('period_status',args),periodApi('payroll_sheet',args),payrollApi('payroll_run',args)])
  if(id===version){readiness.value=r;period.value=p;sheet.value=s;run.value=h}}
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
onMounted(load)
watch(()=>props.company,load)
const hasUnsavedChanges=computed(()=>sendOpen.value||(reopenOpen.value&&!!reopenReason.value.trim()))
function discardChanges(){sendOpen.value=false;reopenOpen.value=false;reopenReason.value='';signers.value={}}
defineExpose({load,hasUnsavedChanges,isSaving:saving,discardChanges})
</script>
<template>
<div class="hr-pay">
 <div class="stock-scope tk-filters">
  <label>Tháng<MonthPicker v-model="month" :max="today?.slice(0,7)" label="Tháng công" :disabled="busy||saving" @change="load"/></label>
  <UiButton variant="outline" :disabled="busy||saving" @click="load"><LotusIcon name="refresh"/>{{busy?'Đang tải…':'Làm mới'}}</UiButton>
  <span class="tk-actions__spacer"></span>
  <a v-if="period" class="stock-button" :href="period.print_url" target="_blank" rel="noopener"><LotusIcon name="printer"/>In bảng lương</a>
  <a class="stock-button hr-pay__export" :href="exportLink"><LotusIcon name="download"/>Xuất bảng lương Excel</a>
 </div>

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
     <template v-if="s.id==='slips'">
      <UiButton v-if="run&&!run.structure" size="sm" :disabled="saving||busy" @click="step('setup_payroll')"><LotusIcon name="settings"/>Cài đặt lương HRMS</UiButton>
      <UiButton v-else-if="run&&!run.entry" size="sm" :disabled="saving||busy||!closed" @click="step('create_payroll')"><LotusIcon name="document"/>Tạo phiếu lương HRMS</UiButton>
      <a v-else-if="run?.entry" class="hr-steps__link" :href="'/app/payroll-entry/'+encodeURIComponent(run.entry.name)" target="_blank" rel="noopener">Mở {{run.entry.name}} ↗</a>
     </template>
     <template v-if="s.id==='post'">
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
  <div><span>Tổng thu nhập</span><strong>{{money(sheet.totals.gross)}}</strong></div>
  <div><span>BH người lao động</span><strong>{{money(sheet.totals.employee_insurance)}}</strong></div>
  <div><span>Thực lĩnh trước thuế</span><strong>{{money(sheet.totals.net)}}</strong></div>
  <div><span>BH doanh nghiệp đóng</span><strong>{{money(sheet.totals.employer_insurance)}}</strong></div>
  <div><span>Phải trả đội khoán</span><strong>{{money(sheet.totals.crew_amount)}}</strong></div>
 </div>

 <nav class="tk-subnav" aria-label="Chi tiết bảng lương"><button v-for="[id,text,count] in tabs" :key="id" type="button" :class="{active:view===id}" :aria-current="view===id?'page':undefined" @click="view=id">{{text}}<span class="hr-pay__count">{{count}}</span></button></nav>

 <section v-if="view==='sheet'&&sheet" class="tk-card hr-pay__table" aria-label="Bảng lương nhân sự">
  <header class="tk-card__head"><h3>Bảng lương {{label(sheet.month)}}</h3><span class="tk-pill" :class="sheet.draft?'is-draft':'is-approved'">{{sheet.draft?'Bản nháp':'Đã chốt'}}</span><span class="tk-hint">Đơn giá giờ = lương CB ÷ {{sheet.hours_base}} · ca đêm +30% · tăng ca 150/200/300%</span></header>
  <div class="hr-pay__scroll"><table><thead><tr><th>Nhân viên</th><th class="num">Lương CB</th><th class="num">Công</th><th class="num">Giờ thường</th><th class="num">Giờ đêm</th><th class="num">Giờ tăng ca</th><th class="num">Lễ, phép (giờ)</th><th class="num">Thu nhập</th><th class="num">BH người LĐ</th><th class="num">Thực lĩnh</th><th>Ghi chú</th></tr></thead>
   <tbody><tr v-for="e in sheet.employees" :key="e.employee"><td><strong>{{e.employee_name}}</strong><small>{{e.employee}} · {{bases[e.payment_basis]||'Chưa chọn cơ chế'}}</small></td><td class="num">{{money(e.base)}}</td><td class="num">{{num(e.workdays)}}</td><td class="num">{{num(e.regular_hours)}}</td><td class="num">{{num(e.night_hours)}}</td><td class="num">{{num(e.ot_regular+e.ot_weekly_off+e.ot_holiday)}}</td><td class="num">{{num(e.paid_hours)}}</td><td class="num">{{money(e.gross)}}</td><td class="num">{{money(e.employee_insurance)}}</td><td class="num"><strong>{{money(e.net)}}</strong></td><td><span v-if="e.via_crew" class="tk-pill">Trả qua đội khoán</span><span v-for="i in e.issues" :key="i" class="tk-pill is-warn">{{i}}</span></td></tr></tbody></table>
   <p v-if="!sheet.employees.length" class="tk-empty">Chưa có nhân viên trong tháng này.</p></div>
 </section>

 <section v-if="view==='slips'&&run" class="tk-card hr-pay__table" aria-label="Phiếu lương HRMS">
  <header class="tk-card__head"><h3>Phiếu lương HRMS</h3><span class="tk-hint">Thuế TNCN chưa tự tính: kế toán nhập Additional Salary (Income Tax) trước khi duyệt.</span></header>
  <div class="hr-pay__scroll"><table v-if="run.slips.length"><thead><tr><th>Phiếu lương</th><th>Nhân viên</th><th class="num">Thu nhập HRMS</th><th class="num">Khấu trừ</th><th class="num">Thực lĩnh</th><th class="num">Lệch bảng Lotus</th><th>Trạng thái</th></tr></thead>
   <tbody><tr v-for="s in run.slips" :key="s.name"><td><a :href="'/app/salary-slip/'+encodeURIComponent(s.name)" target="_blank" rel="noopener">{{s.name}}</a></td><td>{{s.employee_name}}</td><td class="num">{{money(s.gross_pay)}}</td><td class="num">{{money(s.total_deduction)}}</td><td class="num"><strong>{{money(s.net_pay)}}</strong></td><td class="num" :class="{'is-warn':Math.abs(s.difference)>1}">{{money(s.difference)}}</td><td><span class="tk-pill" :class="s.docstatus===1?'is-approved':'is-draft'">{{s.docstatus===1?(s.journal_entry?'Đã hạch toán':'Đã duyệt'):'Nháp'}}</span></td></tr></tbody></table>
   <p v-else class="tk-empty">{{run.structure?'Chưa có phiếu lương HRMS cho tháng này.':'Cài đặt lương HRMS ở bước 3 trước.'}}</p></div>
 </section>

 <section v-if="view==='crews'&&sheet" class="tk-card hr-pay__table" aria-label="Phải trả đội khoán">
  <header class="tk-card__head"><h3>Phải trả đội khoán</h3><span class="tk-hint">Tiền khoán trả cho tổ trưởng/đội, không lên phiếu lương cá nhân.</span></header>
  <div class="hr-pay__scroll"><table v-if="sheet.crews.length"><thead><tr><th>Đội</th><th>Đầu câu</th><th>Công việc</th><th class="num">Khối lượng</th><th class="num">Đơn giá</th><th class="num">Thành tiền</th><th class="num">Tổng công</th></tr></thead>
   <tbody><tr v-for="(c,i) in sheet.crews" :key="i"><td>{{c.team_name}}</td><td>{{c.foreman}}</td><td>{{c.work_name||'—'}}</td><td class="num">{{num(c.completed_qty)}} {{c.uom}}</td><td class="num">{{money(c.unit_rate)}}</td><td class="num"><strong>{{money(c.amount)}}</strong></td><td class="num">{{num(c.workdays)}}</td></tr></tbody></table>
   <p v-else class="tk-empty">Chưa có phiếu khoán đã duyệt trong tháng.</p></div>
 </section>

 <section v-if="view==='issues'" class="tk-card hr-pay__table" aria-label="Cần kiểm tra">
  <header class="tk-card__head"><h3>Cần kiểm tra</h3></header>
  <div class="hr-pay__scroll"><table v-if="issues.length"><thead><tr><th>Nhân viên</th><th>Vấn đề</th></tr></thead><tbody><tr v-for="(i,n) in issues" :key="n"><td>{{i.employee_name}}<small>{{i.employee}}</small></td><td>{{i.issue}}</td></tr></tbody></table>
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
 <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" :alert-only="confirmAlert" @answer="finishConfirm"/>
</div>
</template>
