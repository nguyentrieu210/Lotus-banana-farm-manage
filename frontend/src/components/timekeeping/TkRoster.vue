<script setup>
// Lịch ca: employees x days. Shift managers tap or drag cells, then pick a shift (or no shift); a weekly
// rotation fills Ca 1 → 2 → 3. Changes go through lotus_farm.shift_admin.set_roster, which splits HRMS
// Shift Assignments and refuses closed months. Everyone else sees the grid read-only.
import {computed,onBeforeUnmount,ref,watch} from 'vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import LotusIcon from '../LotusIcon.vue'
import {Button as UiButton} from '../ui/button'
import {Input as UiInput} from '../ui/input'
import UiSelect from '../ui/select/Select.vue'
import {FormField} from '../ui/form-field'
import {call} from '../../api'
import {addDays,changesFor,mondayOf,rotationChanges,shortShift} from '../../roster'

const props=defineProps({company:String,today:String,shifts:{type:Array,default:()=>[]},departments:{type:Array,default:()=>[]}})
const emit=defineEmits(['notice','error'])
const start=ref(mondayOf(props.today||new Date().toISOString().slice(0,10))),span=ref(7),search=ref(''),department=ref('')
const data=ref(null),busy=ref(false),saving=ref(false),picked=ref(new Set()),dragging=ref(false),result=ref(null)
const rotationOpen=ref(false),rotation=ref({start:'',weeks:4,pattern:[],stagger:true,scope:'selected'})
const canManage=computed(()=>!!data.value?.can_manage)
const colors=computed(()=>Object.fromEntries(props.shifts.map((s,i)=>[s.name,s.lotus_color||s.color||['#c43224','#d97706','#2563eb','#7c3aed'][i%4]])))
const ordered=computed(()=>[...props.shifts].sort((a,b)=>String(a.start_time).localeCompare(String(b.start_time))))
const weekday=d=>['CN','T2','T3','T4','T5','T6','T7'][new Date(d+'T00:00:00Z').getUTCDay()]
const dm=d=>d.slice(8,10)+'/'+d.slice(5,7)
const label=computed(()=>dm(start.value)+' – '+dm(addDays(start.value,span.value-1))+'/'+addDays(start.value,span.value-1).slice(0,4))
const key=(employee,date)=>employee+'|'+date
const pickedCells=computed(()=>[...picked.value].map(k=>{const [employee,date]=k.split('|');return {employee,date}}))
const pickedPeople=computed(()=>[...new Set(pickedCells.value.map(c=>c.employee))])
const hhmm=v=>String(v||'').slice(0,5)

let version=0
async function load(){if(!props.company)return;const id=++version;busy.value=true
 try{const r=await call('lotus_farm.shift_admin.roster',{company:props.company,start:start.value,days:span.value,search:search.value||undefined,department:department.value||undefined});if(id===version)data.value=r}
 catch(e){emit('error',e.message)}finally{if(id===version)busy.value=false}}
function move(days){start.value=addDays(start.value,days);picked.value=new Set()}
function closedDay(date){return data.value?.days.find(d=>d.date===date)?.closed}
function toggle(employee,date,on){if(!canManage.value||closedDay(date))return;const next=new Set(picked.value);const k=key(employee,date);(on??!next.has(k))?next.add(k):next.delete(k);picked.value=next}
function down(row,cell){dragging.value=true;toggle(row.employee,cell.date)}
function enter(row,cell){if(dragging.value)toggle(row.employee,cell.date,true)}
function up(){dragging.value=false}
function pickRow(row){if(!canManage.value)return;const next=new Set(picked.value);const all=row.cells.every(c=>closedDay(c.date)||next.has(key(row.employee,c.date)));for(const c of row.cells)if(!closedDay(c.date))all?next.delete(key(row.employee,c.date)):next.add(key(row.employee,c.date));picked.value=next}
function pickDay(date){if(!canManage.value||closedDay(date))return;const next=new Set(picked.value);const all=data.value.rows.every(r=>next.has(key(r.employee,date)));for(const r of data.value.rows)all?next.delete(key(r.employee,date)):next.add(key(r.employee,date));picked.value=next}
async function apply(changes,message){
 saving.value=true;result.value=null
 try{const r=await call('lotus_farm.shift_admin.set_roster',{company:props.company,changes},true);result.value=r;picked.value=new Set()
  if(r.applied.length)emit('notice',message+' ('+r.applied.length+' thay đổi'+(r.errors.length?', '+r.errors.length+' lỗi':'')+').')
  await load()}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
const assign=shift=>apply(changesFor(pickedCells.value,shift),shift?'Đã xếp '+shift:'Đã bỏ ca các ô đã chọn')
function openRotation(){const first3=ordered.value.slice(0,3).map(s=>s.name);rotation.value={start:start.value,weeks:4,pattern:first3,stagger:true,scope:pickedPeople.value.length?'selected':'shown'};rotationOpen.value=true}
const rotationPeople=computed(()=>rotation.value.scope==='selected'?pickedPeople.value:(data.value?.rows||[]).map(r=>r.employee))
const rotationPlan=computed(()=>rotationChanges(rotationPeople.value,mondayOf(rotation.value.start||start.value),Number(rotation.value.weeks)||0,rotation.value.pattern.filter(Boolean),rotation.value.stagger))
async function applyRotation(){await apply(rotationPlan.value,'Đã xếp xoay ca '+rotation.value.pattern.filter(Boolean).join(' → '));rotationOpen.value=false}
watch(()=>[props.company,start.value,span.value,department.value],load,{immediate:true})
let timer;watch(search,()=>{clearTimeout(timer);timer=setTimeout(load,300)})
window.addEventListener('pointerup',up)
onBeforeUnmount(()=>{window.removeEventListener('pointerup',up);clearTimeout(timer)})
defineExpose({load})
</script>

<template>
<section class="tk-card tk-rosterplan" aria-label="Lịch ca">
 <header class="tk-card__head"><h3>Lịch ca</h3>
  <div class="tk-weeknav" role="group" aria-label="Chọn tuần"><UiButton variant="outline" size="sm" aria-label="Tuần trước" :disabled="busy" @click="move(-span)">‹</UiButton><strong>{{label}}</strong><UiButton variant="outline" size="sm" aria-label="Tuần sau" :disabled="busy" @click="move(span)">›</UiButton><UiButton variant="ghost" size="sm" :disabled="busy" @click="start=mondayOf(today)">Tuần này</UiButton></div>
  <UiSelect v-model.number="span" aria-label="Số ngày hiển thị" class="tk-span"><option :value="7">1 tuần</option><option :value="14">2 tuần</option><option :value="28">4 tuần</option></UiSelect>
  <UiSelect v-model="department" aria-label="Lọc bộ phận"><option value="">Mọi bộ phận</option><option v-for="d in departments" :key="d.name" :value="d.name">{{d.department_name||d.name}}</option></UiSelect>
  <UiInput v-model="search" type="search" placeholder="Tìm nhân viên…" aria-label="Tìm nhân viên trong lịch ca" class="tk-search"/>
  <UiButton v-if="canManage" variant="outline" :disabled="saving||!ordered.length" @click="openRotation"><LotusIcon name="refresh"/>Xoay ca theo tuần</UiButton>
 </header>
 <p class="tk-legend tk-legend--shifts"><span v-for="s in ordered" :key="s.name" class="tk-shiftchip" :style="{'--shift':colors[s.name]}"><b>{{shortShift(s.name)}}</b>{{s.name}} {{hhmm(s.start_time)}}–{{hhmm(s.end_time)}}</span><span class="tk-shiftchip is-none"><b>—</b>Không xếp ca</span><span v-if="canManage" class="tk-hint">Bấm hoặc kéo để chọn ô · bấm tên để chọn cả hàng · bấm ngày để chọn cả cột.</span><span v-else class="tk-hint">Chỉ xem. Quản trị viên hoặc Quản lý nhân sự đổi ca.</span></p>
 <p v-if="result&&(result.errors.length||result.warnings.length)" class="tk-banner is-holiday" role="status"><LotusIcon name="flag"/><span><template v-for="e in result.errors" :key="'e'+e.employee">{{e.employee_name}}: {{e.message}}. </template><template v-for="w in result.warnings" :key="'w'+w.employee">{{w.message}} </template></span></p>
 <div class="tk-rostergrid" :class="{busy}" @pointerleave="up">
  <table v-if="data?.rows?.length"><thead><tr><th class="tk-rostergrid__who">Nhân viên</th><th v-for="d in data.days" :key="d.date" :class="{'is-off':d.off,'is-closed':d.closed}"><button type="button" :disabled="!canManage||d.closed" :aria-label="'Chọn cả ngày '+dm(d.date)" @click="pickDay(d.date)"><small>{{weekday(d.date)}}</small>{{dm(d.date)}}<LotusIcon v-if="d.closed" name="lock"/></button></th></tr></thead>
   <tbody><tr v-for="row in data.rows" :key="row.employee">
    <th class="tk-rostergrid__who" scope="row"><button type="button" :disabled="!canManage" @click="pickRow(row)"><strong>{{row.employee_name}}</strong><small>{{row.designation||row.department||row.employee}}</small></button></th>
    <td v-for="(c,i) in row.cells" :key="c.date" :class="{'is-off':data.days[i].off,'is-closed':data.days[i].closed}">
     <button type="button" class="tk-cell" :class="{picked:picked.has(key(row.employee,c.date)),empty:!c.shift}" :style="c.shift?{'--shift':colors[c.shift]||'#4b5563'}:null"
      :disabled="!canManage||data.days[i].closed" :aria-pressed="picked.has(key(row.employee,c.date))?'true':'false'"
      :aria-label="row.employee_name+' '+dm(c.date)+': '+(c.shift||'không xếp ca')+(c.worked?', đã có công duyệt':'')"
      :title="(c.shift||'Không xếp ca')+(c.worked?' · đã có công duyệt':'')" @pointerdown.prevent="down(row,c)" @pointerenter="enter(row,c)">{{c.shift?shortShift(c.shift):'—'}}<i v-if="c.worked" class="tk-cell__done" aria-hidden="true"></i></button>
    </td></tr></tbody></table>
  <p v-else-if="!busy" class="tk-empty">Không có nhân viên đang làm phù hợp bộ lọc.</p>
 </div>
 <div v-if="canManage&&picked.size" class="tk-rosterbar" role="toolbar" aria-label="Đổi ca các ô đã chọn">
  <span>Đã chọn <b>{{picked.size}}</b> ô · {{pickedPeople.length}} người</span>
  <UiButton v-for="s in ordered" :key="s.name" class="tk-rosterbar__shift" :style="{'--shift':colors[s.name]}" :disabled="saving" @click="assign(s.name)">{{s.name}}</UiButton>
  <UiButton variant="outline" :disabled="saving" @click="assign('')">Không xếp ca</UiButton>
  <UiButton variant="ghost" :disabled="saving" @click="picked=new Set()">Bỏ chọn</UiButton>
 </div>

 <WorkspaceModal v-model="rotationOpen" title="Xoay ca theo tuần" :busy="saving" width="620px">
  <form class="tk-shift-form" @submit.prevent="applyRotation">
   <FormField label="Áp dụng cho"><UiSelect v-model="rotation.scope" aria-label="Người áp dụng"><option value="selected" :disabled="!pickedPeople.length">{{pickedPeople.length}} người đã chọn ô</option><option value="shown">Tất cả {{data?.rows?.length||0}} người đang hiện</option></UiSelect></FormField>
   <div class="tk-pair"><FormField label="Từ tuần có ngày" v-slot="f"><UiInput v-bind="f" v-model="rotation.start" type="date"/></FormField><FormField label="Số tuần" v-slot="f"><UiInput v-bind="f" v-model.number="rotation.weeks" type="number" min="1" max="12"/></FormField></div>
   <FormField label="Thứ tự ca mỗi tuần"><div class="tk-pattern"><UiSelect v-for="(p,i) in rotation.pattern" :key="i" v-model="rotation.pattern[i]" :aria-label="'Tuần thứ '+(i+1)+' trong vòng'"><option v-for="s in ordered" :key="s.name" :value="s.name">{{s.name}}</option></UiSelect><UiButton v-if="rotation.pattern.length<4" type="button" variant="ghost" size="sm" @click="rotation.pattern.push(ordered[0]?.name)">＋</UiButton><UiButton v-if="rotation.pattern.length>1" type="button" variant="ghost" size="sm" @click="rotation.pattern.pop()">－</UiButton></div></FormField>
   <label class="tk-check"><input v-model="rotation.stagger" type="checkbox">So le giữa các người, để tuần nào ca nào cũng có người</label>
   <p class="tk-hint">Bắt đầu thứ Hai {{dm(mondayOf(rotation.start||start))}} · {{rotationPlan.length}} khối tuần sẽ được xếp. Ngày đã khóa công bị bỏ qua và báo lỗi.</p>
   <div class="hr-form-footer"><UiButton type="button" variant="outline" :disabled="saving" @click="rotationOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!rotationPlan.length">{{saving?'Đang xếp…':'Xếp '+rotationPlan.length+' tuần ca'}}</UiButton></div>
  </form>
 </WorkspaceModal>
</section>
</template>
