<script setup>
import {computed} from 'vue'
import DataTable from './DataTable.vue'
// Document lists by field name: Vietnamese labels and value formatting on top of the shared DataTable.
import {fmt} from '../domain'
import {label,stateLabel,docLabel} from '../labels'
import {unitLabel} from '../units'

const props=defineProps({
  rows:{type:Array,default:()=>[]},
  columns:{type:Array,default:()=>[]},
  loading:{type:Boolean,default:false},filterValues:Object,serverFilters:{type:Object,default:()=>({})},
})
const emit=defineEmits(['open','filter'])
const labels={name:'Phiếu',docstatus:'Trạng thái',farm:'Vườn',farm_block:'Lô',farm_plot:'Thửa',crop_cycle:'Vụ',posting_date:'Ngày',harvest_date:'Ngày thu',received_date:'Ngày nhận',packing_date:'Ngày đóng gói',gross_weight_kg:'Kg thu',accepted_kg:'Kg đạt',rejected_kg:'Kg loại',input_kg:'Kg vào',output_kg:'Kg ra',stock_entry:'Phiếu kho',modified:'Cập nhật',status:'Trạng thái',approval_state:'Duyệt',supply_state:'Dự thu',resolved_percent:'% xử lý'}
const numericFields=new Set(['planned_qty','completed_qty','actual_workdays','quantity_per_workday','gross_weight_kg','accepted_kg','rejected_kg','input_kg','output_kg','forecast_kg','actual_kg','remaining_demand_kg','ordered_kg','delivered_kg','contributed_kg'])
function displayValue(column,value){
  if(column==='uom')return unitLabel(value)
  if(column==='doctype')return docLabel(value)
  if(column==='docstatus')return ['Nháp','Đã nộp','Đã hủy'][Number(value)]||String(value??'')
  return stateLabel(fmt(value))
}
const columnDefs=computed(()=>props.columns.map((field,index)=>({
  field,
  headerName:label(field,labels[field]),
  minWidth:index===0?160:128,
  flex:index===0?1.3:1,
  cellClass:['lotus-grid-cell',numericFields.has(field)?'lotus-grid-number':'',field==='docstatus'||field==='status'||field==='approval_state'?'lotus-grid-status':''].filter(Boolean).join(' '),
  valueFormatter:params=>displayValue(field,params.value),
})))
</script>

<template>
  <DataTable class="lotus-record-list" :rows="rows" :columns="columnDefs" :loading="loading" :filter-values="filterValues" :server-filters="serverFilters" empty="Chưa có dữ liệu trong phạm vi này." interactive :mobile-limit="4" @open="emit('open',$event)" @filter="emit('filter',$event)"/>
</template>
