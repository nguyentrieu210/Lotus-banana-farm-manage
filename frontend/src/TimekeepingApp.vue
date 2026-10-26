<script setup>
import WorkspaceListToolbar from './components/WorkspaceListToolbar.vue'
import {hrCatalogLabel} from "./hr-catalog-labels"
const props=defineProps({embedded:Boolean,navigationKey:String})
import {computed,nextTick,onMounted,reactive,ref} from 'vue'
import ModalForm from './components/form/ModalForm.vue'
import FormGrid from './components/form/FormGrid.vue'
import LotusField from './components/form/LotusField.vue'
import WorkspaceTabs from './components/WorkspaceTabs.vue'
import DataTable from './components/DataTable.vue'
import TimekeepingGridCell from './components/TimekeepingGridCell.vue'
import LotusIcon from './components/LotusIcon.vue'
import MonthPicker from './components/MonthPicker.vue'
import TkMonthSheet from './components/timekeeping/TkMonthSheet.vue'
import TkSetup from './components/timekeeping/TkSetup.vue'
import TkCorrection from './components/timekeeping/TkCorrection.vue'
import {Button as UiButton} from './components/ui/button'
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
const busy=ref(false),saving=ref(false),error=ref(''),notice=ref('')
const catalog=ref({farms:[],teams:[],shifts:[],employees:[],works:[],genders:[],departments:[],uoms:[]})
const staff=ref([]),crews=ref([]),availableTeams=ref([]),monthData=ref(null),crewMonth=ref(null),eventId=ref(crypto.randomUUID())
const dayInfo=ref({holiday:null,has_calendar:true,period_closed:false,counts:{matching:0,review:0,manual:0},synced:null})
// Dialog handles keep the native-dialog calls (showModal / close) while ModalForm binds to .open.
function dialogHandle(){const open=ref(false);return reactive({open,showModal(){open.value=true},close(){open.value=false}})}
const crewDialog=ref(dialogHandle()),masterDialog=ref(dialogHandle()),confirmDialog=ref(dialogHandle()),setup=ref(null)
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
const attendanceCellActions={
 getRow:data=>staff.value.find(r=>r.employee===data.employee)||data,
 saving:()=>saving.value,
 canEditStaff:()=>canEditStaff.value,
 canCorrect:()=>canCorrect.value,
 chooseStatus:row=>chooseStatus(row),
 editableStatuses:()=>editableStatuses,
 onEdit:edit,
 punchFlags:row=>punchFlags(row),
 punchText:row=>punchText(row),
 useMachine:row=>useMachine(row),
 openCorrection:row=>openCorrection(row),
 rowState:row=>rowState(row),
 stateLabel:v=>stateLabel[v]||v
}
const attendanceRowClass=row=>[
 row.machine?.needs_review?'attendance-review':'',
 row.edited?'is-edited':'',
 row.selected?'is-selected':''
].filter(Boolean).join(' ')
const attendanceColumns=[
 {field:'selected',headerName:'Chọn',minWidth:105,sortable:false,cellRenderer:TimekeepingGridCell,cellRendererParams:attendanceCellActions},
 {field:'employee_name',headerName:'Nhân viên',minWidth:220,cellRenderer:TimekeepingGridCell,cellRendererParams:attendanceCellActions},
 {field:'shift',headerName:'Ca',minWidth:140},
 {field:'status',headerName:'Trạng thái',minWidth:190,cellRenderer:TimekeepingGridCell,cellRendererParams:attendanceCellActions},
 {field:'machine_punch',headerName:'Máy chấm',minWidth:240,valueGetter:p=>punchText(p.data)||'—',cellRenderer:TimekeepingGridCell,cellRendererParams:attendanceCellActions},
 {field:'working_hours',headerName:'Giờ làm',minWidth:130,cellRenderer:TimekeepingGridCell,cellRendererParams:attendanceCellActions},
 {field:'overtime_hours',headerName:'Tăng ca',minWidth:130,cellRenderer:TimekeepingGridCell,cellRendererParams:attendanceCellActions},
 {field:'note',headerName:'Ghi chú',minWidth:200,cellRenderer:TimekeepingGridCell,cellRendererParams:attendanceCellActions},
 {field:'row_state',headerName:'Phiếu',minWidth:180,valueGetter:p=>stateLabel[rowState(p.data)],cellRenderer:TimekeepingGridCell,cellRendererParams:attendanceCellActions}
]

const rowState=r=>r.docstatus===1?'approved':r.machine?.needs_review?'review':r.matches?'matching':!r.name?'empty':'draft'
const stateLabel={empty:'Chưa chấm',draft:'Nháp',approved:'Đã duyệt',review:'Cần kiểm tra',matching:'Khớp máy'}
const counts=computed(()=>{const c={all:staff.value.length,empty:0,draft:0,approved:0,review:0,matching:0};for(const r of staff.value)c[rowState(r)]++;return c})
const views=computed(()=>[['all','Tất cả'],...(counts.value.matching?[['matching','Khớp máy']]:[]),...(counts.value.review?[['review','Cần kiểm tra']]:[]),['empty','Chưa chấm'],['draft','Nháp'],['approved','Đã duyệt']])
// Rows needing a decision come first: device problems, then hand-edited drafts, then the rest.
const rank=r=>r.machine?.needs_review&&r.docstatus===0?0:r.manual?1:r.matches?2:r.docstatus===1?4:3
const shown=computed(()=>(view.value==='all'?staff.value:staff.value.filter(r=>rowState(r)===view.value)).slice().sort((a,b)=>rank(a)-rank(b)))
const allChecked=computed(()=>shown.value.length>0&&shown.value.every(r=>r.selected))

const genderLabel=name=>({Male:'Nam',Female:'Nữ',Other:'Khác',Transgender:'Chuyển giới',Genderqueer:'Phi nhị nguyên',"Prefer not to say":'Không khai báo'})[name]||hrCatalogLabel(name)
const fmt=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
const currency=computed(()=>session.value?.companies.find(c=>c.name===company.value)?.default_currency||'VND')
const cash=n=>Number(n||0).toLocaleString('vi-VN',{style:'currency',currency:currency.value})
const teamName=name=>catalog.value.teams.find(t=>t.name===name)?.team_name||name
const docState=n=>['Nháp','Đã duyệt','Đã hủy'][n]||'Chưa chấm'
const clock=v=>v?String(v).slice(11,16):''
const nextDay=(row,v)=>v&&String(v).slice(0,10)>date.value
const monthLabel=value=>value?'Tháng '+value.slice(5,7)+'/'+value.slice(0,4):''
function punchText(row){
 const p=row.machine
 if(p&&!p.checkins)return p.reason||''
 const span=p?clock(p.in_time)+' → '+(clock(p.out_time)||'?')+(nextDay(row,p.out_time)?' (+1)':''):row.in_time?clock(row.in_time)+' → '+(clock(row.out_time)||'?')+(nextDay(row,row.out_time)?' (+1)':''):''
 return span
}
const punchFlags=row=>{const p=row.machine;if(!p)return [row.late_entry?'Muộn':'',row.early_exit?'Về sớm':''].filter(Boolean)
 return [p.late_minutes>0&&p.late_entry?'Muộn '+p.late_minutes+'′':'',p.early_minutes>0&&p.early_exit?'Về sớm '+p.early_minutes+'′':'',p.after_minutes>=30?'Dư '+p.after_minutes+'′ → đề xuất TC '+p.suggested_overtime+' giờ':'',p.reason&&p.checkins?p.reason:''].filter(Boolean)}

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
   // The board syncs the day's device punches first and returns each row with its device reading.
   const keep=new Set(staff.value.filter(r=>r.selected&&r.date===date.value).map(r=>r.employee))
   const result=await call('lotus_farm.attendance_day.board',{company:company.value,date:date.value,shift:shift.value,search:search.value})
   if(id===version){staff.value=result.rows.map(r=>({...r,date:result.date,selected:keep.has(r.employee),edited:false}));dayInfo.value={holiday:result.holiday,has_calendar:result.has_calendar,period_closed:result.period_closed,counts:result.counts,synced:result.synced};eventId.value=crypto.randomUUID()}
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
// Copies the device reading into one row (never silently over a hand-edited value).
function useMachine(row){const p=row.machine;if(!p?.status||row.docstatus!==0)return
 Object.assign(row,{shift:p.shift||row.shift,status:p.status,working_hours:p.working_hours,overtime_hours:p.suggested_overtime,in_time:p.in_time,out_time:p.out_time,late_entry:p.late_entry,early_exit:p.early_exit});edit(row)}
async function askMatching(){if(!dayInfo.value.counts.matching)return;confirmation.value={type:'matching',action:'submit',count:dayInfo.value.counts.matching};reason.value='';await nextTick();confirmDialog.value.showModal()}
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
 if(confirmation.value?.type==='matching'){
  try{const r=await call('lotus_farm.attendance_day.approve_matching',{company:company.value,date:date.value,shift:shift.value,client_event_id:eventId.value},true);confirmDialog.value.close();notice.value='Đã lưu và duyệt '+r.approved+' dòng khớp máy chấm.';await load()}
  catch(e){error.value=e.message}finally{saving.value=false}
  return}
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
  <WorkspaceListToolbar v-if="tab!=='setup'||(session?.companies?.length||0)>1" :searchable="false" :refreshable="tab!=='setup'" :busy="busy" :refresh-disabled="saving||dirty" @refresh="load">
   <template #filters>
   <LotusField v-if="(session?.companies?.length||0)>1" v-model="company" aria-label="Công ty" :options="(session?.companies||[]).map(c=>c.name)" :searchable="false" :empty-option="null" :disabled="busy||saving||dirty" @update:model-value="changeCompany"/>
   <LotusField v-if="['staff','crew'].includes(tab)" v-model="date" aria-label="Ngày công" type="date" :max="session?.today" :clearable="false" :disabled="busy||saving||dirty" @update:model-value="load"/>
   <LotusField v-else-if="tab==='month'" v-model="month" aria-label="Tháng" type="month" :max="session?.today?.slice(0,7)" :disabled="busy||saving" @update:model-value="load"/>
   <LotusField v-if="tab==='staff'" v-model="shift" aria-label="Ca làm việc" :options="catalog.shifts.map(s=>s.name)" :searchable="false" empty-option="Theo lịch ca" :disabled="busy||saving||dirty" @update:model-value="load"/>
   <LotusField v-if="['crew','month'].includes(tab)" v-model="farm" aria-label="Vườn" :options="catalog.farms.map(f=>({value:f.name,label:f.farm_name}))" :searchable="false" empty-option="Tất cả được phân quyền" :disabled="busy||saving" @update:model-value="load"/>
   <LotusField v-if="tab==='staff'" v-model="search" aria-label="Tìm nhân viên" class="stock-search" type="search" placeholder="Tên hoặc mã nhân viên" :disabled="busy||dirty" @keyup.enter="load"/>
   </template>
  </WorkspaceListToolbar>

  <template v-if="tab==='staff'">
   <p v-if="locked" class="tk-banner is-lock" role="status"><LotusIcon name="lock"/>Tháng {{date.slice(0,7)}} đã khóa công. Chỉ xem; HR Manager mở lại kỳ ở Hồ sơ nhân sự › Kỳ công & bảng lương.</p>
   <p v-else-if="dayInfo.holiday" class="tk-banner is-holiday" role="status"><LotusIcon name="flag"/>{{dayInfo.holiday.weekly_off?'Ngày nghỉ hằng tuần':'Ngày lễ: '+dayInfo.holiday.description}}. Giờ làm ngày này tính hệ số {{dayInfo.holiday.weekly_off?'200%':'300%'}}.</p>
   <p v-else-if="!dayInfo.has_calendar" class="tk-banner is-info" role="status"><LotusIcon name="calendar"/>Chưa có lịch nghỉ năm nay. Tạo ở tab Thiết lập › Lịch nghỉ năm để tính lễ và khóa kỳ.</p>
   <div class="tk-views" role="tablist" aria-label="Lọc theo trạng thái công"><UiButton v-for="[id,label] in views" :key="id" type="button" variant="ghost" role="tab" :aria-selected="view===id?'true':'false'" :class="['is-'+id,{active:view===id}]" @click="view=id">{{label}}<strong>{{counts[id]}}</strong></UiButton></div>
   <div class="attendance-toolbar tk-actions">
    <UiButton v-if="cap.Attendance?.submit&&!locked&&dayInfo.counts.matching" :disabled="saving||busy" @click="askMatching"><LotusIcon name="tick"/>Duyệt {{dayInfo.counts.matching}} dòng khớp máy</UiButton>
    <span v-if="dayInfo.synced" class="tk-hint tk-synced">Máy chấm: đã cập nhật {{dayInfo.synced.synced}} lượt mới{{dayInfo.synced.needs_review?', '+dayInfo.synced.needs_review+' lượt chưa ghép được':''}}</span>
    <span class="tk-actions__spacer"></span>
    <span v-if="selected.length" class="tk-actions__count">Đã chọn {{selected.length}}</span>
    <UiButton v-if="canEditStaff" :disabled="saving||busy||!dirty" @click="saveStaff">Lưu nháp</UiButton>
    <UiButton v-if="cap.Attendance?.submit&&!locked" variant="outline" :disabled="saving||!selected.length||dirty" :title="dirty?'Lưu nháp trước khi duyệt':''" @click="askStaff('submit')"><LotusIcon name="tick"/>Duyệt đã chọn</UiButton>
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
    <LotusField :model-value="allChecked" type="checkbox" label="Chọn tất cả nhân viên đang hiện" @update:model-value="toggleAll"/>
     <DataTable :fill="24" :rows="shown" :columns="attendanceColumns" row-key="employee" storage-key="timekeeping-attendance" :row-class="attendanceRowClass" />
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

 <ModalForm v-model="crewDialog.open" title="Phiếu công đội khoán" :busy="saving" :error="error" width="960px" :readonly="!(crew.docstatus!==1&&(crew.name?cap['Lotus Crew Attendance']?.write:cap['Lotus Crew Attendance']?.create))" submit-label="Lưu nháp" @submit="saveCrew">
  <FormGrid :columns="3">
   <LotusField v-model="crew.work_team" label="Đội khoán" :options="catalog.teams.map(team=>({value:team.name,label:team.team_name+' · '+team.lotus_foreman}))" required :disabled="!!crew.name||saving" @update:model-value="setTeam"/>
   <LotusField v-model="crew.posting_date" label="Ngày công" type="date" :max="session?.today" required :disabled="!!crew.name||saving"/>
   <LotusField v-model="crew.work_type" label="Công việc khoán" :options="(catalog.works||[]).map(w=>({value:w.name,label:w.work_name}))" :disabled="!!crew.name||crew.docstatus===1||saving" @update:model-value="setWork"/>
   <LotusField v-model="crew.headcount" label="Tổng người" type="number" min="0" step="1" required :disabled="crew.docstatus===1||saving"/>
   <LotusField v-model="crew.present" label="Có mặt" type="number" min="0" :max="crew.headcount" step="1" required :disabled="crew.docstatus===1||saving"/>
   <LotusField v-model="crew.workdays" label="Tổng công" type="number" min="0" :max="crew.present" step="0.25" required :disabled="crew.docstatus===1||saving"/>
   <LotusField v-model="crew.completed_qty" label="Khối lượng khoán" type="number" min="0" :disabled="crew.docstatus===1||saving"/>
   <LotusField v-model="crew.uom" label="Đơn vị khoán" :options="catalog.uoms.map(unit=>({value:unit.name,label:unitLabel(unit.name)}))" :required="crew.completed_qty>0" :disabled="crew.docstatus===1||saving||!!crew.work_type"/>
   <LotusField v-model="crew.unit_rate" :label="'Đơn giá khoán ('+currency+')'" type="money" :currency="currency" min="0" :hint="crew.work_type?'Niêm yết '+cash(crew.listed_piecework_rate)+' / '+unitLabel(crew.uom):''" :disabled="crew.docstatus===1||saving"/>
   <LotusField v-if="crew.work_type&&Number(crew.unit_rate)!==Number(crew.listed_piecework_rate)" v-model="crew.rate_override_reason" label="Lý do điều chỉnh đơn giá" type="textarea" wide required :disabled="crew.docstatus===1||saving"/>
   <LotusField v-model="crew.notes" label="Ghi chú" type="textarea" wide maxlength="2000" :disabled="crew.docstatus===1||saving"/>
  </FormGrid>
  <p class="tk-total">Giá trị khoán <strong>{{cash(Number(crew.completed_qty||0)*Number(crew.unit_rate||0))}}</strong></p>
  <template #secondary><UiButton v-if="crew.name&&crew.docstatus===0&&cap['Lotus Crew Attendance']?.delete" type="button" variant="destructive" :disabled="saving" @click="askCrew(crew,'delete')">Xóa nháp</UiButton><UiButton v-if="crew.name&&crew.docstatus===1&&cap['Lotus Crew Attendance']?.cancel" type="button" variant="outline" :disabled="saving" @click="askCrew(crew,'cancel')">Hủy đã duyệt</UiButton></template>
  <template #actions><UiButton v-if="crew.name&&crew.docstatus===0&&cap['Lotus Crew Attendance']?.submit" type="button" variant="outline" :disabled="saving" @click="askCrew(crew,'submit')">Duyệt phiếu</UiButton></template>
 </ModalForm>

 <ModalForm v-model="masterDialog.open" :title="masterTitle[masterKind]" :busy="saving" :error="error" width="760px" submit-label="Tạo mới" @submit="saveMaster">
  <FormGrid>
   <template v-if="masterKind==='employee'">
    <LotusField v-model="master.employee_name" label="Họ tên" required maxlength="140"/>
    <LotusField v-model="master.gender" label="Giới tính" :options="catalog.genders.map(g=>({value:g.name,label:genderLabel(g.name)}))" :searchable="false" empty-option="Chọn giới tính" required/>
    <LotusField v-model="master.date_of_birth" label="Ngày sinh" type="date" :max="session?.today" required/>
    <LotusField v-model="master.date_of_joining" label="Ngày vào làm" type="date" required/>
    <LotusField v-model="master.designation" label="Chức vụ" maxlength="140" placeholder="VD: Quản lý vườn, kế toán…"/>
    <LotusField v-model="master.department" label="Bộ phận" :options="catalog.departments.map(d=>({value:d.name,label:hrCatalogLabel(d.department_name)}))" placeholder="Chưa phân bộ phận"/>
   </template>
   <template v-else-if="masterKind==='team'">
    <LotusField v-model="master.farm" label="Vườn" :options="catalog.farms.map(f2=>({value:f2.name,label:f2.farm_name}))" :searchable="false" empty-option="Chọn vườn" required/>
    <LotusField v-model="master.code" label="Mã đội" required maxlength="140"/>
    <LotusField v-model="master.name" label="Tên đội" required maxlength="140"/>
    <LotusField v-model="master.foreman" label="Đầu câu / người phụ trách" required maxlength="140"/>
    <LotusField v-model="master.phone" label="Điện thoại" maxlength="40"/>
   </template>
   <template v-else>
    <LotusField v-model="master.code" label="Mã vườn" required maxlength="140" placeholder="FARM-222"/>
    <LotusField v-model="master.name" label="Tên vườn" required maxlength="140" placeholder="Vườn 222 Thuận Phú"/>
   </template>
  </FormGrid>
 </ModalForm>

 <TkCorrection v-model="correctionOpen" :company="company" :row="correcting" :shifts="catalog.shifts" @saved="corrected"/>
 <ModalForm v-model="confirmDialog.open" :title="confirmation?.type==='matching'?'Duyệt công khớp máy chấm':confirmation?.action==='submit'?'Duyệt công':confirmation?.action==='cancel'?'Hủy công đã duyệt':'Xóa công nháp'" :busy="saving" :error="error" width="560px" cancel-label="Quay lại" submit-label="Xác nhận" @submit="act">
  <p v-if="confirmation?.type==='staff'">{{confirmation.rows.length}} phiếu công đã chọn.</p>
  <p v-if="confirmation?.type==='matching'">Lưu và duyệt {{confirmation.count}} người có đủ giờ vào/ra trên máy, chưa bị chỉnh tay. Tăng ca lấy theo đề xuất (ra quá ca từ 30 phút, làm tròn 15 phút). Các dòng cần kiểm tra hoặc đã chỉnh tay giữ nguyên để bạn xem.</p>
  <LotusField v-if="confirmation?.action==='cancel'" v-model="reason" label="Lý do hủy" type="textarea" required maxlength="2000"/>
 </ModalForm>
</div></template>