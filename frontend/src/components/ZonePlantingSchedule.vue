<script setup>
import {onMounted,ref,watch} from 'vue'
import {call} from '../api'
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
</script>
<template>
 <section class="zone-plan" aria-label="Kế hoạch trồng theo khu">
  <header><div><strong>Tiến độ trồng VIP 126 theo khu</strong>
   <p>A trồng trước, B–C–D lần lượt sau 1 tháng. Ngày trồng bên dưới là <b>suy ngược</b>, không phải ngày ghi nhận thực tế.</p>
  </div><button type="button" @click="load" :disabled="busy">Làm mới</button></header>
  <p v-if="busy" class="zone-plan__note">Đang kiểm tra dữ liệu đã lưu…</p>
  <p v-if="error" role="alert">{{error}}</p>
  <div v-if="result?.available" class="zone-plan__scroll">
   <table><thead><tr><th>Khu</th><th>Ngày trồng ước tính</th><th>Trổ dự kiến</th><th>Lô</th><th>Đã lưu kế hoạch</th><th>Thực tế</th></tr></thead>
    <tbody>
     <tr v-for="z in result.zones" :key="z.zone">
      <td><b>Khu {{z.zone}}</b></td><td>{{date(z.estimated_planting_date)}}</td>
      <td>{{date(z.estimated_flowering_date)}}</td><td>{{z.lots}}</td>
      <td>{{z.pending?'Chờ xác nhận':z.saved_estimated_dates+' / '+z.lots+' lô'}}</td>
      <td>{{z.actual_planting_lots}} lô có ngày trồng thật</td>
     </tr>
    </tbody>
   </table>
  </div>
  <p v-if="result?.available" class="zone-plan__note"><b>Phân bổ trổ:</b> 20% tháng đầu, 60% tháng tiếp, 20% tháng cuối. Khu E chưa được xác nhận lịch trồng; trong chế độ chạy thử chỉ dùng mốc giả lập. Ngày chọn chồi hoặc trổ ghi nhận mới sẽ thay mốc dự phóng của đợt tương ứng.</p>
 </section>
</template>
<style scoped>
.zone-plan{display:grid;gap:10px;border:1px solid var(--lotus-border,#e2e6eb);border-radius:10px;padding:13px;font-size:12px;color:var(--lotus-text,#273140)}
.zone-plan header{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.zone-plan header p{font-size:11px;color:var(--lotus-muted,#657587);margin:5px 0 0}
.zone-plan header button{border:1px solid var(--lotus-border,#dce2e8);border-radius:7px;background:var(--lotus-surface,#fff);color:inherit;padding:5px 9px}
.zone-plan__scroll{overflow-x:auto}
.zone-plan table{border-collapse:collapse;width:100%;min-width:620px;font-size:11px}
.zone-plan th{text-align:left;background:var(--lotus-table-header,#f7f9fa);font-weight:700}
.zone-plan th,.zone-plan td{padding:9px 10px;border-bottom:1px solid var(--lotus-border,#e1e6e9)}
.zone-plan__note{color:var(--lotus-muted,#657587);margin:0;font-size:11px;line-height:1.6}
</style>
