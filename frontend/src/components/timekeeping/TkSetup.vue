<script setup>
import {computed,reactive,ref,watch} from 'vue'
import DataTable from '../DataTable.vue'
import LotusIcon from '../LotusIcon.vue'
import {Button as UiButton} from '../ui/button'
import {Input as UiInput} from '../ui/input'
import UiSelect from '../ui/select/Select.vue'
import {DatePicker} from '../ui/date-picker'
import {FormField} from '../ui/form-field'
import {call} from '../../api'
import {formatDate} from '../../format'
// /lotus/cham-cong › Thiết lập: shift schedule, shift types, holiday calendar, crews and masters.
const props=defineProps({company:String,session:Object,catalog:{type:Object,default:()=>({})},cap:{type:Object,default:()=>({})},month:String})
const emit=defineEmits(['open-master','changed','notice','error'])
const api=(name,args={},write=false)=>call('lotus_farm.timekeeping.'+name,args,write)
const periodApi=(name,args={},write=false)=>call('lotus_farm.hr_period.'+name,args,write)
const sections=computed(()=>[
 {id:'schedule',label:'Lịch ca',icon:'calendar',allowed:props.cap.Attendance?.create},
 {id:'shifts',label:'Ca làm việc',icon:'clock',allowed:true},
 {id:'calendar',label:'Lịch nghỉ năm',icon:'flag',allowed:props.session?.is_hr_manager},
 {id:'crews',label:'Đội khoán & danh mục',icon:'people',allowed:true},
].filter(s=>s.allowed))
const section=ref('')
watch(sections,list=>{if(!list.some(s=>s.id===section.value))section.value=list[0]?.id||''},{immediate:true})
const busy=ref(false),saving=ref(false)
const fail=e=>emit('error',e.message||String(e))
const hhmm=v=>String(v||'').slice(0,5)

// Shift schedule ------------------------------------------------------------------------------
const schedule=ref([]),plan=reactive({shift:'',start_date:'',end_date:'',employees:[]}),who=ref('')
const people=computed(()=>(props.catalog.employees||[]).filter(e=>!who.value||(e.employee_name+' '+e.name).toLocaleLowerCase('vi-VN').includes(who.value.toLocaleLowerCase('vi-VN'))))
const allShown=computed(()=>people.value.length>0&&people.value.every(e=>plan.employees.includes(e.name)))
function toggleAll(){const names=people.value.map(e=>e.name);plan.employees=allShown.value?plan.employees.filter(n=>!names.includes(n)):[...new Set([...plan.employees,...names])]}
async function loadSchedule(){if(!props.cap.Attendance?.create)return;schedule.value=(await api('shift_schedule',{company:props.company,month:props.month})).rows}
async function saveSchedule(){
 if(!plan.shift||!plan.start_date||!plan.employees.length)return emit('error','Chọn ca, ngày bắt đầu và ít nhất một nhân viên.')
 saving.value=true
 try{const r=await api('assign_shift',{company:props.company,shift:plan.shift,employees:plan.employees,start_date:plan.start_date,end_date:plan.end_date||null},true);emit('notice','Đã xếp '+plan.shift+' cho '+r.names.length+' nhân viên.');plan.employees=[];await loadSchedule()}
 catch(e){fail(e)}finally{saving.value=false}
}
const scheduleColumns=[{field:'employee_name',headerName:'Nhân viên',minWidth:200},{field:'shift_type',headerName:'Ca',minWidth:140},{field:'start_date',headerName:'Từ ngày',minWidth:120,valueFormatter:p=>formatDate(p.value)},{field:'end_date',headerName:'Đến ngày',minWidth:120,valueFormatter:p=>p.value?formatDate(p.value):'Không thời hạn'}]

// Shift types ---------------------------------------------------------------------------------
const shiftColumns=[{field:'name',headerName:'Ca',minWidth:160},{field:'start_time',headerName:'Giờ vào',minWidth:90,valueFormatter:p=>hhmm(p.value)},{field:'end_time',headerName:'Giờ ra',minWidth:90,valueFormatter:p=>hhmm(p.value)},
 {field:'late_entry_grace_period',headerName:'Cho phép muộn',minWidth:120,valueFormatter:p=>(p.value||0)+' phút'},{field:'early_exit_grace_period',headerName:'Cho phép về sớm',minWidth:130,valueFormatter:p=>(p.value||0)+' phút'},
 {field:'working_hours_threshold_for_half_day',headerName:'Dưới giờ này = nửa ngày',minWidth:170,valueFormatter:p=>p.value?p.value+' giờ':'—'},{field:'working_hours_threshold_for_absent',headerName:'Dưới giờ này = vắng',minWidth:150,valueFormatter:p=>p.value?p.value+' giờ':'—'}]

// Holiday calendar ----------------------------------------------------------------------------
const year=ref(Number((props.session?.today||new Date().toISOString()).slice(0,4)))
const info=ref(null),weeklyOff=ref(['Sunday']),holidays=ref([])
const weekdays=[['Monday','T2'],['Tuesday','T3'],['Wednesday','T4'],['Thursday','T5'],['Friday','T6'],['Saturday','T7'],['Sunday','CN']]
const years=computed(()=>{const y=Number((props.session?.today||'2026').slice(0,4));return [y-1,y,y+1]})
async function loadCalendar(){
 if(!props.session?.is_hr_manager)return
 const result=await periodApi('calendar_info',{company:props.company,year:year.value});info.value=result
 // The saved list is rebuilt from these inputs, so existing holidays come back as editable rows.
 const weekly=[...new Set(result.holidays.filter(h=>h.weekly_off).map(h=>result.weekdays[(new Date(h.date+'T00:00:00').getDay()+6)%7]))]
 weeklyOff.value=weekly.length?weekly:['Sunday']
 holidays.value=result.holidays.filter(h=>!h.weekly_off).map(h=>({date:h.date,description:h.description}))
}
function toggleDay(day){weeklyOff.value=weeklyOff.value.includes(day)?weeklyOff.value.filter(d=>d!==day):[...weeklyOff.value,day]}
async function saveCalendar(){
 saving.value=true
 try{const r=await periodApi('setup_calendar',{company:props.company,year:year.value,weekly_off:weeklyOff.value,extra:holidays.value.filter(h=>h.date)},true);emit('notice','Đã lưu lịch nghỉ '+year.value+': '+r.days+' ngày nghỉ.');emit('changed');await loadCalendar()}
 catch(e){fail(e)}finally{saving.value=false}
}

// Crews and masters ---------------------------------------------------------------------------
const farmName=name=>(props.catalog.farms||[]).find(f=>f.name===name)?.farm_name||name
const teamColumns=[{field:'team_name',headerName:'Đội khoán',minWidth:190},{field:'lotus_foreman',headerName:'Đầu câu',minWidth:150},{field:'lotus_foreman_phone',headerName:'Điện thoại',minWidth:140},{field:'farm',headerName:'Vườn',minWidth:160,valueFormatter:p=>farmName(p.value)}]

async function load(){if(!props.company)return;busy.value=true;try{if(section.value==='schedule')await loadSchedule();if(section.value==='calendar')await loadCalendar()}catch(e){fail(e)}finally{busy.value=false}}
watch(()=>[section.value,props.company,props.month],load,{immediate:true})
defineExpose({load})
</script>
<template>
<div class="tk-setup">
 <nav class="tk-subnav" aria-label="Thiết lập chấm công"><button v-for="s in sections" :key="s.id" type="button" :aria-current="section===s.id?'page':undefined" :class="{active:section===s.id}" @click="section=s.id"><LotusIcon :name="s.icon"/>{{s.label}}</button></nav>

 <section v-if="section==='schedule'" class="tk-card" aria-label="Lịch ca">
  <header class="tk-card__head"><h3>Xếp ca theo khoảng ngày</h3></header>
  <div class="tk-form-row">
   <FormField label="Ca" required v-slot="f"><UiSelect v-bind="f" v-model="plan.shift" :disabled="saving"><option value="">Chọn ca</option><option v-for="s in catalog.shifts" :key="s.name" :value="s.name">{{s.name}} · {{hhmm(s.start_time)}}–{{hhmm(s.end_time)}}</option></UiSelect></FormField>
   <FormField label="Từ ngày" required v-slot="f"><DatePicker v-bind="f" v-model="plan.start_date" :disabled="saving" aria-label="Xếp ca từ ngày"/></FormField>
   <FormField label="Đến ngày" hint="Bỏ trống nếu không thời hạn" v-slot="f"><DatePicker v-bind="f" v-model="plan.end_date" :min="plan.start_date" :disabled="saving" aria-label="Xếp ca đến ngày"/></FormField>
  </div>
  <div class="tk-picker">
   <div class="tk-picker__bar"><UiInput v-model="who" type="search" placeholder="Tìm nhân viên…" aria-label="Tìm nhân viên để xếp ca"/><UiButton variant="outline" size="sm" :disabled="!people.length" @click="toggleAll">{{allShown?'Bỏ chọn':'Chọn tất cả'}}</UiButton><span>Đã chọn <strong>{{plan.employees.length}}</strong></span></div>
   <div class="tk-picker__list"><label v-for="e in people" :key="e.name" :class="{checked:plan.employees.includes(e.name)}"><input v-model="plan.employees" type="checkbox" :value="e.name" :disabled="saving"><span>{{e.employee_name}}</span><small>{{e.name}}</small></label><p v-if="!people.length" class="tk-empty">Không có nhân viên phù hợp.</p></div>
  </div>
  <footer class="tk-card__foot"><UiButton :disabled="saving||busy||!plan.shift||!plan.start_date||!plan.employees.length" @click="saveSchedule">{{saving?'Đang xếp ca…':'Xếp ca cho '+plan.employees.length+' người'}}</UiButton></footer>
  <h4 class="tk-card__sub">Lịch ca trong tháng</h4>
  <DataTable :rows="schedule" :columns="scheduleColumns" :loading="busy" empty="Chưa xếp ca trong tháng này."/>
 </section>

 <section v-if="section==='shifts'" class="tk-card" aria-label="Ca làm việc">
  <header class="tk-card__head"><h3>Ca làm việc</h3><UiButton v-if="cap.Attendance?.create" variant="outline" @click="emit('open-master','shift')"><LotusIcon name="plus"/>Thêm ca</UiButton></header>
  <DataTable :rows="catalog.shifts||[]" :columns="shiftColumns" empty="Chưa có ca làm việc. Thêm 3 ca, ví dụ 06:00–14:00, 14:00–22:00, 22:00–06:00."/>
 </section>

 <section v-if="section==='calendar'" class="tk-card" aria-label="Lịch nghỉ năm">
  <header class="tk-card__head"><h3>Lịch nghỉ năm</h3><UiSelect v-model.number="year" class="tk-year" aria-label="Năm lịch nghỉ" :disabled="busy||saving" @change="loadCalendar"><option v-for="y in years" :key="y" :value="y">Năm {{y}}</option></UiSelect><span class="tk-pill" :class="info?.name?(info.is_default?'is-ok':'is-warn'):'is-muted'">{{info?.name?(info.is_default?'Đang áp dụng':'Đã tạo, chưa áp dụng'):'Chưa tạo'}}</span></header>
  <FormField label="Nghỉ hằng tuần"><div class="tk-chips" role="group" aria-label="Nghỉ hằng tuần"><button v-for="[day,short] in weekdays" :key="day" type="button" :aria-pressed="weeklyOff.includes(day)?'true':'false'" :class="{on:weeklyOff.includes(day)}" :disabled="saving" @click="toggleDay(day)">{{short}}</button></div></FormField>
  <div class="tk-holidays"><div class="tk-holidays__head"><span>Ngày lễ</span><span>Tên ngày lễ</span><span></span></div>
   <div v-for="(h,i) in holidays" :key="i" class="tk-holidays__row"><DatePicker v-model="h.date" :aria-label="'Ngày lễ '+(i+1)" :disabled="saving"/><UiInput v-model="h.description" maxlength="140" placeholder="VD: Tết Nguyên đán" :aria-label="'Tên ngày lễ '+(i+1)" :disabled="saving"/><UiButton variant="ghost" size="sm" :aria-label="'Bỏ ngày lễ '+(i+1)" :disabled="saving" @click="holidays.splice(i,1)"><LotusIcon name="trash"/></UiButton></div>
   <p v-if="!holidays.length" class="tk-empty">1/1, 30/4, 1/5 và 2/9 được thêm tự động khi lưu.</p></div>
  <footer class="tk-card__foot"><UiButton variant="outline" :disabled="saving" @click="holidays.push({date:'',description:''})"><LotusIcon name="plus"/>Thêm ngày lễ</UiButton><span class="tk-hint">Tết, Giỗ tổ và ngày liền kề 2/9 đổi theo năm: thêm tay.</span><UiButton :disabled="saving||busy" @click="saveCalendar">{{info?.name?'Cập nhật lịch':'Tạo lịch năm '+year}}</UiButton></footer>
 </section>

 <section v-if="section==='crews'" class="tk-card" aria-label="Đội khoán và danh mục">
  <header class="tk-card__head"><h3>Đội khoán</h3><UiButton v-if="cap['Work Team']?.create" variant="outline" @click="emit('open-master','team')"><LotusIcon name="plus"/>Đội khoán / đầu câu</UiButton><UiButton v-if="cap.Employee?.create" variant="outline" @click="emit('open-master','employee')"><LotusIcon name="plus"/>Nhân sự chính thức</UiButton><UiButton v-if="session?.can_create_farm" variant="outline" @click="emit('open-master','farm')"><LotusIcon name="plus"/>Vườn</UiButton></header>
  <DataTable :rows="catalog.teams||[]" :columns="teamColumns" empty="Chưa có đội khoán được phân quyền."/>
  <footer class="tk-card__links"><a href="/lotus/nhan-su">Hồ sơ nhân sự, tuyển dụng & tiếp nhận ↗</a><a href="/desk/hr-setup">Quản trị HRMS ↗</a></footer>
 </section>
</div>
</template>
