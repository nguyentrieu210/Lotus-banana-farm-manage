<script setup>
import {computed,defineAsyncComponent,onMounted,ref,watch} from 'vue'
import {call} from '../api'
const DesktopForecastChart=defineAsyncComponent(()=>import('./DesktopForecastChart.vue'))
const ZonePlantingSchedule=defineAsyncComponent(()=>import('./ZonePlantingSchedule.vue'))
const props=defineProps({farm:{type:String,default:''},block:{type:String,default:''}})
const area=ref('ALL'),scenario=ref('base'),year=ref('2027'),mode=ref('trial')
const trialBlock=ref(''),trialStage=ref('sucker'),trialDate=ref('2026-11-15'),trialQty=ref('')
const appliedTrial=ref(null)
const loading=ref(false),error=ref(''),forecast=ref(null)
const zoneNames=['ALL','A','B','C','D','E']
const scenarios=[{key:'low',name:'Thấp'},{key:'base',name:'Cơ sở'},{key:'high',name:'Cao'}]
const stageChoices=[{value:'plant',name:'Ngày trồng'},{value:'sucker',name:'Ngày chọn chồi'},
 {value:'shoot',name:'Ngày trổ'},{value:'cut',name:'Ngày cắt bắp'},
 {value:'harvest_actual',name:'Thu hoạch thực tế (giả lập)'}]
const sourceNames={packing_plan:'Kế hoạch VIP 126',planting_records:'Theo dõi trồng mới',sucker_schedule:'Lịch chọn chồi',crop_close:'Báo cáo kết vụ'}
const yearMonths=computed(()=>(forecast.value?.months||[]).filter(m=>m.month.startsWith(year.value)))
const years=computed(()=>[...new Set((forecast.value?.months||[]).map(m=>m.month.slice(0,4)))])
const availableLots=computed(()=>[...new Set((forecast.value?.rows||[]).map(r=>r.block_code))].sort((a,b)=>a.localeCompare(b,'en',{numeric:true})))
const yearRows=computed(()=>(forecast.value?.rows||[]).filter(r=>r.month.startsWith(year.value)))
const ton=n=>new Intl.NumberFormat('vi-VN',{maximumFractionDigits:1}).format(Number(n||0)/1000)
const integer=n=>new Intl.NumberFormat('vi-VN',{maximumFractionDigits:0}).format(Number(n||0))
const dm=s=>s?.split('-').reverse().join('/')||'—'
const stageName=s=>({estimated_flower:'Trổ dự kiến',inferred_plant:'Trồng suy ngược',trial_flower:'Trổ giả lập',sucker:'Chọn chồi',plant:'Ngày trồng',shoot:'Trổ',cut:'Cắt bắp',harvest_actual:'Đã thu'})[s]||s

let seq=0
async function load(){
 const id=++seq
 loading.value=true;error.value=''
 try{
   const isTrial=mode.value==='trial'
   const method=isTrial?'lotus_farm.vip126_trial.calendar':'lotus_farm.vip126_timeline.calendar'
   const args={farm:props.farm||null,block:props.block||null,
     zone:area.value==='ALL'?null:area.value,scenario:scenario.value,
     ...(isTrial&&appliedTrial.value?appliedTrial.value:{})}
   const result=await call(method,args)
   if(seq!==id)return
   forecast.value=result
   if(result?.months?.length&&!result.months.some(m=>m.month.startsWith(year.value))){
     year.value=result.months[0].month.slice(0,4)
   }
 }catch(e){if(id===seq){forecast.value=null;error.value=e.message||'Không đọc được dự phóng'}}
 finally{if(id===seq)loading.value=false}
}
watch(()=>[props.farm,props.block,area.value,mode.value],()=>{
 appliedTrial.value=null;trialBlock.value='';forecast.value=null;load()
})
watch(scenario,()=>{appliedTrial.value=null;load()})
onMounted(load)
function runTrial(){
 if(!trialBlock.value||!trialDate.value||mode.value!=='trial')return
 appliedTrial.value={trial_block:trialBlock.value,trial_stage:trialStage.value,
   trial_date:trialDate.value,...(trialQty.value?{trial_qty:trialQty.value}:{})}
 load()
}
function clearTrial(){appliedTrial.value=null;load()}
</script>
<template>
<section class="vip126-timeline" aria-label="Dự phóng VIP 126 cuốn chiếu">
 <header class="vip126-timeline__head">
  <div><div class="vip126-timeline__eyebrow">VIP 126 · VƯỜN 222 · 36 THÁNG CUỐN CHIẾU</div>
   <h2>{{mode==='trial'?'Thử nghiệm trọn vòng sản xuất':'Dự phóng từ dữ liệu đang có'}}</h2>
   <p>Chọn khu và kịch bản để xem lịch thu. Có thể thử thay một mốc sinh trưởng để toàn bộ các vụ tiếp theo tính lại.</p>
  </div>
  <button type="button" class="vip126-timeline__reload" :disabled="loading" @click="load">↻ Làm mới</button>
 </header>
 <div class="vip126-timeline__segments">
  <button type="button" :class="{selected:mode==='trial'}" :aria-pressed="mode==='trial'" @click="mode='trial'">Chạy thử đủ 64 lô</button>
  <button type="button" :class="{selected:mode==='real'}" :aria-pressed="mode==='real'" @click="mode='real'">Chỉ dữ liệu đang có</button>
 </div>
 <div class="vip126-timeline__warning" role="status">
  <template v-if="mode==='trial'"><strong>THỬ NGHIỆM – KHÔNG PHẢI SẢN LƯỢNG THẬT.</strong>
   Lô chưa có số cây được giả lập theo ha × mật độ; khu E dùng ngày trổ giả lập, khu A–D theo mốc dự kiến đã lưu.
   17 kg là trên mỗi buồng sơ chế theo kế hoạch OneDrive cũ, không phải kg buồng thô.</template>
  <template v-else><strong>DỰ PHÓNG VẬN HÀNH · CHƯA HIỆU CHUẨN.</strong> Chỉ hiển thị dự báo từ số liệu đã ghi nhận hoặc ngày dự kiến bạn nhập; các hệ số chưa xác nhận thực địa.</template>
  Không tạo phiếu thật, tồn kho hay cam kết bán.
 </div>
 <ZonePlantingSchedule :farm="farm" :zone="area" :block="block" />
 <div v-if="mode==='trial'" class="vip126-timeline__flowering">
  <strong>Phân bổ trổ hoa: 20% – 60% – 20%</strong>
  <div class="vip126-timeline__flowering-track">
   <div style="flex:2"><b>20%</b><small>Tháng đầu</small></div>
   <div style="flex:6"><b>60%</b><small>Tháng thứ hai</small></div>
   <div style="flex:2"><b>20%</b><small>Tháng cuối</small></div>
  </div>
  <p>Áp dụng cho từng đợt trổ của mỗi lô; tính ngày thu tương ứng cho 3 đợt và tiếp tục cuốn chiếu các vụ chồi. Ví dụ khu A: 11/2026 (20%), 12/2026 (60%), 01/2027 (20%).</p>
 </div>
 <div class="vip126-timeline__cut-rule">
   <strong>Trổ hoa → cắt bắp: 17 ngày</strong>
   <span>Cắt bắp → thu hoạch: <b>60–70 ngày</b> · Trung bình <b>65 ngày</b> · Từ trổ đến thu: <b>77–87 ngày</b>.</span>
   <small>Áp dụng theo từng đợt 20% / 60% / 20%. Khi có ngày cắt bắp thực tế, mốc cắt bắp được ưu tiên, không cộng thêm 17 ngày.</small>
 </div>
 <div class="vip126-timeline__filters">
  <fieldset><legend>Lọc khu</legend><div class="vip126-timeline__segments">
   <button v-for="z in zoneNames" :key="z" type="button" :aria-pressed="area===z" :class="{selected:area===z}" @click="area=z">{{z==='ALL'?'Tất cả':'Khu '+z}}</button>
  </div></fieldset>
  <fieldset><legend>Kịch bản</legend><div class="vip126-timeline__segments">
   <button v-for="s in scenarios" :key="s.key" type="button" :aria-pressed="scenario===s.key" :class="{selected:scenario===s.key}" @click="scenario=s.key">{{s.name}}</button>
  </div></fieldset>
 </div>
 <div v-if="mode==='trial'" class="vip126-timeline__trial-box">
  <div><strong>Giả lập mốc sinh trưởng của một lô</strong><p>Chỉ tính trên màn hình, không sửa hồ sơ lô.</p></div>
  <label>Lô<select v-model="trialBlock"><option value="">Chọn lô thử</option><option v-for="lot in availableLots" :key="lot" :value="lot">{{lot}}</option></select></label>
  <label>Mốc mới<select v-model="trialStage"><option v-for="s in stageChoices" :key="s.value" :value="s.value">{{s.name}}</option></select></label>
  <label>Ngày<input v-model="trialDate" type="date" /></label>
  <label>Số cây/buồng (tùy chọn)<input v-model="trialQty" type="number" min="1" placeholder="Lấy theo lô" /></label>
  <button type="button" class="vip126-timeline__reload" :disabled="loading||!trialBlock||!trialDate" @click="runTrial">Tính lại 36 tháng</button>
  <button v-if="appliedTrial" type="button" class="vip126-timeline__reload" @click="clearTrial">Bỏ mốc thử</button>
 </div>
 <p v-if="loading" class="vip126-timeline__info">Đang tính lại 36 tháng…</p>
 <p v-if="error" role="alert" class="vip126-timeline__error">{{error}}</p>
 <template v-if="forecast?.available">
  <div class="vip126-timeline__metrics">
   <article><small>Lô đang xem</small><strong>{{forecast.summary.total_lots}}</strong></article>
   <article><small>Lô có lịch dự thu</small><strong>{{forecast.summary.projected_lots}}</strong></article>
   <article><small>Tấn buồng thô mô phỏng</small><strong>{{ton(forecast.summary.gross_kg)}} <em>tấn</em></strong></article>
   <article><small>Thành phẩm dự kiến</small><strong>{{ton(forecast.summary.packed_kg)}} <em>tấn</em></strong></article>
   <article><small>Được phép giao bán</small><strong>0 <em>tấn</em></strong></article>
  </div>
  <div class="vip126-timeline__config">
   <strong>Hệ số: {{forecast.scenario_name}}</strong>
   <span v-if="mode==='trial'">{{integer(forecast.config.density)}} cây/ha để giả lập lô thiếu · {{forecast.config.flower_share*100}}% cây ra buồng · {{forecast.config.cut_rate*100}}% đến cắt bắp · {{forecast.config.harvest_rate*100}}% thu/cắt · {{forecast.config.preprocess_rate*100}}% sơ chế/thu · {{forecast.config.packed_kg_per_processed_bunch}} kg thành phẩm/buồng sơ chế · chu kỳ thu chồi {{forecast.config.ratoon_days}} ngày.</span>
   <span v-else>{{forecast.config.flower_share*100}}% cây ra buồng · {{forecast.config.survival*100}}% còn thu · {{forecast.config.weight_kg}} kg/buồng · QC {{forecast.config.quality*100}}% · đóng gói {{forecast.config.packout*100}}% · chu kỳ chồi {{forecast.config.ratoon_days}} ngày.</span>
  </div>
  <p v-if="mode==='trial'" class="vip126-timeline__info">
   <strong>{{forecast.summary.known_count_lots}} lô có số cây từ Excel</strong> ·
   <strong>{{forecast.summary.synthetic_count_lots}} lô dùng số cây giả lập</strong> ·
   <strong>{{forecast.summary.synthetic_anchor_lots}} lô có ngày trổ giả lập</strong>.
   <span v-if="forecast.trial_event"> Đang thử {{forecast.trial_event.block}} — {{forecast.trial_event.stage}} ngày {{dm(forecast.trial_event.date)}}.</span>
  </p>
  <div class="vip126-timeline__years">
   <button v-for="y in years" :key="y" type="button" :aria-pressed="year===y" :class="{selected:year===y}" @click="year=y">{{y}}</button>
  </div>
  <DesktopForecastChart v-if="yearMonths.some(m=>Number(m.gross_kg)>0)" :months="yearMonths"/>
  <p v-else class="vip126-timeline__info">Chưa có dự thu trong năm/khu này.</p>
  <div class="vip126-timeline__scroll">
   <table>
    <thead><tr><th>Lô</th><th>Vụ</th><th>Tháng trổ</th><th>Tỷ lệ trổ</th><th>Buồng trổ</th><th>Nguồn</th><th>Ngày mốc</th><th>Cắt bắp dự kiến</th><th>Khoảng ngày thu</th><th>Thu cơ sở</th><th>Buồng thu</th><th>Tấn buồng thô *</th><th>Tấn thành phẩm **</th></tr></thead>
    <tbody>
     <tr v-for="(r,i) in yearRows" :key="r.block+'-'+r.cycle_no+'-'+i">
      <td><strong>{{r.block_code}}</strong><small v-if="r.synthetic_count">Cây giả lập</small><small v-if="r.synthetic_stage">Mốc giả lập</small></td>
      <td>{{r.cycle_no}}</td><td>{{r.flowering_month||'—'}}</td><td>{{r.flowering_share_percent==null?'—':r.flowering_share_percent+'%'}}</td><td>{{r.flowering_bunches==null?'—':integer(r.flowering_bunches)}}</td>
      <td>{{r.source_label}}<small v-if="r.cycle_no>1">Từ {{stageName(r.anchor_stage)}}</small></td>
      <td>{{dm(r.source_date)}}</td><td>{{dm(r.cut_date)}}</td><td>{{r.harvest_earliest_date?dm(r.harvest_earliest_date)+' – '+dm(r.harvest_latest_date):'—'}}</td><td>{{dm(r.expected_date)}}</td>
      <td>{{integer(r.bunches)}}</td><td>{{ton(r.gross_kg)}}</td><td>{{ton(r.packed_kg)}}</td>
     </tr>
     <tr v-if="!yearRows.length"><td colspan="13">Chưa có lịch trong năm này.</td></tr>
    </tbody>
   </table>
  </div>
  <details v-if="forecast.issues?.length" class="vip126-timeline__issues"><summary>Các lô cần đối chiếu ({{forecast.issues.length}})</summary>
   <p v-for="(item,i) in forecast.issues" :key="i"><b>{{item.block_code}}:</b> {{item.reason}}</p>
  </details>
  <div class="vip126-timeline__foot">
   <strong>Quy tắc cuốn chiếu:</strong> ngày trồng → chọn chồi → trổ → cắt bắp → thu.
   Khi thay mốc, các kỳ dự kiến tương lai dịch chuyển, lịch sử thực tế không bị ghi đè.
   <p v-if="mode==='trial'">* Kg buồng thô là giả định mô hình. ** Tấn thành phẩm = số buồng sơ chế × kg thành phẩm/buồng; không nhân lặp tỷ lệ QC và packout. Lịch chọn chồi khoảng 6 tháng không phải chu kỳ thu hoạch.</p>
   <p>{{forecast.source_notice}}</p>
   <p v-if="forecast.source_links">Nguồn:
    <a v-for="(url,key) in forecast.source_links" :key="key" :href="url" target="_blank" rel="noopener noreferrer">{{sourceNames[key]||key}} ↗ </a>
   </p>
   <p>Từ {{dm(forecast.from_date)}} đến {{dm(forecast.to_date)}}. Được phép cam kết: <strong>0 tấn</strong> cho đến khi có dữ liệu và duyệt chính thức.</p>
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

.vip126-timeline__flowering{display:grid;gap:8px;padding:13px;border:1px solid var(--lotus-border,#e1e6e9);border-radius:9px;font-size:12px}
.vip126-timeline__flowering-track{display:flex;gap:4px;max-width:600px}
.vip126-timeline__flowering-track div{display:grid;justify-items:center;gap:3px;padding:9px 4px;border-radius:5px;background:var(--lotus-accent-soft,#fcece2);color:var(--lotus-accent,#ac411e)}
.vip126-timeline__flowering-track small{font-size:10px}
.vip126-timeline__flowering p{font-size:11px;color:var(--lotus-muted,#627284);margin:0}
.vip126-timeline__cut-rule{display:grid;gap:4px;padding:12px;border:1px solid var(--lotus-border,#e1e7eb);border-radius:9px;background:var(--lotus-soft,#f8f9fa);font-size:12px}
.vip126-timeline__cut-rule small{font-size:11px;color:var(--lotus-muted,#687687)}
.vip126-timeline__trial-box{display:flex;flex-wrap:wrap;gap:9px;align-items:flex-end;padding:12px;background:var(--lotus-soft,#f6f8fa);border:1px solid var(--lotus-border,#dbe2e8);border-radius:9px;font-size:12px}
.vip126-timeline__trial-box>div{flex-basis:100%}
.vip126-timeline__trial-box p{margin:3px 0;color:var(--lotus-muted,#67788c)}
.vip126-timeline__trial-box label{display:grid;gap:4px}
.vip126-timeline__trial-box select,.vip126-timeline__trial-box input{height:34px;background:var(--lotus-surface,#fff);color:var(--lotus-text,#273140);border:1px solid var(--lotus-border,#dce2e7);border-radius:7px;padding:4px 9px;max-width:195px}
.vip126-timeline__foot a{color:var(--lotus-accent,#b64221);text-decoration:underline;margin-right:6px}
</style>