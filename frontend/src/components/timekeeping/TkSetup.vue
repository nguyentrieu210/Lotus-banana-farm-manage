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
import TkRoster from './TkRoster.vue'
import TkShiftForm from './TkShiftForm.vue'
// /lotus/cham-cong › Thiết lập: roster grid, shift types, holiday calendar, crews and masters.
// Shifts and rosters are changed by Administrator, System Manager and HR Manager (session.can_manage_shifts).
const props=defineProps({company:String,session:Object,catalog:{type:Object,default:()=>({})},cap:{type:Object,default:()=>({})},month:String})
const emit=defineEmits(['open-master','changed','notice','error'])
const api=(name,args={},write=false)=>call('lotus_farm.timekeeping.'+name,args,write)
const periodApi=(name,args={},write=false)=>call('lotus_farm.hr_period.'+name,args,write)
const sections=computed(()=>[
 {id:'schedule',label:'Lịch ca',icon:'calendar',allowed:props.session?.can_manage_shifts||props.cap.Attendance?.read},
 {id:'shifts',label:'Ca làm việc',icon:'clock',allowed:true},
 {id:'calendar',label:'Lịch nghỉ năm',icon:'flag',allowed:props.session?.is_hr_manager},
 {id:'crews',label:'Đội khoán & danh mục',icon:'people',allowed:true},
].filter(s=>s.allowed))
const section=ref('')
watch(sections,list=>{if(!list.some(s=>s.id===section.value))section.value=list[0]?.id||''},{immediate:true})
const busy=ref(false),saving=ref(false)
const roster=ref(null),calendarBaseline=ref('')
const fail=e=>emit('error',e.message||String(e))
const hhmm=v=>String(v||'').slice(0,5)

// Shift types ---------------------------------------------------------------------------------
const shiftRows=ref([]),shiftOpen=ref(false),editingShift=ref(null)
async function loadShifts(){shiftRows.value=(await call('lotus_farm.shift_admin.shifts')).rows}
function openShift(row=null){editingShift.value=row;shiftOpen.value=true}
function shiftSaved(row){emit('notice',(editingShift.value?'Đã lưu ca ':'Đã tạo ca ')+row.name+(row.open_drafts?'. '+row.open_drafts+' phiếu nháp theo ca này nên lấy lại công từ máy.':'.'));emit('changed');loadShifts()}
const overnight=r=>String(r.end_time)<=String(r.start_time)

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
 calendarBaseline.value=JSON.stringify([weeklyOff.value,holidays.value,year.value])
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

async function load(){if(!props.company)return;busy.value=true;try{if(section.value==='shifts')await loadShifts();if(section.value==='calendar')await loadCalendar()}catch(e){fail(e)}finally{busy.value=false}}
watch(()=>[section.value,props.company,props.month],load,{immediate:true})
defineExpose({load,hasChanges:()=>!!shiftOpen.value||!!roster.value?.hasChanges?.()||(!!info.value&&calendarBaseline.value!==JSON.stringify([weeklyOff.value,holidays.value,year.value])),discardChanges:()=>{shiftOpen.value=false;roster.value?.discardChanges?.();load()}})
</script>
<template>
<div class="tk-setup">
 <nav class="tk-subnav" aria-label="Thiết lập chấm công"><button v-for="s in sections" :key="s.id" type="button" :aria-current="section===s.id?'page':undefined" :class="{active:section===s.id}" @click="section=s.id"><LotusIcon :name="s.icon"/>{{s.label}}</button></nav>

 <TkRoster v-if="section==='schedule'" ref="roster" :company="company" :today="session?.today" :shifts="catalog.shifts||[]" :departments="catalog.departments||[]" @notice="emit('notice',$event)" @error="emit('error',$event)"/>

 <section v-if="section==='shifts'" class="tk-card" aria-label="Ca làm việc">
  <header class="tk-card__head"><h3>Ca làm việc</h3><span class="tk-actions__spacer"></span><UiButton v-if="session?.can_manage_shifts" variant="outline" @click="openShift()"><LotusIcon name="plus"/>Thêm ca</UiButton></header>
  <div v-if="shiftRows.length" class="tk-shiftlist">
   <article v-for="r in shiftRows" :key="r.name" class="tk-shiftcard" :style="{'--shift':r.color||'#4b5563'}">
    <header><b>{{r.name}}</b><span class="tk-shiftcard__time">{{hhmm(r.start_time)}} – {{hhmm(r.end_time)}}<small v-if="overnight(r)"> +1 ngày</small></span></header>
    <dl><div><dt>Cho phép muộn / về sớm</dt><dd>{{r.late_grace}}′ / {{r.early_grace}}′</dd></div><div><dt>Nhận lượt chấm</dt><dd>trước {{r.check_in_before}}′ · sau {{r.check_out_after}}′</dd></div>
     <div><dt>Nửa ngày / vắng nếu dưới</dt><dd>{{r.half_day_hours||'—'}} giờ / {{r.absent_hours||'—'}} giờ</dd></div><div><dt>Đang xếp</dt><dd>{{r.assigned}} lượt lịch</dd></div></dl>
    <UiButton v-if="session?.can_manage_shifts" variant="outline" size="sm" :aria-label="'Sửa '+r.name" @click="openShift(r)"><LotusIcon name="edit"/>Sửa ca</UiButton>
   </article>
  </div>
  <p v-else-if="!busy" class="tk-empty">Chưa có ca làm việc. Thêm 3 ca, ví dụ 06:00–14:00, 14:00–22:00, 22:00–06:00.</p>
  <p v-if="!session?.can_manage_shifts" class="tk-hint">Quản trị viên hoặc Quản lý nhân sự thêm và sửa ca.</p>
  <TkShiftForm v-model="shiftOpen" :company="company" :shift="editingShift" @saved="shiftSaved"/>
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
