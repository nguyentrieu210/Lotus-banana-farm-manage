<script setup>
import {computed,ref,watch} from 'vue'
import UiSelect from './ui/select/Select.vue'
import {Button as UiButton} from './ui/button'
import {stateLabel} from '../labels'
import LotusChart from './LotusChart.vue'
import OverviewBoard from './OverviewBoard.vue'
import WorkspaceTabs from './WorkspaceTabs.vue'
import {formatDate,formatMonthShort} from '../format'
// /lotus/reports: charts per operating area from lotus_farm.reporting.charts; the forecast tab keeps the legacy tables (slot).
const props=defineProps({charts:{type:Object,default:null},busy:Boolean,filters:{type:Object,default:()=>({})}})
const emit=defineEmits(['filters','tab'])
const tabs=[{id:'overview',label:'Toàn bộ nghiệp vụ'},{id:'land',label:'Vườn & cây'},{id:'work',label:'Công việc'},{id:'harvest',label:'Thu hoạch & đóng gói'},{id:'stock',label:'Kho'},{id:'people',label:'Nhân sự & lương'},{id:'commerce',label:'Mua & bán'},{id:'forecast',label:'Dự thu & hiệu chuẩn'}]
const tab=ref('overview')
watch(tab,value=>emit('tab',value))
const filterFields=computed(()=>{
 const fields={stock:[['stock_type','Loại phiếu kho']],people:[['department','Phòng ban'],['worker_category','Loại lao động']],commerce:[['buying_status','Trạng thái đơn mua'],['supplier','Nhà cung cấp'],['sales_status','Trạng thái đơn bán'],['customer','Khách hàng']]}
 return (tab.value==='overview'?Object.values(fields).flat():fields[tab.value]||[]).map(([key,label])=>({key,label,options:Object.values(props.charts||{}).find(s=>s?.options?.[key])?.options[key]||[]}))
})
function filter(key,value){emit('filters',{...props.filters,[key]:value})}
const c=computed(()=>props.charts||{})
const n=(v,d=0)=>v==null||Number.isNaN(Number(v))?'—':new Intl.NumberFormat('vi-VN',{maximumFractionDigits:d}).format(Number(v))
const sum=(rows,key)=>(rows||[]).reduce((t,r)=>t+Number(r[key]||0),0)
const pct=(part,whole)=>whole?part/whole*100:null
const shortDay=v=>formatDate(v).slice(0,5)

const land=computed(()=>c.value.land||{})
const zones=computed(()=>land.value.zones||[])
const flowering=computed(()=>land.value.flowering||[])
const counted=computed(()=>zones.value.filter(z=>z.counted_blocks))

const work=computed(()=>c.value.work||{})
const days=computed(()=>work.value.days||[])
const types=computed(()=>work.value.types||[])
const workDone=computed(()=>{const v=days.value.map(d=>d.completion_percent).filter(v=>v!=null);return v.length?v.reduce((a,b)=>a+b,0)/v.length:null})

const harvest=computed(()=>c.value.harvest||{})
const weeks=key=>(harvest.value[key]||[])
const losses=computed(()=>c.value.losses||{})
const stock=computed(()=>c.value.stock||{})
const sectionOf={land,work,harvest,stock}
const denied=computed(()=>sectionOf[tab.value]&&props.charts&&sectionOf[tab.value].value.allowed===false)
</script>
<template>
<section class="lotus-reports">
 <WorkspaceTabs v-model="tab" :items="tabs" label="Nhóm báo cáo"/>
 <div v-if="charts&&filterFields.length" class="scope-picker report-filters"><label v-for="f in filterFields" :key="f.key">{{f.label}}<UiSelect :model-value="filters[f.key]||''" @update:model-value="filter(f.key,$event)"><option value="">Tất cả</option><option v-for="option in f.options" :key="option" :value="option">{{stateLabel(option)}}</option></UiSelect></label><UiButton v-if="Object.values(filters).some(Boolean)" variant="outline" @click="emit('filters',{})">Xoá lọc báo cáo</UiButton></div>
 <p v-if="charts" class="muted lotus-reports-period">Kỳ báo cáo: {{formatDate(charts.from_date)}} – {{formatDate(charts.to_date)}} · {{charts.farms?.length||0}} vườn được xem</p>
 <p v-else-if="busy" class="muted">Đang đọc số liệu…</p>
 <p v-if="denied" role="alert" class="notice">Bạn không có quyền xem phần báo cáo này.</p>

 <OverviewBoard v-else-if="tab==='overview'&&charts" :charts="charts"/>
 <template v-else-if="tab==='people'&&charts"><p class="muted">Nhân sự & lương · {{c.people?.scope_label}}</p>
  <p v-if="c.people?.allowed===false" class="notice">Bạn không có quyền xem báo cáo nhân sự và lương.</p>
  <p v-else-if="c.people?.note" class="notice">{{c.people.note}}</p>
  <template v-else><div class="lotus-stat-row"><div class="lotus-stat"><span>Đang làm</span><strong>{{n(c.people?.active)}}</strong><small>người</small></div><div class="lotus-stat"><span>Chờ tiếp nhận</span><strong>{{n(c.people?.pending)}}</strong><small>hồ sơ</small></div><div class="lotus-stat"><span>Phiếu lương đã duyệt</span><strong>{{n(c.people?.salary_slips)}}</strong><small>phiếu trong kỳ</small></div><div v-for="p in c.people?.payroll||[]" :key="p.currency" class="lotus-stat"><span>Thực lĩnh</span><strong>{{n(p.net)}}</strong><small>{{p.currency}}</small></div></div><LotusChart title="Chấm công" :categories="(c.people?.attendance||[]).map(r=>r.status)" :series="[{name:'Lượt công',data:(c.people?.attendance||[]).map(r=>r.count)}]" unit="lượt"/></template>
 </template>
 <template v-else-if="tab==='commerce'&&charts"><section v-for="key in ['buying','sales']" :key="key"><p class="muted">{{key==='buying'?'Đơn mua':'Đơn bán'}} · {{c[key]?.scope_label}}</p><p v-if="c[key]?.allowed===false" class="notice">Bạn không có quyền xem {{key==='buying'?'đơn mua':'đơn bán'}}.</p><p v-else-if="c[key]?.note" class="notice">{{c[key].note}}</p><template v-else><div class="lotus-stat-row"><div class="lotus-stat"><span>{{key==='buying'?'Đơn mua':'Đơn bán'}}</span><strong>{{n(c[key]?.count)}}</strong><small>đơn đã duyệt trong kỳ</small></div><div v-for="r in c[key]?.totals||[]" :key="r.currency" class="lotus-stat"><span>Giá trị đơn</span><strong>{{n(r.value)}}</strong><small>{{r.currency}}</small></div></div><LotusChart :title="key==='buying'?'Tình trạng đơn mua':'Tình trạng đơn bán'" :categories="(c[key]?.statuses||[]).map(r=>r.status)" :series="[{name:'Số đơn',data:(c[key]?.statuses||[]).map(r=>r.count)}]" unit="đơn"/></template></section></template>
 <template v-else-if="tab==='land'&&charts">
  <div class="lotus-stat-row">
   <div class="lotus-stat"><span>Diện tích</span><strong>{{n(land.area_ha,1)}}</strong><small>ha · {{n(land.blocks)}} lô</small></div>
   <div class="lotus-stat"><span>Số cây kiểm kê</span><strong>{{n(land.trees)}}</strong><small>{{n(land.counted_blocks)}}/{{n(land.blocks)}} lô có số cây</small></div>
   <div class="lotus-stat"><span>Mật độ bình quân</span><strong>{{n(sum(counted,'counted_area_ha')?sum(counted,'trees')/sum(counted,'counted_area_ha'):null)}}</strong><small>cây/ha (khu có số cây)</small></div>
   <div class="lotus-stat"><span>Đợt trổ dự kiến</span><strong>{{n(flowering.length)}}</strong><small>tháng có lô trổ</small></div>
  </div>
  <div class="lotus-chart-grid">
   <LotusChart title="Số cây theo khu" :categories="zones.map(z=>'Khu '+z.zone)" :series="[{name:'Số cây',data:zones.map(z=>z.trees)}]" unit="cây" empty="Chưa có số cây kiểm kê."/>
   <LotusChart title="Diện tích theo khu" :categories="zones.map(z=>'Khu '+z.zone)" :series="[{name:'Diện tích',data:zones.map(z=>z.area_ha)}]" unit="ha" :decimals="1" empty="Chưa có diện tích lô."/>
   <LotusChart title="Mật độ cây theo khu" :categories="counted.map(z=>'Khu '+z.zone)" :series="[{name:'Mật độ',data:counted.map(z=>z.trees_per_ha)}]" unit="cây/ha" empty="Chưa có lô nào được kiểm kê số cây."/>
   <LotusChart title="Lịch trổ dự kiến" :categories="flowering.map(m=>formatMonthShort(m.month))" :series="[{name:'Số cây trổ',data:flowering.map(m=>m.trees)}]" unit="cây" empty="Chưa có ngày trổ dự kiến cho lô nào."/>
  </div>
 </template>

 <template v-else-if="tab==='work'&&charts">
  <p v-if="work.note" class="notice">{{work.note}}</p>
  <template v-else>
   <div class="lotus-stat-row">
    <div class="lotus-stat"><span>Hoàn thành bình quân</span><strong>{{n(workDone,1)}}</strong><small>% mỗi công việc</small></div>
    <div class="lotus-stat"><span>Công cần</span><strong>{{n(sum(days,'required_workdays'),1)}}</strong><small>công theo kế hoạch</small></div>
    <div class="lotus-stat"><span>Công thực tế</span><strong>{{n(sum(days,'actual_workdays'),1)}}</strong><small>công đã báo</small></div>
    <div class="lotus-stat"><span>Công việc</span><strong>{{n(sum(days,'tasks'))}}</strong><small>dòng kế hoạch trong kỳ</small></div>
   </div>
   <div class="lotus-chart-grid">
    <LotusChart kind="line" title="Tỷ lệ hoàn thành theo ngày" :categories="days.map(d=>shortDay(d.date))" :series="[{name:'Hoàn thành',data:days.map(d=>d.completion_percent)}]" unit="%" :decimals="1" empty="Chưa có kế hoạch công việc đã giao trong kỳ."/>
    <LotusChart title="Công cần và công thực tế theo ngày" :categories="days.map(d=>shortDay(d.date))" :series="[{name:'Công cần',data:days.map(d=>d.required_workdays)},{name:'Công thực tế',data:days.map(d=>d.actual_workdays)}]" unit="công" :decimals="1" empty="Chưa có công trong kỳ."/>
    <LotusChart kind="hbar" title="Công theo loại việc" :categories="types.map(t=>t.work)" :series="[{name:'Công cần',data:types.map(t=>t.required_workdays)},{name:'Công thực tế',data:types.map(t=>t.actual_workdays)}]" unit="công" :decimals="1" :height="Math.max(220,types.length*44)" empty="Chưa có công việc trong kỳ."/>
   </div>
  </template>
 </template>

 <template v-else-if="tab==='harvest'&&charts">
  <p v-if="harvest.note" class="notice">{{harvest.note}}</p>
  <div class="lotus-stat-row">
   <div class="lotus-stat"><span>Thu hoạch</span><strong>{{n(sum(weeks('harvest'),'gross_weight_kg'))}}</strong><small>kg buồng</small></div>
   <div class="lotus-stat"><span>QC đạt</span><strong>{{n(pct(sum(weeks('qc'),'accepted_kg'),sum(weeks('qc'),'received_kg')),1)}}</strong><small>% khối lượng nhận</small></div>
   <div class="lotus-stat"><span>Tỷ lệ đóng gói</span><strong>{{n(pct(sum(weeks('packout'),'finished_kg'),sum(weeks('packout'),'input_kg')),1)}}</strong><small>% thành phẩm / đầu vào</small></div>
   <div class="lotus-stat"><span>Buồng hủy</span><strong>{{n(losses.total)}}</strong><small>buồng</small></div>
  </div>
  <div class="lotus-chart-grid">
   <LotusChart title="Sản lượng thu hoạch theo tuần" :categories="weeks('harvest').map(w=>shortDay(w.week))" :series="[{name:'Khối lượng buồng',data:weeks('harvest').map(w=>w.gross_weight_kg)},{name:'Bán được',data:weeks('harvest').map(w=>w.saleable_weight_kg)}]" unit="kg" empty="Chưa có phiếu thu hoạch đã duyệt trong kỳ."/>
   <LotusChart v-if="harvest.qc" title="QC đầu vào theo tuần" :categories="weeks('qc').map(w=>shortDay(w.week))" :series="[{name:'Nhận',data:weeks('qc').map(w=>w.received_kg)},{name:'Đạt',data:weeks('qc').map(w=>w.accepted_kg)}]" unit="kg" empty="Chưa có phiếu QC đầu vào trong kỳ."/>
   <LotusChart v-if="harvest.packout" title="Đóng gói theo tuần" :categories="weeks('packout').map(w=>shortDay(w.week))" :series="[{name:'Đầu vào',data:weeks('packout').map(w=>w.input_kg)},{name:'Thành phẩm',data:weeks('packout').map(w=>w.finished_kg)}]" unit="kg" empty="Chưa có lượt đóng gói trong kỳ."/>
   <LotusChart v-if="losses.allowed!==false" kind="hbar" title="Lý do hủy buồng" :categories="(losses.reasons||[]).map(r=>r.label)" :series="[{name:'Buồng hủy',data:(losses.reasons||[]).map(r=>r.value)}]" unit="buồng" :height="Math.max(200,(losses.reasons||[]).length*36)" empty="Không có buồng hủy trong kỳ."/>
  </div>
 </template>

 <template v-else-if="tab==='stock'&&charts"><p class="muted">Kho · {{stock.scope_label}}</p>
  <p v-if="stock.note" class="notice">{{stock.note}}</p>
  <div class="lotus-chart-grid lotus-chart-grid--single">
   <LotusChart title="Số phiếu kho theo tháng" :categories="(stock.months||[]).map(m=>formatMonthShort(m.month))" :series="[{name:'Nhập',data:(stock.months||[]).map(m=>m.receipt)},{name:'Xuất',data:(stock.months||[]).map(m=>m.issue)},{name:'Chuyển kho',data:(stock.months||[]).map(m=>m.transfer)}]" unit="phiếu" empty="Chưa có phiếu kho đã ghi sổ trong kỳ."/>
  </div>
 </template>

 <div v-show="tab==='forecast'"><slot name="forecast"/></div>
</section>
</template>
