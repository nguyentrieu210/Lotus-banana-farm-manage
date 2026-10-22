<script setup>
const props=defineProps({embedded:Boolean,navigationKey:String})
const emit=defineEmits(['navigation-consumed'])
import {unitLabel} from './units'
import WorkspaceModal from './components/WorkspaceModal.vue'
import DataTable from './components/DataTable.vue'
import {computed,nextTick,onActivated,onMounted,ref,watch} from 'vue'
import WorkspaceTabs from './components/WorkspaceTabs.vue'
import SearchSelect from './components/SearchSelect.vue'
import SchemaForm from './components/SchemaForm.vue'
import WorkMaterialSettings from './components/WorkMaterialSettings.vue'
import AssignApp from './AssignApp.vue'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import {sidebarCollapsed} from './workspace'
import {call,consoleAPI,setCSRF} from './api'
import {cleanFields,fmt} from './domain'
import {stateLabel} from './labels'
import {dismissOnBackdrop} from './dialogs'

const tabs=[{id:'overview',label:'Tổng quan',icon:'◷'},{id:'plans',label:'Kế hoạch',icon:'☷'},{id:'progress',label:'Tiến độ',icon:'✓'},{id:'setup',label:'Danh mục & cấu hình',icon:'⚙'}]
const kinds=[{id:'works',label:'Công việc & năng suất',type:'Work Type'},{id:'norms',label:'Định mức vật tư',type:'Material Norm Profile'},{id:'bases',label:'Cơ sở định mức',type:'Norm Basis'},{id:'categories',label:'Nhóm công đoạn',type:'Work Category'},{id:'teams',label:'Tổ lao động',type:'Work Team'},{id:'cycles',label:'Vụ cây theo lô',type:'Crop Cycle'},{id:'varieties',label:'Giống cây',type:'Banana Variety'},{id:'land',label:'Lô chăm sóc',type:'Farm Block'}]
const session=ref(null),data=ref(null),farm=ref(''),zone=ref(''),date=ref(''),tab=ref('overview'),kind=ref('works'),busy=ref(false),saving=ref(false),error=ref(''),notice=ref(''),search=ref(''),taskState=ref(''),team=ref('')
const planColumns=[
 {field:'name',headerName:'Kế hoạch',minWidth:180},
 {field:'posting_date',headerName:'Ngày',minWidth:135},
 {field:'rate_approval_state',headerName:'Trạng thái',valueGetter:p=>p.data.rate_approval_state==='Pending'?'Chờ duyệt giá':p.data.rate_approval_state==='Rejected'?'Từ chối':p.data.rate_approval_state==='Approved'?'Đã duyệt giá':(['Nháp','Đã giao','Đã hủy'][p.data.docstatus]),minWidth:165},
 {field:'rate_details',headerName:'Chi tiết giá',minWidth:220},
 {field:'rate_request_reason',headerName:'Lý do',minWidth:180},
 {field:'rate_approved_by',headerName:'Người duyệt',minWidth:140},
 {field:'modified',headerName:'Cập nhật',minWidth:185}
]
const configColumns=computed(()=>{
 const action={field:'_action',headerName:'Thao tác',minWidth:145,sortable:false,valueGetter:p=>kind.value==='cycles'?'Xem vụ cây':kind.value==='land'?'Xem lô':data.value?.permissions?.[currentType.value]?.write?'Cấu hình / sửa':'Xem'}
 if(kind.value==='works')return [
  {field:'work_code',headerName:'Mã'},{field:'work_name',headerName:'Công việc'},{field:'category_label',headerName:'Nhóm công đoạn'},
  {field:'uom',headerName:'Đơn vị',valueGetter:p=>unitName(p.data.uom)},
  {field:'payment_basis',headerName:'Hình thức công',valueGetter:p=>p.data.payment_basis?stateLabel(p.data.payment_basis):'Chưa chọn'},
  {field:'productivity_per_workday',headerName:'Năng suất trung bình',valueGetter:p=>p.data.productivity_per_workday>0?fmt(p.data.productivity_per_workday):'Chưa cấu hình'},
  {field:'piecework_rate',headerName:'Đơn giá khoán',valueGetter:p=>p.data.allow_piecework?fmt(p.data.piecework_rate)+' đ/'+unitName(p.data.uom):'—'},
  {field:'active',headerName:'Trạng thái',valueGetter:p=>p.data.active?'Đang dùng':'Ngừng dùng'},action]
 if(kind.value==='norms')return [
  {field:'profile_name',headerName:'Bộ định mức'},{field:'work_label',headerName:'Công việc'},{field:'version',headerName:'Phiên bản'},
  {field:'valid_from',headerName:'Hiệu lực',valueGetter:p=>p.data.valid_from+' / '+(p.data.valid_to||'Chưa đặt ngày kết thúc')},
  {field:'approval_state',headerName:'Trạng thái',valueGetter:p=>stateLabel(p.data.approval_state)},action]
 if(['cycles','land'].includes(kind.value))return [
  {field:'block_code',headerName:'Lô chăm sóc'},{field:'block_label',headerName:'Khu'},{field:'area_ha',headerName:'Diện tích ha',valueGetter:p=>fmt(p.data.area_ha)},
  {field:'cycle_count',headerName:kind.value==='cycles'?'Vụ cây':'Hoạt động',valueGetter:p=>kind.value==='cycles'?cycleFor(p.data).map(c=>c.name+' · Vụ '+c.cycle_no).join('; ')||'Chưa có vụ cây':p.data.active?'Có':'Không'},action]
 return [
  {field:'code',headerName:'Mã',valueGetter:p=>p.data.team_code||p.data.category_code||p.data.variety_code||p.data.basis_code},
  {field:'label',headerName:'Tên',valueGetter:p=>p.data.team_name||p.data.category_name||p.data.variety_name||p.data.basis_name},
  {field:'active',headerName:'Hoạt động',valueGetter:p=>p.data.active?'Có':'Không'},action]
})
function configCellAction(event){
 if(event.colDef?.field!=='_action'||!event.data)return
 const r=event.data
 if(kind.value==='cycles'){if(cycleFor(r).length)edit('Crop Cycle',cycleFor(r)[0].name);else if(mayCreate('Crop Cycle'))newCycle(r)}
 else edit(kind.value==='land'?'Farm Block':currentType.value,r.name)
}
const progressColumns=[
 {field:'work_name',headerName:'Công việc',minWidth:180},
 {field:'block_code',headerName:'Lô chăm sóc',minWidth:130},
 {field:'work_team',headerName:'Tổ',valueGetter:p=>teamName(p.data.work_team),minWidth:150},
 {field:'completed_qty',headerName:'Đã làm / giao',valueGetter:p=>fmt(p.data.completed_qty)+' / '+fmt(p.data.planned_qty)+' '+unitLabel(p.data.uom),minWidth:170},
 {field:'status',headerName:'Trạng thái',valueGetter:p=>stateLabel(p.data.status),minWidth:140},
]
const editor=ref(null),schema=ref(null),dialog=ref(null),editorError=ref('')
const assignmentPortal=ref(null),assignmentDialog=ref(null),assignmentOpen=ref(false),assignmentBusy=ref(false)
async function openAssignment(){if(assignmentOpen.value||!farm.value||!session.value?.commands?.work||busy.value)return;assignmentOpen.value=true;await nextTick();assignmentDialog.value.showModal();if(props.embedded)emit('navigation-consumed');else{const url=new URL(location.href);url.searchParams.delete('action');history.replaceState(history.state,'',url)}}
function closeAssignment(){if(!assignmentBusy.value){assignmentDialog.value.close();assignmentOpen.value=false}}
function cancelAssignment(event){event.preventDefault();closeAssignment()}
function assignmentClosed(){if(!assignmentDialog.value?.open)assignmentOpen.value=false}
async function assignmentCreated(result){date.value=result.posting_date;notice.value=(result.status==='Pending'?'Đã gửi chờ duyệt, chưa giao việc: ':'Đã giao việc theo kế hoạch: ')+result.plan;await load()}
const approvalBusy=ref(false),rejecting=ref(''),rejectReason=ref('')
async function decideRate(p,decision){
 if(approvalBusy.value)return
 if(decision==='Reject'&&!rejectReason.value.trim()){error.value='Nhập lý do từ chối giá khoán.';return}
 approvalBusy.value=true;error.value=''
 try{
  await call('lotus_farm.rate_approval.decide',{plan:p.name,decision,reason:decision==='Reject'?rejectReason.value:''},true)
  notice.value=(decision==='Approve'?'Đã duyệt giá và giao việc: ':'Đã từ chối phiếu: ')+p.name
  rejecting.value='';rejectReason.value='';await load()
 }catch(e){error.value=e.message}
 finally{approvalBusy.value=false}
}
let version=0
const overview=ref({tasks:[]})
const readiness=computed(()=>data.value?.readiness||{})
const farmOptions=computed(()=>(session.value?.farms||[]).map(f=>({value:f.name,label:f.farm_name||f.name})))
const teams=computed(()=>(data.value?.teams||[]).map(t=>({value:t.name,label:t.team_name})))
const missingNorms=computed(()=>readiness.value.missing_productivity?.length||0)
const missingCycles=computed(()=>readiness.value.missing_active_cycles?.length||0)
const ambiguousCycles=computed(()=>readiness.value.ambiguous_active_cycles?.length||0)
const ready=computed(()=>data.value?.plots.some(p=>p.active)&&readiness.value.active_teams>0&&readiness.value.active_works>0&&!missingNorms.value&&!missingCycles.value&&!ambiguousCycles.value)
const selectedKind=computed(()=>kinds.find(k=>k.id===kind.value))
const currentType=computed(()=>selectedKind.value.type)
const normalize=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d')
const matches=r=>!search.value||normalize(Object.values(r).filter(v=>typeof v!=='object').join(' ')).includes(normalize(search.value))
const byName=(list,name,key='name')=>(list||[]).find(r=>r[key]===name)
const unitName=unitLabel
const linkTitles=computed(()=>({'Work Type':Object.fromEntries((data.value?.works||[]).map(r=>[r.name,r.work_name])),'Norm Basis':Object.fromEntries((data.value?.bases||[]).map(r=>[r.name,r.basis_name])),'Work Category':Object.fromEntries((data.value?.categories||[]).map(r=>[r.name,r.category_name])),'Banana Variety':Object.fromEntries((data.value?.varieties||[]).map(r=>[r.name,r.variety_name])),'Crop Cycle':Object.fromEntries((data.value?.cycles||[]).map(r=>[r.name,r.name+' · Lô '+blockName(r.farm_block)])),UOM:{Bunch:'Buồng',Tree:'Cây',Ha:'ha'}}))
const blockName=name=>byName(data.value?.blocks,name)?.block_code||name
const plotName=name=>byName(data.value?.plots,name)?.plot_code||name
const teamName=name=>byName(data.value?.teams,name)?.team_name||name||'Chưa chọn tổ'
const cycleFor=p=>(data.value?.cycles||[]).filter(c=>c.farm_block===p.name)
const activeFor=p=>cycleFor(p).filter(c=>['Active','Harvesting'].includes(c.status))
const configRows=computed(()=>{
 if(!data.value)return []
 const list=kind.value==='cycles'||kind.value==='land'?data.value.blocks.map(p=>({...p,block_label:'Khu '+(p.farm_zone||'—'),cycle_count:activeFor(p).length})):kind.value==='norms'?(data.value.norms||[]).map(n=>({...n,work_label:byName(data.value.works,n.work_type)?.work_name||n.work_type})):data.value[kind.value]||[]
 return list.filter(matches).sort((a,b)=>String(a.work_name||a.team_code||a.plot_code||a.category_name||a.variety_name||a.profile_name||a.basis_name||a.name).localeCompare(String(b.work_name||b.team_code||b.plot_code||b.category_name||b.variety_name||b.profile_name||b.basis_name||b.name),'vi',{numeric:true}))
})
const tasks=computed(()=>(overview.value?.tasks||[]).filter(t=>(!team.value||t.work_team===team.value)&&(!taskState.value||t.status===taskState.value)&&matches({...t,team_label:teamName(t.work_team)})))
const plans=computed(()=>(data.value?.plans||[]).filter(matches))
const legacyURL=(path)=>'/lotus/'+path+'?'+new URLSearchParams({farm:farm.value,date:date.value})
const actions=computed(()=>[
 ...tabs.map(t=>({id:t.id,label:t.label,navigation:true,run:()=>choose(t.id)})),
 ...(session.value?.commands?.work?[{id:'assign',label:'Lập kế hoạch / giao việc',run:openAssignment}]:[]),
 {id:'stock',label:'Quản lý kho',navigation:true,href:'/lotus/kho'},
 {id:'hr',label:'Nhân sự & chấm công',navigation:true,href:'/lotus/nhan-su'}])
function choose(id){tab.value=id;search.value='';const url=new URL(location.href);url.searchParams.set('tab',id);history.replaceState(history.state,'',url)}
function configure(id){kind.value=id;choose('setup')}
async function load(){
 const request=++version;error.value='';busy.value=true
 if(!farm.value){data.value=null;busy.value=false;return}
 try{
  const value=await call('lotus_farm.farm_workspace.load',{farm:farm.value,posting_date:date.value,zone:zone.value||null})
  if(request!==version)return
  data.value=value
  if(session.value?.modules?.work?.includes('Daily Work Plan')){
   const result=await call('lotus_farm.daily_api.daily_overview',{farm:farm.value,posting_date:date.value,zone:zone.value||null})
   if(request!==version)return
   overview.value=result
  }else overview.value={tasks:[]}
  const url=new URL(location.href);url.searchParams.set('farm',farm.value);if(zone.value)url.searchParams.set('zone',zone.value);else url.searchParams.delete('zone');history.replaceState(history.state,'',url)
 }catch(e){if(request===version){error.value=e.message;data.value=null;overview.value={tasks:[]}}}
 finally{if(request===version)busy.value=false}
}
async function boot(){
 busy.value=true
 try{
  session.value=await consoleAPI('bootstrap');setCSRF(session.value.csrf_token);date.value=session.value.today
  const q=new URLSearchParams(location.search),saved=q.get('farm');zone.value=q.get('zone')||''
  farm.value=session.value.farms.some(f=>f.name===saved)?saved:session.value.farms[0]?.name||''
  if(tabs.some(t=>t.id===q.get('tab')))tab.value=q.get('tab')
  await load()
  if(q.get('action')==='assign')await openAssignment()
 }catch(e){error.value=e.message;busy.value=false}
}
const mayCreate=type=>!!data.value?.permissions?.[type]?.create
const writable=computed(()=>editor.value?.doctype!=='Daily Work Plan'&&!!schema.value?.permissions?.[editor.value?.name?'write':'create']&&!(editor.value?.docstatus>0)&&editor.value?.approval_state!=='Approved')
const formSchema=computed(()=>schema.value?{...schema.value,fields:schema.value.fields.filter(f=>f.fieldname!=='farm'&&f.fieldname!=='payment_basis'&&!(editor.value?.doctype==='Work Type'&&((f.fieldname==='piecework_rate'&&!Number(editor.value?.allow_piecework))||false))&&!(editor.value?.doctype==='Crop Cycle'&&['farm_block','farm_plot'].includes(f.fieldname)&&!!editor.value?.[f.fieldname])).map(f=>({...f,
 display_label:editor.value?.doctype==='Work Type'?({allow_daywork:'Cho phép công nhật',allow_piecework:'Cho phép công khoán',productivity_per_workday:'Năng suất trung bình (DVT / công)',piecework_rate:'Đơn giá khoán / ĐVT'})[f.fieldname]:editor.value?.doctype==='Material Norm Profile'?({profile_name:'Tên bộ định mức',lines:'Vật tư định mức'})[f.fieldname]:undefined,
 reqd:f.reqd||(editor.value?.doctype==='Material Norm Profile'&&f.fieldname==='valid_to'&&editor.value?.approval_state==='Approved')||(editor.value?.doctype==='Crop Cycle'&&((f.fieldname==='planting_date'&&Number(editor.value?.cycle_no)===1)||(f.fieldname==='parent_cycle'&&Number(editor.value?.cycle_no)>1)))}))}:null)
async function edit(type,name=null,defaults={}){
 error.value='';editorError.value=''
 try{
  schema.value=await consoleAPI('schema',{doctype:type})
  if(type==='Material Norm Profile'){schema.value.tables['Material Norm Line']=schema.value.tables['Material Norm Line'].map(f=>({...f,default:['basis_qty','frequency','conversion_factor'].includes(f.fieldname)?1:f.default}));if(!name)defaults={version:1,valid_from:date.value,approval_state:'Draft',lines:[{norm_qty:null,basis_qty:1,frequency:1,conversion_factor:1}],...defaults}}
  editor.value=name?await consoleAPI('detail',{doctype:type,name}):{doctype:type,...Object.fromEntries(schema.value.fields.filter(f=>f.default!=null).map(f=>[f.fieldname,f.default])),farm:farm.value,...defaults}
  await nextTick();dialog.value.showModal()
 }catch(e){error.value=e.message}
}
function normOptions(field,search){return call('lotus_farm.farm_workspace.norm_options',{farm:farm.value,doctype:field.options,search,work_type:editor.value?.work_type})}
function newNormVersion(){const source=editor.value;edit('Material Norm Profile',null,{profile_name:source.profile_name,work_type:source.work_type,version:Math.max(source.version,...(data.value.norms||[]).filter(n=>n.profile_name===source.profile_name).map(n=>n.version))+1,valid_from:date.value,valid_to:null,approval_state:'Draft',lines:cleanFields(schema.value,source).lines})}
function newCycle(plot){edit('Crop Cycle',null,{farm_block:plot.name,cycle_no:Math.max(0,...cycleFor(plot).map(c=>Number(c.cycle_no)||0))+1,status:'Planned'})}
async function save(){
 saving.value=true;editorError.value=''
 try{
  const d=editor.value
  await consoleAPI('save',{doctype:d.doctype,name:d.name,base_modified:d.modified,values:cleanFields(schema.value,d)},true)
  dialog.value.close();notice.value='Đã lưu '+(selectedKind.value?.label||'cấu hình')+'.';await load()
 }catch(e){editorError.value=e.message}
 finally{saving.value=false}
}
watch(kind,()=>search.value='')
watch(()=>props.navigationKey,()=>{if(farm.value&&!busy.value&&new URL(location.href).searchParams.get('action')==='assign')openAssignment()},{flush:'post'})
onMounted(boot)
onActivated(()=>{if(farm.value&&!busy.value&&new URL(location.href).searchParams.get('action')==='assign')openAssignment()})
</script>
<template>
 <div class="stock-shell farm-work-shell lotus-ui" :class="{'embedded-workspace':embedded,'sidebar-collapsed':sidebarCollapsed}">
  
  <component :is="embedded?'section':'main'" class="stock-main"><label v-if="data?.zones?.length">Khu<SearchSelect v-model="zone" :options="[{value:'',label:'Tất cả khu'},...data.zones.map(z=>({value:z,label:'Khu '+z}))]" label="Lọc theo khu" @update:model-value="load"/></label><WorkspaceTabs v-if="embedded" :items="tabs" :model-value="tab" @update:model-value="choose($event)"/>
   <p v-if="error" class="stock-error" role="alert">{{error}}</p><p v-if="notice" class="stock-success" role="status">{{notice}}</p>
   <div class="farm-work-scope"><a class="farm-primary-link" href="/work">↗ Mở app công việc điện thoại</a><label>Vườn<SearchSelect v-model="farm" :options="farmOptions" label="Vườn" placeholder="Chọn vườn" :disabled="busy" @change="zone='';load()"/></label><label v-if="tab!=='setup'">Ngày kế hoạch<UiInput v-model="date" type="date" :disabled="busy" @change="load"/></label><UiButton variant="outline" :disabled="busy" @click="load">{{busy?'Đang tải…':'Làm mới'}}</UiButton><UiButton v-if="tab!=='setup'&&session?.commands?.work" class="farm-primary-link" :disabled="busy||!data" @click="openAssignment">＋ Lập kế hoạch / giao việc</UiButton></div>
   <p v-if="!farm&&!busy" class="farm-empty">Chưa có vườn được phân quyền cho tài khoản này.</p>
   <template v-if="data">
    <div v-if="tab!=='setup'" class="farm-heading"><div><small>{{data.company}} · {{data.farm_name}}</small><h1>{{tabs.find(t=>t.id===tab)?.label}}</h1></div><span :class="['farm-status',ready?'ready':'pending']">{{ready?'Đủ cấu hình cơ bản':'Cần hoàn thiện cấu hình'}}</span></div>
    <template v-if="tab==='overview'">
     <div class="farm-kpis"><button @click="configure('land')"><span>Lô chăm sóc</span><strong>{{data.blocks.length}}</strong><small>Danh mục hiện có</small></button><button @click="configure('teams')"><span>Tổ đang hoạt động</span><strong>{{readiness.active_teams}}</strong><small>Quản lý tổ lao động</small></button><button @click="configure('works')"><span>Công việc chưa có năng suất</span><strong>{{missingNorms}}</strong><small>Cấu hình đơn vị / công</small></button><button @click="configure('cycles')"><span>Lô chưa có vụ hoạt động</span><strong>{{missingCycles}}</strong><small>Bổ sung vụ cây thực tế</small></button></div>
     <section class="farm-card"><h2>Chuẩn bị để giao việc</h2><div class="farm-check"><span>{{missingNorms?'○':'✓'}} Định mức năng suất công việc</span><UiButton variant="outline" @click="configure('works')">{{missingNorms?'Bổ sung '+missingNorms+' công việc':'Xem cấu hình'}}</UiButton></div><div class="farm-check"><span>{{missingCycles||ambiguousCycles?'○':'✓'}} Vụ cây theo lô <small v-if="ambiguousCycles">· {{ambiguousCycles}} lô có nhiều vụ hoạt động</small></span><UiButton variant="outline" @click="configure('cycles')">Cấu hình vụ cây</UiButton></div><div class="farm-check"><span>{{readiness.active_teams?'✓':'○'}} Tổ lao động</span><UiButton variant="outline" @click="configure('teams')">Quản lý tổ</UiButton></div><p class="farm-muted">Nhập năng suất và vụ cây đúng thực tế. Hệ thống kiểm tra lại từng lô, công việc và quyền khi giao việc.</p></section>
     <div class="farm-two"><section class="farm-card"><h2>Kế hoạch ngày {{date}}</h2><strong class="farm-big">{{data.plans.length}}</strong><p class="farm-muted">Phiếu kế hoạch, gồm nháp và đã nộp.</p><UiButton variant="outline" @click="choose('plans')">Xem kế hoạch</UiButton></section><section class="farm-card"><h2>Tiến độ hôm nay</h2><strong class="farm-big">{{overview.tasks?.filter(t=>t.status==='Completed').length||0}} / {{overview.tasks?.length||0}}</strong><p class="farm-muted">Dòng việc hoàn thành / đã giao.</p><UiButton variant="outline" @click="choose('progress')">Theo dõi tiến độ</UiButton></section></div>
    </template>
    <template v-else-if="tab==='plans'"><section class="farm-card"><div class="farm-toolbar"><UiInput v-model="search" aria-label="Tìm kế hoạch" placeholder="Tìm mã kế hoạch…"/><UiButton v-if="session?.commands?.work" class="farm-primary-link" :disabled="busy" @click="openAssignment">＋ Lập kế hoạch</UiButton></div><div class="farm-table-wrap"><DataTable :rows="plans" :columns="planColumns" row-key="name" storage-key="farm-work-plans" interactive @open="edit('Daily Work Plan',$event.name)" />
 <div v-if="session?.commands?.rate_approve" class="farm-plan-approvals">
  <div v-for="p in plans.filter(p=>p.docstatus===0&&p.rate_approval_state==='Pending')" :key="p.name" class="farm-card">
   <strong>{{p.name}}</strong><span v-if="p.rate_details">{{p.rate_details}}</span><span v-if="p.rate_request_reason">Lý do: {{p.rate_request_reason}}</span>
   <span v-if="p.owner===session?.user">Không tự duyệt</span>
   <div v-else class="farm-toolbar">
    <UiButton :disabled="approvalBusy" @click="decideRate(p,'Approve')">Duyệt và giao</UiButton>
    <UiButton variant="outline" :disabled="approvalBusy" @click="rejecting=rejecting===p.name?'':p.name">Từ chối</UiButton>
    <div v-if="rejecting===p.name"><UiInput v-model="rejectReason" placeholder="Lý do từ chối"/><UiButton :disabled="approvalBusy||!rejectReason.trim()" @click="decideRate(p,'Reject')">Xác nhận từ chối</UiButton></div>
   </div>
  </div>
 </div></div><p v-if="!plans.length" class="farm-empty">Chưa có kế hoạch phù hợp trong ngày này.</p></section></template>
    <template v-else-if="tab==='progress'"><section class="farm-card"><div class="farm-toolbar"><UiInput v-model="search" aria-label="Tìm tiến độ" placeholder="Tìm công việc, lô, tổ…"/><SearchSelect v-model="team" :options="[{value:'',label:'Tất cả tổ'},...teams]" label="Lọc theo tổ"/><SearchSelect v-model="taskState" :options="[{value:'',label:'Tất cả trạng thái'},...['Planned','Ready','In Progress','Blocked','Completed'].map(value=>({value,label:stateLabel(value)}))]" label="Lọc trạng thái"/><a :href="legacyURL('work')" class="farm-text-link">Cập nhật / ghi kết quả ↗</a></div><DataTable :rows="tasks" :columns="progressColumns" row-key="line" storage-key="farm-work-progress" empty="Chưa có việc được giao phù hợp trong ngày này." /><p v-if="!tasks.length" class="farm-empty">Chưa có việc đã giao phù hợp trong ngày này.</p></section></template>
    <template v-else-if="tab==='setup'">
     <nav class="farm-config-tabs" aria-label="Danh mục cấu hình"><UiButton v-for="k in kinds.filter(k=>['works','teams','cycles'].includes(k.id))" :key="k.id" :variant="kind===k.id?'default':'outline'" @click="kind=k.id">{{k.label}}</UiButton></nav><details class="farm-config-more"><summary>Danh mục bổ trợ</summary><div class="farm-config-tabs"><UiButton v-for="k in kinds.filter(k=>!['works','teams','cycles'].includes(k.id))" :key="k.id" :variant="kind===k.id?'default':'outline'" @click="kind=k.id">{{k.label}}</UiButton></div></details>
     <section class="farm-card"><div class="farm-toolbar"><UiInput v-model="search" :aria-label="'Tìm '+selectedKind.label" placeholder="Gõ để lọc danh mục…"/><span class="farm-muted">{{configRows.length}} dòng</span><UiButton v-if="!['cycles','land'].includes(kind)&&mayCreate(currentType)" @click="edit(currentType)">＋ Thêm {{kind==='teams'?'tổ':kind==='varieties'?'giống':kind==='categories'?'nhóm':kind==='norms'?'định mức vật tư':kind==='bases'?'cơ sở định mức':'công việc'}}</UiButton></div>
      <p v-if="kind==='norms'" class="farm-muted">Mỗi bộ định mức gắn với một công việc và ngày hiệu lực. <UiButton v-if="!data.bases?.length&&mayCreate('Norm Basis')" variant="outline" @click="configure('bases')">Tạo cơ sở định mức</UiButton></p><p v-if="['works','categories','varieties'].includes(kind)" class="farm-muted">Danh mục này dùng chung trong Lotus. Chỉ nhập thông tin và định mức đã được xác nhận.</p>
      <div class="farm-table-wrap"><DataTable :rows="configRows" :columns="configColumns" row-key="name" :storage-key="'farm-work-setup-'+kind" @cell-open="configCellAction" />
 <div v-if="kind==='cycles'" class="farm-cycle-actions">
  <div v-for="r in configRows" :key="r.name" class="farm-toolbar">
   <strong>{{r.block_code}}</strong>
   <UiButton v-for="c in cycleFor(r)" :key="c.name" variant="outline" @click="edit('Crop Cycle',c.name)">{{c.name}} · Vụ {{c.cycle_no}} · {{stateLabel(c.status)}}</UiButton>
   <UiButton v-if="mayCreate('Crop Cycle')" variant="outline" @click="newCycle(r)">＋ Thêm vụ</UiButton>
  </div>
 </div></div><p v-if="!configRows.length" class="farm-empty">Chưa có dữ liệu phù hợp hoặc tài khoản chưa có quyền đọc danh mục.</p>
     </section>
    </template>
   </template>
  </component>
 </div>
 <WorkspaceModal bare title="Lập kế hoạch và giao việc" :busy="assignmentBusy" ref="assignmentDialog" class="farm-assignment" aria-label="Lập kế hoạch và giao việc" @cancel="cancelAssignment" @close="assignmentClosed">
  <header class="farm-assignment-header"><div><h2>Lập kế hoạch / giao việc</h2><p>{{data?.farm_name}}</p></div><UiButton type="button" variant="ghost" :disabled="assignmentBusy" aria-label="Đóng giao việc" @click="closeAssignment">✕</UiButton></header>
  <AssignApp v-if="assignmentOpen" embedded :initial-farm="farm" :initial-date="date" :initial-session="session" :portal-target="assignmentPortal" @busy-change="assignmentBusy=$event" @created="assignmentCreated"/>
  <div ref="assignmentPortal" class="farm-assignment-portals"></div>
 </WorkspaceModal>
 <WorkspaceModal bare title="Cấu hình công việc vườn" :busy="saving" ref="dialog" class="farm-editor" aria-label="Cấu hình công việc vườn" @cancel="saving&&$event.preventDefault()"><form v-if="editor&&schema" @submit.prevent="save"><header><h2>{{editor.name?'Chi tiết':'Thêm mới'}} · {{({'Material Norm Profile':'Định mức vật tư','Norm Basis':'Cơ sở định mức','Work Type':'Công việc & năng suất','Work Team':'Tổ lao động','Crop Cycle':'Vụ cây','Work Category':'Nhóm công đoạn','Banana Variety':'Giống cây','Farm Plot':'Thửa','Daily Work Plan':'Kế hoạch'})[editor.doctype]}}</h2><UiButton variant="ghost" type="button" :disabled="saving" aria-label="Đóng cấu hình" @click="dialog.close()">✕</UiButton></header><p v-if="editorError" class="stock-error" role="alert">{{editorError}}</p><p v-if="editor.doctype==='Work Type'" class="farm-muted">Có thể bật đồng thời công khoán và công nhật. Năng suất là số đơn vị hoàn thành trong một công.</p><p v-if="editor.farm_plot" class="farm-muted">Thửa <strong>{{plotName(editor.farm_plot)}}</strong> · Lô {{blockName(editor.farm_block)}} · {{data?.farm_name}}</p><SchemaForm :schema="formSchema" :link-titles="linkTitles" :link-options="editor.doctype==='Material Norm Profile'?normOptions:undefined" :model="editor" :readonly="!writable||saving" :scope="{farm,company:data?.company}"/><WorkMaterialSettings v-if="editor.doctype==='Work Type'" :key="editor.name||'new'" :work="editor" :farm="farm" :date="date" :data="data" :disabled="saving" @saved="load"/><footer><UiButton v-if="editor.doctype==='Material Norm Profile'&&editor.approval_state==='Approved'&&mayCreate('Material Norm Profile')" type="button" variant="outline" @click="newNormVersion">Tạo phiên bản mới</UiButton><UiButton type="button" variant="outline" :disabled="saving" @click="dialog.close()">Đóng</UiButton><UiButton v-if="writable" type="submit" :disabled="saving">{{saving?'Đang lưu…':'Lưu cấu hình'}}</UiButton></footer></form></WorkspaceModal>
</template>