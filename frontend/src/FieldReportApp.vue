<script setup>
const props=defineProps({embedded:Boolean,navigationKey:String,fieldView:String})
import {computed,inject,onMounted,provide,ref,watch} from 'vue'
import {routerKey,routeLocationKey} from 'vue-router'
import {call,setCSRF} from './api'
import {useDesktopWorkspace} from './use-desktop-workspace'
import {sidebarCollapsed} from './workspace'
import {normalizeFieldView} from './field-report-navigation.js'
import {groups,payModes,payShort,capBases,money,amountText} from './field-work-model.js'
import {unitLabel} from './units'
import {formatDate} from './format'
import WorkToday from './components/field/WorkToday.vue'
import WorkAssign from './components/field/WorkAssign.vue'
import WorkInspect from './components/field/WorkInspect.vue'
import FieldBoard from './components/field/FieldBoard.vue'
import FarmWorkApp from './FarmWorkApp.vue'
import ListPage from './components/ListPage.vue'
import LotusField from './components/form/LotusField.vue'
import FormGrid from './components/form/FormGrid.vue'
import ModalForm from './components/form/ModalForm.vue'
import FormSection from './components/form/FormSection.vue'
import {Button as UiButton} from './components/ui/button'
// Công việc ngoài vườn (/lotus/cong-viec): Hôm nay (báo cáo trên phiếu), giao việc theo lô, nghiệm thu, bảng lô × việc,
// tiền khoán theo người, and the setup (đội, tổ & lô, bảng giá, việc & cách trả). Same components as the /work phone app.
const {desktop,density,gridDensity}=useDesktopWorkspace({embedded:props.embedded})
provide('lotusDesktopDensity',gridDensity)
const router=inject(routerKey,null),route=inject(routeLocationKey,null)
const api=(name,args={},write=false)=>call('lotus_farm.field_report.'+name,args,write)
const view=ref(normalizeFieldView(props.fieldView))
const session=ref(null),setup=ref(null),farm=ref(''),crew=ref(''),day=ref(''),busy=ref(false),error=ref(''),notice=ref('')
const today=computed(()=>session.value?.today||'')
const month=ref('')
const rows=ref([]),search=ref(''),loading=ref(false)

const farmOptions=computed(()=>(session.value?.farms||[]).map(f=>({value:f.name,label:f.farm_name||f.name})))
const crews=computed(()=>setup.value?.crews||[])
const myCrews=computed(()=>crews.value.filter(c=>(setup.value?.my_crews||[]).includes(c.name)))
const crewOptions=computed(()=>myCrews.value.map(c=>({value:c.name,label:c.team_name+(c.zones?.length?' (khu '+c.zones.join(', ')+')':'')})))
const crewName=name=>crews.value.find(c=>c.name===name)?.team_name||name||''
const workName=name=>(setup.value?.works||[]).find(w=>w.name===name)?.work_name||name||''

function query(extra={}){return {...(route?.query||{}),field_view:view.value,farm:farm.value||undefined,crew:crew.value||undefined,date:day.value||undefined,...extra}}
async function go(next,extra={}){
 view.value=normalizeFieldView(next);notice.value=''
 if(router)await router.push({path:'/cong-viec',query:query({field_view:view.value,...extra})})
 await loadView()
}
async function loadSetup(){
 if(!farm.value){setup.value=null;return}
 setup.value=await api('setup',{farm:farm.value})
 if(!myCrews.value.some(c=>c.name===crew.value))crew.value=myCrews.value[0]?.name||''
}
async function boot(){
 busy.value=true;error.value=''
 try{
  session.value=await api('bootstrap');setCSRF(session.value.csrf_token)
  const q=route?.query||{}
  farm.value=session.value.farms.some(f=>f.name===q.farm)?q.farm:session.value.farms[0]?.name||''
  crew.value=q.crew||'';day.value=q.date||session.value.today;month.value=session.value.today.slice(0,7)
  await loadSetup();await loadView()
 }catch(e){error.value=e.message}
 finally{busy.value=false}
}
onMounted(boot)
watch(()=>props.fieldView,value=>{const next=normalizeFieldView(value);if(next!==view.value){view.value=next;loadView()}})

async function loadView(){
 if(!setup.value)return
 const v=view.value
 if(!['payable','rates'].includes(v))return
 loading.value=true;error.value=''
 try{rows.value=v==='payable'?await api('payable',{farm:farm.value,month:month.value}):setup.value.rates}
 catch(e){error.value=e.message;rows.value=[]}
 finally{loading.value=false}
}
async function changeFarm(value){farm.value=value;crew.value='';await loadSetup();await loadView()}

const payableColumns=[
 {field:'employee_name',headerName:'Người làm',minWidth:170},
 {field:'team_name',headerName:'Tổ',minWidth:100},
 {field:'block_code',headerName:'Lô',minWidth:70},
 {field:'work_name',headerName:'Công việc',minWidth:170},
 {field:'pay_mode',headerName:'Cách trả',valueGetter:p=>payShort[p.data.pay_mode],minWidth:100},
 {field:'sessions',headerName:'Số buổi',minWidth:80,sum:true},
 {field:'ticket_amount',headerName:'Tiền cả phiếu',valueFormatter:p=>money(p.value),minWidth:120},
 {field:'amount',headerName:'Phần của người',valueFormatter:p=>money(p.value),minWidth:130,sum:true},
 {field:'locked_at',headerName:'Ngày khoá',valueFormatter:p=>formatDate(p.value),minWidth:100},
]
const basisLabels={Area:'theo ha của lô',Trees:'theo số cây của lô',Count:'theo số đếm'}
const rateColumns=[
 {field:'work_type',headerName:'Công việc',valueGetter:p=>workName(p.data.work_type),minWidth:200},
 {field:'basis',headerName:'Tính theo',valueGetter:p=>basisLabels[p.data.basis]||p.data.basis,minWidth:150},
 {field:'rate',headerName:'Đơn giá',valueFormatter:p=>money(p.value),minWidth:110},
 {field:'uom',headerName:'ĐVT',valueGetter:p=>unitLabel(p.data.uom)||p.data.uom,minWidth:80},
 {field:'norm',headerName:'Năng suất / công',valueGetter:p=>p.data.norm_min||p.data.norm_max?amountText(p.data.norm_min)+' – '+amountText(p.data.norm_max):'',minWidth:130},
 {field:'valid_from',headerName:'Áp dụng từ',minWidth:110},
 {field:'valid_to',headerName:'Đến ngày',minWidth:110},
 {field:'notes',headerName:'Ghi chú',minWidth:180},
]
const catalogColumns=[
 {field:'work_code',headerName:'Mã',minWidth:90},
 {field:'work_name',headerName:'Công việc',minWidth:220},
 {field:'group',headerName:'Nhóm',valueGetter:p=>groups[p.data.group]||'',minWidth:130},
 {field:'pay_mode',headerName:'Cách trả',valueGetter:p=>payModes[p.data.pay_mode]||'',minWidth:160},
 {field:'cap_basis',headerName:'Trần theo',valueGetter:p=>capBases[p.data.cap_basis]||'',minWidth:170},
 {field:'requires_material',headerName:'Bắt buộc vật tư',valueGetter:p=>p.data.requires_material?'Có':'',minWidth:110},
 {field:'rate',headerName:'Giá hiện hành',valueFormatter:p=>p.value?money(p.value):'',minWidth:120},
]

// Đội, tổ & lô
const crewColumns=[
 {field:'team_name',headerName:'Đội',minWidth:160},
 {field:'zones',headerName:'Khu phụ trách',valueGetter:p=>(p.data.zones||[]).join(', '),minWidth:120},
 {field:'leader_name',headerName:'Đội trưởng',minWidth:160},
 {field:'blocks',headerName:'Số lô',valueGetter:p=>(setup.value?.blocks||[]).filter(b=>b.crew===p.data.name).length,minWidth:80},
]
const teamColumns=[
 {field:'team_name',headerName:'Tổ',minWidth:140},
 {field:'lotus_parent_team',headerName:'Thuộc đội',valueGetter:p=>crewName(p.data.lotus_parent_team)||'Chưa xếp',minWidth:160},
 {field:'leader_name',headerName:'Tổ trưởng',minWidth:160},
 {field:'active',headerName:'Hoạt động',valueGetter:p=>p.data.active?'Có':'Không',minWidth:90},
]
const blockColumns=[
 {field:'zone',headerName:'Khu',minWidth:60},
 {field:'block_code',headerName:'Lô',minWidth:70},
 {field:'area_ha',headerName:'Diện tích (ha)',minWidth:110,sum:true},
 {field:'trees',headerName:'Số cây hiện có',minWidth:120,sum:true},
 {field:'crew',headerName:'Đội',valueGetter:p=>crewName(p.data.crew)||'Chưa có đội',minWidth:150},
 {field:'quarantine_until',headerName:'Cách ly thu hoạch đến',valueFormatter:p=>p.value?formatDate(p.value):'',minWidth:150},
]
const users=ref([]),crewForm=ref(null),teamForm=ref(null),rateForm=ref(null),modeForm=ref(null),formBusy=ref(false),formError=ref('')
const userOptions=computed(()=>[{value:'',label:'Chưa chọn'},...users.value.map(u=>({value:u.name,label:(u.full_name||u.name)+' · '+u.name}))])
async function needUsers(){if(!users.value.length)users.value=await api('user_options',{farm:farm.value})}
async function editCrew(row){formError.value='';await needUsers();crewForm.value={name:row?.name||null,team_name:row?.team_name||'',zones:(row?.zones||[]).join(', '),leader:row?.lotus_leader||''}}
async function editTeam(row){formError.value='';await needUsers();teamForm.value={name:row.name,team_name:row.team_name,crew:row.lotus_parent_team||'',leader:row.lotus_leader||''}}
function newRate(){formError.value='';rateForm.value={work_type:'',basis:'Count',rate:null,uom:'',norm_min:null,norm_max:null,valid_from:today.value,valid_to:'',notes:''}}
function editMode(row){if(!setup.value?.manager)return;formError.value='';modeForm.value={work_type:row.name,work_name:row.work_name,group:row.group,pay_mode:row.pay_mode,cap_basis:row.cap_basis||'None',requires_material:!!row.requires_material}}
async function submit(kind){
 formBusy.value=true;formError.value=''
 try{
  if(kind==='crew'){await api('save_crew',{farm:farm.value,...crewForm.value},true);crewForm.value=null;notice.value='Đã lưu đội.'}
  else if(kind==='team'){const f=teamForm.value;await api('save_team',{farm:farm.value,name:f.name,crew:f.crew||null,leader:f.leader||null},true);teamForm.value=null;notice.value='Đã xếp tổ.'}
  else if(kind==='mode'){const f=modeForm.value;await api('save_work_mode',{farm:farm.value,work_type:f.work_type,group:f.group,pay_mode:f.pay_mode,cap_basis:f.cap_basis,requires_material:f.requires_material?1:0},true);modeForm.value=null;notice.value='Đã lưu cách trả. Phiếu đã giao giữ cách trả lúc giao.'}
  else{await api('save_rate',{farm:farm.value,...rateForm.value,valid_to:rateForm.value.valid_to||null},true);rateForm.value=null;notice.value='Đã lưu giá khoán.'}
  await loadSetup();await loadView()
 }catch(e){formError.value=e.message}
 finally{formBusy.value=false}
}
const workOptions=computed(()=>(setup.value?.works||[]).map(w=>({value:w.name,label:w.work_name})))
const basisOptions=Object.entries(basisLabels).map(([value,label])=>({value,label:'Tính '+label}))
const toOptions=map=>Object.entries(map).map(([value,label])=>({value,label}))
const filtered=computed(()=>{const q=search.value.trim().toLowerCase();return q?rows.value.filter(r=>JSON.stringify(r).toLowerCase().includes(q)):rows.value})
defineExpose({hasChanges:()=>false,discardChanges:()=>{},scopeParams:()=>({farm:farm.value})})
</script>

<template>
 <div class="stock-shell field-report-shell lotus-ui" :class="{'embedded-workspace':embedded,'sidebar-collapsed':sidebarCollapsed,'lotus-desktop':desktop,'desktop-compact':density==='compact'}">
  <component :is="embedded?'section':'main'" class="stock-main">
   <p v-if="error" class="stock-error" role="alert">{{error}}</p>
   <p v-if="notice" class="stock-success" role="status">{{notice}}</p>
   <p v-if="busy&&!session" class="lotus-form-note" role="status">Đang tải…</p>
   <template v-if="session&&setup">
    <template v-if="['today','assign','board'].includes(view)">
     <FormGrid :columns="4" class="field-report-scope">
      <LotusField v-if="farmOptions.length>1" :model-value="farm" label="Vườn" :options="farmOptions" @update:model-value="changeFarm"/>
      <LotusField v-model="crew" label="Đội" type="select" :searchable="false" :options="crewOptions" empty-option="Chưa có đội"/>
     </FormGrid>
     <p v-if="!crewOptions.length" class="lotus-form-note">Tài khoản chưa là đội trưởng hoặc tổ trưởng của đội nào. Vào <a href="/lotus/cong-viec?field_view=lots">Đội, tổ &amp; lô</a> để xếp.</p>
     <WorkToday v-if="view==='today'&&crew" v-model:date="day" :farm="farm" :crew="crew" :setup="setup"/>
     <WorkAssign v-else-if="view==='assign'&&crew" :farm="farm" :crew="crew" :setup="setup"/>
     <FieldBoard v-else-if="view==='board'&&crew" v-model:month="month" :farm="farm" :crew="crew"/>
    </template>

    <WorkInspect v-else-if="view==='inspect'" :farm="farm" :setup="setup"/>

    <ListPage v-else-if="view==='payable'" v-model:search="search" title="Tiền khoán theo người" :rows="filtered" :columns="payableColumns" :loading="loading" row-key="key" storage-key="field-work-payable" @refresh="loadView">
     <template #filters><LotusField v-model="month" type="month" aria-label="Tháng" @update:model-value="loadView"/></template>
     <template #before><p class="lotus-form-note">Phiếu khoán đã khoá trong tháng, chia theo buổi cho người làm. Số này vào bảng lương; buổi làm khoán không tính công nhật.</p></template>
    </ListPage>

    <template v-else-if="view==='lots'">
     <FormSection title="Đội" description="Lô thuộc đội theo khu. Quản lý vườn tạo đội và chọn đội trưởng.">
      <template v-if="setup.manager" #actions><UiButton type="button" @click="editCrew(null)">Thêm đội</UiButton></template>
      <ListPage :rows="crews" :columns="crewColumns" :searchable="false" row-key="name" storage-key="field-crews" :interactive="setup.manager" @open="editCrew" @refresh="loadSetup"/>
     </FormSection>
     <FormSection title="Tổ" description="Đội trưởng xếp tổ vào đội và chọn tổ trưởng (tài khoản đã được cấp quyền vườn).">
      <ListPage :rows="setup.teams" :columns="teamColumns" :searchable="false" row-key="name" storage-key="field-teams" interactive @open="editTeam" @refresh="loadSetup"/>
     </FormSection>
     <FormSection title="Lô" description="Diện tích và số cây hiện có của lô là trần khi báo và căn cứ tính khoán cả lô.">
      <ListPage :rows="setup.blocks" :columns="blockColumns" :searchable="false" row-key="name" storage-key="field-blocks" @refresh="loadSetup"/>
     </FormSection>
    </template>

    <ListPage v-else-if="view==='rates'" v-model:search="search" title="Bảng giá khoán" :rows="filtered" :columns="rateColumns" :loading="loading" row-key="name" storage-key="field-rates" @refresh="loadView">
     <template v-if="setup.manager" #actions><UiButton type="button" @click="newRate">Thêm giá</UiButton></template>
     <template #before><p class="lotus-form-note">Đổi giá: thêm dòng mới với ngày áp dụng mới. Giá đã dùng trên phiếu giao không sửa.</p></template>
    </ListPage>

    <template v-else-if="view==='catalog'">
     <ListPage title="Việc & cách trả" :rows="setup.works" :columns="catalogColumns" :searchable="false" row-key="name" storage-key="field-work-modes" :interactive="setup.manager" @open="editMode" @refresh="loadSetup">
      <template #before><p class="lotus-form-note">Cách trả đi theo việc: khoán số lượng (có trần đối chiếu), khoán lô (kỹ thuật vườn nghiệm thu) hoặc công nhật. Người giao việc không đổi được. Quản lý vườn bấm một việc để sửa.</p></template>
     </ListPage>
     <FormSection title="Danh mục công việc đầy đủ"><FarmWorkApp embedded/></FormSection>
    </template>
   </template>
  </component>

  <ModalForm :model-value="!!crewForm" :title="crewForm?.name?'Sửa đội':'Thêm đội'" width="560px" :busy="formBusy" :error="formError" @update:model-value="v=>!v&&(crewForm=null)" @submit="submit('crew')">
   <FormGrid v-if="crewForm" :columns="1">
    <LotusField v-model="crewForm.team_name" label="Tên đội" required placeholder="Đội khu A + B"/>
    <LotusField v-model="crewForm.zones" label="Khu phụ trách" required placeholder="A, B" :hint="'Các khu trong vườn: '+(setup?.zones||[]).join(', ')"/>
    <LotusField v-model="crewForm.leader" label="Đội trưởng" :options="userOptions"/>
   </FormGrid>
  </ModalForm>
  <ModalForm :model-value="!!teamForm" :title="'Xếp '+(teamForm?.team_name||'tổ')" width="560px" :busy="formBusy" :error="formError" @update:model-value="v=>!v&&(teamForm=null)" @submit="submit('team')">
   <FormGrid v-if="teamForm" :columns="1">
    <LotusField v-model="teamForm.crew" label="Thuộc đội" type="select" :searchable="false" :options="[{value:'',label:'Chưa xếp'},...crews.map(c=>({value:c.name,label:c.team_name}))]"/>
    <LotusField v-model="teamForm.leader" label="Tổ trưởng" :options="userOptions" hint="Tổ trưởng báo cáo trên phiếu của tổ mình."/>
   </FormGrid>
  </ModalForm>
  <ModalForm :model-value="!!rateForm" title="Thêm giá khoán" width="720px" :busy="formBusy" :error="formError" @update:model-value="v=>!v&&(rateForm=null)" @submit="submit('rate')">
   <FormGrid v-if="rateForm" :columns="2">
    <LotusField v-model="rateForm.work_type" label="Công việc" :options="workOptions" required wide/>
    <LotusField v-model="rateForm.basis" label="Tính theo" type="select" :searchable="false" :options="basisOptions" required/>
    <LotusField v-model="rateForm.rate" label="Đơn giá (đ)" type="money" required/>
    <LotusField v-model="rateForm.norm_min" label="Năng suất tối thiểu / công" type="number"/>
    <LotusField v-model="rateForm.norm_max" label="Năng suất tối đa / công" type="number"/>
    <LotusField v-model="rateForm.valid_from" label="Áp dụng từ" type="date" required/>
    <LotusField v-model="rateForm.valid_to" label="Đến ngày" type="date"/>
    <LotusField v-model="rateForm.notes" label="Ghi chú" type="textarea" wide/>
   </FormGrid>
  </ModalForm>
  <ModalForm :model-value="!!modeForm" :title="'Cách trả · '+(modeForm?.work_name||'')" width="560px" :busy="formBusy" :error="formError" @update:model-value="v=>!v&&(modeForm=null)" @submit="submit('mode')">
   <FormGrid v-if="modeForm" :columns="1">
    <LotusField v-model="modeForm.group" label="Nhóm việc" type="select" :searchable="false" :options="toOptions(groups)" required/>
    <LotusField v-model="modeForm.pay_mode" label="Cách trả" type="select" :searchable="false" :options="toOptions(payModes)" required/>
    <LotusField v-model="modeForm.cap_basis" label="Trần khi báo" type="select" :searchable="false" :options="toOptions(capBases)"/>
    <LotusField v-model="modeForm.requires_material" label="Bắt buộc ghi vật tư" type="checkbox"/>
   </FormGrid>
  </ModalForm>
 </div>
</template>

<style>
.field-report-scope{margin-bottom:12px}
</style>
