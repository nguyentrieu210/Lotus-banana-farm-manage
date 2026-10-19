<script setup>
import {computed,ref,watch} from 'vue'
import {AgGridVue} from 'ag-grid-vue3'
import '../grid-modules.js'
import {AG_GRID_LOCALE_VN} from '@ag-grid-community/locale'
import {Button as UiButton} from './ui/button'
import {Input as UiInput} from './ui/input'
import UiSelect from './ui/select/Select.vue'
import {compactGridTheme} from '../grid-theme'
import {forecastStates,availabilityStates,filterForecasts,blockTotals,peakWeek,percent,kg} from '../forecast-planning'
import '../forecast-workspace.css'

const props=defineProps({payload:{type:Object,default:()=>({})},loading:Boolean,canCreate:Boolean})
const emit=defineEmits(['open','create','revise','reload','plan','reports'])
const tab=ref('weeks'),query=ref(''),state=ref(''),block=ref(''),selected=ref(null)
const allRows=computed(()=>props.payload?.rows||[])
const rows=computed(()=>filterForecasts(allRows.value,{query:query.value,state:state.value,block:block.value}))
const blocks=computed(()=>[...new Set(allRows.value.map(r=>r.farm_block).filter(Boolean))].sort((a,b)=>a.localeCompare(b)))
const groupRows=computed(()=>blockTotals(rows.value))
const weeks=computed(()=>props.payload?.weeks||[])
const peak=computed(()=>peakWeek(weeks.value))
const summary=computed(()=>props.payload?.summary||{})
watch(allRows,()=>{if(selected.value){selected.value=allRows.value.find(r=>r.name===selected.value.name)||null}})
watch([query,state,block],()=>{if(selected.value&&!rows.value.some(r=>r.name===selected.value.name))selected.value=null})
function open(row){if(row?.name)emit('open',row)}
function takeRow(event){selected.value=event.data||null}
const fmt=p=>p.value==null?'—':kg(p.value)
const columnDefs=[
  {field:'name',headerName:'Mã dự thu',minWidth:142,pinned:'left'},
  {field:'farm',headerName:'Vườn',minWidth:150},
  {field:'farm_block',headerName:'Lô',minWidth:125},
  {field:'crop_cycle',headerName:'Vụ',minWidth:128},
  {field:'period_start_date',headerName:'Từ ngày',minWidth:116},
  {field:'period_end_date',headerName:'Đến ngày',minWidth:116},
  {field:'expected_harvest_bunch_qty',headerName:'Buồng dự kiến',type:'numericColumn',minWidth:137,valueFormatter:fmt},
  {field:'gross_forecast_kg',headerName:'Dự thu (kg buồng)',type:'numericColumn',minWidth:157,valueFormatter:fmt},
  {field:'packed_forecast_kg',headerName:'Đóng gói dự kiến (kg)',type:'numericColumn',minWidth:185,valueFormatter:fmt},
  {field:'available_to_promise_kg',headerName:'Còn có thể giữ (kg)',type:'numericColumn',minWidth:169,valueFormatter:fmt},
  {field:'supply_state',headerName:'Trạng thái',minWidth:134,valueFormatter:p=>forecastStates[p.value]||p.value},
]
const defaultColDef={sortable:true,resizable:true,filter:false}
const showRows=computed(()=>tab.value==='list')
function create(){emit('create',{farm_block:block.value||undefined,period_start_date:props.payload?.from_date||undefined,period_end_date:props.payload?.to_date||undefined})}
</script>

<template>
  <section class="forecast-workspace" aria-label="Điều hành dự thu chuối">
    <div class="forecast-actions">
      <div class="forecast-tabs" role="tablist" aria-label="Cách xem dự thu">
        <button v-for="item in [{id:'weeks',text:'Theo tuần'},{id:'blocks',text:'Theo lô'},{id:'list',text:'Phiếu dự thu'}]" :key="item.id" type="button" role="tab" :aria-selected="tab===item.id" :class="{active:tab===item.id}" @click="tab=item.id">{{item.text}}</button>
      </div>
      <div class="forecast-main-actions">
        <UiButton variant="outline" type="button" :disabled="loading" @click="emit('reload')">Làm mới</UiButton>
        <UiButton v-if="canCreate" type="button" @click="create">+ Tạo dự thu</UiButton>
      </div>
    </div>

    <div class="forecast-metrics">
      <div class="forecast-metric"><span>Dự thu (kg buồng)</span><strong>{{kg(summary.gross_kg)}}</strong><small>{{summary.active_count||0}} bản đã phát hành</small></div>
      <div class="forecast-metric"><span>Dự kiến đóng gói (kg)</span><strong>{{kg(summary.packed_kg)}}</strong><small>Đã trừ các tỷ lệ hao hụt tính toán</small></div>
      <div class="forecast-metric"><span>Còn có thể giữ (kg)</span><strong>{{kg(summary.available_kg)}}</strong><small>Đã trừ lượng giữ cho đơn bán</small></div>
      <div class="forecast-metric"><span>Đã thu hoạch (kg buồng)</span><strong>{{kg(summary.harvested_gross_kg)}}</strong><small>{{props.payload?.actual_readable?'Phiếu thực tế đã xác nhận':'Không có quyền xem thu hoạch'}}</small></div>
      <div class="forecast-metric forecast-metric-alert"><span>Cần xử lý</span><strong>{{summary.draft_count||0}} nháp · {{summary.shortages||0}} thiếu</strong><small>Kiểm tra trước khi lập kế hoạch bán</small></div>
    </div>

    <div class="forecast-filterbar">
      <label>Lô<UiSelect v-model="block" aria-label="Lọc lô"><option value="">Tất cả lô</option><option v-for="value in blocks" :key="value" :value="value">{{value}}</option></UiSelect></label>
      <label>Trạng thái<UiSelect v-model="state" aria-label="Lọc trạng thái"><option value="">Tất cả</option><option v-for="(text,value) in forecastStates" :key="value" :value="value">{{text}}</option></UiSelect></label>
      <label class="forecast-search">Tìm nhanh<UiInput v-model="query" placeholder="Mã dự thu, lô, vụ…" aria-label="Tìm dự thu"/></label>
      <span class="forecast-row-count">{{rows.length}} / {{allRows.length}} phiếu</span>
      <UiButton variant="outline" type="button" @click="emit('plan')">Kế hoạch công việc ↗</UiButton>
      <UiButton variant="outline" type="button" @click="emit('reports')">Đối chiếu dự thu ↗</UiButton>
    </div>

    <p v-if="!allRows.length&&!loading" class="forecast-empty" role="status">Chưa có dự thu trong khoảng ngày và vườn đang chọn. Có thể tạo dự thu mới nếu được phân quyền.</p>
    <template v-else>
      <div v-if="tab==='weeks'" class="forecast-week-panel">
        <div class="forecast-week-head"><strong>Kế hoạch theo tuần</strong><span>Phiếu nhiều tuần được xếp một lần vào tuần bắt đầu trong khoảng lọc, không chia đều sản lượng.</span></div>
        <div class="forecast-week-scroll">
          <table class="forecast-week-table">
            <thead><tr><th>Tuần bắt đầu</th><th>Dự thu ngoài vườn (kg)</th><th>Đóng gói dự kiến (kg)</th><th>Đã thu (kg buồng)</th><th>Số dự thu</th></tr></thead>
            <tbody>
              <tr v-for="week in weeks" :key="week.week_start">
                <td class="forecast-no-wrap"><strong>{{week.week_start}}</strong><small>– {{week.week_end}}</small></td>
                <td><div class="forecast-meter"><div class="forecast-meter-fill forecast-meter-gross" :style="{width:percent(week.gross_kg,peak)+'%'}"/></div><b>{{kg(week.gross_kg)}}</b></td>
                <td><div class="forecast-meter"><div class="forecast-meter-fill" :style="{width:percent(week.packed_kg,peak)+'%'}"/></div><b>{{kg(week.packed_kg)}}</b></td>
                <td><div class="forecast-meter"><div class="forecast-meter-fill forecast-meter-actual" :style="{width:percent(week.actual_gross_kg,peak)+'%'}"/></div><b>{{kg(week.actual_gross_kg)}}</b></td>
                <td>{{week.active_count}}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="forecast-footnote">{{props.payload?.rule}} Sản lượng đã thu là kg buồng thực tế, <strong>không phải</strong> kg thành phẩm đóng gói; đây không phải phép so sánh chênh lệch trực tiếp.</p>
      </div>
      <div v-else-if="tab==='blocks'" class="forecast-week-panel">
        <div class="forecast-week-head"><strong>Phân bổ theo lô</strong><span>Chỉ cộng các bản đã phát hành; bấm lô để lọc phiếu.</span></div>
        <div class="forecast-week-scroll"><table class="forecast-week-table">
          <thead><tr><th>Lô</th><th>Dự thu</th><th>Buồng</th><th>Kg buồng</th><th>Kg đóng gói</th><th>Còn giữ được</th><th>Đã thu (kg buồng, theo phiếu)</th></tr></thead>
          <tbody>
            <tr v-for="item in groupRows" :key="item.key" class="forecast-clickable" tabindex="0" role="button" @click="block=item.farm_block;tab='list'" @keydown.enter="block=item.farm_block;tab='list'">
              <td><strong>{{item.farm_block}}</strong><small>{{item.farm}}</small></td><td>{{item.count}}</td><td>{{kg(item.bunches)}}</td><td>{{kg(item.gross)}}</td><td>{{kg(item.packed)}}</td><td>{{kg(item.available)}}</td><td>{{kg(item.actual)}}</td>
            </tr>
            <tr v-if="!groupRows.length"><td colspan="7">Không có dự thu đã phát hành phù hợp bộ lọc.</td></tr>
          </tbody>
        </table></div>
      </div>
      <div v-else class="forecast-grid-area">
        <div class="forecast-grid-shell">
          <AgGridVue class="forecast-grid" :theme="compactGridTheme" :locale-text="AG_GRID_LOCALE_VN"
            :row-data="rows" :column-defs="columnDefs" :default-col-def="defaultColDef"
            :dom-layout="rows.length<9?'autoHeight':'normal'" :row-selection="{mode:'singleRow',enableClickSelection:true,checkboxes:false}"
            @row-clicked="takeRow" @row-double-clicked="event=>open(event.data)"/>
        </div>
        <aside v-if="selected" class="forecast-inspector" aria-label="Chi tiết dự thu đã chọn">
          <div class="forecast-inspector-title"><strong>{{selected.name}}</strong><button type="button" aria-label="Đóng chi tiết" @click="selected=null">×</button></div>
          <p><span class="forecast-state" :class="'forecast-state-'+selected.supply_state">{{forecastStates[selected.supply_state]||selected.supply_state}}</span></p>
          <dl><dt>Vườn / Lô</dt><dd>{{selected.farm}} / {{selected.farm_block}}</dd><dt>Vụ</dt><dd>{{selected.crop_cycle}}</dd>
            <dt>Thời gian</dt><dd>{{selected.period_start_date}} → {{selected.period_end_date}}</dd>
            <dt>Buồng nguồn</dt><dd>{{kg(selected.net_source_bunch_qty)}} buồng</dd>
            <dt>Trọng lượng trung bình</dt><dd>{{kg(selected.avg_bunch_weight_kg)}} kg/buồng</dd>
            <dt>Dự kiến thu</dt><dd>{{kg(selected.gross_forecast_kg)}} kg buồng</dd>
            <dt>Thành phẩm dự kiến</dt><dd>{{kg(selected.packed_forecast_kg)}} kg</dd>
            <dt>Còn khả dụng</dt><dd>{{kg(selected.available_to_promise_kg)}} kg</dd>
            <dt>Đã thu theo phiếu</dt><dd>{{props.payload?.actual_readable?kg(selected.actual_gross_kg)+' kg buồng':'Không có quyền xem'}}</dd>
          </dl>
          <p v-if="selected.spans_weeks" class="forecast-footnote">Phiếu này trải qua nhiều tuần; trên lịch hiển thị ở tuần bắt đầu.</p>
          <p v-if="selected.availability_status==='Overcommitted'" class="forecast-warning">Đã giữ vượt nguồn cung có thể đáp ứng.</p>
          <UiButton block type="button" @click="open(selected)">Mở phiếu dự thu</UiButton>
          <UiButton v-if="selected.supply_state==='Released'&&canCreate" block variant="outline" type="button" @click="emit('revise',selected)">Tạo bản điều chỉnh</UiButton>
        </aside>
      </div>
    </template>
  </section>
</template>
