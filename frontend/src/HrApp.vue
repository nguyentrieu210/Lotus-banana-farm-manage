<script setup>
import {computed,onMounted,reactive,ref} from 'vue'
import WorkspaceBar from './components/WorkspaceBar.vue'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import UiSelect from './components/ui/select/Select.vue'
import {Textarea as UiTextarea} from './components/ui/textarea'
import {call,setCSRF} from './api'
import {sidebarCollapsed} from './workspace'

const api=(name,args={},write=false)=>call('lotus_farm.hr_workspace.'+name,args,write)
const session=ref(null),company=ref(''),tab=ref('employees'),busy=ref(false),saving=ref(false),error=ref(''),notice=ref('')
const catalog=ref({farms:[],departments:[],designations:[],teams:[],grades:[],employment_types:[],genders:[],openings:[],designation_groups:{},worker_categories:[],payment_bases:[]})
const overview=ref({employees:[],candidates:[]}),payroll=ref({grades:[],assignments:[]}),readiness=ref(null)
const search=ref(''),editEmployee=ref(false),editCandidate=ref(false),candidateHire=ref(null)
const selectedEmployee=ref(null),selectedCandidate=ref(null)
const employeeForm=reactive({}),candidateForm=reactive({})
const isManager=computed(()=>session.value?.is_hr_manager||false)
const money=(n,cur='VND')=>Number(n||0).toLocaleString('vi-VN',{style:'currency',currency:cur||'VND'})
const cats={Permanent:'Dài hạn', 'Fixed-term':'Hợp đồng xác định hạn',Seasonal:'Thời vụ',Probation:'Thử việc'}
const bases={Monthly:'Lương tháng',Daywork:'Công nhật',Piecework:'Khoán sản lượng',Mixed:'Hỗn hợp'}
const stages={New:'Mới',Screening:'Sàng lọc',Interview:'Phỏng vấn',Offered:'Đã mời nhận việc',Hold:'Tạm giữ',Rejected:'Không đạt',Hired:'Đã tiếp nhận'}
const genderName={Male:'Nam',Female:'Nữ',Other:'Khác'}
const routes=[{id:'employees',label:'Hồ sơ nhân viên'},{id:'candidates',label:'Tuyển dụng'},{id:'onboarding',label:'Tiếp nhận'},{id:'designations',label:'Chức danh'},{id:'payroll',label:'Cấu hình lương'}]
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
function resetPanels(){editEmployee.value=false;editCandidate.value=false;candidateHire.value=null;selectedEmployee.value=null;selectedCandidate.value=null;error.value=''}
function chooseTab(t){resetPanels();search.value='';tab.value=t;if(t==='payroll')loadPayroll()}
async function refresh(){if(!company.value)return;busy.value=true;error.value='';try{
  const [c,data]=await Promise.all([api('catalogue',{company:company.value}),api('overview',{company:company.value})])
  catalog.value=c;overview.value=data
}catch(e){error.value=e.message}finally{busy.value=false}}
async function loadPayroll(){if(!isManager.value||!company.value)return;busy.value=true;error.value='';try{[payroll.value,readiness.value]=await Promise.all([api('payroll_overview',{company:company.value}),api('payroll_readiness',{company:company.value,month:today.value.slice(0,7)})])}catch(e){error.value=e.message}finally{busy.value=false}}
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
    lotus_tax_code:'',lotus_social_insurance_no:'',health_insurance_no:'',contract_end_date:'',lotus_onboarding_state:'Pending'})
  editEmployee.value=true
}
async function openEmployee(item){if(!isManager.value)return;busy.value=true;error.value=''
  try{const data=await api('employee_detail',{company:company.value,employee:item.name})
    resetPanels();clear(employeeForm);Object.assign(employeeForm,data,{cccd:''});selectedEmployee.value=item.name;editEmployee.value=true
  }catch(e){error.value=e.message}finally{busy.value=false}}
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
async function seed(){if(!window.confirm('Tạo các chức danh Lotus chưa có trong HRMS? Hành động không xóa hoặc sửa chức danh hiện hữu.'))return
  saving.value=true;error.value=''
  try{const r=await api('seed_designations',{company:company.value},true);notice.value='Đã tạo thêm '+r.count+' chức danh.';await refresh()}catch(e){error.value=e.message}finally{saving.value=false}}
onMounted(init)
</script>

<template>
<div class="stock-shell hr-shell" :class="{'sidebar-collapsed':sidebarCollapsed}">
  <aside class="stock-sidebar">
    <a class="stock-brand" href="/lotus/mobile"><img class="lotus-brand-image" :src="'/assets/lotus_farm/images/lotus-agritech.jpg'" alt="Lotus Agritech"></a>
    <p class="stock-nav-label">NHÂN SỰ LOTUS</p>
    <nav aria-label="Module nhân sự"><UiButton v-for="item in tabs" :key="item.id" variant="outline" :class="{selected:tab===item.id}" @click="chooseTab(item.id)">{{item.label}}</UiButton></nav>
    <div class="stock-sidebar-bottom"><a href="/lotus/cham-cong">Chấm công ↗</a><a href="/desk/hr-setup">Quản trị HRMS ↗</a></div>
  </aside>
  <main class="stock-main">
    <WorkspaceBar :user="session?.user" :title="tabs.find(x=>x.id===tab)?.label||'Nhân sự'" :actions="actions"/>
    <p v-if="error" class="stock-error" role="alert">{{error}}</p><p v-if="notice" class="stock-success" role="status">{{notice}}</p>
    <div class="stock-scope"><label>Công ty <UiSelect v-model="company" :disabled="busy||saving" @change="resetPanels();refresh()"><option v-for="c in session?.companies" :key="c.name" :value="c.name">{{c.name}}</option></UiSelect></label>
      <label v-if="['employees','onboarding','candidates'].includes(tab)">Tìm nhanh <UiInput v-model="search" placeholder="Tên, mã, chức danh hoặc số liên lạc"/></label>
      <UiButton variant="outline" :disabled="busy||saving" @click="tab==='payroll'?loadPayroll():refresh()">{{busy?'Đang tải…':'Làm mới'}}</UiButton>
    </div>
    <section class="hr-headline">
      <div><small>HỒ SƠ NHÂN SỰ</small><strong>{{overview.employees.length}}</strong><span>Người đã ghi nhận trong Employee</span></div>
      <div><small>TIẾP NHẬN</small><strong>{{missingCount}}</strong><span>Chưa xác nhận đủ hồ sơ</span></div>
      <div><small>TUYỂN DỤNG</small><strong>{{overview.candidates.filter(x=>x.status!=='Hired'&&x.status!=='Rejected').length}}</strong><span>Ứng viên đang xử lý</span></div>
    </section>

    <template v-if="tab==='employees'||tab==='onboarding'">
      <div class="attendance-toolbar"><h2>{{tab==='employees'?'Danh sách nhân viên':'Tiếp nhận & kích hoạt'}}</h2>
        <UiButton v-if="isManager" :disabled="saving" @click="emptyEmployee">+ Thêm nhân viên</UiButton><a class="stock-button" href="/app/employee-transfer">Điều chuyển nhân viên (HRMS) ↗</a>
      </div>
      <p class="attendance-legend">Công nhân thử việc, thời vụ hoặc dài hạn có hồ sơ Employee. Đội khoán/nhà thầu chấm theo đội ở module Chấm công, không tự tạo nhân viên giả. Nhân viên chờ tiếp nhận chưa được kích hoạt.</p>
      <section class="stock-panel hr-table"><table><thead><tr><th>Mã</th><th>Họ tên</th><th>Chức danh</th><th>Nông trường</th><th>Loại lao động</th><th>Hình thức công/lương</th><th>Tiếp nhận</th><th></th></tr></thead>
      <tbody><tr v-for="person in filteredEmployees" :key="person.name">
        <td>{{person.name}}</td><td><strong>{{person.employee_name}}</strong><small>{{person.department}}</small></td>
        <td>{{person.designation||'—'}}</td><td>{{person.lotus_farm||'—'}}</td>
        <td>{{cats[person.lotus_worker_category]||person.employment_type||'—'}}</td>
        <td>{{bases[person.lotus_payment_basis]||'Chưa cấu hình'}}</td>
        <td>{{person.lotus_onboarding_state==='Ready'?'Đã tiếp nhận':'Chờ tiếp nhận'}} · {{person.status}}<small v-if="person.contract_end_date&&person.contract_end_date<=today">Hợp đồng đến hạn: {{person.contract_end_date}}</small></td>
        <td><UiButton v-if="isManager" variant="outline" size="sm" @click="openEmployee(person)">Xem / sửa</UiButton></td></tr>
      </tbody></table><p v-if="!filteredEmployees.length" class="stock-empty">Không có nhân viên trong phạm vi này.</p></section>
    </template>

    <template v-if="tab==='candidates'">
      <div class="attendance-toolbar"><h2>Ứng viên và tuyển dụng</h2><UiButton :disabled="saving" @click="emptyCandidate">+ Ứng viên mới</UiButton><a class="stock-button" href="/app/job-opening">Tin tuyển dụng HRMS ↗</a><a class="stock-button" href="/app/job-applicant">Ứng viên HRMS có email ↗</a></div>
      <p class="attendance-legend">Ứng viên Lotus có thể đăng ký bằng số điện thoại, không ép cung cấp email giả. Ứng viên có email hoặc tuyển văn phòng vẫn có thể sử dụng Job Applicant/Job Offer chuẩn HRMS.</p>
      <section class="stock-panel hr-table"><table><thead><tr><th>Ứng viên</th><th>Liên hệ</th><th>Chức danh</th><th>Nông trường</th><th>Nguồn</th><th>Trạng thái</th><th></th></tr></thead>
      <tbody><tr v-for="c in filteredCandidates" :key="c.name"><td><strong>{{c.applicant_name}}</strong><small>{{c.applied_on}}</small></td><td>{{c.phone}}</td><td>{{c.designation}}</td><td>{{c.farm||'—'}}</td><td>{{c.source||'—'}}</td><td>{{stages[c.status]}}</td><td><UiButton variant="outline" size="sm" @click="openCandidate(c)">Xử lý</UiButton><UiButton v-if="isManager&&c.status==='Offered'&&!c.employee" size="sm" @click="startHire(c)">Tiếp nhận</UiButton></td></tr></tbody></table>
      <p v-if="!filteredCandidates.length" class="stock-empty">Chưa có ứng viên trong danh sách.</p></section>
    </template>

    <template v-if="tab==='designations'">
      <div class="attendance-toolbar"><h2>Danh mục chức danh nông trường</h2><UiButton v-if="isManager" :disabled="saving" @click="seed">Tạo các chức danh Lotus còn thiếu</UiButton></div>
      <p class="attendance-legend">Chức danh là Designation chuẩn HRMS, không tự gắn mức lương. Nhóm và tổ/đội thể hiện ở Department, Farm và Work Team. Mức lương do HRMS Salary Structure Assignment quyết định.</p>
      <div class="hr-role-grid"><section v-for="(names,group) in catalog.designation_groups" :key="group" class="stock-panel"><h3>{{group}}</h3><div v-for="name in names" :key="name" class="hr-role-row"><span>{{name}}</span><small>{{catalog.designations.some(d=>d.name===name)?'Đã cấu hình':'Chưa tạo'}}</small></div></section></div>
      <a href="/app/designation">Mở danh mục Designation chuẩn HRMS ↗</a>
    </template>

    <template v-if="tab==='payroll'&&isManager">
      <div class="attendance-toolbar"><h2>Chính sách và cấu hình lương</h2><a href="/app/salary-structure-assignment" class="stock-button">Quyết định lương HRMS ↗</a><a href="/app/salary-structure" class="stock-button">Cấu trúc lương ↗</a><a href="/app/employee-grade" class="stock-button">Cấp bậc ↗</a></div>
      <p class="attendance-legend">Đơn giá công khoán theo công việc nằm trong Work Type, chỉ là giá trị kế hoạch. Lương cơ bản và thay đổi lương phải lập qua Salary Structure Assignment theo ngày hiệu lực. Không lấy giá khoán x khối lượng để tự động lập Salary Slip khi chưa có dữ liệu duyệt và kiểm soát đối soát.</p>
      <section v-if="readiness" class="stock-panel"><h3>Đối soát trước kỳ lương · {{readiness.month}}</h3><p>Nhân viên đang làm: <strong>{{readiness.employees}}</strong> · Chưa có quyết định lương: <strong>{{readiness.employees_without_salary.length}}</strong> · Phiếu chấm công nháp: <strong>{{readiness.attendance_draft_count}}</strong> · Phiếu khoán đội chờ duyệt: <strong>{{readiness.crew_pending_count}}</strong>.</p><p class="attendance-legend">Giá trị khoán đội đã duyệt (chưa phải lương): {{money(readiness.crew_approved_amount)}}; {{readiness.note}}</p><p v-if="readiness.employees_without_salary.length">Chưa cấu hình Salary Structure Assignment: {{readiness.employees_without_salary.map(x=>x.employee_name).join(', ')}}</p></section><section class="stock-panel hr-table"><h3>Cấp bậc lương cấu hình</h3><table><thead><tr><th>Bậc</th><th>Cấu trúc mặc định</th><th>Lương cơ sở tham chiếu</th></tr></thead><tbody><tr v-for="g in payroll.grades" :key="g.name"><td>{{g.name}}</td><td>{{g.default_salary_structure||'Chưa thiết lập'}}</td><td>{{money(g.default_base_pay,g.currency)}}</td></tr></tbody></table></section>
      <section class="stock-panel hr-table"><h3>Quyết định lương đã duyệt mới nhất theo nhân viên</h3><table><thead><tr><th>Mã nhân viên</th><th>Cấu trúc lương</th><th>Hiệu lực từ</th><th>Lương cơ bản</th></tr></thead><tbody><tr v-for="(a,i) in payroll.assignments" :key="i"><td>{{a.employee}}</td><td>{{a.salary_structure}}</td><td>{{a.from_date}}</td><td>{{money(a.base,a.currency)}}</td></tr></tbody></table></section>
    </template>

    <section v-if="editCandidate&&tab==='candidates'" class="stock-panel hr-editor">
      <div class="attendance-toolbar"><h2>{{selectedCandidate?'Cập nhật ứng viên':'Thêm ứng viên'}}</h2><UiButton variant="outline" @click="editCandidate=false">Đóng</UiButton></div>
      <form @submit.prevent="saveCandidate"><div class="hr-form-grid">
        <label>Họ tên *<UiInput v-model="candidateForm.applicant_name" required maxlength="140"/></label>
        <label>Số điện thoại *<UiInput v-model="candidateForm.phone" required maxlength="25"/></label>
        <label>Email (không bắt buộc)<UiInput v-model="candidateForm.email" type="email"/></label>
        <label>Chức danh ứng tuyển *<UiSelect v-model="candidateForm.designation" required :disabled="candidateForm.status==='Hired'"><option value="">Chọn chức danh</option><option v-for="d in catalog.designations" :key="d.name" :value="d.name">{{d.designation_name}}</option></UiSelect></label>
        <label>Nông trường dự kiến<UiSelect v-model="candidateForm.farm"><option value="">Chưa xác định</option><option v-for="f in catalog.farms" :key="f.name" :value="f.name">{{f.farm_name}}</option></UiSelect></label>
        <label>Tin tuyển dụng<UiSelect v-model="candidateForm.job_opening" @change="chooseOpening"><option value="">Không gắn tin</option><option v-for="j in catalog.openings" :key="j.name" :value="j.name">{{j.job_title}}</option></UiSelect></label>
        <label>Ngày đăng ký<UiInput v-model="candidateForm.applied_on" type="date" required/></label>
        <label>Nguồn ứng tuyển<UiSelect v-model="candidateForm.source"><option v-for="s in ['Trực tiếp','Zalo','Facebook','Giới thiệu','Khác']" :key="s">{{s}}</option></UiSelect></label>
        <label>Trạng thái<UiSelect v-model="candidateForm.status" :disabled="!selectedCandidate||candidateForm.status==='Hired'"><option v-for="(label,k) in stages" :key="k" :value="k" :disabled="k==='Hired'">{{label}}</option></UiSelect></label>
        <label>Ngày phỏng vấn<UiInput v-model="candidateForm.interview_on" type="date"/></label>
        <label class="hr-span">Ghi chú đánh giá<UiTextarea v-model="candidateForm.notes" maxlength="2000"/></label>
      </div><div class="attendance-toolbar"><UiButton type="submit" :disabled="saving||candidateForm.status==='Hired'">{{saving?'Đang lưu…':'Lưu ứng viên'}}</UiButton><UiButton v-if="isManager&&candidateForm.status==='Offered'&&selectedCandidate" type="button" variant="outline" @click="startHire(candidateForm)">Tiếp nhận làm nhân viên</UiButton></div></form>
    </section>

    <section v-if="editEmployee&&['employees','onboarding'].includes(tab)" class="stock-panel hr-editor">
      <div class="attendance-toolbar"><h2>{{selectedEmployee?'Hồ sơ '+selectedEmployee:candidateHire?'Tiếp nhận từ ứng viên':'Tạo hồ sơ nhân viên'}}</h2><UiButton variant="outline" @click="editEmployee=false;candidateHire=null">Đóng</UiButton></div>
      <p class="attendance-legend">CCCD được lưu mã hóa; hệ thống chỉ hiển thị 4 số cuối, không gửi CCCD vào bảng nhân viên. Nhập CCCD mới chỉ khi tạo hoặc cần cập nhật. Đối chiếu giấy tờ gốc trước khi duyệt.</p>
      <form @submit.prevent="saveEmployee"><div class="hr-form-grid">
        <label>Họ tên *<UiInput v-model="employeeForm.employee_name" required :disabled="!!candidateHire" maxlength="140"/></label>
        <label>Giới tính *<UiSelect v-model="employeeForm.gender" required><option value="">Chọn</option><option v-for="g in catalog.genders" :key="g.name" :value="g.name">{{genderName[g.name]||g.name}}</option></UiSelect></label>
        <label>Ngày sinh *<UiInput v-model="employeeForm.date_of_birth" type="date" :max="today" required/></label>
        <label>Ngày vào làm *<UiInput v-model="employeeForm.date_of_joining" type="date" required/></label>
        <label>Chức danh *<UiSelect v-model="employeeForm.designation" required :disabled="!!candidateHire"><option value="">Chọn</option><option v-for="d in catalog.designations" :key="d.name" :value="d.name">{{d.name}}</option></UiSelect></label>
        <label>Phòng ban<UiSelect v-model="employeeForm.department"><option value="">Chưa gắn</option><option v-for="d in catalog.departments" :key="d.name" :value="d.name">{{d.department_name}}</option></UiSelect></label>
        <label>Loại lao động *<UiSelect v-model="employeeForm.lotus_worker_category" required><option value="">Chọn</option><option v-for="c in catalog.worker_categories" :key="c" :value="c">{{cats[c]}}</option></UiSelect></label>
        <label>Cơ chế công/lương *<UiSelect v-model="employeeForm.lotus_payment_basis" required><option value="">Chọn</option><option v-for="v in catalog.payment_bases" :key="v" :value="v">{{bases[v]}}</option></UiSelect></label>
        <label>Nông trường<UiSelect v-model="employeeForm.lotus_farm" :disabled="!!candidateHire" @change="employeeForm.lotus_work_team=''"><option value="">Chưa phân công</option><option v-for="f in catalog.farms" :key="f.name" :value="f.name">{{f.farm_name}}</option></UiSelect></label>
        <label>Tổ/đội nội bộ<UiSelect v-model="employeeForm.lotus_work_team"><option value="">Chưa phân tổ</option><option v-for="t in teamChoices" :key="t.name" :value="t.name">{{t.team_name}}</option></UiSelect></label>
        <label>Loại HĐ lao động chuẩn HRMS<UiSelect v-model="employeeForm.employment_type"><option value="">Chưa chọn</option><option v-for="t in catalog.employment_types" :key="t.name" :value="t.name">{{t.name}}</option></UiSelect></label>
        <label>Ngày hết hạn hợp đồng<UiInput v-model="employeeForm.contract_end_date" type="date"/></label>
        <label>Cấp bậc HRMS<UiSelect v-model="employeeForm.grade"><option value="">Chưa phân bậc</option><option v-for="g in catalog.grades" :key="g.name" :value="g.name">{{g.name}}</option></UiSelect></label>
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
      </div></form>
    </section>
  </main>
</div>
</template>