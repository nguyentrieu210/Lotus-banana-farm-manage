<script setup>
const props=defineProps({embedded:Boolean,navigationKey:String})
import {computed,onMounted,reactive,ref} from 'vue'
import WorkspaceTabs from './components/WorkspaceTabs.vue'
import WorkspaceListToolbar from './components/WorkspaceListToolbar.vue'
import WorkspaceSummaryStrip from './components/WorkspaceSummaryStrip.vue'
import WorkspaceModal from './components/WorkspaceModal.vue'
import WorkspaceConfirm from './components/WorkspaceConfirm.vue'
import LotusIcon from './components/LotusIcon.vue'
import {useWorkspaceConfirm} from './use-workspace-confirm'
import HrOperations from './components/HrOperations.vue'
import CccdQrScanner from './components/CccdQrScanner.vue'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import UiSelect from './components/ui/select/Select.vue'
import {Textarea as UiTextarea} from './components/ui/textarea'
import {useNoticeToast} from './use-toast'
import {call,setCSRF} from './api'
import {sidebarCollapsed} from './workspace'
import {stateLabel} from './labels'
import {hrCatalogLabel} from './hr-catalog-labels'
const {open:confirmOpen,title:confirmTitle,message:confirmMessage,alertOnly:confirmAlert,ask:askConfirm,tell,finish:finishConfirm}=useWorkspaceConfirm()

const api=(name,args={},write=false)=>call('lotus_farm.hr_workspace.'+name,args,write)
const session=ref(null),company=ref(''),tab=ref('employees'),busy=ref(false),saving=ref(false),error=ref(''),notice=ref('')
const catalog=ref({farms:[],departments:[],designations:[],teams:[],grades:[],employment_types:[],genders:[],openings:[],designation_groups:{},worker_categories:[],payment_bases:[]})
const overview=ref({employees:[],candidates:[]}),readiness=ref(null)
const periodApi=(name,args={},write=false)=>call('lotus_farm.hr_period.'+name,args,write)
const payrollApi=(name,args={},write=false)=>call('lotus_farm.hr_payroll.'+name,args,write)
const payMonth=ref(''),period=ref(null),sheet=ref(null),run=ref(null),reopenOpen=ref(false),reopenReason=ref(''),offboardOpen=ref(false)
const offboard=reactive({relieving_date:'',reason:''})
const exportPayroll=computed(()=>'/api/method/lotus_farm.hr_period.export_payroll?'+new URLSearchParams({company:company.value,month:payMonth.value}))
const lastMonth=()=>{const d=new Date((session.value?.today||new Date().toISOString().slice(0,10))+'T00:00:00');d.setDate(1);d.setMonth(d.getMonth()-1);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')}
const search=ref(''),editEmployee=ref(false),editCandidate=ref(false),candidateHire=ref(null),cccdScanOpen=ref(false)
const selectedEmployee=ref(null),selectedCandidate=ref(null)
const employeeForm=reactive({}),candidateForm=reactive({})
const isManager=computed(()=>session.value?.is_hr_manager||false)
const money=(n,cur='VND')=>Number(n||0).toLocaleString('vi-VN',{style:'currency',currency:cur||'VND'})
const cats={Permanent:'Dài hạn', 'Fixed-term':'Hợp đồng xác định hạn',Seasonal:'Thời vụ',Probation:'Thử việc'}
const bases={Monthly:'Lương tháng',Daywork:'Công nhật',Piecework:'Khoán sản lượng',Mixed:'Hỗn hợp'}
const stages={New:'Mới',Screening:'Sàng lọc',Interview:'Phỏng vấn',Offered:'Đã mời nhận việc',Hold:'Tạm giữ',Rejected:'Không đạt',Hired:'Đã tiếp nhận'}
const genderName={Male:'Nam',Female:'Nữ',Other:'Khác'}
const contractTypeNames={Apprentice:'Học việc',Intern:'Thực tập',Piecework:'Khoán theo sản phẩm',Commission:'Theo hoa hồng',Contract:'Hợp đồng',Probation:'Thử việc','Part-time':'Bán thời gian','Full-time':'Toàn thời gian'}
const routes=[{id:'employees',label:'Hồ sơ nhân viên'},{id:'candidates',label:'Tuyển dụng'},{id:'onboarding',label:'Tiếp nhận'},{id:'designations',label:'Chức danh'},{id:'operations',label:'Cơ cấu · Nhập dữ liệu · Máy chấm công'},{id:'payroll',label:'Kỳ công & bảng lương'}]
const tabs=computed(()=>routes.filter(r=>r.id!=='payroll'||isManager.value))
const actions=computed(()=>[
  {id:'home',label:'Trang chủ Lotus',navigation:true,href:'/lotus/mobile'},
  {id:'attendance',label:'Chấm công',navigation:true,href:'/lotus/cham-cong'},
  {id:'work',label:'Kế hoạch & giao việc',navigation:true,href:'/lotus/cong-viec'},
  ...tabs.value.map(t=>({id:t.id,label:t.label,navigation:true,run:()=>chooseTab(t.id)})),
  {id:'hrms',label:'Quản trị Frappe HRMS',navigation:true,href:'/desk/hr-setup'},
])
const filteredEmployees=computed(()=>overview.value.employees.filter(e=>{
  if(tab.value==='onboarding'&&e.lotus_onboarding_state==='Ready')return false
  const needle=search.value.toLocaleLowerCase('vi-VN')
  return [e.name,e.employee_name,e.designation,e.department,e.lotus_farm].some(v=>String(v||'').toLocaleLowerCase('vi-VN').includes(needle))
}))
const filteredCandidates=computed(()=>overview.value.candidates.filter(c=>
  [c.applicant_name,c.phone,c.designation,c.status].some(v=>String(v||'').toLocaleLowerCase('vi-VN').includes(search.value.toLocaleLowerCase('vi-VN')))
))
const teamChoices=computed(()=>catalog.value.teams.filter(t=>t.farm===employeeForm.lotus_farm&&t.lotus_team_type!=='Contractor'))
const missingCount=computed(()=>overview.value.employees.filter(e=>e.lotus_onboarding_state!=='Ready').length)
const today=computed(()=>session.value?.today||'')
function clear(obj){for(const k of Object.keys(obj))delete obj[k]}
function resetPanels(){cccdScanOpen.value=false;editEmployee.value=false;editCandidate.value=false;candidateHire.value=null;selectedEmployee.value=null;selectedCandidate.value=null;error.value=''}
function chooseTab(t){resetPanels();search.value='';tab.value=t;if(t==='payroll')loadPayroll()}
async function refresh(){if(!company.value)return;busy.value=true;error.value='';try{
  const [c,data]=await Promise.all([api('catalogue',{company:company.value}),api('overview',{company:company.value})])
  catalog.value=c;overview.value=data
}catch(e){error.value=e.message}finally{busy.value=false}}
async function loadPayroll(){if(!isManager.value||!company.value)return;payMonth.value||=lastMonth();busy.value=true;error.value='';try{const args={company:company.value,month:payMonth.value};[readiness.value,period.value,sheet.value,run.value]=await Promise.all([api('payroll_readiness',args),periodApi('period_status',args),periodApi('payroll_sheet',args),payrollApi('payroll_run',args)])}catch(e){error.value=e.message}finally{busy.value=false}}
async function closePeriod(){if(!await askConfirm('Khóa kỳ công '+payMonth.value+'? Sau khi khóa, chấm công, phiếu khoán và phân công lao động của tháng không sửa được; bảng lương được chốt.'))return
  saving.value=true;error.value='';try{await periodApi('close_period',{company:company.value,month:payMonth.value},true);notice.value='Đã khóa kỳ '+payMonth.value+'.';await loadPayroll()}catch(e){error.value=e.message}finally{saving.value=false}}
async function reopenPeriod(){saving.value=true;error.value='';try{await periodApi('reopen_period',{company:company.value,month:payMonth.value,reason:reopenReason.value},true);reopenOpen.value=false;reopenReason.value='';notice.value='Đã mở lại kỳ '+payMonth.value+'.';await loadPayroll()}catch(e){error.value=e.message}finally{saving.value=false}}
// HRMS payroll: one-time structure setup, then Payroll Entry -> Salary Slips -> accounting entry for a closed month.
async function payrollStep(step){const ask={setup_payroll:'Tạo thành phần lương, tài khoản và cấu trúc lương giờ công trong HRMS?',create_payroll:'Tạo bảng lương HRMS và phiếu lương nháp cho tháng '+payMonth.value+'?',post_payroll:'Duyệt toàn bộ phiếu lương tháng '+payMonth.value+' và hạch toán sang kế toán? Bút toán: Nợ chi phí lương / Có phải trả người lao động, bảo hiểm phải nộp.'}[step]
 if(!await askConfirm(ask))return
 saving.value=true;error.value='';try{const r=await payrollApi(step,step==='setup_payroll'?{company:company.value}:{company:company.value,month:payMonth.value},true);notice.value=step==='setup_payroll'?'Đã cài đặt cấu trúc '+r.structure+'.':step==='create_payroll'?'Đã tạo bảng lương '+r.name+' ('+r.employees+' nhân viên).':'Đã duyệt phiếu lương và hạch toán '+(r.journal_entries||[]).join(', ')+'.';await loadPayroll()}catch(e){error.value=e.message}finally{saving.value=false}}
function startOffboard(){offboard.relieving_date=today.value;offboard.reason='';error.value='';offboardOpen.value=true}
async function confirmOffboard(){saving.value=true;error.value='';try{await api('offboard_employee',{company:company.value,employee:selectedEmployee.value,modified:employeeForm.modified,...offboard},true);offboardOpen.value=false;notice.value='Đã ghi nhận nghỉ việc.';resetPanels();await refresh()}catch(e){error.value=e.message}finally{saving.value=false}}
async function init(){busy.value=true;try{
  session.value=await api('bootstrap');setCSRF(session.value.csrf_token)
  company.value=session.value.companies[0]?.name||''
  await refresh()
}catch(e){error.value=e.message}finally{busy.value=false}}
function emptyEmployee(){
  resetPanels();clear(employeeForm)
  Object.assign(employeeForm,{employee_name:'',gender:'',date_of_birth:'',date_of_joining:today.value,designation:'',department:'',
    employment_type:'',grade:'',reports_to:'',lotus_worker_category:'Seasonal',lotus_payment_basis:'Daywork',
    lotus_farm:'',lotus_work_team:'',cell_number:'',personal_email:'',current_address:'',permanent_address:'',
    cccd:'',lotus_id_issue_on:'',lotus_id_issue_at:'',lotus_emergency_name:'',lotus_emergency_phone:'',
    lotus_tax_code:'',lotus_social_insurance_no:'',health_insurance_no:'',contract_end_date:'',lotus_onboarding_state:'Pending',
    lotus_base_salary:0,lotus_daily_rate:0})
  editEmployee.value=true
}
async function openEmployee(item){if(!isManager.value)return;busy.value=true;error.value=''
  try{const data=await api('employee_detail',{company:company.value,employee:item.name})
    resetPanels();clear(employeeForm);Object.assign(employeeForm,data,{cccd:''});selectedEmployee.value=item.name;editEmployee.value=true
  }catch(e){error.value=e.message}finally{busy.value=false}}
async function applyScannedCccd(info){
  if (!isManager.value || !editEmployee.value || saving.value) return
  // Candidate name comes from the hiring record and cannot be overwritten here.
  if (candidateHire.value && employeeForm.employee_name.trim() !== info.employee_name) {
    await tell('Tên trên QR khác tên ứng viên đã tiếp nhận. Kiểm tra và sửa hồ sơ ứng viên trước.')
    return
  }
  const changed=['employee_name','date_of_birth','gender','current_address','lotus_id_issue_on']
    .some(key => employeeForm[key] && String(employeeForm[key]).trim() !== String(info[key]||'').trim())
  if (changed && !await askConfirm('Thông tin QR khác dữ liệu đang nhập. Dùng thông tin trên QR để thay các trường này?')) return
  saving.value=true;error.value=''
  try{
    const check=await api('check_cccd',{company:company.value,cccd:info.cccd,employee:selectedEmployee.value},true)
    if(check.duplicate){
      await tell('CCCD này đã tồn tại trong hệ thống. Không thể nhập trùng.')
      return
    }
    // The residence field is not necessarily the registered permanent address.
    Object.assign(employeeForm,info)
    cccdScanOpen.value=false
    notice.value='Đã điền từ QR. Kiểm tra nơi cư trú và các trường còn thiếu trước khi lưu hồ sơ.'
  }catch(e){error.value=e.message;await tell('Không kiểm tra được CCCD: '+e.message)}
  finally{saving.value=false}
}
async function saveEmployee(){saving.value=true;error.value='';notice.value=''
  try{
    const args={company:company.value,values:{...employeeForm}}
    let result
    if(candidateHire.value)result=await api('hire_candidate',{...args,candidate:candidateHire.value.name,modified:candidateHire.value.modified},true)
    else result=await api('save_employee',{...args,employee:selectedEmployee.value,modified:employeeForm.modified},true)
    notice.value='Đã lưu nhân viên '+result.name+'. Nhân sự mới sẽ ở trạng thái Chờ tiếp nhận cho đến khi kiểm tra đủ hồ sơ.'
    resetPanels();await refresh()
  }catch(e){error.value=e.message}finally{saving.value=false}
}
async function approveOnboarding(){if(!selectedEmployee.value)return;saving.value=true;error.value=''
  try{await api('set_onboarding_ready',{company:company.value,employee:selectedEmployee.value,modified:employeeForm.modified},true)
    notice.value='Đã duyệt tiếp nhận và kích hoạt nhân viên.';resetPanels();await refresh()
  }catch(e){error.value=e.message}finally{saving.value=false}
}
function emptyCandidate(){resetPanels();clear(candidateForm);Object.assign(candidateForm,{applicant_name:'',phone:'',email:'',designation:'',farm:'',job_opening:'',applied_on:today.value,source:'Trực tiếp',status:'New',interview_on:'',notes:''});editCandidate.value=true}
async function openCandidate(item){busy.value=true;error.value='';try{const details=await api('candidate_detail',{company:company.value,candidate:item.name});resetPanels();selectedCandidate.value=item.name;clear(candidateForm);Object.assign(candidateForm,details);editCandidate.value=true}catch(e){error.value=e.message}finally{busy.value=false}}
async function saveCandidate(){saving.value=true;error.value=''
  try{const result=await api('save_candidate',{company:company.value,name:selectedCandidate.value,modified:candidateForm.modified,values:{...candidateForm}},true)
    notice.value='Đã lưu ứng viên '+result.name;resetPanels();await refresh()
  }catch(e){error.value=e.message}finally{saving.value=false}}
function startHire(item){emptyEmployee();candidateHire.value=item;employeeForm.employee_name=item.applicant_name;employeeForm.designation=item.designation;employeeForm.lotus_farm=item.farm||'';employeeForm.cell_number=item.phone;tab.value='onboarding';}
function chooseOpening(){const opening=catalog.value.openings.find(x=>x.name===candidateForm.job_opening);if(opening)candidateForm.designation=opening.designation}
async function seed(){if(!await askConfirm('Tạo các chức danh Lotus chưa có trong HRMS? Hành động không xóa hoặc sửa chức danh hiện hữu.'))return
  saving.value=true;error.value=''
  try{const r=await api('seed_designations',{company:company.value},true);notice.value='Đã tạo thêm '+r.count+' chức danh.';await refresh()}catch(e){error.value=e.message}finally{saving.value=false}}
onMounted(init)
// Success messages show as toasts (errors stay inline next to the form).
useNoticeToast(notice)
</script>

<template>
<div class="stock-shell hr-shell lotus-ui" :class="{'embedded-workspace':embedded,'sidebar-collapsed':sidebarCollapsed}">
  
  <component :is="embedded?'section':'main'" class="stock-main"><WorkspaceTabs v-if="embedded" :items="tabs" :model-value="tab" @update:model-value="chooseTab($event)"/>
    
    <p v-if="error" class="stock-error" role="alert">{{error}}</p>
    <WorkspaceSummaryStrip v-if="['employees','onboarding','candidates'].includes(tab)" :items="[{label:'Hồ sơ nhân sự',value:overview.employees.length},{label:'Chờ tiếp nhận',value:missingCount},{label:'Ứng viên đang xử lý',value:overview.candidates.filter(x=>!['Hired','Rejected'].includes(x.status)).length}]"/>
    <WorkspaceListToolbar v-model="search" :searchable="['employees','onboarding','candidates'].includes(tab)" placeholder="Tìm tên, mã, chức danh hoặc số liên lạc…" :busy="busy||saving" @refresh="tab==='payroll'?loadPayroll():refresh()">
      <template #filters><label v-if="(session?.companies?.length||0)>1">Công ty <UiSelect v-model="company" :disabled="busy||saving" @change="resetPanels();refresh()"><option v-for="c in session?.companies" :key="c.name" :value="c.name">{{c.name}}</option></UiSelect></label><label v-if="tab==='payroll'">Tháng <UiInput v-model="payMonth" type="month" :max="today.slice(0,7)" aria-label="Tháng công" :disabled="busy||saving" @change="loadPayroll"/></label></template>
      <template v-if="['employees','onboarding'].includes(tab)"><a class="workspace-secondary-link" href="/hr-mobile">Ứng dụng điện thoại ↗</a><a class="workspace-secondary-link" href="/app/employee-transfer">Điều chuyển ↗</a><UiButton v-if="isManager" :disabled="saving" @click="emptyEmployee">＋ Thêm nhân viên</UiButton></template>
      <template v-if="tab==='payroll'"><a class="stock-button" :href="exportPayroll">Xuất bảng lương Excel</a></template>
      <template v-if="tab==='candidates'"><a class="workspace-secondary-link" href="/app/job-opening">Tin tuyển dụng ↗</a><UiButton :disabled="saving" @click="emptyCandidate">＋ Thêm ứng viên</UiButton></template>
    </WorkspaceListToolbar>

    <template v-if="tab==='employees'||tab==='onboarding'">
      <section class="stock-panel hr-table workspace-record-list workspace-employee-list"><table><colgroup><col><col><col><col><col><col><col class="workspace-col-status"><col class="workspace-col-actions"></colgroup><thead><tr><th>Mã</th><th>Họ tên</th><th>Chức danh</th><th>Vườn</th><th>Loại lao động</th><th>Hình thức công/lương</th><th>Tiếp nhận</th><th></th></tr></thead>
      <tbody><tr v-for="person in filteredEmployees" :key="person.name">
        <td>{{person.name}}</td><td><strong>{{person.employee_name}}</strong><small>{{person.department}}</small></td>
        <td>{{hrCatalogLabel(person.designation)||'—'}}</td><td>{{person.lotus_farm||'—'}}</td>
        <td>{{cats[person.lotus_worker_category]||contractTypeNames[person.employment_type]||person.employment_type||'—'}}</td>
        <td>{{bases[person.lotus_payment_basis]||'Chưa cấu hình'}}</td>
        <td><span class="workspace-status" :class="{'is-ready':person.lotus_onboarding_state==='Ready'}">{{person.lotus_onboarding_state==='Ready'?'Đã tiếp nhận':'Chờ tiếp nhận'}}</span><small>{{stateLabel(person.status)}}</small><small v-if="person.contract_end_date&&person.contract_end_date<=today">Hợp đồng đến hạn: {{person.contract_end_date}}</small></td>
        <td><UiButton v-if="isManager" variant="outline" size="sm" @click="openEmployee(person)">Xem / sửa</UiButton></td></tr>
      </tbody></table><p v-if="!filteredEmployees.length" class="stock-empty">Không có nhân viên trong phạm vi này.</p></section>
    </template>

    <template v-if="tab==='candidates'">
      <section class="stock-panel hr-table workspace-record-list"><table><colgroup><col><col><col><col><col><col class="workspace-col-status"><col class="workspace-col-actions"></colgroup><thead><tr><th>Ứng viên</th><th>Liên hệ</th><th>Chức danh</th><th>Vườn</th><th>Nguồn</th><th>Trạng thái</th><th></th></tr></thead>
      <tbody><tr v-for="c in filteredCandidates" :key="c.name"><td><strong>{{c.applicant_name}}</strong><small>{{c.applied_on}}</small></td><td>{{c.phone}}</td><td>{{c.designation}}</td><td>{{c.farm||'—'}}</td><td>{{c.source||'—'}}</td><td>{{stages[c.status]}}</td><td><UiButton variant="outline" size="sm" @click="openCandidate(c)">Xử lý</UiButton><UiButton v-if="isManager&&c.status==='Offered'&&!c.employee" size="sm" @click="startHire(c)">Tiếp nhận</UiButton></td></tr></tbody></table>
      <p v-if="!filteredCandidates.length" class="stock-empty">Chưa có ứng viên trong danh sách.</p></section>
    </template>

    <template v-if="tab==='operations'"><HrOperations :company="company" :manager="isManager"/></template>
    <template v-if="tab==='designations'">
      <div class="attendance-toolbar"><h2>Danh mục chức danh vườn</h2><UiButton v-if="isManager" :disabled="saving" @click="seed">Tạo các chức danh Lotus còn thiếu</UiButton></div>
      <p class="attendance-legend">Chức danh là Designation chuẩn HRMS, không tự gắn mức lương. Nhóm và tổ/đội thể hiện ở Department, Farm và Work Team. Mức lương do HRMS Salary Structure Assignment quyết định.</p>
      <div class="hr-role-grid"><section v-for="(names,group) in catalog.designation_groups" :key="group" class="stock-panel"><h3>{{group}}</h3><div v-for="name in names" :key="name" class="hr-role-row"><span>{{name}}</span><small>{{catalog.designations.some(d=>d.name===name)?'Đã cấu hình':'Chưa tạo'}}</small></div></section></div>
      <a href="/app/designation">Mở danh mục Designation chuẩn HRMS ↗</a>
    </template>

    <template v-if="tab==='payroll'&&isManager">
      <div class="hr-payroll">
        <section v-if="period" class="stock-panel" aria-label="Kỳ công">
          <div class="attendance-toolbar"><h3>Kỳ công {{period.month}}</h3><span class="workspace-status" :class="{'is-ready':period.status==='Closed'}">{{period.status==='Closed'?'Đã khóa':'Đang mở'}}</span>
            <UiButton v-if="period.status!=='Closed'" :disabled="saving||busy||period.future||period.blockers.length>0" @click="closePeriod">Khóa kỳ</UiButton>
            <UiButton v-else variant="outline" :disabled="saving||busy" @click="reopenReason='';reopenOpen=true">Mở lại kỳ</UiButton>
            <small v-if="period.status==='Closed'">Khóa bởi {{period.closed_by}} lúc {{String(period.closed_at||'').slice(0,16)}}</small><small v-else-if="period.future">Chỉ khóa khi tháng đã kết thúc.</small></div>
          <ul v-if="period.status!=='Closed'&&period.blockers.length" class="hr-payroll-blockers" aria-label="Việc cần xử lý trước khi khóa"><li v-for="b in period.blockers" :key="b.code"><strong>{{b.label}}</strong>: {{b.count}}<small v-if="b.employees"> · {{b.employees.slice(0,8).map(e=>e.employee_name).join(', ')}}{{b.employees.length>8?'…':''}}</small></li></ul>
          <p v-else-if="period.status!=='Closed'" class="hr-payroll-note">Đã đủ điều kiện khóa kỳ.</p>
        </section>
        <section v-if="readiness" class="stock-panel" aria-label="Đối soát trước kỳ lương">
          <WorkspaceSummaryStrip :items="[{label:'Đang làm',value:readiness.employees},{label:'Thiếu lương CB / đơn giá',value:readiness.employees_without_salary.length},{label:'Chấm công nháp',value:readiness.attendance_draft_count},{label:'Khoán đội chờ duyệt',value:readiness.crew_pending_count},{label:'Log máy chưa chuyển',value:readiness.open_punches}]"/>
          <p v-if="readiness.employees_without_salary.length" class="hr-payroll-warning">Thiếu mức lương: {{readiness.employees_without_salary.map(x=>x.employee_name+' ('+x.issue+')').join(', ')}}</p>
          <p v-if="readiness.onboarding_pending?.length" class="hr-payroll-warning">Đang làm nhưng chưa duyệt tiếp nhận: {{readiness.onboarding_pending.map(x=>x.employee_name).join(', ')}}</p>
        </section>
        <section v-if="sheet" class="stock-panel hr-table" aria-label="Bảng lương nhân sự">
          <div class="attendance-toolbar"><h3>Bảng lương {{sheet.month}}{{sheet.draft?' · bản nháp':''}}</h3><span>Đơn giá giờ = lương CB ÷ {{sheet.hours_base}} · Thu nhập <strong>{{money(sheet.totals.gross,sheet.currency)}}</strong> · Thực lĩnh trước thuế <strong>{{money(sheet.totals.net,sheet.currency)}}</strong></span></div>
          <table><thead><tr><th>Nhân viên</th><th>Lương CB</th><th>Công</th><th>Giờ thường</th><th>Giờ đêm</th><th>Giờ tăng ca</th><th>Lễ, phép (giờ)</th><th>Thu nhập</th><th>BH người LĐ</th><th>Thực lĩnh</th><th>Ghi chú</th></tr></thead>
          <tbody><tr v-for="e in sheet.employees" :key="e.employee"><td><strong>{{e.employee_name}}</strong><small>{{bases[e.payment_basis]||'—'}}</small></td><td>{{money(e.base,sheet.currency)}}</td><td>{{e.workdays}}</td><td>{{e.regular_hours}}</td><td>{{e.night_hours}}</td><td>{{e.ot_regular+e.ot_weekly_off+e.ot_holiday}}</td><td>{{e.paid_hours}}</td><td>{{money(e.gross,sheet.currency)}}</td><td>{{money(e.employee_insurance,sheet.currency)}}</td><td><strong>{{money(e.net,sheet.currency)}}</strong></td><td>{{e.via_crew?'Trả qua đội khoán':e.issues.join('; ')}}</td></tr></tbody></table>
          <p v-if="!sheet.employees.length" class="stock-empty">Chưa có nhân viên trong tháng này.</p>
        </section>
        <section v-if="run" class="stock-panel hr-table" aria-label="Lương HRMS và hạch toán">
          <div class="attendance-toolbar"><h3>Lương HRMS &amp; hạch toán</h3>
            <UiButton v-if="!run.structure" :disabled="saving||busy" @click="payrollStep('setup_payroll')">Cài đặt lương HRMS</UiButton>
            <UiButton v-else-if="!run.entry" :disabled="saving||busy||period?.status!=='Closed'" @click="payrollStep('create_payroll')">Tạo phiếu lương HRMS</UiButton>
            <UiButton v-else-if="run.slips.some(s=>s.docstatus===0)" :disabled="saving||busy" @click="payrollStep('post_payroll')">Duyệt &amp; hạch toán</UiButton>
            <small v-if="run.structure&&!run.entry&&period?.status!=='Closed'">Khóa kỳ công trước khi tạo phiếu lương.</small>
            <a v-if="run.entry" class="workspace-secondary-link" :href="'/app/payroll-entry/'+encodeURIComponent(run.entry.name)" target="_blank" rel="noopener">{{run.entry.name}} ↗</a>
            <a v-for="j in run.journal_entries" :key="j" class="workspace-secondary-link" :href="'/app/journal-entry/'+encodeURIComponent(j)" target="_blank" rel="noopener">Bút toán {{j}} ↗</a></div>
          <table v-if="run.slips.length"><thead><tr><th>Phiếu lương</th><th>Nhân viên</th><th>Thu nhập HRMS</th><th>Khấu trừ</th><th>Thực lĩnh</th><th>Lệch so với bảng Lotus</th><th>Trạng thái</th></tr></thead>
          <tbody><tr v-for="s in run.slips" :key="s.name"><td><a :href="'/app/salary-slip/'+encodeURIComponent(s.name)" target="_blank" rel="noopener">{{s.name}}</a></td><td>{{s.employee_name}}</td><td>{{money(s.gross_pay,sheet?.currency)}}</td><td>{{money(s.total_deduction,sheet?.currency)}}</td><td><strong>{{money(s.net_pay,sheet?.currency)}}</strong></td><td :class="{'hr-payroll-warning':Math.abs(s.difference)>1}">{{money(s.difference,sheet?.currency)}}</td><td>{{s.docstatus===1?(s.journal_entry?'Đã hạch toán':'Đã duyệt'):'Nháp'}}</td></tr></tbody></table>
          <p v-else-if="run.structure" class="hr-payroll-note">Chưa có phiếu lương HRMS cho tháng này.</p>
          <p class="hr-payroll-note">Thuế TNCN chưa tự tính: kế toán nhập bằng Additional Salary (Income Tax) trước khi duyệt phiếu.</p>
        </section>
        <section v-if="sheet" class="stock-panel hr-table" aria-label="Phải trả đội khoán">
          <div class="attendance-toolbar"><h3>Phải trả đội khoán</h3><span>Tổng <strong>{{money(sheet.totals.crew_amount,sheet.currency)}}</strong></span></div>
          <table><thead><tr><th>Đội</th><th>Đầu câu</th><th>Công việc</th><th>Khối lượng</th><th>Đơn giá</th><th>Thành tiền</th><th>Tổng công</th></tr></thead>
          <tbody><tr v-for="(c,i) in sheet.crews" :key="i"><td>{{c.team_name}}</td><td>{{c.foreman}}</td><td>{{c.work_name||'—'}}</td><td>{{c.completed_qty}} {{c.uom}}</td><td>{{money(c.unit_rate,sheet.currency)}}</td><td><strong>{{money(c.amount,sheet.currency)}}</strong></td><td>{{c.workdays}}</td></tr></tbody></table>
          <p v-if="!sheet.crews.length" class="stock-empty">Chưa có phiếu khoán đã duyệt trong tháng.</p>
        </section>
      </div>
    </template>

    <WorkspaceModal v-model="editCandidate" :title="selectedCandidate?'Cập nhật ứng viên':'Thêm ứng viên'" :busy="saving">
      <p v-if="error" class="stock-error" role="alert">{{error}}</p>
      <form @submit.prevent="saveCandidate"><div class="hr-form-grid">
        <label>Họ tên *<UiInput v-model="candidateForm.applicant_name" required maxlength="140"/></label>
        <label>Số điện thoại *<UiInput v-model="candidateForm.phone" required maxlength="25"/></label>
        <label>Email (không bắt buộc)<UiInput v-model="candidateForm.email" type="email"/></label>
        <label>Chức danh ứng tuyển *<UiSelect v-model="candidateForm.designation" required :disabled="candidateForm.status==='Hired'"><option value="">Chọn chức danh</option><option v-for="d in catalog.designations" :key="d.name" :value="d.name">{{hrCatalogLabel(d.designation_name)}}</option></UiSelect></label>
        <label>Vườn dự kiến<UiSelect v-model="candidateForm.farm"><option value="">Chưa xác định</option><option v-for="f in catalog.farms" :key="f.name" :value="f.name">{{f.farm_name}}</option></UiSelect></label>
        <label>Tin tuyển dụng<UiSelect v-model="candidateForm.job_opening" @change="chooseOpening"><option value="">Không gắn tin</option><option v-for="j in catalog.openings" :key="j.name" :value="j.name">{{j.job_title}}</option></UiSelect></label>
        <label>Ngày đăng ký<UiInput v-model="candidateForm.applied_on" type="date" required/></label>
        <label>Nguồn ứng tuyển<UiSelect v-model="candidateForm.source"><option v-for="s in ['Trực tiếp','Zalo','Facebook','Giới thiệu','Khác']" :key="s">{{s}}</option></UiSelect></label>
        <label>Trạng thái<UiSelect v-model="candidateForm.status" :disabled="!selectedCandidate||candidateForm.status==='Hired'"><option v-for="(label,k) in stages" :key="k" :value="k" :disabled="k==='Hired'">{{label}}</option></UiSelect></label>
        <label>Ngày phỏng vấn<UiInput v-model="candidateForm.interview_on" type="date"/></label>
        <label class="hr-span">Ghi chú đánh giá<UiTextarea v-model="candidateForm.notes" maxlength="2000"/></label>
      </div><div class="attendance-toolbar"><UiButton type="submit" :disabled="saving||candidateForm.status==='Hired'">{{saving?'Đang lưu…':'Lưu ứng viên'}}</UiButton><UiButton v-if="isManager&&candidateForm.status==='Offered'&&selectedCandidate" type="button" variant="outline" @click="startHire(candidateForm)">Tiếp nhận làm nhân viên</UiButton></div></form>
    </WorkspaceModal>

    <WorkspaceModal v-model="editEmployee" :title="selectedEmployee?'Hồ sơ '+selectedEmployee:candidateHire?'Tiếp nhận từ ứng viên':'Tạo hồ sơ nhân viên'" :busy="saving" width="1080px">
      <p v-if="error" class="stock-error" role="alert">{{error}}</p>
      <p class="attendance-legend">CCCD được lưu mã hóa; hệ thống chỉ hiển thị 4 số cuối, không gửi CCCD vào bảng nhân viên. Nhập CCCD mới chỉ khi tạo hoặc cần cập nhật. Đối chiếu giấy tờ gốc trước khi duyệt.</p>
      <div class="attendance-toolbar"><UiButton v-if="isManager" type="button" :disabled="saving" @click="cccdScanOpen=true"><LotusIcon name="scan"/>Quét QR CCCD</UiButton><span class="attendance-legend">Quét để tự điền thông tin. Chỉ lưu khi bấm Lưu hồ sơ.</span></div>
      <CccdQrScanner v-if="cccdScanOpen" @close="cccdScanOpen=false" @confirmed="applyScannedCccd"/>
      <form @submit.prevent="saveEmployee"><div class="hr-form-grid">
        <label>Họ tên *<UiInput v-model="employeeForm.employee_name" required :disabled="!!candidateHire" maxlength="140"/></label>
        <label>Giới tính *<UiSelect v-model="employeeForm.gender" required><option value="">Chọn</option><option v-for="g in catalog.genders" :key="g.name" :value="g.name">{{genderName[g.name]||hrCatalogLabel(g.name)}}</option></UiSelect></label>
        <label>Ngày sinh *<UiInput v-model="employeeForm.date_of_birth" type="date" :max="today" required/></label>
        <label>Ngày vào làm *<UiInput v-model="employeeForm.date_of_joining" type="date" required/></label>
        <label>Chức danh *<UiSelect v-model="employeeForm.designation" required :disabled="!!candidateHire"><option value="">Chọn</option><option v-for="d in catalog.designations" :key="d.name" :value="d.name">{{hrCatalogLabel(d.name)}}</option></UiSelect></label>
        <label>Phòng ban<UiSelect v-model="employeeForm.department"><option value="">Chưa gắn</option><option v-for="d in catalog.departments" :key="d.name" :value="d.name">{{hrCatalogLabel(d.department_name)}}</option></UiSelect></label>
        <label>Loại lao động *<UiSelect v-model="employeeForm.lotus_worker_category" required><option value="">Chọn</option><option v-for="c in catalog.worker_categories" :key="c" :value="c">{{cats[c]}}</option></UiSelect></label>
        <label>Cơ chế công/lương *<UiSelect v-model="employeeForm.lotus_payment_basis" required><option value="">Chọn</option><option v-for="v in catalog.payment_bases" :key="v" :value="v">{{bases[v]}}</option></UiSelect></label>
        <label>Vườn<UiSelect v-model="employeeForm.lotus_farm" :disabled="!!candidateHire" @change="employeeForm.lotus_work_team=''"><option value="">Chưa phân công</option><option v-for="f in catalog.farms" :key="f.name" :value="f.name">{{f.farm_name}}</option></UiSelect></label>
        <label>Tổ/đội nội bộ<UiSelect v-model="employeeForm.lotus_work_team"><option value="">Chưa phân tổ</option><option v-for="t in teamChoices" :key="t.name" :value="t.name">{{t.team_name}}</option></UiSelect></label>
        <label>Hình thức làm việc / hợp đồng<UiSelect v-model="employeeForm.employment_type"><option value="">Chưa chọn</option><option v-for="t in catalog.employment_types" :key="t.name" :value="t.name">{{contractTypeNames[t.name]||t.name}}</option></UiSelect></label>
        <label>Ngày hết hạn hợp đồng<UiInput v-model="employeeForm.contract_end_date" type="date"/></label>

        <label>Số điện thoại<UiInput v-model="employeeForm.cell_number" required/></label>
        <label>Email cá nhân<UiInput v-model="employeeForm.personal_email" type="email"/></label>
        <label>CCCD {{employeeForm.cccd_recorded?'(đã có, ****'+employeeForm.lotus_cccd_last4+')':''}}<UiInput v-model="employeeForm.cccd" autocomplete="off" inputmode="numeric" maxlength="18" placeholder="12 chữ số"/></label>
        <label>Ngày cấp CCCD<UiInput v-model="employeeForm.lotus_id_issue_on" type="date"/></label>
        <label>Nơi cấp CCCD<UiInput v-model="employeeForm.lotus_id_issue_at"/></label>
        <label>Người liên hệ khẩn cấp<UiInput v-model="employeeForm.lotus_emergency_name"/></label>
        <label>Điện thoại khẩn cấp<UiInput v-model="employeeForm.lotus_emergency_phone"/></label>
        <label>BHXH<UiInput v-model="employeeForm.lotus_social_insurance_no"/></label>
        <label>BHYT<UiInput v-model="employeeForm.health_insurance_no"/></label>
        <label>Mã số thuế cá nhân<UiInput v-model="employeeForm.lotus_tax_code"/></label>
        <label v-if="['Monthly','Mixed'].includes(employeeForm.lotus_payment_basis)">Lương cơ bản tháng (VND)<UiInput v-model.number="employeeForm.lotus_base_salary" type="number" min="0" step="1000"/></label>
        <label v-if="['Daywork','Mixed'].includes(employeeForm.lotus_payment_basis)">Đơn giá công nhật (VND)<UiInput v-model.number="employeeForm.lotus_daily_rate" type="number" min="0" step="1000"/></label>
        <label v-if="selectedEmployee&&employeeForm.lotus_payment_basis&&employeeForm.lotus_payment_basis!=='Piecework'">Mức lương áp dụng từ<UiInput v-model="employeeForm.pay_from_date" type="date" :min="employeeForm.date_of_joining"/></label>
        <label class="hr-span">Địa chỉ hiện tại<UiTextarea v-model="employeeForm.current_address"/></label>
        <label class="hr-span">Địa chỉ thường trú<UiTextarea v-model="employeeForm.permanent_address"/></label>
      </div>
      <div v-if="selectedEmployee" class="hr-checklist"><strong>Tiếp nhận: {{employeeForm.lotus_onboarding_state==='Ready'?'Đã duyệt':'Chưa duyệt'}}</strong>
        <p v-if="employeeForm.onboarding_gaps?.length">Còn thiếu: {{employeeForm.onboarding_gaps.join(', ')}}.</p>
        <p v-else>Đã đủ các trường dữ liệu tối thiểu. Kiểm tra chứng từ gốc và điều kiện hợp đồng trước khi duyệt.</p>
      </div>
      <div class="attendance-toolbar"><UiButton type="submit" :disabled="saving">{{saving?'Đang lưu…':'Lưu hồ sơ'}}</UiButton>
        <UiButton v-if="selectedEmployee&&employeeForm.lotus_onboarding_state!=='Ready'&&!employeeForm.onboarding_gaps?.length" variant="outline" type="button" :disabled="saving" @click="approveOnboarding">Duyệt tiếp nhận & kích hoạt</UiButton>
        <a v-if="selectedEmployee" class="stock-button" :href="'/app/employee/'+encodeURIComponent(selectedEmployee)" target="_blank" rel="noopener">Employee HRMS ↗</a>
        <UiButton v-if="selectedEmployee&&employeeForm.status!=='Left'" variant="outline" type="button" :disabled="saving" @click="startOffboard">Cho nghỉ việc</UiButton>
        <small v-if="employeeForm.status==='Left'">Đã nghỉ việc từ {{employeeForm.relieving_date}}</small>
      </div></form>
    </WorkspaceModal>

    <WorkspaceModal v-model="offboardOpen" :title="'Cho nghỉ việc · '+(employeeForm.employee_name||'')" :busy="saving">
      <p v-if="error" class="stock-error" role="alert">{{error}}</p>
      <form @submit.prevent="confirmOffboard"><div class="hr-form-grid">
        <label>Ngày làm việc cuối *<UiInput v-model="offboard.relieving_date" type="date" required :min="employeeForm.date_of_joining"/></label>
        <label class="hr-span">Lý do *<UiTextarea v-model="offboard.reason" required maxlength="500"/></label>
      </div><p class="attendance-legend">Hồ sơ chuyển sang Đã nghỉ; phân công tổ và mã máy chấm công đang mở được đóng tại ngày này.</p>
      <div class="attendance-toolbar"><UiButton type="submit" :disabled="saving">{{saving?'Đang lưu…':'Xác nhận nghỉ việc'}}</UiButton><UiButton type="button" variant="outline" :disabled="saving" @click="offboardOpen=false">Quay lại</UiButton></div></form>
    </WorkspaceModal>

    <WorkspaceModal v-model="reopenOpen" :title="'Mở lại kỳ công '+payMonth" :busy="saving">
      <p v-if="error" class="stock-error" role="alert">{{error}}</p>
      <form @submit.prevent="reopenPeriod"><label class="hr-span">Lý do mở lại *<UiTextarea v-model="reopenReason" required minlength="5" maxlength="500"/></label>
      <div class="attendance-toolbar"><UiButton type="submit" :disabled="saving">Mở lại kỳ</UiButton><UiButton type="button" variant="outline" :disabled="saving" @click="reopenOpen=false">Quay lại</UiButton></div></form>
    </WorkspaceModal>
  </component>
<WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" :alert-only="confirmAlert" @answer="finishConfirm"/>
</div>
</template>
