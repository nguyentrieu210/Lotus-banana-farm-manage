<script setup>
import {ref} from 'vue'
import LotusIcon from '../LotusIcon.vue'
import LotusMobileNetBar from '../LotusMobileNetBar.vue'
import {Button as UiButton} from '../ui/button'
import {Segmented} from '../ui/segmented'
import {NumberStepper} from '../ui/number-stepper'
import {Switch} from '../ui/switch'
import {StatTile} from '../ui/stat-tile'
import {LotCard,RibbonPicker} from '../agri'
import {todayLots,TODAY} from './sample-data.js'
// Điện thoại: the phone kit in device frames — 390 px light, the lot-entry sheet offline, the same screen outdoors,
// and 320 px to prove nothing overflows (spec 004, User Story 4, FR-023 to FR-028).
const tab=ref('today'),cut=ref(12),cancelled=ref(null),ribbon=ref('CAM'),outdoor=ref(true)
const nav=[['today','Hôm nay','clipboard'],['assign','Giao việc','users'],['report','Báo cáo','chart'],['check','Nghiệm thu','check-circle'],['me','Tôi','user-cog']]
const ribbons=[{code:'CAM',week:46,hint:'tuần này'},{code:'DEN',week:45},{code:'XANH_DUONG',week:44},{code:'TRANG',week:43}]
const frames=[{key:'light',title:'Báo cáo hôm nay',width:390,cls:''},{key:'outdoor',title:'Báo cáo hôm nay',width:390,cls:'lotus-outdoor-preview lotus-outdoor'},{key:'narrow',title:'Báo cáo hôm nay',width:320,cls:''}]
</script>
<template>
 <div class="sc-phones">
  <figure v-for="f in frames.slice(0,1)" :key="f.key" class="sc-phone-wrap"><div class="sc-phone" :style="{width:f.width+'px'}"><div class="sc-phone__screen" :class="f.cls">
   <header class="sc-phone__header"><span class="sc-phone__logo"><img :src="'/assets/lotus_farm/images/lotus-agritech-header-v2.png'" alt="Lotus Agritech"></span><strong>{{f.title}}</strong></header>
   <div class="sc-phone__body">
    <Segmented v-model="tab" label="Xem" block :options="[{value:'today',label:'Hôm nay'},{value:'sent',label:'Đã gửi',count:2},{value:'history',label:'Lịch sử'}]"/>
    <div class="sc-phone__meta"><span class="lotus-chip lotus-chip--bare">10/11/2026</span><span class="lotus-chip lotus-chip--bare">Tổ 01</span><span class="lotus-chip lotus-chip--info"><LotusIcon name="edit"/>1 lô chưa gửi</span></div>
    <LotCard v-for="lot in todayLots.slice(0,3)" :key="lot.code" :lot="lot" :today="TODAY" :max-ribbons="3"/>
    <UiButton size="lg" class="sc-phone__cta"><LotusIcon name="send"/>Gửi báo cáo ngày</UiButton>
   </div>
   <nav class="sc-tabbar" aria-label="Điều hướng mẫu"><button v-for="[k,label,icon] in nav" :key="k" type="button" :class="{'is-active':k==='today'}"><LotusIcon :name="icon"/><span>{{label}}</span></button></nav>
  </div></div><figcaption>390 px · sáng · thanh dưới có chữ</figcaption></figure>

  <figure class="sc-phone-wrap"><div class="sc-phone" style="width:390px"><div class="sc-phone__screen">
   <header class="sc-phone__header"><span class="sc-phone__logo"><img :src="'/assets/lotus_farm/images/lotus-agritech-header-v2.png'" alt=""></span><strong>Báo cáo hôm nay</strong></header>
   <LotusMobileNetBar :online="false" :queued="3"/>
   <div class="sc-phone__body sc-phone__body--dim" aria-hidden="true"><LotCard :lot="todayLots[0]" :today="TODAY" :interactive="false"/></div>
   <section class="sc-sheet" aria-label="Nhập lô A5">
    <span class="sc-sheet__handle" aria-hidden="true"/>
    <div class="sc-sheet__head"><strong>Lô A5 · 10/11/2026</strong><span class="lotus-chip lotus-chip--bare lotus-chip--sm">Khu A · 3,96 ha</span></div>
    <div class="sc-sheet__works"><span class="lotus-chip lotus-chip--primary lotus-chip--lg"><LotusIcon name="scissors"/>Cắt bắp</span><span class="lotus-chip lotus-chip--bare lotus-chip--lg">+ Chích bắp</span><span class="lotus-chip lotus-chip--bare lotus-chip--lg">+ Bao buồng</span><span class="lotus-chip lotus-chip--bare lotus-chip--lg">+ Hủy buồng</span></div>
    <label class="sc-label">Số buồng cắt bắp</label>
    <NumberStepper v-model="cut" label="Số buồng cắt bắp" unit="buồng" size="lg" block/>
    <label class="sc-label">Màu dây buộc</label>
    <RibbonPicker v-model="ribbon" :options="ribbons" label="Màu dây buộc"/>
    <label class="sc-label">Buồng hủy (để trống nếu không có)</label>
    <NumberStepper v-model="cancelled" label="Buồng hủy" unit="buồng" size="lg" block/>
    <div class="sc-sheet__foot"><UiButton variant="outline" size="lg">Hủy</UiButton><UiButton size="lg">Lưu lô này</UiButton></div>
   </section>
  </div></div><figcaption>Hộp nhập lô · mất mạng · số to, nút cộng trừ lớn</figcaption></figure>

  <figure v-for="f in frames.slice(1)" :key="f.key" class="sc-phone-wrap"><div class="sc-phone" :style="{width:f.width+'px'}"><div class="sc-phone__screen" :class="f.cls">
   <header class="sc-phone__header"><span class="sc-phone__logo"><img :src="'/assets/lotus_farm/images/lotus-agritech-header-v2.png'" alt=""></span><strong>{{f.title}}</strong></header>
   <div class="sc-phone__body">
    <div v-if="f.key==='outdoor'" class="sc-phone__setting"><Switch v-model="outdoor" label="Chế độ ngoài trời"/></div>
    <StatTile label="Lô đã nhập hôm nay" :value="2" unit="/ 6 lô" icon="clipboard" tone="info"/>
    <LotCard v-for="lot in todayLots.slice(3,5)" :key="lot.code" :lot="lot" :today="TODAY" :max-ribbons="2"/>
   </div>
   <nav class="sc-tabbar" aria-label="Điều hướng mẫu"><button v-for="[k,label,icon] in nav" :key="k" type="button" :class="{'is-active':k==='today'}"><LotusIcon :name="icon"/><span>{{label}}</span></button></nav>
  </div></div><figcaption>{{f.key==='outdoor'?'390 px · ngoài trời: chữ ≥ 7:1, vùng bấm 48 px':'320 px · không tràn ngang'}}</figcaption></figure>
 </div>
</template>
