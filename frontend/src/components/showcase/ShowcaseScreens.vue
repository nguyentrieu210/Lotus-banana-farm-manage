<script setup>
import {computed,ref} from 'vue'
import LotusIcon from '../LotusIcon.vue'
import ListPage from '../ListPage.vue'
import DataTable from '../DataTable.vue'
import {Button as UiButton} from '../ui/button'
import {Input as UiInput} from '../ui/input'
import {Select as UiSelect} from '../ui/select'
import {FormField} from '../ui/form-field'
import {DatePicker} from '../ui/date-picker'
import {Banner} from '../ui/banner'
import {StatTile} from '../ui/stat-tile'
import {StatusChip} from '../ui/status-chip'
import {Steps} from '../ui/steps'
import {LotGrid,LotCard,ForecastWeekChart,WeekChip} from '../agri'
import {LOT_METRICS} from '../../lot-states.js'
import {dueCol,moneyCol,qtyCol,statusCol,progressCol} from '../../grid-columns.js'
import {stateLabel} from '../../labels.js'
import {purchaseRows,lots,todayLots,forecastWeeks,TODAY} from './sample-data.js'
// Mẫu màn hình: whole screens built only from the kit — the owner's layout rules applied (spec 004, FR-021):
// create first on the left, row 2 = search and filters, no decorative title over the table, entry in a modal, save on the right.
const search=ref(''),status=ref(''),date=ref('2026-11-10')
const columns=[{field:'name',headerName:'Số chứng từ',minWidth:128},dueCol('due','Hạn giao',{today:TODAY}),{field:'supplier',headerName:'Nhà cung cấp',minWidth:170,flex:1.5},qtyCol('qty','Số lượng',{unitField:'uom',digits:0}),moneyCol('amount','Thành tiền',{minWidth:130}),progressCol('received','Đã nhận',{maxField:'qty',tone:'success',minWidth:120}),statusCol('status','Trạng thái',{labelOf:v=>stateLabel(v),minWidth:136})]
const rows=computed(()=>purchaseRows.filter(r=>(!status.value||r.status===status.value)&&(!search.value||(r.name+r.supplier+r.item).toLowerCase().includes(search.value.toLowerCase()))))
const nav=[['Tổng quan','chart',[]],['Việc hằng ngày','clipboard',['Hôm nay','Màu dây & thu hoạch','Giao việc theo vòng','Nghiệm thu','Xưởng']],['Dự thu','trending',[]],['Vườn & lô','sprout',[]],['Kho','warehouse',[]],['Mua hàng','cart',['Đề xuất mua','Đơn mua','Nhận hàng','Hóa đơn NCC','Công nợ']],['Tài chính – Kế toán','wallet',[]],['Nhân sự','users',[]]]
const lines=[{item:'Phân NPK 16-16-8',qty:120,uom:'bao',price:385000},{item:'Kali clorua',qty:60,uom:'bao',price:520000},{item:'Dây buộc màu',qty:35,uom:'cuộn',price:96000}]
const lineColumns=[{field:'item',headerName:'Vật tư',flex:2,minWidth:130},qtyCol('qty','Số lượng',{unitField:'uom',digits:0,minWidth:96}),moneyCol('total','Thành tiền',{minWidth:124})]
const lineRows=lines.map(l=>({...l,total:l.qty*l.price}))
const reportLots=lots.map(l=>({code:l.code,zone:l.zone,state:l.report}))
</script>
<template>
 <div class="sc-stack">
  <figure class="sc-app" style="margin:0">
   <aside class="sc-app__side">
    <div class="sc-app__brand"><img :src="'/assets/lotus_farm/images/lotus-agritech-header-v2.png'" alt="Lotus Agritech"></div>
    <nav class="sc-app__nav" aria-label="Điều hướng mẫu"><div v-for="[group,icon,items] in nav" :key="group" class="sc-app__group" :class="{'is-open':items.length}"><span class="sc-app__group-head" :class="{'is-current':group==='Mua hàng'}"><LotusIcon :name="icon"/>{{group}}<LotusIcon name="chevron-down" class="sc-app__chev"/></span><span v-for="item in items" :key="item" class="sc-app__item" :class="{'is-active':item==='Đơn mua'}">{{item}}</span></div></nav>
   </aside>
   <div class="sc-app__main">
    <header class="sc-app__top"><LotusIcon name="menu"/><LotusIcon name="home"/><strong>Đơn mua</strong><span class="sc-app__farm"><LotusIcon name="sprout"/>Vườn mẫu 1<LotusIcon name="chevron-down"/></span><span class="sc-app__search"><LotusIcon name="search"/>Tìm nhanh…<kbd>Ctrl K</kbd></span><span class="sc-app__spacer"/><LotusIcon name="moon"/><span class="sc-app__user"><span class="lotus-avatar lotus-avatar--sm" data-hue="1">TH</span>Trần Thị Hồng</span></header>
    <div class="sc-app__content">
     <ListPage v-model:search="search" :rows="rows" :columns="columns" row-key="name" storage-key="showcase-screen-po" :fill="-1" :page-size="20" search-placeholder="Tìm số, nhà cung cấp, vật tư…" interactive>
      <template #actions><UiButton><LotusIcon name="plus"/>Tạo đơn mua</UiButton><UiButton variant="outline"><LotusIcon name="upload"/>Nhập từ Excel</UiButton></template>
      <template #filters><UiSelect v-model="status" aria-label="Trạng thái"><option value="">Mọi trạng thái</option><option value="Pending">Chờ duyệt</option><option value="To Sign">Chờ ký</option><option value="To Receive">Chờ nhận hàng</option><option value="Completed">Đã hoàn thành</option></UiSelect><DatePicker v-model="date" label="Từ ngày"/></template>
     </ListPage>
    </div>
   </div>
   <figcaption class="lotus-sr-only">Khung máy tính mẫu: thanh bên, thanh trên, trang danh sách đơn mua</figcaption>
  </figure>

  <div class="sc-grid-2 sc-grid-2--wide">
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Hôm nay của đội khu A</h3><WeekChip date="2026-11-10" :today="TODAY" long/></header>
    <div class="lotus-card__body sc-stack">
     <div class="lotus-stat-row"><StatTile label="Lô đã báo cáo" :value="38" unit="/ 64 lô" icon="clipboard" tone="info" :delta="6" delta-label="so với giờ này hôm qua"/><StatTile label="Buồng thu hôm nay" :value="1210" unit="buồng" icon="bunch" tone="success"/><StatTile label="Lô cách ly" :value="5" unit="lô" icon="shield" tone="danger"/></div>
     <LotGrid :lots="reportLots" :states="LOT_METRICS.report.states" label="Báo cáo hôm nay theo lô"/>
     <div class="lotus-lotcards"><LotCard v-for="lot in todayLots.slice(0,3)" :key="lot.code" :lot="lot" :today="TODAY"/></div>
    </div>
   </article>
   <div class="sc-modal-demo">
    <section class="sc-modal" aria-label="Hộp nhập mẫu">
     <header class="sc-modal__head"><h3>Đơn mua PO-2026-00118</h3><StatusChip status="To Sign" label="Chờ kế toán ký" size="sm"/><UiButton variant="outline" size="sm"><LotusIcon name="x"/>Đóng</UiButton></header>
     <div class="sc-modal__body">
      <Steps :steps="[{label:'Lập',state:'done',meta:'Thư'},{label:'Trưởng phòng',state:'done',meta:'Hồng'},{label:'Kế toán',state:'current'},{label:'Giám đốc',state:'waiting'}]"/>
      <div class="sc-form">
       <FormField label="Nhà cung cấp" required v-slot="field"><UiInput v-bind="field" model-value="Đại lý Phân bón Minh Phát"/></FormField>
       <FormField label="Ngày giao" v-slot="field"><DatePicker v-bind="field" v-model="date"/></FormField>
       <FormField label="Kho nhận" required error="Chọn kho nhận trước khi gửi duyệt." v-slot="field"><UiSelect v-bind="field" model-value=""><option value="">Chọn kho…</option><option>Kho tổng</option></UiSelect></FormField>
       <FormField label="Số hóa đơn" hint="Nhập đúng như trên hóa đơn giấy" v-slot="field"><UiInput v-bind="field" placeholder="0001234"/></FormField>
      </div>
      <DataTable :rows="lineRows" :columns="lineColumns" storage-key="showcase-lines" :paginate="false" :exportable="false" :columns-menu="false"/>
      <Banner tone="warning" title="Giá Kali cao hơn lần mua trước 6%">Ghi lý do ở phần ghi chú trước khi gửi duyệt.</Banner>
     </div>
     <footer class="sc-modal__foot"><UiButton variant="destructive"><LotusIcon name="ban"/>Hủy đơn</UiButton><span class="sc-app__spacer"/><UiButton variant="outline">Lưu nháp</UiButton><UiButton><LotusIcon name="send"/>Gửi duyệt</UiButton></footer>
    </section>
   </div>
  </div>
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Dự thu toàn vườn, 14 tuần</h3><span class="lotus-sample">Dữ liệu mẫu</span></header><div class="lotus-card__body"><ForecastWeekChart :weeks="forecastWeeks" :today="TODAY" :height="260"/></div></article>
 </div>
</template>
