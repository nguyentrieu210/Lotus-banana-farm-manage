<script setup>
import {computed,ref,watch} from 'vue'
import {compactGridTheme as theme} from '../grid-theme'
import {AG_GRID_LOCALE_VN} from '@ag-grid-community/locale'
import ExcelHeader from './ExcelHeader.vue'
import {uiFarmLabel} from '../labels'
import {AgGridVue} from 'ag-grid-vue3'
import {AllCommunityModule,ModuleRegistry,themeQuartz} from 'ag-grid-community'
import {Button as UiButton} from './ui/button'
ModuleRegistry.registerModules([AllCommunityModule])
const props=defineProps({rows:{type:Array,default:()=>[]},columns:{type:Array,required:true},loading:Boolean,empty:{type:String,default:'Chưa có dữ liệu.'},interactive:Boolean,serverSort:Boolean,showEmptyHeaders:Boolean,filterValues:Object,serverFilters:{type:Object,default:()=>({})}})
const emit=defineEmits(['open','cell-open','filter','sort'])
const localFilters=ref({})
const key=c=>c.field||c.colId||c.headerName
watch(()=>props.columns.map(key).join('|'),()=>{const allowed=new Set(props.columns.map(key));localFilters.value=Object.fromEntries(Object.entries(localFilters.value).filter(([field])=>allowed.has(field)))})
const raw=(row,col)=>col.valueGetter?col.valueGetter({data:row}):row[col.field]
const visibleRows=computed(()=>props.filterValues?props.rows:props.rows.filter(row=>Object.entries(localFilters.value).every(([field,values])=>values.includes(raw(row,props.columns.find(col=>key(col)===field))))))
function headerParams(col){const field=key(col);const choices=props.filterValues?.[field]||[...new Set(props.rows.map(row=>raw(row,col)))].map(value=>({value}));return {choices:choices.map(row=>({...row,label:row.label??(col.valueFormatter?col.valueFormatter({value:row.value}):row.value)})),selection:props.filterValues?props.serverFilters[field]:localFilters.value[field],apply:values=>{if(props.filterValues)emit('filter',{field,values});else{const next={...localFilters.value};if(values===null)delete next[field];else next[field]=values;localFilters.value=next}}}}
const defs=computed(()=>props.columns.map(c=>({...c,headerName:uiFarmLabel(c.headerName),flex:c.flex||1,minWidth:c.minWidth||100,sortable:true,filter:false,resizable:true,headerComponent:ExcelHeader,headerComponentParams:headerParams(c)})))

function value(row,col){if(col.mobileValue)return col.mobileValue(row);const value=col.valueGetter?col.valueGetter({data:row}):row[col.field];return col.valueFormatter?col.valueFormatter({value,data:row}):value??'—'}
function sorted(event){if(props.serverSort)emit('sort',event.api.getColumnState().filter(c=>c.sort).sort((a,b)=>(a.sortIndex||0)-(b.sortIndex||0)).map(c=>({colId:c.colId,sort:c.sort})))}
function open(event){if(props.interactive&&event.data)emit('open',event.data)}
</script>
<template>
 <div class="lotus-data-table" :aria-busy="loading">
  <div v-if="!visibleRows.length&&!showEmptyHeaders" class="empty stock-empty" role="status">{{loading?'Đang tải…':empty}}</div>
  <template v-else>
   <div class="lotus-ag-grid-shell" :class="{'lotus-ag-grid-shell--scroll':visibleRows.length>10}"><AgGridVue class="lotus-ag-grid" :theme="theme" :locale-text="{...AG_GRID_LOCALE_VN,noRowsToShow:empty}" :loading="loading" :row-data="visibleRows" :column-defs="defs" :dom-layout="visibleRows.length>10?'normal':'autoHeight'" :animate-rows="true" :get-row-class="params=>params.data?.shortage_qty>0?'lotus-shortage-row':''" :enable-cell-text-selection="true" @sort-changed="sorted" @row-clicked="open" @cell-clicked="emit('cell-open',$event)" @cell-key-down="event=>{if(event.event?.key==='Enter'){open(event);emit('cell-open',event)}}" /></div>
   <div class="lotus-mobile-records"><p v-if="!visibleRows.length" role="status">{{loading?'Đang tải…':empty}}</p><component :is="interactive?UiButton:'article'" v-for="(row,index) in visibleRows" :key="row.name||index" class="lotus-mobile-record" variant="ghost" @click="interactive&&emit('open',row)"><strong>{{value(row,columns[0])}}</strong><span v-for="col in columns.slice(1)" :key="col.field||col.headerName" class="lotus-mobile-record-detail"><span>{{uiFarmLabel(col.headerName)}}</span><UiButton v-if="col.colId" variant="link" size="sm" @click.stop="emit('cell-open',{data:row,colDef:col})">{{value(row,col)}}</UiButton><span v-else>{{value(row,col)}}</span></span></component></div>
  </template>
 </div>
</template>
