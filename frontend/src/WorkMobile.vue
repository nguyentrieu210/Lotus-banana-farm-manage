<script setup>
import {computed,onBeforeUnmount,onMounted,ref,watch} from 'vue'
import LotusField from './components/form/LotusField.vue'
import LotusMobileShell from './components/LotusMobileShell.vue'
import LotusMobileFeedback from './components/LotusMobileFeedback.vue'
import LotusMobileButton from './components/LotusMobileButton.vue'
import LotusMobileDialog from './components/LotusMobileDialog.vue'
import LotusMobileSignatureSettings from './components/LotusMobileSignatureSettings.vue'
import LotToday from './components/field/LotToday.vue'
import CrewStatus from './components/field/CrewStatus.vue'
import RibbonBoard from './components/field/RibbonBoard.vue'
import CareDueList from './components/field/CareDueList.vue'
import MyPay from './components/field/MyPay.vue'
import WorkAssign from './components/field/WorkAssign.vue'
import ReleaseNotes from './components/ReleaseNotes.vue'
import WorkInspect from './components/field/WorkInspect.vue'
import {useMobileConfirm} from './use-mobile-confirm'
import {useMobileViewport} from './use-mobile-viewport'
import {logoutPwa} from './mobile-push-session'
import {call,setCSRF} from './api'
// Công việc ngoài vườn (/work) on the phone: Hôm nay (báo cáo ngày of the tổ, lô by lô), Xác nhận and Giao việc (đội
// trưởng), Nghiệm thu (kỹ thuật vườn) and Tôi (tiền khoán tạm tính). The same components as /lotus/cong-viec, with `mobile`.
const {keyboard}=useMobileViewport()
function openSetup(){window.dispatchEvent(new Event('lotus:open-setup'))}
const api=(name,args={},write=false)=>call('lotus_farm.field_report.'+name,args,write)
const allTabs=[{name:'home',label:'Hôm nay',icon:'notes-o'},{name:'confirm',label:'Xác nhận',icon:'certificate'},{name:'assign',label:'Giao việc',icon:'todo-list-o'},{name:'profile',label:'Tôi',icon:'user-o'}]
const screen=ref('home'),session=ref(null),setup=ref(null),farm=ref(''),crew=ref(''),date=ref('')
const busy=ref(false),saving=ref(false),error=ref('')
const {dialog:leaveDialog,message:leaveMessage,ask:askLeave,finish:finishLeave}=useMobileConfirm()
const mobileTitle=computed(()=>({home:'Báo cáo hôm nay',confirm:'Xác nhận báo cáo',assign:'Giao việc theo lô',inspect:'Nghiệm thu',profile:'Tôi'})[screen.value])
const farms=computed(()=>(session.value?.farms||[]).map(f=>({value:f.name,label:f.farm_name||f.name})))
const crews=computed(()=>(setup.value?.crews||[]).filter(c=>(setup.value?.my_crews||[]).includes(c.name)))
const crewOptions=computed(()=>crews.value.map(c=>({value:c.name,label:c.team_name})))
// Giao việc shows only for a đội trưởng (or quản lý vườn); Nghiệm thu only for a kỹ thuật vườn (or quản lý vườn).
const supervises=computed(()=>(setup.value?.supervised_crews||[]).length>0)
// Four tabs (spec 002): Hôm nay, Giao việc (with nghiệm thu for kỹ thuật vườn), Xác nhận, Tôi.
const mobileTabs=computed(()=>allTabs.filter(t=>t.name==='assign'?supervises.value||!!setup.value?.inspector:t.name!=='confirm'||supervises.value))
const tabs=computed(()=>mobileTabs.value.map(t=>t.name))
const farmName=computed(()=>(session.value?.farms||[]).find(f=>f.name===farm.value)?.farm_name||farm.value||'Chọn vườn')
const refreshKey=ref(0),pickedTeam=ref('')
function openTeam(team){pickedTeam.value=team;refreshKey.value++;changeTab('home')}

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
async function changeTab(tab){
 if(saving.value||!tabs.value.includes(tab)||screen.value===tab)return
 screen.value=tab;error.value='';window.scrollTo({top:0,behavior:'instant'})
}
async function changeFarm(value){farm.value=value;await loadSetup()}
async function refreshCurrentScreen(){refreshKey.value++}
async function logout(){
 if(saving.value||!await askLeave('Đăng xuất khỏi Công việc ngoài vườn?'))return
 saving.value=true;error.value=''
 try{await logoutPwa('work',{csrf:session.value?.csrf_token||'',home:'/work'})}
 catch(e){error.value='Không đăng xuất được: '+(e?.message||'')}
 finally{saving.value=false}
}
watch(error,value=>{if(value)requestAnimationFrame(()=>document.querySelector('.lotus-work .lotus-mobile-feedback')?.scrollIntoView({block:'nearest',behavior:'smooth'}))})
onMounted(bootstrap)
onBeforeUnmount(()=>finishLeave(false))
</script>

<template>
 <LotusMobileShell app="work" :user="session?.user||''" :refresh="refreshCurrentScreen" :refreshable="true" class="lotus-mobile lotus-work" :class="{'mobile-keyboard-open':keyboard}"
  :title="mobileTitle" :tabs="mobileTabs" :active-tab="screen" :back="false" :keyboard-open="keyboard" :disabled="saving"
  @navigate="changeTab">
  <main class="mobile-container" id="lotus-content" :aria-busy="busy||saving">
   <LotusMobileFeedback v-if="error" kind="error">{{error}}</LotusMobileFeedback>
   <LotusMobileFeedback v-if="busy" kind="loading">Đang tải dữ liệu…</LotusMobileFeedback>
   <template v-if="session">
    <div v-if="['home','confirm','assign'].includes(screen)" class="work-scope">
     <LotusField v-if="farms.length>1" :model-value="farm" label="Vườn" type="select" :searchable="false" :options="farms" mobile @update:model-value="changeFarm"/>
     <LotusField v-if="crewOptions.length>1" v-model="crew" label="Đội" type="select" :searchable="false" :options="crewOptions" mobile/>
    </div>
    <LotusMobileFeedback v-if="setup&&!crewOptions.length&&screen!=='inspect'&&screen!=='profile'" kind="warning">Tài khoản chưa là tổ trưởng hoặc đội trưởng của đội nào. Nhờ quản lý vườn xếp ở Công việc ngoài vườn → Đội, tổ &amp; lô.</LotusMobileFeedback>

    <LotToday v-if="screen==='home'&&setup&&crew&&date" :key="'today'+refreshKey+crew" v-model:date="date" :farm="farm" :crew="crew" :setup="setup" :initial-team="pickedTeam" mobile/>
    <template v-else-if="screen==='confirm'&&setup&&crew">
     <CrewStatus :key="'confirm'+refreshKey+crew" :farm="farm" :crew="crew" :date="date" mobile @pick="openTeam"/>
     <h2 class="work-section-title">Màu dây &amp; cần thu</h2>
     <RibbonBoard :key="'ribbon'+refreshKey+farm" :farm="farm" mobile compact/>
    </template>
    <template v-else-if="screen==='assign'&&setup">
     <template v-if="crew&&supervises">
      <CareDueList :key="'due'+refreshKey+crew" :farm="farm" :crew="crew" mobile @assigned="refreshKey++"/>
      <h2 class="work-section-title">Phiếu đã giao</h2>
      <WorkAssign :key="'assign'+refreshKey" :farm="farm" :crew="crew" :setup="setup" mobile/>
     </template>
     <template v-if="setup.inspector"><h2 class="work-section-title">Chờ nghiệm thu khoán lô</h2><WorkInspect :key="'inspect'+refreshKey" :farm="farm" :setup="setup" mobile/></template>
    </template>

    <template v-else-if="screen==='profile'">
     <h1>Tôi</h1>
     <section class="mobile-account"><div class="mobile-avatar" aria-hidden="true">👤</div><div><strong>{{session.user}}</strong><small>Tài khoản Công việc ngoài vườn</small></div></section>
     <div class="mobile-list-card"><div class="mobile-profile-row"><span>Vườn</span><strong>{{farmName}}</strong></div></div>
     <MyPay v-if="farm" :key="'pay'+refreshKey" :farm="farm" mobile/>
     <LotusField v-if="farms.length>1" :model-value="farm" label="Đổi vườn" type="select" :searchable="false" :options="farms" mobile @update:model-value="changeFarm"/>
     <a class="work-outline" href="/lotus/cong-viec">Mở trên máy tính</a>
     <LotusMobileSignatureSettings :user="session?.user||''"/>
     <LotusMobileButton type="button" @click="openSetup">Cài ứng dụng và thông báo</LotusMobileButton>
     <LotusMobileButton class="mobile-logout" type="button" :disabled="saving" @click="logout">Đăng xuất</LotusMobileButton>
    </template>
   </template>
  </main>
  <ReleaseNotes :user="session?.user||''"/>
  <LotusMobileDialog ref="leaveDialog" class="mobile-leave-dialog" @cancel.prevent="finishLeave(false)">
   <div class="mobile-leave-content"><h2>Rời màn hình?</h2><p>{{leaveMessage}}</p><div><LotusMobileButton type="button" autofocus @click="finishLeave(false)">Ở lại</LotusMobileButton><LotusMobileButton type="button" class="danger" @click="finishLeave(true)">Rời đi</LotusMobileButton></div></div>
  </LotusMobileDialog>
 </LotusMobileShell>
</template>

<style>
.lotus-work .work-scope{display:grid;gap:8px;margin-bottom:12px}
.lotus-work .work-section-title{margin:18px 0 8px;font-size:var(--lotus-text-md);font-weight:600;color:var(--lotus-text-strong)}
</style>
