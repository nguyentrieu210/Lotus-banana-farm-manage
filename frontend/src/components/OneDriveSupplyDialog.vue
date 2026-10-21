<script setup>
import {computed,ref,watch} from 'vue'
import {call,consoleAPI} from '../api'
import WorkspaceModal from './WorkspaceModal.vue'
import DataTable from './DataTable.vue'
import LinkPicker from './LinkPicker.vue'
import {Button as UiButton} from './ui/button'
import {Input as UiInput} from './ui/input'
import {FormField} from './ui/form-field'
import {DatePicker} from './ui/date-picker'

const props=defineProps({source:Object,month:String,company:String,canPrepare:Boolean})
const emit=defineEmits(['close','created','edit'])
const periodStart=ref(''),periodEnd=ref(''),outputs=ref([]),result=ref(null),error=ref(''),busy=ref(false)
let request=0,eventId=''
const number=value=>value==null?'—':Number(value).toLocaleString('vi-VN',{maximumFractionDigits:3})
const sourceId=computed(()=>props.source?.source||props.source?.source_cut_operation||'')
const formKey=computed(()=>JSON.stringify([sourceId.value,props.source?.source_hash,periodStart.value,periodEnd.value,outputs.value]))
const complete=computed(()=>props.canPrepare&&sourceId.value&&periodStart.value&&periodEnd.value&&periodStart.value<=periodEnd.value&&(!props.source?.window_start||periodStart.value>=props.source.window_start)&&(!props.source?.window_end||periodEnd.value<=props.source.window_end)&&outputs.value.length&&outputs.value.every(row=>row.item&&row.packout_profile&&Number(row.share_percent)>0)&&outputs.value.reduce((sum,row)=>sum+Number(row.share_percent||0),0)<=100.000001)
const columns=[{field:'source_cut_operation',headerName:'Đợt cắt bắp gốc'},{field:'period_start_date',headerName:'Từ'},{field:'period_end_date',headerName:'Đến'},...['source_bunch_qty','gross_forecast_kg','packed_forecast_kg'].map((field,index)=>({field,headerName:['Buồng nguồn','Kg nguyên buồng','Kg dự thành phẩm'][index],valueFormatter:({value})=>number(value)}))]
function reset(){
 request++;busy.value=false;error.value='';result.value=null;eventId=''
 const start=props.source?.window_start||'',end=props.source?.window_end||start
 const month=props.month||props.source?.month
 const monthStart=month?month+'-01':start
 const monthEnd=month?new Date(Date.UTC(Number(month.slice(0,4)),Number(month.slice(5,7)),0)).toISOString().slice(0,10):end
 periodStart.value=start&&monthStart?([start,monthStart].sort().at(-1)):start
 periodEnd.value=end&&monthEnd?([end,monthEnd].sort()[0]):end
 outputs.value=[{item:'',packout_profile:'',share_percent:100}]
}
watch(()=>[props.source,props.month],reset,{immediate:true})
watch(formKey,()=>{request++;result.value=null;error.value='';eventId='';busy.value=false})
async function linkOptions(doctype,search,row){return consoleAPI('link_options',{doctype,search,company:props.company||null,farm:props.source?.farm,item:doctype==='Packout Profile'?row.item:null,approved_only:doctype==='Packout Profile'?1:0,on_date:periodStart.value||null})}
function newEvent(){return globalThis.crypto?.randomUUID?.()||`onedrive-cut-${Date.now()}-${Math.random().toString(36).slice(2)}`}
async function prepare(preview){
 if(!complete.value||busy.value||(!preview&&!result.value))return
 const token=++request,key=formKey.value
 if(!eventId)eventId=newEvent()
 busy.value=true;error.value=''
 try{
  const response=await call('lotus_farm.onedrive_supply.prepare_cut_forecasts',{
   source_cuts:[sourceId.value],period_start:periodStart.value,period_end:periodEnd.value,
   output_mapping:outputs.value.map(row=>({...row,share_percent:Number(row.share_percent)})),
   client_event_id:eventId,preview:preview?1:0,
   expected_source_hash:preview?null:(result.value?.source_hash||result.value?.drafts?.[0]?.source_hash||null),
  },true)
  if(token!==request||key!==formKey.value)return
  if(preview)result.value=response
  else{emit('created',response);emit('close')}
 }catch(e){if(token===request)error.value=e.message}
 finally{if(token===request)busy.value=false}
}
</script>

<template>
 <WorkspaceModal :model-value="!!source" title="Dự thu từ buồng đã cắt bắp" :busy="busy" @update:model-value="!$event&&emit('close')">
  <template v-if="source">
   <dl class="cut-evidence"><div><dt>Đợt cắt bắp gốc</dt><dd>{{sourceId}}</dd></div><div><dt>Vườn / lô / thửa</dt><dd>{{source.farm}} / {{source.farm_block}} / {{source.farm_plot||'—'}}</dd></div><div><dt>Vụ / đợt chồi</dt><dd>{{source.crop_cycle}} / {{source.sucker_selection_batch||'Chưa có hồ sơ chồi'}}</dd></div><div><dt>Cửa sổ dự thu</dt><dd>{{source.window_start}} – {{source.window_end}}</dd></div><div><dt>Buồng còn lại</dt><dd>{{number(source.remaining_bunch_qty)}}</dd></div><div><dt>Phiên bản thông số</dt><dd>{{source.process_adoption}}</dd></div></dl>
   <div class="cut-actions"><UiButton variant="outline" @click="emit('edit','Bunch Operation',sourceId)">Mở đợt cắt bắp gốc</UiButton></div>
   <template v-if="canPrepare">
    <div class="cut-period"><FormField label="Dự thu từ" required v-slot="field"><DatePicker v-bind="field" v-model="periodStart" :min="source.window_start" :max="source.window_end" label="Dự thu từ"/></FormField><FormField label="Dự thu đến" required v-slot="field"><DatePicker v-bind="field" v-model="periodEnd" :min="periodStart||source.window_start" :max="source.window_end" label="Dự thu đến"/></FormField></div>
    <div v-for="(row,index) in outputs" :key="index" class="cut-output">
     <FormField label="Sản phẩm" required v-slot="field"><LinkPicker v-bind="field" v-model="row.item" :fetch-options="search=>linkOptions('Item',search,row)" @update:model-value="row.packout_profile=''"/></FormField>
     <FormField label="Hệ số đóng gói đã duyệt" required v-slot="field"><LinkPicker v-bind="field" v-model="row.packout_profile" :disabled="!row.item" :fetch-options="search=>linkOptions('Packout Profile',search,row)"/></FormField>
     <FormField label="Tỷ phần kg sơ chế (%)" required v-slot="field"><UiInput v-bind="field" v-model.number="row.share_percent" type="number" min="0" max="100" step="any"/></FormField>
     <UiButton v-if="outputs.length>1" variant="outline" @click="outputs.splice(index,1)">Xóa dòng {{index+1}}</UiButton>
    </div>
    <div class="cut-actions"><UiButton variant="outline" :disabled="busy" @click="outputs.push({item:'',packout_profile:'',share_percent:0})">Thêm sản phẩm</UiButton><UiButton :disabled="!complete||busy" @click="prepare(true)">Xem trước dự thu</UiButton></div>
    <p v-if="!complete" class="notice">Chọn sản phẩm, hệ số đã duyệt và tổng phân bổ lớn hơn 0%, tối đa 100% trước khi xem trước.</p>
    <template v-if="result"><p v-for="(issue,index) in result.issues||[]" :key="index" class="error">{{typeof issue==='string'?issue:issue.message}}</p><DataTable :rows="result.drafts||[]" :columns="columns"/><div class="cut-actions"><UiButton :disabled="busy||!result.drafts?.length||!!result.issues?.length" @click="prepare(false)">Tạo dự thu nháp</UiButton></div></template>
   </template>
   <p v-if="error" role="alert" class="error">{{error}}</p>
  </template>
 </WorkspaceModal>
</template>

<style scoped>
.cut-evidence{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--lotus-space-2);margin:0}.cut-evidence dt{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}.cut-evidence dd{margin:0;overflow-wrap:anywhere}.cut-actions{display:flex;gap:var(--lotus-space-2);padding:var(--lotus-space-2) 0;overflow-x:auto}.cut-actions>*{flex:0 0 auto}.cut-period{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--lotus-space-3)}.cut-output{display:grid;grid-template-columns:1fr 1fr 10rem auto;gap:var(--lotus-space-2);align-items:end;margin:var(--lotus-space-2) 0}
@media(max-width:640px){.cut-evidence,.cut-period,.cut-output{grid-template-columns:1fr}}
</style>
