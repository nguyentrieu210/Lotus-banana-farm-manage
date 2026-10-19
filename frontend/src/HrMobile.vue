<script setup>
import {computed,onMounted,onBeforeUnmount,reactive,ref} from 'vue'
import {Icon} from 'vant'
import LotusMobileShell from './components/LotusMobileShell.vue'
import LotusMobileInput from './components/LotusMobileInput.vue'
import LotusMobileSelect from './components/LotusMobileSelect.vue'
import LotusMobileFeedback from './components/LotusMobileFeedback.vue'
import LotusMobileButton from './components/LotusMobileButton.vue'
import LotusMobileDialog from './components/LotusMobileDialog.vue'
import {useMobileConfirm} from './use-mobile-confirm'
import {logoutPwa} from './mobile-push-session'
import CccdQrScanner from './components/CccdQrScanner.vue'
import {call,setCSRF} from './api'
import {useMobileViewport} from './use-mobile-viewport'
const api=(name,args={},post=false)=>call('lotus_farm.hr_workspace.'+name,args,post)
const {keyboard}=useMobileViewport()
const {dialog:confirmDialog,message:confirmMessage,ask:askConfirm,finish:finishConfirm}=useMobileConfirm()
const session=ref(null),company=ref(''),busy=ref(false),saving=ref(false)
const initialTab=new URLSearchParams(window.location.search).get('tab')
const error=ref(''),notice=ref(''),screen=ref(['home','employees','onboarding','profile','candidates'].includes(initialTab)?initialTab:'home'),search=ref(''),scanOpen=ref(false)
const people=ref([]),candidates=ref([]),catalog=ref({farms:[],teams:[],departments:[],designations:[],genders:[],employment_types:[],grades:[],worker_categories:[],payment_bases:[]})
const employee=reactive({}),candidate=reactive({})
const selectedEmployee=ref(null),selectedCandidate=ref(null),hireFrom=ref(null)
const roots=['home','employees','onboarding','profile']
const tabs=[{name:'home',label:'Trang chủ',icon:'wap-home-o'},{name:'employees',label:'Nhân viên',icon:'friends-o'},{name:'onboarding',label:'Tiếp nhận',icon:'passed'},{name:'profile',label:'Tôi',icon:'user-o'}]
const title=computed(()=>({home:'Nhân sự Lotus',employees:'Hồ sơ nhân viên',onboarding:'Tiếp nhận',profile:'Tài khoản',employee:'Hồ sơ nhân viên',candidates:'Tuyển dụng',candidate:'Hồ sơ ứng viên'})[screen.value]||'Nhân sự Lotus')
const rootTab=computed(()=>roots.includes(screen.value)?screen.value:screen.value==='candidate'?'home':'employees')
const manager=computed(()=>!!session.value?.is_hr_manager)
const missing=computed(()=>people.value.filter(p=>p.lotus_onboarding_state!=='Ready'))
const fold=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').toLowerCase()
const filtered=computed(()=>{
 const pool=screen.value==='onboarding'?missing.value:people.value
 return pool.filter(p=>fold([p.name,p.employee_name,p.designation,p.department,p.lotus_farm].join(' ')).includes(fold(search.value)))
})
const shortlist=computed(()=>candidates.value.filter(p=>fold([p.applicant_name,p.phone,p.designation].join(' ')).includes(fold(search.value))))
const genOptions=computed(()=>(catalog.value.genders||[]).map(g=>({value:g.name,label:({Male:'Nam',Female:'Nữ',Other:'Khác'})[g.name]||g.name})))
const farms=computed(()=>(catalog.value.farms||[]).map(p=>({value:p.name,label:p.farm_name||p.name})))
const departments=computed(()=>(catalog.value.departments||[]).map(p=>({value:p.name,label:p.department_name||p.name})))
const titles=computed(()=>(catalog.value.designations||[]).map(p=>({value:p.name,label:p.designation_name||p.name})))
const teams=computed(()=>(catalog.value.teams||[]).filter(p=>p.farm===employee.lotus_farm&&p.lotus_team_type!=='Contractor').map(p=>({value:p.name,label:p.team_name||p.name})))
const choices=values=>(values||[]).map(x=>({value:x.name||x,label:x.name||x}))
const contractTypeNames={Apprentice:'Học việc',Intern:'Thực tập',Piecework:'Khoán theo sản phẩm',Commission:'Theo hoa hồng',Contract:'Hợp đồng',Probation:'Thử việc','Part-time':'Bán thời gian','Full-time':'Toàn thời gian'}
const contractTypes=computed(()=>(catalog.value.employment_types||[]).map(t=>({value:t.name,label:contractTypeNames[t.name]||t.name})))
const categories=[{value:'Permanent',label:'Dài hạn'},{value:'Fixed-term',label:'Hợp đồng xác định hạn'},{value:'Seasonal',label:'Thời vụ'},{value:'Probation',label:'Thử việc'}]
const payments=[{value:'Monthly',label:'Lương tháng'},{value:'Daywork',label:'Công nhật'},{value:'Piecework',label:'Khoán sản lượng'},{value:'Mixed',label:'Hỗn hợp'}]
const candidateStatuses={New:'Mới',Screening:'Sàng lọc',Interview:'Phỏng vấn',Offered:'Đã mời nhận việc',Hold:'Tạm giữ',Rejected:'Không đạt',Hired:'Đã tiếp nhận'}
function msg(e){return String(e?.message||'Không thể kết nối Lotus.')}
function nav(dest){if(saving.value||screen.value===dest)return;scanOpen.value=false;screen.value=dest;search.value='';error.value='';notice.value='';window.scrollTo({top:0,behavior:'instant'})}
function back(){nav(selectedEmployee.value?'employees':'home')}
function blankEmployee(){
 selectedEmployee.value=null;hireFrom.value=null
 Object.keys(employee).forEach(k=>delete employee[k])
 Object.assign(employee,{employee_name:'',gender:'',date_of_birth:'',date_of_joining:session.value?.today||'',designation:'',department:'',
 employment_type:'',grade:'',lotus_worker_category:'Seasonal',lotus_payment_basis:'Daywork',lotus_farm:'',lotus_work_team:'',
 cell_number:'',personal_email:'',cccd:'',current_address:'',permanent_address:'',lotus_id_issue_on:'',lotus_id_issue_at:'',
 lotus_emergency_name:'',lotus_emergency_phone:'',lotus_social_insurance_no:'',health_insurance_no:'',lotus_tax_code:'',contract_end_date:''})
 nav('employee')
}
async function openEmployee(row){
 if(!manager.value)return
 busy.value=true;error.value=''
 try{
  const value=await api('employee_detail',{company:company.value,employee:row.name})
  Object.keys(employee).forEach(k=>delete employee[k])
  Object.assign(employee,value,{cccd:''});selectedEmployee.value=row.name;hireFrom.value=null
  nav('employee')
 }catch(e){error.value=msg(e)}finally{busy.value=false}
}
function updateFarm(value){employee.lotus_farm=value;employee.lotus_work_team=''}
async function useQr(info){
 if(saving.value||!manager.value)return
 const hasDiff=['employee_name','gender','date_of_birth','current_address','lotus_id_issue_on'].some(k=>employee[k]&&String(employee[k]).trim()!==String(info[k]||'').trim())
 if(hireFrom.value && employee.employee_name.trim()!==info.employee_name){error.value='Tên trên CCCD khác tên ứng viên. Kiểm tra hồ sơ ứng viên trước.';return}
 if(hasDiff&&!await askConfirm('Dữ liệu QR khác một số mục đang điền. Thay bằng thông tin trên CCCD?'))return
 saving.value=true;error.value=''
 try{
  const found=await api('check_cccd',{company:company.value,cccd:info.cccd,employee:selectedEmployee.value},true)
  if(found.duplicate){error.value='Số CCCD đã có trong hồ sơ khác, không thể nhập trùng.';return}
  Object.assign(employee,info)
  scanOpen.value=false
  notice.value='Đã điền thông tin từ mã QR. Kiểm tra lại trước khi lưu.'
 }catch(e){error.value=msg(e)}finally{saving.value=false}
}
async function reload(){
 if(!company.value)return
 busy.value=true;error.value=''
 try{
  const [list,cat]=await Promise.all([api('overview',{company:company.value}),api('catalogue',{company:company.value})])
  people.value=list.employees||[];candidates.value=list.candidates||[];catalog.value=cat
 }catch(e){error.value=msg(e)}finally{busy.value=false}
}
async function init(){
 busy.value=true
 try{
  session.value=await api('bootstrap')
  setCSRF(session.value.csrf_token)
  company.value=session.value.companies?.[0]?.name||''
  if(!company.value)throw Error('Tài khoản chưa được cấp công ty quản lý.')
  await reload()
 }catch(e){error.value=msg(e)}finally{busy.value=false}
}
async function saveEmployee(){
 if(!manager.value||saving.value)return
 saving.value=true;error.value='';notice.value=''
 try{
  const values={...employee}
  const result=hireFrom.value?await api('hire_candidate',{company:company.value,candidate:hireFrom.value.name,modified:hireFrom.value.modified,values},true):
    await api('save_employee',{company:company.value,employee:selectedEmployee.value,modified:employee.modified,values},true)
  await reload();saving.value=false;nav('employees')
  notice.value='Đã lưu hồ sơ '+result.name+'. Nếu là nhân viên mới, cần duyệt tiếp nhận riêng.'
 }catch(e){error.value=msg(e)}finally{saving.value=false}
}
async function approve(){
 if(!selectedEmployee.value||!manager.value||saving.value)return
 if(!await askConfirm('Đã kiểm tra giấy tờ gốc và các điều kiện tiếp nhận?'))return
 saving.value=true;error.value=''
 try{
  await api('set_onboarding_ready',{company:company.value,employee:selectedEmployee.value,modified:employee.modified},true)
  await reload();saving.value=false;nav('onboarding')
  notice.value='Đã duyệt tiếp nhận nhân viên.'
 }catch(e){error.value=msg(e)}finally{saving.value=false}
}
function blankCandidate(){
 selectedCandidate.value=null;Object.keys(candidate).forEach(k=>delete candidate[k])
 Object.assign(candidate,{applicant_name:'',phone:'',email:'',designation:'',farm:'',job_opening:'',applied_on:session.value?.today||'',
 source:'Trực tiếp',status:'New',notes:'',interview_on:''})
 nav('candidate')
}
async function openCandidate(row){
 busy.value=true;error.value=''
 try{
  const data=await api('candidate_detail',{company:company.value,candidate:row.name})
  Object.keys(candidate).forEach(k=>delete candidate[k]);Object.assign(candidate,data)
  selectedCandidate.value=row.name;nav('candidate')
 }catch(e){error.value=msg(e)}finally{busy.value=false}
}
async function saveCandidate(){
 saving.value=true;error.value='';notice.value=''
 try{
  const result=await api('save_candidate',{company:company.value,name:selectedCandidate.value,modified:candidate.modified,values:{...candidate}},true)
  await reload();saving.value=false;nav('candidates');notice.value='Đã lưu ứng viên '+result.name
 }catch(e){error.value=msg(e)}finally{saving.value=false}
}
function hireCandidate(){
 if(!manager.value||candidate.status!=='Offered'||candidate.employee)return
 blankEmployee()
 hireFrom.value={name:selectedCandidate.value,modified:candidate.modified}
 employee.employee_name=candidate.applicant_name
 employee.cell_number=candidate.phone
 employee.designation=candidate.designation
 employee.lotus_farm=candidate.farm||''
}
function openSetup(){window.dispatchEvent(new Event('lotus:open-setup'))}
async function logout(){
 if(saving.value||!await askConfirm('Đăng xuất khỏi Nhân sự Lotus?'))return
 saving.value=true;error.value=''
 try{await logoutPwa('hr',{csrf:session.value?.csrf_token||'',home:'/hr-mobile'})}
 catch(e){error.value='Không đăng xuất được: '+msg(e)}
 finally{saving.value=false}
}
onMounted(()=>{void init()})
</script>

<template>
 <LotusMobileShell app="hr" :refresh="reload" :refreshable="roots.includes(screen)" :tabs="tabs" :title="title" :active-tab="rootTab"
  :back="!roots.includes(screen)" :keyboard-open="keyboard" :disabled="saving"
  @navigate="nav" @back="back">
  <main class="hr-mobile-main">
   <LotusMobileFeedback v-if="error" kind="error">{{error}}</LotusMobileFeedback>
   <LotusMobileFeedback v-if="notice" kind="success">{{notice}}</LotusMobileFeedback>
   <LotusMobileFeedback v-if="busy" kind="loading">Đang tải dữ liệu…</LotusMobileFeedback>
   <template v-if="screen==='home'">
    <div class="hr-mobile-stats">
     <button type="button" @click="nav('employees')"><strong>{{people.length}}</strong><span>Nhân viên</span></button>
     <button type="button" @click="nav('onboarding')"><strong>{{missing.length}}</strong><span>Chờ tiếp nhận</span></button>
     <button type="button" @click="nav('candidates')"><strong>{{candidates.length}}</strong><span>Ứng viên</span></button>
    </div>
    <div v-if="manager" class="hr-mobile-actions">
     <LotusMobileButton variant="primary" block icon="scan" @click="blankEmployee();scanOpen=true">Quét CCCD thêm nhân viên</LotusMobileButton>
     <LotusMobileButton plain block icon="plus" @click="blankEmployee">Nhập hồ sơ nhân viên</LotusMobileButton>
     <LotusMobileButton plain block icon="friends-o" @click="blankCandidate">Thêm ứng viên</LotusMobileButton>
    </div>
    <section class="hr-mobile-card">
     <h2>Nhân sự cần xử lý</h2>
     <p v-if="!missing.length" class="mobile-empty">Không có nhân viên chờ tiếp nhận.</p>
     <button v-for="person in missing.slice(0,8)" :key="person.name" type="button" class="hr-mobile-row" @click="openEmployee(person)">
      <span><strong>{{person.employee_name}}</strong><small>{{person.designation||'Chưa có chức danh'}} · {{person.lotus_farm||'Chưa chọn vườn'}}</small></span><Icon name="arrow"/>
     </button>
    </section>
   </template>
   <template v-else-if="screen==='employees'||screen==='onboarding'">
    <div class="hr-mobile-top">
     <LotusMobileInput v-model="search" label="Tìm nhân viên" placeholder="Họ tên, mã, chức danh…"/>
     <LotusMobileButton v-if="manager&&screen==='employees'" variant="primary" block icon="plus" @click="blankEmployee">Thêm nhân viên</LotusMobileButton>
    </div>
    <section class="hr-mobile-card">
     <p v-if="!filtered.length" class="mobile-empty">Chưa có nhân viên phù hợp.</p>
     <button v-for="person in filtered" :key="person.name" type="button" class="hr-mobile-row" :disabled="!manager" @click="openEmployee(person)">
      <span><strong>{{person.employee_name}}</strong><small>{{person.name}} · {{person.designation||'Chưa có chức danh'}}</small>
       <small>{{person.lotus_farm||'Chưa chọn vườn'}} · {{person.lotus_onboarding_state==='Ready'?'Đã tiếp nhận':'Chờ tiếp nhận'}}</small></span>
      <Icon v-if="manager" name="arrow"/>
     </button>
    </section>
   </template>
   <template v-else-if="screen==='employee'">
    <div class="hr-mobile-title">
     <h2>{{selectedEmployee?'Sửa nhân viên':'Tạo hồ sơ nhân viên'}}</h2>
     <LotusMobileButton plain size="small" @click="nav('employees')">Đóng</LotusMobileButton>
    </div>
    <section class="hr-mobile-card">
     <LotusMobileButton variant="primary" block icon="scan" :disabled="saving" @click="scanOpen=true">Quét mã QR căn cước</LotusMobileButton>
     <p class="hr-mobile-caption">Dữ liệu QR chỉ điền vào form. Kiểm tra thẻ gốc trước khi duyệt.</p>
     <p v-if="employee.cccd_recorded" class="hr-mobile-caption">Đã có CCCD kết thúc bằng {{employee.lotus_cccd_last4}}.</p>
    </section>
    <form class="hr-mobile-form" @submit.prevent="saveEmployee">
     <section class="hr-mobile-card">
      <h2>Thông tin cá nhân</h2>
      <LotusMobileInput v-model="employee.employee_name" label="Họ và tên" required :disabled="!!hireFrom" maxlength="140"/>
      <LotusMobileSelect v-model="employee.gender" label="Giới tính" :options="genOptions" placeholder="Chọn giới tính" required/>
      <LotusMobileInput v-model="employee.date_of_birth" type="date" label="Ngày sinh" :max="session?.today" required/>
      <LotusMobileInput v-model="employee.cccd" label="Số CCCD" inputmode="numeric" maxlength="12" placeholder="12 chữ số" hint="Bỏ trống nếu đã lưu CCCD trước đó."/>
      <LotusMobileInput v-model="employee.lotus_id_issue_on" type="date" label="Ngày cấp CCCD"/>
      <LotusMobileInput v-model="employee.lotus_id_issue_at" label="Nơi cấp CCCD"/>
      <LotusMobileInput v-model="employee.current_address" type="textarea" label="Nơi cư trú"/>
      <LotusMobileInput v-model="employee.permanent_address" type="textarea" label="Địa chỉ thường trú"/>
      <LotusMobileInput v-model="employee.cell_number" label="Số điện thoại" type="tel" required/>
      <LotusMobileInput v-model="employee.personal_email" label="Email cá nhân" type="email"/>
     </section>
     <section class="hr-mobile-card">
      <h2>Thông tin công việc</h2>
      <LotusMobileInput v-model="employee.date_of_joining" label="Ngày vào làm" type="date" required/>
      <LotusMobileSelect v-model="employee.designation" label="Chức danh" :options="titles" placeholder="Chọn chức danh" :disabled="!!hireFrom" required/>
      <LotusMobileSelect :model-value="employee.lotus_farm" @update:model-value="updateFarm" label="Vườn" :options="[{value:'',label:'Chưa phân công'},...farms]" :disabled="!!hireFrom"/>
      <LotusMobileSelect v-model="employee.department" label="Phòng ban" :options="[{value:'',label:'Chưa chọn'},...departments]"/>
      <LotusMobileSelect v-model="employee.lotus_work_team" label="Tổ/đội" :options="[{value:'',label:'Chưa phân tổ'},...teams]"/>
      <LotusMobileSelect v-model="employee.lotus_worker_category" label="Loại lao động" :options="categories" required/>
      <LotusMobileSelect v-model="employee.lotus_payment_basis" label="Cơ chế công/lương" :options="payments" required/>
      <LotusMobileSelect v-model="employee.employment_type" label="Hình thức làm việc / hợp đồng" :options="[{value:'',label:'Chưa chọn'},...contractTypes]"/>
      <LotusMobileInput v-model="employee.contract_end_date" type="date" label="Ngày hết hạn hợp đồng"/>
     </section>
     <section class="hr-mobile-card">
      <h2>Thông tin bổ sung</h2>
      <LotusMobileInput v-model="employee.lotus_emergency_name" label="Người liên hệ khẩn cấp"/>
      <LotusMobileInput v-model="employee.lotus_emergency_phone" label="SĐT khẩn cấp" type="tel"/>
      <LotusMobileInput v-model="employee.lotus_social_insurance_no" label="Số BHXH"/>
      <LotusMobileInput v-model="employee.health_insurance_no" label="Số BHYT"/>
      <LotusMobileInput v-model="employee.lotus_tax_code" label="Mã số thuế cá nhân"/>
     </section>
     <section v-if="selectedEmployee" class="hr-mobile-card">
      <strong>Tiếp nhận: {{employee.lotus_onboarding_state==='Ready'?'Đã duyệt':'Chờ duyệt'}}</strong>
      <p v-if="employee.onboarding_gaps?.length">Thiếu: {{employee.onboarding_gaps.join(', ')}}</p>
      <LotusMobileButton v-if="employee.lotus_onboarding_state!=='Ready'&&!employee.onboarding_gaps?.length" block type="button" :disabled="saving" @click="approve">Duyệt tiếp nhận</LotusMobileButton>
     </section>
     <LotusMobileButton variant="primary" block type="submit" :loading="saving" :disabled="!manager||saving">Lưu hồ sơ</LotusMobileButton>
    </form>
   </template>
   <template v-else-if="screen==='candidates'">
    <LotusMobileInput v-model="search" label="Tìm ứng viên" placeholder="Họ tên hoặc SĐT"/>
    <LotusMobileButton v-if="manager" variant="primary" block icon="plus" @click="blankCandidate">Thêm ứng viên</LotusMobileButton>
    <section class="hr-mobile-card">
     <p v-if="!shortlist.length" class="mobile-empty">Không có ứng viên.</p>
     <button v-for="item in shortlist" :key="item.name" type="button" class="hr-mobile-row" @click="openCandidate(item)">
      <span><strong>{{item.applicant_name}}</strong><small>{{item.phone}} · {{item.designation}}</small><small>{{candidateStatuses[item.status]||item.status}}</small></span>
      <Icon name="arrow"/>
     </button>
    </section>
   </template>
   <template v-else-if="screen==='candidate'">
    <form class="hr-mobile-form" @submit.prevent="saveCandidate">
     <section class="hr-mobile-card">
      <h2>Thông tin ứng viên</h2>
      <LotusMobileInput v-model="candidate.applicant_name" label="Họ tên" required/>
      <LotusMobileInput v-model="candidate.phone" label="Số điện thoại" type="tel" required/>
      <LotusMobileInput v-model="candidate.email" label="Email" type="email"/>
      <LotusMobileSelect v-model="candidate.designation" label="Chức danh ứng tuyển" :options="titles" :disabled="candidate.status==='Hired'" required/>
      <LotusMobileSelect v-model="candidate.farm" label="Vườn dự kiến" :options="[{value:'',label:'Chưa chọn'},...farms]"/>
      <LotusMobileInput v-model="candidate.applied_on" label="Ngày đăng ký" type="date" required/>
      <LotusMobileSelect v-model="candidate.source" label="Nguồn" :options="['Trực tiếp','Zalo','Facebook','Giới thiệu','Khác'].map(x=>({value:x,label:x}))"/>
      <LotusMobileSelect v-model="candidate.status" label="Trạng thái" :disabled="!selectedCandidate||candidate.status==='Hired'"
       :options="[{value:'New',label:'Mới'},{value:'Screening',label:'Sàng lọc'},{value:'Interview',label:'Phỏng vấn'},{value:'Offered',label:'Đã mời nhận việc'},{value:'Hold',label:'Tạm giữ'},{value:'Rejected',label:'Không đạt'}]"/>
      <LotusMobileInput v-model="candidate.notes" label="Ghi chú" type="textarea"/>
     </section>
     <LotusMobileButton variant="primary" block type="submit" :loading="saving" :disabled="saving||candidate.status==='Hired'">Lưu ứng viên</LotusMobileButton>
     <LotusMobileButton v-if="manager&&selectedCandidate&&candidate.status==='Offered'&&!candidate.employee" block plain type="button" @click="hireCandidate">Tiếp nhận làm nhân viên</LotusMobileButton>
     <LotusMobileButton block plain type="button" @click="nav('candidates')">Đóng</LotusMobileButton>
    </form>
   </template>
   <template v-else-if="screen==='profile'">
    <section class="hr-mobile-card">
     <h2>Tài khoản</h2><p>{{session?.user||'Chưa đăng nhập'}}</p>
     <p>Quyền: {{manager?'Quản lý nhân sự':'Nhân viên nhân sự (chỉ xem hồ sơ)'}}</p>
     <LotusMobileSelect v-if="session?.companies?.length>1" v-model="company" label="Công ty"
      :options="session.companies.map(c=>({value:c.name,label:c.name}))" @update:model-value="reload"/>
     <LotusMobileButton block plain icon="replay" @click="reload">Tải lại</LotusMobileButton>
     <LotusMobileButton block plain icon="apps-o" @click="openSetup">Cài đặt / hướng dẫn ban đầu</LotusMobileButton>
     <p class="hr-mobile-caption">Để cài PWA, mở bằng Chrome hoặc Safari thay vì trình duyệt bên trong ChatGPT/Zalo.</p>
     <a href="/lotus/nhan-su">Mở Nhân sự trên máy tính</a>
     <LotusMobileButton block plain type="button" @click="logout">Đăng xuất</LotusMobileButton>
    </section>
    <section class="hr-mobile-card"><h2>Nghiệp vụ nâng cao</h2>
     <p>Nhập Excel, thiết lập máy chấm công và cấu hình lương tiếp tục quản lý trên bản máy tính.</p>
    </section>
   </template>
  </main>
  <CccdQrScanner v-if="scanOpen" @close="scanOpen=false" @confirmed="useQr"/>
  <LotusMobileDialog ref="confirmDialog" class="mobile-leave-dialog" @cancel.prevent="finishConfirm(false)">
   <div class="mobile-leave-content"><h2>Xác nhận</h2><p>{{confirmMessage}}</p><div><LotusMobileButton type="button" autofocus @click="finishConfirm(false)">Hủy</LotusMobileButton><LotusMobileButton type="button" variant="primary" @click="finishConfirm(true)">Đồng ý</LotusMobileButton></div></div>
  </LotusMobileDialog>
 </LotusMobileShell>
</template>
