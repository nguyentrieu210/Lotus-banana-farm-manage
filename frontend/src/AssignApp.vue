<script setup>
import {computed,onMounted,ref} from 'vue'
import {consoleAPI,call,setCSRF} from './api'
import {cleanItems,placeOptions} from './assign-model'

const session=ref(null),catalog=ref(null),farm=ref(''),team=ref(''),date=ref(''),items=ref([{location:'',work_type:'',qty:''}])
const pending=ref([])
const busy=ref(false),submitting=ref(false),message=ref(''),error=ref(''),preview=ref(null),created=ref(null)
const places=computed(()=>placeOptions(catalog.value||{}))
const works=computed(()=>catalog.value?.works||[])
const activeFarm=computed(()=>session.value?.farms?.find(f=>f.name===farm.value))
const previewTotal=computed(()=>preview.value?.lines?.length||0)
function workChanged(item){item.payment_basis=works.value.find(w=>w.name===item.work_type)?.payment_basis||'Daywork';item.agreed_unit_price='';loadPrice(item)}
async function loadPrice(item){
 invalidate();item.listed_unit_price=null;item.quoteError='';
 if(item.payment_basis!=='Piece'||!item.work_type)return
 const key=[farm.value,date.value,item.work_type].join('|');item.quoteKey=key
 try{const q=await call('lotus_farm.mobile_assignment.quote',{farm:farm.value,posting_date:date.value,work_type:item.work_type});if(item.quoteKey===key&&key===[farm.value,date.value,item.work_type].join('|'))item.listed_unit_price=q.listed_unit_price}catch(e){item.quoteError=e.message}
}
function dateChanged(){invalidate();items.value.forEach(item=>{item.agreed_unit_price='';loadPrice(item)})}
function invalidate(){preview.value=null;created.value=null;error.value='';message.value=''}
function add(){items.value.push({location:'',work_type:'',qty:''});invalidate()}
function remove(i){items.value.splice(i,1);invalidate()}
function workLabel(name){return works.value.find(w=>w.name===name)?.work_name||name}
function unit(name){return works.value.find(w=>w.name===name)?.uom||''}
function number(v){return Number(v||0).toLocaleString('vi-VN',{maximumFractionDigits:3})}
async function loadCatalog(){
 invalidate();catalog.value=null;team.value='';pending.value=[];items.value=[{location:'',work_type:'',qty:''}];if(!farm.value)return
 busy.value=true
 try{catalog.value=await call('lotus_farm.mobile_assignment.options',{farm:farm.value});team.value=catalog.value.teams[0]?.name||'';pending.value=await call('lotus_farm.mobile_assignment.pending_prices',{farm:farm.value})}
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
 try{preview.value=await call('lotus_farm.mobile_assignment.preview',{farm:farm.value,posting_date:date.value,work_team:team.value,items:clean},true)}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
async function submit(){
 if(!preview.value||submitting.value)return
 submitting.value=true;error.value=''
 try{
  created.value=await call('lotus_farm.mobile_assignment.create',{
   farm:farm.value,posting_date:date.value,work_team:team.value,items:cleanItems(items.value)},true)
  message.value=(created.value.status==='Pending'?'Đã lưu chờ quản lý khác duyệt giá. Chưa giao việc. Mã: ':'Đã giao '+created.value.count+' dòng công việc. Mã kế hoạch: ')+created.value.plan
  preview.value=null
 }catch(e){error.value=e.message}
 finally{submitting.value=false}
}
function reset(){items.value=[{location:'',work_type:'',qty:''}];invalidate()}
onMounted(boot)
</script>
<template>
 <main class="shell">
  <fieldset :disabled="busy||submitting" style="border:0;padding:0;margin:0;min-width:0">
  <div class="top"><div><p class="eyebrow">LOTUS FARM · NGOÀI VƯỜN</p><h1>Giao việc nhanh</h1><p class="hint">Chọn lô <strong>hoặc</strong> thửa · không nhập lại thông tin cấp trên</p></div><a href="/lotus/today">Quản lý ↗</a></div>
  <div v-if="busy&&!session" class="spinner">Đang mở dữ liệu nông trường…</div>
  <template v-else>
   <div v-if="error" class="error" role="alert">{{error}}</div>
   <div v-if="message" class="success" role="status">{{message}}</div>
   <section class="panel fields">
    <label>Nông trường
     <select v-model="farm" @change="loadCatalog"><option value="">Chọn nông trường</option><option v-for="f in session?.farms||[]" :key="f.name" :value="f.name">{{f.farm_name||f.name}}</option></select>
    </label>
    <div class="fields" style="grid-template-columns:1fr 1.25fr">
     <label>Ngày <input type="date" v-model="date" @change="dateChanged"/></label>
     <label>Giao cho tổ
      <select v-model="team" @change="invalidate"><option value="">Chọn tổ</option><option v-for="t in catalog?.teams||[]" :key="t.name" :value="t.name">{{t.team_name}}</option></select>
     </label>
    </div>
    <div v-if="!catalog&&farm" class="hint">Đang lấy các lô, thửa và tổ của nông trường…</div>
    <div v-if="catalog&&(!catalog.plots.length||!catalog.teams.length||!catalog.works.length)" class="error">Nông trường chưa có đủ lô/thửa, tổ hoặc loại công việc. Cần nạp dữ liệu mẫu hoặc danh mục thật.</div>
   </section>
   <section v-for="(item,i) in items" :key="i" class="panel fields">
    <div class="job-head"><strong>Việc {{i+1}}</strong><button v-if="items.length>1" type="button" class="remove" @click="remove(i)" :aria-label="'Xóa việc '+(i+1)">Xóa</button></div>
    <label>Vị trí thực hiện
     <select v-model="item.location" @change="invalidate"><option value="">Chọn một lô hoặc thửa</option>
      <optgroup label="Theo lô — tự chia xuống các thửa">
       <option v-for="p in places.filter(p=>p.value.startsWith('block:'))" :key="p.value" :value="p.value">{{p.label}}</option>
      </optgroup>
      <optgroup label="Theo thửa — chỉ giao đúng thửa đó">
       <option v-for="p in places.filter(p=>p.value.startsWith('plot:'))" :key="p.value" :value="p.value">{{p.label}} · {{p.subtitle}}</option>
      </optgroup>
     </select>
    </label>
    <p v-if="item.location?.startsWith('block:')" class="hint">Lô này gồm nhiều thửa. Số lượng sẽ được chia theo diện tích, có bảng xem trước.</p>
    <label>Công việc
     <select v-model="item.work_type" @change="workChanged(item)"><option value="">Chọn công việc</option><option v-for="w in works" :key="w.name" :value="w.name">{{w.work_name}}</option></select>
    </label>
    <label>Số lượng giao <span class="muted">{{unit(item.work_type)}}</span>
     <input v-model="item.qty" @input="invalidate" inputmode="decimal" type="number" min="0" step="any" placeholder="Ví dụ: 800"/>
    </label>
    <label>Cách trả công
     <select v-model="item.payment_basis" @change="item.agreed_unit_price='';loadPrice(item)"><option value="Daywork">Công nhật</option><option value="Piece">Khoán sản lượng</option></select>
    </label>
    <template v-if="item.payment_basis==='Piece'">
     <p v-if="item.quoteError" class="error">{{item.quoteError}}</p>
     <p class="hint">Giá niêm yết: {{item.listed_unit_price==null?'Chưa có':number(item.listed_unit_price)+'đ / '+unit(item.work_type)}}</p>
     <label>Đơn giá giao (đ / {{unit(item.work_type)}})<input type="number" min="0" step="any" inputmode="decimal" v-model="item.agreed_unit_price" :placeholder="String(item.listed_unit_price??'')" @input="invalidate"/></label>
     <p class="hint">Tiền dự tính: {{number(Number(item.qty||0)*Number(item.agreed_unit_price||item.listed_unit_price||0))}}đ · Chốt tiền theo số lượng nghiệm thu đạt.</p>
     <label>Tiêu chuẩn đạt<input v-model="item.acceptance_criteria" @input="invalidate" placeholder="Ghi yêu cầu để tổ làm và người nghiệm thu kiểm tra"/></label>
     <label v-if="Number(item.agreed_unit_price)>Number(item.listed_unit_price)">Lý do vượt giá<input v-model="item.price_reason" @input="invalidate" placeholder="Cần quản lý khác duyệt trước khi giao"/></label>
    </template>
    <p v-else class="hint">Trả theo số công được xác nhận. Sản lượng dùng theo dõi năng suất; không cộng thêm tiền khoán.</p>
   </section>
   <button class="add" @click="add">＋ Thêm công việc / lô khác</button>
   <section v-if="preview" class="panel">
    <div class="panel-title"><span>Xem trước {{previewTotal}} dòng giao</span><span class="pill">Chưa giao</span></div>
    <p class="note">{{preview.note}}</p>
    <p class="hint">Nhân công dự tính theo định mức: {{number(preview.required_workdays)}} công. Đây là lượng công cần, chưa phải chấm công thực tế.</p>
    <p v-for="m in preview.materials" :key="m.item+'|'+m.uom" class="hint">Cần {{number(m.qty)}} {{m.uom}} · {{m.item}}</p>
    <p v-if="preview.missing_norms?.length" class="hint">Chưa có định mức vật tư được duyệt: {{preview.missing_norms.join(', ')}}. Chưa tính được nhu cầu cho các việc này.</p>
    <div v-for="(line,i) in preview.lines" :key="i" class="preview-row">
     <span><strong>{{line.work_name}}</strong><br/><span class="muted">Thửa {{line.plot_code}}</span></span>
     <span>{{number(line.planned_qty)}} {{line.uom}}<br/>
      <small v-if="line.payment_basis==='Piece'">{{number(line.agreed_unit_price)}}đ/{{line.uom}} · {{number(line.estimated_amount)}}đ<br/>{{line.acceptance_criteria}}<br/>{{line.price_approval_state==='Pending'?'Chờ duyệt vượt giá':'Giá trong mức niêm yết'}}</small>
      <small v-else>Công nhật</small>
     </span>
    </div>
   </section>
   <div v-if="created" class="panel"><div class="panel-title">{{created.status==='Pending'?'Đã lưu chờ duyệt giá':'Giao việc thành công ✓'}}</div><p class="hint">{{created.status==='Pending'?'Kế hoạch chưa được giao. Quản lý khác mở kế hoạch để kiểm tra và duyệt.':'Đã lưu kế hoạch ngày.'}} Muốn giao thêm thì bấm “Giao việc mới”.</p><a :href="'/app/daily-work-plan/'+encodeURIComponent(created.plan)">Mở kế hoạch / duyệt giá ↗</a><button class="add" @click="reset">Giao việc mới</button></div>
   <section v-if="pending.length" class="panel"><strong>Kế hoạch chờ duyệt giá</strong><p v-for="p in pending" :key="p.name"><a :href="'/app/daily-work-plan/'+encodeURIComponent(p.name)">{{p.posting_date}} · {{p.name}}</a></p></section>
  </template>
  </fieldset>
 </main>
 <footer v-if="session&&!created" class="bar"><div class="bar-inner">
  <button class="secondary" type="button" @click="reset">Làm lại</button>
  <button v-if="!preview" class="primary" type="button" :disabled="busy||!catalog" @click="showPreview">{{busy?'Đang kiểm tra…':'Xem trước giao việc'}}</button>
  <button v-else class="primary" type="button" :disabled="submitting" @click="submit">{{submitting?'Đang giao…':'Xác nhận giao việc'}}</button>
 </div></footer>
</template>

