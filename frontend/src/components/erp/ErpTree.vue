<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {call} from '../../api'
import {Button} from '../ui/button'
import DataTable from '../DataTable.vue'
const props=defineProps({doctype:String,company:String})
const emit=defineEmits(['open'])
const data=ref({rows:[]}),expanded=ref(new Set()),error=ref(''),loading=ref(false)
const rows=computed(()=>{const groups=new Map();for(const row of data.value.rows){const parent=row._erp_parent||'';if(!groups.has(parent))groups.set(parent,[]);groups.get(parent).push(row)}const result=[],seen=new Set();function visit(parent,depth){for(const row of groups.get(parent)||[]){if(seen.has(row.name))continue;seen.add(row.name);result.push({...row,_depth:depth,_children:groups.has(row.name)});if(expanded.value.has(row.name))visit(row.name,depth+1)}}visit('',0);return result})
let generation=0
async function load(){const id=++generation;loading.value=true;error.value='';try{const r=await call('lotus_farm.erp_workbench.tree',{doctype:props.doctype,company:props.company});if(id!==generation)return;data.value=r;expanded.value=new Set(r.rows.filter(r=>!r._erp_parent).map(r=>r.name))}catch(e){if(id===generation)error.value=e.message}finally{if(id===generation)loading.value=false}}
function toggle(name){const next=new Set(expanded.value);next.has(name)?next.delete(name):next.add(name);expanded.value=next}
watch(()=>[props.doctype,props.company],load)
onMounted(load)
</script>
<template><section class="erp-tree"><p v-if="error" role="alert" class="erp-error">{{error}}</p><DataTable :rows="rows" :columns="[{field:'name',headerName:'Tên',minWidth:300}]" row-key="name" :loading="loading" :storage-key="'erp-tree-'+doctype"><template #cell-name="{row}"><span :style="{paddingLeft:row._depth*18+'px'}"><Button v-if="row._children" variant="ghost" size="sm" :aria-label="(expanded.has(row.name)?'Thu gọn ':'Mở nhóm ')+row.name" @click="toggle(row.name)">{{expanded.has(row.name)?'−':'+'}}</Button><Button variant="link" size="sm" @click="emit('open',{doctype,name:row.name})">{{row[data.title_field]||row.name}}</Button></span></template></DataTable></section></template>
