<script setup>
import {computed,onMounted,reactive,ref} from 'vue'
import {call,consoleAPI,setCSRF} from './api'
import {has,shortcuts,taskStatus,pathWithFarm} from './mobile-nav'

const session=ref(null),profile=ref(null),farm=ref(''),date=ref('')
const loading=ref(true),refreshing=ref(false),saving=ref(false)
const error=ref(''),saved=ref(''),tab=ref('today')
const day=ref(null),catalog=ref(null)
const report=reactive({farm_plot:'',crop_cycle:'',sucker_selection_batch:'',disease:'',affected_plants:'',severity:'Medium',action_taken:''})
const options=computed(()=>shortcuts(profile.value,session.value||{}))
const farmLabel=computed(()=>profile.value?.farms?.find(f=>f.name===farm.value)?.farm_name||farm.value)
const crops=computed(()=>catalog.value?.cycles?.filter(c=>c.farm_plot===report.farm_plot)||[])
const cohorts=computed(()=>catalog.value?.cohorts?.filter(c=>c.crop_cycle===report.crop_cycle)||[])
const crop=computed(()=>crops.value.find(c=>c.name===report.crop_cycle))
const tasks=computed(()=>day.value?.tasks||[])
const latest=computed(()=>tasks.value.slice(0,4))
const canObserve=computed(()=>has(profile.value,'observation'))
const canSeeTasks=computed(()=>has(profile.value,'tasks')||has(profile.value,'overview'))
const num=v=>Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:2})
const tabItems=[{key:'today',label:'Hôm nay',icon:'⌂'},{key:'tasks',label:'Công việc',icon:'☷'},{key:'entry',label:'Ghi nhận',icon:'✎'},{key:'account',label:'Tài khoản',icon:'♙'}]
let requestVersion=0

async function boot(){
 try{
  session.value=await consoleAPI('bootstrap')
  setCSRF(session.value.csrf_token)
  profile.value=await call('lotus_farm.mobile_portal.profile')
  date.value=profile.value.today
  const savedFarm=new URLSearchParams(location.search).get('farm')
  farm.value=profile.value.farms.some(f=>f.name===savedFarm)?savedFarm:(profile.value.farms[0]?.name||'')
  if(farm.value)await reload()
 }catch(e){error.value=e.message||'Không thể mở ứng dụng.'}
 finally{loading.value=false}
}

async function reload(){
 const seq=++requestVersion
 day.value=null;catalog.value=null;saved.value='';error.value=''
 if(!farm.value)return
 refreshing.value=true
 try{
  const response=await call('lotus_farm.mobile_portal.overview',{farm:farm.value,posting_date:date.value})
  if(seq!==requestVersion)return
  day.value=response
  if(canObserve.value){
   const c=await call('lotus_farm.mobile_portal.observation_options',{farm:farm.value})
   if(seq!==requestVersion)return
   catalog.value=c
  }
 }catch(e){if(seq===requestVersion)error.value=e.message}
 finally{if(seq===requestVersion)refreshing.value=false}
}
function selectTab(key){tab.value=key;error.value='';saved.value='';window.scrollTo?.(0,0)}
function changeFarm(){report.farm_plot='';report.crop_cycle='';report.sucker_selection_batch='';reload()}
function changePlot(){report.crop_cycle='';report.sucker_selection_batch=''}
function changeCycle(){report.sucker_selection_batch=''}
function openOption(item){
 if(item.tab){selectTab(item.tab);return}
 if(item.url)window.location.href=pathWithFarm(item.url,farm.value)
}
async function submitObservation(){
 if(saving.value||!canObserve.value)return
 error.value='';saved.value=''
 if(!farm.value||!report.farm_plot||!report.crop_cycle||!report.disease||!report.affected_plants||!report.action_taken.trim()){
  error.value='Hãy chọn thửa, vụ, loại bệnh, số cây và mô tả trước khi gửi.';return
 }
 if(crop.value?.cycle_type==='Ratoon'&&!report.sucker_selection_batch){
  error.value='Vụ tái sinh cần chọn đợt chồi.';return
 }
 saving.value=true
 try{
  const created=await call('lotus_farm.mobile_portal.report_observation',{
   farm:farm.value,posting_date:date.value,farm_plot:report.farm_plot,crop_cycle:report.crop_cycle,
   sucker_selection_batch:report.sucker_selection_batch||null,disease:report.disease,
   affected_plants:report.affected_plants,severity:report.severity,action_taken:report.action_taken.trim()
  },true)
  saved.value='Đã gửi phiếu kiểm tra '+created.name
  report.disease='';report.affected_plants='';report.action_taken=''
 }catch(e){error.value=e.message}
 finally{saving.value=false}
}
onMounted(boot)
</script>

<template>
 <div class="mobile-shell">
  <header class="hero">
   <div class="brand">LOTUS FARM · MOBILE</div>
   <h1>{{ tab==='today'?'Hôm nay':tab==='tasks'?'Công việc':tab==='entry'?'Ghi nhận tại vườn':'Tài khoản' }}</h1>
   <p v-if="profile">{{ profile.roles.map(r=>r.label).join(' · ')||'Quản trị hệ thống' }}</p>
   <p v-else>Ứng dụng chung cho nhiều bộ phận</p>
   <div v-if="profile?.farms?.length" class="scope">
    <label>Nông trường
     <select v-model="farm" @change="changeFarm" aria-label="Chọn nông trường">
      <option v-for="f in profile.farms" :key="f.name" :value="f.name">{{ f.farm_name||f.name }}</option>
     </select>
    </label>
    <label>Ngày
     <input v-model="date" type="date" @change="reload" aria-label="Chọn ngày"/>
    </label>
   </div>
  </header>

  <div v-if="loading" class="panel muted">Đang đọc quyền và nông trường được giao…</div>
  <template v-else>
   <div v-if="error" class="error" role="alert">{{error}}</div>
   <div v-if="saved" class="success" role="status">{{saved}}</div>
   <div v-if="profile&&!profile.farms.length" class="notice">Tài khoản chưa được cấp nông trường. Quản trị viên cần cấp User Permission → Farm trước khi dùng.</div>
   <template v-if="profile?.farms?.length">
    <template v-if="tab==='today'">
     <div class="section-head"><h2>{{farmLabel}}</h2><button class="soft" type="button" :disabled="refreshing" @click="reload">↻ Cập nhật</button></div>
     <div v-if="canSeeTasks" class="stats" aria-label="Tình hình công việc">
      <div class="stat"><strong>{{day?.total??'—'}}</strong><span>Việc được xem</span></div>
      <div class="stat"><strong>{{day?.completed??'—'}}</strong><span>Đã hoàn thành</span></div>
      <div class="stat"><strong>{{day?.remaining??'—'}}</strong><span>Chưa hoàn thành</span></div>
     </div>
     <div v-if="has(profile,'tasks')&&day?.team_assigned===false" class="notice">Tổ trưởng chưa được gán vào tổ. Nhờ quản lý mở danh mục Tổ làm việc và chọn “Tổ trưởng phụ trách”.</div>
     <div class="section-head"><h2>Chức năng của tôi</h2><span class="quiet">{{options.length}} mục</span></div>
     <div v-if="options.length" class="shortcut-grid">
      <button v-for="item in options" :key="item.name" class="shortcut" type="button" @click="openOption(item)">
       <span class="mark" aria-hidden="true">{{item.icon}}</span><strong>{{item.name}}</strong><small>{{item.detail}}</small>
      </button>
     </div>
     <div v-else class="notice">Chưa có chức năng phù hợp với quyền hiện tại. Liên hệ quản trị viên để phân quyền.</div>
     <template v-if="canSeeTasks&&latest.length">
      <div class="section-head"><h2>Việc trong ngày</h2><button class="soft" @click="selectTab('tasks')">Xem tất cả →</button></div>
      <div class="tasks">
       <div v-for="task in latest" :key="task.line" class="task">
        <div class="task-top"><strong>{{task.work_name}}</strong><span class="state" :class="{completed:task.status==='Completed',blocked:task.status==='Blocked'}">{{taskStatus(task.status)}}</span></div>
        <small>Thửa {{task.plot_code}} · {{task.work_team||'Chưa chọn tổ'}}</small>
        <div class="numbers">{{num(task.completed_qty)}} / {{num(task.planned_qty)}} {{task.uom}}</div>
       </div>
      </div>
     </template>
    </template>

    <template v-else-if="tab==='tasks'">
     <div class="section-head"><h2>Việc ngày {{date}}</h2><button class="soft" type="button" @click="reload" :disabled="refreshing">↻</button></div>
     <div v-if="!canSeeTasks" class="notice">Vai trò hiện tại không có danh sách giao việc ở nông trường.</div>
     <template v-else>
      <p class="muted">Chỉ hiển thị những công việc tài khoản được quyền xem. Tổ trưởng xem việc của tổ được gán, kỹ thuật xem việc giao đích danh.</p>
      <div v-if="!tasks.length" class="empty">{{refreshing?'Đang cập nhật…':'Chưa có công việc nào được giao trong ngày này.'}}</div>
      <div v-else class="tasks">
       <article v-for="task in tasks" :key="task.line" class="task">
        <div class="task-top"><strong>{{task.work_name}}</strong><span class="state" :class="{completed:task.status==='Completed',blocked:task.status==='Blocked'}">{{taskStatus(task.status)}}</span></div>
        <small>Thửa {{task.plot_code}} · Tổ {{task.work_team||'Chưa phân tổ'}}</small>
        <div class="numbers">Hoàn thành {{num(task.completed_qty)}} / {{num(task.planned_qty)}} {{task.uom}}</div>
        <small v-if="task.responsible">Phụ trách: {{task.responsible}}</small>
       </article>
      </div>
      <div class="notice">Màn hình này theo dõi việc đã giao. Ghi nhận sản lượng thực tế vẫn theo quy trình nghiệm thu hiện có, không tự coi khối lượng giao là khối lượng hoàn thành.</div>
     </template>
    </template>

    <template v-else-if="tab==='entry'">
     <div v-if="has(profile,'assign')" class="panel">
      <div class="section-head"><h2>Giao công việc mới</h2></div>
      <p class="muted">Chọn một tổ, một hoặc nhiều công việc và các lô/thửa cần làm. Có màn hình xem trước.</p>
      <a class="link" :href="pathWithFarm('/lotus/giao-viec',farm)">Mở giao việc nhanh →</a>
     </div>
     <div v-if="canObserve" class="panel">
      <h2 style="font-size:18px;margin:0 0 7px">Ghi nhận sâu bệnh</h2>
      <p class="muted">Chọn đúng thửa và vụ chuối. Phiếu được lưu trực tiếp trong Lotus.</p>
      <form class="form" @submit.prevent="submitObservation">
       <label>Thửa
        <select v-model="report.farm_plot" @change="changePlot" required>
         <option value="">Chọn thửa</option>
         <option v-for="p in catalog?.plots||[]" :key="p.name" :value="p.name">{{p.plot_code||p.name}}</option>
        </select>
       </label>
       <label>Vụ chuối
        <select v-model="report.crop_cycle" @change="changeCycle" required>
         <option value="">Chọn vụ</option>
         <option v-for="c in crops" :key="c.name" :value="c.name">{{c.name}}</option>
        </select>
       </label>
       <label v-if="crop?.cycle_type==='Ratoon'">Đợt chồi
        <select v-model="report.sucker_selection_batch" required>
         <option value="">Chọn đợt chồi</option>
         <option v-for="c in cohorts" :key="c.name" :value="c.name">{{c.name}}</option>
        </select>
       </label>
       <label>Loại bệnh
        <select v-model="report.disease" required>
         <option value="">Chọn loại bệnh</option>
         <option v-for="d in catalog?.diseases||[]" :key="d.name" :value="d.name">{{d.disease_name||d.name}}</option>
        </select>
       </label>
       <label>Số cây bị ảnh hưởng<input v-model="report.affected_plants" type="number" min="1" max="1000000" step="1" inputmode="numeric" required/></label>
       <label>Mức độ
        <select v-model="report.severity"><option value="Low">Nhẹ</option><option value="Medium">Trung bình</option><option value="High">Nặng</option></select>
       </label>
       <label>Tình trạng / cách xử lý<textarea v-model="report.action_taken" maxlength="1000" required placeholder="Ví dụ: Vàng lá tại góc thửa, đã đánh dấu để kiểm tra lại"/></label>
       <button class="primary" type="submit" :disabled="saving||refreshing||!catalog">{{saving?'Đang gửi…':'Gửi ghi nhận'}}</button>
      </form>
     </div>
     <div v-if="!canObserve&&!has(profile,'assign')" class="notice">Chưa có phiếu nhập nhanh cho vai trò này. Các chức năng đã được cấp có tại trang Hôm nay.</div>
    </template>

    <template v-else-if="tab==='account'">
     <div class="panel">
      <h2 style="font-size:18px;margin-top:0">Tài khoản</h2>
      <p class="muted">{{profile.user}}</p>
      <strong style="font-size:13px">Vai trò đang có</strong>
      <div class="roles" style="margin-top:12px"><span v-for="role in profile.roles" :key="role.name" class="role">{{role.label}}</span><span v-if="!profile.roles.length" class="role">Quản trị viên</span></div>
     </div>
     <div class="panel">
      <strong style="font-size:13px">Nông trường được truy cập</strong>
      <p v-for="f in profile.farms" :key="f.name" class="muted">{{f.farm_name||f.name}}</p>
      <p class="muted">Quyền được kiểm tra lại trên máy chủ khi mở dữ liệu hoặc gửi phiếu. Thay đổi quyền cần quản trị viên thực hiện trong Frappe.</p>
      <a class="link" href="/lotus/today">Mở giao diện quản lý đầy đủ →</a>
     </div>
    </template>
   </template>
  </template>
 </div>
 <nav v-if="profile" class="tabs" aria-label="Điều hướng ứng dụng">
  <button v-for="item in tabItems" :key="item.key" type="button" :class="{active:tab===item.key}" @click="selectTab(item.key)">
   <span class="tabicon" aria-hidden="true">{{item.icon}}</span>{{item.label}}
  </button>
 </nav>
</template>
