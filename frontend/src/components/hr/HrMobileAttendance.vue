<script setup>
// Nhân sự PWA › Chấm công: today's board from the time clock, grouped by shift. One tap approves every row
// the clock fully explains; tapping a person edits that day, corrects an approved day, or changes the
// person's shift (shift managers). Same endpoints as /lotus/cham-cong (lotus_farm.attendance_day, shift_admin).
import {computed,onMounted,reactive,ref,watch} from 'vue'
import LotusMobileButton from '../LotusMobileButton.vue'
import LotusMobileInput from '../LotusMobileInput.vue'
import LotusMobileSelect from '../LotusMobileSelect.vue'
import LotusMobileFeedback from '../LotusMobileFeedback.vue'
import LotusMobileDialog from '../LotusMobileDialog.vue'
import {call} from '../../api'
import '../../hr-mobile-attendance.css'
import {applyPresence,presencePayload} from '../../attendance-presence'

const props=defineProps({company:String,today:String})
const emit=defineEmits(['notice','error'])
const date=ref(props.today),filter=ref('all'),data=ref(null),busy=ref(false),saving=ref(false),boot=ref(null),shifts=ref([])
const sheet=ref(null),person=ref(null),form=reactive({}),mode=ref('day')
const STATUS=[{value:'Present',label:'Có mặt'},{value:'Half Day',label:'Nửa ngày'},{value:'Absent',label:'Vắng'},{value:'Work From Home',label:'Làm từ xa'}]
const statusLabel=v=>STATUS.find(s=>s.value===v)?.label||(v==='On Leave'?'Nghỉ phép':'Chưa chấm')
const hhmm=v=>v?String(v).slice(11,16):''
const plus=(v)=>v&&String(v).slice(0,10)>date.value?' (+1)':''
const canManage=computed(()=>!!boot.value?.can_manage_shifts)
const canSubmit=computed(()=>!!boot.value?.capabilities?.Attendance?.submit)
const canEdit=computed(()=>!!(boot.value?.capabilities?.Attendance?.create||boot.value?.capabilities?.Attendance?.write))
const presenceOptions=[{value:1,label:'Có mặt'},{value:0,label:'Vắng'}]
const allowanceOptions=[{value:0,label:'Không'},{value:1,label:'Có phụ cấp'}]
const locked=computed(()=>!!data.value?.period_closed)
const kind=r=>r.legacy_conflict?'review':r.docstatus===1?'approved':r.machine?.needs_review?'review':r.matches?'matching':r.morning_present||r.afternoon_present?'partial':r.machine&&r.machine.status==='Absent'?'absent':'none'
const KINDS={matching:'Đủ công',partial:'Nửa công',review:'Cần kiểm tra',approved:'Đã duyệt',present:'Có lượt chấm',absent:'Chưa chấm',none:'Chưa có dữ liệu'}
const rows=computed(()=>(data.value?.rows||[]).filter(r=>filter.value==='all'||kind(r)===filter.value))
const counts=computed(()=>{const c={};for(const r of data.value?.rows||[])c[kind(r)]=(c[kind(r)]||0)+1;return c})
const late=computed(()=>(data.value?.rows||[]).filter(r=>r.machine?.late_entry).length)
async function load(){if(!props.company||!date.value)return;busy.value=true
 try{if(!boot.value){boot.value=await call('lotus_farm.timekeeping.bootstrap');shifts.value=(await call('lotus_farm.timekeeping.catalogue',{company:props.company})).shifts||[]}
  data.value=await call('lotus_farm.attendance_day.board',{company:props.company,date:date.value,daily_presence:1})}
 catch(e){emit('error',e.message)}finally{busy.value=false}}
async function approveMatching(){
 saving.value=true
 try{const reviewed_rows=(data.value?.rows||[]).filter(r=>r.matches).map(r=>({row_key:r.row_key,review_hash:r.review_hash}));const r=await call('lotus_farm.attendance_day.approve_matching',{company:props.company,date:date.value,daily_presence:1,client_event_id:crypto.randomUUID(),reviewed_rows},true);emit('notice','Đã duyệt '+r.approved+' dòng công khớp máy chấm.');await load()}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
function open(r){person.value=r;mode.value=r.docstatus===1?'correct':'day';const m=r.machine||{}
 Object.assign(form,{status:r.status||m.status||'Present',working_hours:Number(r.name?r.working_hours:m.working_hours||0),overtime_hours:Number(r.name?r.overtime_hours||0:m.suggested_overtime||0),
  note:r.note||'',reason:'',allowance:Number(r.allowance)?1:0,shift:r.shift||m.shift||'',from:date.value,to:date.value,in_time:r.in_time||m.in_time||null,out_time:r.out_time||m.out_time||null,late_entry:r.late_entry??m.late_entry??0,early_exit:r.early_exit??m.early_exit??0,...presencePayload(r)})
 sheet.value.showModal()}
async function saveDay(){const r=person.value;saving.value=true
 try{
  if(mode.value==='day'){await call('lotus_farm.timekeeping.save_staff',{company:props.company,date:date.value,daily_presence:1,client_event_id:crypto.randomUUID(),rows:[{employee:r.employee,name:r.name,modified:r.modified,...presencePayload(form),status:form.status,
    working_hours:form.status==='Absent'?0:form.working_hours,overtime_hours:form.status==='Absent'?0:form.overtime_hours,allowance:Number(form.allowance)?1:0,in_time:form.in_time,out_time:form.out_time,late_entry:form.late_entry?1:0,early_exit:form.early_exit?1:0,shift:form.shift||null,note:form.note}]},true);emit('notice','Đã lưu nháp công của '+r.employee_name+'.')}
  if(mode.value==='correct'){await call('lotus_farm.shift_admin.correct_attendance',{company:props.company,name:r.name,modified:r.modified,reason:form.reason,values:{daily_presence:1,...presencePayload(form),status:form.status,working_hours:form.working_hours,overtime_hours:form.overtime_hours,note:form.note}},true);emit('notice','Đã sửa công đã duyệt của '+r.employee_name+'.')}
  if(mode.value==='shift'){const res=await call('lotus_farm.shift_admin.set_roster',{company:props.company,changes:[{employee:r.employee,from:form.from,to:form.to||null,shift:form.shift}]},true)
   if(res.errors.length)throw Error(res.errors[0].message);emit('notice','Đã đổi ca cho '+r.employee_name+(res.warnings.length?'. '+res.warnings[0].message:'.'))}
  sheet.value.close();await load()}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
// Phụ cấp công việc on an approved day is written at once while the month is open (no correction needed).
async function toggleApprovedAllowance(){const r=person.value;saving.value=true
 try{await call('lotus_farm.attendance_day.set_allowance',{company:props.company,date:date.value,rows:[{employee:r.employee,name:r.name,modified:r.modified}],allowance:Number(r.allowance)?0:1},true)
  emit('notice',(Number(r.allowance)?'Đã bỏ':'Đã tick')+' phụ cấp của '+r.employee_name+'.');sheet.value.close();await load()}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
function shiftDay(days){const d=new Date(date.value+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+days);const v=d.toISOString().slice(0,10);if(v<=props.today)date.value=v}
watch(date,load)
// The app session (and so today) may arrive after this screen mounts.
watch(()=>props.today,value=>{if(value&&!date.value)date.value=value})
watch(()=>props.company,()=>{boot.value=null;load()})
onMounted(load)
defineExpose({load})
</script>

<template>
<section class="hr-att">
 <div class="hr-att__date"><LotusMobileButton plain aria-label="Ngày trước" @click="shiftDay(-1)">‹</LotusMobileButton><LotusMobileInput v-model="date" type="date" :max="today" aria-label="Ngày công"/><LotusMobileButton plain aria-label="Ngày sau" :disabled="date>=today" @click="shiftDay(1)">›</LotusMobileButton></div>
 <LotusMobileFeedback v-if="locked" kind="warning">Tháng này đã khóa công, chỉ xem.</LotusMobileFeedback>
 <LotusMobileFeedback v-if="data?.synced?.synced" kind="info">Máy chấm vừa gửi thêm {{data.synced.synced}} lượt.</LotusMobileFeedback>
 <div class="hr-att__stats">
  <button type="button" :class="{on:filter==='matching'}" @click="filter=filter==='matching'?'all':'matching'"><strong>{{counts.matching||0}}</strong><span>Khớp máy</span></button>
  <button type="button" :class="{on:filter==='partial'}" @click="filter=filter==='partial'?'all':'partial'"><strong>{{counts.partial||0}}</strong><span>Nửa công</span></button>
  <button type="button" :class="{on:filter==='absent'}" @click="filter=filter==='absent'?'all':'absent'"><strong>{{counts.absent||0}}</strong><span>Chưa vào</span></button>
  <button type="button" :class="{on:filter==='approved'}" @click="filter=filter==='approved'?'all':'approved'"><strong>{{counts.approved||0}}</strong><span>Đã duyệt</span></button>
 </div>
 <p v-if="late" class="hr-att__hint">{{late}} người đi muộn hôm nay.</p>
 <LotusMobileButton v-if="canSubmit&&!locked&&data?.counts?.matching" variant="primary" block :loading="saving" @click="approveMatching">Duyệt {{data.counts.matching}} dòng công khớp máy</LotusMobileButton>
 <LotusMobileFeedback v-if="busy" kind="loading">Đang tải công…</LotusMobileFeedback>
 <section class="hr-att__group">
  <button v-for="r in rows" :key="r.row_key||r.employee" type="button" class="hr-att__row" :class="'is-'+kind(r)" @click="open(r)">
   <span class="hr-att__who"><strong>{{r.employee_name}}</strong><small>{{KINDS[kind(r)]}}<template v-if="r.name"> · {{statusLabel(r.status)}}</template><template v-if="Number(r.allowance)"> · Có phụ cấp</template></small></span>
   <span class="hr-att__clock"><b>Sáng {{r.morning_time?hhmm(r.morning_time):r.morning_present?'Có':'—'}} · Chiều {{r.afternoon_time?hhmm(r.afternoon_time):r.afternoon_present?'Có':'—'}}</b><small>{{r.working_hours/8}} công</small>
    <small v-if="r.machine?.needs_review">{{r.machine.reason}}</small></span>
  </button>
 </section>
 <p v-if="data&&!rows.length&&!busy" class="mobile-empty">Không có ai ở mục này.</p>

 <LotusMobileDialog ref="sheet" @cancel="sheet.close()">
  <form v-if="person" class="hr-att__sheet" @submit.prevent="saveDay">
   <h2>{{person.employee_name}}</h2>
   <p class="hr-att__hint">Sáng {{person.morning_time?hhmm(person.morning_time):'—'}} · Chiều {{person.afternoon_time?hhmm(person.afternoon_time):'—'}} · {{form.working_hours/8}} công</p>
   <div class="hr-att__modes" role="tablist">
    <button v-if="person.docstatus!==1&&!locked" type="button" role="tab" :aria-selected="mode==='day'?'true':'false'" :class="{on:mode==='day'}" @click="mode='day'">Công ngày</button>
    <button v-if="person.docstatus===1&&canManage&&!locked" type="button" role="tab" :aria-selected="mode==='correct'?'true':'false'" :class="{on:mode==='correct'}" @click="mode='correct'">Sửa công</button>
   </div>
   <template v-if="mode!=='shift'">
    <LotusMobileSelect v-model="form.morning_present" label="Sáng" :options="presenceOptions" :disabled="locked||!canEdit||person.legacy_conflict||person.status==='On Leave'||person.docstatus===1&&!canManage" @update:model-value="applyPresence(form)"/>
    <LotusMobileSelect v-model="form.afternoon_present" label="Chiều" :options="presenceOptions" :disabled="locked||!canEdit||person.legacy_conflict||person.status==='On Leave'||person.docstatus===1&&!canManage" @update:model-value="applyPresence(form)"/>
    <LotusMobileSelect v-if="mode==='day'" v-model="form.allowance" label="Phụ cấp công việc" :options="allowanceOptions" :disabled="locked||!canEdit||person.legacy_conflict||person.status==='On Leave'||!form.working_hours" hint="Cả ngày đủ mức, một buổi nửa mức"/>
    <LotusMobileButton v-if="mode==='correct'&&canEdit&&!locked&&(Number(person.allowance)||person.working_hours>0)" block :loading="saving" @click="toggleApprovedAllowance">{{Number(person.allowance)?'Bỏ phụ cấp công việc':'Tick phụ cấp công việc'}}</LotusMobileButton>
    <LotusMobileInput v-model="form.note" label="Ghi chú" maxlength="2000"/>
    <LotusMobileInput v-if="mode==='correct'" v-model="form.reason" label="Lý do sửa" required minlength="5" placeholder="VD: tổ trưởng xác nhận có mặt"/>
   </template>
   <template v-else>
    <LotusMobileSelect v-model="form.shift" label="Ca mới" :options="[{value:'',label:'Không xếp ca'},...shifts.map(s=>({value:s.name,label:s.name+' · '+String(s.start_time).slice(0,5)+'–'+String(s.end_time).slice(0,5)}))]"/>
    <LotusMobileInput v-model="form.from" label="Từ ngày" type="date" required/>
    <LotusMobileInput v-model="form.to" label="Đến ngày" type="date" :min="form.from" hint="Bỏ trống nếu áp dụng lâu dài"/>
   </template>
   <div class="hr-att__actions"><LotusMobileButton plain :disabled="saving" @click="sheet.close()">Đóng</LotusMobileButton>
    <LotusMobileButton v-if="!locked&&!person.legacy_conflict&&person.status!=='On Leave'&&((mode==='day'&&canEdit)||(mode==='correct'&&canManage))" variant="primary" type="submit" :loading="saving" :disabled="mode==='correct'&&String(form.reason||'').trim().length<5">{{mode==='correct'?'Lưu bản sửa':'Lưu nháp'}}</LotusMobileButton></div>
  </form>
 </LotusMobileDialog>
</section>
</template>
