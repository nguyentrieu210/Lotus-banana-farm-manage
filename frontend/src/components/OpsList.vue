<script setup>
import {Button as UiButton} from './ui/button'
import {computed,ref} from 'vue'
import ExcelHeader from './ExcelHeader.vue'
import {compactGridTheme as theme} from '../grid-theme'
import {AG_GRID_LOCALE_VN} from '@ag-grid-community/locale'
import {AgGridVue} from 'ag-grid-vue3'
import {AllCommunityModule,ModuleRegistry,themeQuartz} from 'ag-grid-community'
import {fmt} from '../domain'
import {label,stateLabel} from '../labels'

ModuleRegistry.registerModules([AllCommunityModule])
const props=defineProps({
  rows:{type:Array,default:()=>[]},
  columns:{type:Array,default:()=>[]},
  loading:{type:Boolean,default:false},filterValues:Object,serverFilters:{type:Object,default:()=>({})},
})
const emit=defineEmits(['open','filter'])
const labels={name:'Phiếu',docstatus:'Trạng thái',farm:'Nông trường',farm_block:'Lô',farm_plot:'Thửa',crop_cycle:'Vụ',posting_date:'Ngày',harvest_date:'Ngày thu',received_date:'Ngày nhận',packing_date:'Ngày đóng gói',gross_weight_kg:'Kg thu',accepted_kg:'Kg đạt',rejected_kg:'Kg loại',input_kg:'Kg vào',output_kg:'Kg ra',stock_entry:'Phiếu kho',modified:'Cập nhật',status:'Trạng thái',approval_state:'Duyệt',supply_state:'Dự thu',resolved_percent:'% xử lý'}
const numericFields=new Set(['planned_qty','completed_qty','actual_workdays','quantity_per_workday','gross_weight_kg','accepted_kg','rejected_kg','input_kg','output_kg','forecast_kg','actual_kg','remaining_demand_kg','ordered_kg','delivered_kg','contributed_kg'])
function displayValue(column,value){
  if(column==='docstatus')return ['Nháp','Đã nộp','Đã hủy'][Number(value)]||String(value??'')
  return stateLabel(fmt(value))
}
const localFilters=ref({})
const visibleRows=computed(()=>props.filterValues?props.rows:props.rows.filter(row=>Object.entries(localFilters.value).every(([field,values])=>values.includes(row[field]))))
function headerParams(field){const choices=props.filterValues?.[field]||[...new Set(props.rows.map(row=>row[field]))].map(value=>({value}));return {choices:choices.map(row=>({...row,label:displayValue(field,row.value)})),selection:props.filterValues?props.serverFilters[field]:localFilters.value[field],apply:values=>{if(props.filterValues)emit('filter',{field,values});else{const next={...localFilters.value};if(values===null)delete next[field];else next[field]=values;localFilters.value=next}}}}
const columnDefs=computed(()=>props.columns.map((field,index)=>({
  field,
  headerName:label(field,labels[field]),
  minWidth:index===0?160:128,
  flex:index===0?1.3:1,
  sortable:true,
  filter:false,headerComponent:ExcelHeader,headerComponentParams:headerParams(field),
  resizable:true,
  cellClass:params=>['lotus-grid-cell',numericFields.has(field)?'lotus-grid-number':'',field==='docstatus'||field==='status'||field==='approval_state'?'lotus-grid-status':''].filter(Boolean).join(' '),
  valueFormatter:params=>displayValue(field,params.value),
})))
const defaultColDef={sortable:true,filter:false,resizable:true}
function onRowClicked(event){if(event.data)emit('open',event.data)}
function onCellKeyDown(event){if(event.event?.key==='Enter'&&event.data)emit('open',event.data)}
function displayFirst(row){return displayValue(props.columns[0],row[props.columns[0]])}
</script>

<template>
  <div class="lotus-record-list">
    <div v-if="loading&&!visibleRows.length" class="empty" role="status">Đang tải…</div>
    <div v-else-if="!visibleRows.length" class="empty">Chưa có dữ liệu trong phạm vi này.</div>
    <template v-else>
      <div class="lotus-ag-grid-shell" :class="{'lotus-ag-grid-shell--scroll':visibleRows.length>10}">
        <AgGridVue
          class="lotus-ag-grid"
          :theme="theme" :locale-text="AG_GRID_LOCALE_VN"
          :row-data="visibleRows"
          :column-defs="columnDefs"
          :default-col-def="defaultColDef"
          :dom-layout="visibleRows.length>10?'normal':'autoHeight'"
          :animate-rows="true"
          @row-clicked="onRowClicked"
          @cell-key-down="onCellKeyDown"
        />
      </div>
      <div class="lotus-mobile-records">
        <UiButton variant="outline" v-for="(row,i) in visibleRows" :key="row.name||row.line||i" type="button" class="lotus-mobile-record" @click="emit('open',row)">
          <strong>{{displayFirst(row)}}</strong>
          <span v-for="column in columns.slice(1,4)" :key="column" class="lotus-mobile-record-detail"><span>{{label(column,labels[column])}}</span><span>{{displayValue(column,row[column])}}</span></span>
          <span aria-hidden="true" class="lotus-mobile-record-arrow">›</span>
        </UiButton>
      </div>
      <div class="lotus-grid-footer">{{visibleRows.length}} dòng trên trang này · Bấm dòng để mở phiếu · Lọc và sắp xếp trong trang hiện tại</div>
    </template>
  </div>
</template>
