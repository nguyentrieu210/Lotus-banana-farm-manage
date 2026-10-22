<script setup>
import {computed} from 'vue'
import DataTable from '../DataTable.vue'
// Bảng công tháng dạng ma trận AG Grid, dữ liệu gốc và số công đã duyệt giữ nguyên.
const props=defineProps({data:{type:Object,default:null},kind:{type:String,default:'staff'},month:String,currency:{type:String,default:'VND'}})
const codes={Present:'X','Half Day':'½',Absent:'V','Work From Home':'TX','On Leave':'P'}
const tone={Present:'ok','Work From Home':'ok','Half Day':'half',Absent:'off','On Leave':'leave'}
const weekday=['CN','T2','T3','T4','T5','T6','T7']
const fmt=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:2})
const cash=n=>Number(n||0).toLocaleString('vi-VN',{style:'currency',currency:props.currency})
const days=computed(()=>{
 if(!props.data)return []
 const [y,m]=String(props.month||props.data.month).split('-').map(Number)
 const calendar=Object.keys(props.data.holidays||{}).length>0
 return Array.from({length:props.data.days},(_,i)=>{const d=i+1,dow=new Date(y,m-1,d).getDay(),flag=props.data.holidays?.[String(d)]
  return {d,label:weekday[dow],off:calendar?flag===1:dow===0,holiday:flag===0}})
})
function cell(row,day){
 const entries=row.days?.[String(day)]||[]
 if(!entries.length)return {text:'',cls:''}
 if(props.kind==='staff'){const e=entries[0];return {text:entries.map(r=>codes[r.status]||'?').join('/'),cls:'is-'+(tone[e.status]||'none')+(entries.some(r=>r.docstatus===0)?' is-draft':''),title:entries.map(r=>(r.docstatus===0?'Nháp · ':'')+r.status).join(', ')}}
 return {text:fmt(entries.reduce((n,r)=>n+Number(r.workdays||0),0)),cls:'is-ok'+(entries.some(r=>r.docstatus===0)?' is-draft':''),title:entries.length+' phiếu'}
}
const nameCol={field:props.kind==='staff'?'employee_name':'team_name',headerName:props.kind==='staff'?'Nhân viên':'Đội khoán',minWidth:200,pinned:'left',valueFormatter:p=>p.value+' · '+(props.kind==='staff'?p.data?.employee:p.data?.foreman||'')}
const columns=computed(()=>[
 {...nameCol,field:props.kind==='staff'?'employee_name':'team_name',headerName:props.kind==='staff'?'Nhân viên':'Đội khoán'},
 ...days.value.map(day=>({colId:'day_'+day.d,headerName:day.d+' '+day.label,minWidth:75,maxWidth:95,sortable:false,
  valueGetter:p=>cell(p.data,day.d).text,
  cellClass:p=>[cell(p.data,day.d).cls,day.off?'is-off':'',day.holiday?'is-holiday':''].filter(Boolean).join(' '),
  headerClass:[day.off?'is-off':'',day.holiday?'is-holiday':''].filter(Boolean).join(' '),
  tooltipValueGetter:p=>cell(p.data,day.d).title})),
 {field:'workdays',headerName:'Công',minWidth:85,valueFormatter:p=>fmt(p.value)},
 ...(props.kind==='staff'?[{field:'working_hours',headerName:'Giờ',valueFormatter:p=>fmt(p.value)},{field:'overtime_hours',headerName:'Tăng ca',valueFormatter:p=>fmt(p.value)}]:[{field:'amount',headerName:'Giá trị khoán',valueFormatter:p=>cash(p.value)}]),
 {field:'draft_count',headerName:'Nháp',valueFormatter:p=>p.value||'',cellClass:p=>p.value?'is-warn':''}
])
</script>
<template>
<div class="tk-sheet" role="region" :aria-label="kind==='staff'?'Bảng công nhân sự':'Bảng công đội khoán'" tabindex="0">
 <DataTable :rows="data?.rows||[]" :columns="columns" :row-key="kind==='staff'?'employee':'team'" :storage-key="'tk-month-'+kind" empty="Chưa có bảng công trong tháng."/>
 <p v-if="!data?.rows?.length" class="tk-empty">{{kind==='staff'?'Chưa có nhân viên trong tháng này.':'Chưa có phiếu công đội khoán trong tháng.'}}</p>
</div>
</template>