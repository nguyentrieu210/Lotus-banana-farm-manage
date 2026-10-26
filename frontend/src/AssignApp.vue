<script setup>
import {MoneyInput} from './components/ui/input'
import LotusField from './components/form/LotusField.vue'
import {FormField} from './components/ui/form-field'
import {unitLabel} from './units'
import WorkspaceBar from './components/WorkspaceBar.vue'
import {sidebarCollapsed} from './workspace'
import SearchSelect from './components/SearchSelect.vue'
import {computed,onMounted,ref,watch,provide} from 'vue'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import {Badge as UiBadge} from './components/ui/badge'
import {consoleAPI,call,setCSRF} from './api'
import {cleanItems,placeOptions,assignmentCatalogueReady} from './assign-model'

const props=defineProps({embedded:Boolean,initialFarm:{type:String,default:''},initialDate:{type:String,default:''},initialSession:{type:Object,default:null},portalTarget:{type:Object,default:null}})
const emit=defineEmits(['busy-change','created'])
provide('searchSelectTarget',computed(()=>props.portalTarget||'body'))
const session=ref(null),catalog=ref(null),farm=ref(''),team=ref(''),date=ref(''),items=ref([{location:'',work_type:'',qty:''}])
const busy=ref(false),submitting=ref(false),message=ref(''),error=ref(''),preview=ref(null),created=ref(null),approvalReason=ref('')
watch([busy,submitting],()=>emit('busy-change',busy.value||submitting.value),{immediate:true})
const places=computed(()=>placeOptions(catalog.value||{}))
const works=computed(()=>catalog.value?.works||[])
const farmOptions=computed(()=>(session.value?.farms||[]).map(f=>({value:f.name,label:f.farm_name||f.name})))
const teamOptions=computed(()=>(catalog.value?.teams||[]).map(t=>({value:t.name,label:t.team_name})))
const workOptions=computed(()=>works.value.map(w=>({value:w.name,label:w.work_name})))
function modes(name){const w=works.value.find(x=>x.name===name);if(!w)return [];return [...(Number(w.allow_daywork)?[{value:'Daywork',label:'Công nhật'}]:[]),...(Number(w.allow_piecework)?[{value:'Piece',label:'Công khoán'}]:[]),...(Number(w.allow_daywork)&&Number(w.allow_piecework)?[{value:'Both',label:'Cả công nhật và khoán (theo dõi riêng)'}]:[])]}
const locationOptions=computed(()=>places.value.filter(p=>p.value.startsWith('block:')).map(p=>({...p,subtitle:'Giao việc trực tiếp cho lô'})))
const activeFarm=computed(()=>session.value?.farms?.find(f=>f.name===farm.value))
const previewTotal=computed(()=>preview.value?.lines?.length||0)
const previewWorkdays=computed(()=>preview.value?.lines?.reduce((total,line)=>total+Number(line.required_workdays||0),0)||0)
const previewPiecework=computed(()=>preview.value?.lines?.reduce((total,line)=>total+Number(line.estimated_piecework_amount||0),0)||0)
function listedRate(item){return Number(works.value.find(w=>w.name===item.work_type)?.piecework_rate||0)}
function canSetRate(item){const w=works.value.find(x=>x.name===item.work_type);return !!w&&Number(w.allow_piecework)&&item.payment_mode!=='Daywork'}
function invalidate(){preview.value=null;created.value=null;error.value='';message.value=''}
function add(){items.value.push({location:'',work_type:'',qty:'',payment_mode:''});invalidate()}
function remove(i){items.value.splice(i,1);invalidate()}
function workLabel(name){return works.value.find(w=>w.name===name)?.work_name||name}
function unit(name){return unitLabel(works.value.find(w=>w.name===name)?.uom)}
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
  session.value=props.initialSession||await consoleAPI('bootstrap')
  setCSRF(session.value.csrf_token)
  if(!session.value.commands?.work)throw new Error('Tài khoản cần quyền quản lý vườn để giao việc.')
  date.value=props.initialDate||session.value.today
  const saved=props.initialFarm||new URLSearchParams(location.search).get('farm')
  farm.value=session.value.farms.some(f=>f.name===saved)?saved:(session.value.farms[0]?.name||'')
  if(farm.value)await loadCatalog()
 }catch(e){error.value=e.message}
 finally{busy.value=false}
}
async function showPreview(){
 error.value='';message.value='';created.value=null
 if(!farm.value||!team.value||!date.value){error.value='Chọn vườn, tổ và ngày trước.';return}
 let clean
 try{clean=cleanItems(items.value)}catch(e){error.value=e.message;return}
 busy.value=true
 try{preview.value=await call('lotus_farm.mobile_assignment.preview',{farm:farm.value,work_team:team.value,items:clean,posting_date:date.value},true)}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
async function submit(){
 if(!preview.value||submitting.value)return
 submitting.value=true;error.value=''
 try{
  created.value=await call('lotus_farm.mobile_assignment.create',{
   farm:farm.value,posting_date:date.value,work_team:team.value,items:cleanItems(items.value),rate_request_reason:approvalReason.value},true)
  message.value=(created.value.status==='Pending'?'Đã gửi chờ duyệt giá khoán: ':'Đã giao việc: ')+created.value.count+' dòng công việc. Mã kế hoạch: '+created.value.plan
  preview.value=null
  emit('created',{...created.value,farm:farm.value,posting_date:date.value})
 }catch(e){error.value=e.message}
 finally{submitting.value=false}
}
function reset(){items.value=[{location:'',work_type:'',qty:'',payment_mode:''}];invalidate()}
onMounted(boot)
const workspaceActions=computed(()=>[{id:'home',label:'Trang chủ Lotus',navigation:true,href:'/lotus/mobile'},{id:'farm-work',label:'Công việc vườn',navigation:true,href:'/lotus/cong-viec'+(farm.value?'?farm='+encodeURIComponent(farm.value):'')},...(session.value?.capabilities?.stock?[{id:'stock',label:'Quản lý kho',navigation:true,href:'/lotus/kho'}]:[]),{id:'new-job',label:'Thêm công việc',run:add}])
</script>
<template>
 <div class="assignment-workspace lotus-ui"><WorkspaceBar v-if="!embedded" :user="session?.user" title="Giao việc nhanh" :actions="workspaceActions" :sidebar="false" /><main class="shell">

  <div v-if="busy&&!session" class="spinner">Đang mở dữ liệu vườn…</div>
  <template v-else>
   <div v-if="error" class="error" role="alert">{{error}}</div>
   <div v-if="message" class="success" role="status">{{message}}</div>
   <section class="panel fields">
    <label>Vườn
     <SearchSelect v-model="farm" :options="farmOptions" label="Vườn" placeholder="Chọn vườn" :disabled="busy||submitting||embedded" @change="loadCatalog"/>
    </label>
    <div class="fields" style="grid-template-columns:1fr 1.25fr">
     <FormField label="Ngày" v-slot="f"><UiInput v-bind="f" type="date" :disabled="busy||submitting" v-model="date" @change="invalidate"/></FormField>
     <label>Giao cho tổ
      <SearchSelect v-model="team" :options="teamOptions" label="Giao cho tổ" placeholder="Chọn tổ" :disabled="busy||submitting" @change="invalidate"/>
     </label>
    </div>
    <div v-if="!catalog&&farm" class="hint">Đang lấy danh sách lô, tổ và công việc…</div>
    <div v-if="catalog&&(!assignmentCatalogueReady(catalog))" class="error" role="alert">Vườn chưa có đủ lô, tổ hoặc công việc đang hoạt động. Kiểm tra danh mục trước khi giao việc.</div>
   </section>
   <section v-for="(item,i) in items" :key="i" class="panel fields">
    <div class="job-head"><strong>Việc {{i+1}}</strong><UiButton v-if="items.length>1" type="button" :disabled="busy||submitting" class="remove" @click="remove(i)" :aria-label="'Xóa việc '+(i+1)">Xóa</UiButton></div>
    <label>Vị trí thực hiện
     <SearchSelect v-model="item.location" :options="locationOptions" label="Lô thực hiện" placeholder="Chọn hoặc gõ tìm lô" :disabled="busy||submitting" @change="invalidate"/>
    </label>
    <p v-if="item.location?.startsWith('block:')" class="hint">Khối lượng giao được ghi trực tiếp cho lô đã chọn.</p>
    <label>Công việc
     <SearchSelect v-model="item.work_type" :options="workOptions" label="Công việc" placeholder="Chọn hoặc gõ tìm công việc" :disabled="busy||submitting" @change="invalidate"/>
    </label>
    <LotusField v-if="modes(item.work_type).length" v-model="item.payment_mode" label="Hình thức tính công" :options="modes(item.work_type)" :searchable="false" empty-option="Theo cấu hình công việc" :disabled="busy||submitting" @update:model-value="invalidate"/>
    <label v-if="canSetRate(item)">Đơn giá khoán đề xuất (đ/{{unit(item.work_type)}})
     <MoneyInput v-model="item.piecework_rate" :disabled="busy||submitting" :placeholder="number(listedRate(item))" @input="invalidate"/>
     <span class="hint">Giá niêm yết: {{number(listedRate(item))}} đ. Bỏ trống để lấy giá chuẩn; vượt giá sẽ cần duyệt.</span>
    </label>
    <label>Số lượng giao <span class="muted">{{unit(item.work_type)}}</span>
     <UiInput :disabled="busy||submitting" v-model="item.qty" @input="invalidate" inputmode="decimal" type="number" min="0" step="any" placeholder="Ví dụ: 800"/>
    </label>
   </section>
   <UiButton class="add" :disabled="busy||submitting" @click="add">＋ Thêm công việc / lô khác</UiButton>
   <section v-if="preview" class="panel">
    <div class="panel-title"><span>Xem trước {{previewTotal}} dòng giao</span><UiBadge variant="secondary" class="pill">Chưa giao</UiBadge></div>
    <p class="note">{{preview.note}}</p>
    <p v-if="preview.approval_required" role="status" class="hint"><strong>Giá khoán cao hơn niêm yết.</strong> Khi xác nhận, phiếu chỉ lưu chờ duyệt; chưa giao xuống tổ cho đến khi được duyệt.</p>
    <LotusField v-if="preview.approval_required" v-model="approvalReason" label="Lý do đề nghị tăng giá" type="textarea" maxlength="500" rows="2" placeholder="Ví dụ: lô khó làm, cần thêm nhân lực…" :disabled="submitting"/>
    <p class="hint"><strong>Tổng dự kiến:</strong> {{number(previewWorkdays)}} công lao động (khoảng {{Math.ceil(previewWorkdays)}} người nếu hoàn thành trong 1 ngày) · {{number(previewPiecework)}} đ tiền khoán (nếu có). Hai số này không phải hai khoản lương cộng lại.</p>
    <div v-if="preview.materials?.length" class="preview-materials"><strong>Vật tư cần theo định mức:</strong><div v-for="m in preview.materials" :key="m.item+'-'+m.uom" class="preview-row"><span>{{m.item}}</span><strong>{{number(m.required_qty)}} {{unitLabel(m.uom)}}</strong></div><p class="hint">Đây là lượng cần dùng, chưa trừ tồn kho và chưa tạo phiếu xuất/mua.</p></div>
    <p v-if="preview.missing_norms?.length" class="hint" role="status">Chưa có định mức vật tư đã duyệt cho: {{preview.missing_norms.join(', ')}}. Chưa thể kết luận các công việc này không cần vật tư.</p>
    <div v-for="(line,i) in preview.lines" :key="i" class="preview-row">
     <span><strong>{{line.work_name}}</strong><br/><span class="muted">Thửa {{line.plot_code}}</span></span>
     <span><small v-if="line.requires_approval"><strong>Chờ duyệt: {{number(line.requested_piecework_rate)}} đ / đơn vị (giá chuẩn {{number(line.list_piecework_rate)}} đ)</strong></small>{{number(line.planned_qty)}} {{unitLabel(line.uom)}}<small v-if="line.required_workdays"> · {{number(line.required_workdays)}} công dự kiến</small><small v-if="line.estimated_piecework_amount"> · {{number(line.estimated_piecework_amount)}} đ khoán dự kiến</small></span>
    </div>
   </section>
   <div v-if="created" class="panel"><div class="panel-title">{{created.status==='Pending'?'Đã gửi duyệt giá khoán':'Giao việc thành công'}}</div><p class="hint">{{created.status==='Pending'?'Phiếu chưa giao xuống tổ, chờ người có quyền duyệt giá.':'Phiếu đã giao xuống tổ.'}} Đã lưu {{created.count}} dòng. Muốn giao thêm thì bấm “Giao việc mới”.</p><UiButton class="add" @click="reset">Giao việc mới</UiButton></div>
  </template>
 </main></div>
 <footer v-if="session&&!created" class="bar"><div class="bar-inner">
  <UiButton variant="secondary" class="secondary" type="button" :disabled="busy||submitting" @click="reset">Làm lại</UiButton>
  <UiButton v-if="!preview" class="primary" type="button" :disabled="busy||!catalog" @click="showPreview">{{busy?'Đang kiểm tra…':'Xem trước giao việc'}}</UiButton>
  <UiButton v-else class="primary" type="button" :disabled="submitting||(preview.approval_required&&!approvalReason.trim())" @click="submit">{{submitting?'Đang lưu...':preview.approval_required?'Gửi duyệt giá khoán':'Xác nhận giao việc'}}</UiButton>
 </div></footer>
</template>
