<script setup>
import {unitLabel} from './units'
import {computed,nextTick,onMounted,ref,watch} from 'vue'
import WorkspaceBar from './components/WorkspaceBar.vue'
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
const kinds=[{id:'works',label:'Công việc & năng suất',type:'Work Type'},{id:'norms',label:'Định mức vật tư',type:'Material Norm Profile'},{id:'bases',label:'Cơ sở định mức',type:'Norm Basis'},{id:'categories',label:'Nhóm công đoạn',type:'Work Category'},{id:'teams',label:'Tổ lao động',type:'Work Team'},{id:'cycles',label:'Vụ cây theo thửa',type:'Crop Cycle'},{id:'varieties',label:'Giống cây',type:'Banana Variety'},{id:'land',label:'Lô & thửa',type:'Farm Plot'}]
const session=ref(null),data=ref(null),farm=ref(''),date=ref(''),tab=ref('overview'),kind=ref('works'),busy=ref(false),saving=ref(false),error=ref(''),notice=ref(''),search=ref(''),taskState=ref(''),team=ref('')
const editor=ref(null),schema=ref(null),dialog=ref(null),editorError=ref('')
const assignmentPortal=ref(null),assignmentDialog=ref(null),assignmentOpen=ref(false),assignmentBusy=ref(false)
async function openAssignment(){if(!farm.value||!session.value?.commands?.work||busy.value)return;assignmentOpen.value=true;await nextTick();assignmentDialog.value.showModal();const url=new URL(location.href);url.searchParams.delete('action');history.replaceState(null,'',url)}
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
const linkTitles=computed(()=>({'Work Type':Object.fromEntries((data.value?.works||[]).map(r=>[r.name,r.work_name])),'Norm Basis':Object.fromEntries((data.value?.bases||[]).map(r=>[r.name,r.basis_name])),'Work Category':Object.fromEntries((data.value?.categories||[]).map(r=>[r.name,r.category_name])),'Banana Variety':Object.fromEntries((data.value?.varieties||[]).map(r=>[r.name,r.variety_name])),'Crop Cycle':Object.fromEntries((data.value?.cycles||[]).map(r=>[r.name,r.name+' · Thửa '+plotName(r.farm_plot)])),UOM:{Bunch:'Buồng',Tree:'Cây',Ha:'ha'}}))
const blockName=name=>byName(data.value?.blocks,name)?.block_code||name
const plotName=name=>byName(data.value?.plots,name)?.plot_code||name
const teamName=name=>byName(data.value?.teams,name)?.team_name||name||'Chưa chọn tổ'
const cycleFor=p=>(data.value?.cycles||[]).filter(c=>c.farm_plot===p.name)
const activeFor=p=>cycleFor(p).filter(c=>['Active','Harvesting'].includes(c.status))
const configRows=computed(()=>{
 if(!data.value)return []
 const list=kind.value==='cycles'||kind.value==='land'?data.value.plots.map(p=>({...p,block_label:blockName(p.farm_block),cycle_count:activeFor(p).length})):kind.value==='norms'?(data.value.norms||[]).map(n=>({...n,work_label:byName(data.value.works,n.work_type)?.work_name||n.work_type})):data.value[kind.value]||[]
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
function choose(id){tab.value=id;search.value='';const url=new URL(location.href);url.searchParams.set('tab',id);history.replaceState(null,'',url)}
function configure(id){kind.value=id;choose('setup')}
async function load(){
 const request=++version;error.value='';busy.value=true
 if(!farm.value){data.value=null;busy.value=false;return}
 try{
  const value=await call('lotus_farm.farm_workspace.load',{farm:farm.value,posting_date:date.value})
  if(request!==version)return
  data.value=value
  if(session.value?.modules?.work?.includes('Daily Work Plan')){
   const result=await call('lotus_farm.daily_api.daily_overview',{farm:farm.value,posting_date:date.value})
   if(request!==version)return
   overview.value=result
  }else overview.value={tasks:[]}
  const url=new URL(location.href);url.searchParams.set('farm',farm.value);history.replaceState(null,'',url)
 }catch(e){if(request===version){error.value=e.message;data.value=null;overview.value={tasks:[]}}}
 finally{if(request===version)busy.value=false}
}
async function boot(){
 busy.value=true
 try{
  session.value=await consoleAPI('bootstrap');setCSRF(session.value.csrf_token);date.value=session.value.today
  const q=new URLSearchParams(location.search),saved=q.get('farm')
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
function newCycle(plot){edit('Crop Cycle',null,{farm_block:plot.farm_block,farm_plot:plot.name,cycle_no:Math.max(0,...cycleFor(plot).map(c=>Number(c.cycle_no)||0))+1,status:'Planned'})}
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
onMounted(boot)
</script>
<template>
 <div class="stock-shell farm-work-shell lotus-ui" :class="{'sidebar-collapsed':sidebarCollapsed}">
  <aside class="stock-sidebar"><a class="stock-brand" href="/lotus/mobile"><img class="lotus-brand-image" :src="'/assets/lotus_farm/images/lotus-agritech.jpg'" alt="Lotus Agritech"></a><p class="stock-nav-label">CÔNG VIỆC VƯỜN</p><nav aria-label="Công việc vườn"><UiButton v-for="t in tabs" :key="t.id" variant="outline" :class="{selected:tab===t.id}" @click="choose(t.id)">{{t.icon}} <span>{{t.label}}</span></UiButton></nav><div class="farm-side-links"><a :href="'/lotus/plan-norm'+(farm?'?farm='+encodeURIComponent(farm):'')">Cấu hình kế hoạch & định mức ↗</a><a href="/lotus/kho">Quản lý kho ↗</a><a href="/lotus/cham-cong">Nhân sự & chấm công ↗</a></div></aside>
  <main class="stock-main"><WorkspaceBar :user="session?.user" title="Công việc vườn" :actions="actions"/>
   <p v-if="error" class="stock-error" role="alert">{{error}}</p><p v-if="notice" class="stock-success" role="status">{{notice}}</p>
   <div class="farm-work-scope"><a class="farm-primary-link" href="/work">↗ Mở app công việc điện thoại</a><label>Vườn<SearchSelect v-model="farm" :options="farmOptions" label="Vườn" placeholder="Chọn vườn" :disabled="busy" @change="load"/></label><label v-if="tab!=='setup'">Ngày kế hoạch<UiInput v-model="date" type="date" :disabled="busy" @change="load"/></label><UiButton variant="outline" :disabled="busy" @click="load">{{busy?'Đang tải…':'Làm mới'}}</UiButton><UiButton v-if="tab!=='setup'&&session?.commands?.work" class="farm-primary-link" :disabled="busy||!data" @click="openAssignment">＋ Lập kế hoạch / giao việc</UiButton></div>
   <p v-if="!farm&&!busy" class="farm-empty">Chưa có vườn được phân quyền cho tài khoản này.</p>
   <template v-if="data">
    <div v-if="tab!=='setup'" class="farm-heading"><div><small>{{data.company}} · {{data.farm_name}}</small><h1>{{tabs.find(t=>t.id===tab)?.label}}</h1></div><span :class="['farm-status',ready?'ready':'pending']">{{ready?'Đủ cấu hình cơ bản':'Cần hoàn thiện cấu hình'}}</span></div>
    <template v-if="tab==='overview'">
     <div class="farm-kpis"><button @click="configure('land')"><span>Lô chăm sóc / thửa</span><strong>{{data.blocks.length}} / {{data.plots.length}}</strong><small>Danh mục hiện có</small></button><button @click="configure('teams')"><span>Tổ đang hoạt động</span><strong>{{readiness.active_teams}}</strong><small>Quản lý tổ lao động</small></button><button @click="configure('works')"><span>Công việc chưa có năng suất</span><strong>{{missingNorms}}</strong><small>Cấu hình đơn vị / công</small></button><button @click="configure('cycles')"><span>Thửa chưa có vụ hoạt động</span><strong>{{missingCycles}}</strong><small>Bổ sung vụ cây thực tế</small></button></div>
     <section class="farm-card"><h2>Chuẩn bị để giao việc</h2><div class="farm-check"><span>{{missingNorms?'○':'✓'}} Định mức năng suất công việc</span><UiButton variant="outline" @click="configure('works')">{{missingNorms?'Bổ sung '+missingNorms+' công việc':'Xem cấu hình'}}</UiButton></div><div class="farm-check"><span>{{missingCycles||ambiguousCycles?'○':'✓'}} Vụ cây theo thửa <small v-if="ambiguousCycles">· {{ambiguousCycles}} thửa có nhiều vụ hoạt động</small></span><UiButton variant="outline" @click="configure('cycles')">Cấu hình vụ cây</UiButton></div><div class="farm-check"><span>{{readiness.active_teams?'✓':'○'}} Tổ lao động</span><UiButton variant="outline" @click="configure('teams')">Quản lý tổ</UiButton></div><p class="farm-muted">Nhập năng suất và vụ cây đúng thực tế. Hệ thống kiểm tra lại từng thửa, công việc và quyền khi giao việc.</p></section>
     <div class="farm-two"><section class="farm-card"><h2>Kế hoạch ngày {{date}}</h2><strong class="farm-big">{{data.plans.length}}</strong><p class="farm-muted">Phiếu kế hoạch, gồm nháp và đã nộp.</p><UiButton variant="outline" @click="choose('plans')">Xem kế hoạch</UiButton></section><section class="farm-card"><h2>Tiến độ hôm nay</h2><strong class="farm-big">{{overview.tasks?.filter(t=>t.status==='Completed').length||0}} / {{overview.tasks?.length||0}}</strong><p class="farm-muted">Dòng việc hoàn thành / đã giao.</p><UiButton variant="outline" @click="choose('progress')">Theo dõi tiến độ</UiButton></section></div>
    </template>
    <template v-else-if="tab==='plans'"><section class="farm-card"><div class="farm-toolbar"><UiInput v-model="search" aria-label="Tìm kế hoạch" placeholder="Tìm mã kế hoạch…"/><UiButton v-if="session?.commands?.work" class="farm-primary-link" :disabled="busy" @click="openAssignment">＋ Lập kế hoạch</UiButton></div><div class="farm-table-wrap"><table><thead><tr><th>Kế hoạch</th><th>Ngày</th><th>Trạng thái</th><th>Duyệt giá</th><th>Cập nhật</th></tr></thead><tbody><tr v-for="p in plans" :key="p.name"><td><button class="farm-text-link" @click="edit('Daily Work Plan',p.name)">{{p.name}}</button><div v-if="p.rate_details" class="farm-muted">{{p.rate_details}}</div><div v-if="p.rate_request_reason" class="farm-muted">Lý do: {{p.rate_request_reason}}</div></td><td>{{p.posting_date}}</td><td>{{p.rate_approval_state==='Pending'?'Chờ duyệt giá':p.rate_approval_state==='Rejected'?'Từ chối':p.rate_approval_state==='Approved'?'Đã duyệt giá':(['Nháp','Đã giao','Đã hủy'][p.docstatus])}}</td><td><template v-if="session?.commands?.rate_approve&&p.docstatus===0&&p.rate_approval_state==='Pending'"><span v-if="p.owner===session?.user">Không tự duyệt</span><template v-else><UiButton :disabled="approvalBusy" @click="decideRate(p,'Approve')">Duyệt và giao</UiButton><UiButton variant="outline" :disabled="approvalBusy" @click="rejecting=rejecting===p.name?'':p.name">Từ chối</UiButton><div v-if="rejecting===p.name"><UiInput v-model="rejectReason" placeholder="Lý do từ chối"/><UiButton :disabled="approvalBusy||!rejectReason.trim()" @click="decideRate(p,'Reject')">Xác nhận từ chối</UiButton></div></template></template><span v-else>{{p.rate_approved_by||'-'}}</span></td><td>{{p.modified}}</td></tr></tbody></table></div><p v-if="!plans.length" class="farm-empty">Chưa có kế hoạch phù hợp trong ngày này.</p></section></template>
    <template v-else-if="tab==='progress'"><section class="farm-card"><div class="farm-toolbar"><UiInput v-model="search" aria-label="Tìm tiến độ" placeholder="Tìm công việc, thửa, tổ…"/><SearchSelect v-model="team" :options="[{value:'',label:'Tất cả tổ'},...teams]" label="Lọc theo tổ"/><SearchSelect v-model="taskState" :options="[{value:'',label:'Tất cả trạng thái'},...['Planned','Ready','In Progress','Blocked','Completed'].map(value=>({value,label:stateLabel(value)}))]" label="Lọc trạng thái"/><a :href="legacyURL('work')" class="farm-text-link">Cập nhật / ghi kết quả ↗</a></div><div class="farm-table-wrap"><table><thead><tr><th>Công việc</th><th>Thửa</th><th>Tổ</th><th>Đã làm / giao</th><th>Trạng thái</th></tr></thead><tbody><tr v-for="t in tasks" :key="t.line"><td>{{t.work_name}}</td><td>{{t.plot_code}}</td><td>{{teamName(t.work_team)}}</td><td>{{fmt(t.completed_qty)}} / {{fmt(t.planned_qty)}} {{unitLabel(t.uom)}}</td><td>{{stateLabel(t.status)}}</td></tr></tbody></table></div><p v-if="!tasks.length" class="farm-empty">Chưa có việc đã giao phù hợp trong ngày này.</p></section></template>
    <template v-else-if="tab==='setup'">
     <nav class="farm-config-tabs" aria-label="Danh mục cấu hình"><UiButton v-for="k in kinds.filter(k=>['works','teams','cycles'].includes(k.id))" :key="k.id" :variant="kind===k.id?'default':'outline'" @click="kind=k.id">{{k.label}}</UiButton></nav><details class="farm-config-more"><summary>Danh mục bổ trợ</summary><div class="farm-config-tabs"><UiButton v-for="k in kinds.filter(k=>!['works','teams','cycles'].includes(k.id))" :key="k.id" :variant="kind===k.id?'default':'outline'" @click="kind=k.id">{{k.label}}</UiButton></div></details>
     <section class="farm-card"><div class="farm-toolbar"><UiInput v-model="search" :aria-label="'Tìm '+selectedKind.label" placeholder="Gõ để lọc danh mục…"/><span class="farm-muted">{{configRows.length}} dòng</span><UiButton v-if="!['cycles','land'].includes(kind)&&mayCreate(currentType)" @click="edit(currentType)">＋ Thêm {{kind==='teams'?'tổ':kind==='varieties'?'giống':kind==='categories'?'nhóm':kind==='norms'?'định mức vật tư':kind==='bases'?'cơ sở định mức':'công việc'}}</UiButton></div>
      <p v-if="kind==='norms'" class="farm-muted">Mỗi bộ định mức gắn với một công việc và ngày hiệu lực. <UiButton v-if="!data.bases?.length&&mayCreate('Norm Basis')" variant="outline" @click="configure('bases')">Tạo cơ sở định mức</UiButton></p><p v-if="['works','categories','varieties'].includes(kind)" class="farm-muted">Danh mục này dùng chung trong Lotus. Chỉ nhập thông tin và định mức đã được xác nhận.</p>
      <div class="farm-table-wrap"><table>
       <thead><tr v-if="kind==='works'"><th>Mã</th><th>Công việc</th><th>Nhóm công đoạn</th><th>Đơn vị</th><th>Hình thức công</th><th>Năng suất trung bình</th><th>Đơn giá khoán</th><th>Trạng thái</th><th></th></tr><tr v-else-if="kind==='norms'"><th>Bộ định mức</th><th>Công việc</th><th>Phiên bản</th><th>Hiệu lực từ / đến</th><th>Trạng thái</th><th></th></tr><tr v-else-if="['cycles','land'].includes(kind)"><th>Thửa</th><th>Lô cha</th><th>Diện tích ha</th><th>{{kind==='cycles'?'Vụ cây':'Hoạt động'}}</th><th></th></tr><tr v-else><th>Mã</th><th>Tên</th><th>Hoạt động</th><th></th></tr></thead>
       <tbody><tr v-for="r in configRows" :key="r.name">
        <template v-if="kind==='works'"><td>{{r.work_code}}</td><td>{{r.work_name}}</td><td>{{r.category_label}}</td><td>{{unitName(r.uom)}}</td><td><span :class="{'farm-missing':!r.payment_basis}">{{r.payment_basis?stateLabel(r.payment_basis):'Chưa chọn'}}</span></td><td><span :class="{'farm-missing':!r.productivity_per_workday}">{{r.productivity_per_workday>0?fmt(r.productivity_per_workday):'Chưa cấu hình'}}</span></td><td>{{r.allow_piecework?fmt(r.piecework_rate)+' đ/'+unitName(r.uom):'—'}}</td><td>{{r.active?'Đang dùng':'Ngừng dùng'}}</td><td><UiButton variant="outline" @click="edit('Work Type',r.name)">{{data.permissions['Work Type'].write?'Cấu hình':'Xem'}}</UiButton></td></template>
        <template v-else-if="kind==='norms'"><td>{{r.profile_name}}</td><td>{{r.work_label}}</td><td>{{r.version}}</td><td>{{r.valid_from}} / {{r.valid_to||'Chưa đặt ngày kết thúc'}}</td><td>{{stateLabel(r.approval_state)}}</td><td><UiButton variant="outline" @click="edit('Material Norm Profile',r.name)">{{r.approval_state==='Approved'?'Xem / tạo phiên bản':'Cấu hình'}}</UiButton></td></template><template v-else-if="['cycles','land'].includes(kind)"><td>{{r.plot_code}}</td><td>{{r.block_label}}</td><td>{{fmt(r.area_ha)}}</td><td v-if="kind==='cycles'"><span v-if="!cycleFor(r).length" class="farm-missing">Chưa có vụ cây</span><button v-for="c in cycleFor(r)" :key="c.name" class="farm-cycle-link" @click="edit('Crop Cycle',c.name)">{{c.name}} · Vụ {{c.cycle_no}} · {{stateLabel(c.status)}}</button></td><td v-else>{{r.active?'Có':'Không'}}</td><td><UiButton v-if="kind==='cycles'&&mayCreate('Crop Cycle')" variant="outline" @click="newCycle(r)">＋ Thêm vụ</UiButton><UiButton v-else-if="kind==='land'" variant="outline" @click="edit('Farm Plot',r.name)">Xem thửa</UiButton></td></template>
        <template v-else><td>{{r.team_code||r.category_code||r.variety_code||r.basis_code}}</td><td>{{r.team_name||r.category_name||r.variety_name||r.basis_name}}</td><td>{{r.active?'Có':'Không'}}</td><td><UiButton variant="outline" @click="edit(currentType,r.name)">{{data.permissions[currentType].write?'Sửa':'Xem'}}</UiButton></td></template>
       </tr></tbody>
      </table></div><p v-if="!configRows.length" class="farm-empty">Chưa có dữ liệu phù hợp hoặc tài khoản chưa có quyền đọc danh mục.</p>
     </section>
    </template>
   </template>
  </main>
 </div>
 <dialog ref="assignmentDialog" class="farm-assignment" aria-label="Lập kế hoạch và giao việc" @click="!assignmentBusy&&dismissOnBackdrop($event)" @cancel="cancelAssignment" @close="assignmentClosed">
  <header class="farm-assignment-header"><div><h2>Lập kế hoạch / giao việc</h2><p>{{data?.farm_name}}</p></div><UiButton type="button" variant="ghost" :disabled="assignmentBusy" aria-label="Đóng giao việc" @click="closeAssignment">✕</UiButton></header>
  <AssignApp v-if="assignmentOpen" embedded :initial-farm="farm" :initial-date="date" :initial-session="session" :portal-target="assignmentPortal" @busy-change="assignmentBusy=$event" @created="assignmentCreated"/>
  <div ref="assignmentPortal" class="farm-assignment-portals"></div>
 </dialog>
 <dialog ref="dialog" class="farm-editor" aria-label="Cấu hình công việc vườn" @click="!saving&&dismissOnBackdrop($event)" @cancel="saving&&$event.preventDefault()"><form v-if="editor&&schema" @submit.prevent="save"><header><h2>{{editor.name?'Chi tiết':'Thêm mới'}} · {{({'Material Norm Profile':'Định mức vật tư','Norm Basis':'Cơ sở định mức','Work Type':'Công việc & năng suất','Work Team':'Tổ lao động','Crop Cycle':'Vụ cây','Work Category':'Nhóm công đoạn','Banana Variety':'Giống cây','Farm Plot':'Thửa','Daily Work Plan':'Kế hoạch'})[editor.doctype]}}</h2><UiButton variant="ghost" type="button" :disabled="saving" aria-label="Đóng cấu hình" @click="dialog.close()">✕</UiButton></header><p v-if="editorError" class="stock-error" role="alert">{{editorError}}</p><p v-if="editor.doctype==='Work Type'" class="farm-muted">Có thể bật đồng thời công khoán và công nhật. Năng suất là số đơn vị hoàn thành trong một công.</p><p v-if="editor.farm_plot" class="farm-muted">Thửa <strong>{{plotName(editor.farm_plot)}}</strong> · Lô {{blockName(editor.farm_block)}} · {{data?.farm_name}}</p><SchemaForm :schema="formSchema" :link-titles="linkTitles" :link-options="editor.doctype==='Material Norm Profile'?normOptions:undefined" :model="editor" :readonly="!writable||saving" :scope="{farm,company:data?.company}"/><WorkMaterialSettings v-if="editor.doctype==='Work Type'" :key="editor.name||'new'" :work="editor" :farm="farm" :date="date" :data="data" :disabled="saving" @saved="load"/><footer><UiButton v-if="editor.doctype==='Material Norm Profile'&&editor.approval_state==='Approved'&&mayCreate('Material Norm Profile')" type="button" variant="outline" @click="newNormVersion">Tạo phiên bản mới</UiButton><UiButton type="button" variant="outline" :disabled="saving" @click="dialog.close()">Đóng</UiButton><UiButton v-if="writable" type="submit" :disabled="saving">{{saving?'Đang lưu…':'Lưu cấu hình'}}</UiButton></footer></form></dialog>
</template>
