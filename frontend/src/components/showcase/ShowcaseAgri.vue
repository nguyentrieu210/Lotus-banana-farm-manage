<script setup>
import {computed,ref} from 'vue'
import {StatTile} from '../ui/stat-tile'
import {Segmented} from '../ui/segmented'
import {StatusChip} from '../ui/status-chip'
import {LotGrid,LotCard,RibbonChip,RibbonLegend,WeekChip,WeekStrip,DueMeter,QuarantineBadge,ForecastWeekChart,AgeHistogram,ZoneChip,MapLegend,ShiftCard,CrewChip,RibbonBatchCard} from '../agri'
import {LOT_METRICS} from '../../lot-states.js'
import {weekKey} from '../../agri-format.js'
import {lots,ribbonBatches,forecastWeeks,ageBins,todayLots,careRounds,shifts,TODAY} from './sample-data.js'
// Nông nghiệp: the agritech pack on sample data — 64 lots, 12 ribbon weeks, 14 forecast weeks (spec 004, User Story 5).
const metric=ref('care')
const picked=ref('')
const week=ref('2026-W46')
const gridLots=computed(()=>lots.map(l=>({code:l.code,zone:l.zone,state:l[metric.value]})))
const metricOptions=Object.entries(LOT_METRICS).map(([value,m])=>({value,label:m.label}))
const harvestWeeks=forecastWeeks.filter(w=>w.week>=45&&w.week<=48).map(weekKey)
const ribbonsByWeek=Object.fromEntries(ribbonBatches.map(b=>[weekKey({year:2026,week:b.week}),[b.code]]))
const forecastByWeek=Object.fromEntries(forecastWeeks.map(w=>[weekKey(w),w.forecast]))
const counts=computed(()=>{const c={};for(const l of lots)c[l.care]=(c[l.care]||0)+1;return c})
const zoneLegend=[{label:'Khu A',colour:'var(--lotus-map-zone-a)',count:13},{label:'Khu B',colour:'var(--lotus-map-zone-b)',count:13},{label:'Khu C',colour:'var(--lotus-map-zone-c)',count:13},{label:'Khu D',colour:'var(--lotus-map-zone-d)',count:13},{label:'Khu E',colour:'var(--lotus-map-zone-e)',count:12}]
const ripe=ribbonBatches.map(b=>({...b,ripe:b.age>=9&&b.age<=11}))
</script>
<template>
 <div class="sc-stack">
  <div class="lotus-stat-row">
   <StatTile label="Buồng thu tuần 46" :value="6640" unit="buồng" icon="bunch" tone="success" :delta="120" delta-label="so với tuần 45"/>
   <StatTile label="Dự thu tuần 47" :value="7350" unit="buồng" icon="trending" tone="info" hint="Khoảng 6.762 – 7.865"/>
   <StatTile label="Lô quá hạn chăm sóc" :value="counts.overdue||0" unit="lô" icon="alert" tone="danger" :delta="2" good-when="down" delta-label="so với hôm qua"/>
   <StatTile label="Còn trên cây" :value="1957" unit="buồng" icon="leaf" tone="primary" hint="10 đợt màu dây"/>
   <StatTile label="Tỉ lệ buồng/thùng" :value="null" icon="package" missing="Chưa có ca đóng gói nào chốt hôm nay"/>
  </div>
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Cả vườn trong một lần nhìn</h3><Segmented v-model="metric" label="Tô màu lô theo" :options="metricOptions"/></header>
   <div class="lotus-card__body sc-split">
    <LotGrid v-model="picked" :lots="gridLots" :states="LOT_METRICS[metric].states" :label="'Lô theo '+LOT_METRICS[metric].label"/>
    <aside class="sc-stack-sm">
     <MapLegend title="Khu của vườn" :items="zoneLegend"/>
     <MapLegend title="Năng suất (tấn/ha)" :scale="['var(--lotus-seq-1)','var(--lotus-seq-2)','var(--lotus-seq-3)','var(--lotus-seq-4)','var(--lotus-seq-5)','var(--lotus-seq-6)','var(--lotus-seq-7)']" :ends="['35','60']"/>
     <div class="sc-row"><ZoneChip zone="A"/><ZoneChip zone="B"/><ZoneChip zone="C"/><ZoneChip zone="D"/><ZoneChip zone="E"/></div>
     <p v-if="picked" class="sc-note">Đã chọn lô <b>{{picked}}</b>: bấm một ô lô thì mở chi tiết lô.</p>
    </aside>
   </div>
  </article>
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Thẻ lô: hôm nay của tổ</h3><span class="lotus-sample">Dữ liệu mẫu</span></header>
   <div class="lotus-card__body lotus-lotcards"><LotCard v-for="lot in todayLots" :key="lot.code" :lot="lot" :today="TODAY"/></div>
  </article>
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Bảng màu dây</h3><RibbonLegend :items="ribbonBatches.slice(0,7).map(b=>({code:b.code,count:b.left}))"/></header>
   <div class="lotus-card__body lotus-batches"><RibbonBatchCard v-for="b in ripe" :key="b.code+b.week" :batch="b" :today="TODAY" interactive/></div>
  </article>
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Tuần: màu dây đã cắt, tuần thu, dự thu</h3><span class="sc-row"><WeekChip date="2026-11-10" :today="TODAY" long/><WeekChip :year="2026" :week="47" harvest/><WeekChip :year="2026" :week="53"/></span></header>
   <div class="lotus-card__body"><WeekStrip v-model="week" :today="TODAY" :before="11" :after="7" :harvest="harvestWeeks" :ribbons="ribbonsByWeek" :values="forecastByWeek" unit="buồng" label="Tuần dự thu"/></div>
  </article>
  <div class="sc-grid-2">
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Dự thu và thực tế theo tuần</h3></header><div class="lotus-card__body"><ForecastWeekChart :weeks="forecastWeeks" :today="TODAY"/></div></article>
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Buồng trên cây theo tuổi</h3></header><div class="lotus-card__body"><AgeHistogram :bins="ageBins"/></div></article>
  </div>
  <div class="sc-grid-3">
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Vòng chăm sóc đến hạn</h3></header>
    <div class="lotus-card__body sc-stack-sm"><div v-for="r in careRounds" :key="r.lot+r.work" class="sc-due-row"><span class="sc-due-row__lot">Lô {{r.lot}}</span><DueMeter :due="r.due" :today="TODAY" :cycle="r.cycle" :label="r.work"/></div></div>
   </article>
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Cách ly, tổ, màu dây</h3></header>
    <div class="lotus-card__body sc-stack-sm">
     <QuarantineBadge until="2026-11-14" :today="TODAY"/><QuarantineBadge until="2026-11-10" :today="TODAY"/>
     <div class="sc-row"><CrewChip name="Lê Văn Bình" team="Tổ 01 · Đội khu A"/><CrewChip name="Võ Thị Lan" team="Tổ 05 · Đội khu D"/></div>
     <div class="sc-row"><RibbonChip code="CAM" :week="40" :count="12"/><RibbonChip code="TRANG" :week="44" :count="6"/><RibbonChip code="DEN" :week="41" :count="19"/><RibbonChip code="XANH_LA_DO" :week="37" :count="233"/></div>
     <div class="sc-row"><StatusChip status="Quarantine" label="Đang cách ly"/><StatusChip status="Due" label="Đến hạn cắt lá"/><StatusChip status="Overdue" label="Quá hạn 3 ngày"/></div>
    </div>
   </article>
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Ca xưởng đóng gói</h3></header>
    <div class="lotus-card__body sc-stack-sm"><ShiftCard v-for="s in shifts" :key="s.date+s.name" :shift="s"/></div>
   </article>
  </div>
 </div>
</template>
