<script setup>
import {computed,onUnmounted,ref,watch} from 'vue'
import ListPage from '../ListPage.vue'
import LotusIcon from '../LotusIcon.vue'
import {Button as UiButton} from '../ui/button'
import {erp} from '../../erp-api'
import {display,docstatusLabel,tr} from '../../erp-meta'
// Any ERP document list: server search, sort and pages (native list permissions), columns from the DocType list view.
const props=defineProps({doctype:{type:String,required:true},label:String,company:String,currency:String,canCreate:Boolean})
const emit=defineEmits(['open','new'])
const data=ref(null),busy=ref(false),error=ref(''),search=ref(''),searchDraft=ref(''),start=ref(0),pageSize=ref(50),sort=ref('modified desc')
let version=0,timer=null
async function load(reset=false){
 if(reset)start.value=0
 const request=++version;busy.value=true;error.value=''
 try{
  const result=await erp('listing',{doctype:props.doctype,company:props.company,search:search.value,start:start.value,length:pageSize.value||100,sort:sort.value})
  if(request===version)data.value=result
 }catch(e){if(request===version)error.value='Không tải được danh sách: '+e.message}
 finally{if(request===version)busy.value=false}
}
watch(()=>[props.doctype,props.company],()=>{sort.value='modified desc';search.value='';searchDraft.value='';load(true)},{immediate:true})
watch(searchDraft,value=>{clearTimeout(timer);timer=setTimeout(()=>{const term=String(value||'').trim();if(term!==search.value){search.value=term;load(true)}},250)})
onUnmounted(()=>clearTimeout(timer))
const columns=computed(()=>(data.value?.columns||[]).filter(c=>c.fieldname!=='modified').map(c=>({
 field:c.fieldname,headerName:c.fieldname==='name'?'Số / mã':c.fieldname==='docstatus'?'Trạng thái chứng từ':tr(c.label),
 minWidth:c.fieldname==='name'?170:['Currency','Float','Int'].includes(c.fieldtype)?120:130,
 ...(c.fieldname==='name'?{flex:1.2}:{}),
 ...(['Currency','Float','Int','Percent'].includes(c.fieldtype)?{type:'numericColumn'}:{}),
 valueFormatter:p=>c.fieldname==='docstatus'?docstatusLabel(p.value):display(p.value,c,p.data?.currency||props.currency)
})))
// Server sort: one column at a time, like the native list.
function sorted(model){const first=model?.[0];sort.value=first?first.colId+' '+first.sort:'modified desc';load(true)}
async function exportRows(){
 const rows=[]
 for(let offset=0;;offset+=100){
  const page=await erp('listing',{doctype:props.doctype,company:props.company,search:search.value,start:offset,length:100,sort:sort.value})
  rows.push(...page.rows)
  if(!page.has_more)return rows
  if(rows.length>=20000)throw new Error('Danh sách có trên 20.000 dòng. Lọc hẹp hơn trước khi xuất Excel.')
 }
}
defineExpose({refresh:()=>load()})
</script>

<template>
 <ListPage :title="label||doctype" :rows="data?.rows||[]" :columns="columns" :loading="busy" :error="error" v-model:search="searchDraft" search-placeholder="Tìm theo số, tên…"
   paged :start="start" :page-size="pageSize" :total="data?.total_count" :has-more="data?.has_more" @update:start="value=>{start=value;load()}" @update:page-size="value=>{pageSize=value;start=0;load()}" @refresh="load()"
   :storage-key="'erp-list:'+doctype" server-sort interactive :export-rows="exportRows" :export-title="label||doctype" show-empty-headers
   :empty="search?'Không có chứng từ khớp từ khóa.':'Chưa có chứng từ.'" @sort="sorted" @open="row=>emit('open',row.name)">
  <template #actions><UiButton v-if="canCreate" @click="emit('new')"><LotusIcon name="plus"/>Tạo mới</UiButton></template>
 </ListPage>
</template>
