<script setup>
import {computed,onUnmounted,ref,watch} from 'vue'
import {call} from '../../api'
import ListPage from '../ListPage.vue'
import StockScope from './StockScope.vue'
import {reportColumns,fmt} from '../../stock-columns'
// Báo cáo nhập – xuất – tồn theo số lượng (kỳ, kho). The value version is in Kế toán → Báo cáo → Nhập – xuất – tồn.
const props=defineProps({company:String,warehouse:String,session:Object,warehouses:{type:Array,default:()=>[]},refreshKey:Number})
const emit=defineEmits(['update:warehouse','update:company'])
const monthStart=day=>day?day.slice(0,8)+'01':''
const data=ref(null),busy=ref(false),error=ref(''),search=ref(''),searchDraft=ref(''),from=ref(monthStart(props.session?.today)),to=ref(props.session?.today||'')
const warehouseLabel=id=>props.warehouses.find(w=>w.name===id)?.warehouse_name||id||'—'
const columns=computed(()=>reportColumns(warehouseLabel))
const summary=computed(()=>data.value?[{label:'Kỳ báo cáo',value:data.value.from_date.split('-').reverse().join('/')+' – '+data.value.to_date.split('-').reverse().join('/')},{label:'Số mặt hàng',value:fmt(data.value.item_count)},{label:'Số dòng (vật tư × kho)',value:fmt(data.value.rows.length)}]:[])
let version=0,timer=null
async function load(){
 if(!props.company){version++;data.value=null;return}
 const request=++version;busy.value=true;error.value=''
 try{
  const result=await call('lotus_farm.warehouse.stock_summary',{company:props.company,warehouse:props.warehouse,from_date:from.value,to_date:to.value,search:search.value})
  if(request===version)data.value=result
 }catch(e){if(request===version)error.value='Không tải được báo cáo: '+e.message}
 finally{if(request===version)busy.value=false}
}
watch(searchDraft,value=>{clearTimeout(timer);timer=setTimeout(()=>{const term=String(value||'').trim();if(term!==search.value){search.value=term;load()}},220)})
onUnmounted(()=>clearTimeout(timer))
watch(()=>[props.company,props.warehouse,props.refreshKey],load,{immediate:true})
watch([from,to],load)
defineExpose({refresh:load})
</script>

<template>
 <ListPage title="Báo cáo nhập – xuất – tồn" :rows="data?.rows||[]" :columns="columns" :loading="busy" :error="error" :summary="summary" v-model:search="searchDraft" search-placeholder="Tìm vật tư, nhóm…" @refresh="load"
   storage-key="lotus-stock-report" show-empty-headers empty="Không có phát sinh trong kỳ. Đổi khoảng ngày hoặc kho.">
  <template #filters><StockScope dates v-model:from="from" v-model:to="to" :warehouse="warehouse" :company="company" :warehouses="warehouses" :companies="session?.companies||[]" :disabled="busy" @update:warehouse="emit('update:warehouse',$event)" @update:company="emit('update:company',$event)"/></template>
  <p class="stock-report-note">Báo cáo theo số lượng của đơn vị tồn kho gốc. Giá trị nhập – xuất – tồn xem tại Kế toán → Báo cáo.</p>
 </ListPage>
</template>
