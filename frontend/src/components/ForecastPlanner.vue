<script setup>
import {computed,ref,watch} from 'vue'
import {Button as UiButton} from './ui/button'
import '../forecast-calendar.css'

const props=defineProps({
  payload:{type:Object,default:()=>({})},
  loading:Boolean,
  canSettings:Boolean,
  canEditBlock:Boolean,
})
const emit=defineEmits(['reload','settings','edit-block'])
const search=ref('')
const year=ref('')
const selectedMonth=ref('')
const numbers=new Intl.NumberFormat('vi-VN',{maximumFractionDigits:1})
const ton=value=>numbers.format((Number(value)||0)/1000)
const bunches=value=>new Intl.NumberFormat('vi-VN',{maximumFractionDigits:0}).format(Number(value)||0)
const allMonths=computed(()=>props.payload?.months||[])
const years=computed(()=>[...new Set(allMonths.value.map(x=>x.month.slice(0,4)))])
watch(years,values=>{if(!values.includes(year.value))year.value=values[0]||''},{immediate:true})
const months=computed(()=>allMonths.value.filter(x=>x.month.startsWith(year.value)))
const maxGross=computed(()=>Math.max(1,...months.value.map(m=>Number(m.gross_kg)||0)))
const allRows=computed(()=>props.payload?.rows||[])
const rows=computed(()=>allRows.value.filter(r=>
 (!year.value||r.month.startsWith(year.value))
 &&(!selectedMonth.value||r.month===selectedMonth.value)
 &&(!search.value||[r.farm_block,r.block_name,r.cycle,r.source_label].some(x=>String(x||'').toLocaleLowerCase('vi').includes(search.value.toLocaleLowerCase('vi'))))
))
const yearTotal=computed(()=>months.value.reduce((sum,m)=>sum+(Number(m.gross_kg)||0),0))
const issueCount=computed(()=>props.payload?.issues?.length||0)
const confidence=r=>r?.confidence||'—'
const monthName=m=>String(Number(m.slice(5)))+'/ '+m.slice(0,4)
function pickMonth(key){selectedMonth.value=selectedMonth.value===key?'':key}
</script>

<template>
  <section class="calendar-board" aria-label="Kế hoạch dự thu chuối 36 tháng">
    <div class="calendar-head">
      <div>
        <h2>Dự thu 3 năm</h2>
        <p>Tự tính theo ngày trồng → chọn chồi → trổ buồng → cắt bắp. Có số liệu mới thì ưu tiên nguồn sát thu hoạch hơn.</p>
      </div>
      <div class="calendar-buttons">
        <UiButton v-if="canSettings" variant="outline" type="button" @click="emit('settings',null)">Thiết lập hệ số</UiButton>
        <UiButton variant="outline" type="button" :disabled="loading" @click="emit('reload')">Làm mới</UiButton>
      </div>
    </div>
    <div class="calendar-kpis">
      <article><small>Tổng dự thu 36 tháng</small><strong>{{ton(payload.summary?.gross_kg)}} <em>tấn buồng</em></strong><span>Ước tính, chưa phải sản lượng chốt</span></article>
      <article><small>Thành phẩm dự kiến</small><strong>{{ton(payload.summary?.packed_kg)}} <em>tấn</em></strong><span>Đã áp dụng hệ số chất lượng và đóng gói</span></article>
      <article><small>Lô đã có dự tính</small><strong>{{payload.summary?.ready_blocks||0}} / {{payload.summary?.blocks||0}}</strong><span>Chỉ dùng lô có dữ liệu và bộ hệ số hợp lệ</span></article>
      <article><small>Cần kiểm tra</small><strong>{{issueCount}}</strong><span>Thiếu thông số hoặc chưa rõ đợt cây</span></article>
    </div>
    <div class="calendar-toolbar">
      <div class="calendar-years" role="tablist" aria-label="Chọn năm">
        <button v-for="y in years" :key="y" :aria-selected="year===y" role="tab" type="button" :class="{active:year===y}" @click="year=y;selectedMonth=''">{{y}}</button>
      </div>
      <label>Tìm lô <input v-model="search" type="search" placeholder="Tên lô, số vụ, nguồn tính…" /></label>
      <span class="calendar-total">Năm {{year}}: <b>{{ton(yearTotal)}} tấn buồng</b></span>
    </div>
    <section class="calendar-panel">
      <div class="calendar-panel-title"><strong>Sản lượng theo tháng</strong><span>Chọn tháng để xem các lô dự kiến thu</span></div>
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
        <table class="calendar-table">
          <thead><tr><th>Lô</th><th>Vụ</th><th>Ngày dự thu</th><th>Nguồn tính</th><th>Độ tin cậy</th><th>Buồng</th><th>Tấn buồng</th><th>Tấn thành phẩm</th></tr></thead>
          <tbody>
            <tr v-for="(r,i) in rows" :key="r.farm_block+'-'+r.cycle+'-'+r.month+'-'+r.source+'-'+i">
              <td><strong>{{r.block_name}}</strong><small>{{r.farm}}</small></td>
              <td>{{r.cycle_no}}</td>
              <td>{{r.expected_date}}</td>
              <td>{{r.source_label}}<small v-if="r.projected">Chỉ là dự phóng, chưa chốt</small></td>
              <td><span class="calendar-confidence" :class="r.source">{{confidence(r)}}</span></td>
              <td>{{bunches(r.bunches)}}</td>
              <td>{{ton(r.gross_kg)}}</td>
              <td>{{ton(r.packed_kg)}}</td>
            </tr>
            <tr v-if="!rows.length"><td colspan="8" class="calendar-hint">Chưa có số dự thu đủ căn cứ. Hãy xem mục Cần bổ sung dữ liệu ở dưới.</td></tr>
          </tbody>
        </table>
      </div>
      <p class="calendar-note">Không cộng các công đoạn trùng một đợt. Các đợt chưa đủ thông tin liên kết sẽ được báo cần đối chiếu; số tự dự phóng không dùng để cam kết bán hàng.</p>
    </section>
    <details v-if="issueCount" class="calendar-issues">
      <summary>Cần bổ sung dữ liệu ({{issueCount}})</summary>
      <div class="calendar-issues-list">
        <div v-for="(issue,i) in payload.issues" :key="i"><b>{{issue.block_name||issue.farm_block}}:</b> {{issue.message}} <button v-if="canEditBlock" class="calendar-issue-edit" type="button" @click="emit('edit-block',issue.farm_block)">Sửa thông tin lô</button></div>
      </div>
      <p v-if="canSettings">Bấm <b>Thiết lập hệ số</b> để thêm số ngày từ trồng đến thu và chu kỳ vụ chồi, sau đó phát hành bộ hệ số theo quy trình duyệt.</p>
    </details>
    <p class="calendar-footnote">Khoảng kế hoạch: {{payload.from_date||'—'}} đến {{payload.to_date||'—'}}. {{payload.note}}</p>
  </section>
</template>
