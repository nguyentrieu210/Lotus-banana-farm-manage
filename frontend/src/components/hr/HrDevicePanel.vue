<script setup>
// Nhân sự › Máy chấm công: each clock's connection status, how to point an ADMS clock at Lotus, editing a
// clock, and mapping the IDs a clock uses to employees (lotus_farm.device_admin). Punch logs stay below.
import {computed,reactive,ref,watch} from 'vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import LotusIcon from '../LotusIcon.vue'
import {Button as UiButton} from '../ui/button'
import {Input as UiInput} from '../ui/input'
import UiSelect from '../ui/select/Select.vue'
import {call} from '../../api'

const props=defineProps({company:String,farms:{type:Array,default:()=>[]}})
const emit=defineEmits(['changed','notice','error'])
const data=ref(null),busy=ref(false),saving=ref(false),formOpen=ref(false),guideFor=ref(null),search=ref(''),loadError=ref('')
const form=reactive({}),choice=reactive({})
const MODES=[['ADMS','ADMS – máy tự gửi lên Lotus (khuyên dùng)'],['File CSV','Nhập file CSV từ máy'],['LAN SDK','LAN SDK (chưa hỗ trợ)'],['Vendor Cloud','Dịch vụ hãng (chưa hỗ trợ)']]
const modeLabel=m=>(MODES.find(x=>x[0]===m)||[m,m])[1].split(' – ')[0].split(' (')[0]
const ago=v=>{if(!v)return 'chưa từng';const m=Math.round((Date.now()-new Date(String(v).replace(' ','T')+'+07:00'))/60000);return m<1?'vừa xong':m<60?m+' phút trước':m<1440?Math.round(m/60)+' giờ trước':Math.round(m/1440)+' ngày trước'}
const employeeName=n=>(data.value?.employees||[]).find(e=>e.name===n)?.employee_name||n
const unmapped=computed(()=>(data.value?.unmapped||[]).filter(u=>!search.value||(u.device_user_id+' '+u.name_on_device).toLowerCase().includes(search.value.toLowerCase())))
async function load(){
 if(!props.company){data.value=null;loadError.value='Chưa chọn công ty để xem máy chấm công.';return}
 busy.value=true;loadError.value=''
 try{
  const result=await call('lotus_farm.device_admin.overview',{company:props.company})
  if(!result||typeof result!=='object')throw new Error('Máy chủ chưa trả về danh sách máy chấm công.')
  data.value={...result,machines:result.machines||[],unmapped:result.unmapped||[],employees:result.employees||[]}
  for(const u of data.value.unmapped)choice[u.device+'|'+u.device_user_id]=u.suggested||''
 }catch(e){loadError.value=e.message||'Không lấy được dữ liệu máy chấm công.';emit('error',loadError.value)}finally{busy.value=false}
}
function openForm(m=null){Object.assign(form,{name:null,modified:null,farm:props.farms[0]?.name||'',device_code:'',device_name:'',model:'',serial_number:'',connection_mode:'ADMS',timezone:'Asia/Ho_Chi_Minh',active:1,notes:''},m||{});formOpen.value=true}
async function saveForm(){saving.value=true
 try{const {name,modified,...values}=form;const r=await call('lotus_farm.hr_operations.save_device',{company:props.company,values,name,modified},true);formOpen.value=false
  emit('notice',(name?'Đã lưu máy ':'Đã khai báo máy ')+form.device_code+'.');await load();emit('changed');if(form.connection_mode==='ADMS'&&!name)guideFor.value=data.value.machines.find(m=>m.name===r.name)||null}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
async function map(u){const employee=choice[u.device+'|'+u.device_user_id];if(!employee)return;saving.value=true
 try{const r=await call('lotus_farm.device_admin.map_device_user',{company:props.company,device:u.device,device_user_id:u.device_user_id,employee},true)
  emit('notice','Đã gắn mã '+u.device_user_id+' cho '+employeeName(employee)+(r.remapped?'; '+r.remapped+' lượt chấm trước đó đã được tính.':'.'));await load();emit('changed')}
 catch(e){emit('error',e.message)}finally{saving.value=false}}
watch(()=>props.company,load,{immediate:true})
defineExpose({load})
</script>

<template>
<section class="hr-ops-panel hr-devices" aria-label="Máy chấm công">
 <header class="hr-devices__head"><h3>Máy chấm công</h3><UiButton variant="outline" :disabled="busy" @click="load">Làm mới danh sách</UiButton><UiButton v-if="data?.can_manage" variant="outline" :disabled="busy" @click="openForm()"><LotusIcon name="plus"/>Khai báo máy</UiButton></header>
 <p v-if="busy" class="tk-hint" role="status">Đang lấy danh sách máy chấm công…</p>
 <p v-if="loadError" class="hr-ops-error" role="alert">{{loadError}} <UiButton variant="outline" size="sm" @click="load">Thử lại</UiButton></p>
 <div v-if="data?.machines?.length" class="hr-devices__grid">
  <article v-for="m in data.machines" :key="m.name" class="hr-device" :class="{'is-online':m.online,'is-off':!m.active}">
   <header><span class="hr-device__dot" aria-hidden="true"></span><b>{{m.device_name}}</b><small>{{m.device_code}}</small></header>
   <p class="hr-device__state">{{!m.active?'Đã tắt':m.connection_mode==='LAN SDK'?'LAN SDK (chưa xác nhận tự động)':m.connection_mode==='Vendor Cloud'?'Cloud (chưa xác nhận tự động)':m.connection_mode==='File CSV'?'Nhập từ file CSV':m.online?'Đang kết nối':'Chưa nhận kết nối ADMS'}}<small v-if="m.connection_mode==='ADMS'"> · liên lạc {{ago(m.last_seen_at)}}</small></p>
   <dl><div><dt>Hôm nay</dt><dd>{{m.punches_today}} lượt chấm</dd></div><div><dt>Mã đã gắn</dt><dd>{{m.mapped}} người</dd></div><div><dt>Lượt chấm cuối</dt><dd>{{ago(m.last_event_at)}}</dd></div><div><dt>Kết nối · SN</dt><dd>{{modeLabel(m.connection_mode)}}<template v-if="m.serial_number"> · {{m.serial_number}}</template></dd></div></dl>
   <footer><UiButton v-if="m.connection_mode==='ADMS'" variant="outline" size="sm" @click="guideFor=m">Cách cài trên máy</UiButton><UiButton v-if="data.can_manage" variant="ghost" size="sm" :aria-label="'Sửa máy '+m.device_code" @click="openForm(m)"><LotusIcon name="edit"/>Sửa</UiButton></footer>
  </article>
 </div>
 <p v-else-if="!busy&&!loadError" class="tk-empty">Chưa khai báo máy chấm công. Bấm Khai báo máy, chọn ADMS và nhập số serial (SN) in trên máy.</p>

 <section v-if="data" class="hr-devices__map" aria-label="Gắn mã máy với nhân viên">
  <header class="hr-devices__head"><h4>Mã trên máy chưa gắn nhân viên <span class="hr-pay__count">{{data.unmapped.length}}</span></h4><UiInput v-model="search" type="search" placeholder="Tìm mã hoặc tên trên máy…" aria-label="Tìm mã trên máy"/></header>
  <p class="tk-hint">Máy gửi danh sách người đã đăng ký vân tay/khuôn mặt cùng tên trên máy. Lotus gợi ý nhân viên trùng tên; kiểm tra rồi bấm Gắn. Các lượt chấm trước đó của mã này được tính lại ngay.</p>
  <div v-if="unmapped.length" class="hr-ops-scroll"><table><thead><tr><th>Máy</th><th>Mã trên máy</th><th>Tên trên máy</th><th>Lượt chờ</th><th>Nhân viên</th><th></th></tr></thead>
   <tbody><tr v-for="u in unmapped" :key="u.device+u.device_user_id"><td>{{data.machines.find(m=>m.name===u.device)?.device_code||u.device}}</td><td><b>{{u.device_user_id}}</b></td><td>{{u.name_on_device||'—'}}</td><td>{{u.punches||0}}</td>
    <td><UiSelect v-model="choice[u.device+'|'+u.device_user_id]" :aria-label="'Nhân viên cho mã '+u.device_user_id" :disabled="!data.can_manage||saving"><option value="">Chọn nhân viên…</option><option v-for="e in data.employees" :key="e.name" :value="e.name">{{e.employee_name}} · {{e.name}}{{e.name===u.suggested?' (gợi ý)':''}}</option></UiSelect></td>
    <td><UiButton v-if="data.can_manage" size="sm" :disabled="saving||!choice[u.device+'|'+u.device_user_id]" @click="map(u)">Gắn</UiButton></td></tr></tbody></table></div>
  <p v-else class="tk-empty">Mọi mã trên máy đã gắn nhân viên.</p>
 </section>

 <WorkspaceModal v-model="formOpen" :title="form.name?'Sửa máy '+form.device_code:'Khai báo máy chấm công'" :busy="saving" width="640px">
  <form class="hr-ops-form" @submit.prevent="saveForm">
   <label>Vườn<UiSelect v-model="form.farm" required><option value="">Chọn vườn</option><option v-for="f in farms" :key="f.name" :value="f.name">{{f.farm_name||f.name}}</option></UiSelect></label>
   <label>Mã máy<UiInput v-model="form.device_code" required placeholder="VD: CONG-A"/></label>
   <label>Tên máy<UiInput v-model="form.device_name" required placeholder="VD: Cổng đội khu A"/></label>
   <label>Cách kết nối<UiSelect v-model="form.connection_mode"><option v-for="[v,l] in MODES" :key="v" :value="v">{{l}}</option></UiSelect></label>
   <label>Số serial (SN)<UiInput v-model="form.serial_number" :required="form.connection_mode==='ADMS'" placeholder="Menu › Thông tin hệ thống › Serial"/></label>
   <label>Dòng máy / hãng<UiInput v-model="form.model" placeholder="VD: ZKTeco MB360, Ronald Jack X628"/></label>
   <label class="tk-check"><input v-model="form.active" type="checkbox" :true-value="1" :false-value="0">Đang sử dụng</label>
   <div class="hr-ops-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="formOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving">{{saving?'Đang lưu…':'Lưu máy'}}</UiButton></div>
  </form>
 </WorkspaceModal>

 <WorkspaceModal :model-value="!!guideFor" :title="'Cài máy '+(guideFor?.device_code||'')+' gửi dữ liệu lên Lotus'" width="640px" @update:model-value="guideFor=null">
  <ol v-if="guideFor&&data" class="hr-devices__guide">
   <li>Trên máy: <b>Menu › Kết nối (Comm.) › Cloud Server / ADMS</b>.</li>
   <li>Bật <b>ADMS / Kết nối máy chủ</b>, tắt "Tên miền" nếu máy yêu cầu IP thì dùng tên miền dưới đây.</li>
   <li>Địa chỉ máy chủ: <code>{{data.adms.server}}</code> · Cổng: <code>{{data.adms.port}}</code>{{data.adms.https?' · bật HTTPS/SSL nếu máy có tùy chọn':''}}.</li>
   <li>Kiểm tra số serial trên máy đúng: <code>{{guideFor.serial_number}}</code>.</li>
   <li>Khởi động lại máy. Trong 1–2 phút thẻ máy chuyển sang <b>Đang kết nối</b>; lượt chấm mới về Lotus ngay, danh sách mã trên máy hiện ở bảng "chưa gắn nhân viên".</li>
  </ol>
  <p class="tk-hint">Lotus chỉ nhận lượt chấm và tên người trên máy, không nhận mẫu vân tay hay khuôn mặt. Máy chưa khai báo SN bị từ chối.</p>
 </WorkspaceModal>
</section>
</template>
