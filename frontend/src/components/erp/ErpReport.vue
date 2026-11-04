<script setup>
import {computed,reactive,ref,watch} from 'vue'
import LotusField from '../form/LotusField.vue'
import LotusIcon from '../LotusIcon.vue'
import DataTable from '../DataTable.vue'
import WorkspaceSummaryStrip from '../WorkspaceSummaryStrip.vue'
import {Button as UiButton} from '../ui/button'
import {erp,erpFileUrl} from '../../erp-api'
import {display,evaluate,tr} from '../../erp-meta'
import {systemLabel} from '../../system-translations.js'
// A native ERPNext/HRMS report: its filters (parsed from the installed report, never its JavaScript), result and summary.
const props=defineProps({name:{type:String,required:true},label:String,company:String,currency:String,showBack:{type:Boolean,default:true}})
const emit=defineEmits(['back'])
const definition=ref(null),values=reactive({}),result=ref(null),busy=ref(false),error=ref('')
async function load(){
 error.value='';result.value=null;definition.value=null
 try{
  const d=await erp('report_definition',{name:props.name,company:props.company})
  for(const key of Object.keys(values))delete values[key]
  Object.assign(values,d.defaults||{})
  definition.value=d
  await run()
 }catch(e){error.value='Không mở được báo cáo: '+e.message}
}
watch(()=>[props.name,props.company],load,{immediate:true})
const filters=computed(()=>(definition.value?.filters||[]).filter(f=>!f.hidden&&evaluate(f.depends_on,values)))
const options=f=>(Array.isArray(f.options)?f.options:String(f.options||'').split('\n')).filter(o=>o!==''&&o!=null).map(o=>typeof o==='object'?{value:o.value,label:systemLabel(String(o.label??o.value))}:{value:o,label:systemLabel(String(o))})
const kind=f=>({Link:'link','Dynamic Link':'link',MultiSelectList:'link',Select:'select',Date:'date',Check:'checkbox',Int:'number',Float:'number',Currency:'money'})[f.fieldtype]||'text'
async function linkOptions(f,search){
 const linkType=f.fieldtype==='Dynamic Link'||f.dynamic_options?values[f.options==='party_type'||f.dynamic_options?'party_type':f.options]:undefined
 return (await erp('report_link_options',{name:props.name,fieldname:f.fieldname,search,company:props.company,link_type:linkType})).map(r=>({value:r.value,label:r.label&&r.label!==r.value?r.label+' · '+r.value:r.value}))
}
const shown=f=>f.fieldtype==='MultiSelectList'?(values[f.fieldname]||[])[0]||'':values[f.fieldname]??''
function set(f,v){values[f.fieldname]=f.fieldtype==='MultiSelectList'?(v?[v]:[]):f.fieldtype==='Check'?(v?1:0):v}
async function run(){
 const missing=filters.value.filter(f=>f.reqd&&(values[f.fieldname]==null||values[f.fieldname]===''||(Array.isArray(values[f.fieldname])&&!values[f.fieldname].length)))
 if(missing.length){error.value='Chọn: '+missing.map(f=>tr(f.label)).join(', ');return}
 busy.value=true;error.value=''
 try{result.value=await erp('run_report',{name:props.name,filters:{...values},company:props.company})}
 catch(e){error.value=e.message;result.value=null}finally{busy.value=false}
}
// Columns arrive as dicts or "Label:Type/Options:Width" strings; rows as dicts or arrays.
const columnDefs=computed(()=>(result.value?.columns||[]).map((c,i)=>{
 if(typeof c==='string'){const [label,type='Data']=c.split(':');return {fieldname:'col_'+i,label,fieldtype:type.split('/')[0]}}
 return {fieldname:c.fieldname||'col_'+i,label:c.label||c.fieldname,fieldtype:c.fieldtype||'Data',options:c.options}
}))
const rows=computed(()=>(result.value?.result||[]).filter(r=>r&&typeof r==='object').map((r,i)=>{
 const row=Array.isArray(r)?Object.fromEntries(columnDefs.value.map((c,j)=>[c.fieldname,r[j]])):{...r}
 row.__row=i;return row
}))
const currency=row=>row?.currency||row?.account_currency||row?.presentation_currency||values.presentation_currency||props.currency
const columns=computed(()=>columnDefs.value.map((c,i)=>({
 field:c.fieldname,headerName:tr(c.label),minWidth:i===0?220:['Currency','Float','Int'].includes(c.fieldtype)?120:130,...(i===0?{flex:1.5}:{}),
 ...(['Currency','Float','Int','Percent'].includes(c.fieldtype)?{type:'numericColumn'}:{}),sum:false,
 valueFormatter:p=>{const text=display(p.value,c,currency(p.data));return i===0&&p.data?.indent?' '.repeat(Number(p.data.indent))+text:text}
})))
const summary=computed(()=>(result.value?.report_summary||[]).map(s=>({label:tr(s.label),value:display(s.value,{fieldtype:s.datatype},s.currency||props.currency)})))
function exportExcel(){window.open(erpFileUrl('export_report',{name:props.name,filters:{...values},company:props.company}),'_blank','noopener')}
</script>

<template>
 <section class="erp-report" :aria-label="label||name">
  <header class="erp-report__header">
   <UiButton v-if="showBack" variant="ghost" size="sm" aria-label="Về phân hệ" title="Về phân hệ" @click="emit('back')"><LotusIcon name="arrow-left"/></UiButton>
   <h2>{{label||name}}</h2>
   <div class="erp-report__actions"><UiButton :disabled="busy||!definition" @click="run"><LotusIcon name="refresh"/>{{busy?'Đang chạy…':'Chạy báo cáo'}}</UiButton>
    <UiButton v-if="definition?.can_export" variant="outline" :disabled="busy" @click="exportExcel"><LotusIcon name="download"/>Xuất Excel</UiButton></div>
  </header>
  <form v-if="definition" class="erp-report__filters" @submit.prevent="run">
   <template v-for="f in filters" :key="f.fieldname">
    <LotusField v-if="kind(f)==='link'" type="combobox" :label="tr(f.label)" :model-value="shown(f)" :display-value="shown(f)" :fetch-options="search=>linkOptions(f,search)" :required="!!f.reqd" @update:model-value="v=>set(f,v)"/>
    <LotusField v-else-if="kind(f)==='select'" type="select" :label="tr(f.label)" :model-value="values[f.fieldname]??''" :options="options(f)" :searchable="false" :empty-option="f.reqd?null:'—'" @update:model-value="v=>set(f,v)"/>
    <LotusField v-else-if="kind(f)==='checkbox'" type="checkbox" :label="tr(f.label)" :model-value="!!Number(values[f.fieldname])" @update:model-value="v=>set(f,v)"/>
    <LotusField v-else :type="kind(f)" :label="tr(f.label)" :model-value="values[f.fieldname]??''" :required="!!f.reqd" @update:model-value="v=>set(f,v)"/>
   </template>
  </form>
  <p v-if="error" class="erp-form__error" role="alert">{{error}}</p>
  <p v-if="result?.message" class="erp-form__loading">{{result.message}}</p>
  <WorkspaceSummaryStrip v-if="summary.length" :items="summary"/>
  <DataTable v-if="result" :rows="rows" :columns="columns" :loading="busy" row-key="__row" :storage-key="'erp-report:'+name" :totals="false" :fill="24" :export-title="label||name" empty="Báo cáo không có dòng nào với bộ lọc này."/>
 </section>
</template>

<style>
.erp-report{display:grid;gap:12px;min-width:0}
.erp-report__header{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px}
.erp-report__header h2{margin:0;flex:1;font-size:var(--lotus-text-lg,1.1rem)}
.erp-report__header svg{width:16px;height:16px}
.erp-report__actions{display:flex;gap:6px}
.erp-report__filters{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;padding:12px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
</style>
