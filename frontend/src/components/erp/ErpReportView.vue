<script setup>
import {computed,onBeforeUnmount,onMounted,ref,watch} from 'vue'
import {call} from '../../api'
import {visibleField,requiredField} from '../../erp-form.js'
import ErpField from './ErpField.vue'
import DataTable from '../DataTable.vue'
import LotusChart from '../LotusChart.vue'
import {Button} from '../ui/button'
const props=defineProps({name:{type:String,required:true},company:String,initialFilters:Object})
const emit=defineEmits(['open-document','open-report','company','filters','error'])
const definition=ref(null),filters=ref({}),result=ref(null),loading=ref(false),error=ref(''),dirty=ref(false),collapsed=ref(new Set()),prepared=ref('')
let version=0,timer,pollTimer,initializing=false
const preparedStatus=ref('')
const api=(method,args={},write=false)=>call('lotus_farm.erp_workbench.'+method,args,write,{timeoutMs:write?90000:60000})
const fields=computed(()=>(definition.value?.filters||[]).filter(f=>visibleField(f,filters.value)))
const invalid=computed(()=>fields.value.some(f=>requiredField(f,filters.value)&&((filters.value[f.fieldname]??'')===''||Array.isArray(filters.value[f.fieldname])&&!filters.value[f.fieldname].length)))
const nativeColumns=computed(()=>(result.value?.columns||[]).map((c,i)=>typeof c==='string'?{fieldname:'col_'+i,label:c.split(':')[0],fieldtype:(c.split(':')[1]||'Data').split('/')[0],options:(c.split(':')[1]||'').split('/')[1]}:{...c,fieldname:c.fieldname||'col_'+i}))
const columns=computed(()=>nativeColumns.value.map(c=>({field:c.fieldname,headerName:c.label||c.fieldname,minWidth:c.width||(['Currency','Float','Int','Percent'].includes(c.fieldtype)?140:210),flex:c.fieldname==='account'?2:1})))
const allRows=computed(()=>(result.value?.result||[]).map((row,i)=>({...Array.isArray(row)?Object.fromEntries(nativeColumns.value.map((c,j)=>[c.fieldname,row[j]])):row,_erp_row:String(i)})))
const rows=computed(()=>{let hiddenAt=null;return allRows.value.filter(r=>{const indent=Number(r.indent||0);if(hiddenAt!==null&&indent>hiddenAt)return false;hiddenAt=collapsed.value.has(r._erp_row)?indent:null;return true})})
const chart=computed(()=>result.value?.chart?.data||{})
const chartSeries=computed(()=>(chart.value.datasets||[]).map(s=>({name:s.name||'Giá trị',data:s.values||[]})))
const exportUrl=computed(()=>'/api/method/lotus_farm.erp_workbench.export_report?'+new URLSearchParams({name:props.name,company:props.company||'',filters:JSON.stringify(filters.value)}))
const number=(v,decimals=2)=>Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:decimals})
function format(value,column,row){if(value==null||value==='')return '';if(['Currency','Float','Percent','Int'].includes(column?.fieldtype))return number(value,column.fieldtype==='Int'?0:column.precision??2)+(column.fieldtype==='Percent'?' %':'');return String(value).replace(/<[^>]*>/g,'')}
function summaryValue(s){return s.datatype==='Currency'?number(s.value)+' '+(s.currency||filters.value.presentation_currency||''):typeof s.value==='number'?number(s.value):s.value}
function toggle(row){const next=new Set(collapsed.value);next.has(row._erp_row)?next.delete(row._erp_row):next.add(row._erp_row);collapsed.value=next}
function hasChildren(row){const index=Number(row._erp_row);return Number(allRows.value[index+1]?.indent||0)>Number(row.indent||0)}
function linkFor(column,row,value){if(!column||!value||row.is_total_row)return null;if(column.fieldname==='account'){if(row.account&&row.account_name&&!String(row.account).startsWith("'"))return {report:'General Ledger',filters:{...filters.value,account:[row.account]}};return null};if(column.fieldtype==='Link'&&column.options)return {doctype:column.options,name:value};if(column.fieldtype==='Dynamic Link'&&row[column.options])return {doctype:row[column.options],name:value};return null}
function follow(column,row,value){const link=linkFor(column,row,value);if(link?.report)emit('open-report',{name:link.report,filters:link.filters});else if(link)emit('open-document',link)}
async function load(){clearTimeout(pollTimer);prepared.value='';preparedStatus.value='';const id=++version;loading.value=true;error.value='';initializing=true;result.value=null;try{const d=await api('report_definition',{name:props.name,company:props.company});if(id!==version)return;definition.value=d;filters.value={...d.defaults,...props.initialFilters,...(props.company?{company:props.company}:{})};for(const field of d.filters||[])if(field.fieldtype==='MultiSelectList'&&filters.value[field.fieldname]&&!Array.isArray(filters.value[field.fieldname]))filters.value[field.fieldname]=[filters.value[field.fieldname]];collapsed.value=new Set();await run(id)}catch(e){if(id===version)error.value=e.message}finally{if(id===version){loading.value=false;initializing=false;dirty.value=false}}}
async function run(existingVersion){if(!definition.value||invalid.value)return;const id=existingVersion??++version;loading.value=true;error.value='';try{const r=await api('run_report',{name:props.name,filters:JSON.stringify(filters.value),company:props.company});if(id!==version)return;result.value=r;dirty.value=false;emit('filters',{...filters.value})}catch(e){if(id===version){error.value=e.message;result.value=null}}finally{if(id===version)loading.value=false}}
async function change(field,value){filters.value={...filters.value,[field.fieldname]:value};dirty.value=true;if(field.fieldname==='party_type')filters.value.party=[];if(field.fieldname==='company'){emit('company',value);return}if(['from_fiscal_year','to_fiscal_year'].includes(field.fieldname)&&value){try{const r=await api('document',{doctype:'Fiscal Year',name:value});filters.value={...filters.value,[field.fieldname==='from_fiscal_year'?'period_start_date':'period_end_date']:r.doc[field.fieldname==='from_fiscal_year'?'year_start_date':'year_end_date']}}catch(e){error.value=e.message}}clearTimeout(timer);if(!initializing&&!invalid.value)timer=setTimeout(()=>run(),450)}
async function prepare(){if(invalid.value||loading.value)return;loading.value=true;error.value='';try{const r=await api('prepare_report',{name:props.name,filters:JSON.stringify(filters.value),company:props.company},true);prepared.value=typeof r==='string'?r:r?.name||'';preparedStatus.value='Đang chờ xử lý';pollPrepared(version)}catch(e){error.value=e.message}finally{loading.value=false}}
async function pollPrepared(id){if(!prepared.value||id!==version)return;try{const r=await api('prepared_result',{name:prepared.value,company:props.company});if(id!==version)return;preparedStatus.value=r.status;if(r.status==='Completed'){result.value=r.result;dirty.value=false;return}if(r.status==='Failed'){error.value=r.error||'Báo cáo nền chưa hoàn thành.';return}pollTimer=setTimeout(()=>pollPrepared(id),5000)}catch(e){if(id===version)error.value=e.message}}
function print(){window.print()}
watch(()=>[props.name,props.company],load)
onMounted(load)
onBeforeUnmount(()=>{version++;clearTimeout(timer);clearTimeout(pollTimer)})
defineExpose({refresh:()=>run(),hasChanges:()=>false,discardChanges:()=>{}})
</script>
<template>
 <section class="erp-report" :aria-busy="loading">
  <div class="erp-report-toolbar">
   <div class="erp-report-filters"><ErpField v-for="field in fields" :key="field.fieldname" :field="field" :model-value="filters[field.fieldname]" :doc="filters" :company="company" :report="name" @update:model-value="change(field,$event)"/></div>
   <div class="erp-toolbar-actions"><Button variant="outline" :disabled="loading||invalid" @click="run()">{{loading?'Đang tải…':'Làm mới'}}</Button><Button v-if="definition?.prepared_report" variant="outline" :disabled="loading||invalid" @click="prepare">Chạy nền</Button><Button v-if="definition?.can_export&&result" as="a" variant="outline" :href="exportUrl" download>Excel toàn bộ</Button><Button v-if="result" variant="outline" @click="print">In</Button></div>
  </div>
  <p v-if="error" role="alert" class="erp-error">{{error}}</p><p v-if="loading" role="status">Đang tải báo cáo…</p><p v-if="dirty&&!loading" role="status">Bộ lọc đã đổi. Làm mới để xem kết quả.</p><p v-if="prepared" role="status">Báo cáo nền {{prepared}}: {{preparedStatus}}.</p>
  <template v-if="result">
   <p v-if="result.message" class="erp-report-message">{{result.message}}</p>
   <div v-if="result.report_summary?.length" class="erp-report-summary"><div v-for="(s,i) in result.report_summary" :key="i" :class="{'is-negative':s.indicator==='Red'||Number(s.value)<0}"><span>{{s.label}}</span><strong>{{summaryValue(s)}}</strong></div></div>
   <LotusChart v-if="chart.labels?.length&&chartSeries.length" :title="definition?.title||name" :kind="result.chart.type==='line'?'line':'bar'" :categories="chart.labels" :series="chartSeries" :height="240"/>
   <DataTable :rows="rows" :columns="columns" :loading="loading" row-key="_erp_row" :storage-key="'erp-report-'+name" :row-class="row=>row.is_group?'erp-report-group':''" empty="Báo cáo không có phát sinh theo bộ lọc.">
    <template #cell="{row,value,column}"><span class="erp-report-value" :style="column.field==='account'?{paddingLeft:Number(row.indent||0)*14+'px'}:undefined"><Button v-if="column.field==='account'&&hasChildren(row)" variant="ghost" size="sm" :aria-label="(collapsed.has(row._erp_row)?'Mở ':'Thu gọn ')+(row.account_name||value)" @click="toggle(row)">{{collapsed.has(row._erp_row)?'+':'−'}}</Button><Button v-if="linkFor(nativeColumns.find(c=>c.fieldname===column.field),row,value)" variant="link" size="sm" @click="follow(nativeColumns.find(c=>c.fieldname===column.field),row,value)">{{column.field==='account'?(row.account_name||format(value,nativeColumns.find(c=>c.fieldname===column.field),row)):format(value,nativeColumns.find(c=>c.fieldname===column.field),row)}}</Button><span v-else>{{format(value,nativeColumns.find(c=>c.fieldname===column.field),row)}}</span></span></template>
   </DataTable>
   <footer class="erp-list-footer"><span>{{allRows.length}} dòng</span><span>{{filters.presentation_currency||''}}</span></footer>
  </template>
 </section>
</template>
