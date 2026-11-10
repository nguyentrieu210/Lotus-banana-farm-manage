<script setup>
import {tablePage} from './table-pagination'
import WorkspaceBar from './components/WorkspaceBar.vue'
import AiChatBubble from './components/AiChatBubble.vue'
import ReleaseNotes from './components/ReleaseNotes.vue'
import WorkspaceSidebar from './components/WorkspaceSidebar.vue'
import ReportsWorkspace from './components/ReportsWorkspace.vue'
import WorkspaceScopeBar from './components/WorkspaceScopeBar.vue'
import {sidebarCollapsed} from './workspace'
import {Input as UiInput} from './components/ui/input'
import UiSelect from './components/ui/select/Select.vue'
import {computed,defineAsyncComponent,onMounted,onUnmounted,ref,watch} from 'vue'
import LotusIcon from './components/LotusIcon.vue'
import {Toaster,useNoticeToast,toast} from './components/ui/toast'
import WorkspaceConfirm from './components/WorkspaceConfirm.vue'
import {useWorkspaceConfirm} from './use-workspace-confirm'
import {loadDraft,saveDraft,clearDraft} from './form-drafts'
import {Pagination} from './components/ui/pagination'
import {useRoute,useRouter} from 'vue-router'
import {routeScope,permittedRoute} from './router'
import {hrPageTitle,visibleHrNavigation,hrHref} from './hr-navigation.js'
import {workspaceModules,internalWorkspaceTarget} from './workspace-routes'
import {procurementNavigation,normalizeBuyingView} from './procurement-navigation'
import {stockViewTitle} from './stock-navigation.js'
import {financeViewTitle} from './finance-navigation.js'
import {fieldViewTitle} from './field-report-navigation.js'
import {erpViewLabel} from './erp-sections.js'
import {safeLotusDate,lotusDateMinus,isISODate} from './date-safe'
import {Button as UiButton} from './components/ui/button'
import {useSession,useScope} from './store'
import {call,consoleAPI} from './api'
import {pages,titles,moduleKey,cleanFields} from './domain'
import {docLabel,stateLabel} from './labels'
const OpsList=defineAsyncComponent(()=>import('./components/OpsList.vue'))
const DataTable=defineAsyncComponent(()=>import('./components/DataTable.vue'))
import SchemaForm from './components/SchemaForm.vue'
import CareMap from './components/CareMap.vue'
import WorkspaceModal from './components/WorkspaceModal.vue'
import MobileHome from './components/MobileHome.vue'
import WorkspaceLoading from './components/WorkspaceLoading.vue'
const workspaceComponents={
 'mua-hang':defineAsyncComponent({loader:()=>import('./components/ProcurementWorkspace.vue'),loadingComponent:WorkspaceLoading,delay:0}),
 'nguoi-dung':defineAsyncComponent({loader:()=>import('./UserAdminApp.vue'),loadingComponent:WorkspaceLoading,delay:0}),
 'nhan-su':defineAsyncComponent({loader:()=>import('./HrApp.vue'),loadingComponent:WorkspaceLoading,delay:0}),
 'cham-cong':defineAsyncComponent({loader:()=>import('./TimekeepingApp.vue'),loadingComponent:WorkspaceLoading,delay:0}),
 'kho':defineAsyncComponent({loader:()=>import('./StockApp.vue'),loadingComponent:WorkspaceLoading,delay:0}),
 'cong-viec':defineAsyncComponent({loader:()=>import('./FieldReportApp.vue'),loadingComponent:WorkspaceLoading,delay:0}),
 farms:defineAsyncComponent({loader:()=>import('./FarmLandApp.vue'),loadingComponent:WorkspaceLoading,delay:0}),
 'tai-chinh':defineAsyncComponent({loader:()=>import('./FinanceApp.vue'),loadingComponent:WorkspaceLoading,delay:0}),
 forecast:defineAsyncComponent({loader:()=>import('./BlockForecastApp.vue'),loadingComponent:WorkspaceLoading,delay:0}),
 'mau-day':defineAsyncComponent({loader:()=>import('./ColorTagCatalogApp.vue'),loadingComponent:WorkspaceLoading,delay:0}),
}
import {mobileTabs as getMobileTabs} from './mobile-menu'
const reportFilters=ref({})
const reportTab=ref('overview')
const scopeOptions=ref({zones:[],blocks:[]}),cached=ref(false)
const session=useSession(),scope=useScope(),route=useRoute(),router=useRouter(),releaseNotes=ref(null)
const columnFilters=ref({})
function applyColumns({field,values}){const next={...columnFilters.value};if(values===null)delete next[field];else next[field]=values;columnFilters.value=next;start.value=0;load()}
onMounted(()=>watch(()=>[page.value,scope.company,scope.farm,scope.zone,scope.block,scope.date,scope.from_date,scope.to_date],()=>{columnFilters.value={}},{flush:'sync'}))
const busy=ref(false),error=ref(''),message=ref(''),doctype=ref(''),list=ref({rows:[],columns:[],has_more:false}),start=ref(0),pageSize=ref(50),search=ref(''),sort=ref('modified desc')
const editor=ref(null),schema=ref(null),audit=ref(null),dialogBusy=ref(false),mapData=ref(null),settingsDoc=ref(null),settingsSchema=ref(null)
const page=computed(()=>route.path.slice(1)||'today'),key=computed(()=>moduleKey(page.value)),types=computed(()=>session.modules[key.value]||[])
const nav=computed(()=>pages.filter(([p])=>permittedRoute('/'+p,session)))
const charts=ref(null)
const embeddedComponent=computed(()=>workspaceComponents[page.value]||null)
const workspaceMain=ref(null),workspaceChild=ref(null)
const workspaceTitle=computed(()=>page.value==='nhan-su'?hrPageTitle(route.query.hr_view):(page.value==='mua-hang'?(procurementNavigation.find(r=>r.id===normalizeBuyingView(route.query.buying_view))?.label||erpViewLabel('buying',route.query.buying_view)):page.value==='cong-viec'?fieldViewTitle(route.query.field_view):page.value==='kho'?stockViewTitle(route.query.stock_view||route.query.tab):page.value==='tai-chinh'?financeViewTitle(route.query.tab,session):titles[page.value])||'Lotus')
const bottomTabs=computed(()=>getMobileTabs(session))
const farms=computed(()=>session.farms.filter(f=>!scope.company||f.company===scope.company)),companies=computed(()=>[...new Set(session.farms.map(f=>f.company))]),scopeArgs=computed(()=>scope.query())
async function refresh(){await run(async()=>{await session.load(true);cached.value=!!session.offline;await load()})}
async function run(fn){error.value='';try{return await fn()}catch(e){if(!e.stale)error.value=e.message;return null}}
function go(path,extra={}){router.push({path:'/'+path,query:scope.query({...(moduleKey(path)!==key.value?{status:''}:{}),...(['mua-hang','kho'].includes(path)?workspaceChild.value?.scopeParams?.()||{}:{}),...extra})})}
function navigateWorkspace(href){const target=internalWorkspaceTarget(href,location.origin);if(target&&permittedRoute(target.path,session,target.query)){go(target.path.slice(1),target.query);return}location.assign(href)}
function consumeWorkspaceAction(){if(route.query.action){const query={...route.query};delete query.action;router.replace({path:route.path,query})}}
function followWorkspaceLink(event){if(event.defaultPrevented||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;const anchor=event.target.closest?.('a[href]');if(!anchor||anchor.target||anchor.hasAttribute('download'))return;const target=internalWorkspaceTarget(anchor.href,location.origin);if(target&&permittedRoute(target.path,session,target.query)){event.preventDefault();event.stopPropagation();go(target.path.slice(1),target.query)}}
function openMobileAction(action){if(action.id==='farm-work'&&innerWidth>900){go('cong-viec');return}if(action.href){navigateWorkspace(action.href+(scope.farm?(action.href.includes('?')?'&farm=':'?farm=')+encodeURIComponent(scope.farm):''));return}if(action.path)go(action.path)}
watch(page,()=>{workspaceMain.value?.scrollTo({top:0,behavior:'instant'})},{flush:'post'})
function updateScope(){start.value=0;router.replace({path:route.path,query:scope.query()})}
// Top-bar "Vườn làm việc": switch the whole workspace to one farm (its company too); khu and lô start over.
async function chooseWorkFarm(value){const farm=session.farms.find(f=>f.name===value);scope.farm=value||'';if(farm?.company)scope.company=farm.company;scope.clearBelow('farm');start.value=0
 // Keep the module view (stock_view, buying_view, tab…) and only swap the scope.
 const query={...route.query,...scope.query()};for(const key of ['farm','company','zone','block'])if(!scope[key])delete query[key]
 await router.replace({path:route.path,query});await load()}
function applyViewControls(){scope.search=search.value;scope.sort=sort.value;start.value=0;updateScope()}
let loadVersion=0
async function load(){const version=++loadVersion;if(!session.ready||page.value==='denied')return;if(page.value==='mobile'||workspaceModules[page.value]){busy.value=false;error.value='';return;}const current=async promise=>{const result=await promise;if(version!==loadVersion){const e=new Error('Scope changed');e.stale=true;throw e}return result};const loadConsole=(...args)=>current(consoleAPI(...args)),loadCall=(...args)=>current(call(...args));list.value={rows:[],columns:[],has_more:false};mapData.value=null;busy.value=true;error.value='';await run(async()=>{
 scopeOptions.value=await loadConsole('scope_options',{company:scope.company,farm:scope.farm,zone:scope.zone,block:scope.block});if(scopeOptions.value?.scope)Object.assign(scope, Object.fromEntries(Object.entries(scopeOptions.value.scope).map(([k,v])=>[k,v||''])));
 if(page.value==='reports'){
  const to=safeLotusDate(scope.to_date,scope.date,session.today),from=isISODate(scope.from_date)?scope.from_date:lotusDateMinus(to,29)
  charts.value=await loadCall('lotus_farm.reporting.charts',{from_date:from,to_date:to,farm:scope.farm||null,company:scope.company||null,zone:scope.zone||null,block:scope.block||null,report_filters:JSON.stringify(reportFilters.value)})
  return
 }
 if(page.value==='map'){mapData.value=scope.farm?await loadCall('lotus_farm.field.map_block_data',{farm:scope.farm,zone:scope.zone||null,block:scope.block||null,include_draft:1}):null;return}
 if(page.value==='admin/settings'){settingsSchema.value=await loadConsole('schema',{doctype:'Lotus Farm Settings'});settingsDoc.value=await loadConsole('settings');return}
 if(route.query.doctype&&types.value.includes(route.query.doctype))doctype.value=String(route.query.doctype)
 else if(!types.value.includes(doctype.value))doctype.value=types.value[0]||''
 if(!doctype.value)return
 list.value=await tablePage(args=>loadConsole('listing',args),{doctype:doctype.value,...scopeArgs.value,start:start.value,search:search.value,sort:sort.value,status:scope.status,include_filter_values:1,column_filters:JSON.stringify(columnFilters.value)},{pageSize:pageSize.value})
 });if(version===loadVersion)busy.value=false}
async function edit(type,name=null,defaults={}){await run(async()=>{schema.value=await consoleAPI('schema',{doctype:type});const doc=name?await consoleAPI('detail',{doctype:type,name}):{doctype:type,...Object.fromEntries(schema.value.fields.filter(f=>f.default!=null).map(f=>[f.fieldname,f.default])),farm:scope.farm,company:scope.company||session.farms.find(f=>f.name===scope.farm)?.company,posting_date:scope.date,...defaults};editor.value=doc;editorSnapshot.value=snapshotOf(doc);offerDraft(type,name);audit.value=null})}
async function save(){dialogBusy.value=true;await run(async()=>{const d=editor.value;editor.value=await consoleAPI('save',{doctype:d.doctype,name:d.name,base_modified:d.modified,values:cleanFields(schema.value,d)},true);editorSnapshot.value=snapshotOf(editor.value);if(!d.name)clearDraft(d.doctype);message.value='Đã lưu phiếu nháp.';await load()});dialogBusy.value=false}
async function showAudit(){audit.value=await run(()=>consoleAPI('audit',{doctype:editor.value.doctype,name:editor.value.name}))}
async function saveSettings(){dialogBusy.value=true;await run(async()=>{settingsDoc.value=await consoleAPI('save_settings',{base_token:settingsDoc.value._settings_token,values:cleanFields(settingsSchema.value,settingsDoc.value)},true);message.value='Đã lưu cấu hình.'});dialogBusy.value=false}
const auditColumns=[{field:'field',headerName:'Trường'},{field:'before',headerName:'Trước'},{field:'after',headerName:'Sau'}]
function changes(version){try{return JSON.parse(version.data).changed||[]}catch{return []}}
function typeChanged(){start.value=0;scope.status='';updateScope();load()}
function pageMore(delta){start.value=Math.max(0,start.value+delta);load()}
onMounted(async()=>{await run(async()=>{await session.load();scope.fromQuery(routeScope(route),session.today,session.farms);if(companies.value.length===1)scope.company=companies.value[0];search.value=scope.search||'';sort.value=scope.sort||'modified desc';if(!nav.value.some(([p])=>p===page.value)&&page.value==='today'&&nav.value.length)go(nav.value[0][0]);else await load()});window.addEventListener('lotus-cached-read',()=>{cached.value=true});window.addEventListener('online',async()=>{cached.value=false;await run(async()=>{const old=session.user;await session.load(true);if(old!==session.user){editor.value=null;scope.clearBelow('company')}scope.fromQuery(routeScope(route),session.today,session.farms);await load()})})})
watch(()=>route.fullPath,()=>{if(session.ready){scope.fromQuery(routeScope(route),session.today,session.farms);search.value=scope.search||'';sort.value=scope.sort||'modified desc';start.value=0;load()}})
const workspaceActions=computed(()=>[...visibleHrNavigation(session).map(item=>({id:'hr-'+item.id,label:item.label,navigation:true,href:hrHref(item)})),...nav.value.filter(([id])=>!['nhan-su','cham-cong'].includes(id)).map(([id,label])=>({id,label,navigation:true,run:()=>go(id)})),...(session.capabilities.stock?[{id:'stock',label:'Quản lý kho',navigation:true,href:'/lotus/kho'}]:[])])
// Success messages show as toasts (errors stay inline next to the form).
useNoticeToast(message)
// Unsaved changes in the document editor: confirm before closing, warn before leaving the page,
// and keep a local draft of new documents so a closed tab or crash does not lose typing.
const editorSnapshot=ref('')
const {open:confirmOpen,title:confirmTitle,message:confirmMessage,alertOnly:confirmAlert,ask:askConfirm,finish:finishConfirm}=useWorkspaceConfirm()
const removeWorkspaceGuard=router.beforeEach(async(to,from)=>{
 const changed=to.path!==from.path||['buying_view','stock_view','company','warehouse'].some(k=>to.query[k]!==from.query[k])
 if(changed&&workspaceChild.value?.hasChanges?.()){
  if(!await askConfirm('Bỏ phần chưa lưu và chuyển màn hình?'))return false
  workspaceChild.value?.discardChanges?.()
 }
})
function preventWorkspaceUnload(event){if(workspaceChild.value?.hasChanges?.()){event.preventDefault();event.returnValue=''}}
onMounted(()=>window.addEventListener('beforeunload',preventWorkspaceUnload))
onUnmounted(()=>{removeWorkspaceGuard();window.removeEventListener('beforeunload',preventWorkspaceUnload)})

const snapshotOf=doc=>schema.value&&doc?JSON.stringify(cleanFields(schema.value,doc)):''
const editorDirty=computed(()=>!!editor.value&&!!schema.value&&snapshotOf(editor.value)!==editorSnapshot.value)
async function closeEditor(){
 if(editorDirty.value&&!await askConfirm('Phiếu có thay đổi chưa lưu. Đóng và bỏ thay đổi?','Bỏ thay đổi?'))return
 if(editor.value&&!editor.value.name)clearDraft(editor.value.doctype)
 editor.value=null;audit.value=null
}
function offerDraft(type,name){
 if(name)return
 const draft=loadDraft(type);if(!draft)return
 toast({title:'Có bản nháp chưa lưu',description:'Lưu lúc '+new Date(draft.savedAt).toLocaleString('vi-VN'),tone:'info',action:{label:'Khôi phục',run:()=>{if(editor.value?.doctype===type&&!editor.value.name)Object.assign(editor.value,draft.values)}}})
}
let draftTimer
watch(()=>editor.value&&!editor.value.name&&editorDirty.value?snapshotOf(editor.value):'',value=>{clearTimeout(draftTimer);if(value)draftTimer=setTimeout(()=>saveDraft(editor.value.doctype,cleanFields(schema.value,editor.value)),800)})
function beforeUnload(event){if(editorDirty.value){event.preventDefault();event.returnValue=''}}
onMounted(()=>window.addEventListener('beforeunload',beforeUnload))

// Ctrl-K record search: only document types this session can open, via the permission-checked link_options.
const searchableDoctypes=['Farm','Farm Block']
async function searchRecords(text){
 const allowed=new Set(Object.values(session.modules||{}).flat())
 const types=searchableDoctypes.filter(type=>allowed.has(type))
 const groups=await Promise.all(types.map(type=>consoleAPI('link_options',{doctype:type,search:text,farm:scope.farm||undefined}).then(rows=>(rows||[]).slice(0,4).map(row=>({id:type+':'+row.value,record:true,kind:docLabel(type),label:row.label&&row.label!==row.value?row.label+' · '+row.value:row.value,run:()=>edit(type,row.value)}))).catch(()=>[])))
 return groups.flat().slice(0,20)
}

</script>

<template><a class="lotus-skip-link" href="#lotus-main">Bỏ qua tới nội dung</a><div class="app-shell lotus-ui workspace-shell" @click.capture="followWorkspaceLink" :class="{'mobile-landing':page==='mobile','map-workspace':page==='map','sidebar-collapsed':sidebarCollapsed}"><WorkspaceSidebar :nav="nav" :page="page" :hr-view="route.query.hr_view" :buying-view="route.query.buying_view" :stock-view="route.query.stock_view||route.query.tab" :finance-view="route.query.tab" :field-view="route.query.field_view" @go="go" /><main ref="workspaceMain" id="lotus-main" tabindex="-1"><WorkspaceBar :farms="session.farms" :farm="scope.farm" @update:farm="chooseWorkFarm" :user="session.user" :title="workspaceTitle" :actions="workspaceActions" :navigate="navigateWorkspace" :record-search="searchRecords" @whats-new="releaseNotes?.open()" /><WorkspaceScopeBar v-if="!embeddedComponent&&page!=='map'" :land="page!=='reports'||!['commerce','stock','people'].includes(reportTab)" :farm-visible="page!=='reports'||!['commerce','stock'].includes(reportTab)" :page="page" :busy="busy" :options="scopeOptions" :companies="companies" :farms="farms" @change="updateScope" @refresh="refresh" /><p v-if="error" role="alert" class="error">{{error}}</p><p v-if="busy" class="muted">Đang đọc số liệu…</p>
<p v-if="cached||session.offline" class="notice" role="status">Đang dùng dữ liệu đã lưu của {{session.user}}. Quyền, ngày và số liệu sẽ được kiểm tra lại khi gửi.</p><div v-show="embeddedComponent" class="workspace-module-host"><KeepAlive><component v-if="embeddedComponent" ref="workspaceChild" :is="embeddedComponent" :key="page" :navigation-key="['cong-viec','mua-hang','kho'].includes(page)?route.fullPath:undefined" :buying-view="route.query.buying_view" :stock-view="route.query.stock_view||route.query.tab" :company="route.query.company" :warehouse="route.query.warehouse" :hr-view="page==='nhan-su'?route.query.hr_view:undefined" :field-view="page==='cong-viec'?route.query.field_view:undefined" :embedded="true" @navigation-consumed="consumeWorkspaceAction"/></KeepAlive></div><section v-if="page==='denied'" class="panel" role="alert"><h2>Không có quyền mở màn hình này</h2><p>Chọn một mục được phép trong menu hoặc đăng nhập lại.</p><a href="/login?redirect-to=/lotus/today">Đăng nhập</a></section><template v-else-if="embeddedComponent"></template><section v-else-if="page==='mobile'"><MobileHome :session="session" :farm="scope.farm" @select="openMobileAction"/></section>
 <section v-else-if="page==='reports'"><ReportsWorkspace :charts="charts" :busy="busy" :filters="reportFilters" @tab="reportTab=$event" @filters="reportFilters=$event;load()"/></section>
<section v-else-if="page==='map'" class="map-panel"><CareMap :collection="mapData" :farm="scope.farm" :user="session.user" @reset="scope.zone='';scope.block='';updateScope()" @open="scope.block=$event;updateScope()"><template #filters><WorkspaceScopeBar page="map" :busy="busy" :options="scopeOptions" :companies="companies" :farms="farms" @change="updateScope" @refresh="refresh"/></template></CareMap></section>
<section v-else-if="page==='admin/settings'" class="panel"><div class="section-title"><div><h2>Cấu hình Lotus</h2><p class="muted">Các ngưỡng và hệ số phải do vận hành duyệt; ứng dụng không tự đoán số.</p></div><UiButton variant="outline" v-if="settingsSchema?.permissions?.write" :loading="dialogBusy" @click="saveSettings">Lưu cấu hình</UiButton></div><SchemaForm v-if="settingsSchema&&settingsDoc" :schema="settingsSchema" :model="settingsDoc" :scope="scope" :readonly="!settingsSchema.permissions.write"/></section>
<section v-else><div class="view-controls"><UiSelect v-model="doctype" @change="typeChanged"><option v-for="t in types" :key="t" :value="t">{{docLabel(t)}}</option></UiSelect><UiInput v-model="search" placeholder="Tìm mã phiếu…" @keyup.enter="applyViewControls" /><UiSelect v-model="scope.status" @change="updateScope"><option value="">Tất cả trạng thái</option><option v-for="state in list.status_options||[]" :key="state" :value="state">{{['0','1','2'].includes(state)?['Nháp','Đã nộp','Đã hủy'][Number(state)]:stateLabel(state)}}</option></UiSelect><UiSelect v-model="sort" @change="applyViewControls"><option value="modified desc">Mới cập nhật</option><option value="modified asc">Cũ nhất</option><option value="name asc">Mã tăng dần</option></UiSelect><UiButton variant="outline" v-if="session.creatable[doctype]===true" @click="edit(doctype)">Thêm phiếu</UiButton></div>
<section class="panel"><OpsList :paginate="false" :row-index-offset="start" :rows="list.rows" :columns="list.columns" :filter-values="list.filter_values" :server-filters="columnFilters" @filter="applyColumns" :loading="busy" @open="edit(doctype,$event.name)"/><Pagination :page-size="pageSize" :disabled="busy" @update:page-size="value=>{pageSize=value;start=0;load()}" :start="start" :count="list.rows.length" :has-more="!!list.has_more" @update:start="value=>pageMore(value-start)"/></section></section>
</main></div><nav v-if="page!=='denied'" class="mobile-bottom-nav" aria-label="Điều hướng trên điện thoại"><UiButton variant="outline" v-for="tab in bottomTabs" :key="tab.id" :class="{active:page===tab.path}" :aria-current="page===tab.path?'page':undefined" @click="go(tab.path)"><LotusIcon :name="tab.icon" class="mobile-bottom-icon"/><small>{{tab.label}}</small></UiButton></nav>
<WorkspaceModal v-if="editor&&schema" :model-value="true" :title="docLabel(editor.doctype)" width="1100px" :busy="dialogBusy" @update:model-value="!$event&&(closeEditor())"><p v-if="error" class="error" role="alert">{{error}}</p><div class="actions"><UiButton variant="outline" v-if="editor.name?schema.permissions.write:schema.permissions.create" :loading="dialogBusy" @click="save">Lưu nháp</UiButton><UiButton variant="outline" v-if="editor.name" @click="showAudit">Lịch sử</UiButton><a v-if="editor.name" :href="'/app/'+editor.doctype.toLowerCase().replaceAll(' ','-')+'/'+encodeURIComponent(editor.name)" target="_blank">Mở ERP ↗</a></div><SchemaForm :schema="schema" :model="editor" :scope="scope"/><section v-if="audit" class="panel audit-drawer"><h3>Lịch sử thay đổi</h3><p>{{audit.owner}} · tạo {{audit.created}}</p><article v-for="version in audit.versions" :key="version.name"><strong>{{version.owner}} · {{version.creation}}</strong><DataTable :rows="changes(version).map(c=>({field:c[0],before:c[1],after:c[2]}))" :columns="auditColumns" /><details><summary>Chi tiết bảng con</summary><pre>{{JSON.stringify(JSON.parse(version.data),null,2)}}</pre></details></article><article v-for="comment in audit.comments" :key="comment.creation"><strong>{{comment.owner}} · {{comment.creation}}</strong><p>{{comment.content.replace(/<[^>]*>/g,'')}}</p></article></section></WorkspaceModal>
<WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" :alert-only="confirmAlert" @answer="finishConfirm"/><Toaster/><AiChatBubble v-if="session.user&&!session.offline" :user="session.user"/>
<ReleaseNotes ref="releaseNotes" :user="session.user"/>
</template>
