<script setup>
import {computed} from 'vue'
import LotusChart from './LotusChart.vue'
import {StatTile} from './ui/stat-tile'
import {stateLabel} from '../labels'
import {formatMonthShort} from '../format'
const props=defineProps({charts:Object})
const c=computed(()=>props.charts||{})
const sum=(rows,key)=>(rows||[]).reduce((t,r)=>t+Number(r[key]||0),0)
const cards=computed(()=>[
 ['Diện tích chăm sóc',c.value.land?.area_ha,'ha'],['Số cây',c.value.land?.trees,'cây'],
 ['Công thực tế',c.value.work?.days?sum(c.value.work.days,'workdays'):null,'công'],
 ['Thu hoạch',c.value.harvest?.allowed?sum(c.value.harvest.weeks,'weight_kg'):null,'kg'],
 ['Thành phẩm',c.value.packout?.weeks?sum(c.value.packout.weeks,'finished_kg'):null,'kg'],
 ['Dự thu '+(c.value.forecast?.horizon_weeks||13)+' tuần tới',c.value.forecast?.allowed?c.value.forecast.bunches:null,'buồng'],
 ['Nhân sự đang làm · theo vườn',c.value.people?.active,'người'],['Đơn mua · công ty',c.value.buying?.count,'đơn'],['Đơn bán · công ty',c.value.sales?.count,'đơn'],
])
</script>
<template><div class="overview-board">
 <div class="lotus-stat-row"><StatTile v-for="[label,value,unit] in cards" :key="label" :label="label" :value="value" :unit="unit" :digits="1"/></div>
 <div class="lotus-chart-grid">
  <LotusChart v-if="c.land?.allowed" title="Diện tích và phân khu" :categories="(c.land.zones||[]).map(z=>'Khu '+z.zone)" :series="[{name:'Diện tích',data:(c.land.zones||[]).map(z=>z.area_ha)}]" unit="ha" :decimals="1"/>
  <LotusChart v-if="c.land?.allowed" title="Số cây theo khu" :categories="(c.land.zones||[]).map(z=>'Khu '+z.zone)" :series="[{name:'Số cây',data:(c.land.zones||[]).map(z=>z.trees)}]" unit="cây"/>
  <LotusChart v-if="c.work?.allowed&&!c.work.note" title="Công thực tế theo ngày" :categories="(c.work.days||[]).map(d=>d.date.slice(5))" :series="[{name:'Công thực tế',data:(c.work.days||[]).map(d=>d.workdays)}]" unit="công" :decimals="1"/>
  <LotusChart v-if="c.harvest?.allowed" title="Thu hoạch theo tuần" :categories="(c.harvest.weeks||[]).map(w=>w.week.slice(5))" :series="[{name:'Thu hoạch',data:(c.harvest.weeks||[]).map(w=>w.weight_kg)}]" unit="kg"/>
  <LotusChart v-if="c.losses?.allowed" kind="hbar" title="Tổn thất theo nguyên nhân" :categories="(c.losses.reasons||[]).map(r=>r.label)" :series="[{name:'Buồng hủy',data:(c.losses.reasons||[]).map(r=>r.value)}]" unit="buồng"/>
  <LotusChart v-if="c.forecast?.allowed" title="Dự thu theo tháng" :categories="(c.forecast.months||[]).map(m=>formatMonthShort(m.month))" :series="[{name:'Dự thu',data:(c.forecast.months||[]).map(m=>m.bunches)}]" unit="buồng"/>
  <LotusChart v-if="c.people?.allowed&&!c.people.note" title="Chấm công nhân sự · theo vườn" :categories="(c.people.attendance||[]).map(r=>stateLabel(r.status))" :series="[{name:'Lượt công',data:(c.people.attendance||[]).map(r=>r.count)}]" unit="lượt"/>
  <LotusChart v-if="c.buying?.allowed&&!c.buying.note" title="Tình trạng đơn mua · công ty" :categories="(c.buying.statuses||[]).map(r=>stateLabel(r.status))" :series="[{name:'Đơn mua',data:(c.buying.statuses||[]).map(r=>r.count)}]" unit="đơn"/>
  <LotusChart v-if="c.sales?.allowed&&!c.sales.note" title="Tình trạng đơn bán · công ty" :categories="(c.sales.statuses||[]).map(r=>stateLabel(r.status))" :series="[{name:'Đơn bán',data:(c.sales.statuses||[]).map(r=>r.count)}]" unit="đơn"/>
 </div>
 <p v-for="key in ['work','packout','stock','people','buying','sales'].filter(k=>c[k]?.note)" :key="key" class="muted">{{c[key].note}}</p>
</div></template>
