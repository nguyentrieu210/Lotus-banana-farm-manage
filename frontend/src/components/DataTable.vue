<script setup>
import {computed,getCurrentInstance,inject,nextTick,onBeforeUnmount,onMounted,reactive,ref,useSlots,watch} from 'vue'
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
import ColumnVisibilityMenu from './ColumnVisibilityMenu.vue'
import {columnId,normalizeColumnLayout,loadColumnLayout,saveColumnLayout,orderedColumns,displayedColumns,moveColumn,pinColumn,setVisibleColumns,hasSavedColumnLayout,changeColumnVisibility} from '../grid-visibility'
import {loadColumnWidths,saveColumnWidths} from '../grid-state'
import {gridRowId} from '../grid-row-id'
import ModalForm from './form/ModalForm.vue'
import {summableColumn,totalsRow} from '../grid-totals'
import {sortExcelChoices} from '../excel-filter-state'
import {buildXlsx,exportExcelFile} from '../excel-export'
import {Pagination} from './ui/pagination'
import UiSelect from './ui/select/Select.vue'
const desktopDensity=inject('lotusDesktopDensity',null)
// Shared lists use compact rows; explicit comfortable mode keeps a little more breathing room.
const theme=computed(()=>{const comfortable=desktopDensity?.value==='comfortable';return (desktopGridThemes[desktopDensity?.value]||compactGridTheme).withParams({fontSize:comfortable?13:12,rowHeight:comfortable?40:34,headerHeight:comfortable?38:33,spacing:3})})
const props=defineProps({rows:{type:Array,default:()=>[]},columns:{type:Array,required:true},loading:Boolean,empty:{type:String,default:'Chưa có dữ liệu.'},emptyHint:{type:String,default:''},storageKey:String,rowKey:String,pinnedBottomRows:{type:Array,default:()=>[]},mobileLimit:Number,interactive:Boolean,rowClass:Function,serverSort:Boolean,showEmptyHeaders:Boolean,filterValues:Object,serverFilters:{type:Object,default:()=>({})},totals:{type:Boolean,default:true},totalsLabel:{type:String,default:'Tổng'},rowDetail:{type:Boolean,default:true},fill:{type:Number,default:-1},paginate:{type:Boolean,default:true},pageSize:{type:Number,default:50},exportRows:Function,exportTitle:String,exportable:{type:Boolean,default:true},columnsMenu:{type:Boolean,default:true},hiddenColumns:{type:Array,default:null},selectionEnabled:{type:Boolean,default:true},selectedRowKeys:{type:Array,default:null},rowIndexOffset:{type:Number,default:0},columnLayout:{type:Object,default:null},columnPresets:{type:Array,default:()=>[]}})
const emit=defineEmits(['open','cell-open','filter','sort','visible-rows','row-double-open','update:hiddenColumns','update:columnLayout','row-selection-change','page-selection-change','selection-clear'])
// AG Grid's Vue adapter clones row data. Editable slots must update the source record by its stable ID.
const sourceRows=computed(()=>new Map(props.rows.map(row=>[gridRowId(row,props.rowKey),row])))
const slots=useSlots(),slotRenderers=new Map()
function slotRenderer(field){
 if(!slotRenderers.has(field))slotRenderers.set(field,{props:['params'],setup(props){return()=>{
  const data=props.params.data
  const scope={row:sourceRows.value.get(gridRowId(data,props.rowKey))||(data?reactive(data):data),value:props.params.value,params:props.params,column:props.params.colDef}
  return (slots['cell-'+field]||slots.cell)?.(scope)
 }}})
 return slotRenderers.get(field)
}
const localFilters=ref({})
const key=c=>c.field||c.colId||c.headerName
watch(()=>props.columns.map(key).join('|'),()=>{const allowed=new Set(props.columns.map(key));localFilters.value=Object.fromEntries(Object.entries(localFilters.value).filter(([field])=>allowed.has(field)))})
const raw=(row,col)=>col.valueGetter?col.valueGetter({data:row}):row[col.field]
const passes=(row,skip)=>Object.entries(localFilters.value).every(([field,values])=>field===skip||values.includes(raw(row,props.columns.find(col=>key(col)===field))))
const visibleRows=computed(()=>props.filterValues?props.rows:props.rows.filter(row=>passes(row)))
// Empty local-filter results unmount AG Grid; publish the empty selection explicitly.
watch(visibleRows,list=>{if(!list.length)emit('visible-rows',[])},{flush:'post'})
// Like Excel: a column's value list shows what is left after the OTHER columns' filters, sorted, blanks last.
function headerParams(col){const field=key(col);const choices=props.filterValues?.[field]||[...new Map(props.rows.filter(row=>passes(row,field)).map(data=>({value:raw(data,col),data})).map(r=>[r.value,r])).values()];return {choices:sortExcelChoices(choices.map(row=>({...row,label:row.label??(col.valueFormatter?col.valueFormatter({value:row.value,data:row.data||{}}):row.value)}))),selection:props.filterValues?props.serverFilters[field]:localFilters.value[field],apply:values=>{if(props.filterValues)emit('filter',{field,values});else{const next={...localFilters.value};if(values===null)delete next[field];else next[field]=values;localFilters.value=next}}}}
const rowIdentity=computed(()=>visibleRows.value.map((r,i)=>gridRowId(r,props.rowKey)||i).join('|'))
const mobileColumns=computed(()=>activeDisplayColumns.value.filter(c=>!c.hideOnMobile))
// Sum row on every table: the row count plus the numeric columns of the rows on screen (after column filters), pinned under the grid.
// A screen's own pinnedBottomRows win; :totals="false" turns it off (statements, check lists); a column opts in/out with sum:true|false.
const sumColumns=computed(()=>activeDisplayColumns.value.filter(c=>summableColumn(c,visibleRows.value,raw)))
const autoTotals=computed(()=>props.totals&&!props.pinnedBottomRows.length&&visibleRows.value.length?[totalsRow(props.columns.filter(c=>columnId(c)!==nativeSelectId.value),sumColumns.value,visibleRows.value,raw,key,props.totalsLabel)]:[])
const totalText=(col,total)=>{const v=total[key(col)];try{return col.valueFormatter?col.valueFormatter({value:v,data:total,node:{rowPinned:'bottom'}}):v}catch{return v}}
const bottomRows=computed(()=>props.pinnedBottomRows.length?props.pinnedBottomRows:autoTotals.value)
// Formatters and getters written for real rows must not break on the sum row.
const pinnedSafe=c=>({...(c.valueGetter?{valueGetter:p=>p.node?.rowPinned?p.data?.[key(c)]:c.valueGetter(p)}:{}),...(c.valueFormatter?{valueFormatter:p=>{if(!p.node?.rowPinned)return c.valueFormatter(p);if(p.value==null||p.value==='')return '';if(p.data?.__lotus_total&&typeof p.value==='string')return p.value;try{const text=c.valueFormatter(p);return text==='—'?'':text}catch{return p.value}}}:{})})
// Sum/pinned rows are plain text in every column, whatever renderer (inputs, buttons, slots) the column uses for real rows.
const pinnedText=p=>document.createTextNode(String(p.valueFormatted??p.value??''))
const pinnedRenderer=c=>({cellRendererSelector:p=>p.node?.rowPinned?{component:pinnedText}:c.cellRendererSelector?.(p)})
const defs=computed(()=>orderedColumns(props.columns,effectiveLayout.value).map(c=>({...c,...pinnedSafe(c),colId:c.colId||key(c),hide:Boolean(c.hide||selectedHidden.value.includes(columnId(c))),pinned:effectiveLayout.value.pinned.includes(columnId(c))?'left':null,headerName:uiFarmLabel(c.headerName),headerTooltip:c.headerTooltip||uiFarmLabel(c.headerName),tooltipValueGetter:c.tooltipValueGetter||((p)=>p.valueFormatted??p.value??''),flex:c.flex??1,minWidth:c.minWidth||90,sortable:c.sortable!==false,filter:false,resizable:true,headerComponent:ExcelHeader,headerComponentParams:headerParams(c),...((slots['cell-'+key(c)]||slots.cell)?{cellRenderer:slotRenderer(key(c))}:{}),...pinnedRenderer(c)})))

function value(row,col){if(col.mobileValue)return col.mobileValue(row);const value=col.valueGetter?col.valueGetter({data:row}):row[col.field];return col.valueFormatter?col.valueFormatter({value,data:row}):value??'—'}
let restoring=false
function sorted(event){sortState.value=event.api.getColumnState().filter(c=>c.sort).map(c=>({colId:c.colId,sort:c.sort,sortIndex:c.sortIndex}));if(props.serverSort&&!restoring)emit('sort',event.api.getColumnState().filter(c=>c.sort).sort((a,b)=>(a.sortIndex||0)-(b.sortIndex||0)).map(c=>({colId:c.colId,sort:c.sort})))}
// Row click: screens that handle @open / @cell-open / @row-double-open keep their own behaviour; every other table opens a read-only detail of the row.
const listeners=getCurrentInstance()?.vnode.props||{}
const ownsClick=()=>Boolean(listeners.onOpen||listeners.onCellOpen||listeners.onRowDoubleOpen)
const detail=ref(null)
const detailOpen=computed({get:()=>Boolean(detail.value),set:value=>{if(!value)detail.value=null}})
const detailTitle=computed(()=>detail.value?String(value(detail.value,activeDisplayColumns.value[0]||props.columns[0])??'Chi tiết dòng'):'')
function showDetail(row){if(props.rowDetail&&!ownsClick()&&row)detail.value=sourceRows.value.get(gridRowId(row,props.rowKey))||row}
function open(event){
 if(!event.data||event.node?.rowPinned||['__lotus_select','__lotus_stt'].includes(event.column?.getColId?.()))return
 if(event.event?.target?.closest?.('button,a,input,select,textarea,label,[role=checkbox],[role=combobox]'))return
 if(props.interactive)emit('open',event.data);else showDetail(event.data)
}
// fill >= 0 (list pages): the scrolling grid ends `fill` px above the window bottom, so the sum row and the pager below stay visible.
const shell=ref(null),fitHeight=ref(0)
function fit(){const el=shell.value;if(props.fill<0||!el)return;fitHeight.value=Math.max(280,Math.floor(window.innerHeight-el.getBoundingClientRect().top-props.fill-(props.paginate?56:0)))}
// Pager: the same one on every table. AG Grid pages the sorted rows (so sorting covers all pages); lists paged by the server pass paginate=false.
const pageStart=ref(0)
const pageRows=computed(()=>props.paginate?visibleRows.value.slice(pageStart.value,pageStart.value+props.pageSize):visibleRows.value)
watch(()=>rowIdentity.value,()=>{pageStart.value=0})
function pageChanged(event){const page=event.api?.paginationGetCurrentPage?.();if(props.paginate&&Number.isInteger(page))pageStart.value=page*props.pageSize;nextTick(refreshSelection)}
function goPage(start){pageStart.value=start;gridApi.value?.paginationGoToPage(Math.floor(start/props.pageSize))}
onMounted(()=>{if(props.fill>=0){window.addEventListener('resize',fit);nextTick(fit)}})
onBeforeUnmount(()=>window.removeEventListener('resize',fit))
watch(()=>[visibleRows.value.length>10,rowIdentity.value,props.loading],()=>nextTick(fit))
// A rendered row may move after filtering or sorting. Its ID must come from its document, not its index.
const getRowId=params=>gridRowId(params.data,props.rowKey)
const hasLocalFilters=computed(()=>!props.filterValues&&Object.keys(localFilters.value).length>0)
// Column widths persist per table (storageKey, or the column set) so a resized grid stays that way after reload.
const widthKey=computed(()=>props.storageKey||props.columns.map(key).join('|'))
const localLayout=ref({hidden:[],order:[],pinned:[]})
watch([widthKey,()=>props.columns.map(columnId).join('|')],()=>{
 const saved=loadColumnLayout(widthKey.value,props.columns)
 const firstPreset=props.columnPresets?.[0]
 localLayout.value=!hasSavedColumnLayout(widthKey.value)&&firstPreset?setVisibleColumns(props.columns,saved,firstPreset.visible||[]):saved
},{immediate:true})
const effectiveLayout=computed(()=>normalizeColumnLayout(props.columns,{
 ...(props.columnLayout||localLayout.value),
 ...((props.hiddenColumns&&!props.columnLayout)?{hidden:props.hiddenColumns}:{})
}))
const selectedHidden=computed(()=>effectiveLayout.value.hidden)
const activeDisplayColumns=computed(()=>displayedColumns(props.columns,effectiveLayout.value))
const activeColumns=computed(()=>activeDisplayColumns.value.filter(c=>columnId(c)!==nativeSelectId.value&&!c.suppressExport&&!c.columnChooserLocked))
function applyColumnLayout(api=gridApi.value){
 if(!api)return
 const cols=orderedColumns(props.columns,effectiveLayout.value).filter(c=>columnId(c)!==nativeSelectId.value)
 api.applyColumnState({state:[{colId:nativeSelectId.value||'__lotus_select',pinned:'left',hide:false,width:42},{colId:'__lotus_stt',pinned:'left',width:52},...cols.map(col=>({colId:columnId(col),hide:Boolean(col.hide||selectedHidden.value.includes(columnId(col))),pinned:effectiveLayout.value.pinned.includes(columnId(col))?'left':null}))],applyOrder:true})
}
function setColumnLayout(next){
 const normalized=normalizeColumnLayout(props.columns,next)
 localLayout.value=normalized
 saveColumnLayout(widthKey.value,props.columns,normalized)
 emit('update:hiddenColumns',normalized.hidden)
 emit('update:columnLayout',normalized)
 nextTick(()=>applyColumnLayout())
}
function toggleColumn(id){setColumnLayout({...effectiveLayout.value,hidden:changeColumnVisibility(props.columns,selectedHidden.value,id)})}
function resetColumns(){setColumnLayout({hidden:[],order:[],pinned:[]})}
function showAllColumns(){setColumnLayout({...effectiveLayout.value,hidden:[]})}
function reorderColumn(id,direction){setColumnLayout(moveColumn(props.columns,effectiveLayout.value,id,direction))}
function togglePin(id){setColumnLayout(pinColumn(props.columns,effectiveLayout.value,id))}
function applyColumnPreset(id){
 const preset=props.columnPresets.find(p=>p.id===id)
 if(preset)setColumnLayout(setVisibleColumns(props.columns,effectiveLayout.value,preset.visible||[]))
}
watch(effectiveLayout,()=>nextTick(()=>applyColumnLayout()))
const gridApi=ref(null),sortState=ref([])

// Two fixed utility columns are independent of business columns, filters and Excel exports.
const selectedLocal=ref(new Set())
const selectedIds=computed(()=>new Set(props.selectedRowKeys??[...selectedLocal.value]))
const selectedCount=computed(()=>selectedIds.value.size)
const getSelectionId=row=>gridRowId(row,props.rowKey)
function refreshSelection(){
 gridApi.value?.refreshCells?.({force:true,columns:['__lotus_select']})
 gridApi.value?.refreshHeader?.()
}
watch(()=>props.selectedRowKeys,()=>nextTick(refreshSelection),{deep:true})
function setRowSelected(row,selected){
 const id=getSelectionId(row)
 if(props.selectedRowKeys===null){
  const next=new Set(selectedLocal.value)
  selected?next.add(id):next.delete(id)
  selectedLocal.value=next
 }
 emit('row-selection-change',{id,row,selected})
 nextTick(refreshSelection)
}
function rowsInCurrentPage(){
 const api=gridApi.value
 if(!api)return props.paginate?pageRows.value:visibleRows.value
 const start=props.paginate?(api.paginationGetCurrentPage?.()||0)*props.pageSize:0
 const end=props.paginate?start+props.pageSize:Infinity
 const result=[]
 api.forEachNodeAfterFilterAndSort(node=>{
  if(node.data&&!node.rowPinned&&node.rowIndex>=start&&node.rowIndex<end)result.push(node.data)
 })
 return result
}
function togglePageSelection(){
 const rows=rowsInCurrentPage()
 if(!rows.length)return
 const select=!rows.every(row=>selectedIds.value.has(getSelectionId(row)))
 if(props.selectedRowKeys===null){
  const next=new Set(selectedLocal.value)
  rows.forEach(row=>select?next.add(getSelectionId(row)):next.delete(getSelectionId(row)))
  selectedLocal.value=next
 }
 emit('page-selection-change',{rows,selected:select})
 nextTick(refreshSelection)
}
function clearSelected(){
 if(props.selectedRowKeys===null)selectedLocal.value=new Set()
 emit('selection-clear')
 nextTick(refreshSelection)
}
function utilityButton(pressed,label){
 const button=document.createElement('button')
 button.type='button'
 button.className='lotus-grid-select-toggle'+(pressed?' is-on':'')
 button.setAttribute('aria-pressed',String(pressed))
 button.setAttribute('aria-label',label)
 button.title=label
 const mark=document.createElement('span')
 mark.setAttribute('aria-hidden','true')
 mark.textContent=pressed?'✓':''
 button.appendChild(mark)
 return button
}
function renderSelectionCell(params){
 if(!params.data||params.node?.rowPinned)return ''
 const row=params.data
 const selected=selectedIds.value.has(getSelectionId(row))
 const button=utilityButton(selected,selected?'Bỏ chọn dòng':'Chọn dòng')
 button.addEventListener('click',event=>{
  event.preventDefault();event.stopPropagation()
  setRowSelected(row,!selectedIds.value.has(getSelectionId(row)))
 })
 return button
}
function renderSelectHeader(){
 const host=document.createElement('div')
 host.className='lotus-grid-select-header'
 const pageRows=rowsInCurrentPage()
 const selected=Boolean(pageRows.length)&&pageRows.every(row=>selectedIds.value.has(getSelectionId(row)))
 const button=utilityButton(selected,selected?'Bỏ chọn các dòng trang này':'Chọn tất cả dòng trang này')
 button.disabled=!pageRows.length
 if(pageRows.length&&!selected&&pageRows.some(row=>selectedIds.value.has(getSelectionId(row))))button.classList.add('is-partial')
 button.addEventListener('click',event=>{event.preventDefault();event.stopPropagation();togglePageSelection()})
 host.appendChild(button)
 return host
}
// AG Grid header components must be classes with init/getGui; a plain function is constructed with `new`
// and its returned element has no getGui, which stops the whole grid from rendering.
const domHeader=build=>class{init(params){this.gui=build(params)}getGui(){return this.gui}refresh(){return false}destroy(){}}
const selectHeader=domHeader(()=>renderSelectHeader())
const selectDef={colId:'__lotus_select',headerName:'Chọn',width:42,minWidth:42,maxWidth:42,
 pinned:'left',lockPinned:true,lockPosition:'left',suppressMovable:true,resizable:false,
 sortable:false,filter:false,suppressHeaderMenuButton:true,suppressColumnsToolPanel:true,
 headerComponent:selectHeader,cellRenderer:renderSelectionCell,cellClass:'lotus-grid-select-cell'}
const sttDef={colId:'__lotus_stt',headerName:'STT',width:52,minWidth:52,maxWidth:52,
 pinned:'left',lockPinned:true,lockPosition:'left',suppressMovable:true,resizable:false,
 sortable:false,filter:false,suppressHeaderMenuButton:true,suppressColumnsToolPanel:true,
 valueGetter:params=>params.node?.rowPinned?'':(Number.isInteger(params.node?.rowIndex)?props.rowIndexOffset+params.node.rowIndex+1:''),
 cellClass:'lotus-grid-stt-cell'}
// Existing operational checkbox columns (HR/payroll/quotation) keep their business behavior.
const nativeSelectId=computed(()=>columnId(props.columns.find(c=>c.headerName==='Chọn'&&['__pick','selected','select_log','choice'].includes(columnId(c)))||{})||null)
const pickerColumns=computed(()=>props.columns.map(c=>columnId(c)===nativeSelectId.value?{...c,columnChooserLocked:true,suppressExport:true}:c))
const nativeSelectionHeader=domHeader(()=>{const label=document.createElement('span');label.textContent='Chọn';label.className='lotus-grid-native-select-header';return label})
const gridDefs=computed(()=>{
 const own=defs.value.find(c=>columnId(c)===nativeSelectId.value)
 const body=defs.value.filter(c=>columnId(c)!==nativeSelectId.value)
 const select=own?{...own,width:42,minWidth:42,maxWidth:42,flex:0,
  pinned:'left',lockPinned:true,lockPosition:'left',suppressMovable:true,
  hide:false,sortable:false,filter:false,headerComponent:nativeSelectionHeader,headerTooltip:'Chọn dòng'}:selectDef
 return [select,sttDef,...body]
})

const columnLabels=computed(()=>Object.fromEntries(props.columns.map(c=>[key(c),uiFarmLabel(c.headerName)])))
// Saved views: column filters (local tables) + sort, applied back onto the grid.
// Server-filtered lists (filterValues) get the same chips and views: each changed column is sent back as a filter event.
const mobileFilter=ref('')
const filterable=computed(()=>activeDisplayColumns.value.filter(c=>c.filterable!==false))
const mobileFilterParams=computed(()=>{const col=props.columns.find(c=>key(c)===mobileFilter.value);return col?{...headerParams(col),displayName:uiFarmLabel(col.headerName)}:null})
const activeFilters=computed(()=>props.filterValues?Object.fromEntries(Object.entries(props.serverFilters||{}).filter(([,values])=>Array.isArray(values))):localFilters.value)
function applyView(view){
 const next=view.filters||{}
 if(props.filterValues){for(const field of new Set([...Object.keys(activeFilters.value),...Object.keys(next)]))if(JSON.stringify(activeFilters.value[field]??null)!==JSON.stringify(next[field]??null))emit('filter',{field,values:next[field]??null})}
 else localFilters.value={...next}
 gridApi.value?.applyColumnState({state:view.sort||[],defaultState:{sort:null}})
}
// The grid is rebuilt when its rows change (filters, reload): bring back saved widths and the current sort without re-asking the server.
function restoreWidths(event){gridApi.value=event.api;const widths=loadColumnWidths(widthKey.value);if(widths.length)event.api.applyColumnState({state:widths});applyColumnLayout(event.api);nextTick(refreshSelection)
 if(sortState.value.length){restoring=true;try{event.api.applyColumnState({state:sortState.value,defaultState:{sort:null}})}finally{restoring=false}}}
function resized(event){if(event.finished&&event.source!=='api')saveColumnWidths(widthKey.value,event.api.getColumnState())}
function reportVisible(event){const records=[];event.api.forEachNodeAfterFilterAndSort(node=>{if(node.data)records.push(node.data)});emit('visible-rows',records)}
const exporting=ref(false),exportError=ref('')
async function downloadExcel(){
 if(exporting.value)return
 exporting.value=true;exportError.value=''
 try{
  const records=[]
  if(props.exportRows)records.push(...await props.exportRows())
  else if(gridApi.value)gridApi.value.forEachNodeAfterFilterAndSort(node=>{if(node.data)records.push(node.data)})
  else records.push(...visibleRows.value)
  if(!records.length)throw new Error('Bảng hiện không có dữ liệu để xuất.')
  const bytes=buildXlsx(activeColumns.value,records)
  exportExcelFile(bytes,props.exportTitle||props.storageKey||'Bang-du-lieu')
 }catch(e){exportError.value=e?.message||'Không thể xuất Excel.'}
 finally{exporting.value=false}
}
</script>
<template>
 <div class="lotus-data-table" :aria-busy="loading">
  <div v-if="columnsMenu||exportable||selectedCount" class="lotus-data-table__export">
   <span v-if="selectedCount" class="lotus-data-table__selected">{{selectedCount}} dòng đã chọn <button type="button" @click="clearSelected">Bỏ chọn</button></span>
   <ColumnVisibilityMenu v-if="columnsMenu&&columns.length>1" :columns="pickerColumns" :layout="effectiveLayout" :presets="columnPresets" @toggle="toggleColumn" @reset="resetColumns" @all="showAllColumns" @move="reorderColumn" @pin="togglePin" @preset="applyColumnPreset"/>
   <UiButton v-if="exportable" variant="outline" size="sm" type="button" :disabled="loading||exporting||(!visibleRows.length&&!exportRows)" :title="exportRows?'Xuất toàn bộ dòng phù hợp bộ lọc':'Xuất các dòng đã tải, theo bộ lọc và thứ tự hiện tại'" @click="downloadExcel"><LotusIcon name="download"/>{{exporting?'Đang xuất…':'Xuất Excel'}}</UiButton>
  </div>
  <p v-if="exportError" role="alert" class="lotus-data-table__export-error">{{exportError}}</p>
  <DataTableViews :storage-key="widthKey" :filters="activeFilters" :sort="sortState" :labels="columnLabels" @apply="applyView" @clear="applyView({filters:{},sort:sortState})"/>
  <div v-if="!visibleRows.length&&!showEmptyHeaders&&loading" class="lotus-table-skeleton" role="status" aria-label="Đang tải dữ liệu"><UiSkeleton v-for="n in 5" :key="n" class="lotus-table-skeleton__row"/></div>
  <DesktopEmptyState v-else-if="!visibleRows.length&&!showEmptyHeaders" class="empty stock-empty" :title="empty" :description="hasLocalFilters?'Bộ lọc cột đang ẩn toàn bộ dòng.':emptyHint">
   <template v-if="hasLocalFilters||$slots['empty-actions']" #actions><UiButton v-if="hasLocalFilters" type="button" variant="outline" size="sm" @click="localFilters={}">Xóa bộ lọc</UiButton><slot name="empty-actions"/></template>
  </DesktopEmptyState>
  <template v-else>
   <div ref="shell" class="lotus-ag-grid-shell" :class="{'lotus-ag-grid-shell--scroll':visibleRows.length>10,'lotus-ag-grid-shell--detail':rowDetail&&!interactive&&!ownsClick()}" :style="fill>=0&&fitHeight&&visibleRows.length>10?{height:fitHeight+'px'}:null"><AgGridVue :key="rowIdentity" class="lotus-ag-grid" :theme="theme" :locale-text="{...AG_GRID_LOCALE_VN,noRowsToShow:empty}" :loading="loading" :row-data="visibleRows" :pinned-bottom-row-data="bottomRows" :get-row-id="getRowId" :column-defs="gridDefs" :dom-layout="visibleRows.length>10?'normal':'autoHeight'" :pagination="paginate" :pagination-page-size="pageSize" :pagination-page-size-selector="false" :suppress-pagination-panel="true" @pagination-changed="pageChanged" :animate-rows="true" :get-row-class="params=>rowClass?rowClass(params.data):(params.data?.shortage_qty>0?'lotus-shortage-row':'')" :enable-cell-text-selection="true" @grid-ready="restoreWidths" @column-resized="resized" @sort-changed="sorted" @model-updated="reportVisible" @row-clicked="open" @row-double-clicked="event=>event.data&&!['__lotus_select','__lotus_stt'].includes(event.column?.getColId?.())&&emit('row-double-open',event.data)" @cell-clicked="event=>{if(!['__lotus_select','__lotus_stt'].includes(event.column?.getColId?.()))emit('cell-open',event)}" @cell-key-down="event=>{if(event.event?.key==='Enter'){open(event);emit('cell-open',event)}}" /></div>
   <div v-if="rows.length>5||Object.keys(activeFilters).length" class="lotus-mobile-filter"><UiSelect v-model="mobileFilter" aria-label="Lọc theo cột"><option value="">Lọc theo cột…</option><option v-for="col in filterable" :key="key(col)" :value="key(col)">{{uiFarmLabel(col.headerName)}}{{activeFilters[key(col)]?' · đang lọc':''}}</option></UiSelect><ExcelHeader v-if="mobileFilterParams" :key="mobileFilter" :params="mobileFilterParams"/></div>
   <div class="lotus-mobile-records"><div v-if="!visibleRows.length&&loading" class="lotus-table-skeleton" role="status" aria-label="Đang tải dữ liệu"><UiSkeleton v-for="n in 3" :key="n" class="lotus-table-skeleton__row"/></div><p v-else-if="!visibleRows.length" role="status">{{empty}}</p>
    <div v-for="(row,index) in pageRows" :key="gridRowId(row,rowKey)" class="lotus-mobile-record-entry" :class="{'lotus-mobile-record-entry--selectable':selectionEnabled}">
     <button v-if="selectionEnabled" type="button" class="lotus-grid-select-toggle" :class="{'is-on':selectedIds.has(getSelectionId(row))}" :aria-pressed="selectedIds.has(getSelectionId(row))" :aria-label="selectedIds.has(getSelectionId(row))?'Bỏ chọn dòng':'Chọn dòng'" @click.stop="setRowSelected(row,!selectedIds.has(getSelectionId(row)))"><span aria-hidden="true">{{selectedIds.has(getSelectionId(row))?'✓':''}}</span></button>
     <component :is="interactive?UiButton:'article'" class="lotus-mobile-record" variant="ghost" @click="interactive?emit('open',row):showDetail(row)">
      <span class="lotus-mobile-record__prefix"><span class="lotus-mobile-record__stt">{{rowIndexOffset+pageStart+index+1}}</span></span>
      <strong>{{value(row,mobileColumns[0]||activeDisplayColumns[0]||columns[0])}}</strong>
      <span v-for="col in mobileColumns.slice(1,mobileLimit||undefined)" :key="col.field||col.headerName" class="lotus-mobile-record-detail"><span>{{uiFarmLabel(col.headerName)}}</span><slot v-if="!interactive&&($slots['cell-'+key(col)]||$slots.cell)" :name="$slots['cell-'+key(col)]?'cell-'+key(col):'cell'" :row="row" :value="raw(row,col)" :column="col" :params="{data:row,value:raw(row,col),colDef:col}"/><UiButton v-else-if="!interactive&&col.colId" variant="link" size="sm" @click.stop="emit('cell-open',{data:row,colDef:col})">{{value(row,col)}}</UiButton><span v-else>{{value(row,col)}}</span></span>
      <LotusIcon v-if="interactive" name="chevron" class="lotus-mobile-record-arrow"/>
     </component>
    </div>
    <dl v-for="total in bottomRows" :key="'total'" class="lotus-mobile-total"><dt>{{totalsLabel}} ({{visibleRows.length}} dòng)</dt><div v-for="col in sumColumns" :key="key(col)" class="lotus-mobile-record-detail"><span>{{uiFarmLabel(col.headerName)}}</span><span>{{totalText(col,total)}}</span></div></dl></div>
   <Pagination v-if="paginate" :start="pageStart" :count="pageRows.length" :total="visibleRows.length" :page-size="pageSize" @update:start="goPage"/>
  </template>
  <ModalForm v-model="detailOpen" :title="detailTitle" readonly width="720px">
   <dl v-if="detail" class="lotus-row-detail">
    <div v-for="col in activeDisplayColumns" :key="key(col)"><dt>{{uiFarmLabel(col.headerName)}}</dt>
     <dd><slot v-if="$slots['cell-'+key(col)]||$slots.cell" :name="$slots['cell-'+key(col)]?'cell-'+key(col):'cell'" :row="detail" :value="raw(detail,col)" :column="col" :params="{data:detail,value:raw(detail,col),colDef:col}"/><template v-else>{{value(detail,col)}}</template></dd></div>
   </dl>
  </ModalForm>
 </div>
</template>
<style>
.lotus-data-table{min-width:0}

.lotus-grid-select-cell,.lotus-grid-stt-cell{display:flex!important;align-items:center;justify-content:center!important;padding-left:2px!important;padding-right:2px!important}
.lotus-data-table .ag-cell:not(.lotus-grid-select-cell):not(.lotus-grid-stt-cell){padding-left:8px!important;padding-right:8px!important;text-overflow:ellipsis;overflow:hidden;white-space:nowrap}
.lotus-data-table .ag-header-cell{padding-left:7px!important;padding-right:7px!important}
.lotus-data-table__export{gap:6px!important;margin-bottom:4px!important}
.lotus-data-table__export button{min-height:29px}
.lotus-data-table .ag-pinned-left-header,.lotus-data-table .ag-pinned-left-cols-container{border-right:1px solid var(--lotus-border)}
.lotus-grid-stt-cell{font-variant-numeric:tabular-nums;color:var(--lotus-muted)}
.lotus-grid-select-header,.lotus-grid-native-select-header{display:flex;align-items:center;justify-content:center;width:100%;height:100%}
.lotus-grid-native-select-header{font-size:11px;font-weight:600;white-space:nowrap}
.lotus-grid-select-toggle{display:inline-flex!important;align-items:center!important;justify-content:center!important;flex:none!important;width:20px!important;height:20px!important;min-width:20px!important;min-height:20px!important;max-height:20px!important;margin:0!important;padding:0!important;border:1px solid var(--lotus-border)!important;border-radius:5px!important;background:var(--lotus-surface)!important;color:#fff!important;font-family:inherit!important;line-height:1!important;cursor:pointer}
.lotus-grid-select-toggle.is-on{border-color:var(--lotus-primary)!important;background:var(--lotus-primary)!important}
.lotus-grid-select-toggle.is-partial{border-color:var(--lotus-primary)!important;background:var(--lotus-soft)!important}
.lotus-grid-select-toggle.is-partial span{background:var(--lotus-primary);width:9px;height:2px}
.lotus-grid-select-toggle:focus-visible{outline:2px solid var(--lotus-primary)!important;outline-offset:2px!important}
.lotus-grid-select-toggle:disabled{opacity:.5;cursor:default}
.lotus-grid-select-toggle span{font-size:15px!important;font-weight:700!important}
.lotus-data-table__selected{display:flex;align-items:center;gap:8px;margin-right:auto;color:var(--lotus-muted);font-size:12px}
.lotus-data-table__selected button{padding:4px 6px;border:0;background:transparent;color:var(--lotus-primary);cursor:pointer;font:inherit}
.lotus-mobile-record__prefix{display:inline-flex;align-items:center;gap:8px;flex:none}
.lotus-mobile-record__stt{min-width:25px;font-variant-numeric:tabular-nums;color:var(--lotus-muted);font-size:12px}
.lotus-mobile-record-entry{position:relative}
.lotus-mobile-record-entry>.lotus-grid-select-toggle{position:absolute;top:calc(var(--lotus-space-3) + var(--lotus-space-1)/2);left:var(--lotus-space-3);z-index:1}
.lotus-mobile-record-entry--selectable .lotus-mobile-record__prefix{padding-left:calc(var(--lotus-space-6) + var(--lotus-space-1))}
.lotus-mobile-record-entry:not(:last-child)>.lotus-mobile-record{border-bottom:1px solid var(--lotus-border)}

.lotus-data-table__export{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:8px;margin:0 0 6px}
.lotus-data-table__export-error{color:var(--lotus-danger);font-size:12px;text-align:right;margin:0 0 6px}
/* AG Grid owns the sole vertical scroll area. Its header and pinned total stay visible. */
.lotus-ag-grid-shell--scroll{overflow:hidden}
.lotus-ag-grid-shell--detail .ag-row:not(.ag-row-pinned){cursor:pointer}
.lotus-ag-grid :is(.ag-grid-pinned-bottom-rows,.ag-floating-bottom) .ag-row{font-weight:650;background:var(--lotus-soft)}
.lotus-row-detail{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px 20px;margin:0}
.lotus-row-detail>div{min-width:0}
.lotus-row-detail dt{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.lotus-row-detail dd{margin:2px 0 0;color:var(--lotus-text);overflow-wrap:anywhere}
.lotus-mobile-total{display:grid;gap:6px;margin:0;padding:12px;font-weight:650;background:var(--lotus-soft);border-top:1px solid var(--lotus-border)}
.lotus-mobile-total dt{font-size:var(--lotus-text-sm)}
.lotus-mobile-total .lotus-mobile-record-detail{display:flex;justify-content:space-between;gap:12px}
</style>
