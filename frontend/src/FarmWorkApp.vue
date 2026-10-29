<script setup>
const props=defineProps({embedded:Boolean,navigationKey:String})
import {unitLabel} from './units'
import WorkspaceModal from './components/WorkspaceModal.vue'
import DataTable from './components/DataTable.vue'
import {computed,nextTick,onMounted,ref,watch} from 'vue'
import SearchSelect from './components/SearchSelect.vue'
import SchemaForm from './components/SchemaForm.vue'
import WorkMaterialSettings from './components/WorkMaterialSettings.vue'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import {sidebarCollapsed} from './workspace'
import {call,consoleAPI,setCSRF} from './api'
import {cleanFields,fmt} from './domain'
import {stateLabel} from './labels'
import {dismissOnBackdrop} from './dialogs'

// Danh mục công việc vườn (Work Type, tổ, vụ cây, định mức…). Daily reports and lot assignment live in FieldReportApp.
const kinds=[{id:'works',label:'Công việc & năng suất',type:'Work Type'},{id:'norms',label:'Định mức vật tư',type:'Material Norm Profile'},{id:'bases',label:'Cơ sở định mức',type:'Norm Basis'},{id:'categories',label:'Nhóm công đoạn',type:'Work Category'},{id:'teams',label:'Tổ lao động',type:'Work Team'},{id:'cycles',label:'Vụ cây theo lô',type:'Crop Cycle'},{id:'varieties',label:'Giống cây',type:'Banana Variety'},{id:'land',label:'Lô chăm sóc',type:'Farm Block'}]
const session=ref(null),data=ref(null),farm=ref(''),zone=ref(''),date=ref(''),tab=ref('setup'),kind=ref('works'),busy=ref(false),saving=ref(false),error=ref(''),notice=ref(''),search=ref(''),taskState=ref(''),team=ref('')
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
const editor=ref(null),schema=ref(null),dialog=ref(null),editorError=ref('')
let version=0
const farmOptions=computed(()=>(session.value?.farms||[]).map(f=>({value:f.name,label:f.farm_name||f.name})))
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
async function load(){
 const request=++version;error.value='';busy.value=true
 if(!farm.value){data.value=null;busy.value=false;return}
 try{
  const value=await call('lotus_farm.farm_workspace.load',{farm:farm.value,posting_date:date.value,zone:zone.value||null})
  if(request!==version)return
  data.value=value
  const url=new URL(location.href);url.searchParams.set('farm',farm.value);if(zone.value)url.searchParams.set('zone',zone.value);else url.searchParams.delete('zone');history.replaceState(history.state,'',url)
 }catch(e){if(request===version){error.value=e.message;data.value=null}}
 finally{if(request===version)busy.value=false}
}
async function boot(){
 busy.value=true
 try{
  session.value=await consoleAPI('bootstrap');setCSRF(session.value.csrf_token);date.value=session.value.today
  const q=new URLSearchParams(location.search),saved=q.get('farm');zone.value=q.get('zone')||''
  farm.value=session.value.farms.some(f=>f.name===saved)?saved:session.value.farms[0]?.name||''
  await load()
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
onMounted(boot)
</script>
<template>
 <div class="stock-shell farm-work-shell lotus-ui" :class="{'embedded-workspace':embedded,'sidebar-collapsed':sidebarCollapsed}">
  
  <component :is="embedded?'section':'main'" class="stock-main"><label v-if="data?.zones?.length">Khu<SearchSelect v-model="zone" :options="[{value:'',label:'Tất cả khu'},...data.zones.map(z=>({value:z,label:'Khu '+z}))]" label="Lọc theo khu" @update:model-value="load"/></label>
   <p v-if="error" class="stock-error" role="alert">{{error}}</p><p v-if="notice" class="stock-success" role="status">{{notice}}</p>
   <div class="farm-work-scope"><label>Vườn<SearchSelect v-model="farm" :options="farmOptions" label="Vườn" placeholder="Chọn vườn" :disabled="busy" @change="zone='';load()"/></label><UiButton variant="outline" :disabled="busy" @click="load">{{busy?'Đang tải…':'Làm mới'}}</UiButton></div>
   <p v-if="!farm&&!busy" class="farm-empty">Chưa có vườn được phân quyền cho tài khoản này.</p>
   <template v-if="data">
    <template v-if="tab==='setup'">
     <nav class="farm-config-tabs" aria-label="Danh mục cấu hình"><UiButton v-for="k in kinds.filter(k=>['works','teams','cycles'].includes(k.id))" :key="k.id" :variant="kind===k.id?'default':'outline'" @click="kind=k.id">{{k.label}}</UiButton></nav><details class="farm-config-more"><summary>Danh mục bổ trợ</summary><div class="farm-config-tabs"><UiButton v-for="k in kinds.filter(k=>!['works','teams','cycles'].includes(k.id))" :key="k.id" :variant="kind===k.id?'default':'outline'" @click="kind=k.id">{{k.label}}</UiButton></div></details>
     <section class="farm-card"><div class="farm-toolbar"><UiInput v-model="search" :aria-label="'Tìm '+selectedKind.label" placeholder="Gõ để lọc danh mục…"/><span class="farm-muted">{{configRows.length}} dòng</span><UiButton v-if="!['cycles','land'].includes(kind)&&mayCreate(currentType)" @click="edit(currentType)">＋ Thêm {{kind==='teams'?'tổ':kind==='varieties'?'giống':kind==='categories'?'nhóm':kind==='norms'?'định mức vật tư':kind==='bases'?'cơ sở định mức':'công việc'}}</UiButton></div>
      <p v-if="kind==='norms'" class="farm-muted">Mỗi bộ định mức gắn với một công việc và ngày hiệu lực. <UiButton v-if="!data.bases?.length&&mayCreate('Norm Basis')" variant="outline" @click="kind='bases'">Tạo cơ sở định mức</UiButton></p><p v-if="['works','categories','varieties'].includes(kind)" class="farm-muted">Danh mục này dùng chung trong Lotus. Chỉ nhập thông tin và định mức đã được xác nhận.</p>
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
 <WorkspaceModal title="Cấu hình công việc vườn" :busy="saving" ref="dialog" class="farm-editor" aria-label="Cấu hình công việc vườn" @cancel="saving&&$event.preventDefault()"><form v-if="editor&&schema" @submit.prevent="save"><p v-if="editorError" class="stock-error" role="alert">{{editorError}}</p><p v-if="editor.doctype==='Work Type'" class="farm-muted">Có thể bật đồng thời công khoán và công nhật. Năng suất là số đơn vị hoàn thành trong một công.</p><p v-if="editor.farm_plot" class="farm-muted">Thửa <strong>{{plotName(editor.farm_plot)}}</strong> · Lô {{blockName(editor.farm_block)}} · {{data?.farm_name}}</p><SchemaForm :schema="formSchema" :link-titles="linkTitles" :link-options="editor.doctype==='Material Norm Profile'?normOptions:undefined" :model="editor" :readonly="!writable||saving" :scope="{farm,company:data?.company}"/><WorkMaterialSettings v-if="editor.doctype==='Work Type'" :key="editor.name||'new'" :work="editor" :farm="farm" :date="date" :data="data" :disabled="saving" @saved="load"/><footer><UiButton v-if="editor.doctype==='Material Norm Profile'&&editor.approval_state==='Approved'&&mayCreate('Material Norm Profile')" type="button" variant="outline" @click="newNormVersion">Tạo phiên bản mới</UiButton><UiButton type="button" variant="outline" :disabled="saving" @click="dialog.close()">Đóng</UiButton><UiButton v-if="writable" type="submit" :disabled="saving">{{saving?'Đang lưu…':'Lưu cấu hình'}}</UiButton></footer></form></WorkspaceModal>
</template>