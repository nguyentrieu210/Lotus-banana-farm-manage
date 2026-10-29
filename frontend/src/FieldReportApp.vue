<script setup>
const props=defineProps({embedded:Boolean,navigationKey:String,fieldView:String})
import {computed,inject,onMounted,provide,ref,watch} from 'vue'
import {routerKey,routeLocationKey} from 'vue-router'
import {call,setCSRF} from './api'
import {useDesktopWorkspace} from './use-desktop-workspace'
import {sidebarCollapsed} from './workspace'
import {normalizeFieldView} from './field-report-navigation.js'
import {reportStates,payShort,basisLabels,money,amountText} from './field-report-model.js'
import {unitLabel} from './units'
import FieldReportDay from './components/field/FieldReportDay.vue'
import FieldAssignments from './components/field/FieldAssignments.vue'
import FieldBoard from './components/field/FieldBoard.vue'
import FarmWorkApp from './FarmWorkApp.vue'
import ListPage from './components/ListPage.vue'
import LotusField from './components/form/LotusField.vue'
import FormGrid from './components/form/FormGrid.vue'
import ModalForm from './components/form/ModalForm.vue'
import FormSection from './components/form/FormSection.vue'
import {Button as UiButton} from './components/ui/button'
import WorkspaceConfirm from './components/WorkspaceConfirm.vue'
import {useWorkspaceConfirm} from './use-workspace-confirm'
// Công việc vườn: the đội daily report (báo cáo ngày), giao việc theo lô and the lô × việc board, its lists, the month's
// tiền khoán and the giao lô setup.
const {desktop,density,gridDensity}=useDesktopWorkspace({embedded:props.embedded})
provide('lotusDesktopDensity',gridDensity)
const router=inject(routerKey,null),route=inject(routeLocationKey,null)
const api=(name,args={},write=false)=>call('lotus_farm.field_report.'+name,args,write)
const confirm=useWorkspaceConfirm()
const view=ref(normalizeFieldView(props.fieldView))
const session=ref(null),setup=ref(null),farm=ref(''),crew=ref(''),day=ref(''),busy=ref(false),error=ref(''),notice=ref('')
const dayView=ref(null)
const today=computed(()=>session.value?.today||'')
const monthStart=value=>String(value||'').slice(0,8)+'01'
const fromDate=ref(''),toDate=ref(''),listCrew=ref(''),month=ref('')
const rows=ref([]),search=ref(''),loading=ref(false)

const farmOptions=computed(()=>(session.value?.farms||[]).map(f=>({value:f.name,label:f.farm_name||f.name})))
const crews=computed(()=>setup.value?.crews||[])
const myCrews=computed(()=>crews.value.filter(c=>(setup.value?.my_crews||[]).includes(c.name)))
const crewOptions=computed(()=>myCrews.value.map(c=>({value:c.name,label:c.team_name+(c.zones?.length?' (khu '+c.zones.join(', ')+')':'')})))
const allCrewOptions=computed(()=>[{value:'',label:'Tất cả đội'},...crewOptions.value])
const crewName=name=>crews.value.find(c=>c.name===name)?.team_name||name||''
const teamName=name=>(setup.value?.teams||[]).find(t=>t.name===name)?.team_name||name||''
const workName=name=>(setup.value?.works||[]).find(w=>w.name===name)?.work_name||name||''
const blockCode=name=>(setup.value?.blocks||[]).find(b=>b.name===name)?.block_code||name||''

function query(extra={}){return {...(route?.query||{}),field_view:view.value,farm:farm.value||undefined,crew:crew.value||undefined,date:day.value||undefined,...extra}}
async function go(next,extra={}){
 if(dayView.value?.hasChanges()&&!await confirm.ask('Báo cáo có thay đổi chưa lưu. Bỏ và chuyển mục?'))return
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
  crew.value=q.crew||'';day.value=q.date||session.value.today
  fromDate.value=monthStart(session.value.today);toDate.value=session.value.today;month.value=session.value.today.slice(0,7)
  await loadSetup();await loadView()
 }catch(e){error.value=e.message}
 finally{busy.value=false}
}
onMounted(boot)
watch(()=>props.fieldView,value=>{const next=normalizeFieldView(value);if(next!==view.value){view.value=next;loadView()}})

async function loadView(){
 if(!setup.value)return
 const v=view.value
 if(!['reports','bunch','payable','rates'].includes(v))return
 loading.value=true;error.value=''
 try{
  if(v==='reports')rows.value=await api('reports',{farm:farm.value,from_date:fromDate.value,to_date:toDate.value,crew:listCrew.value||null})
  else if(v==='bunch')rows.value=await api('report_lines',{farm:farm.value,from_date:fromDate.value,to_date:toDate.value,crew:listCrew.value||null,section:'Bunch'})
  else if(v==='payable')rows.value=(await api('payable',{farm:farm.value,month:month.value})).map(r=>({...r,key:[r.work_team,r.work_type,r.rate].join('|')}))
  else rows.value=setup.value.rates
 }catch(e){error.value=e.message;rows.value=[]}
 finally{loading.value=false}
}
async function changeFarm(value){farm.value=value;crew.value='';await loadSetup();await loadView()}
function openReport(row){crew.value=row.crew;day.value=row.date;go('day')}

const reportColumns=[
 {field:'date',headerName:'Ngày',minWidth:110},
 {field:'crew',headerName:'Đội',valueGetter:p=>crewName(p.data.crew),minWidth:150},
 {field:'state',headerName:'Trạng thái',valueGetter:p=>p.data.overdue?'Quá hạn xác nhận':reportStates[p.data.state]||p.data.state,minWidth:140},
 {field:'lines',headerName:'Số dòng',minWidth:90},
 {field:'workdays',headerName:'Tổng công',minWidth:100},
 {field:'piece_amount',headerName:'Tiền khoán',valueFormatter:p=>money(p.value),minWidth:130,sum:true},
 {field:'under_norm',headerName:'Chưa đạt',minWidth:90},
 {field:'weather',headerName:'Thời tiết',minWidth:160},
]
const bunchColumns=[
 {field:'date',headerName:'Ngày',minWidth:110},
 {field:'crew',headerName:'Đội',valueGetter:p=>crewName(p.data.crew),minWidth:130},
 {field:'work_team',headerName:'Tổ',valueGetter:p=>teamName(p.data.work_team),minWidth:110},
 {field:'work_type',headerName:'Công đoạn',valueGetter:p=>workName(p.data.work_type),minWidth:150},
 {field:'farm_block',headerName:'Lô',valueGetter:p=>blockCode(p.data.farm_block),minWidth:80},
 {field:'qty',headerName:'Số buồng',minWidth:100,sum:true},
 {field:'ribbon',headerName:'Màu dây',minWidth:130},
 {field:'pay_kind',headerName:'Loại công',valueGetter:p=>payShort[p.data.pay_kind],minWidth:90},
 {field:'amount',headerName:'Thành tiền',valueFormatter:p=>money(p.value),minWidth:120,sum:true},
 {field:'state',headerName:'Trạng thái',valueGetter:p=>reportStates[p.data.state],minWidth:120},
]
const payableColumns=[
 {field:'work_team',headerName:'Tổ',valueGetter:p=>teamName(p.data.work_team),minWidth:130},
 {field:'work_type',headerName:'Công việc',valueGetter:p=>workName(p.data.work_type),minWidth:180},
 {field:'qty',headerName:'Khối lượng',minWidth:110,unitField:'uom'},
 {field:'uom',headerName:'ĐVT',valueGetter:p=>unitLabel(p.data.uom)||p.data.uom,minWidth:80},
 {field:'rate',headerName:'Đơn giá',valueFormatter:p=>money(p.value),minWidth:110},
 {field:'workdays',headerName:'Số công',minWidth:90},
 {field:'amount',headerName:'Thành tiền',valueFormatter:p=>money(p.value),minWidth:130,sum:true},
]
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
]
const users=ref([]),crewForm=ref(null),teamForm=ref(null),rateForm=ref(null),formBusy=ref(false),formError=ref('')
const userOptions=computed(()=>[{value:'',label:'Chưa chọn'},...users.value.map(u=>({value:u.name,label:(u.full_name||u.name)+' · '+u.name}))])
async function needUsers(){if(!users.value.length)users.value=await api('user_options',{farm:farm.value})}
async function editCrew(row){formError.value='';await needUsers();crewForm.value={name:row?.name||null,team_name:row?.team_name||'',zones:(row?.zones||[]).join(', '),leader:row?.lotus_leader||''}}
async function editTeam(row){formError.value='';await needUsers();teamForm.value={name:row.name,team_name:row.team_name,crew:row.lotus_parent_team||'',leader:row.lotus_leader||''}}
function newRate(){formError.value='';rateForm.value={work_type:'',basis:'Count',rate:null,uom:'',norm_min:null,norm_max:null,valid_from:today.value,valid_to:'',notes:''}}
async function submit(kind){
 formBusy.value=true;formError.value=''
 try{
  if(kind==='crew'){await api('save_crew',{farm:farm.value,...crewForm.value},true);crewForm.value=null;notice.value='Đã lưu đội.'}
  else if(kind==='team'){const f=teamForm.value;await api('save_team',{farm:farm.value,name:f.name,crew:f.crew||null,leader:f.leader||null},true);teamForm.value=null;notice.value='Đã xếp tổ.'}
  else{await api('save_rate',{farm:farm.value,...rateForm.value,valid_to:rateForm.value.valid_to||null},true);rateForm.value=null;notice.value='Đã lưu giá khoán.'}
  await loadSetup();await loadView()
 }catch(e){formError.value=e.message}
 finally{formBusy.value=false}
}
const workOptions=computed(()=>(setup.value?.works||[]).map(w=>({value:w.name,label:w.work_name})))
const basisOptions=Object.entries(basisLabels).map(([value,label])=>({value,label:'Tính '+label}))
const filtered=computed(()=>{const q=search.value.trim().toLowerCase();return q?rows.value.filter(r=>JSON.stringify(r).toLowerCase().includes(q)):rows.value})
defineExpose({hasChanges:()=>!!dayView.value?.hasChanges(),discardChanges:()=>{},scopeParams:()=>({farm:farm.value})})
</script>

<template>
 <div class="stock-shell field-report-shell lotus-ui" :class="{'embedded-workspace':embedded,'sidebar-collapsed':sidebarCollapsed,'lotus-desktop':desktop,'desktop-compact':density==='compact'}">
  <component :is="embedded?'section':'main'" class="stock-main">
   <p v-if="error" class="stock-error" role="alert">{{error}}</p>
   <p v-if="notice" class="stock-success" role="status">{{notice}}</p>
   <p v-if="busy&&!session" class="lotus-form-note" role="status">Đang tải…</p>
   <template v-if="session&&setup">
    <template v-if="['day','assign','board'].includes(view)">
     <FormGrid :columns="4" class="field-report-scope">
      <LotusField v-if="farmOptions.length>1" :model-value="farm" label="Vườn" :options="farmOptions" @update:model-value="changeFarm"/>
      <LotusField v-model="crew" label="Đội" type="select" :searchable="false" :options="crewOptions" empty-option="Chưa có đội"/>
      <LotusField v-if="view==='day'" v-model="day" label="Ngày" type="date"/>
     </FormGrid>
     <p v-if="!crewOptions.length" class="lotus-form-note">Tài khoản chưa là đội trưởng hoặc tổ trưởng của đội nào. Vào <a href="/lotus/cong-viec?field_view=lots">Đội, tổ &amp; lô</a> để xếp.</p>
     <FieldReportDay v-if="view==='day'&&crew&&day" ref="dayView" :farm="farm" :crew="crew" :date="day" :setup="setup"/>
     <FieldAssignments v-else-if="view==='assign'&&crew" :farm="farm" :crew="crew" :setup="setup"/>
     <FieldBoard v-else-if="view==='board'&&crew" v-model:month="month" :farm="farm" :crew="crew"/>
    </template>

    <ListPage v-else-if="view==='reports'" v-model:search="search" title="Danh sách báo cáo" :rows="filtered" :columns="reportColumns" :loading="loading" row-key="name" storage-key="field-reports" interactive @open="openReport" @refresh="loadView">
     <template #filters><LotusField v-model="fromDate" type="date" aria-label="Từ ngày" @update:model-value="loadView"/><LotusField v-model="toDate" type="date" aria-label="Đến ngày" @update:model-value="loadView"/><LotusField v-model="listCrew" type="select" :searchable="false" :options="allCrewOptions" empty-option="Tất cả đội" aria-label="Đội" @update:model-value="loadView"/></template>
    </ListPage>

    <ListPage v-else-if="view==='bunch'" v-model:search="search" title="Chăm sóc buồng" :rows="filtered" :columns="bunchColumns" :loading="loading" row-key="line_id" storage-key="field-bunch" @refresh="loadView">
     <template #filters><LotusField v-model="fromDate" type="date" aria-label="Từ ngày" @update:model-value="loadView"/><LotusField v-model="toDate" type="date" aria-label="Đến ngày" @update:model-value="loadView"/><LotusField v-model="listCrew" type="select" :searchable="false" :options="allCrewOptions" empty-option="Tất cả đội" aria-label="Đội" @update:model-value="loadView"/></template>
    </ListPage>

    <ListPage v-else-if="view==='payable'" v-model:search="search" title="Tiền khoán tháng" :rows="filtered" :columns="payableColumns" :loading="loading" row-key="key" storage-key="field-payable" @refresh="loadView">
     <template #filters><LotusField v-model="month" type="month" aria-label="Tháng" @update:model-value="loadView"/></template>
     <template #before><p class="lotus-form-note">Chỉ tính dòng công khoán của báo cáo đã xác nhận. Số này cũng hiện ở Chấm công → Phải trả đội khoán.</p></template>
    </ListPage>

    <template v-else-if="view==='lots'">
     <FormSection title="Đội" description="Lô thuộc đội theo khu. Quản lý vườn tạo đội và chọn đội trưởng.">
      <template v-if="setup.manager" #actions><UiButton type="button" @click="editCrew(null)">Thêm đội</UiButton></template>
      <ListPage :rows="crews" :columns="crewColumns" :searchable="false" row-key="name" storage-key="field-crews" :interactive="setup.manager" @open="editCrew" @refresh="loadSetup"/>
     </FormSection>
     <FormSection title="Tổ" description="Đội trưởng xếp tổ vào đội và chọn tổ trưởng (tài khoản đã được cấp quyền vườn).">
      <ListPage :rows="setup.teams" :columns="teamColumns" :searchable="false" row-key="name" storage-key="field-teams" interactive @open="editTeam" @refresh="loadSetup"/>
     </FormSection>
     <FormSection title="Lô" description="Diện tích và số cây hiện có của lô là căn cứ tính khoán cả lô.">
      <ListPage :rows="setup.blocks" :columns="blockColumns" :searchable="false" row-key="name" storage-key="field-blocks" @refresh="loadSetup"/>
     </FormSection>
    </template>

    <ListPage v-else-if="view==='rates'" v-model:search="search" title="Bảng giá khoán" :rows="filtered" :columns="rateColumns" :loading="loading" row-key="name" storage-key="field-rates" @refresh="loadView">
     <template v-if="setup.manager" #actions><UiButton type="button" @click="newRate">Thêm giá</UiButton></template>
     <template #before><p class="lotus-form-note">Đổi giá: thêm dòng mới với ngày áp dụng mới. Giá đã dùng trong báo cáo không sửa.</p></template>
    </ListPage>

    <FarmWorkApp v-else-if="view==='catalog'" embedded/>
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
    <LotusField v-model="teamForm.leader" label="Tổ trưởng" :options="userOptions" hint="Tổ trưởng nhập báo cáo của tổ mình."/>
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
  <WorkspaceConfirm :open="confirm.open.value" :title="confirm.title.value" :message="confirm.message.value" :alert-only="confirm.alertOnly.value" @answer="confirm.finish"/>
 </div>
</template>

<style>
.field-report-scope{margin-bottom:12px}
</style>
