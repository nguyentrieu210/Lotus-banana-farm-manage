<script setup>
const props=defineProps({embedded:Boolean,navigationKey:String,hrView:{type:String,default:'employees'}})
import {computed,onMounted,onBeforeUnmount,onDeactivated,nextTick,reactive,ref,watch} from 'vue'
import {useRouter} from 'vue-router'
import {normalizeHrView} from './hr-navigation.js'
import WorkspaceListToolbar from './components/WorkspaceListToolbar.vue'
import WorkspaceSummaryStrip from './components/WorkspaceSummaryStrip.vue'
import DataTable from './components/DataTable.vue'
import WorkspaceModal from './components/WorkspaceModal.vue'
import WorkspaceConfirm from './components/WorkspaceConfirm.vue'
import LotusIcon from './components/LotusIcon.vue'
import {useWorkspaceConfirm} from './use-workspace-confirm'
import HrOperations from './components/HrOperations.vue'
import HrPayrollPeriod from './components/hr/HrPayrollPeriod.vue'
import CccdQrScanner from './components/CccdQrScanner.vue'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import UiSelect from './components/ui/select/Select.vue'
import {Textarea as UiTextarea} from './components/ui/textarea'
import {DatePicker} from './components/ui/date-picker'
import {FormField} from './components/ui/form-field'
import {useNoticeToast} from './use-toast'
import {call,setCSRF} from './api'
import {DEFAULT_CCCD_ISSUER} from './cccd-issuer'
import {sidebarCollapsed} from './workspace'
import {stateLabel} from './labels'
import {hrCatalogLabel} from './hr-catalog-labels'
import {formatDate} from './format'
const {open:confirmOpen,title:confirmTitle,message:confirmMessage,alertOnly:confirmAlert,ask:askConfirm,tell,finish:finishConfirm}=useWorkspaceConfirm()

// /lotus/nhan-su: employee records, recruitment, onboarding, organisation, imports, attendance devices and the
// monthly period / payroll (HR Manager). Native HRMS stays the source of truth for Employee and payroll.
const api=(name,args={},write=false)=>call('lotus_farm.hr_workspace.'+name,args,write)
const session=ref(null),company=ref(''),tab=ref(normalizeHrView(props.hrView)),busy=ref(false),saving=ref(false),error=ref(''),notice=ref('')
const router=props.embedded?useRouter():null
const catalog=ref({farms:[],departments:[],designations:[],teams:[],grades:[],employment_types:[],genders:[],openings:[],designation_groups:{},worker_categories:[],payment_bases:[]})
const overview=ref({employees:[],candidates:[]})
const employeeFilters=reactive({farm:'',department:'',team:'',status:'',category:'',stage:''})
const search=ref(''),editEmployee=ref(false),editCandidate=ref(false),candidateHire=ref(null),cccdScanOpen=ref(false),offboardOpen=ref(false)
const selectedEmployee=ref(null),selectedCandidate=ref(null),ops=ref(null),payroll=ref(null)
const revealedCccd=ref('')
const showHireDetails=ref(false)
const employeeForm=reactive({}),candidateForm=reactive({}),offboard=reactive({relieving_date:'',reason:''})
const isManager=computed(()=>session.value?.is_hr_manager||false)
const cats={Permanent:'Dài hạn','Fixed-term':'Hợp đồng xác định hạn',Seasonal:'Thời vụ',Probation:'Thử việc'}
const bases={Monthly:'Lương tháng',Daywork:'Công nhật',Piecework:'Khoán sản lượng',Mixed:'Hỗn hợp'}
const stages={New:'Mới',Screening:'Sàng lọc',Interview:'Phỏng vấn',Offered:'Đã mời nhận việc',Hold:'Tạm giữ',Rejected:'Không đạt',Hired:'Đã tiếp nhận'}
const stageTone={New:'is-muted',Screening:'is-draft',Interview:'is-draft',Offered:'is-review',Hold:'is-muted',Rejected:'is-muted',Hired:'is-approved'}
const genderName={Male:'Nam',Female:'Nữ',Other:'Khác'}
const contractTypeNames={Apprentice:'Học việc',Intern:'Thực tập',Piecework:'Khoán theo sản phẩm',Commission:'Theo hoa hồng',Contract:'Hợp đồng',Probation:'Thử việc','Part-time':'Bán thời gian','Full-time':'Toàn thời gian'}
const listTab=computed(()=>['employees','onboarding','candidates'].includes(tab.value))
const filteredEmployees=computed(()=>overview.value.employees.filter(e=>{
 if(tab.value==='onboarding'&&e.lotus_onboarding_state==='Ready')return false
 if(Object.entries({farm:'lotus_farm',department:'department',team:'lotus_work_team',status:'status',category:'lotus_worker_category'}).some(([k,f])=>employeeFilters[k]&&e[f]!==employeeFilters[k]))return false
 const needle=search.value.toLocaleLowerCase('vi-VN')
 return [e.name,e.employee_name,e.designation,e.department,e.lotus_farm].some(v=>String(v||'').toLocaleLowerCase('vi-VN').includes(needle))
}))
const filteredCandidates=computed(()=>overview.value.candidates.filter(c=>(!employeeFilters.farm||c.farm===employeeFilters.farm)&&(!employeeFilters.stage||c.status===employeeFilters.stage)&&
 [c.applicant_name,c.phone,c.designation,c.status].some(v=>String(v||'').toLocaleLowerCase('vi-VN').includes(search.value.toLocaleLowerCase('vi-VN')))
))
const teamChoices=computed(()=>catalog.value.teams.filter(t=>t.farm===employeeForm.lotus_farm&&t.lotus_team_type!=='Contractor'))
const missingCount=computed(()=>overview.value.employees.filter(e=>e.lotus_onboarding_state!=='Ready').length)
const designationCount=computed(()=>{const all=Object.values(catalog.value.designation_groups||{}).flat();return {all:all.length,done:all.filter(n=>catalog.value.designations.some(d=>d.name===n)).length}})
const today=computed(()=>session.value?.today||'')
const contractDue=e=>e.contract_end_date&&e.contract_end_date<=today.value
const candidateColumns=[
 {field:'applicant_name',headerName:'Ứng viên',minWidth:180,valueGetter:p=>p.data.applicant_name+' · '+formatDate(p.data.applied_on)},
 {field:'phone',headerName:'Liên hệ',minWidth:135},
 {field:'designation',headerName:'Chức danh',valueGetter:p=>hrCatalogLabel(p.data.designation),minWidth:155},
 {field:'farm',headerName:'Vườn',minWidth:125},
 {field:'source',headerName:'Nguồn',minWidth:125},
 {field:'status',headerName:'Trạng thái',valueGetter:p=>stages[p.data.status]||p.data.status,minWidth:150},
 {field:'candidate_action',headerName:'Thao tác',valueGetter:p=>isManager.value&&p.data.status==='Offered'&&!p.data.employee?'Tiếp nhận':'Xử lý',minWidth:115,sortable:false}
]
function candidateCellAction(event){
 if(event.colDef?.field!=='candidate_action'||!event.data)return
 if(isManager.value&&event.data.status==='Offered'&&!event.data.employee)startHire(event.data)
 else openCandidate(event.data)
}
const employeeColumns=computed(()=>[
 {field:'name',headerName:'Mã',minWidth:160},
 {field:'employee_name',headerName:'Họ tên',minWidth:200,flex:1.5},
 {field:'department',headerName:'Phòng ban',minWidth:170,valueFormatter:p=>p.value||'—'},
 {field:'designation',headerName:'Chức danh',minWidth:170,valueGetter:p=>hrCatalogLabel(p.data.designation)||'—'},
 {field:'lotus_farm',headerName:'Vườn',minWidth:150,valueGetter:p=>catalog.value.farms.find(f=>f.name===p.data.lotus_farm)?.farm_name||p.data.lotus_farm||'—'},
 {field:'lotus_worker_category',headerName:'Loại lao động',minWidth:170,valueGetter:p=>cats[p.data.lotus_worker_category]||contractTypeNames[p.data.employment_type]||p.data.employment_type||'—'},
 {field:'lotus_payment_basis',headerName:'Cơ chế lương',minWidth:150,valueGetter:p=>bases[p.data.lotus_payment_basis]||'Chưa cấu hình'},
 {field:'lotus_onboarding_state',headerName:'Tiếp nhận',minWidth:165,cellClass:'lotus-grid-status',valueGetter:p=>p.data.lotus_onboarding_state==='Ready'?'Đã tiếp nhận':'Chờ tiếp nhận'},
 {field:'status',headerName:'Trạng thái',minWidth:180,valueGetter:p=>stateLabel(p.data.status)+(contractDue(p.data)?' · Hợp đồng đến hạn '+formatDate(p.data.contract_end_date):'')},
])
function clear(obj){for(const k of Object.keys(obj))delete obj[k]}
function resetPanels(){revealedCccd.value='';cccdScanOpen.value=false;editEmployee.value=false;editCandidate.value=false;candidateHire.value=null;selectedEmployee.value=null;selectedCandidate.value=null;error.value=''}
function applyView(t){resetPanels();offboardOpen.value=false;search.value='';tab.value=normalizeHrView(t)}
const formSnapshots=reactive({employee:'',candidate:'',offboard:''})
for(const [key,open,form] of [['employee',editEmployee,employeeForm],['candidate',editCandidate,candidateForm],['offboard',offboardOpen,offboard]]){
 watch(open,value=>{if(value)formSnapshots[key]=JSON.stringify(form)},{flush:'post'})
}
const dirty=computed(()=>!!(
 (editEmployee.value&&formSnapshots.employee!==JSON.stringify(employeeForm))||
 (editCandidate.value&&formSnapshots.candidate!==JSON.stringify(candidateForm))||
 (offboardOpen.value&&formSnapshots.offboard!==JSON.stringify(offboard))||ops.value?.hasUnsavedChanges||payroll.value?.hasUnsavedChanges))
async function allowNavigation(){
 if(saving.value||ops.value?.isSaving||payroll.value?.isSaving){await tell('Đang lưu dữ liệu. Vui lòng chờ hoàn tất.');return false}
 return !dirty.value||await askConfirm('Có thay đổi chưa lưu. Rời mục này và bỏ các thay đổi đang nhập?','Rời nghiệp vụ nhân sự')
}
watch(()=>props.hrView,view=>{if(normalizeHrView(view)!==tab.value){ops.value?.discardChanges?.();payroll.value?.discardChanges?.();applyView(view)}})
let removeNavigationGuard
onMounted(()=>{
 if(router)removeNavigationGuard=router.beforeEach((to,from)=>{
  if(from.path!=='/nhan-su'||(to.path===from.path&&normalizeHrView(to.query.hr_view)===normalizeHrView(from.query.hr_view)))return true
  return allowNavigation()
 })
})
onBeforeUnmount(()=>removeNavigationGuard?.())
onDeactivated(()=>{resetPanels();offboardOpen.value=false;ops.value?.discardChanges?.();payroll.value?.discardChanges?.()})
async function refresh(){if(!company.value)return;busy.value=true;error.value=''
 try{const [c,data]=await Promise.all([api('catalogue',{company:company.value}),api('overview',{company:company.value})]);catalog.value=c;overview.value=data}
 catch(e){error.value=e.message}finally{busy.value=false}}
function reload(){if(['organization','import','devices'].includes(tab.value))ops.value?.refresh();refresh()}
async function init(){busy.value=true
 try{session.value=await api('bootstrap');setCSRF(session.value.csrf_token);if(tab.value==='payroll'&&!isManager.value){if(router)await router.replace('/denied');else error.value='Không có quyền xem kỳ công & bảng lương.';return}company.value=session.value.companies[0]?.name||'';await refresh()}
 catch(e){error.value=e.message}finally{busy.value=false}}

function emptyEmployee(){
 resetPanels();clear(employeeForm)
 Object.assign(employeeForm,{employee_name:'',gender:'',date_of_birth:'',date_of_joining:today.value,designation:'',department:'',
  employment_type:'',grade:'',reports_to:'',lotus_worker_category:'Seasonal',lotus_payment_basis:'Daywork',
  lotus_farm:'',lotus_work_team:'',cell_number:'',personal_email:'',current_address:'',permanent_address:'',
  cccd:'',lotus_id_issue_on:'',lotus_id_issue_at:DEFAULT_CCCD_ISSUER,lotus_emergency_name:'',lotus_emergency_phone:'',
  lotus_tax_code:'',lotus_social_insurance_no:'',health_insurance_no:'',contract_end_date:'',lotus_onboarding_state:'Pending',
  lotus_base_salary:0,lotus_daily_rate:0,lotus_dependents:0,lotus_pit_commitment:0})
 editEmployee.value=true
}
async function openEmployee(item){if(!isManager.value)return;busy.value=true;error.value=''
 try{const data=await api('employee_detail',{company:company.value,employee:item.name});resetPanels();clear(employeeForm);Object.assign(employeeForm,data,{cccd:''});selectedEmployee.value=item.name;editEmployee.value=true}
 catch(e){error.value=e.message}finally{busy.value=false}}
async function revealEmployeeCccd(){
 if(!selectedEmployee.value||!isManager.value)return
 try{
  const result=await api('reveal_employee_cccd',{company:company.value,employee:selectedEmployee.value},true)
  revealedCccd.value=result.cccd||''
 }catch(e){error.value=e.message}
}
async function applyScannedCccd(info){
 if(!isManager.value||!editEmployee.value||saving.value)return
 // Candidate name comes from the hiring record and cannot be overwritten here.
 if(candidateHire.value&&employeeForm.employee_name.trim()!==info.employee_name){await tell('Tên trên QR khác tên ứng viên đã tiếp nhận. Kiểm tra và sửa hồ sơ ứng viên trước.');return}
 const changed=['employee_name','date_of_birth','gender','current_address','lotus_id_issue_on'].some(key=>employeeForm[key]&&String(employeeForm[key]).trim()!==String(info[key]||'').trim())
 if(changed&&!await askConfirm('Thông tin QR khác dữ liệu đang nhập. Dùng thông tin trên QR để thay các trường này?'))return
 saving.value=true;error.value=''
 try{
  const check=await api('check_cccd',{company:company.value,cccd:info.cccd,employee:selectedEmployee.value},true)
  if(check.duplicate){await tell('CCCD này đã tồn tại trong hệ thống. Không thể nhập trùng.');return}
  // The residence field is not necessarily the registered permanent address.
  Object.assign(employeeForm,info);cccdScanOpen.value=false
  notice.value='Đã điền từ QR. Kiểm tra nơi cư trú và các trường còn thiếu trước khi lưu hồ sơ.'
 }catch(e){error.value=e.message;await tell('Không kiểm tra được CCCD: '+e.message)}
 finally{saving.value=false}
}
async function saveEmployee(){if(saving.value)return;saving.value=true;error.value='';notice.value=''
 const hiring=!!candidateHire.value
 try{
  const args={company:company.value,values:{...employeeForm}}
  const result=candidateHire.value?await api('hire_candidate',{...args,candidate:candidateHire.value.name,modified:candidateHire.value.modified,approve_basic:true},true):await api('save_employee',{...args,employee:selectedEmployee.value,modified:employeeForm.modified},true)
  notice.value=result.onboarding_state==='Ready'&&candidateHire.value?'Đã tiếp nhận cơ bản và kích hoạt nhân viên '+result.name+'. Có thể bổ sung giấy tờ sau.':'Đã lưu nhân viên '+result.name+'.'+(selectedEmployee.value?'':' Nhân sự mới ở trạng thái Chờ duyệt tiếp nhận cơ bản.')
  resetPanels();await refresh()
  if(hiring){saving.value=false;if(router){const query={...router.currentRoute.value.query};delete query.hr_view;await router.push({path:'/nhan-su',query})}else applyView('employees')}
 }catch(e){error.value=e.message}finally{saving.value=false}
}
async function approveOnboarding(){if(!selectedEmployee.value)return
 if(!await askConfirm('Duyệt tiếp nhận cơ bản và kích hoạt nhân viên? CCCD, địa chỉ và liên hệ khẩn cấp có thể bổ sung sau.'))return
 saving.value=true;error.value=''
 try{await api('set_onboarding_ready',{company:company.value,employee:selectedEmployee.value,modified:employeeForm.modified},true);notice.value='Đã duyệt tiếp nhận và kích hoạt nhân viên.';resetPanels();await refresh()}
 catch(e){error.value=e.message}finally{saving.value=false}}
function startOffboard(){offboard.relieving_date=today.value;offboard.reason='';error.value='';offboardOpen.value=true}
async function confirmOffboard(){saving.value=true;error.value=''
 try{await api('offboard_employee',{company:company.value,employee:selectedEmployee.value,modified:employeeForm.modified,...offboard},true);offboardOpen.value=false;notice.value='Đã ghi nhận nghỉ việc.';resetPanels();await refresh()}
 catch(e){error.value=e.message}finally{saving.value=false}}

function emptyCandidate(){resetPanels();clear(candidateForm);Object.assign(candidateForm,{applicant_name:'',phone:'',email:'',designation:'',farm:'',job_opening:'',applied_on:today.value,source:'Trực tiếp',status:'New',interview_on:'',notes:''});editCandidate.value=true}
async function openCandidate(item){busy.value=true;error.value=''
 try{const details=await api('candidate_detail',{company:company.value,candidate:item.name});resetPanels();selectedCandidate.value=item.name;clear(candidateForm);Object.assign(candidateForm,details);editCandidate.value=true}
 catch(e){error.value=e.message}finally{busy.value=false}}
async function saveCandidate(){saving.value=true;error.value=''
 try{const result=await api('save_candidate',{company:company.value,name:selectedCandidate.value,modified:candidateForm.modified,values:{...candidateForm}},true);notice.value='Đã lưu ứng viên '+result.name;resetPanels();await refresh()}
 catch(e){error.value=e.message}finally{saving.value=false}}
async function startHire(item){
 if(router){const query={...router.currentRoute.value.query,hr_view:'onboarding'};const failure=await router.push({path:'/nhan-su',query});if(failure)return;await nextTick()}
 else applyView('onboarding')
 emptyEmployee();showHireDetails.value=false;candidateHire.value=item;employeeForm.employee_name=item.applicant_name;employeeForm.designation=item.designation;employeeForm.lotus_farm=item.farm||'';employeeForm.cell_number=item.phone
}
function chooseOpening(){const opening=catalog.value.openings.find(x=>x.name===candidateForm.job_opening);if(opening)candidateForm.designation=opening.designation}
async function seed(){if(!await askConfirm('Tạo các chức danh Lotus chưa có trong HRMS? Hành động không xóa hoặc sửa chức danh hiện hữu.'))return
 saving.value=true;error.value=''
 try{const r=await api('seed_designations',{company:company.value},true);notice.value='Đã tạo thêm '+r.count+' chức danh.';await refresh()}
 catch(e){error.value=e.message}finally{saving.value=false}}
onMounted(init)
// Success messages show as toasts (errors stay inline next to the form).
useNoticeToast(notice)
</script>

<template>
<div class="stock-shell hr-shell lotus-ui" :class="{'embedded-workspace':embedded,'sidebar-collapsed':sidebarCollapsed}">
 <component :is="embedded?'section':'main'" class="stock-main">
  <p v-if="error&&!editEmployee&&!editCandidate&&!offboardOpen" class="stock-error" role="alert">{{error}}</p>

  <WorkspaceListToolbar v-if="tab!=='payroll'" v-model="search" :searchable="listTab" placeholder="Tìm tên, mã, chức danh hoặc số liên lạc…" :busy="busy||saving" @refresh="reload">
   <template #filters><label v-if="(session?.companies?.length||0)>1">Công ty <UiSelect v-model="company" :disabled="busy||saving" @change="Object.keys(employeeFilters).forEach(k=>employeeFilters[k]='');resetPanels();refresh()"><option v-for="c in session?.companies" :key="c.name" :value="c.name">{{c.name}}</option></UiSelect></label>
   <template v-if="listTab"><label>Vườn<UiSelect v-model="employeeFilters.farm" @change="employeeFilters.team='' "><option value="">Tất cả vườn</option><option v-for="f in catalog.farms" :key="f.name" :value="f.name">{{f.farm_name||f.name}}</option></UiSelect></label>
   <template v-if="tab!=='candidates'"><label>Phòng ban<UiSelect v-model="employeeFilters.department"><option value="">Tất cả phòng ban</option><option v-for="d in catalog.departments" :key="d.name" :value="d.name">{{d.department_name||d.name}}</option></UiSelect></label><label>Tổ/đội<UiSelect v-model="employeeFilters.team"><option value="">Tất cả tổ/đội</option><option v-for="t in catalog.teams.filter(t=>!employeeFilters.farm||t.farm===employeeFilters.farm)" :key="t.name" :value="t.name">{{t.team_name||t.name}}</option></UiSelect></label><label>Loại lao động<UiSelect v-model="employeeFilters.category"><option value="">Tất cả</option><option v-for="(label,key) in cats" :key="key" :value="key">{{label}}</option></UiSelect></label><label>Trạng thái<UiSelect v-model="employeeFilters.status"><option value="">Tất cả</option><option v-for="s in ['Active','Inactive','Suspended','Left']" :key="s" :value="s">{{stateLabel(s)}}</option></UiSelect></label></template>
   <label v-else>Trạng thái ứng viên<UiSelect v-model="employeeFilters.stage"><option value="">Tất cả</option><option v-for="(label,key) in stages" :key="key" :value="key">{{label}}</option></UiSelect></label></template>
   </template>
   <template v-if="['employees','onboarding'].includes(tab)"><a class="workspace-secondary-link" href="/hr-mobile">Ứng dụng điện thoại ↗</a><a class="workspace-secondary-link" href="/app/employee-transfer">Điều chuyển ↗</a><UiButton v-if="isManager" :disabled="saving" @click="emptyEmployee"><LotusIcon name="plus"/>Thêm nhân viên</UiButton></template>
   <template v-if="tab==='candidates'"><a class="workspace-secondary-link" href="/app/job-opening">Tin tuyển dụng ↗</a><UiButton :disabled="saving" @click="emptyCandidate"><LotusIcon name="plus"/>Thêm ứng viên</UiButton></template>
   <template v-if="tab==='organization'&&isManager"><UiButton variant="outline" :disabled="saving" @click="seed">Tạo chức danh Lotus còn thiếu</UiButton></template>
  </WorkspaceListToolbar>
  <WorkspaceSummaryStrip v-if="listTab" :items="[{label:'Hồ sơ nhân sự',value:overview.employees.length},{label:'Chờ tiếp nhận',value:missingCount},{label:'Ứng viên đang xử lý',value:overview.candidates.filter(x=>!['Hired','Rejected'].includes(x.status)).length}]"/>

  <template v-if="tab==='employees'||tab==='onboarding'">
   <section class="stock-panel workspace-employee-list" :aria-label="tab==='onboarding'?'Nhân viên chờ tiếp nhận':'Hồ sơ nhân viên'">
    <DataTable :key="company+':'+tab" :storage-key="'hr-employees:'+company+':'+tab" :rows="filteredEmployees" :columns="employeeColumns" :loading="busy" :interactive="isManager" :empty="tab==='onboarding'?'Không còn nhân viên chờ tiếp nhận.':'Không có nhân viên trong phạm vi này.'" @open="openEmployee"/>
   </section>
  </template>

  <template v-if="tab==='candidates'">
   <section class="stock-panel hr-table workspace-record-list" aria-label="Ứng viên"><DataTable :rows="filteredCandidates" :columns="candidateColumns" row-key="name" storage-key="hr-candidates" @cell-open="candidateCellAction" />
     <div v-if="isManager&&filteredCandidates.some(c=>c.status==='Offered'&&!c.employee)" class="hr-candidate-ready"><div v-for="c in filteredCandidates.filter(c=>c.status==='Offered'&&!c.employee)" :key="c.name" class="hr-ops-actions"><strong>{{c.applicant_name}}</strong><UiButton size="sm" @click="startHire(c)">Tiếp nhận</UiButton></div></div>
    <p v-if="!filteredCandidates.length" class="stock-empty">Chưa có ứng viên trong danh sách.</p></section>
  </template>

  <template v-if="tab==='organization'">
   <HrOperations ref="ops" :company="company" :manager="isManager" view="organization"/>
   <section class="tk-card hr-roles" aria-label="Danh mục chức danh">
    <header class="tk-card__head"><h3>Danh mục chức danh</h3><span class="tk-pill" :class="designationCount.done===designationCount.all?'is-approved':'is-draft'">{{designationCount.done}}/{{designationCount.all}} đã tạo</span><span class="tk-actions__spacer"></span><a class="workspace-secondary-link" href="/app/designation">Designation HRMS ↗</a></header>
    <div class="hr-role-grid"><div v-for="(names,group) in catalog.designation_groups" :key="group" class="hr-role-group"><h4>{{group}}</h4><ul><li v-for="name in names" :key="name"><span>{{name}}</span><span class="tk-pill" :class="catalog.designations.some(d=>d.name===name)?'is-approved':'is-muted'">{{catalog.designations.some(d=>d.name===name)?'Đã tạo':'Chưa tạo'}}</span></li></ul></div></div>
   </section>
  </template>
  <HrOperations v-if="tab==='import'" ref="ops" :company="company" :manager="isManager" view="import"/>
  <HrOperations v-if="tab==='devices'" :key="'devices'" ref="ops" :company="company" :manager="isManager" view="devices"/>
  <HrPayrollPeriod v-if="tab==='payroll'&&isManager" ref="payroll" :company="company" :today="today" @notice="notice=$event" @error="error=$event"/>

  <WorkspaceModal v-model="editCandidate" :title="selectedCandidate?'Cập nhật ứng viên':'Thêm ứng viên'" :busy="saving">
   <p v-if="error" class="stock-error" role="alert">{{error}}</p>
   <form @submit.prevent="saveCandidate"><div class="hr-form-grid">
    <FormField label="Họ tên" required v-slot="f"><UiInput v-bind="f" v-model="candidateForm.applicant_name" maxlength="140"/></FormField>
    <FormField label="Số điện thoại" required v-slot="f"><UiInput v-bind="f" v-model="candidateForm.phone" maxlength="25" inputmode="tel"/></FormField>
    <FormField label="Email" hint="Không bắt buộc" v-slot="f"><UiInput v-bind="f" v-model="candidateForm.email" type="email"/></FormField>
    <FormField label="Chức danh ứng tuyển" required v-slot="f"><UiSelect v-bind="f" v-model="candidateForm.designation" :disabled="candidateForm.status==='Hired'"><option value="">Chọn chức danh</option><option v-for="d in catalog.designations" :key="d.name" :value="d.name">{{hrCatalogLabel(d.designation_name)}}</option></UiSelect></FormField>
    <FormField label="Vườn dự kiến" v-slot="f"><UiSelect v-bind="f" v-model="candidateForm.farm"><option value="">Chưa xác định</option><option v-for="farm in catalog.farms" :key="farm.name" :value="farm.name">{{farm.farm_name}}</option></UiSelect></FormField>
    <FormField label="Tin tuyển dụng" v-slot="f"><UiSelect v-bind="f" v-model="candidateForm.job_opening" @change="chooseOpening"><option value="">Không gắn tin</option><option v-for="j in catalog.openings" :key="j.name" :value="j.name">{{j.job_title}}</option></UiSelect></FormField>
    <FormField label="Ngày đăng ký" required v-slot="f"><DatePicker v-bind="f" v-model="candidateForm.applied_on" aria-label="Ngày đăng ký"/></FormField>
    <FormField label="Nguồn ứng tuyển" v-slot="f"><UiSelect v-bind="f" v-model="candidateForm.source"><option v-for="s in ['Trực tiếp','Zalo','Facebook','Giới thiệu','Khác']" :key="s">{{s}}</option></UiSelect></FormField>
    <FormField label="Trạng thái" v-slot="f"><UiSelect v-bind="f" v-model="candidateForm.status" :disabled="!selectedCandidate||candidateForm.status==='Hired'"><option v-for="(text,k) in stages" :key="k" :value="k" :disabled="k==='Hired'">{{text}}</option></UiSelect></FormField>
    <FormField label="Ngày phỏng vấn" v-slot="f"><DatePicker v-bind="f" v-model="candidateForm.interview_on" aria-label="Ngày phỏng vấn"/></FormField>
    <FormField label="Ghi chú đánh giá" class="hr-span" v-slot="f"><UiTextarea v-bind="f" v-model="candidateForm.notes" maxlength="2000"/></FormField>
   </div><div class="hr-form-footer"><UiButton v-if="isManager&&candidateForm.status==='Offered'&&selectedCandidate" type="button" variant="outline" @click="startHire(candidateForm)">Tiếp nhận làm nhân viên</UiButton><span class="tk-actions__spacer"></span><UiButton type="button" variant="outline" :disabled="saving" @click="editCandidate=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||candidateForm.status==='Hired'">{{saving?'Đang lưu…':'Lưu ứng viên'}}</UiButton></div></form>
  </WorkspaceModal>

  <WorkspaceModal v-model="editEmployee" :title="selectedEmployee?employeeForm.employee_name+' · '+selectedEmployee:candidateHire?'Tiếp nhận từ ứng viên':'Tạo hồ sơ nhân viên'" :busy="saving" width="1080px">
   <p v-if="error" class="stock-error" role="alert">{{error}}</p>
   <div v-if="selectedEmployee" class="hr-checklist" :class="employeeForm.onboarding_gaps?.length?'is-warn':'is-ok'">
    <strong>{{employeeForm.lotus_onboarding_state==='Ready'?'Đã tiếp nhận cơ bản':'Chờ duyệt tiếp nhận cơ bản'}}</strong>
    <span v-if="employeeForm.onboarding_gaps?.length">Còn thiếu: {{employeeForm.onboarding_gaps.join(', ')}}.</span>
    <span v-else-if="employeeForm.lotus_onboarding_state!=='Ready'">Đủ thông tin cơ bản để tiếp nhận. Giấy tờ chi tiết có thể bổ sung sau.</span>
    <span v-if="employeeForm.dossier_gaps?.length">Hồ sơ bổ sung sau: {{employeeForm.dossier_gaps.join(', ')}}.</span>
    <UiButton v-if="employeeForm.lotus_onboarding_state!=='Ready'&&!employeeForm.onboarding_gaps?.length" size="sm" type="button" :disabled="saving" @click="approveOnboarding">Duyệt tiếp nhận cơ bản</UiButton>
   </div>
   <CccdQrScanner v-if="cccdScanOpen" @close="cccdScanOpen=false" @confirmed="applyScannedCccd"/>
   <form @submit.prevent="saveEmployee">
    <p v-if="candidateHire" class="hr-form-note">Duyệt một lần để tạo và kích hoạt nhân viên. CCCD, địa chỉ, liên hệ khẩn cấp và bảo hiểm có thể bổ sung sau.</p>
    <UiButton v-if="candidateHire" type="button" variant="outline" size="sm" :aria-expanded="showHireDetails" @click="showHireDetails=!showHireDetails">{{showHireDetails?'Ẩn thông tin bổ sung':'Bổ sung giấy tờ và thông tin khác'}}</UiButton>
    <h3 class="hr-form-section">Thông tin cá nhân<UiButton v-if="isManager" type="button" variant="outline" size="sm" :disabled="saving" @click="cccdScanOpen=true"><LotusIcon name="scan"/>Quét QR CCCD</UiButton></h3>
    <div class="hr-form-grid">
     <FormField label="Họ tên" required v-slot="f"><UiInput v-bind="f" v-model="employeeForm.employee_name" :disabled="!!candidateHire" maxlength="140"/></FormField>
     <FormField label="Giới tính" required v-slot="f"><UiSelect v-bind="f" v-model="employeeForm.gender"><option value="">Chọn</option><option v-for="g in catalog.genders" :key="g.name" :value="g.name">{{genderName[g.name]||hrCatalogLabel(g.name)}}</option></UiSelect></FormField>
     <FormField label="Ngày sinh" required v-slot="f"><DatePicker v-bind="f" v-model="employeeForm.date_of_birth" :max="today" aria-label="Ngày sinh"/></FormField>
     <FormField label="Số điện thoại" required v-slot="f"><UiInput v-bind="f" v-model="employeeForm.cell_number" inputmode="tel"/></FormField>
     <FormField v-if="!candidateHire||showHireDetails" label="Email cá nhân" v-slot="f"><UiInput v-bind="f" v-model="employeeForm.personal_email" type="email"/></FormField>
     <FormField v-if="!candidateHire||showHireDetails" label="Người liên hệ khẩn cấp" v-slot="f"><UiInput v-bind="f" v-model="employeeForm.lotus_emergency_name"/></FormField>
     <FormField v-if="!candidateHire||showHireDetails" label="Điện thoại khẩn cấp" v-slot="f"><UiInput v-bind="f" v-model="employeeForm.lotus_emergency_phone" inputmode="tel"/></FormField>
     <FormField v-if="!candidateHire||showHireDetails" label="Địa chỉ hiện tại" class="hr-span" v-slot="f"><UiTextarea v-bind="f" v-model="employeeForm.current_address" rows="2"/></FormField>
     <FormField v-if="!candidateHire||showHireDetails" label="Địa chỉ thường trú" class="hr-span" v-slot="f"><UiTextarea v-bind="f" v-model="employeeForm.permanent_address" rows="2"/></FormField>
    </div>
    <template v-if="!candidateHire||showHireDetails"><h3 class="hr-form-section">Giấy tờ & bảo hiểm</h3>
    <div class="hr-form-grid">
     <FormField :label="'CCCD'+(employeeForm.cccd_recorded?' (đã có ****'+employeeForm.lotus_cccd_last4+')':'')" hint="Lưu mã hóa; chỉ nhập khi tạo mới hoặc cần cập nhật." v-slot="f"><UiInput v-bind="f" v-model="employeeForm.cccd" autocomplete="off" inputmode="numeric" maxlength="18" placeholder="12 chữ số"/></FormField>
     <div v-if="selectedEmployee&&employeeForm.cccd_recorded" class="hr-span" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
      <strong v-if="revealedCccd">{{revealedCccd}}</strong><span v-else>CCCD: ••••••••{{employeeForm.lotus_cccd_last4}}</span>
      <UiButton type="button" variant="outline" size="sm" :disabled="saving" @click="revealedCccd?revealedCccd='':revealEmployeeCccd()">{{revealedCccd?'Ẩn CCCD':'Hiện đủ 12 số'}}</UiButton>
     </div>
     <FormField label="Ngày cấp CCCD" v-slot="f"><DatePicker v-bind="f" v-model="employeeForm.lotus_id_issue_on" :max="today" aria-label="Ngày cấp CCCD"/></FormField>
     <FormField label="Nơi cấp CCCD" v-slot="f"><UiInput v-bind="f" v-model="employeeForm.lotus_id_issue_at"/></FormField>
     <FormField label="Số BHXH" hint="Có số BHXH thì bảng lương trừ 10,5% bảo hiểm." v-slot="f"><UiInput v-bind="f" v-model="employeeForm.lotus_social_insurance_no"/></FormField>
     <FormField label="Số BHYT" v-slot="f"><UiInput v-bind="f" v-model="employeeForm.health_insurance_no"/></FormField>
     <FormField label="Mã số thuế cá nhân" v-slot="f"><UiInput v-bind="f" v-model="employeeForm.lotus_tax_code"/></FormField>
     <FormField label="Số người phụ thuộc đã đăng ký" hint="Mỗi người được giảm trừ khi tính thuế TNCN (hợp đồng từ 3 tháng)." v-slot="f"><UiInput v-bind="f" v-model.number="employeeForm.lotus_dependents" type="number" min="0" max="20"/></FormField>
     <FormField label="Cam kết 08/CK-TNCN" hint="Lao động thời vụ có thu nhập dưới mức chịu thuế: không khấu trừ 10%." v-slot="f"><label class="hr-check"><input v-bind="f" v-model="employeeForm.lotus_pit_commitment" type="checkbox" :true-value="1" :false-value="0">Đã nộp cam kết</label></FormField>
    </div>
    </template><h3 class="hr-form-section">Công việc & hợp đồng</h3>
    <div class="hr-form-grid">
     <FormField label="Ngày vào làm" required v-slot="f"><DatePicker v-bind="f" v-model="employeeForm.date_of_joining" aria-label="Ngày vào làm"/></FormField>
     <FormField label="Chức danh" required v-slot="f"><UiSelect v-bind="f" v-model="employeeForm.designation" :disabled="!!candidateHire"><option value="">Chọn</option><option v-for="d in catalog.designations" :key="d.name" :value="d.name">{{hrCatalogLabel(d.name)}}</option></UiSelect></FormField>
     <FormField v-if="!candidateHire||showHireDetails" label="Phòng ban" v-slot="f"><UiSelect v-bind="f" v-model="employeeForm.department"><option value="">Chưa gắn</option><option v-for="d in catalog.departments" :key="d.name" :value="d.name">{{hrCatalogLabel(d.department_name)}}</option></UiSelect></FormField>
     <FormField label="Vườn" v-slot="f"><UiSelect v-bind="f" v-model="employeeForm.lotus_farm" :disabled="!!candidateHire" @change="employeeForm.lotus_work_team=''"><option value="">Chưa phân công</option><option v-for="farm in catalog.farms" :key="farm.name" :value="farm.name">{{farm.farm_name}}</option></UiSelect></FormField>
     <FormField v-if="!candidateHire||showHireDetails" label="Tổ/đội nội bộ" v-slot="f"><UiSelect v-bind="f" v-model="employeeForm.lotus_work_team"><option value="">Chưa phân tổ</option><option v-for="t in teamChoices" :key="t.name" :value="t.name">{{t.team_name}}</option></UiSelect></FormField>
     <FormField label="Loại lao động" required v-slot="f"><UiSelect v-bind="f" v-model="employeeForm.lotus_worker_category"><option value="">Chọn</option><option v-for="c in catalog.worker_categories" :key="c" :value="c">{{cats[c]}}</option></UiSelect></FormField>
     <FormField v-if="!candidateHire||showHireDetails" label="Hình thức làm việc / hợp đồng" v-slot="f"><UiSelect v-bind="f" v-model="employeeForm.employment_type"><option value="">Chưa chọn</option><option v-for="t in catalog.employment_types" :key="t.name" :value="t.name">{{contractTypeNames[t.name]||t.name}}</option></UiSelect></FormField>
     <FormField v-if="!candidateHire||showHireDetails" label="Ngày hết hạn hợp đồng" v-slot="f"><DatePicker v-bind="f" v-model="employeeForm.contract_end_date" :min="employeeForm.date_of_joining" aria-label="Ngày hết hạn hợp đồng"/></FormField>
    </div>
    <h3 class="hr-form-section">Lương</h3>
    <div class="hr-form-grid">
     <FormField label="Cơ chế công/lương" required v-slot="f"><UiSelect v-bind="f" v-model="employeeForm.lotus_payment_basis"><option value="">Chọn</option><option v-for="v in catalog.payment_bases" :key="v" :value="v">{{bases[v]}}</option></UiSelect></FormField>
     <FormField v-if="['Monthly','Mixed'].includes(employeeForm.lotus_payment_basis)" label="Lương cơ bản tháng (VND)" hint="Cho 26 công × 8 giờ" v-slot="f"><UiInput v-bind="f" v-model.number="employeeForm.lotus_base_salary" type="number" min="0" step="1000"/></FormField>
     <FormField v-if="['Daywork','Mixed'].includes(employeeForm.lotus_payment_basis)" label="Đơn giá công nhật (VND)" hint="Lương CB = đơn giá × 26" v-slot="f"><UiInput v-bind="f" v-model.number="employeeForm.lotus_daily_rate" type="number" min="0" step="1000"/></FormField>
     <FormField v-if="selectedEmployee&&employeeForm.lotus_payment_basis&&employeeForm.lotus_payment_basis!=='Piecework'" label="Mức lương áp dụng từ" hint="Mặc định đầu tháng này" v-slot="f"><DatePicker v-bind="f" v-model="employeeForm.pay_from_date" :min="employeeForm.date_of_joining" aria-label="Mức lương áp dụng từ"/></FormField>
     <p v-if="employeeForm.lotus_payment_basis==='Piecework'" class="hr-span hr-form-note">Khoán sản lượng: tiền trả qua đội khoán, không lên phiếu lương cá nhân.</p>
    </div>
    <div class="hr-form-footer">
     <a v-if="selectedEmployee" class="workspace-secondary-link" :href="'/lotus_employee_print?company='+encodeURIComponent(company)+'&employee='+encodeURIComponent(selectedEmployee)" target="_blank" rel="noopener">In phiếu tiếp nhận có chữ ký ↗</a>
     <a v-if="selectedEmployee" class="workspace-secondary-link" :href="'/app/employee/'+encodeURIComponent(selectedEmployee)" target="_blank" rel="noopener">Mở trong HRMS ↗</a>
     <UiButton v-if="selectedEmployee&&employeeForm.status!=='Left'" variant="outline" type="button" :disabled="saving" @click="startOffboard">Cho nghỉ việc</UiButton>
     <small v-if="employeeForm.status==='Left'">Đã nghỉ việc từ {{formatDate(employeeForm.relieving_date)}}</small>
     <span class="tk-actions__spacer"></span>
     <UiButton type="button" variant="outline" :disabled="saving" @click="editEmployee=false">Hủy</UiButton>
     <UiButton type="submit" :disabled="saving">{{saving?'Đang lưu…':candidateHire?'Duyệt tiếp nhận cơ bản':'Lưu hồ sơ'}}</UiButton>
    </div>
   </form>
  </WorkspaceModal>

  <WorkspaceModal v-model="offboardOpen" :title="'Cho nghỉ việc · '+(employeeForm.employee_name||'')" :busy="saving" width="560px">
   <p v-if="error" class="stock-error" role="alert">{{error}}</p>
   <form @submit.prevent="confirmOffboard"><div class="hr-form-grid hr-form-grid--single">
    <FormField label="Ngày làm việc cuối" required v-slot="f"><DatePicker v-bind="f" v-model="offboard.relieving_date" :min="employeeForm.date_of_joining" aria-label="Ngày làm việc cuối"/></FormField>
    <FormField label="Lý do" required hint="Phân công tổ và mã máy chấm công đang mở sẽ được đóng tại ngày này." v-slot="f"><UiTextarea v-bind="f" v-model="offboard.reason" maxlength="500"/></FormField>
   </div><div class="hr-form-footer"><span class="tk-actions__spacer"></span><UiButton type="button" variant="outline" :disabled="saving" @click="offboardOpen=false">Quay lại</UiButton><UiButton type="submit" variant="destructive" :disabled="saving">{{saving?'Đang lưu…':'Xác nhận nghỉ việc'}}</UiButton></div></form>
  </WorkspaceModal>
 </component>
 <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" :alert-only="confirmAlert" :cancel-label="confirmTitle==='Rời nghiệp vụ nhân sự'?'Ở lại':'Hủy'" :confirm-label="confirmTitle==='Rời nghiệp vụ nhân sự'?'Rời đi':'Đồng ý'" @answer="finishConfirm"/>
</div>
</template>
