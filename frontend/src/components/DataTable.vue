<script setup>
import {computed,inject,ref,watch} from 'vue'
import {compactGridTheme,desktopGridThemes} from '../grid-theme'
import {AG_GRID_LOCALE_VN} from '@ag-grid-community/locale'
import ExcelHeader from './ExcelHeader.vue'
import {uiFarmLabel} from '../labels'
import {AgGridVue} from 'ag-grid-vue3'
import {themeQuartz} from 'ag-grid-community'
import '../grid-modules.js'
import {Button as UiButton} from './ui/button'
import {Skeleton as UiSkeleton} from './ui/skeleton'
import DesktopEmptyState from './DesktopEmptyState.vue'
import LotusIcon from './LotusIcon.vue'
import DataTableViews from './DataTableViews.vue'
import {loadColumnWidths,saveColumnWidths} from '../grid-state'
import {gridRowId} from '../grid-row-id'
const desktopDensity=inject('lotusDesktopDensity',null)
const theme=computed(()=>desktopGridThemes[desktopDensity?.value]||compactGridTheme)
const props=defineProps({rows:{type:Array,default:()=>[]},columns:{type:Array,required:true},loading:Boolean,empty:{type:String,default:'Chưa có dữ liệu.'},emptyHint:{type:String,default:''},storageKey:String,rowKey:String,pinnedBottomRows:{type:Array,default:()=>[]},mobileLimit:Number,interactive:Boolean,rowClass:Function,serverSort:Boolean,showEmptyHeaders:Boolean,filterValues:Object,serverFilters:{type:Object,default:()=>({})}})
const emit=defineEmits(['open','cell-open','filter','sort','visible-rows','row-double-open'])
const localFilters=ref({})
const key=c=>c.field||c.colId||c.headerName
watch(()=>props.columns.map(key).join('|'),()=>{const allowed=new Set(props.columns.map(key));localFilters.value=Object.fromEntries(Object.entries(localFilters.value).filter(([field])=>allowed.has(field)))})
const raw=(row,col)=>col.valueGetter?col.valueGetter({data:row}):row[col.field]
const visibleRows=computed(()=>props.filterValues?props.rows:props.rows.filter(row=>Object.entries(localFilters.value).every(([field,values])=>values.includes(raw(row,props.columns.find(col=>key(col)===field))))))
// Empty local-filter results unmount AG Grid; publish the empty selection explicitly.
watch(visibleRows,list=>{if(!list.length)emit('visible-rows',[])},{flush:'post'})
function headerParams(col){const field=key(col);const choices=props.filterValues?.[field]||[...new Map(props.rows.map(data=>({value:raw(data,col),data})).map(r=>[r.value,r])).values()];return {choices:choices.map(row=>({...row,label:row.label??(col.valueFormatter?col.valueFormatter({value:row.value,data:row.data||{}}):row.value)})),selection:props.filterValues?props.serverFilters[field]:localFilters.value[field],apply:values=>{if(props.filterValues)emit('filter',{field,values});else{const next={...localFilters.value};if(values===null)delete next[field];else next[field]=values;localFilters.value=next}}}}
const rowIdentity=computed(()=>visibleRows.value.map((r,i)=>gridRowId(r,props.rowKey)||i).join('|'))
const mobileColumns=computed(()=>props.columns.filter(c=>!c.hideOnMobile))
const defs=computed(()=>props.columns.map(c=>({...c,headerName:uiFarmLabel(c.headerName),flex:c.flex||1,minWidth:c.minWidth||100,sortable:c.sortable!==false,filter:false,resizable:true,headerComponent:ExcelHeader,headerComponentParams:headerParams(c)})))

function value(row,col){if(col.mobileValue)return col.mobileValue(row);const value=col.valueGetter?col.valueGetter({data:row}):row[col.field];return col.valueFormatter?col.valueFormatter({value,data:row}):value??'—'}
function sorted(event){sortState.value=event.api.getColumnState().filter(c=>c.sort).map(c=>({colId:c.colId,sort:c.sort,sortIndex:c.sortIndex}));if(props.serverSort)emit('sort',event.api.getColumnState().filter(c=>c.sort).sort((a,b)=>(a.sortIndex||0)-(b.sortIndex||0)).map(c=>({colId:c.colId,sort:c.sort})))}
function open(event){if(props.interactive&&event.data)emit('open',event.data)}
// A rendered row may move after filtering or sorting. Its ID must come from its document, not its index.
const getRowId=params=>gridRowId(params.data,props.rowKey)
const hasLocalFilters=computed(()=>!props.filterValues&&Object.keys(localFilters.value).length>0)
// Column widths persist per table (storageKey, or the column set) so a resized grid stays that way after reload.
const widthKey=computed(()=>props.storageKey||props.columns.map(key).join('|'))
const gridApi=ref(null),sortState=ref([])
const columnLabels=computed(()=>Object.fromEntries(props.columns.map(c=>[key(c),uiFarmLabel(c.headerName)])))
// Saved views: column filters (local tables) + sort, applied back onto the grid.
function applyView(view){if(!props.filterValues)localFilters.value={...(view.filters||{})};gridApi.value?.applyColumnState({state:view.sort||[],defaultState:{sort:null}})}
function restoreWidths(event){gridApi.value=event.api;const widths=loadColumnWidths(widthKey.value);if(widths.length)event.api.applyColumnState({state:widths})}
function resized(event){if(event.finished&&event.source!=='api')saveColumnWidths(widthKey.value,event.api.getColumnState())}
function reportVisible(event){const records=[];event.api.forEachNodeAfterFilterAndSort(node=>{if(node.data)records.push(node.data)});emit('visible-rows',records)}
</script>
<template>
 <div class="lotus-data-table" :aria-busy="loading">
  <DataTableViews v-if="!filterValues" :storage-key="widthKey" :filters="localFilters" :sort="sortState" :labels="columnLabels" @apply="applyView" @clear="localFilters={}"/>
  <div v-if="!visibleRows.length&&!showEmptyHeaders&&loading" class="lotus-table-skeleton" role="status" aria-label="Đang tải dữ liệu"><UiSkeleton v-for="n in 5" :key="n" class="lotus-table-skeleton__row"/></div>
  <DesktopEmptyState v-else-if="!visibleRows.length&&!showEmptyHeaders" class="empty stock-empty" :title="empty" :description="hasLocalFilters?'Bộ lọc cột đang ẩn toàn bộ dòng.':emptyHint">
   <template v-if="hasLocalFilters||$slots['empty-actions']" #actions><UiButton v-if="hasLocalFilters" type="button" variant="outline" size="sm" @click="localFilters={}">Xóa bộ lọc</UiButton><slot name="empty-actions"/></template>
  </DesktopEmptyState>
  <template v-else>
   <div class="lotus-ag-grid-shell" :class="{'lotus-ag-grid-shell--scroll':visibleRows.length>10}"><AgGridVue :key="rowIdentity" class="lotus-ag-grid" :theme="theme" :locale-text="{...AG_GRID_LOCALE_VN,noRowsToShow:empty}" :loading="loading" :row-data="visibleRows" :pinned-bottom-row-data="pinnedBottomRows" :get-row-id="getRowId" :column-defs="defs" :dom-layout="visibleRows.length>10?'normal':'autoHeight'" :animate-rows="true" :get-row-class="params=>rowClass?rowClass(params.data):(params.data?.shortage_qty>0?'lotus-shortage-row':'')" :enable-cell-text-selection="true" @grid-ready="restoreWidths" @column-resized="resized" @sort-changed="sorted" @model-updated="reportVisible" @row-clicked="open" @row-double-clicked="event=>event.data&&emit('row-double-open',event.data)" @cell-clicked="emit('cell-open',$event)" @cell-key-down="event=>{if(event.event?.key==='Enter'){open(event);emit('cell-open',event)}}" /></div>
   <div class="lotus-mobile-records"><div v-if="!visibleRows.length&&loading" class="lotus-table-skeleton" role="status" aria-label="Đang tải dữ liệu"><UiSkeleton v-for="n in 3" :key="n" class="lotus-table-skeleton__row"/></div><p v-else-if="!visibleRows.length" role="status">{{empty}}</p><component :is="interactive?UiButton:'article'" v-for="(row,index) in visibleRows" :key="gridRowId(row,rowKey)" class="lotus-mobile-record" variant="ghost" @click="interactive&&emit('open',row)"><strong>{{value(row,mobileColumns[0]||columns[0])}}</strong><span v-for="col in mobileColumns.slice(1,mobileLimit||undefined)" :key="col.field||col.headerName" class="lotus-mobile-record-detail"><span>{{uiFarmLabel(col.headerName)}}</span><UiButton v-if="col.colId" variant="link" size="sm" @click.stop="emit('cell-open',{data:row,colDef:col})">{{value(row,col)}}</UiButton><span v-else>{{value(row,col)}}</span></span><LotusIcon v-if="interactive" name="chevron" class="lotus-mobile-record-arrow"/></component></div>
  </template>
 </div>
</template>