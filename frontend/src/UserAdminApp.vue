<script setup>
import {Checkbox} from './components/ui/checkbox'
import LotusField from './components/form/LotusField.vue'
import {computed,onMounted,reactive,ref,watch} from 'vue'
import WorkspaceTabs from './components/WorkspaceTabs.vue'
import WorkspaceListToolbar from './components/WorkspaceListToolbar.vue'
import DataTable from './components/DataTable.vue'
import LotusIcon from './components/LotusIcon.vue'
import FormField from './components/ui/form-field/FormField.vue'
import SearchSelect from './components/SearchSelect.vue'
import UserRolePicker from './components/UserRolePicker.vue'
import UserPermissionAudit from './components/UserPermissionAudit.vue'
import {scopeWarnings,normalizeSearch} from './user-access'
import {hrCatalogLabel} from './hr-catalog-labels'
import WorkspaceModal from './components/WorkspaceModal.vue'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import UiSelect from './components/ui/select/Select.vue'
import {useNoticeToast} from './use-toast'
import {call,setCSRF} from './api'
defineProps({embedded:Boolean})
const api=(name,args={},write=false)=>call('lotus_farm.user_admin.'+name,args,write)
const session=ref(null),rows=ref([]),busy=ref(false),saving=ref(false),error=ref(''),formError=ref(''),notice=ref(''),search=ref(''),status=ref(''),start=ref(0),hasMore=ref(false)
const open=ref(false),tab=ref('profile'),selected=ref(null),form=reactive({}),farmSearch=ref(''),teamSearch=ref('')
const formTabs=[{id:'profile',label:'Hồ sơ'},{id:'roles',label:'Vai trò & quyền'},{id:'scope',label:'Vườn & tổ'},{id:'audit',label:'Kiểm tra quyền'}]
const roleNames=computed(()=>Object.fromEntries((session.value?.roles||[]).map(x=>[x.name,x.label])))
const assignableRoles=computed(()=>new Set((session.value?.roles||[]).filter(r=>r.assignable).map(r=>r.name)))
const warnings=computed(()=>scopeWarnings(form))
const columns=[{field:'full_name',headerName:'Người dùng',minWidth:180},{field:'name',headerName:'Email đăng nhập',minWidth:220},{field:'username',headerName:'Tên đăng nhập',minWidth:140},{field:'enabled',headerName:'Trạng thái',valueFormatter:p=>p.value?'Đang hoạt động':'Đã khóa'},{colId:'edit',headerName:'Hồ sơ & quyền',valueGetter:()=> 'Mở',width:140}]
const matches=(q,...parts)=>normalizeSearch(parts.join(' ')).includes(normalizeSearch(q))
const farms=computed(()=>(session.value?.farms||[]).filter(x=>matches(farmSearch.value,x.farm_name,x.name)))
const teams=computed(()=>(session.value?.teams||[]).filter(x=>form.farms?.includes(x.farm)&&matches(teamSearch.value,x.team_name,x.name)))
const readOnly=computed(()=>form.protected||(!session.value?.can_write&&!!selected.value))
const otherRoles=computed(()=>(form.roles||[]).filter(x=>!roleNames.value[x]))
// Only employees without a login (or this user's own) can be linked.
const employees=computed(()=>[{value:'',label:'Chưa gắn nhân sự'},...(session.value?.employees||[]).filter(e=>!e.user_id||e.user_id===selected.value).map(e=>({value:e.name,label:e.employee_name+' · '+e.name+(e.designation?' · '+hrCatalogLabel(e.designation):'')}))])
let request=0,timer
async function load(){const id=++request;busy.value=true;error.value='';try{const data=await api('users',{search:search.value,status:status.value,start:start.value});if(id===request){rows.value=data.rows;hasMore.value=data.has_more}}catch(e){if(id===request)error.value=e.message}finally{if(id===request)busy.value=false}}
watch([search,status],()=>{clearTimeout(timer);start.value=0;timer=setTimeout(load,250)})
function reset(data){for(const k of Object.keys(form))delete form[k];Object.assign(form,data);tab.value='profile';formError.value='';farmSearch.value='';teamSearch.value='';open.value=true}
function create(){selected.value=null;reset({email:'',first_name:'',last_name:'',username:'',phone:'',mobile_no:'',enabled:0,roles:[],farms:[],teams:[],advanced_grants:[],employee:''})}
async function edit(row){busy.value=true;error.value='';try{const data=await api('detail',{user:row.name});selected.value=row.name;reset(data)}catch(e){error.value=e.message}finally{busy.value=false}}
function toggle(key,value,checked){const next=new Set(form[key]||[]);checked?next.add(value):next.delete(value);form[key]=[...next];if(key==='farms')form.teams=(form.teams||[]).filter(name=>session.value.teams.some(t=>t.name===name&&next.has(t.farm)))}
async function save(){if(readOnly.value||saving.value)return;if(!form.first_name?.trim()||!form.email?.includes('@')){tab.value='profile';formError.value='Nhập tên và email đăng nhập hợp lệ.';return}saving.value=true;formError.value='';try{const data=await api('save',{user:selected.value,values:{...form,roles:form.roles.filter(x=>assignableRoles.value.has(x))}},true);notice.value='Đã lưu hồ sơ và phân quyền cho '+data.email+(data.removed_disabled_roles?.length?'. ERPNext đã gỡ các role bị khóa: '+data.removed_disabled_roles.join(', '):'');open.value=false;await load()}catch(e){formError.value=e.message}finally{saving.value=false}}
function page(delta){start.value=Math.max(0,start.value+delta*50);load()}
onMounted(async()=>{busy.value=true;try{session.value=await api('bootstrap');setCSRF(session.value.csrf_token);await load()}catch(e){error.value=e.message}finally{busy.value=false}})
// Success messages show as toasts (errors stay inline next to the form).
useNoticeToast(notice)
</script>
<template><section class="user-admin lotus-ui">
<p v-if="error" role="alert" class="stock-error">{{error}}</p>
<WorkspaceListToolbar v-model="search" placeholder="Tìm tên, email hoặc tên đăng nhập…" :busy="busy" @refresh="load"><template #filters><UiSelect v-model="status" aria-label="Trạng thái tài khoản"><option value="">Tất cả trạng thái</option><option value="1">Đang hoạt động</option><option value="0">Đã khóa</option></UiSelect></template><UiButton v-if="session?.can_create" :disabled="busy" @click="create"><LotusIcon name="plus"/>Tạo người dùng</UiButton></WorkspaceListToolbar>
<DataTable :rows="rows" :columns="columns" :loading="busy" interactive storage-key="user-admin" empty="Không có tài khoản phù hợp." @open="edit"/>
<div class="user-pagination"><UiButton variant="outline" :disabled="!start||busy" @click="page(-1)">Trước</UiButton><span>{{rows.length?start+1:0}}–{{start+rows.length}}</span><UiButton variant="outline" :disabled="!hasMore||busy" @click="page(1)">Sau</UiButton></div>
<WorkspaceModal v-model="open" :title="selected?'Hồ sơ người dùng · '+selected:'Tạo hồ sơ người dùng'" :busy="saving" width="900px">
<WorkspaceTabs :items="formTabs" :model-value="tab" @update:model-value="tab=$event" label="Hồ sơ và phân quyền"/>
<p v-if="formError" role="alert" class="stock-error">{{formError}}</p>
<p v-for="warning in warnings" :key="warning" role="status" class="stock-error">{{warning}}</p>
<form novalidate @submit.prevent="save"><fieldset :disabled="readOnly||saving" class="user-fields">
<div v-show="tab==='profile'" class="hr-form-grid">
<FormField label="Email đăng nhập" required v-slot="f"><UiInput v-bind="f" v-model="form.email" type="email" :disabled="!!selected" autocomplete="off"/></FormField><FormField label="Tên" required v-slot="f"><UiInput v-bind="f" v-model="form.first_name" autocomplete="given-name"/></FormField><FormField label="Họ và tên đệm" v-slot="f"><UiInput v-bind="f" v-model="form.last_name" autocomplete="family-name"/></FormField><FormField label="Tên đăng nhập" v-slot="f"><UiInput v-bind="f" v-model="form.username" autocomplete="off"/></FormField><FormField label="Điện thoại" v-slot="f"><UiInput v-bind="f" v-model="form.phone" type="tel"/></FormField><FormField label="Di động" v-slot="f"><UiInput v-bind="f" v-model="form.mobile_no" type="tel"/></FormField>
<FormField class="user-wide" label="Nhân sự của tài khoản" hint="Gắn nhân sự để được chọn ký duyệt và nhận thông báo đến lượt ký."><SearchSelect v-model="form.employee" :options="employees" label="Nhân sự của tài khoản"/></FormField>
<LotusField type="checkbox" label="Kích hoạt tài khoản" :model-value="!!form.enabled" @update:model-value="value=>form.enabled=value?1:0"/><p v-if="!selected" class="user-hint">Tài khoản mới mặc định bị khóa. Sau khi cấp quyền và kích hoạt, người dùng đặt mật khẩu qua “Quên mật khẩu” tại trang đăng nhập. Lưu hồ sơ không gửi email.</p></div>
<div v-show="tab==='roles'"><p v-if="form.role_profile" class="user-hint">Vai trò đang được quản lý theo mẫu. Chỉnh mẫu tại quản trị nâng cao.</p><UserRolePicker v-model="form.roles" :roles="session?.roles||[]" :effective-roles="form.effective_roles||[]" :disabled="!!form.role_profile"/><p v-if="otherRoles.length" class="user-hint">Vai trò khác được giữ nguyên: {{otherRoles.join(', ')}}</p><p v-if="form.roles?.includes('System Manager')" class="user-hint">Quản trị hệ thống được quản lý tài khoản, vai trò và cấu hình hệ thống.</p></div>
<div v-show="tab==='scope'" class="user-scope-grid"><section><h3>Vườn được truy cập</h3><FormField label="Tìm vườn" v-slot="f"><UiInput v-bind="f" v-model="farmSearch" type="search"/></FormField><div class="user-choice-list"><label v-for="farm in farms" :key="farm.name" class="user-choice"><Checkbox :model-value="!!form.farms?.includes(farm.name)" @update:model-value="value=>toggle('farms',farm.name,value)"/><span>{{farm.farm_name||farm.name}}<small v-if="farm.farm_name">{{farm.name}}</small></span></label><p v-if="!farms.length" class="stock-empty">Không có vườn phù hợp.</p></div></section><section><h3>Tổ được giao</h3><FormField label="Tìm tổ trong vườn đã chọn" v-slot="f"><UiInput v-bind="f" v-model="teamSearch" type="search"/></FormField><div class="user-choice-list"><label v-for="team in teams" :key="team.name" class="user-choice"><Checkbox :model-value="!!form.teams?.includes(team.name)" @update:model-value="value=>toggle('teams',team.name,value)"/><span>{{team.team_name||team.name}}<small>{{team.farm}}</small></span></label><p v-if="!teams.length" class="stock-empty">Chọn vườn để xem các tổ.</p></div></section><p class="user-hint">Tổ trưởng và giám sát cần được cấp cả vườn và tổ. Vai trò quản lý xem các tổ thuộc vườn được cấp theo quyền hiện hành.</p><p v-if="form.advanced_grants?.length" class="user-hint">Có {{form.advanced_grants.length}} phạm vi nâng cao được giữ nguyên.</p><ul v-if="form.advanced_grants?.length" class="user-hint"><li v-for="g in form.advanced_grants" :key="g.doctype+g.value+g.applicable_for">{{g.doctype}} · {{g.value}}{{g.applicable_for?' · Áp dụng cho '+g.applicable_for:''}}</li></ul></div>
<UserPermissionAudit v-show="tab==='audit'" :audit="form.permission_audit"/></fieldset><footer class="user-form-footer"><a v-if="selected" :href="'/app/user/'+encodeURIComponent(selected)" target="_blank" rel="noopener" class="workspace-secondary-link">Quản trị nâng cao ↗</a><span v-if="form.protected" class="user-hint">Tài khoản hệ thống được bảo vệ.</span><UiButton v-if="!readOnly" type="submit" :disabled="saving">{{saving?'Đang lưu…':'Lưu hồ sơ & phân quyền'}}</UiButton></footer></form>
</WorkspaceModal></section></template>
