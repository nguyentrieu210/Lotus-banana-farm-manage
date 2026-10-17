<script setup>
import {computed,defineAsyncComponent,onMounted,ref,watch} from 'vue'
import {call} from '../api'
const DesktopForecastChart=defineAsyncComponent(()=>import('./DesktopForecastChart.vue'))
const props=defineProps({
 farm:{type:String,default:''},block:{type:String,default:''},
})
const area=ref('ALL'),scenario=ref('base'),year=ref('2027')
const loading=ref(false),err=ref(''),forecast=ref(null)
const yearMonths=computed(()=>forecast.value?.months.filter(m=>m.month.startsWith(year.value))||[])
const years=computed(()=>[...new Set((forecast.value?.months||[]).map(m=>m.month.slice(0,4)))])
const zoneNames=['ALL','A','B','C','D','E']
const scenarios=[
 {key:'low',name:'Thấp'}, {key:'base',name:'Cơ sở'}, {key:'high',name:'Cao'},
]
let request=0
async function load(){
 const seq=++request;loading.value=true;err.value=''
 try{
   const data=await call('lotus_farm.vip126_timeline.calendar',
    {farm:props.farm||null,block:props.block||null,zone:area.value==='ALL'?null:area.value,
     scenario:scenario.value})
   if(seq===request){
     forecast.value=data
     if(data?.months?.length&&!data.months.some(m=>m.month.startsWith(year.value))){
       year.value=data.months[0].month.slice(0,4)
     }
   }
 }catch(e){if(seq===request)err.value=e.message||'Không tải được dự phóng'}
 finally{if(seq===request)loading.value=false}
}
watch(()=>[props.farm,props.block,area.value,scenario.value],load)
onMounted(load)
const rows=computed(()=>forecast.value?.rows.filter(r=>r.month.startsWith(year.value))||[])
const ton=n=>new Intl.NumberFormat('vi-VN',{maximumFractionDigits:1}).format(Number(n||0)/1000)
const intl=n=>new Intl.NumberFormat('vi-VN',{maximumFractionDigits:0}).format(n||0)
const dm=s=>s?.split('-').reverse().join('/')||'—'
const stageName=s=>({estimated_flower:'Trổ dự kiến',sucker:'Chọn chồi',plant:'Ngày trồng',shoot:'Trổ đã ghi',cut:'Cắt bắp',harvest_actual:'Đã thu'})[s]||s
</script>
<template>
 <section class="vip126-timeline" aria-label="Dự phóng VIP 126 theo mốc sinh trưởng">
  <div class="vip126-timeline__head">
   <div>
    <div class="vip126-timeline__eyebrow">VIP 126 · VƯỜN 222 · 36 THÁNG CUỐN CHIẾU</div>
    <h2>Dự phóng từ mốc sinh trưởng mới nhất</h2>
    <p>Số cây đã nạp vào hồ sơ lô. Khi ghi chọn chồi, trổ hoặc cắt bắp, lịch thu của đợt đó và các vụ chồi tiếp theo được tính lại.</p>
   </div>
   <button type="button" class="vip126-timeline__reload" :disabled="loading" @click="load"> <span aria-hidden="true">↻</span> Làm mới</button>
  </div>
  <div class="vip126-timeline__warning" role="status"><strong>DỰ PHÓNG VẬN HÀNH · CHƯA HIỆU CHUẨN</strong> — số cây từ Excel là số thực đã nạp, còn tỷ lệ trổ, kg/buồng, QC và chu kỳ chồi là giả định kịch bản. Không phải sản lượng đã duyệt hoặc có thể cam kết bán.</div>
  <div class="vip126-timeline__filters">
   <fieldset><legend>Lọc khu</legend><div class="vip126-timeline__segments">
    <button v-for="z in zoneNames" :key="z" type="button" :aria-pressed="area===z" :class="{selected:area===z}" @click="area=z">
      {{z==='ALL'?'Tất cả':('Khu '+z)}}
    </button>
   </div></fieldset>
   <fieldset><legend>Kịch bản</legend><div class="vip126-timeline__segments">
    <button v-for="s in scenarios" :key="s.key" type="button" :aria-pressed="scenario===s.key" :class="{selected:scenario===s.key}" @click="scenario=s.key">{{s.name}}</button>
   </div></fieldset>
  </div>
  <p v-if="loading" class="vip126-timeline__info">Đang tính lại 36 tháng từ dữ liệu hiện tại…</p>
  <p v-if="err" class="vip126-timeline__error" role="alert">{{err}}</p>
  <template v-if="forecast?.available">
   <div class="vip126-timeline__metrics">
    <article><small>Lô được chọn</small><strong>{{forecast.summary.total_lots}}</strong></article>
    <article><small>Lô có lịch dự phóng</small><strong>{{forecast.summary.projected_lots}}</strong></article>
    <article><small>Dự thu 36 tháng</small><strong>{{ton(forecast.summary.gross_kg)}} <em>tấn buồng</em></strong></article>
    <article><small>Đóng gói kịch bản</small><strong>{{ton(forecast.summary.packed_kg)}} <em>tấn</em></strong></article>
    <article><small>Được phép giao bán</small><strong>0 <em>tấn</em></strong></article>
   </div>
   <div class="vip126-timeline__config">
    <strong>Hệ số đang thử — {{forecast.scenario_name}}</strong>
    <span>{{forecast.config.flower_share*100}}% cây trong đợt trổ ·
     {{forecast.config.survival*100}}% còn thu · {{forecast.config.weight_kg}} kg/buồng ·
     QC {{forecast.config.quality*100}}% · đóng gói {{forecast.config.packout*100}}% ·
     vụ chồi sau {{forecast.config.ratoon_days}} ngày</span>
   </div>
   <div class="vip126-timeline__years">
    <button v-for="y in years" :key="y" type="button" :aria-pressed="year===y" :class="{selected:year===y}" @click="year=y">{{y}}</button>
   </div>
   <DesktopForecastChart v-if="yearMonths.some(m=>Number(m.gross_kg)>0)" :months="yearMonths"/>
   <p v-else class="vip126-timeline__info">Chưa có sản lượng cho khu/năm đã chọn. Cần số cây và mốc sinh trưởng có căn cứ.</p>
   <div class="vip126-timeline__scroll">
    <table>
     <thead><tr><th>Lô</th><th>Vụ</th><th>Nguồn mới nhất</th><th>Mốc nguồn</th><th>Ngày thu dự kiến</th><th>Buồng</th><th>Tấn buồng</th><th>Tấn thành phẩm</th></tr></thead>
     <tbody>
      <tr v-for="(r,i) in rows" :key="r.block+'-'+r.cycle_no+'-'+i">
       <td><strong>{{r.block_code}}</strong></td><td>{{r.cycle_no}}</td>
       <td>{{r.source_label}}<small v-if="r.cycle_no>1">Tính lại từ {{stageName(r.anchor_stage)}}</small></td>
       <td>{{dm(r.source_date)}}</td><td>{{dm(r.expected_date)}}</td>
       <td>{{intl(r.bunches)}}</td><td>{{ton(r.gross_kg)}}</td><td>{{ton(r.packed_kg)}}</td>
      </tr>
      <tr v-if="!rows.length"><td colspan="8">Chưa có lịch dự phóng trong năm này.</td></tr>
     </tbody>
    </table>
   </div>
   <details v-if="forecast.issues.length" class="vip126-timeline__issues">
    <summary>Các lô cần đối chiếu ({{forecast.issues.length}})</summary>
    <p v-for="(issue,i) in forecast.issues" :key="i"><b>{{issue.block_code}}:</b> {{issue.reason}}</p>
   </details>
   <div class="vip126-timeline__foot">
    <b>Quy tắc ghi đè theo dòng thời gian:</b> ngày trồng → chọn chồi → trổ → cắt bắp; mốc ghi nhận ở đợt mới sẽ thay lịch dự phóng tương lai. Không xóa ngày/sản lượng đã ghi nhận thực tế.
    <p>{{forecast.source_notice}}</p>
    <p>Khung kế hoạch: {{dm(forecast.from_date)}} đến {{dm(forecast.to_date)}}. Được phép cam kết: <b>0 tấn</b> đến khi người có quyền duyệt số liệu và lập phiếu dự thu chính thức.</p>
   </div>
  </template>
 </section>
</template>
<style scoped>
.vip126-timeline{margin:15px 0 18px;display:grid;gap:13px;background:var(--lotus-surface,#fff);border:1px solid var(--lotus-border,#e3e7ec);border-radius:12px;padding:17px;color:var(--lotus-text,#253142);min-width:0}
.vip126-timeline :deep(.lotus-forecast-chart__canvas){height:285px;min-height:260px}
.vip126-timeline__head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.vip126-timeline__eyebrow{font-size:10px;letter-spacing:.06em;color:var(--lotus-accent,#b64221);font-weight:750}
.vip126-timeline__head h2{font-size:19px;letter-spacing:-.02em;margin:4px 0}
.vip126-timeline__head p{font-size:12px;color:var(--lotus-muted,#687787);margin:0}
.vip126-timeline__warning{background:#fff5e9;border:1px solid #eacbb0;border-radius:9px;padding:11px 13px;color:#914316;font-size:12px;line-height:1.6}
.vip126-timeline__filters{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end}
.vip126-timeline__filters fieldset{border:0;padding:0;min-width:0;margin:0}
.vip126-timeline__filters legend{font-weight:650;color:var(--lotus-muted,#546272);font-size:12px;margin-bottom:5px}
.vip126-timeline__segments{display:flex;gap:5px;flex-wrap:wrap}
.vip126-timeline__segments button,.vip126-timeline__years button,.vip126-timeline__reload{border:1px solid var(--lotus-border,#dce1e6);padding:7px 11px;background:var(--lotus-surface,#fff);color:var(--lotus-text,#293444);border-radius:8px;cursor:pointer;font:inherit;font-size:12px}
.vip126-timeline__segments button.selected,.vip126-timeline__years button.selected{background:var(--lotus-accent-soft,#fff0e6);border-color:var(--lotus-accent,#b64221);color:var(--lotus-accent,#b64221);font-weight:700}
.vip126-timeline__metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}
.vip126-timeline__metrics article{padding:12px;border:1px solid var(--lotus-border,#e4e9ef);border-radius:9px;display:grid;gap:6px}
.vip126-timeline__metrics small{font-size:11px;color:var(--lotus-muted,#728092)}
.vip126-timeline__metrics strong{font-size:21px;font-variant-numeric:tabular-nums}
.vip126-timeline__metrics em{font-size:11px;font-weight:450;font-style:normal}
.vip126-timeline__config{display:grid;gap:5px;padding:11px 13px;background:var(--lotus-soft,#f6f8fa);font-size:12px;border-radius:9px}
.vip126-timeline__config span{color:var(--lotus-muted,#657688)}
.vip126-timeline__years{display:flex;gap:7px;flex-wrap:wrap}
.vip126-timeline__scroll{max-height:390px;overflow:auto;border:1px solid var(--lotus-border,#e1e7ed);border-radius:9px}
.vip126-timeline__scroll table{border-collapse:collapse;min-width:910px;width:100%;font-variant-numeric:tabular-nums}
.vip126-timeline__scroll th{text-align:left;position:sticky;top:0;background:var(--lotus-table-header,#f7f8fa);font-weight:650;padding:9px 10px;font-size:11px}
.vip126-timeline__scroll td{border-top:1px solid var(--lotus-border,#e7eaee);padding:9px 10px;font-size:12px}
.vip126-timeline__scroll small{display:block;color:var(--lotus-muted,#6d7a8a);font-size:10px}
.vip126-timeline__foot{font-size:11px;line-height:1.7;color:var(--lotus-muted,#6e7c8d)}
.vip126-timeline__foot p{margin:5px 0}
.vip126-timeline__issues summary{cursor:pointer;font-weight:650;font-size:12px}
.vip126-timeline__issues p{font-size:11px;margin:6px}
.vip126-timeline__info,.vip126-timeline__error{font-size:12px}
.vip126-timeline__error{color:#b91c1c}
.dark .vip126-timeline__warning{background:#392b23;border-color:#704d38;color:#f5c6a3}
@media(max-width:1000px){.vip126-timeline__metrics{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:580px){.vip126-timeline__metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.vip126-timeline{padding:12px}}
</style>
