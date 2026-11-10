<script setup>
import {computed} from 'vue'
import DataTable from './DataTable.vue'
// Document lists by field name: Vietnamese labels and value formatting on top of the shared DataTable.
import {fmt} from '../domain'
import {label,stateLabel} from '../labels'

const props=defineProps({
  rows:{type:Array,default:()=>[]},
  columns:{type:Array,default:()=>[]},
  loading:{type:Boolean,default:false},filterValues:Object,serverFilters:{type:Object,default:()=>({})},
})
const emit=defineEmits(['open','filter'])
const labels={name:'Phiếu',docstatus:'Trạng thái',farm:'Vườn',farm_block:'Lô',posting_date:'Ngày',modified:'Cập nhật',status:'Trạng thái',approval_state:'Duyệt'}
function displayValue(column,value){
  if(column==='docstatus')return ['Nháp','Đã nộp','Đã hủy'][Number(value)]||String(value??'')
  return stateLabel(fmt(value))
}
const columnDefs=computed(()=>props.columns.map((field,index)=>({
  field,
  headerName:label(field,labels[field]),
  minWidth:index===0?160:128,
  flex:index===0?1.3:1,
  cellClass:['lotus-grid-cell',field==='docstatus'||field==='status'||field==='approval_state'?'lotus-grid-status':''].filter(Boolean).join(' '),
  valueFormatter:params=>displayValue(field,params.value),
})))
</script>

<template>
  <DataTable class="lotus-record-list" :rows="rows" :columns="columnDefs" :loading="loading" :filter-values="filterValues" :server-filters="serverFilters" empty="Chưa có dữ liệu trong phạm vi này." interactive :mobile-limit="4" @open="emit('open',$event)" @filter="emit('filter',$event)"/>
</template>
