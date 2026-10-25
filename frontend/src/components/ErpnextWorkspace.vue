<script setup>
import {computed,defineAsyncComponent,inject,onBeforeUnmount,onMounted,ref,watch} from 'vue'
import {routerKey,routeLocationKey} from 'vue-router'
import {call} from '../api'
import {erpFeatureLabels,erpModuleLabels,erpNavigationText} from '../erpnext-navigation'
import {erpDestination,erpLegacyQuery} from '../erp-locations'
import {useWorkspaceConfirm} from '../use-workspace-confirm'
import ProcurementField from './ProcurementField.vue'
import WorkspaceConfirm from './WorkspaceConfirm.vue'
import WorkspaceModal from './WorkspaceModal.vue'
import LotusIcon from './LotusIcon.vue'
import {Button} from './ui/button'
import {Sheet} from './ui/sheet'
import {Tooltip} from './ui/tooltip'
import ErpModuleNav from './erp/ErpModuleNav.vue'
import ErpDocumentList from './erp/ErpDocumentList.vue'
import ErpDocumentEditor from './erp/ErpDocumentEditor.vue'
import ErpReportView from './erp/ErpReportView.vue'
import ErpOverview from './erp/ErpOverview.vue'
import '../erp-workbench.css'
const props=defineProps({company:String,warehouse:String,embedded:Boolean,defaultModule:{type:String,default:'Stock'}})
const route=inject(routeLocationKey,null),router=inject(routerKey,null),path=route?.path||'/erpnext'
const query=()=>route?.query||Object.fromEntries(new URLSearchParams(location.search))
const active=()=>!route||route.path===path
const catalogue=ref({modules:[],rows:[],companies:[],warehouses:[]}),busy=ref(false),error=ref(''),navigationOpen=ref(false),editor=ref(null),mapped=ref(null),quick=ref(null),quickEditor=ref(null),extension=ref(null),heading=ref('')
const module=ref(query().module||props.defaultModule),company=ref(props.company||query().company||''),warehouse=ref(props.warehouse||query().warehouse||'')
const selected=ref({kind:'Workspace',name:module.value}),docName=ref(''),newDoc=ref(false),initialFilters=ref({}),initialSearch=ref('')
const confirm=useWorkspaceConfirm(),confirmOpen=confirm.open,confirmTitle=confirm.title,confirmMessage=confirm.message
const FinancePlanning=defineAsyncComponent(()=>import('./finance/FinancePlanning.vue'))
const FinanceExtension=defineAsyncComponent(()=>import('../FinanceApp.vue'))
const ProcurementExtension=defineAsyncComponent(()=>import('./ProcurementWorkspace.vue'))
const purchaseViews={quote_comparison:'quotes',purchase_funding:'payments',purchase_payables:'payables',purchase_reports:'reports'}
const HrExtension=defineAsyncComponent(()=>import('../HrApp.vue'))
const StockOperations=defineAsyncComponent(()=>import('../StockApp.vue'))
const Timekeeping=defineAsyncComponent(()=>import('../TimekeepingApp.vue'))
const nativeRows=computed(()=>catalogue.value.rows.filter(r=>r.module===module.value&&['DocType','Report','Workspace','Dashboard'].includes(r.kind)))
const purchasingFinance=computed(()=>catalogue.value.rows.some(r=>r.kind==='DocType'&&r.name==='Payment Entry'))
const customRows=computed(()=>module.value==='Accounts'?[...[['planning','Kế hoạch tài chính'],['cash','Chi hộ · hoàn ứng · phiếu chi'],['reports','Báo cáo kế toán Việt Nam'],['settings','Thiết lập kế toán Lotus']].map(([name,label])=>({id:'lotus-'+name,kind:'Lotus',name,label,group:'Lotus',module:module.value}))]:module.value==='Buying'?[['quote_comparison','Chọn báo giá và chia đơn'],...(purchasingFinance.value?[['purchase_funding','Chi hộ · hoàn ứng mua hàng'],['purchase_payables','Đối chiếu công nợ ngày chốt'],['purchase_reports','Thu chi nguyên vật liệu']]:[])].map(([name,label])=>({id:'lotus-'+name,kind:'Lotus',name,label,group:'Lotus',module:module.value})):module.value==='Stock'?[{id:'lotus-material-demand',kind:'Lotus',name:'demand',label:'Nhu cầu vật tư vườn',group:'Lotus',module:module.value}]:module.value==='HR Setup'?[{id:'lotus-hr',kind:'Lotus',name:'hr',label:'Kỳ công · nhập dữ liệu · thiết bị',group:'Lotus',module:module.value}]:module.value.includes('Attendance')?[{id:'lotus-team-attendance',kind:'Lotus',name:'attendance',label:'Chấm công đội vườn',group:'Lotus',module:module.value}]:[])
const rows=computed(()=>[...nativeRows.value,...customRows.value])
const title=computed(()=>heading.value||erpFeatureLabels[selected.value.name]||customRows.value.find(r=>r.name===selected.value.name)?.label||erpModuleLabels[selected.value.name]||erpNavigationText(selected.value.name))
const icons={Stock:'warehouse',Buying:'cart',Accounts:'calculator',Selling:'cart',Assets:'building',Manufacturing:'settings',Projects:'list','HR Setup':'users',Payroll:'wallet','Shift & Attendance':'calendar'}
function parse(value){try{return JSON.parse(value||'{}')}catch{return {}}}
function readQuery(){const q=query();module.value=q.module||props.defaultModule;company.value=q.company||props.company||'';warehouse.value=q.warehouse||props.warehouse||'';initialFilters.value=q.erp_filters?parse(q.erp_filters):{};initialSearch.value=q.erp_search||'';const destination=erpDestination(path,q,module.value);newDoc.value=!!destination.isNew;docName.value=destination.document||'';selected.value={kind:destination.kind,name:destination.name};if(destination.kind==='Report'&&!q.erp_filters)initialFilters.value=Object.fromEntries(['from_date','to_date','warehouse'].filter(k=>q[k]).map(k=>[k,q[k]]));heading.value=''}
function stateQuery(){return {module:module.value,...(['Workspace','Dashboard'].includes(selected.value.kind)?{erp_home:'1'}:{}),...erpLegacyQuery(path,selected.value),...(selected.value.kind==='Lotus'?{...(purchaseViews[selected.value.name]?{buying_view:purchaseViews[selected.value.name]}:{}),...(['planning','cash','reports','settings'].includes(selected.value.name)?{tab:selected.value.name}:{}),...(selected.value.name==='hr'?{hr_view:query().hr_view||'payroll'}:{})}:{}),...(company.value?{company:company.value}:{}),...(warehouse.value?{warehouse:warehouse.value}:{}),...(selected.value.kind==='DocType'?{erp_doctype:selected.value.name,...(newDoc.value?{erp_new:'1'}:docName.value?{erp_doc:docName.value}:{})}:selected.value.kind==='Report'?{erp_report:selected.value.name}:selected.value.kind==='Lotus'?{erp_custom:selected.value.name}:{}),...(Object.keys(initialFilters.value).length?{erp_filters:JSON.stringify(initialFilters.value)}:{}),...(initialSearch.value?{erp_search:initialSearch.value}:{})}}
let internalNavigation=0
function navigate(replace=false){if(!active())return;const q=stateQuery();if(router){internalNavigation++;return Promise.resolve(router[replace?'replace':'push']({path,query:q})).finally(()=>internalNavigation--)}history[replace?'replaceState':'pushState'](history.state,'',location.pathname+'?'+new URLSearchParams(q))}
async function canLeave(){if(quickEditor.value?.isBusy?.())return false;if(quickEditor.value?.hasChanges?.()&&!await confirm.ask('Có thay đổi chưa lưu trong biểu mẫu thêm nhanh. Bỏ thay đổi?'))return false;quick.value=null;const current=editor.value||extension.value;if(current?.isBusy?.())return false;if(current?.hasChanges?.()){if(!await confirm.ask('Có thay đổi chưa lưu. Bỏ thay đổi và rời biểu mẫu?'))return false;current.discardChanges?.()}return true}
async function open(item){if(!await canLeave())return;navigationOpen.value=false;mapped.value=null;heading.value='';docName.value=item.name&&item.doctype?item.name:'';newDoc.value=!!item.isNew;selected.value={kind:item.doctype?'DocType':item.kind||'DocType',name:item.doctype||item.name};initialFilters.value=item.filters||{};initialSearch.value='';navigate()}
function feature(item){let filters={};if(item.href){const u=new URL(item.href,location.origin);for(const [k,v]of u.searchParams)if(!['company','warehouse'].includes(k)){try{filters[k]=JSON.parse(v)}catch{filters[k]=v}}}return open({...item,filters})}
async function changeModule(value){if(!await canLeave())return;module.value=value;selected.value={kind:'Workspace',name:value};docName.value='';newDoc.value=false;mapped.value=null;heading.value='';initialFilters.value={};navigate()}
async function changeCompany(value){if(!await canLeave())return;company.value=value;warehouse.value='';mapped.value=null;navigate();load()}
async function load(){if(!active())return;const id=++generation;busy.value=true;error.value='';try{const r=await call('lotus_farm.erpnext_workspace.catalog',{company:company.value||undefined});if(id!==generation||!active())return;catalogue.value=r;if(!r.modules.some(m=>m.value===module.value))module.value=r.modules[0]?.value||'';if(!company.value&&r.companies.length){company.value=typeof r.companies[0]==='string'?r.companies[0]:r.companies[0].name;navigate(true)}}catch(e){if(id===generation)error.value=e.message}finally{if(id===generation)busy.value=false}}
async function mappedDocument(result){if(!await canLeave())return;mapped.value=result;selected.value={kind:'DocType',name:result.doc.doctype};newDoc.value=true;docName.value='';heading.value='';navigate()}
function saved(value){newDoc.value=false;docName.value=value.name;mapped.value=null;navigate(true)}
function reportFilters(value){initialFilters.value=value;navigate(true)}
function listState(value){initialFilters.value=value.filters;initialSearch.value=value.search;navigate(true)}
function quickSaved(value){const callback=quick.value?.onSaved;quick.value=null;callback?.(value)}
async function closeQuick(){if(quickEditor.value?.hasChanges?.()&&!await confirm.ask('Bỏ thay đổi chưa lưu ở biểu mẫu thêm nhanh?'))return;quick.value=null}
let generation=0
const removeGuard=router?.beforeEach(async(to,from)=>{if(internalNavigation||from.path!==path||!active())return true;if(to.fullPath===from.fullPath)return true;return canLeave()})
watch(()=>route?.fullPath,()=>{if(!active())return;const previousCompany=company.value;readQuery();if(company.value!==previousCompany)load()})
onMounted(()=>{readQuery();load()})
onBeforeUnmount(()=>{generation++;removeGuard?.()})
defineExpose({hasChanges:()=>(editor.value||extension.value)?.hasChanges?.()||false,discardChanges:()=>(editor.value||extension.value)?.discardChanges?.(),scopeParams:()=>({company:company.value,warehouse:warehouse.value})})
</script>
<template>
 <section class="erp-workbench lotus-ui" aria-label="Phân hệ doanh nghiệp Lotus">
  <aside class="erp-app-rail" aria-label="Phân hệ"><a href="/lotus/today" class="erp-lotus-home" aria-label="Trang chủ Lotus">L</a><Tooltip v-for="item in catalogue.modules" :key="item.value" :content="erpModuleLabels[item.value]||item.label" side="right"><Button variant="ghost" :aria-label="erpModuleLabels[item.value]||item.label" :title="erpModuleLabels[item.value]||item.label" :class="{'is-active':module===item.value}" @click="changeModule(item.value)"><LotusIcon :name="icons[item.value]||'list'"/></Button></Tooltip></aside>
  <aside class="erp-sidebar"><ProcurementField :model-value="module" :display-value="erpModuleLabels[module]||module" label="Phân hệ" :options="catalogue.modules.map(m=>({value:m.value,label:erpModuleLabels[m.value]||m.label}))" @update:model-value="changeModule"/><ErpModuleNav :module="module" :rows="rows" :selected="selected" @open="feature"/></aside>
  <div class="erp-work-area"><header class="erp-workbench-header"><Button variant="ghost" class="erp-mobile-menu" aria-label="Mở điều hướng phân hệ" @click="navigationOpen=true"><LotusIcon name="menu"/></Button><Button v-if="selected.kind==='DocType'&&(docName||newDoc)" variant="ghost" aria-label="Trở về danh sách" @click="open({kind:'DocType',name:selected.name})"><LotusIcon name="chevron-left"/></Button><h1>{{title}}</h1><ProcurementField :model-value="company" label="Công ty" :options="catalogue.companies.map(c=>({value:typeof c==='string'?c:c.name,label:typeof c==='string'?c:c.name}))" :searchable="false" @update:model-value="changeCompany"/><a href="/lotus/today" class="erp-exit-link">Vườn</a></header>
   <div class="erp-work-content"><p v-if="busy" role="status">Đang tải phân hệ…</p><p v-if="error" role="alert" class="erp-error">{{error}}</p>
    <ErpDocumentEditor v-if="selected.kind==='DocType'&&(docName||newDoc)" ref="editor" :doctype="selected.name" :name="newDoc?undefined:docName" :company="company" :warehouse="warehouse" :initial-document="mapped" @open-document="open" @open-list="open" @open-report="open({...$event,kind:'Report'})" @quick-create="quick=$event" @mapped="mappedDocument" @saved="saved" @title="heading=$event"/>
    <ErpDocumentList v-else-if="selected.kind==='DocType'" :key="selected.name" :doctype="selected.name" :company="company" :initial-filters="initialFilters" :initial-search="initialSearch" @open="open" @create="open({...$event,isNew:true})" @single="open" @state="listState"/>
    <ErpReportView v-else-if="selected.kind==='Report'" :key="selected.name" :name="selected.name" :company="company" :initial-filters="initialFilters" @company="changeCompany" @filters="reportFilters" @open-document="open" @open-report="open({...$event,kind:'Report'})"/>
    <FinancePlanning ref="extension" v-else-if="selected.kind==='Lotus'&&selected.name==='planning'" embedded :company="company" class="erp-lotus-extension erp-lotus-planning"/>
    <ProcurementExtension ref="extension" v-else-if="selected.kind==='Lotus'&&purchaseViews[selected.name]" embedded :buying-view="purchaseViews[selected.name]" :company="company" :warehouse="warehouse" class="erp-lotus-extension"/>
    <FinanceExtension ref="extension" v-else-if="selected.kind==='Lotus'&&['cash','reports','settings'].includes(selected.name)" embedded class="erp-lotus-extension"/>
    <HrExtension ref="extension" v-else-if="selected.kind==='Lotus'&&selected.name==='hr'" embedded :hr-view="query().hr_view||'payroll'" class="erp-lotus-extension"/>
    <StockOperations ref="extension" v-else-if="selected.kind==='Lotus'&&selected.name==='demand'" embedded stock-view="planning" :company="company" :warehouse="warehouse" class="erp-lotus-extension"/>
    <Timekeeping ref="extension" v-else-if="selected.kind==='Lotus'&&selected.name==='attendance'" embedded :company="company" class="erp-lotus-extension"/>
    <ErpOverview v-else :module="module" :company="company" :rows="nativeRows" @open="feature"/>
   </div>
  </div>
  <Sheet v-model:open="navigationOpen" side="left" width="280px" :title="erpModuleLabels[module]||module"><ProcurementField :model-value="module" :display-value="erpModuleLabels[module]||module" label="Phân hệ" :options="catalogue.modules.map(m=>({value:m.value,label:erpModuleLabels[m.value]||m.label}))" @update:model-value="changeModule"/><ErpModuleNav :module="module" :rows="rows" :selected="selected" @open="feature"/></Sheet>
  <WorkspaceModal :model-value="!!quick" :title="'Thêm '+erpNavigationText(quick?.doctype||'')" width="1100px" @update:model-value="!$event&&closeQuick()"><ErpDocumentEditor v-if="quick" ref="quickEditor" :doctype="quick.doctype" :company="company" @saved="quickSaved"/></WorkspaceModal>
  <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" @answer="confirm.finish"/>
 </section>
</template>
