<script setup>
import WorkspaceBar from './components/WorkspaceBar.vue'
import {sidebarCollapsed} from './workspace'
import UiSelect from './components/ui/select/Select.vue'
import {computed,onMounted,ref} from 'vue'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import {Badge as UiBadge} from './components/ui/badge'
import {consoleAPI,call,setCSRF} from './api'
import {cleanItems,placeOptions} from './assign-model'

const session=ref(null),catalog=ref(null),farm=ref(''),team=ref(''),date=ref(''),items=ref([{location:'',work_type:'',qty:''}])
const busy=ref(false),submitting=ref(false),message=ref(''),error=ref(''),preview=ref(null),created=ref(null)
const places=computed(()=>placeOptions(catalog.value||{}))
const works=computed(()=>catalog.value?.works||[])
const activeFarm=computed(()=>session.value?.farms?.find(f=>f.name===farm.value))
const previewTotal=computed(()=>preview.value?.lines?.length||0)
function invalidate(){preview.value=null;created.value=null;error.value='';message.value=''}
function add(){items.value.push({location:'',work_type:'',qty:''});invalidate()}
function remove(i){items.value.splice(i,1);invalidate()}
function workLabel(name){return works.value.find(w=>w.name===name)?.work_name||name}
function unit(name){return works.value.find(w=>w.name===name)?.uom||''}
function number(v){return Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:3})}
async function loadCatalog(){
 invalidate();catalog.value=null;team.value='';if(!farm.value)return
 busy.value=true
 try{catalog.value=await call('lotus_farm.mobile_assignment.options',{farm:farm.value});team.value=catalog.value.teams[0]?.name||''}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
async function boot(){
 busy.value=true
 try{
  session.value=await consoleAPI('bootstrap')
  setCSRF(session.value.csrf_token)
  if(!session.value.commands?.work)throw new Error('Tài khoản cần quyền quản lý nông trường để giao việc.')
  date.value=session.value.today
  const saved=new URLSearchParams(location.search).get('farm')
  farm.value=session.value.farms.some(f=>f.name===saved)?saved:(session.value.farms[0]?.name||'')
  if(farm.value)await loadCatalog()
 }catch(e){error.value=e.message}
 finally{busy.value=false}
}
async function showPreview(){
 error.value='';message.value='';created.value=null
 if(!farm.value||!team.value||!date.value){error.value='Chọn nông trường, tổ và ngày trước.';return}
 let clean
 try{clean=cleanItems(items.value)}catch(e){error.value=e.message;return}
 busy.value=true
 try{preview.value=await call('lotus_farm.mobile_assignment.preview',{farm:farm.value,work_team:team.value,items:clean},true)}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
async function submit(){
 if(!preview.value||submitting.value)return
 submitting.value=true;error.value=''
 try{
  created.value=await call('lotus_farm.mobile_assignment.create',{
   farm:farm.value,posting_date:date.value,work_team:team.value,items:cleanItems(items.value)},true)
  message.value='Đã giao '+created.value.count+' dòng công việc. Mã kế hoạch: '+created.value.plan
  preview.value=null
 }catch(e){error.value=e.message}
 finally{submitting.value=false}
}
function reset(){items.value=[{location:'',work_type:'',qty:''}];invalidate()}
onMounted(boot)
const workspaceActions=computed(()=>[{id:'home',label:'Trang chủ Lotus',navigation:true,href:'/lotus/mobile'},...(session.value?.capabilities?.stock?[{id:'stock',label:'Quản lý kho',navigation:true,href:'/lotus/kho'}]:[]),{id:'new-job',label:'Thêm công việc',run:add}])
</script>
<template>
 <div class="assignment-workspace"><WorkspaceBar :user="session?.user" title="Giao việc nhanh" :actions="workspaceActions" :sidebar="false" /><main class="shell">

  <div v-if="busy&&!session" class="spinner">Đang mở dữ liệu nông trường…</div>
  <template v-else>
   <div v-if="error" class="error" role="alert">{{error}}</div>
   <div v-if="message" class="success" role="status">{{message}}</div>
   <section class="panel fields">
    <label>Nông trường
     <UiSelect v-model="farm" @change="loadCatalog"><option value="">Chọn nông trường</option><option v-for="f in session?.farms||[]" :key="f.name" :value="f.name">{{f.farm_name||f.name}}</option></UiSelect>
    </label>
    <div class="fields" style="grid-template-columns:1fr 1.25fr">
     <label>Ngày <UiInput type="date" v-model="date" @change="invalidate"/></label>
     <label>Giao cho tổ
      <UiSelect v-model="team" @change="invalidate"><option value="">Chọn tổ</option><option v-for="t in catalog?.teams||[]" :key="t.name" :value="t.name">{{t.team_name}}</option></UiSelect>
     </label>
    </div>
    <div v-if="!catalog&&farm" class="hint">Đang lấy các lô, thửa và tổ của nông trường…</div>
    <div v-if="catalog&&(!catalog.plots.length||!catalog.teams.length||!catalog.works.length)" class="error">Nông trường chưa có đủ lô/thửa, tổ hoặc loại công việc. Cần nạp dữ liệu mẫu hoặc danh mục thật.</div>
   </section>
   <section v-for="(item,i) in items" :key="i" class="panel fields">
    <div class="job-head"><strong>Việc {{i+1}}</strong><UiButton v-if="items.length>1" type="button" class="remove" @click="remove(i)" :aria-label="'Xóa việc '+(i+1)">Xóa</UiButton></div>
    <label>Vị trí thực hiện
     <UiSelect v-model="item.location" @change="invalidate"><option value="">Chọn một lô hoặc thửa</option>
      <optgroup label="Theo lô — tự chia xuống các thửa">
       <option v-for="p in places.filter(p=>p.value.startsWith('block:'))" :key="p.value" :value="p.value">{{p.label}}</option>
      </optgroup>
      <optgroup label="Theo thửa — chỉ giao đúng thửa đó">
       <option v-for="p in places.filter(p=>p.value.startsWith('plot:'))" :key="p.value" :value="p.value">{{p.label}} · {{p.subtitle}}</option>
      </optgroup>
     </UiSelect>
    </label>
    <p v-if="item.location?.startsWith('block:')" class="hint">Lô này gồm nhiều thửa. Số lượng sẽ được chia theo diện tích, có bảng xem trước.</p>
    <label>Công việc
     <UiSelect v-model="item.work_type" @change="invalidate"><option value="">Chọn công việc</option><option v-for="w in works" :key="w.name" :value="w.name">{{w.work_name}}</option></UiSelect>
    </label>
    <label>Số lượng giao <span class="muted">{{unit(item.work_type)}}</span>
     <UiInput v-model="item.qty" @input="invalidate" inputmode="decimal" type="number" min="0" step="any" placeholder="Ví dụ: 800"/>
    </label>
   </section>
   <UiButton class="add" @click="add">＋ Thêm công việc / lô khác</UiButton>
   <section v-if="preview" class="panel">
    <div class="panel-title"><span>Xem trước {{previewTotal}} dòng giao</span><UiBadge variant="secondary" class="pill">Chưa giao</UiBadge></div>
    <p class="note">{{preview.note}}</p>
    <div v-for="(line,i) in preview.lines" :key="i" class="preview-row">
     <span><strong>{{line.work_name}}</strong><br/><span class="muted">Thửa {{line.plot_code}}</span></span>
     <span>{{number(line.planned_qty)}} {{line.uom}}</span>
    </div>
   </section>
   <div v-if="created" class="panel"><div class="panel-title">Giao việc thành công ✓</div><p class="hint">Đã lưu {{created.count}} dòng vào kế hoạch ngày. Muốn giao thêm thì bấm “Giao việc mới”.</p><UiButton class="add" @click="reset">Giao việc mới</UiButton></div>
  </template>
 </main></div>
 <footer v-if="session&&!created" class="bar"><div class="bar-inner">
  <UiButton variant="secondary" class="secondary" type="button" @click="reset">Làm lại</UiButton>
  <UiButton v-if="!preview" class="primary" type="button" :disabled="busy||!catalog" @click="showPreview">{{busy?'Đang kiểm tra…':'Xem trước giao việc'}}</UiButton>
  <UiButton v-else class="primary" type="button" :disabled="submitting" @click="submit">{{submitting?'Đang giao…':'Xác nhận giao việc'}}</UiButton>
 </div></footer>
</template>
