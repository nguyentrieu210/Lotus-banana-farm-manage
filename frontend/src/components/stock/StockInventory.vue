<script setup>
import {computed,onUnmounted,ref,watch} from 'vue'
import {call} from '../../api'
import ListPage from '../ListPage.vue'
import StockScope from './StockScope.vue'
import LotusIcon from '../LotusIcon.vue'
import {Button as UiButton} from '../ui/button'
import {stockColumns} from '../../stock-columns'
import {updateColumnFilter,shiftISODate,hasStockSearchFilters,stockEmptyKind} from '../../stock-filter-state'
// Tồn kho: balance per item with global minimum, demand of the next 7 days and incoming orders. Quick actions open the shared forms.
const props=defineProps({company:String,warehouse:String,session:Object,warehouses:{type:Array,default:()=>[]},refreshKey:Number,canCreate:Boolean,showPurchase:Boolean})
const emit=defineEmits(['update:warehouse','update:company','create','receive','purchase','edit-master'])
const api=(name,args={})=>call('lotus_farm.warehouse.'+name,args)
const data=ref(null),busy=ref(false),error=ref(''),search=ref(''),searchDraft=ref(''),start=ref(0),sort=ref([]),filters=ref({})
const demandWindowDays=7
const demandFrom=ref(props.session?.today||''),demandTo=ref(props.session?.today?shiftISODate(props.session.today,demandWindowDays-1):'')
let version=0,timer=null
async function load(reset=false){
 if(reset)start.value=0
 if(!props.company){version++;data.value=null;return}
 const request=++version;busy.value=true;error.value=''
 try{
  const result=await api('overview',{company:props.company,warehouse:props.warehouse,search:search.value,start:start.value,sort_model:JSON.stringify(sort.value),column_filters:JSON.stringify(filters.value),from_date:demandFrom.value,to_date:demandTo.value})
  if(request!==version)return
  data.value=result
  // A filter can leave the current page empty: jump back to the last page with rows.
  if(start.value>0&&!result.items?.length&&result.total_count>0){start.value=Math.floor((result.total_count-1)/50)*50;return load()}
 }catch(e){if(request===version)error.value='Không tải được dữ liệu mới: '+e.message}
 finally{if(request===version)busy.value=false}
}
watch(searchDraft,value=>{clearTimeout(timer);timer=setTimeout(()=>{const term=String(value||'').trim();if(term!==search.value){search.value=term;load(true)}},220)})
onUnmounted(()=>clearTimeout(timer))
watch(()=>[props.company,props.warehouse,props.refreshKey],()=>{filters.value={};load(true)},{immediate:true})
const hasFilters=computed(()=>hasStockSearchFilters(search.value,filters.value)||!!props.warehouse)
function clearFilters(){filters.value={};search.value='';searchDraft.value='';sort.value=[];if(props.warehouse)emit('update:warehouse','');else load(true)}
const empty=computed(()=>{const kind=stockEmptyKind({company:props.company,warehouseCount:props.warehouses.length,catalogueCount:data.value?.catalogue_count||0,filteredCount:data.value?.total_count||0,loading:busy.value||(!data.value&&!!props.company)})
 return {'no-company':'Chọn công ty để xem tồn kho.','no-warehouse':'Chưa có kho hoạt động.','no-items':'Chưa có vật tư trong danh mục.'}[kind]||'Không có vật tư khớp bộ lọc. Bỏ lọc để xem lại danh sách.'})
const permissions=computed(()=>props.session?.permissions||{})
const actions=[{kind:'receipt-order',label:'Nhập theo đơn',icon:'receive',doctype:'Purchase Receipt'},{kind:'receipt',label:'Nhập không theo đơn',icon:'download',doctype:'Stock Entry'},{kind:'issue',label:'Xuất kho',icon:'issue',doctype:'Stock Entry'},{kind:'transfer',label:'Chuyển kho',icon:'transfer',doctype:'Stock Entry'},{kind:'count',label:'Kiểm kê',icon:'check',doctype:'Stock Reconciliation'}]
function act(action){if(action.kind==='receipt-order')emit('receive');else emit('create',action.kind)}
defineExpose({refresh:()=>load()})
</script>

<template>
 <ListPage title="Tồn kho" class="stock-inventory-table" :rows="data?.items||[]" :columns="stockColumns" :loading="busy" :error="error" v-model:search="searchDraft" search-placeholder="Tìm vật tư…"
   paged :start="start" :total="data?.total_count" :has-more="data?.has_more" @update:start="value=>{start=value;load()}" @refresh="load()"
   storage-key="lotus-stock-inventory" :show-empty-headers="(data?.catalogue_count??0)>0" server-sort interactive :filter-values="data?.filter_values" :server-filters="filters" :empty="empty"
   @sort="model=>{sort=model;load(true)}" @filter="({field,values})=>{filters=updateColumnFilter(filters,field,values);load(true)}" @open="row=>emit('edit-master','item',row.name)">
  <template #filters><StockScope :warehouse="warehouse" :company="company" :warehouses="warehouses" :companies="session?.companies||[]" :disabled="busy" @update:warehouse="emit('update:warehouse',$event)" @update:company="emit('update:company',$event)"/><UiButton v-if="hasFilters" variant="outline" @click="clearFilters">Bỏ lọc</UiButton></template>
  <template #actions><div class="stock-quick-actions" role="group" aria-label="Thao tác kho nhanh">
   <UiButton v-if="showPurchase" variant="outline" class="stock-quick-action" :disabled="!company||!permissions['Purchase Order']" @click="emit('purchase')"><LotusIcon name="cart"/>Tạo đơn mua</UiButton>
   <UiButton v-for="action in actions" :key="action.kind" variant="outline" class="stock-quick-action" :disabled="!canCreate||!permissions[action.doctype]" @click="act(action)"><LotusIcon :name="action.icon"/>{{action.label}}</UiButton>
  </div></template>
 </ListPage>
</template>
