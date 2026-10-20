<script setup>
import {computed,onMounted,reactive,ref,watch} from 'vue'
import {call} from '../api'
import {stateLabel} from '../labels'
import {Button as UiButton} from './ui/button'
import {Input as UiInput} from './ui/input'
import UiSelect from './ui/select/Select.vue'
import {DatePicker} from './ui/date-picker'
import '../hr-operations.css'
import WorkspaceModal from './WorkspaceModal.vue'
import WorkspaceConfirm from './WorkspaceConfirm.vue'
import {useWorkspaceConfirm} from '../use-workspace-confirm'

const {open:confirmOpen,title:confirmTitle,message:confirmMessage,alertOnly:confirmAlert,ask:askConfirm,finish:finishConfirm}=useWorkspaceConfirm()
// view: render one area as its own page tab (organization | import | devices = machines + punches); empty keeps the inner tabs.
const props=defineProps({company:{type:String,default:''},manager:Boolean,view:{type:String,default:''}})
const tabs=[{id:'organization',label:'Sơ đồ tổ chức'},{id:'import',label:'Nhập Excel'},{id:'devices',label:'Máy chấm công'},{id:'logs',label:'Lượt chấm công'}]
const kinds=['Department','Designation','Work Team','Employee','Staff Assignment','Shift Type','Shift Assignment','Device Mapping','Checkin CSV']
const kindLabels={'Department':'Bộ phận','Designation':'Chức danh','Work Team':'Đội/tổ','Employee':'Nhân viên','Staff Assignment':'Chức vụ / phân công','Shift Type':'Loại ca','Shift Assignment':'Xếp ca nhân viên','Device Mapping':'Mã máy ↔ nhân viên','Checkin CSV':'Dữ liệu quẹt máy'}
const columns={
 Department:['department_name','parent_department'],Designation:['designation_name'],
 'Work Team':['farm','team_code','team_name'],
 'Staff Assignment':['employee','farm','department','designation','work_team','role_title','valid_from','valid_to','approver'],
 'Shift Type':['shift_name','start_time','end_time'],
 'Shift Assignment':['employee','shift_type','start_date','end_date'],
 Employee:['employee_name','gender','date_of_birth','date_of_joining','designation','department','lotus_farm','lotus_work_team','attendance_device_id'],
 'Device Mapping':['device','device_user_id','employee','valid_from','valid_to'],
 'Checkin CSV':['device','device_user_id','punched_at','log_type','source_event_id']
}
const api=(method,args={},post=false)=>call('lotus_farm.hr_operations.'+method,args,post)
const editAssignment=ref(false),editDevice=ref(false)
const active=ref(props.view||'organization'),farm=ref(''),busy=ref(false),error=ref(''),notice=ref('')
const org=ref(null),hardware=ref(null),kind=ref('Designation'),uploadName=ref('')
const uploadData=ref([]),preview=ref(null),selected=ref([])
const machine=reactive({device_code:'',device_name:'',model:'',serial_number:'',connection_mode:'File CSV',timezone:'Asia/Ho_Chi_Minh',active:1,farm:'',notes:''})
const assignment=reactive({employee:'',farm:'',department:'',designation:'',work_team:'',role_title:'',valid_from:'',valid_to:'',approver:'',notes:''})
const farmChoices=computed(()=>org.value?.farms||[])
const visibleTeams=computed(()=>(org.value?.teams||[]).filter(t=>!assignment.farm||t.farm===assignment.farm))
const readOnly=computed(()=>!props.manager)
const selectedPunches=computed(()=>selected.value.filter(id=>hardware.value?.punches?.some(p=>p.name===id)))
const fmt=n=>Number(n||0).toLocaleString('vi-VN')
async function refresh(){
 if(!props.company)return
 busy.value=true;error.value=''
 try{
  const [o,d]=await Promise.all([api('organization',{company:props.company}),api('devices',{company:props.company})])
  org.value=o;hardware.value=d
  const options=o.farms||[]
  if(!options.some(f=>f.name===farm.value))farm.value=options[0]?.name||''
  if(!machine.farm)machine.farm=farm.value
  if(!assignment.farm)assignment.farm=farm.value
 }catch(e){error.value=e.message}finally{busy.value=false}
}
onMounted(refresh)
defineExpose({refresh})
watch(()=>props.company,()=>{org.value=null;hardware.value=null;preview.value=null;uploadData.value=[];farm.value='';refresh()})
function choose(id){active.value=id;notice.value='';error.value=''}
function template(){
 const header=columns[kind.value]||[]
 const csv='\ufeff'+header.join(',')+'\r\n'
 const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}))
 const a=document.createElement('a');a.href=url;a.download='lotus-'+kind.value.toLowerCase().replace(/\s+/g,'-')+'-mau.csv';a.click()
 setTimeout(()=>URL.revokeObjectURL(url),1000)
}
async function fileChanged(event){
 error.value='';notice.value='';preview.value=null;uploadData.value=[]
 const file=event.target.files?.[0]
 if(!file)return
 if(file.size>2500000){error.value='Tệp tối đa 2,5 MB';return}
 uploadName.value=file.name
 busy.value=true
 try{
  const contents=await new Promise((resolve,reject)=>{
   const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file)
  })
  const result=await call('lotus_farm.hr_import_file.parse_upload',
   {company:props.company,kind:kind.value,filename:file.name,content_b64:contents},true)
  uploadData.value=result.rows;preview.value=result.preview;notice.value=result.warning
 }catch(e){error.value=e.message}finally{busy.value=false}
}
async function confirmImport(){
 if(!preview.value||preview.value.errors?.length||!preview.value.ready||!props.manager)return
 if(!await askConfirm('Xác nhận ghi '+preview.value.ready+' dòng '+kindLabels[kind.value]+' vào Lotus? Hệ thống không tự duyệt công hoặc trả lương.'))return
 busy.value=true;error.value=''
 try{
  const result=await api('commit_import',{company:props.company,kind:kind.value,rows:uploadData.value,review_hash:preview.value.review_hash},true)
  notice.value='Đã tạo '+result.created+' dòng; bỏ qua '+result.skipped+' dòng đã có; chưa ghép nhân viên: '+result.unmapped
  preview.value=null;uploadData.value=[];await refresh()
 }catch(e){error.value=e.message}finally{busy.value=false}
}
async function seed(){
 if(!props.manager||!farm.value)return
 if(!await askConfirm('Tạo bộ phận + đội/tổ mẫu khu A–D cho vườn đã chọn? Không tạo nhân viên và không có lương.'))return
 busy.value=true;error.value=''
 try{
  const r=await call('lotus_farm.hr_setup.seed_organization',{company:props.company,farm:farm.value},true)
  notice.value='Đã tạo '+r.departments+' bộ phận, '+r.teams+' đội/tổ; bỏ qua '+r.skipped+' dòng đã tồn tại. '+r.warning
  await refresh()
 }catch(e){error.value=e.message}finally{busy.value=false}
}
async function saveDevice(){
 if(!props.manager)return
 busy.value=true;error.value=''
 try{
  const r=await api('save_device',{company:props.company,values:{...machine}},true)
  editDevice.value=false;notice.value='Đã lưu máy '+r.name+' (chưa bật kết nối thiết bị nếu chưa cấu hình giao thức).'
  Object.assign(machine,{device_code:'',device_name:'',model:'',serial_number:'',connection_mode:'File CSV',timezone:'Asia/Ho_Chi_Minh',active:1,farm:farm.value,notes:''})
  await refresh()
 }catch(e){error.value=e.message}finally{busy.value=false}
}
async function saveAssignment(){
 if(!props.manager)return
 busy.value=true;error.value=''
 try{
  await call('lotus_farm.hr_setup.save_assignment',{company:props.company,values:{...assignment}},true)
  editAssignment.value=false;notice.value='Đã ghi lịch sử phân công. Nếu đổi vườn chính thức, phải làm điều chuyển trong HRMS.'
  Object.assign(assignment,{employee:'',farm:farm.value,department:'',designation:'',work_team:'',role_title:'',valid_from:'',valid_to:'',approver:'',notes:''})
  await refresh()
 }catch(e){error.value=e.message}finally{busy.value=false}
}
async function sync(){
 if(!props.manager||!selectedPunches.value.length)return
 if(!await askConfirm('Chuyển '+selectedPunches.value.length+' log đã chọn vào Employee Checkin của HRMS? Đây KHÔNG phải bảng công đã duyệt.'))return
 busy.value=true;error.value=''
 try{
  const r=await api('sync_checkins',{company:props.company,names:selectedPunches.value},true)
  notice.value='Đã chuyển '+r.synced+', đã có '+r.skipped+', cần kiểm tra '+r.needs_review+' log.'
  selected.value=[];await refresh()
 }catch(e){error.value=e.message}finally{busy.value=false}
}
// Punches that will never be attendance (unknown ID, test swipe) are set aside so the month can close.
const ignoreOpen=ref(false),ignoreReason=ref('')
const openPunches=computed(()=>(hardware.value?.punches||[]).filter(p=>!['Synced','Ignored'].includes(p.state)))
const allOpen=computed(()=>openPunches.value.length>0&&openPunches.value.every(p=>selected.value.includes(p.name)))
function toggleOpen(){selected.value=allOpen.value?[]:openPunches.value.map(p=>p.name)}
async function ignore(){
 busy.value=true;error.value=''
 try{const r=await call('lotus_farm.attendance_day.ignore_punches',{company:props.company,names:selectedPunches.value,reason:ignoreReason.value},true)
  notice.value='Đã bỏ qua '+r.ignored+' log. Các log này không tính công và không chặn khóa kỳ.';ignoreOpen.value=false;ignoreReason.value='';selected.value=[];await refresh()}
 catch(e){error.value=e.message}finally{busy.value=false}
}
const syncFrom=ref(''),syncTo=ref('')
async function syncRange(){
 if(!props.manager||!syncFrom.value||!syncTo.value)return
 if(!await askConfirm('Chuyển mọi log chưa chuyển từ '+syncFrom.value+' đến '+syncTo.value+' vào Employee Checkin? Log chưa ghép mã sẽ giữ lại để kiểm tra.'))return
 busy.value=true;error.value=''
 try{
  const r=await api('sync_ready_checkins',{company:props.company,from_date:syncFrom.value,to_date:syncTo.value},true)
  notice.value='Đã chuyển '+r.synced+', đã có '+r.skipped+', cần kiểm tra '+r.needs_review+' log.'+(r.more?' Còn log trong khoảng này, bấm chuyển tiếp.':'')
  selected.value=[];await refresh()
 }catch(e){error.value=e.message}finally{busy.value=false}
}
</script>
<template>
<div class="hr-ops">
 <nav v-if="!view" class="hr-ops-tabs" aria-label="Quản trị nhân sự bổ sung">
  <button type="button" v-for="t in tabs" :key="t.id" :class="{active:active===t.id}" @click="choose(t.id)">{{t.label}}</button>
 </nav>
 <p v-if="error" class="hr-ops-error" role="alert">{{error}}</p>
 <p v-if="notice" class="hr-ops-notice" role="status">{{notice}}</p>
 <div v-if="!manager||!view" class="hr-ops-actions"><span v-if="!manager">Tài khoản chỉ có quyền xem. Liên hệ HR Manager để thay đổi.</span>
  <UiButton v-if="!view" type="button" variant="outline" :disabled="busy||!company" @click="refresh">{{busy?'Đang tải…':'Làm mới'}}</UiButton>
 </div>
 <template v-if="active==='organization'">
  <div class="hr-ops-head"><h3>Cơ cấu vườn</h3>
   <label>Vườn<UiSelect v-model="farm"><option v-for="f in farmChoices" :key="f.name" :value="f.name">{{f.farm_name}}</option></UiSelect></label></div>
  <section class="hr-ops-panel">
   <div class="hr-ops-tree">
    <div class="hr-ops-tree-root"><strong>Giám đốc / Ban quản lý</strong><small>Điều hành chung và phân công</small></div>
    <div class="hr-ops-departments"><div v-for="item in (org?.template_departments||[]).filter(x=>!x.code.startsWith('TEAM_')&&x.code!=='BOARD')" :key="item.code">
      <strong>{{item.name}}</strong><small>{{(org?.departments||[]).some(d=>d.department_name===item.name)?'Đã cấu hình':'Mẫu đề xuất'}}</small>
     </div></div>
    <div class="hr-ops-teams"><div v-for="zone in ['A','B','C','D']" :key="zone">
     <strong>Đội khu {{zone}} · 55 ha</strong><small>Đội trưởng 1 người</small>
     <div class="hr-ops-subteam"><span>Tổ {{zone}}1 · 25 ha</span><span>Tổ {{zone}}2 · 25 ha</span></div>
     </div></div>
   </div>
   <p class="hr-ops-tip">Một đội 55 ha nhưng 2 tổ × 25 ha chỉ bằng 50 ha. Phần 5 ha mỗi đội cần xác nhận, không tự phân bổ.</p>
   <UiButton v-if="manager" type="button" :disabled="busy||!farm" @click="seed">Tạo bộ phận và 12 đội/tổ mẫu</UiButton>
  </section>
  <section class="hr-ops-panel">
   <h3>Lịch sử phân công nhân viên</h3>
   <UiButton v-if="manager" type="button" variant="outline" @click="editAssignment=true">＋ Thêm phân công</UiButton><WorkspaceModal v-if="manager" v-model="editAssignment" title="Phân công nhân viên" :busy="busy"><p v-if="error" class="hr-ops-error" role="alert">{{error}}</p><form class="hr-ops-form" @submit.prevent="saveAssignment">
    <label>Nhân viên<UiSelect v-model="assignment.employee" required><option value="">Chọn nhân viên</option><option v-for="e in org?.employees||[]" :key="e.name" :value="e.name">{{e.employee_name}} · {{e.name}}</option></UiSelect></label>
    <label>Vườn<UiSelect v-model="assignment.farm" required><option value="">Chọn vườn</option><option v-for="f in farmChoices" :key="f.name" :value="f.name">{{f.farm_name}}</option></UiSelect></label>
    <label>Bộ phận<UiSelect v-model="assignment.department"><option value="">Chọn</option><option v-for="d in org?.departments||[]" :key="d.name" :value="d.name">{{d.department_name}}</option></UiSelect></label>
    <label>Chức danh<UiSelect v-model="assignment.designation"><option value="">Chọn</option><option v-for="d in org?.designations||[]" :key="d.name" :value="d.name">{{d.designation_name}}</option></UiSelect></label>
    <label>Tổ/đội<UiSelect v-model="assignment.work_team"><option value="">Chọn</option><option v-for="t in visibleTeams" :key="t.name" :value="t.name">{{t.team_name}}</option></UiSelect></label>
    <label>Chức vụ thực tế<UiInput v-model="assignment.role_title" placeholder="VD: Đội trưởng, tổ trưởng"/></label>
    <label>Ngày bắt đầu<DatePicker v-model="assignment.valid_from" required aria-label="Ngày bắt đầu"/></label>
    <label>Ngày kết thúc (nếu có)<DatePicker v-model="assignment.valid_to" :min="assignment.valid_from" aria-label="Ngày kết thúc"/></label>
    <label>Cấp trên<UiSelect v-model="assignment.approver"><option value="">Chưa chọn</option><option v-for="e in org?.employees||[]" :key="e.name" :value="e.name">{{e.employee_name}}</option></UiSelect></label>
    <UiButton type="submit" :disabled="busy">Lưu phân công</UiButton>
   </form></WorkspaceModal>
   <div class="hr-ops-scroll"><table><thead><tr><th>Nhân viên</th><th>Vườn</th><th>Tổ/đội</th><th>Chức vụ</th><th>Từ ngày</th><th>Đến ngày</th></tr></thead>
    <tbody><tr v-for="a in org?.assignments||[]" :key="a.name"><td>{{org.employees.find(e=>e.name===a.employee)?.employee_name||a.employee}}</td><td>{{a.farm}}</td><td>{{org.teams.find(t=>t.name===a.work_team)?.team_name||'—'}}</td><td>{{a.role_title||'—'}}</td><td>{{a.valid_from}}</td><td>{{a.valid_to||'Hiện tại'}}</td></tr></tbody></table></div>
  </section>
 </template>
 <template v-else-if="active==='import'">
  <section class="hr-ops-panel">
   <h3>Nhập nhân sự và danh mục từ Excel/CSV</h3>
   <p>Thứ tự: Bộ phận → Chức danh → Đội/tổ → Nhân viên → Chức vụ/phân công → Loại ca → Xếp ca → Mã máy. Log nhập cuối cùng.</p>
   <div class="hr-ops-actions"><a href="/app/shift-type">Quản lý loại ca HRMS ↗</a><a href="/app/shift-assignment">Phê duyệt xếp ca ↗</a><a href="/app/leave-application">Nghỉ phép ↗</a><a href="/lotus/cham-cong">Bảng công Lotus ↗</a></div>
   <div class="hr-ops-form">
    <label>Loại dữ liệu<UiSelect v-model="kind" @change="preview=null;uploadData=[]"><option v-for="k in kinds" :key="k" :value="k">{{kindLabels[k]}}</option></UiSelect></label>
    <div class="hr-ops-form-actions"><UiButton variant="outline" type="button" @click="template">Tải file mẫu CSV</UiButton></div>
    <label>Chọn tệp Excel hoặc CSV<input type="file" accept=".csv,.xlsx" :disabled="!manager||busy" @change="fileChanged"/></label>
   </div>
   <p class="hr-ops-tip">Giữ mã máy và mã nhân viên dạng chữ trong Excel để không mất số 0 đầu. Chỉ nhập danh sách thật sau khi đã đối chiếu; không nhập vân tay/khuôn mặt.</p>
   <div v-if="preview" class="hr-ops-panel">
    <strong>{{uploadName}}: {{preview.ready}} dòng hợp lệ, {{preview.errors.length}} dòng lỗi.</strong>
    <ul v-if="preview.errors.length"><li v-for="r in preview.errors" :key="r.row">Dòng {{r.row}}: {{r.error}}</li></ul>
    <div v-if="preview.normalized?.length" class="hr-ops-scroll"><table><thead><tr><th>Dòng</th><th v-for="field in columns[kind]" :key="field">{{field}}</th></tr></thead>
     <tbody><tr v-for="r in preview.normalized.slice(0,20)" :key="r.row"><td>{{r.row}}</td><td v-for="field in columns[kind]" :key="field">{{r.values[field]||'—'}}</td></tr></tbody></table></div>
    <p v-if="preview.ready>20" class="hr-ops-tip">Đang hiện 20 dòng đầu, các dòng còn lại vẫn được kiểm tra.</p>
    <UiButton v-if="manager" type="button" :disabled="busy||preview.errors?.length>0||!preview.ready" @click="confirmImport">Xác nhận nhập {{preview.ready}} dòng</UiButton>
   </div>
  </section>
 </template>
 <template v-else-if="active==='devices'">
  <section class="hr-ops-panel"><h3>Máy chấm công</h3>
   <div class="hr-ops-scroll"><table><thead><tr><th>Mã máy</th><th>Tên</th><th>Vườn</th><th>Dòng máy</th><th>Kiểu kết nối</th><th>Trạng thái</th></tr></thead>
     <tbody><tr v-for="m in hardware?.machines||[]" :key="m.name"><td>{{m.device_code}}</td><td>{{m.device_name}}</td><td>{{m.farm}}</td><td>{{m.model||'Chưa rõ'}}</td><td>{{m.connection_mode}}</td><td>{{m.active?'Đang dùng':'Tắt'}}</td></tr></tbody></table></div>
   <UiButton v-if="manager" type="button" variant="outline" @click="editDevice=true">＋ Khai báo máy</UiButton>
   <WorkspaceModal v-if="manager" v-model="editDevice" title="Khai báo máy chấm công" :busy="busy"><p v-if="error" class="hr-ops-error" role="alert">{{error}}</p><form class="hr-ops-form" @submit.prevent="saveDevice">
    <label>Vườn<UiSelect v-model="machine.farm" required><option value="">Chọn</option><option v-for="f in farmChoices" :key="f.name" :value="f.name">{{f.farm_name}}</option></UiSelect></label>
    <label>Mã máy<UiInput v-model="machine.device_code" required placeholder="VD: ATT-A-01"/></label>
    <label>Tên máy<UiInput v-model="machine.device_name" required placeholder="VD: Cổng đội khu A"/></label>
    <label>Dòng máy / hãng<UiInput v-model="machine.model" placeholder="Mã chính xác trên tem máy"/></label>
    <label>Serial máy<UiInput v-model="machine.serial_number"/></label>
    <label>Cách kết nối<UiSelect v-model="machine.connection_mode"><option v-for="mode in ['File CSV','ADMS','LAN SDK','Vendor Cloud']" :key="mode">{{mode}}</option></UiSelect></label>
    <label>Múi giờ<UiInput v-model="machine.timezone" readonly/></label>
    <UiButton type="submit" :disabled="busy">Lưu máy</UiButton>
   </form></WorkspaceModal>
   <p class="hr-ops-tip">ADMS, LAN SDK hoặc Cloud là loại giao thức khai báo, chưa phải kết nối đang hoạt động. Không tự mở cổng mạng hoặc tải dữ liệu sinh trắc học.</p>
  </section>
 </template>
 <template v-if="active==='logs'||view==='devices'">
  <section class="hr-ops-panel">
   <h3>Lượt chấm công</h3>
   <div class="hr-ops-actions"><a href="/app/employee-checkin">Xem log HRMS ↗</a><a href="/app/shift-assignment">Xem lịch ca ↗</a><a href="/app/attendance">Chấm công đã duyệt ↗</a></div>
   <div class="hr-ops-metrics"><span>Chưa ghép: <strong>{{hardware?.counts?.Unmapped||0}}</strong></span><span>Chờ chuyển: <strong>{{hardware?.counts?.Ready||0}}</strong></span><span>Đã chuyển: <strong>{{hardware?.counts?.Synced||0}}</strong></span><span>Cần kiểm tra: <strong>{{hardware?.counts?.['Needs Review']||0}}</strong></span><span>Đã bỏ qua: <strong>{{hardware?.counts?.Ignored||0}}</strong></span></div>
   <div class="hr-ops-actions"><UiButton v-if="manager" type="button" :disabled="busy||!selectedPunches.length" @click="sync">Chuyển {{selectedPunches.length}} log sang HRMS</UiButton><UiButton v-if="manager" type="button" variant="outline" :disabled="busy||!selectedPunches.length" @click="ignoreReason='';ignoreOpen=true">Bỏ qua {{selectedPunches.length}} log…</UiButton><a href="/lotus/cham-cong">Mở bảng công để duyệt ↗</a></div>
   <div v-if="manager" class="hr-ops-actions"><label>Từ ngày<DatePicker v-model="syncFrom" :disabled="busy" aria-label="Chuyển log từ ngày"/></label><label>Đến ngày<DatePicker v-model="syncTo" :min="syncFrom" :disabled="busy" aria-label="Chuyển log đến ngày"/></label><UiButton type="button" variant="outline" :disabled="busy||!syncFrom||!syncTo" @click="syncRange">Chuyển tất cả log trong khoảng</UiButton><span class="hr-ops-tip">Hệ thống tự chuyển log hôm nay và hôm qua mỗi 10 phút; mở Chấm công cũng cập nhật ngày đang xem.</span></div>
   <div class="hr-ops-scroll"><table><thead><tr><th><input v-if="manager&&openPunches.length" type="checkbox" :checked="allOpen" aria-label="Chọn mọi log chưa xử lý" @change="toggleOpen"/></th><th>Thời gian</th><th>Máy</th><th>Mã trên máy</th><th>Nhân viên</th><th>Vào / Ra</th><th>Trạng thái</th></tr></thead>
    <tbody><tr v-for="p in hardware?.punches||[]" :key="p.name">
     <td><input v-if="manager&&!['Synced','Ignored'].includes(p.state)" type="checkbox" :value="p.name" v-model="selected" :aria-label="'Chọn log '+p.punched_at"/></td>
     <td>{{p.punched_at}}</td><td>{{p.device}}</td><td>{{p.device_user_id}}</td><td>{{p.employee||'Chưa ghép'}}</td><td>{{stateLabel(p.log_type||'Unknown')}}</td><td>{{stateLabel(p.state)}}</td>
    </tr></tbody></table></div>
   <p class="hr-ops-tip">Nếu chưa có log, vào tab Nhập Excel → Mã máy ↔ nhân viên, sau đó Nhập log máy. Log trùng sẽ được bỏ qua.</p>
  </section>
 </template>
 <WorkspaceModal v-model="ignoreOpen" title="Bỏ qua log máy chấm công" :busy="busy" width="560px">
  <form class="hr-ops-form" @submit.prevent="ignore"><p>{{selectedPunches.length}} log đã chọn sẽ không tính công và không chặn khóa kỳ. Log gốc vẫn được lưu để đối soát.</p>
   <label>Lý do<UiInput v-model="ignoreReason" required minlength="5" maxlength="300" placeholder="VD: thẻ thử máy, mã không thuộc nhân viên nào"/></label>
   <div class="hr-ops-actions"><UiButton type="button" variant="outline" :disabled="busy" @click="ignoreOpen=false">Quay lại</UiButton><UiButton type="submit" :disabled="busy||ignoreReason.trim().length<5">Bỏ qua log</UiButton></div></form>
 </WorkspaceModal>
 <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" :alert-only="confirmAlert" @answer="finishConfirm"/>
</div>
</template>
