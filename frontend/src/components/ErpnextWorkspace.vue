<script setup>
import {computed,inject,onMounted,ref,watch} from 'vue'
import {routerKey,routeLocationKey} from 'vue-router'
import {call} from '../api'
import {erpModuleLabels,erpKindLabels,erpFeatures} from '../erpnext-navigation'
import ProcurementField from './ProcurementField.vue'
import WorkspaceListToolbar from './WorkspaceListToolbar.vue'
import DataTable from './DataTable.vue'
const props=defineProps({company:String,warehouse:String,embedded:Boolean})
const route=inject(routeLocationKey,null),router=inject(routerKey,null)
const query=()=>route?.query||Object.fromEntries(new URLSearchParams(location.search))
const data=ref({modules:[],rows:[],companies:[],warehouses:[]}),busy=ref(false),error=ref('')
const module=ref(query().module||'Stock'),kind=ref(query().kind||''),search=ref(query().erp_search||'')
const company=ref(props.company||query().company||''),warehouse=ref(props.warehouse||query().warehouse||'')
const to=ref(query().to_date||''),from=ref(query().from_date||'')
let version=0
const modules=computed(()=>[{value:'',label:'Tất cả phân hệ'},...data.value.modules.map(m=>({...m,label:erpModuleLabels[m.value]||m.label}))])
const kinds=[{value:'',label:'Tất cả chức năng'},...Object.entries(erpKindLabels).map(([value,label])=>({value,label}))]
const rows=computed(()=>erpFeatures(data.value.rows,{module:module.value,kind:kind.value,search:search.value}))
const columns=[{field:'title',headerName:'Chức năng',minWidth:230},{field:'module_title',headerName:'Phân hệ',minWidth:140},{field:'kind_title',headerName:'Loại',minWidth:150},{field:'group',headerName:'Nhóm',minWidth:130},{field:'name',headerName:'Tên ERPNext',minWidth:200}]
function saveQuery(){if(route&&route.path!=='/erpnext')return;const next={...query()};for(const [k,v] of Object.entries({module:module.value,kind:kind.value,erp_search:search.value,company:company.value,warehouse:warehouse.value,from_date:from.value,to_date:to.value})){if(v)next[k]=v;else delete next[k]}if(router)router.replace({path:'/erpnext',query:next});else history.replaceState(history.state,'',location.pathname+(new URLSearchParams(next).size?'?'+new URLSearchParams(next):''))}
async function load(){if(route&&route.path!=='/erpnext')return;const id=++version;busy.value=true;error.value='';try{const result=await call('lotus_farm.erpnext_workspace.catalog',{module:module.value||undefined,company:company.value||undefined,warehouse:warehouse.value||undefined,from_date:from.value||undefined,to_date:to.value||undefined});if(id!==version)return;data.value=result;if(module.value&&!result.modules.some(m=>m.value===module.value)){module.value='';saveQuery()}}catch(e){if(id===version){data.value.rows=[];error.value=e.message}}finally{if(id===version)busy.value=false}}
watch([module,company,warehouse,from,to],()=>{saveQuery();load()})
watch([kind,search],saveQuery)
watch(()=>props.company,v=>{company.value=v||''})
watch(()=>props.warehouse,v=>{warehouse.value=v||''})
watch(()=>route?.query, q=>{if(!q||route.path!=='/erpnext')return;module.value=q.module||'';kind.value=q.kind||'';search.value=q.erp_search||'';company.value=q.company||'';warehouse.value=q.warehouse||'';from.value=q.from_date||'';to.value=q.to_date||''})
function changeCompany(value){warehouse.value='';company.value=value}
onMounted(load)
</script>
<template>
 <section class="erpnext-workspace lotus-ui" aria-label="Chức năng ERPNext">
  <WorkspaceListToolbar v-model="search" placeholder="Tìm chức năng, chứng từ, báo cáo…" :busy="busy" @refresh="load">
   <template #filters>
    <ProcurementField v-model="module" label="Phân hệ" :options="modules"/>
    <ProcurementField v-model="kind" label="Loại chức năng" :options="kinds" :searchable="false"/>
    <ProcurementField :model-value="company" label="Công ty" :options="[{value:'',label:'Tất cả công ty'},...data.companies.map(c=>({value:c.name,label:c.name}))]" :searchable="false" @update:model-value="changeCompany"/>
    <ProcurementField v-model="warehouse" label="Kho" :options="[{value:'',label:'Tất cả kho'},...data.warehouses.filter(w=>!company||w.company===company).map(w=>({value:w.name,label:w.warehouse_name||w.name}))]" :searchable="false"/>
    <ProcurementField v-model="from" label="Từ ngày" type="date"/>
    <ProcurementField v-model="to" label="Đến ngày" type="date"/>
   </template>
  </WorkspaceListToolbar>
  <p v-if="error" role="alert" class="erpnext-error">{{error}}</p>
  <DataTable :rows="rows" :columns="columns" :loading="busy" row-key="id" storage-key="erpnext-features" empty="Không có chức năng phù hợp với quyền và bộ lọc.">
   <template #cell-title="{row}"><a :href="row.href" target="_blank" rel="noopener" :aria-label="row.title+' · mở ERPNext'">{{row.title}}</a></template>
  </DataTable>
  <footer class="erpnext-footer"><span>{{rows.length}} chức năng</span><a href="/desk" target="_blank" rel="noopener">Mở ERPNext</a></footer>
 </section>
</template>
<style scoped>
.erpnext-workspace{display:grid;gap:var(--lotus-space-3);min-width:0;width:100%;overflow:hidden;padding:var(--lotus-space-3)}
.erpnext-workspace :deep(.workspace-list-toolbar){flex-wrap:nowrap;overflow-x:auto;align-items:flex-end;max-width:100%}
.erpnext-workspace :deep(.workspace-list-filters){flex-wrap:nowrap;flex-shrink:0;align-items:flex-end}
.erpnext-workspace :deep(.lotus-data-table){min-width:0;max-width:100%}
.erpnext-workspace :deep(.workspace-list-filters>.lotus-field){width:160px;flex-shrink:0}
.erpnext-workspace :deep(.workspace-list-search){min-width:200px}
.erpnext-workspace :deep(a){color:var(--lotus-primary);text-decoration:underline;text-underline-offset:3px}
.erpnext-error{color:var(--lotus-danger);margin:0}
.erpnext-footer{display:flex;justify-content:space-between;gap:var(--lotus-space-3);font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
</style>
