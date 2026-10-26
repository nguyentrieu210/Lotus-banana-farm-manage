<script setup>
const props=defineProps({embedded:Boolean,navigationKey:String,stockView:String,company:String,warehouse:String})
import {computed,inject,onMounted,provide,ref,watch} from 'vue'
import {routerKey,routeLocationKey} from 'vue-router'
import {call,setCSRF} from './api'
import {useDesktopWorkspace} from './use-desktop-workspace'
import {sidebarCollapsed} from './workspace'
import {useWorkspaceConfirm} from './use-workspace-confirm'
import {stockNavigation,normalizeStockView,documentViews} from './stock-navigation.js'
import WorkspaceTabs from './components/WorkspaceTabs.vue'
import WorkspaceConfirm from './components/WorkspaceConfirm.vue'
import WarehouseInstall from './components/WarehouseInstall.vue'
import WarehousePlanning from './components/WarehousePlanning.vue'
import WarehouseReceiving from './components/WarehouseReceiving.vue'
import StockInventory from './components/stock/StockInventory.vue'
import StockDocumentList from './components/stock/StockDocumentList.vue'
import StockLedger from './components/stock/StockLedger.vue'
import StockReport from './components/stock/StockReport.vue'
import StockMasterList from './components/stock/StockMasterList.vue'
import StockDocumentForm from './components/stock/StockDocumentForm.vue'
import StockDocumentDetail from './components/stock/StockDocumentDetail.vue'
import StockMasterForm from './components/stock/StockMasterForm.vue'
import StockScope from './components/stock/StockScope.vue'
import {Button as UiButton} from './components/ui/button'
// Kho workspace shell: session, company/warehouse scope and the view chosen in the sidebar (?stock_view=).
// Each view is its own component; the forms (phiếu kho, chi tiết, danh mục, nhận hàng theo đơn) are shared by every view.
const {desktop,density,gridDensity}=useDesktopWorkspace({embedded:props.embedded})
provide('lotusDesktopDensity',gridDensity)
const router=inject(routerKey,null),route=inject(routeLocationKey,null)
const confirm=useWorkspaceConfirm()
const api=(name,args={})=>call('lotus_farm.warehouse.'+name,args)
const session=ref(null),company=ref(''),warehouse=ref(''),scope=ref(null),busy=ref(false),error=ref(''),notice=ref(''),refreshKey=ref(0)
const view=ref(normalizeStockView(props.stockView))
const documentForm=ref(null),documentDetail=ref(null),masterForm=ref(null),receivingView=ref(null),planningView=ref(null)
const warehouses=computed(()=>scope.value?.warehouses||[])
const canCreate=computed(()=>!!company.value&&warehouses.value.length>0&&!!scope.value?.catalogue_count)
const masterViews=['warehouses','items','groups','uoms']
const warehousePwa=window.location.pathname.replace(/\/$/,'')==='/warehouse'
const mobileViews=['stock','receipts','issues','movements']

async function loadScope(){
 if(!company.value){scope.value=null;return}
 try{scope.value=await api('overview',{company:company.value,start:0})}catch(e){error.value='Không tải được danh sách kho: '+e.message}
}
async function initialize(){
 busy.value=true
 try{
  session.value=await api('bootstrap');setCSRF(session.value.csrf_token)
  company.value=props.company||session.value.companies[0]?.name||'';warehouse.value=props.warehouse||''
  if(props.stockView==='buying'){await openBuying({buying_view:'orders'},true);return}
  await loadScope()
 }catch(e){error.value=e.message}finally{busy.value=false}
}
onMounted(initialize)

function query(extra={}){return {...(route?.query||{}),stock_view:view.value,company:company.value||undefined,warehouse:warehouse.value||undefined,...extra}}
async function go(next){
 if(hasChanges()&&!await confirm.ask('Bỏ phần chưa lưu và chuyển mục?'))return
 discardChanges();view.value=normalizeStockView(next);notice.value=''
 if(router)await router.push({path:'/kho',query:query({stock_view:view.value,tab:undefined})})
}
function setWarehouse(value){warehouse.value=value||'';if(router)router.replace({path:'/kho',query:query()})}
async function setCompany(value){company.value=value;warehouse.value='';scope.value=null;if(router)router.replace({path:'/kho',query:query()});await loadScope()}
async function openBuying(extra,replace=false){
 const q={company:company.value,warehouse:warehouse.value||undefined,...extra}
 if(router)await router[replace?'replace':'push']({path:'/mua-hang',query:q})
 else location.assign('/lotus/mua-hang?'+new URLSearchParams(Object.fromEntries(Object.entries(q).filter(([,v])=>v))))
}
function changed(){refreshKey.value++}
async function openDocument(doctype,name){
 error.value=''
 try{if(doctype==='Purchase Receipt')await receivingView.value?.openReceipt(name);else await documentDetail.value.open(doctype,name)}
 catch(e){error.value=e.message}
}
async function documentSaved(result){
 notice.value='Đã lưu phiếu nháp '+result.name+'.'+(result.warning?' '+result.warning:'')
 changed()
 const list=Object.entries(documentViews).find(([,kind])=>kind===result.form_kind)?.[0]
 if(list&&list!==view.value)await go(list)
 await openDocument(result.doctype,result.name)
}
async function masterSaved(result){notice.value=result.deleted?'Đã xóa danh mục.':'Đã lưu danh mục '+result.name+'.';changed();await loadScope()}
function hasChanges(){return !!documentForm.value?.hasChanges()||!!masterForm.value?.hasChanges()||!!receivingView.value?.hasChanges()}
function discardChanges(){documentForm.value?.discardChanges();masterForm.value?.discardChanges();documentDetail.value?.discardChanges();receivingView.value?.discardChanges()}
defineExpose({hasChanges,discardChanges,scopeParams:()=>({company:company.value,warehouse:warehouse.value||undefined})})
watch(()=>props.stockView,value=>{const next=normalizeStockView(value);if(next!==view.value)view.value=next})
watch(()=>props.company,value=>{if(value&&value!==company.value)setCompany(value)})
watch(()=>props.warehouse,value=>{if((value||'')!==warehouse.value)warehouse.value=value||''})
const listProps=computed(()=>({company:company.value,warehouse:warehouse.value,session:session.value,warehouses:warehouses.value,refreshKey:refreshKey.value}))
// v-on="listEvents" takes event names (it adds the "on" prefix itself).
const listEvents={'update:warehouse':setWarehouse,'update:company':setCompany,'open-document':openDocument}
const tabs=computed(()=>(warehousePwa?stockNavigation.filter(r=>mobileViews.includes(r.id)):stockNavigation).map(({id,label})=>({id,label})))
</script>

<template>
 <div class="stock-shell lotus-ui" :class="{'embedded-workspace':embedded,'sidebar-collapsed':sidebarCollapsed,'warehouse-pwa':warehousePwa,'lotus-desktop':desktop,'desktop-compact':density==='compact'}">
  <component :is="embedded?'section':'main'" class="stock-main">
   <WorkspaceTabs v-if="!embedded&&!warehousePwa" :items="tabs" :model-value="view" label="Các mục kho" @update:model-value="go"/>
   <WarehouseInstall v-if="warehousePwa"/>
   <p v-if="error" class="stock-error" role="alert">{{error}}</p>
   <p v-if="notice" class="stock-success" role="status">{{notice}}</p>
   <p v-if="busy&&!session" class="lotus-form-note" role="status">Đang tải kho…</p>
   <template v-if="session">
    <StockInventory v-if="view==='stock'" v-bind="listProps" v-on="listEvents" :can-create="canCreate" :show-purchase="desktop||embedded" @create="kind=>documentForm.open(kind)" @receive="receivingView.openPicker()" @purchase="openBuying({buying_view:'orders',action:'create_order'})" @edit-master="(kind,name)=>masterForm.open(kind,name)"/>
    <StockDocumentList v-else-if="documentViews[view]" :kind="view" v-bind="listProps" v-on="listEvents" :can-create="canCreate" @create="kind=>documentForm.open(kind)" @receive="receivingView.openPicker()"/>
    <StockLedger v-else-if="view==='movements'" v-bind="listProps" v-on="listEvents"/>
    <StockReport v-else-if="view==='report'" v-bind="listProps" v-on="listEvents"/>
    <WarehousePlanning v-else-if="view==='planning'" ref="planningView" :company="company" :warehouse="warehouse" :today="session.today">
     <template #scope><StockScope :warehouse="warehouse" :company="company" :warehouses="warehouses" :companies="session.companies||[]" @update:warehouse="setWarehouse" @update:company="setCompany"/></template>
    </WarehousePlanning>
    <StockMasterList v-else-if="masterViews.includes(view)" :kind="view" :company="company" :session="session" :refresh-key="refreshKey" @new-master="kind=>masterForm.open(kind)" @edit-master="(kind,name)=>masterForm.open(kind,name)"/>
   </template>
   <nav v-if="warehousePwa" class="warehouse-pwa-bottom-nav" aria-label="Điều hướng Kho điện thoại">
    <UiButton v-for="tab in tabs" :key="tab.id" type="button" variant="ghost" :class="{active:view===tab.id}" :aria-current="view===tab.id?'page':undefined" @click="go(tab.id)">{{tab.label}}</UiButton>
   </nav>
  </component>
  <WarehouseReceiving ref="receivingView" :company="company" :warehouse="warehouse" :today="session?.today" :confirm="confirm.ask" @changed="changed"/>
  <StockDocumentForm ref="documentForm" :company="company" :warehouse="warehouse" :warehouses="warehouses" :session="session" @saved="documentSaved"/>
  <StockDocumentDetail ref="documentDetail" :warehouses="warehouses" :session="session" @changed="changed" @edit="current=>documentForm.edit(current)"/>
  <StockMasterForm ref="masterForm" :company="company" :session="session" @saved="masterSaved"/>
  <WorkspaceConfirm :open="confirm.open.value" :title="confirm.title.value" :message="confirm.message.value" :alert-only="confirm.alertOnly.value" @answer="confirm.finish"/>
 </div>
</template>
