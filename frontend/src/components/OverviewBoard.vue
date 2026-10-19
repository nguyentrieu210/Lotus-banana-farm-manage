<script setup>
import {computed} from 'vue'
import LotusChart from './LotusChart.vue'
import {stateLabel} from '../labels'
const props=defineProps({charts:Object})
const c=computed(()=>props.charts||{})
const sum=(rows,key)=>(rows||[]).reduce((t,r)=>t+Number(r[key]||0),0)
const n=v=>v==null?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:1})
const cards=computed(()=>[
 ['Diện tích chăm sóc',c.value.land?.area_ha,'ha'],['Số cây',c.value.land?.trees,'cây'],
 ['Công thực tế',c.value.work?.allowed?sum(c.value.work.days,'actual_workdays'):null,'công'],
 ['Thu hoạch',c.value.harvest?.allowed?sum(c.value.harvest.harvest,'gross_weight_kg'):null,'kg'],
 ['Thành phẩm',c.value.harvest?.packout?sum(c.value.harvest.packout,'finished_kg'):null,'kg'],
 ['Nhân sự đang làm',c.value.people?.active,'người'],['Đơn mua',c.value.buying?.count,'đơn'],['Đơn bán',c.value.sales?.count,'đơn'],
])
</script>
<template><div class="overview-board">
 <div class="lotus-stat-row"><div v-for="[label,value,unit] in cards" :key="label" class="lotus-stat"><span>{{label}}</span><strong>{{n(value)}}</strong><small>{{unit}}</small></div></div>
 <div class="lotus-chart-grid">
  <LotusChart v-if="c.land?.allowed" title="Diện tích và phân khu" :categories="(c.land.zones||[]).map(z=>'Khu '+z.zone)" :series="[{name:'Diện tích',data:(c.land.zones||[]).map(z=>z.area_ha)}]" unit="ha" :decimals="1"/>
  <LotusChart v-if="c.land?.allowed" title="Số cây theo khu" :categories="(c.land.zones||[]).map(z=>'Khu '+z.zone)" :series="[{name:'Số cây',data:(c.land.zones||[]).map(z=>z.trees)}]" unit="cây"/>
  <LotusChart v-if="c.work?.allowed&&!c.work.note" kind="line" title="Tiến độ công việc" :categories="(c.work.days||[]).map(d=>d.date.slice(5))" :series="[{name:'Hoàn thành',data:(c.work.days||[]).map(d=>d.completion_percent)}]" unit="%"/>
  <LotusChart v-if="c.harvest?.allowed" title="Thu hoạch và sản lượng bán được" :categories="(c.harvest.harvest||[]).map(w=>w.week.slice(5))" :series="[{name:'Thu hoạch',data:(c.harvest.harvest||[]).map(w=>w.gross_weight_kg)},{name:'Bán được',data:(c.harvest.harvest||[]).map(w=>w.saleable_weight_kg)}]" unit="kg"/>
  <LotusChart v-if="c.losses?.allowed" kind="hbar" title="Tổn thất theo nguyên nhân" :categories="(c.losses.reasons||[]).map(r=>r.label)" :series="[{name:'Buồng hủy',data:(c.losses.reasons||[]).map(r=>r.value)}]" unit="buồng"/>
  <LotusChart v-if="c.people?.allowed&&!c.people.note" title="Chấm công nhân sự" :categories="(c.people.attendance||[]).map(r=>stateLabel(r.status))" :series="[{name:'Lượt công',data:(c.people.attendance||[]).map(r=>r.count)}]" unit="lượt"/>
  <LotusChart v-if="c.buying?.allowed&&!c.buying.note" title="Tình trạng đơn mua" :categories="(c.buying.statuses||[]).map(r=>stateLabel(r.status))" :series="[{name:'Đơn mua',data:(c.buying.statuses||[]).map(r=>r.count)}]" unit="đơn"/>
  <LotusChart v-if="c.sales?.allowed&&!c.sales.note" title="Tình trạng đơn bán" :categories="(c.sales.statuses||[]).map(r=>stateLabel(r.status))" :series="[{name:'Đơn bán',data:(c.sales.statuses||[]).map(r=>r.count)}]" unit="đơn"/>
 </div>
 <p v-for="key in ['work','harvest','stock','people','buying','sales'].filter(k=>c[k]?.note)" :key="key" class="muted">{{c[key].note}}</p>
</div></template>
