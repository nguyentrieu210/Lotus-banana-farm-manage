<script setup>
import {computed,onUnmounted,ref,watch} from 'vue'
import {call} from '../../api'
import ListPage from '../ListPage.vue'
import StockScope from './StockScope.vue'
import LotusIcon from '../LotusIcon.vue'
import {Button as UiButton} from '../ui/button'
import {documentColumns} from '../../stock-columns'
import {updateColumnFilter,hasStockSearchFilters} from '../../stock-filter-state'
// Nhập kho · Xuất kho · Chuyển kho · Kiểm kê: one list per kind of stock document, each with its own create buttons.
const props=defineProps({kind:{type:String,required:true},company:String,warehouse:String,session:Object,warehouses:{type:Array,default:()=>[]},refreshKey:Number,canCreate:Boolean})
const emit=defineEmits(['update:warehouse','update:company','create','receive','open-document'])
const titles={receipts:'Phiếu nhập kho',issues:'Phiếu xuất kho',transfers:'Phiếu chuyển kho',counts:'Phiếu kiểm kê'}
const creators={
 receipts:[{kind:'receipt-order',label:'Nhập theo đơn mua',icon:'receive',doctype:'Purchase Receipt'},{kind:'receipt',label:'Nhập không theo đơn',icon:'download',doctype:'Stock Entry'}],
 issues:[{kind:'issue',label:'Tạo phiếu xuất',icon:'issue',doctype:'Stock Entry'}],
 transfers:[{kind:'transfer',label:'Tạo phiếu chuyển',icon:'transfer',doctype:'Stock Entry'}],
 counts:[{kind:'count',label:'Tạo phiếu kiểm kê',icon:'check',doctype:'Stock Reconciliation'}]
}
const data=ref(null),busy=ref(false),error=ref(''),search=ref(''),searchDraft=ref(''),start=ref(0),sort=ref([]),filters=ref({}),from=ref(''),to=ref('')
const warehouseLabel=id=>props.warehouses.find(w=>w.name===id)?.warehouse_name||id||'—'
const columns=computed(()=>documentColumns(warehouseLabel))
let version=0,timer=null
async function load(reset=false){
 if(reset)start.value=0
 if(!props.company){version++;data.value=null;return}
 const request=++version;busy.value=true;error.value=''
 try{
  const result=await call('lotus_farm.warehouse.documents',{company:props.company,warehouse:props.warehouse,kind:props.kind,search:search.value,from_date:from.value,to_date:to.value,start:start.value,sort_model:JSON.stringify(sort.value),column_filters:JSON.stringify(filters.value)})
  if(request===version)data.value=result
 }catch(e){if(request===version)error.value='Không tải được danh sách phiếu: '+e.message}
 finally{if(request===version)busy.value=false}
}
watch(searchDraft,value=>{clearTimeout(timer);timer=setTimeout(()=>{const term=String(value||'').trim();if(term!==search.value){search.value=term;load(true)}},220)})
onUnmounted(()=>clearTimeout(timer))
watch(()=>[props.kind,props.company,props.warehouse,props.refreshKey],()=>load(true),{immediate:true})
watch([from,to],()=>load(true))
const hasFilters=computed(()=>hasStockSearchFilters(search.value,filters.value)||!!from.value||!!to.value||!!props.warehouse)
function clearFilters(){filters.value={};sort.value=[];search.value='';searchDraft.value='';from.value='';to.value='';if(props.warehouse)emit('update:warehouse','');else load(true)}
function act(action){if(action.kind==='receipt-order')emit('receive');else emit('create',action.kind)}
defineExpose({refresh:()=>load()})
</script>

<template>
 <ListPage :title="titles[kind]" :rows="data?.rows||[]" :columns="columns" :loading="busy" :error="error" v-model:search="searchDraft" search-placeholder="Tìm số phiếu…"
   paged :start="start" :total="data?.total_count" :has-more="data?.has_more" @update:start="value=>{start=value;load()}" @refresh="load()"
   :storage-key="'lotus-stock-documents-'+kind" show-empty-headers server-sort interactive :filter-values="data?.filter_values" :server-filters="filters" empty="Không có phiếu phù hợp. Thử bỏ lọc hoặc thay đổi khoảng ngày."
   @sort="model=>{sort=model;load(true)}" @filter="({field,values})=>{filters=updateColumnFilter(filters,field,values);load(true)}" @open="row=>emit('open-document',row.doctype,row.name)">
  <template #filters><StockScope dates v-model:from="from" v-model:to="to" :warehouse="warehouse" :company="company" :warehouses="warehouses" :companies="session?.companies||[]" :disabled="busy" @update:warehouse="emit('update:warehouse',$event)" @update:company="emit('update:company',$event)"/><UiButton v-if="hasFilters" variant="outline" @click="clearFilters">Bỏ lọc</UiButton></template>
  <template #actions><UiButton v-for="(action,index) in creators[kind]" :key="action.kind" :variant="index?'outline':'default'" :disabled="!canCreate||!session?.permissions?.[action.doctype]" @click="act(action)"><LotusIcon :name="action.icon"/>{{action.label}}</UiButton></template>
 </ListPage>
</template>
