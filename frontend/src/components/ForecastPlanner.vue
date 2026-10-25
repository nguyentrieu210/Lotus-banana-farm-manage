<script setup>
import {FormField} from './ui/form-field'
import {computed,defineAsyncComponent,ref,watch} from 'vue'
import {Button as UiButton} from './ui/button'
import {Input as UiInput} from './ui/input'
import WorkspaceTabs from './WorkspaceTabs.vue'
import DesktopPageHeading from './DesktopPageHeading.vue'
import DesktopMetricCard from './DesktopMetricCard.vue'
import DesktopEmptyState from './DesktopEmptyState.vue'
import DataTable from './DataTable.vue'
import {sampleForecastCalendar} from '../forecast-sample.js'
const DesktopForecastChart=defineAsyncComponent(()=>import('./DesktopForecastChart.vue'))
import '../forecast-calendar.css'

const props=defineProps({
  payload:{type:Object,default:()=>({})},
  loading:Boolean,
  canSettings:Boolean,
  canEditBlock:Boolean,
  canDownloadTemplate:Boolean,
})
const emit=defineEmits(['reload','settings','edit-block','download-template','demo-changed'])
const demoMode=ref(false)
const displayPayload=computed(()=>demoMode.value?sampleForecastCalendar(props.payload?.from_date||'2026-10-01'):props.payload)
const search=ref('')
const year=ref('')
const selectedMonth=ref('')
const numbers=new Intl.NumberFormat('vi-VN',{maximumFractionDigits:1})
const ton=value=>numbers.format((Number(value)||0)/1000)
const bunches=value=>new Intl.NumberFormat('vi-VN',{maximumFractionDigits:0}).format(Number(value)||0)
const allMonths=computed(()=>displayPayload.value?.months||[])
const years=computed(()=>[...new Set(allMonths.value.map(x=>x.month.slice(0,4)))])
watch(years,values=>{if(!values.includes(year.value))year.value=values[0]||''},{immediate:true})
const months=computed(()=>allMonths.value.filter(x=>x.month.startsWith(year.value)))
const maxGross=computed(()=>Math.max(1,...months.value.map(m=>Number(m.gross_kg)||0)))
const allRows=computed(()=>displayPayload.value?.rows||[])
const rows=computed(()=>allRows.value.filter(r=>
 (!year.value||r.month.startsWith(year.value))
 &&(!selectedMonth.value||r.month===selectedMonth.value)
 &&(!search.value||[r.farm_block,r.block_name,r.cycle,r.source_label].some(x=>String(x||'').toLocaleLowerCase('vi').includes(search.value.toLocaleLowerCase('vi'))))
))
const yearTotal=computed(()=>months.value.reduce((sum,m)=>sum+(Number(m.gross_kg)||0),0))
const issueCount=computed(()=>displayPayload.value?.issues?.length||0)
const confidence=r=>r?.confidence||'—'
const monthName=m=>String(Number(m.slice(5)))+'/ '+m.slice(0,4)
const calendarCols=[{field:'block_name',headerName:'Lô'},{field:'cycle_no',headerName:'Vụ'},{field:'expected_date',headerName:'Ngày dự thu'},{field:'source_label',headerName:'Nguồn tính',valueFormatter:p=>p.value+(p.data?.projected?' · Chỉ dự phóng, chưa chốt':'')},{field:'confidence',headerName:'Độ tin cậy'},{field:'bunches',headerName:'Buồng',valueFormatter:p=>bunches(p.value)},{field:'gross_kg',headerName:'Tấn buồng',valueFormatter:p=>ton(p.value)},{field:'packed_kg',headerName:'Tấn thành phẩm',valueFormatter:p=>ton(p.value)}]
function pickMonth(key){selectedMonth.value=selectedMonth.value===key?'':key}
</script>

<template>
  <section class="calendar-board" aria-label="Kế hoạch dự thu chuối 36 tháng">
    <DesktopPageHeading title="Dự thu 3 năm" eyebrow="Kế hoạch sản lượng 36 tháng" description="Tính tự động theo ngày trồng → chọn chồi → trổ buồng → cắt bắp. Dữ liệu mới được ưu tiên hơn.">
      <template #actions><div class="calendar-buttons">
        <UiButton v-if="!demoMode&&canSettings" variant="outline" type="button" @click="emit('settings',null)">Thiết lập hệ số</UiButton>
        <UiButton v-if="!demoMode&&canDownloadTemplate" variant="outline" type="button" @click="emit('download-template')">Tải bảng nhập ngày trồng</UiButton>
        <UiButton variant="outline" type="button" :aria-pressed="demoMode" @click="demoMode=!demoMode;selectedMonth='';year='';emit('demo-changed',demoMode)">{{demoMode?'Xem dữ liệu thật':'Xem dữ liệu mẫu'}}</UiButton>
        <UiButton variant="outline" type="button" :disabled="loading" @click="emit('reload')">Làm mới</UiButton>
      </div></template>
    </DesktopPageHeading>
    <div v-if="demoMode" class="calendar-demo-warning" role="status"><strong>ĐANG XEM DỮ LIỆU MẪU</strong> · Đây là các lô giả lập để xem giao diện và kiểm tra thứ tự ưu tiên. Không phải dữ liệu Lotus, không ghi vào hệ thống và không dùng để giao hàng.</div>
    <div class="calendar-kpis">
      <DesktopMetricCard label="Tổng dự thu 36 tháng" :value="ton(displayPayload.summary?.gross_kg)" unit="tấn buồng" description="Ước tính, chưa phải sản lượng chốt"/>
      <DesktopMetricCard label="Thành phẩm dự kiến" :value="ton(displayPayload.summary?.packed_kg)" unit="tấn" description="Đã áp dụng hệ số chất lượng và đóng gói"/>
      <DesktopMetricCard label="Lô đã có dự tính" :value="(displayPayload.summary?.ready_blocks||0)+' / '+(displayPayload.summary?.blocks||0)" description="Chỉ tính khi đủ dữ liệu và hệ số"/>
      <DesktopMetricCard label="Cần kiểm tra" :value="issueCount" description="Thiếu thông số hoặc chưa rõ đợt cây" :warning="issueCount>0"/>
    </div>
    <div class="calendar-toolbar">
      <WorkspaceTabs label="Chọn năm" :items="years.map(y=>({id:y,label:y}))" :model-value="year" @update:model-value="y=>{year=y;selectedMonth=''}"/>
      <FormField label="Tìm lô" v-slot="f"><UiInput v-bind="f" v-model="search" type="search" placeholder="Tên lô, số vụ, nguồn tính…" /></FormField>
      <span class="calendar-total">Năm {{year}}: <b>{{ton(yearTotal)}} tấn buồng</b></span>
    </div>
    <section class="calendar-panel">
      <div class="calendar-panel-title"><strong>Sản lượng theo tháng</strong><span>Chọn tháng để xem các lô dự kiến thu</span></div>
      <DesktopForecastChart v-if="months.some(m=>Number(m.gross_kg)>0||Number(m.actual_gross_kg)>0)" :months="months"/>
      <DesktopEmptyState v-else title="Chưa có sản lượng dự thu đủ căn cứ" description="Nhập ngày trồng trên lô và bổ sung bộ hệ số đã duyệt. Lotus không tự đoán sản lượng khi thiếu thông tin." icon="▤"/>
      <div v-if="months.length" class="calendar-months">
        <button v-for="m in months" :key="m.month" type="button" :aria-pressed="selectedMonth===m.month" :class="{active:selectedMonth===m.month}" @click="pickMonth(m.month)">
          <span>Tháng {{Number(m.month.slice(5))}}</span>
          <div class="calendar-track"><div :style="{height:Math.max(1,Number(m.gross_kg)/maxGross*100)+'%'}" /></div>
          <strong>{{ton(m.gross_kg)}}</strong>
          <small>tấn</small>
        </button>
      </div>
      <p v-else class="calendar-hint">Không có tháng trong khoảng kế hoạch.</p>
    </section>
    <section class="calendar-panel">
      <div class="calendar-panel-title"><strong>{{selectedMonth?'Dự thu tháng '+monthName(selectedMonth):'Các đợt dự thu năm '+year}}</strong><span>{{rows.length}} đợt · nhấp dòng để xem nguồn tính</span></div>
      <div class="calendar-scroll">
        <DataTable :rows="rows" :columns="calendarCols" storage-key="forecast-calendar-grid" empty="Không có dự thu phù hợp."/>
      </div>
      <p class="calendar-note">Không cộng các công đoạn trùng một đợt. Các đợt chưa đủ thông tin liên kết sẽ được báo cần đối chiếu; số tự dự phóng không dùng để cam kết bán hàng.</p>
    </section>
    <details v-if="issueCount" class="calendar-issues">
      <summary>Cần bổ sung dữ liệu ({{issueCount}})</summary>
      <div class="calendar-issues-list">
        <div v-for="(issue,i) in displayPayload.issues" :key="i"><b>{{issue.block_name||issue.farm_block}}:</b> {{issue.message}} <UiButton v-if="!demoMode&&canEditBlock" class="calendar-issue-edit" type="button" variant="outline" size="sm" @click="emit('edit-block',issue.farm_block)">Sửa thông tin lô</UiButton></div>
      </div>
      <p v-if="canSettings">Bấm <b>Thiết lập hệ số</b> để thêm số ngày từ trồng đến thu và chu kỳ vụ chồi, sau đó phát hành bộ hệ số theo quy trình duyệt.</p>
    </details>
    <p class="calendar-footnote">Khoảng kế hoạch: {{displayPayload.from_date||'—'}} đến {{displayPayload.to_date||'—'}}. {{displayPayload.note}}</p>
  </section>
</template>