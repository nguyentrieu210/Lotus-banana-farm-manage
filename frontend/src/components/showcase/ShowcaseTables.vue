<script setup>
import DataTable from '../DataTable.vue'
import {numberCol,moneyCol,qtyCol,dateCol,dueCol,statusCol,progressCol,ribbonCol,personCol,deltaCol} from '../../grid-columns.js'
import {purchaseRows,harvestRows,TODAY} from './sample-data.js'
import {stateLabel} from '../../labels.js'
// Bảng: the shared DataTable with typed columns (spec 004, User Story 2, FR-014). Same component as every screen.
const purchaseColumns=[
 {field:'name',headerName:'Số chứng từ',minWidth:140,pinned:'left'},
 dateCol('date','Ngày'),
 dueCol('due','Hạn giao',{today:TODAY}),
 {field:'supplier',headerName:'Nhà cung cấp',minWidth:220,flex:1.6},
 {field:'item',headerName:'Vật tư',minWidth:150},
 qtyCol('qty','Số lượng',{unitField:'uom',digits:0}),
 moneyCol('amount','Thành tiền',{minWidth:150}),
 progressCol('received','Đã nhận',{maxField:'qty',tone:'success'}),
 statusCol('status','Trạng thái',{labelOf:v=>stateLabel(v)}),
 personCol('owner','Người lập',{teamField:'team'}),
]
const harvestColumns=[
 {field:'lot',headerName:'Lô',minWidth:80,pinned:'left'},
 ribbonCol('ribbon','Màu dây',{weekField:'week'}),
 numberCol('cut','Cắt bắp',{unit:'buồng'}),
 numberCol('harvested','Đã thu',{unit:'buồng'}),
 numberCol('left','Còn trên cây',{unit:'buồng'}),
 numberCol('kg','Khối lượng',{unit:'kg'}),
 deltaCol('delta','Lệch dự thu',{unit:'buồng'}),
 personCol('lead','Tổ trưởng',{teamField:'crew'}),
 statusCol('status','Trạng thái',{labelOf:v=>v==='Quarantine'?'Đang cách ly':stateLabel(v)}),
]
const harvest=harvestRows.map((r,i)=>({...r,delta:[12,-31,0,null,-8][i]}))
</script>
<template>
 <div class="sc-stack">
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Đơn mua: số đều cột, chip trạng thái, tiến độ, hạn quá</h3><span class="lotus-sample">Dữ liệu mẫu</span></header>
   <div class="lotus-card__body"><DataTable :rows="purchaseRows" :columns="purchaseColumns" row-key="name" storage-key="showcase-purchase" :page-size="10" export-title="Đơn mua mẫu"/></div>
  </article>
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Thu hoạch theo lô: màu dây, tổ trưởng, lệch dự thu</h3><span class="lotus-sample">Dữ liệu mẫu</span></header>
   <div class="lotus-card__body"><DataTable :rows="harvest" :columns="harvestColumns" row-key="lot" storage-key="showcase-harvest" :paginate="false"/></div>
  </article>
  <div class="sc-grid-2">
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Bảng trống</h3></header><div class="lotus-card__body"><DataTable :rows="[]" :columns="harvestColumns" storage-key="showcase-empty" empty="Chưa có thu hoạch trong tuần này." :exportable="false" :columns-menu="false"/></div></article>
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Bảng đang tải</h3></header><div class="lotus-card__body"><DataTable :rows="[]" :columns="harvestColumns" storage-key="showcase-loading" loading :exportable="false" :columns-menu="false"/></div></article>
  </div>
 </div>
</template>
