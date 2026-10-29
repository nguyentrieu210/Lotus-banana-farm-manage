<script setup>
import {computed,onBeforeUnmount,onMounted,ref,watch} from 'vue'
import LotusField from './components/form/LotusField.vue'
import LotusMobileShell from './components/LotusMobileShell.vue'
import LotusMobileFeedback from './components/LotusMobileFeedback.vue'
import LotusMobileButton from './components/LotusMobileButton.vue'
import LotusMobileDialog from './components/LotusMobileDialog.vue'
import LotusMobileSignatureSettings from './components/LotusMobileSignatureSettings.vue'
import FieldReportDay from './components/field/FieldReportDay.vue'
import FieldAssignments from './components/field/FieldAssignments.vue'
import {useMobileConfirm} from './use-mobile-confirm'
import {useMobileViewport} from './use-mobile-viewport'
import {logoutPwa} from './mobile-push-session'
import {call,setCSRF} from './api'
import {formatDate} from './format'
import {reportStates,money,amountText} from './field-report-model.js'
// Công việc ngoài vườn (/work): the đội daily report on the phone. Tổ trưởng report on the phiếu giao of their own tổ at
// the office (wifi); the đội trưởng gives việc theo lô (tab Giao việc), adds công nhật and confirms the day; the same
// screens as /lotus/cong-viec.
const {keyboard}=useMobileViewport()
function openSetup(){window.dispatchEvent(new Event('lotus:open-setup'))}
const api=(name,args={},write=false)=>call('lotus_farm.field_report.'+name,args,write)
const allTabs=[{name:'home',label:'Báo cáo',icon:'notes-o'},{name:'assign',label:'Giao việc',icon:'todo-list-o'},{name:'history',label:'Đã báo cáo',icon:'orders-o'},{name:'profile',label:'Tôi',icon:'user-o'}]
const screen=ref('home'),session=ref(null),setup=ref(null),farm=ref(''),crew=ref(''),date=ref('')
const busy=ref(false),saving=ref(false),error=ref(''),reports=ref([]),dayView=ref(null)
const {dialog:leaveDialog,message:leaveMessage,ask:askLeave,finish:finishLeave}=useMobileConfirm()
const mobileTitle=computed(()=>({home:'Báo cáo ngày',assign:'Giao việc theo lô',history:'Đã báo cáo',profile:'Tôi'})[screen.value])
const farms=computed(()=>(session.value?.farms||[]).map(f=>({value:f.name,label:f.farm_name||f.name})))
const crews=computed(()=>(setup.value?.crews||[]).filter(c=>(setup.value?.my_crews||[]).includes(c.name)))
const crewOptions=computed(()=>crews.value.map(c=>({value:c.name,label:c.team_name})))
// Giao việc shows only for a đội trưởng (or quản lý vườn).
const supervises=computed(()=>(setup.value?.supervised_crews||[]).length>0)
const mobileTabs=computed(()=>allTabs.filter(t=>t.name!=='assign'||supervises.value))
const tabs=computed(()=>mobileTabs.value.map(t=>t.name))
const crewName=name=>(setup.value?.crews||[]).find(c=>c.name===name)?.team_name||name
const farmName=computed(()=>(session.value?.farms||[]).find(f=>f.name===farm.value)?.farm_name||farm.value||'Chọn vườn')

async function loadSetup(){
 setup.value=farm.value?await api('setup',{farm:farm.value}):null
 if(!crews.value.some(c=>c.name===crew.value))crew.value=crews.value[0]?.name||''
}
async function bootstrap(){
 busy.value=true;error.value=''
 try{
  session.value=await api('bootstrap');setCSRF(session.value.csrf_token)
  date.value=session.value.today
  // Start on the first farm where this account leads a đội or tổ.
  for(const f of session.value.farms){farm.value=f.name;await loadSetup();if(crews.value.length)break}
 }catch(e){error.value=e.message}
 finally{busy.value=false}
}
async function loadHistory(){
 if(!farm.value)return
 busy.value=true;error.value=''
 try{
  const to=session.value.today,from=new Date(Date.parse(to)-30*86400000).toISOString().slice(0,10)
  reports.value=await api('reports',{farm:farm.value,from_date:from,to_date:to})
 }catch(e){error.value=e.message}
 finally{busy.value=false}
}
function confirmLeave(){
 if(!dayView.value?.hasChanges())return Promise.resolve(true)
 return askLeave('Báo cáo có thay đổi chưa lưu. Rời màn hình sẽ mất phần đang nhập.')
}
async function changeTab(tab){
 if(saving.value||!tabs.value.includes(tab)||screen.value===tab||!await confirmLeave())return
 screen.value=tab;error.value='';window.scrollTo({top:0,behavior:'instant'})
 if(tab==='history')await loadHistory()
}
async function openReport(row){crew.value=row.crew;date.value=row.date;screen.value='home'}
async function changeFarm(value){if(!await confirmLeave())return;farm.value=value;await loadSetup()}
async function refreshCurrentScreen(){if(screen.value==='history')await loadHistory();else await dayView.value?.reload()}
async function logout(){
 if(saving.value||!await confirmLeave()||!await askLeave('Đăng xuất khỏi Công việc ngoài vườn?'))return
 saving.value=true;error.value=''
 try{await logoutPwa('work',{csrf:session.value?.csrf_token||'',home:'/work'})}
 catch(e){error.value='Không đăng xuất được: '+(e?.message||'')}
 finally{saving.value=false}
}
function beforeUnload(e){if(dayView.value?.hasChanges()){e.preventDefault();e.returnValue=''}}
watch(error,value=>{if(value)requestAnimationFrame(()=>document.querySelector('.lotus-work .lotus-mobile-feedback')?.scrollIntoView({block:'nearest',behavior:'smooth'}))})
onMounted(()=>{window.addEventListener('beforeunload',beforeUnload);bootstrap()})
onBeforeUnmount(()=>{finishLeave(false);window.removeEventListener('beforeunload',beforeUnload)})
</script>

<template>
 <LotusMobileShell app="work" :user="session?.user||''" :refresh="refreshCurrentScreen" :refreshable="true" class="lotus-mobile lotus-work" :class="{'mobile-keyboard-open':keyboard}"
  :title="mobileTitle" :tabs="mobileTabs" :active-tab="screen" :back="false" :keyboard-open="keyboard" :disabled="saving"
  @navigate="changeTab">
  <main class="mobile-container" id="lotus-content" :aria-busy="busy||saving">
   <LotusMobileFeedback v-if="error" kind="error">{{error}}</LotusMobileFeedback>
   <LotusMobileFeedback v-if="busy" kind="loading">Đang tải dữ liệu…</LotusMobileFeedback>
   <template v-if="session">
    <template v-if="screen==='home'">
     <div class="work-scope">
      <LotusField v-if="farms.length>1" :model-value="farm" label="Vườn" type="select" :searchable="false" :options="farms" mobile @update:model-value="changeFarm"/>
      <LotusField v-if="crewOptions.length>1" v-model="crew" label="Đội" type="select" :searchable="false" :options="crewOptions" mobile/>
      <LotusField v-model="date" label="Ngày" type="date" mobile/>
     </div>
     <LotusMobileFeedback v-if="setup&&!crewOptions.length" kind="warning">Tài khoản chưa là tổ trưởng hoặc đội trưởng của đội nào. Nhờ quản lý vườn xếp ở Báo cáo ngày → Đội, tổ &amp; lô.</LotusMobileFeedback>
     <FieldReportDay v-if="setup&&crew&&date" ref="dayView" :farm="farm" :crew="crew" :date="date" :setup="setup" mobile @busy-change="saving=$event"/>
    </template>

    <template v-else-if="screen==='assign'">
     <div class="work-scope"><LotusField v-if="crewOptions.length>1" v-model="crew" label="Đội" type="select" :searchable="false" :options="crewOptions" mobile/></div>
     <FieldAssignments v-if="setup&&crew" :farm="farm" :crew="crew" :setup="setup" mobile/>
    </template>

    <template v-else-if="screen==='history'">
     <p v-if="!reports.length&&!busy" class="work-muted">Chưa có báo cáo trong 30 ngày gần đây.</p>
     <button v-for="r in reports" :key="r.name" type="button" class="mobile-list-card work-report-card" @click="openReport(r)">
      <strong>{{formatDate(r.date)}} · {{crewName(r.crew)}}</strong>
      <span>{{r.overdue?'Quá hạn xác nhận':reportStates[r.state]}} · {{r.lines}} dòng · {{amountText(r.workdays)}} công · {{money(r.piece_amount)}}</span>
     </button>
    </template>

    <template v-else-if="screen==='profile'">
     <h1>Tôi</h1>
     <section class="mobile-account"><div class="mobile-avatar" aria-hidden="true">👤</div><div><strong>{{session.user}}</strong><small>Tài khoản Công việc ngoài vườn</small></div></section>
     <div class="mobile-list-card"><div class="mobile-profile-row"><span>Vườn</span><strong>{{farmName}}</strong></div></div>
     <LotusField v-if="farms.length>1" :model-value="farm" label="Đổi vườn" type="select" :searchable="false" :options="farms" mobile @update:model-value="changeFarm"/>
     <a class="work-outline" href="/lotus/cong-viec">Mở trên máy tính</a>
     <LotusMobileSignatureSettings :user="session?.user||''"/>
     <LotusMobileButton type="button" @click="openSetup">Cài ứng dụng và thông báo</LotusMobileButton>
     <LotusMobileButton class="mobile-logout" type="button" :disabled="saving" @click="logout">Đăng xuất</LotusMobileButton>
    </template>
   </template>
  </main>
  <LotusMobileDialog ref="leaveDialog" class="mobile-leave-dialog" @cancel.prevent="finishLeave(false)">
   <div class="mobile-leave-content"><h2>Rời màn hình?</h2><p>{{leaveMessage}}</p><div><LotusMobileButton type="button" autofocus @click="finishLeave(false)">Ở lại</LotusMobileButton><LotusMobileButton type="button" class="danger" @click="finishLeave(true)">Rời đi</LotusMobileButton></div></div>
  </LotusMobileDialog>
 </LotusMobileShell>
</template>

<style>
.lotus-work .work-scope{display:grid;gap:8px;margin-bottom:12px}
.lotus-work .work-report-card{display:grid;gap:4px;width:100%;text-align:left;font:inherit;cursor:pointer}
.lotus-work .work-report-card span{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
</style>
