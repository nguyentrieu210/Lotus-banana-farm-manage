<script setup>
import {onMounted,ref,watch} from 'vue'
import {call} from '../api'
import DataTable from './DataTable.vue'
const props=defineProps({farm:{type:String,default:''},zone:{type:String,default:'ALL'},block:{type:String,default:''}})
const result=ref(null),busy=ref(false),error=ref('')
let seq=0
async function load(){
 const id=++seq
 busy.value=true;error.value=''
 try {
  const value=await call('lotus_farm.vip126_zone_plan.status',{
   farm:props.farm||null,block:props.block||null,
   zone:props.zone==='ALL'?null:props.zone
  })
  if(id===seq)result.value=value
 }catch(e){if(id===seq)error.value=e.message||'Không tải được tiến độ dữ liệu khu'}
 finally{if(id===seq)busy.value=false}
}
watch(()=>[props.farm,props.zone,props.block],load)
onMounted(load)
const date=s=>s?.split('-').reverse().join('/')||'Chưa xác nhận'
const columns=[{field:'zone',headerName:'Khu',valueFormatter:p=>'Khu '+p.value},
 {field:'estimated_planting_date',headerName:'Ngày trồng ước tính',valueFormatter:p=>date(p.value)},
 {field:'estimated_sucker_selection_date',headerName:'Chọn chồi dự kiến',valueFormatter:p=>date(p.value)},
 {field:'estimated_flowering_date',headerName:'Trổ đợt đầu',valueFormatter:p=>date(p.value)},
 {field:'lots',headerName:'Lô'},
 {field:'saved_estimated_dates',headerName:'Đã lưu kế hoạch',valueFormatter:p=>p.data?.pending?'Chờ xác nhận':p.value+' / '+p.data?.lots+' lô'},
 {field:'actual_planting_lots',headerName:'Thực tế',valueFormatter:p=>p.value+' lô có ngày trồng thật'}]
</script>
<template>
 <section class="zone-plan" aria-label="Kế hoạch trồng theo khu">
  <header><div><strong>Tiến độ trồng VIP 126 theo khu</strong>
   <p>A trồng suy ngược 01/05/2026, B–C–D lần lượt sau 1 tháng. Ngày trồng bên dưới là <b>suy ngược</b>, không phải ngày ghi nhận thực tế.</p>
  </div><button type="button" @click="load" :disabled="busy">Làm mới</button></header>
  <p v-if="busy" class="zone-plan__note">Đang kiểm tra dữ liệu đã lưu…</p>
  <p v-if="error" role="alert">{{error}}</p>
  <div v-if="result?.available" class="zone-plan__scroll">
   <DataTable :rows="result.zones||[]" :columns="columns" row-key="zone" storage-key="zone-planting" empty="Chưa có khu phù hợp."/>
  </div>
  <p v-if="result?.available" class="zone-plan__note"><b>Phân bổ trổ:</b> 20% tháng đầu, 60% tháng tiếp, 20% tháng cuối. Trổ đầu sau trồng 6 tháng; chọn chồi 90 ngày sau trồng. Khu E chưa được xác nhận lịch trồng; trong chế độ chạy thử chỉ dùng mốc giả lập. Ngày chọn chồi hoặc trổ ghi nhận mới sẽ thay mốc dự phóng của đợt tương ứng.</p>
 </section>
</template>
<style scoped>
.zone-plan{display:grid;gap:10px;border:1px solid var(--lotus-border,var(--lotus-neutral-200));border-radius:10px;padding:13px;font-size:12px;color:var(--lotus-text,var(--lotus-neutral-800))}
.zone-plan header{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.zone-plan header p{font-size:11px;color:var(--lotus-muted,var(--lotus-neutral-600));margin:5px 0 0}
.zone-plan header button{border:1px solid var(--lotus-border,var(--lotus-neutral-200));border-radius:7px;background:var(--lotus-surface,#fff);color:inherit;padding:5px 9px}
.zone-plan__scroll{overflow-x:auto}
.zone-plan table{border-collapse:collapse;width:100%;min-width:620px;font-size:11px}
.zone-plan th{text-align:left;background:var(--lotus-table-header,var(--lotus-neutral-50));font-weight:700}
.zone-plan th,.zone-plan td{padding:9px 10px;border-bottom:1px solid var(--lotus-border,var(--lotus-neutral-200))}
.zone-plan__note{color:var(--lotus-muted,var(--lotus-neutral-600));margin:0;font-size:11px;line-height:1.6}
</style>