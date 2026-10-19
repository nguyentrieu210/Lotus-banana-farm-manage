<script setup>
import {computed} from 'vue'
// Month matrix for /lotus/cham-cong: one row per employee (or crew), one compact column per day,
// weekly off / public holidays shaded, drafts marked and excluded from the totals.
const props=defineProps({data:{type:Object,default:null},kind:{type:String,default:'staff'},month:String,currency:{type:String,default:'VND'}})
const codes={Present:'X','Half Day':'½',Absent:'V','Work From Home':'TX','On Leave':'P'}
const tone={Present:'ok','Work From Home':'ok','Half Day':'half',Absent:'off','On Leave':'leave'}
const weekday=['CN','T2','T3','T4','T5','T6','T7']
const fmt=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:2})
const cash=n=>Number(n||0).toLocaleString('vi-VN',{style:'currency',currency:props.currency})
const days=computed(()=>{
 if(!props.data)return []
 const [y,m]=String(props.month||props.data.month).split('-').map(Number)
 // Without a company calendar Sundays are still shaded so the sheet reads naturally.
 const calendar=Object.keys(props.data.holidays||{}).length>0
 return Array.from({length:props.data.days},(_,i)=>{const d=i+1,dow=new Date(y,m-1,d).getDay(),flag=props.data.holidays?.[String(d)]
  return {d,label:weekday[dow],off:calendar?flag===1:dow===0,holiday:flag===0}})
})
function cell(row,day){
 const entries=row.days[String(day)]||[]
 if(!entries.length)return {text:'',cls:''}
 if(props.kind==='staff'){const e=entries[0];return {text:entries.map(r=>codes[r.status]||'?').join('/'),cls:'is-'+(tone[e.status]||'none')+(entries.some(r=>r.docstatus===0)?' is-draft':''),title:entries.map(r=>(r.docstatus===0?'Nháp · ':'')+r.status).join(', ')}}
 return {text:fmt(entries.reduce((n,r)=>n+Number(r.workdays||0),0)),cls:'is-ok'+(entries.some(r=>r.docstatus===0)?' is-draft':''),title:entries.length+' phiếu'}
}
</script>
<template>
<div class="tk-sheet" role="region" :aria-label="kind==='staff'?'Bảng công nhân sự':'Bảng công đội khoán'" tabindex="0">
 <table>
  <thead><tr><th scope="col" class="tk-sheet__name">{{kind==='staff'?'Nhân viên':'Đội khoán'}}</th>
   <th v-for="day in days" :key="day.d" scope="col" :class="{'is-off':day.off,'is-holiday':day.holiday}"><span>{{day.d}}</span><small>{{day.label}}</small></th>
   <th scope="col" class="tk-sheet__total">Công</th>
   <template v-if="kind==='staff'"><th scope="col" class="tk-sheet__total">Giờ</th><th scope="col" class="tk-sheet__total">Tăng ca</th></template>
   <th v-else scope="col" class="tk-sheet__total">Giá trị khoán</th>
   <th scope="col" class="tk-sheet__total">Nháp</th></tr></thead>
  <tbody>
   <tr v-for="row in data?.rows||[]" :key="row.employee||row.team">
    <th scope="row" class="tk-sheet__name"><strong>{{kind==='staff'?row.employee_name:row.team_name}}</strong><small>{{kind==='staff'?row.employee:row.foreman}}</small></th>
    <td v-for="day in days" :key="day.d" :class="[cell(row,day.d).cls,{'is-off':day.off,'is-holiday':day.holiday}]" :title="cell(row,day.d).title">{{cell(row,day.d).text}}</td>
    <td class="tk-sheet__total"><strong>{{fmt(row.workdays)}}</strong></td>
    <template v-if="kind==='staff'"><td class="tk-sheet__total">{{fmt(row.working_hours)}}</td><td class="tk-sheet__total">{{fmt(row.overtime_hours)}}</td></template>
    <td v-else class="tk-sheet__total">{{cash(row.amount)}}</td>
    <td class="tk-sheet__total" :class="{'is-warn':row.draft_count}">{{row.draft_count||''}}</td>
   </tr>
  </tbody>
 </table>
 <p v-if="!data?.rows?.length" class="tk-empty">{{kind==='staff'?'Chưa có nhân viên trong tháng này.':'Chưa có phiếu công đội khoán trong tháng.'}}</p>
</div>
</template>
