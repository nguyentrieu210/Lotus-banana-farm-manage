<script setup>
import {computed,onUnmounted,ref,watch} from 'vue'
import {call} from '../../api'
import ListPage from '../ListPage.vue'
import StockScope from './StockScope.vue'
import {Button as UiButton} from '../ui/button'
import {movementColumns} from '../../stock-columns'
import {updateColumnFilter,hasStockSearchFilters} from '../../stock-filter-state'
// Sổ kho: every stock movement (thẻ kho) with quantity before/after; search an item to read its card.
const props=defineProps({company:String,warehouse:String,session:Object,warehouses:{type:Array,default:()=>[]},refreshKey:Number})
const emit=defineEmits(['update:warehouse','update:company','open-document'])
const data=ref(null),busy=ref(false),error=ref(''),search=ref(''),searchDraft=ref(''),start=ref(0),sort=ref([]),filters=ref({}),from=ref(''),to=ref('')
const warehouseLabel=id=>props.warehouses.find(w=>w.name===id)?.warehouse_name||id||'—'
const columns=computed(()=>movementColumns(warehouseLabel))
const columnPresets=[
 {id:'compact',label:'Gọn',visible:['posting_date','voucher_no','content','item_name','in_qty','out_qty','qty_after_transaction']},
 {id:'production',label:'Theo sản xuất',visible:['posting_date','voucher_no','item_name','content','usage_area','work_team','receiver','out_qty']},
 {id:'full',label:'Đầy đủ',visible:['posting_date','voucher_no','transaction_type','content','item_name','item_code','warehouse','stock_uom','opening_qty','in_qty','out_qty','qty_after_transaction','receiver','usage_area','work_team']}
]
let version=0,timer=null
async function load(reset=false){
 if(reset)start.value=0
 if(!props.company){version++;data.value=null;return}
 const request=++version;busy.value=true;error.value=''
 try{
  const result=await call('lotus_farm.warehouse.movements',{company:props.company,warehouse:props.warehouse,search:search.value,from_date:from.value,to_date:to.value,start:start.value,sort_model:JSON.stringify(sort.value),column_filters:JSON.stringify(filters.value)})
  if(request===version)data.value=result
 }catch(e){if(request===version)error.value='Không tải được sổ kho: '+e.message}
 finally{if(request===version)busy.value=false}
}
watch(searchDraft,value=>{clearTimeout(timer);timer=setTimeout(()=>{const term=String(value||'').trim();if(term!==search.value){search.value=term;load(true)}},220)})
onUnmounted(()=>clearTimeout(timer))
watch(()=>[props.company,props.warehouse,props.refreshKey],()=>load(true),{immediate:true})
watch([from,to],()=>load(true))
const hasFilters=computed(()=>hasStockSearchFilters(search.value,filters.value)||!!from.value||!!to.value||!!props.warehouse)
function clearFilters(){filters.value={};sort.value=[];search.value='';searchDraft.value='';from.value='';to.value='';if(props.warehouse)emit('update:warehouse','');else load(true)}
function open(row){if(['Stock Entry','Stock Reconciliation','Purchase Receipt'].includes(row.voucher_type))emit('open-document',row.voucher_type,row.voucher_no);else error.value='Loại phiếu này chưa có form chi tiết trong màn hình kho.'}
// Export every permitted movement matching the current search, date and column filters.
async function exportLedgerRows(){
 const args={company:props.company,warehouse:props.warehouse,search:search.value,from_date:from.value,to_date:to.value,sort_model:JSON.stringify(sort.value),column_filters:JSON.stringify(filters.value)}
 const rows=[]
 for(let offset=0;;offset+=50){
  const page=await call('lotus_farm.warehouse.movements',{...args,start:offset})
  rows.push(...(page.rows||[]))
  if(!page.has_more)return rows
  if(rows.length>=20000)throw new Error('Sổ kho có trên 20.000 dòng. Hãy chọn khoảng ngày ngắn hơn để xuất Excel.')
  if(!page.rows?.length)throw new Error('Không tải đủ dữ liệu sổ kho để xuất.')
 }
}
defineExpose({refresh:()=>load()})
</script>

<template>
 <ListPage title="Sổ kho" :rows="data?.rows||[]" :columns="columns" :loading="busy" :error="error" v-model:search="searchDraft" search-placeholder="Tìm vật tư/phiếu…"
   paged :start="start" :total="data?.total_count" :has-more="data?.has_more" @update:start="value=>{start=value;load()}" @refresh="load()"
   storage-key="lotus-stock-ledger" :column-presets="columnPresets" :export-rows="exportLedgerRows" export-title="So-kho" show-empty-headers server-sort interactive :filter-values="data?.filter_values" :server-filters="filters" empty="Không có phát sinh nhập xuất phù hợp. Thử bỏ lọc hoặc thay đổi ngày."
   @sort="model=>{sort=model;load(true)}" @filter="({field,values})=>{filters=updateColumnFilter(filters,field,values);load(true)}" @open="open">
  <template #filters><StockScope dates v-model:from="from" v-model:to="to" :warehouse="warehouse" :company="company" :warehouses="warehouses" :companies="session?.companies||[]" :disabled="busy" @update:warehouse="emit('update:warehouse',$event)" @update:company="emit('update:company',$event)"/><UiButton v-if="hasFilters" variant="outline" @click="clearFilters">Bỏ lọc</UiButton></template>
 </ListPage>
</template>
