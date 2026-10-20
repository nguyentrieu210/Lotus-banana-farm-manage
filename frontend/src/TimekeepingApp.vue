<script setup>
const props=defineProps({embedded:Boolean,navigationKey:String})
import {computed,nextTick,onMounted,reactive,ref} from 'vue'
import WorkspaceModal from './components/WorkspaceModal.vue'
import WorkspaceTabs from './components/WorkspaceTabs.vue'
import DataTable from './components/DataTable.vue'
import LotusIcon from './components/LotusIcon.vue'
import MonthPicker from './components/MonthPicker.vue'
import TkMonthSheet from './components/timekeeping/TkMonthSheet.vue'
import TkSetup from './components/timekeeping/TkSetup.vue'
import TkCorrection from './components/timekeeping/TkCorrection.vue'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import UiSelect from './components/ui/select/Select.vue'
import {Textarea as UiTextarea} from './components/ui/textarea'
import {DatePicker} from './components/ui/date-picker'
import {FormField} from './components/ui/form-field'
import {DropdownMenu,DropdownMenuTrigger,DropdownMenuContent,DropdownMenuItem,DropdownMenuSeparator} from './components/ui/dropdown-menu'
import {useNoticeToast} from './use-toast'
import {call,setCSRF} from './api'
import {sidebarCollapsed} from './workspace'
import {unitLabel} from './units'
import {formatDate} from './format'

// /lotus/cham-cong: daily staff attendance (HRMS Attendance, filled from device check-ins), contractor crew sheets,
// the month sheet and setup. Drafts are reviewed and submitted here; a closed month is read-only.
const api=(name,args={},write=false)=>call('lotus_farm.timekeeping.'+name,args,write)
const session=ref(null),company=ref(''),date=ref(''),month=ref(''),shift=ref(''),farm=ref(''),tab=ref('staff'),search=ref(''),view=ref('all')
const busy=ref(false),saving=ref(false),machineBusy=ref(false),error=ref(''),notice=ref('')
const catalog=ref({farms:[],teams:[],shifts:[],employees:[],works:[],genders:[],departments:[],uoms:[]})
const staff=ref([]),crews=ref([]),availableTeams=ref([]),monthData=ref(null),crewMonth=ref(null),eventId=ref(crypto.randomUUID())
const dayInfo=ref({holiday:null,has_calendar:true,period_closed:false})
const crewDialog=ref(null),masterDialog=ref(null),confirmDialog=ref(null),setup=ref(null)
const masterKind=ref('employee'),confirmation=ref(null),reason=ref('')
const correcting=ref(null),correctionOpen=ref(false)
const canCorrect=computed(()=>!!session.value?.can_manage_shifts&&!locked.value)
function openCorrection(row){correcting.value=row;correctionOpen.value=true}
async function corrected(r){notice.value='Đã sửa công ('+r.amended_from+' → '+r.name+').';await load()}
const crew=reactive({}),master=reactive({}),crewBaseline=ref('')
const crewSnapshot=()=>JSON.stringify(Object.fromEntries(['work_type','headcount','present','workdays','completed_qty','uom','unit_rate','rate_override_reason','notes'].map(f=>[f,crew[f]])))

const cap=computed(()=>session.value?.capabilities||{})
const dirty=computed(()=>staff.value.some(r=>r.edited))
const locked=computed(()=>!!dayInfo.value.period_closed)
const canEditStaff=computed(()=>!locked.value&&!!(cap.value.Attendance?.create||cap.value.Attendance?.write))
const selected=computed(()=>staff.value.filter(r=>r.selected))
const statuses={'Present':'Có mặt','Half Day':'Nửa ngày','Absent':'Vắng','Work From Home':'Làm từ xa','On Leave':'Nghỉ phép'}
const editableStatuses=Object.entries(statuses).filter(([key])=>key!=='On Leave')
const rowState=r=>r.machine?.needs_review?'review':!r.name?'empty':r.docstatus===1?'approved':'draft'
const stateLabel={empty:'Chưa chấm',draft:'Nháp',approved:'Đã duyệt',review:'Cần kiểm tra'}
const counts=computed(()=>{const c={all:staff.value.length,empty:0,draft:0,approved:0,review:0};for(const r of staff.value)c[rowState(r)]++;return c})
const views=computed(()=>[['all','Tất cả'],['empty','Chưa chấm'],['draft','Nháp'],['approved','Đã duyệt'],...(counts.value.review?[['review','Cần kiểm tra']]:[])])
const shown=computed(()=>view.value==='all'?staff.value:staff.value.filter(r=>rowState(r)===view.value))
const allChecked=computed(()=>shown.value.length>0&&shown.value.every(r=>r.selected))

const genderLabel=name=>({Male:'Nam',Female:'Nữ',Other:'Khác',Transgender:'Chuyển giới',Genderqueer:'Phi nhị nguyên',"Prefer not to say":'Không khai báo'})[name]||name
const fmt=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
const currency=computed(()=>session.value?.companies.find(c=>c.name===company.value)?.default_currency||'VND')
const cash=n=>Number(n||0).toLocaleString('vi-VN',{style:'currency',currency:currency.value})
const teamName=name=>catalog.value.teams.find(t=>t.name===name)?.team_name||name
const docState=n=>['Nháp','Đã duyệt','Đã hủy'][n]||'Chưa chấm'
const clock=v=>v?String(v).slice(11,16):''
const monthLabel=value=>value?'Tháng '+value.slice(5,7)+'/'+value.slice(0,4):''
function punchText(row){
 const p=row.machine
 if(p&&!p.checkins)return p.reason||''
 const span=p?clock(p.in_time)+'–'+(clock(p.out_time)||'?'):row.in_time?clock(row.in_time)+'–'+(clock(row.out_time)||'?'):''
 return span
}
const punchFlags=row=>{const p=row.machine||row;return [p.late_entry?'Muộn':'',p.early_exit?'Về sớm':'',row.machine?.reason&&row.machine.checkins?row.machine.reason:''].filter(Boolean)}

const tabs=computed(()=>[
 {id:'staff',label:'Nhân sự chính thức',allowed:cap.value.Attendance?.read&&cap.value.Employee?.read},
 {id:'crew',label:'Đội khoán',allowed:cap.value['Lotus Crew Attendance']?.read},
 {id:'month',label:'Bảng công tháng',allowed:cap.value.Attendance?.read||cap.value['Lotus Crew Attendance']?.read},
 {id:'setup',label:'Thiết lập',allowed:true},
].filter(t=>t.allowed))

let version=0
async function loadCatalog(){catalog.value={...catalog.value,...await api('catalogue',{company:company.value})}}
async function load(){if(!company.value)return;const id=++version;busy.value=true;error.value=''
 try{
  if(tab.value==='staff'){
   const result=await api('staff_day',{company:company.value,date:date.value,shift:shift.value,search:search.value})
   if(id===version){staff.value=result.rows.map(r=>({...r,selected:false,edited:false,machine:null}));dayInfo.value={holiday:result.holiday,has_calendar:result.has_calendar,period_closed:result.period_closed};eventId.value=crypto.randomUUID();view.value='all'}
  }
  if(tab.value==='crew'){const result=await api('crew_day',{company:company.value,date:date.value,farm:farm.value});if(id===version){crews.value=result.rows;availableTeams.value=result.teams}}
  if(tab.value==='month'){
   const [people,teams]=await Promise.all([cap.value.Attendance?.read&&cap.value.Employee?.read?api('monthly',{company:company.value,month:month.value}):null,cap.value['Lotus Crew Attendance']?.read?api('crew_monthly',{company:company.value,month:month.value,farm:farm.value}):null])
   if(id===version){monthData.value=people;crewMonth.value=teams}
  }
  if(tab.value==='setup')await setup.value?.load()
 }catch(e){if(id===version)error.value=e.message}finally{if(id===version)busy.value=false}
}
async function init(){busy.value=true
 try{session.value=await api('bootstrap');setCSRF(session.value.csrf_token);company.value=session.value.companies[0]?.name||'';date.value=session.value.today;month.value=date.value.slice(0,7);tab.value=tabs.value[0]?.id||'setup';if(company.value){await loadCatalog();await load()}}
 catch(e){error.value=e.message}finally{busy.value=false}}
async function changeCompany(){farm.value='';shift.value='';staff.value=[];await loadCatalog();await load()}
function chooseTab(value){if(dirty.value){error.value='Lưu hoặc bỏ thay đổi bảng công trước khi chuyển màn hình.';return}tab.value=value;notice.value='';load()}

function edit(row){row.selected=true;row.edited=true}
function chooseStatus(row){row.working_hours=row.status==='Half Day'?4:row.status==='Absent'?0:8;if(row.status==='Absent')row.overtime_hours=0;edit(row)}
function markPresent(){for(const row of staff.value)if(row.docstatus===0&&row.status!=='On Leave'&&!row.status){row.status='Present';chooseStatus(row)}}
function toggleAll(){const value=!allChecked.value;for(const r of shown.value)r.selected=value}
// Fills unsaved rows from device check-ins; the manager still reviews, saves and submits.
async function fromMachine(){machineBusy.value=true;error.value=''
 try{
  const result=await api('propose_from_checkins',{company:company.value,date:date.value,shift:shift.value});const proposals=new Map(result.rows.map(r=>[r.employee,r]));let applied=0,review=0
  for(const row of staff.value){const p=proposals.get(row.employee);if(!p||row.docstatus!==0||row.status==='On Leave')continue
   row.machine=p;if(p.needs_review){review++;continue}if(!p.status)continue
   Object.assign(row,{shift:p.shift||row.shift,status:p.status,working_hours:p.working_hours,overtime_hours:p.overtime_hours,in_time:p.in_time,out_time:p.out_time,late_entry:p.late_entry,early_exit:p.early_exit});edit(row);applied++}
  notice.value='Đã điền '+applied+' dòng từ '+result.checkins+' lượt chấm'+(review?'; '+review+' dòng thiếu lượt chấm cần kiểm tra':'')+'. Kiểm tra rồi bấm Lưu nháp.'
 }catch(e){error.value=e.message}finally{machineBusy.value=false}}
async function saveStaff(){
 const rows=selected.value.filter(r=>r.docstatus===0&&r.status&&r.status!=='On Leave')
 if(!rows.length){error.value='Chọn nhân viên và trạng thái để lưu nháp.';return}
 saving.value=true;error.value=''
 try{await api('save_staff',{company:company.value,date:date.value,shift:shift.value,client_event_id:eventId.value,rows:rows.map(r=>({employee:r.employee,name:r.name,modified:r.modified,status:r.status,working_hours:r.working_hours,overtime_hours:r.overtime_hours||0,in_time:r.in_time||null,out_time:r.out_time||null,late_entry:r.late_entry?1:0,early_exit:r.early_exit?1:0,shift:r.shift||null,note:r.note}))},true);notice.value='Đã lưu '+rows.length+' dòng công nháp.';await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
async function askStaff(action){
 const rows=selected.value
 if(!rows.length||rows.some(r=>r.edited||!r.name||r.docstatus!==(action==='cancel'?1:0))){error.value='Chọn các phiếu '+(action==='cancel'?'đã duyệt':'nháp đã lưu')+' phù hợp thao tác. Lưu thay đổi trước khi duyệt.';return}
 confirmation.value={type:'staff',action,rows:rows.map(r=>({name:r.name,modified:r.modified}))};reason.value='';await nextTick();confirmDialog.value.showModal()}
async function askCrew(row,action){if(action==='submit'&&crewSnapshot()!==crewBaseline.value){error.value='Lưu thay đổi trước khi duyệt phiếu công.';return}confirmation.value={type:'crew',action,name:row.name,modified:row.modified};reason.value='';await nextTick();confirmDialog.value.showModal()}
async function act(){saving.value=true;error.value=''
 try{const item=confirmation.value;await api(item.type==='staff'?'staff_action':'crew_action',{company:company.value,...item,reason:reason.value},true);confirmDialog.value.close();if(item.type==='crew')crewDialog.value.close();notice.value=item.action==='submit'?'Đã duyệt bảng công.':item.action==='cancel'?'Đã hủy phiếu công.':'Đã xóa phiếu nháp.';await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}

async function openCrew(row=null){error.value='';Object.assign(crew,{name:null,modified:null,farm:farm.value||catalog.value.farms[0]?.name||'',work_team:'',posting_date:date.value,headcount:0,present:0,workdays:0,completed_qty:0,uom:'',unit_rate:0,work_type:'',listed_piecework_rate:0,rate_override_reason:'',notes:'',client_event_id:crypto.randomUUID()},row||{});crewBaseline.value=crewSnapshot();await nextTick();crewDialog.value.showModal()}
function setTeam(){const team=catalog.value.teams.find(t=>t.name===crew.work_team);if(team)crew.farm=team.farm}
function setWork(){const work=(catalog.value.works||[]).find(w=>w.name===crew.work_type);if(work){crew.uom=work.uom;crew.listed_piecework_rate=Number(work.piecework_rate||0);crew.unit_rate=crew.listed_piecework_rate;crew.rate_override_reason=''}}
async function saveCrew(){saving.value=true;error.value='';try{const {client_event_id,...values}=crew;await api('save_crew',{company:company.value,values,client_event_id},true);crewDialog.value.close();notice.value='Đã lưu phiếu công đội khoán nháp.';await load()}catch(e){error.value=e.message}finally{saving.value=false}}
const masterTitle={employee:'Thêm nhân sự chính thức',team:'Đội khoán / đầu câu',farm:'Thêm vườn'}
async function openMaster(kind){error.value='';masterKind.value=kind;for(const key of Object.keys(master))delete master[key]
 Object.assign(master,kind==='employee'?{employee_name:'',gender:'',date_of_birth:'',date_of_joining:date.value,designation:'',department:''}:kind==='team'?{farm:farm.value||catalog.value.farms[0]?.name||'',name:'',code:'',foreman:'',phone:''}:{code:'',name:''})
 await nextTick();masterDialog.value.showModal()}
async function saveMaster(){saving.value=true;error.value=''
 try{if(masterKind.value==='farm')await api('create_farm',{company:company.value,...master},true);else await api(masterKind.value==='employee'?'create_employee':'create_team',{company:company.value,values:{...master}},true)
  masterDialog.value.close();notice.value='Đã tạo '+({employee:'nhân viên',team:'đội khoán',farm:'vườn'})[masterKind.value]+'.';await loadCatalog();await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}

const crewColumns=[{field:'work_team',headerName:'Đội khoán',minWidth:190,valueFormatter:p=>teamName(p.value)},{field:'work_type',headerName:'Công việc',minWidth:170,valueFormatter:p=>(catalog.value.works||[]).find(w=>w.name===p.value)?.work_name||p.value||'Cũ'},{field:'foreman',headerName:'Đầu câu',minWidth:140},{field:'headcount',headerName:'Tổng người',minWidth:100},{field:'present',headerName:'Có mặt',minWidth:85},{field:'workdays',headerName:'Tổng công',minWidth:100,valueFormatter:p=>fmt(p.value)},{field:'amount',headerName:'Giá trị khoán',minWidth:140,valueFormatter:p=>cash(p.value)},{field:'docstatus',headerName:'Trạng thái',minWidth:110,valueFormatter:p=>docState(p.value)}]
const printLink=kind=>'/lotus/in-cong?'+new URLSearchParams({company:company.value,month:month.value,kind,...(farm.value&&kind==='crew'?{farm:farm.value}:{})})
const exportLink=kind=>'/api/method/lotus_farm.timekeeping.export_month?'+new URLSearchParams({company:company.value,month:month.value,kind,...(farm.value&&kind==='crew'?{farm:farm.value}:{})})
onMounted(init)
// Success messages show as toasts (errors stay inline next to the form).
useNoticeToast(notice)
</script>

<template><div class="stock-shell attendance-shell tk-shell lotus-ui" :class="{'embedded-workspace':embedded,'sidebar-collapsed':sidebarCollapsed}">
 <component :is="embedded?'section':'main'" class="stock-main"><WorkspaceTabs v-if="embedded" :items="tabs" :model-value="tab" label="Chấm công" @update:model-value="chooseTab($event)"/>
  <p v-if="error" class="stock-error" role="alert">{{error}}</p>
  <div v-if="tab!=='setup'||(session?.companies?.length||0)>1" class="stock-scope tk-filters">
   <label v-if="(session?.companies?.length||0)>1">Công ty<UiSelect v-model="company" :disabled="busy||saving||dirty" @change="changeCompany"><option v-for="c in session?.companies" :key="c.name">{{c.name}}</option></UiSelect></label>
   <label v-if="['staff','crew'].includes(tab)">Ngày công<DatePicker v-model="date" :max="session?.today" :clearable="false" aria-label="Ngày công" :disabled="busy||saving||dirty" @change="load"/></label>
   <label v-else-if="tab==='month'">Tháng<MonthPicker v-model="month" :max="session?.today?.slice(0,7)" :disabled="busy||saving" @change="load"/></label>
   <label v-if="tab==='staff'">Ca làm việc<UiSelect v-model="shift" :disabled="busy||saving||dirty" @change="load"><option value="">Theo lịch ca</option><option v-for="s in catalog.shifts" :key="s.name">{{s.name}}</option></UiSelect></label>
   <label v-if="['crew','month'].includes(tab)">Vườn<UiSelect v-model="farm" :disabled="busy||saving" @change="load"><option value="">Tất cả được phân quyền</option><option v-for="f in catalog.farms" :key="f.name" :value="f.name">{{f.farm_name}}</option></UiSelect></label>
   <label v-if="tab==='staff'" class="stock-search">Tìm nhân viên<UiInput v-model="search" type="search" placeholder="Tên hoặc mã nhân viên" :disabled="busy||dirty" @keyup.enter="load"/></label>
   <UiButton v-if="tab!=='setup'" variant="outline" :disabled="busy||saving||dirty" aria-label="Làm mới" @click="load"><LotusIcon name="refresh"/>{{busy?'Đang tải…':'Làm mới'}}</UiButton>
  </div>

  <template v-if="tab==='staff'">
   <p v-if="locked" class="tk-banner is-lock" role="status"><LotusIcon name="lock"/>Tháng {{date.slice(0,7)}} đã khóa công. Chỉ xem; HR Manager mở lại kỳ ở Hồ sơ nhân sự › Kỳ công & bảng lương.</p>
   <p v-else-if="dayInfo.holiday" class="tk-banner is-holiday" role="status"><LotusIcon name="flag"/>{{dayInfo.holiday.weekly_off?'Ngày nghỉ hằng tuần':'Ngày lễ: '+dayInfo.holiday.description}}. Giờ làm ngày này tính hệ số {{dayInfo.holiday.weekly_off?'200%':'300%'}}.</p>
   <p v-else-if="!dayInfo.has_calendar" class="tk-banner is-info" role="status"><LotusIcon name="calendar"/>Chưa có lịch nghỉ năm nay. Tạo ở tab Thiết lập › Lịch nghỉ năm để tính lễ và khóa kỳ.</p>
   <div class="tk-views" role="tablist" aria-label="Lọc theo trạng thái công"><button v-for="[id,label] in views" :key="id" type="button" role="tab" :aria-selected="view===id?'true':'false'" :class="['is-'+id,{active:view===id}]" @click="view=id">{{label}}<strong>{{counts[id]}}</strong></button></div>
   <div class="attendance-toolbar tk-actions">
    <UiButton v-if="cap.Attendance?.create&&session?.can_read_checkins&&!locked" variant="outline" :disabled="machineBusy||saving||busy" @click="fromMachine"><LotusIcon name="clock"/>{{machineBusy?'Đang đọc máy…':'Lấy công từ máy chấm'}}</UiButton>
    <span class="tk-actions__spacer"></span>
    <span v-if="selected.length" class="tk-actions__count">Đã chọn {{selected.length}}</span>
    <UiButton v-if="canEditStaff" :disabled="saving||busy||!dirty" @click="saveStaff">Lưu nháp</UiButton>
    <UiButton v-if="cap.Attendance?.submit&&!locked" variant="outline" :disabled="saving||!selected.length" @click="askStaff('submit')"><LotusIcon name="tick"/>Duyệt đã chọn</UiButton>
    <DropdownMenu v-if="!locked&&(cap.Attendance?.create||cap.Attendance?.cancel||cap.Attendance?.delete||dirty)">
     <DropdownMenuTrigger as-child><UiButton variant="outline" aria-label="Thao tác khác"><LotusIcon name="more"/></UiButton></DropdownMenuTrigger>
     <DropdownMenuContent align="end">
      <DropdownMenuItem v-if="cap.Attendance?.create" @select="markPresent"><LotusIcon name="check"/>Có mặt cho người chưa chấm</DropdownMenuItem>
      <DropdownMenuItem v-if="cap.Attendance?.cancel" @select="askStaff('cancel')"><LotusIcon name="x"/>Hủy phiếu đã duyệt</DropdownMenuItem>
      <DropdownMenuItem v-if="cap.Attendance?.delete" @select="askStaff('delete')"><LotusIcon name="trash"/>Xóa phiếu nháp</DropdownMenuItem>
      <template v-if="dirty"><DropdownMenuSeparator/><DropdownMenuItem @select="load"><LotusIcon name="refresh"/>Bỏ thay đổi chưa lưu</DropdownMenuItem></template>
     </DropdownMenuContent>
    </DropdownMenu>
   </div>
   <section class="stock-panel attendance-roster tk-roster" aria-label="Bảng chấm công trong ngày">
    <table><thead><tr><th class="tk-col-check"><input type="checkbox" :checked="allChecked" aria-label="Chọn tất cả nhân viên đang hiện" @change="toggleAll"></th><th>Nhân viên</th><th class="tk-col-shift">Ca</th><th class="tk-col-status">Trạng thái</th><th class="tk-col-punch">Máy chấm</th><th class="tk-col-num">Giờ làm</th><th class="tk-col-num">Tăng ca</th><th>Ghi chú</th><th class="tk-col-state">Phiếu</th></tr></thead>
     <tbody><tr v-for="row in shown" :key="row.employee" :class="{'attendance-review':row.machine?.needs_review,'is-edited':row.edited,'is-selected':row.selected}">
      <td class="tk-col-check"><input v-model="row.selected" type="checkbox" :aria-label="'Chọn '+row.employee_name"></td>
      <td class="tk-col-person"><strong>{{row.employee_name}}</strong><small>{{row.employee}}<template v-if="row.designation||row.department"> · {{row.designation||row.department}}</template></small></td>
      <td class="tk-col-shift" data-label="Ca">{{row.shift||'—'}}</td>
      <td class="tk-col-status" data-label="Trạng thái"><UiSelect v-model="row.status" :aria-label="'Trạng thái '+row.employee_name" :disabled="saving||row.docstatus===1||row.status==='On Leave'||!canEditStaff" @change="chooseStatus(row)"><option value="">Chưa chấm</option><option v-if="row.status==='On Leave'" value="On Leave">Nghỉ phép (HRMS)</option><option v-for="[value,label] in editableStatuses" :key="value" :value="value">{{label}}</option></UiSelect></td>
      <td class="tk-col-punch" data-label="Máy chấm"><span>{{punchText(row)||'—'}}</span><small v-for="flag in punchFlags(row)" :key="flag" class="tk-flag">{{flag}}</small><small v-if="row.machine?.needs_review" class="tk-flag is-warn">Cần kiểm tra</small></td>
      <td class="tk-col-num" data-label="Giờ làm"><UiInput v-model.number="row.working_hours" type="number" min="0" max="24" step="0.25" :aria-label="'Giờ làm '+row.employee_name" :disabled="saving||row.docstatus===1||row.status==='On Leave'||!canEditStaff" @input="edit(row)"/></td>
      <td class="tk-col-num" data-label="Tăng ca"><UiInput v-model.number="row.overtime_hours" type="number" min="0" max="16" step="0.25" :aria-label="'Giờ tăng ca '+row.employee_name" :disabled="saving||row.docstatus===1||['On Leave','Absent'].includes(row.status)||!canEditStaff" @input="edit(row)"/></td>
      <td class="tk-col-note" data-label="Ghi chú"><UiInput v-model="row.note" :aria-label="'Ghi chú '+row.employee_name" :disabled="saving||row.docstatus===1||!canEditStaff" @input="edit(row)"/></td>
      <td class="tk-col-state" data-label="Phiếu"><span class="tk-pill" :class="'is-'+rowState(row)">{{stateLabel[rowState(row)]}}</span><small v-if="row.edited" class="tk-flag is-warn">Chưa lưu</small><UiButton v-if="canCorrect&&row.docstatus===1" variant="link" size="sm" class="tk-correct" :aria-label="'Sửa công đã duyệt của '+row.employee_name" @click="openCorrection(row)">Sửa công</UiButton></td>
     </tr></tbody></table>
    <div v-if="!shown.length&&!busy" class="tk-empty">
     <template v-if="staff.length">Không có nhân viên ở trạng thái này.</template>
     <template v-else>Chưa có nhân viên đang làm trong công ty này.<UiButton v-if="cap.Employee?.create" variant="link" @click="openMaster('employee')">Thêm nhân sự</UiButton></template>
    </div>
   </section>
  </template>

  <template v-if="tab==='crew'">
   <div class="attendance-toolbar tk-actions"><UiButton v-if="cap['Lotus Crew Attendance']?.create" :disabled="!availableTeams.length||saving" @click="openCrew()"><LotusIcon name="plus"/>Phiếu công đội khoán</UiButton><UiButton v-if="cap['Work Team']?.create" variant="outline" @click="openMaster('team')"><LotusIcon name="people"/>Đội / đầu câu</UiButton><span class="tk-actions__spacer"></span><span class="tk-actions__count">{{crews.length}} phiếu ngày {{formatDate(date)}}</span></div>
   <p v-if="!availableTeams.length&&!busy" class="tk-banner is-info" role="status"><LotusIcon name="people"/>Chưa có đội khoán đang hoạt động. Tạo đội và đầu câu trước khi lập phiếu công.</p>
   <section class="stock-panel"><DataTable :rows="crews" :columns="crewColumns" :loading="busy" interactive @open="openCrew" empty="Chưa có phiếu công đội khoán trong ngày."/></section>
  </template>

  <template v-if="tab==='month'">
   <section v-if="monthData" class="tk-card" aria-label="Bảng công nhân sự tháng">
    <header class="tk-card__head"><h3>Nhân sự chính thức · {{monthLabel(month)}}</h3><span v-if="monthData.period_closed" class="tk-pill is-approved"><LotusIcon name="lock"/>Đã khóa kỳ</span><span class="tk-actions__spacer"></span><a v-if="cap.Attendance?.print" class="stock-button" :href="printLink('staff')" target="_blank" rel="noopener"><LotusIcon name="printer"/>In bảng công</a><a v-if="cap.Attendance?.export" class="stock-button" :href="exportLink('staff')"><LotusIcon name="download"/>Xuất CSV</a></header>
    <TkMonthSheet :data="monthData" kind="staff" :month="month" :currency="currency"/>
    <p class="tk-legend"><span class="is-ok">X</span> Có mặt <span class="is-half">½</span> Nửa ngày <span class="is-off">V</span> Vắng <span class="is-ok">TX</span> Từ xa <span class="is-leave">P</span> Nghỉ phép <span class="is-draft">X</span> Nháp, chưa tính tổng <span class="is-day-off"></span> Ngày nghỉ tuần <span class="is-day-holiday"></span> Ngày lễ</p>
   </section>
   <section v-if="crewMonth" class="tk-card" aria-label="Bảng công đội khoán tháng">
    <header class="tk-card__head"><h3>Đội khoán · {{monthLabel(month)}}</h3><span class="tk-actions__spacer"></span><a v-if="cap['Lotus Crew Attendance']?.print" class="stock-button" :href="printLink('crew')" target="_blank" rel="noopener"><LotusIcon name="printer"/>In bảng công</a><a v-if="cap['Lotus Crew Attendance']?.export" class="stock-button" :href="exportLink('crew')"><LotusIcon name="download"/>Xuất CSV</a></header>
    <TkMonthSheet :data="crewMonth" kind="crew" :month="month" :currency="currency"/>
    <p class="tk-legend">Mỗi ô là tổng công của đội trong ngày. Giá trị khoán là khoản phải trả cho đội, chưa phải chứng từ thanh toán.</p>
   </section>
  </template>

  <TkSetup v-if="tab==='setup'" ref="setup" :company="company" :session="session" :catalog="catalog" :cap="cap" :month="month" @open-master="openMaster" @changed="loadCatalog" @notice="notice=$event" @error="error=$event"/>
 </component>

 <WorkspaceModal bare title="Phiếu công đội khoán" :busy="saving" ref="crewDialog" class="stock-dialog"><form @submit.prevent="saveCrew"><header><h2>Phiếu công đội khoán</h2><UiButton type="button" variant="outline" :disabled="saving" aria-label="Đóng phiếu công đội" @click="crewDialog.close()"><LotusIcon name="x"/></UiButton></header><p v-if="error" class="stock-error" role="alert">{{error}}</p>
  <div class="attendance-form">
   <FormField label="Đội khoán" required v-slot="f"><UiSelect v-bind="f" v-model="crew.work_team" :disabled="!!crew.name||saving" @change="setTeam"><option value="">Chọn đội</option><option v-for="team in catalog.teams" :key="team.name" :value="team.name">{{team.team_name}} · {{team.lotus_foreman}}</option></UiSelect></FormField>
   <FormField label="Ngày công" required v-slot="f"><DatePicker v-bind="f" v-model="crew.posting_date" :max="session?.today" :disabled="!!crew.name||saving" aria-label="Ngày công đội"/></FormField>
   <FormField label="Công việc khoán" v-slot="f"><UiSelect v-bind="f" v-model="crew.work_type" :disabled="!!crew.name||crew.docstatus===1||saving" @change="setWork"><option value="">Chọn công việc</option><option v-for="w in catalog.works||[]" :key="w.name" :value="w.name">{{w.work_name}}</option></UiSelect></FormField>
   <FormField label="Tổng người" required v-slot="f"><UiInput v-bind="f" v-model.number="crew.headcount" type="number" min="0" step="1" :disabled="crew.docstatus===1||saving"/></FormField>
   <FormField label="Có mặt" required v-slot="f"><UiInput v-bind="f" v-model.number="crew.present" type="number" min="0" :max="crew.headcount" step="1" :disabled="crew.docstatus===1||saving"/></FormField>
   <FormField label="Tổng công" required v-slot="f"><UiInput v-bind="f" v-model.number="crew.workdays" type="number" min="0" :max="crew.present" step="0.25" :disabled="crew.docstatus===1||saving"/></FormField>
   <FormField label="Khối lượng khoán" v-slot="f"><UiInput v-bind="f" v-model.number="crew.completed_qty" type="number" min="0" step="any" :disabled="crew.docstatus===1||saving"/></FormField>
   <FormField label="Đơn vị khoán" :required="crew.completed_qty>0" v-slot="f"><UiSelect v-bind="f" v-model="crew.uom" :disabled="crew.docstatus===1||saving||!!crew.work_type"><option value="">Chọn đơn vị</option><option v-for="unit in catalog.uoms" :key="unit.name" :value="unit.name">{{unitLabel(unit.name)}}</option></UiSelect></FormField>
   <FormField :label="'Đơn giá khoán ('+currency+')'" :hint="crew.work_type?'Niêm yết '+cash(crew.listed_piecework_rate)+' / '+unitLabel(crew.uom):''" v-slot="f"><UiInput v-bind="f" v-model.number="crew.unit_rate" type="number" min="0" step="any" :disabled="crew.docstatus===1||saving"/></FormField>
   <FormField v-if="crew.work_type&&Number(crew.unit_rate)!==Number(crew.listed_piecework_rate)" label="Lý do điều chỉnh đơn giá" required v-slot="f"><UiTextarea v-bind="f" v-model="crew.rate_override_reason" :disabled="crew.docstatus===1||saving"/></FormField>
  </div>
  <FormField label="Ghi chú" v-slot="f"><UiTextarea v-bind="f" v-model="crew.notes" :disabled="crew.docstatus===1||saving" maxlength="2000"/></FormField>
  <p class="tk-total">Giá trị khoán <strong>{{cash(Number(crew.completed_qty||0)*Number(crew.unit_rate||0))}}</strong></p>
  <footer><UiButton v-if="crew.name&&crew.docstatus===0&&cap['Lotus Crew Attendance']?.delete" type="button" variant="destructive" :disabled="saving" @click="askCrew(crew,'delete')">Xóa nháp</UiButton><UiButton v-if="crew.name&&crew.docstatus===1&&cap['Lotus Crew Attendance']?.cancel" type="button" variant="outline" :disabled="saving" @click="askCrew(crew,'cancel')">Hủy đã duyệt</UiButton><UiButton v-if="crew.name&&crew.docstatus===0&&cap['Lotus Crew Attendance']?.submit" type="button" variant="outline" :disabled="saving" @click="askCrew(crew,'submit')">Duyệt phiếu</UiButton><UiButton v-if="crew.docstatus!==1&&(crew.name?cap['Lotus Crew Attendance']?.write:cap['Lotus Crew Attendance']?.create)" type="submit" :disabled="saving">Lưu nháp</UiButton></footer>
 </form></WorkspaceModal>

 <WorkspaceModal bare title="Danh mục chấm công" :busy="saving" ref="masterDialog" class="stock-dialog"><form @submit.prevent="saveMaster"><header><h2>{{masterTitle[masterKind]}}</h2><UiButton type="button" variant="outline" :disabled="saving" aria-label="Đóng thiết lập" @click="masterDialog.close()"><LotusIcon name="x"/></UiButton></header><p v-if="error" class="stock-error" role="alert">{{error}}</p>
  <div class="attendance-form">
   <template v-if="masterKind==='employee'">
    <FormField label="Họ tên" required v-slot="f"><UiInput v-bind="f" v-model="master.employee_name" maxlength="140"/></FormField>
    <FormField label="Giới tính" required v-slot="f"><UiSelect v-bind="f" v-model="master.gender"><option value="">Chọn giới tính</option><option v-for="gender in catalog.genders" :key="gender.name" :value="gender.name">{{genderLabel(gender.name)}}</option></UiSelect></FormField>
    <FormField label="Ngày sinh" required v-slot="f"><DatePicker v-bind="f" v-model="master.date_of_birth" :max="session?.today" aria-label="Ngày sinh"/></FormField>
    <FormField label="Ngày vào làm" required v-slot="f"><DatePicker v-bind="f" v-model="master.date_of_joining" aria-label="Ngày vào làm"/></FormField>
    <FormField label="Chức vụ" v-slot="f"><UiInput v-bind="f" v-model="master.designation" maxlength="140" placeholder="VD: Quản lý vườn, kế toán…"/></FormField>
    <FormField label="Bộ phận" v-slot="f"><UiSelect v-bind="f" v-model="master.department"><option value="">Chưa phân bộ phận</option><option v-for="department in catalog.departments" :key="department.name" :value="department.name">{{department.department_name}}</option></UiSelect></FormField>
   </template>
   <template v-else-if="masterKind==='team'">
    <FormField label="Vườn" required v-slot="f"><UiSelect v-bind="f" v-model="master.farm"><option value="">Chọn vườn</option><option v-for="f2 in catalog.farms" :key="f2.name" :value="f2.name">{{f2.farm_name}}</option></UiSelect></FormField>
    <FormField label="Mã đội" required v-slot="f"><UiInput v-bind="f" v-model="master.code" maxlength="140"/></FormField>
    <FormField label="Tên đội" required v-slot="f"><UiInput v-bind="f" v-model="master.name" maxlength="140"/></FormField>
    <FormField label="Đầu câu / người phụ trách" required v-slot="f"><UiInput v-bind="f" v-model="master.foreman" maxlength="140"/></FormField>
    <FormField label="Điện thoại" v-slot="f"><UiInput v-bind="f" v-model="master.phone" maxlength="40"/></FormField>
   </template>
   <template v-else>
    <FormField label="Mã vườn" required v-slot="f"><UiInput v-bind="f" v-model="master.code" maxlength="140" placeholder="FARM-222"/></FormField>
    <FormField label="Tên vườn" required v-slot="f"><UiInput v-bind="f" v-model="master.name" maxlength="140" placeholder="Vườn 222 Thuận Phú"/></FormField>
   </template>
  </div>
  <footer><UiButton type="button" variant="outline" :disabled="saving" @click="masterDialog.close()">Hủy</UiButton><UiButton type="submit" :disabled="saving">{{saving?'Đang lưu…':'Tạo mới'}}</UiButton></footer>
 </form></WorkspaceModal>

 <TkCorrection v-model="correctionOpen" :company="company" :row="correcting" :shifts="catalog.shifts" @saved="corrected"/>
 <WorkspaceModal bare title="Xác nhận bảng công" :busy="saving" ref="confirmDialog" class="stock-dialog"><form @submit.prevent="act"><header><h2>{{confirmation?.action==='submit'?'Duyệt công':confirmation?.action==='cancel'?'Hủy công đã duyệt':'Xóa công nháp'}}</h2><UiButton type="button" variant="outline" :disabled="saving" aria-label="Đóng xác nhận công" @click="confirmDialog.close()"><LotusIcon name="x"/></UiButton></header><p v-if="error" class="stock-error" role="alert">{{error}}</p>
  <p v-if="confirmation?.type==='staff'">{{confirmation.rows.length}} phiếu công đã chọn.</p>
  <FormField v-if="confirmation?.action==='cancel'" label="Lý do hủy" required v-slot="f"><UiTextarea v-bind="f" v-model="reason" maxlength="2000"/></FormField>
  <footer><UiButton type="button" variant="outline" :disabled="saving" @click="confirmDialog.close()">Quay lại</UiButton><UiButton type="submit" :variant="confirmation?.action==='submit'?'default':'destructive'" :disabled="saving">Xác nhận</UiButton></footer>
 </form></WorkspaceModal>
</div></template>
