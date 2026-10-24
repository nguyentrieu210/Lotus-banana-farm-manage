<script setup>
import {computed,onBeforeUnmount,onMounted,ref,watch} from 'vue'
import {call} from '../../api'
import ErpField from './ErpField.vue'
import ErpTree from './ErpTree.vue'
import ProcurementField from '../ProcurementField.vue'
import DataTable from '../DataTable.vue'
import {Input} from '../ui/input'
import {Button} from '../ui/button'
import {Sheet} from '../ui/sheet'
import {Pagination} from '../ui/pagination'
const props=defineProps({doctype:String,company:String,initialFilters:Object,initialSearch:String})
const emit=defineEmits(['open','create','state','single'])
const treeMode=ref(false)
const schema=ref(null),result=ref({rows:[],columns:[]}),search=ref(props.initialSearch||''),filters=ref({...props.initialFilters}),start=ref(0),sort=ref('modified desc'),loading=ref(false),error=ref(''),filterOpen=ref(false),filterField=ref(''),operator=ref('='),filterValue=ref('')
let generation=0,timer
const api=(m,args)=>call('lotus_farm.erp_workbench.'+m,args)
const fields=computed(()=>[{fieldname:'name',label:'Mã',fieldtype:'Data'},...(schema.value?.is_submittable?[{fieldname:'docstatus',label:'Trạng thái chứng từ',fieldtype:'Select',options:[{value:0,label:'Nháp'},{value:1,label:'Đã duyệt'},{value:2,label:'Đã hủy'}]}]:[]),...(schema.value?.fields||[]).filter(f=>!['Tab Break','Section Break','Column Break','Table','Table MultiSelect','HTML','Button','Password','Text Editor'].includes(f.fieldtype))])
const chosenField=computed(()=>fields.value.find(f=>f.fieldname===filterField.value))
const columns=computed(()=>result.value.columns.map(c=>({field:c.fieldname,headerName:c.label,minWidth:c.fieldname==='name'?220:145,valueFormatter:({value})=>c.fieldname==='docstatus'?['Nháp','Đã duyệt','Đã hủy'][Number(value)]:['Currency','Float','Int','Percent'].includes(c.fieldtype)?Number(value||0).toLocaleString('vi-VN'):value})))
const exportUrl=computed(()=>'/api/method/lotus_farm.erp_workbench.export_list?'+new URLSearchParams({doctype:props.doctype,company:props.company||'',search:search.value,filters:JSON.stringify(filters.value),sort:sort.value}))
async function load(reset=false){if(reset)start.value=0;const id=++generation;loading.value=true;error.value='';try{if(!schema.value){schema.value=await api('schema',{doctype:props.doctype});if(id!==generation)return;if(schema.value.issingle){emit('single',{doctype:props.doctype,name:props.doctype});return}}const r=await api('listing',{doctype:props.doctype,company:props.company,search:search.value,filters:JSON.stringify(filters.value),start:start.value,sort:sort.value});if(id!==generation)return;result.value=r;emit('state',{search:search.value,filters:filters.value})}catch(e){if(id===generation)error.value=e.message}finally{if(id===generation)loading.value=false}}
function addFilter(){if(!chosenField.value)return;let value=filterValue.value;if(['in','not in','between'].includes(operator.value))value=String(value).split(',').map(v=>v.trim());filters.value={...filters.value,[filterField.value]:[operator.value,value]};filterOpen.value=false;load(true)}
function removeFilter(key){const next={...filters.value};delete next[key];filters.value=next;load(true)}
function sorted(value){if(!value[0])return;const next=value[0].colId+' '+value[0].sort;if(next===sort.value)return;sort.value=next;load(true)}
watch(search,()=>{clearTimeout(timer);timer=setTimeout(()=>load(true),300)})
watch(()=>[props.doctype,props.company],()=>{generation++;schema.value=null;result.value={rows:[],columns:[]};filters.value={...props.initialFilters};search.value=props.initialSearch||'';load(true)})
onMounted(()=>load())
onBeforeUnmount(()=>{generation++;clearTimeout(timer)})
</script>
<template>
 <section class="erp-list" :aria-busy="loading"><div class="erp-list-toolbar"><Input v-model="search" type="search" aria-label="Tìm chứng từ" placeholder="Tìm mã, tên…"/><Button v-if="schema?.is_tree" variant="outline" @click="treeMode=!treeMode">{{treeMode?'Danh sách':'Cây'}}</Button><Button variant="outline" @click="filterOpen=true">Bộ lọc{{Object.keys(filters).length?' ('+Object.keys(filters).length+')':''}}</Button><Button variant="outline" :disabled="loading" @click="load()">Làm mới</Button><span class="erp-action-spacer"/><Button v-if="schema?.permissions.export" as="a" variant="outline" :href="exportUrl" download>Excel toàn bộ</Button><Button v-if="schema?.permissions.create" @click="emit('create',{doctype})">Thêm mới</Button></div>
  <div v-if="Object.keys(filters).length" class="erp-filter-chips"><Button v-for="(value,key) in filters" :key="key" variant="outline" size="sm" :aria-label="'Bỏ lọc '+key" @click="removeFilter(key)">{{fields.find(f=>f.fieldname===key)?.label||key}}: {{Array.isArray(value)?value.join(' '):value}} ×</Button></div><p v-if="error" role="alert" class="erp-error">{{error}}</p>
  <ErpTree v-if="treeMode" :doctype="doctype" :company="company" @open="emit('open',$event)"/><DataTable v-else :rows="result.rows" :columns="columns" :loading="loading" row-key="name" :storage-key="'erp-list-'+doctype" :filter-values="{}" server-sort @sort="sorted" @row-double-open="emit('open',{doctype,name:$event.name})"><template #cell-name="{row}"><Button variant="link" size="sm" @click="emit('open',{doctype,name:row.name})">{{row.name}}</Button></template></DataTable>
  <Pagination v-if="!treeMode" :start="start" :count="result.rows.length" :has-more="result.has_more" :total="Number(result.total_count)||0" :disabled="loading" @update:start="start=$event;load()"/>
  <Sheet v-model:open="filterOpen" title="Lọc chứng từ"><div class="erp-filter-form"><ProcurementField v-model="filterField" label="Trường" :options="fields.map(f=>({value:f.fieldname,label:f.label}))" @update:model-value="filterValue=''"/><ProcurementField v-model="operator" label="Điều kiện" :options="[{value:'=',label:'Bằng'},{value:'!=',label:'Khác'},{value:'like',label:'Chứa (%từ khóa%)'},{value:'>',label:'Lớn hơn'},{value:'<',label:'Nhỏ hơn'},{value:'in',label:'Thuộc danh sách (phân cách dấu phẩy)'},{value:'between',label:'Trong khoảng (phân cách dấu phẩy)'}]"/><ErpField v-if="chosenField" v-model="filterValue" :field="['in','between'].includes(operator)?{...chosenField,fieldtype:'Data'}:chosenField" :doctype="doctype" :company="company"/></div><template #footer><Button :disabled="!chosenField||filterValue===''" @click="addFilter">Áp dụng</Button></template></Sheet>
 </section>
</template>
