<script setup>
import {computed,onMounted,ref} from 'vue'
import {Icon} from 'vant'
import {call,setCSRF} from './api'
import LotusMobileShell from './components/LotusMobileShell.vue'
import LotusMobileInput from './components/LotusMobileInput.vue'
import LotusMobileButton from './components/LotusMobileButton.vue'
import MobileLinkField from './components/MobileLinkField.vue'
import LotusMobileFeedback from './components/LotusMobileFeedback.vue'
import {useMobileViewport} from './use-mobile-viewport'
import {logoutPwa} from './mobile-push-session'

const api=(name,args={},write=false)=>call('lotus_farm.field_proposal.'+name,args,write)
const {keyboard}=useMobileViewport()
const setup=ref(null),tab=ref('home'),screen=ref('home')
const rows=ref([]),reviewRows=ref([]),current=ref(null),form=ref(null)
const busy=ref(false),saving=ref(false),error=ref(''),notice=ref(''),reviewNote=ref('')
const filter=ref('')
let requestSerial=0
const phoneTabs=computed(()=>[
 {name:'home',label:'Trang chủ',icon:'wap-home-o'},
 {name:'history',label:'Phiếu của tôi',icon:'orders-o'},
 ...(setup.value?.reviewer?[{name:'review',label:'Chờ duyệt',icon:'passed'}]:[]),
 {name:'profile',label:'Tôi',icon:'user-o'}
])
const title=computed(()=>screen.value==='form'?'Lập đề xuất':screen.value==='detail'?'Chi tiết đề xuất':({home:'Đề xuất vật tư, chi phí',history:'Phiếu của tôi',review:'Chờ duyệt',profile:'Tài khoản'})[tab.value])
const selectedTab=computed(()=>screen.value==='detail'?'history':screen.value==='form'?'home':tab.value)
const farms=computed(()=>(setup.value?.farms||[]).map(f=>({value:f.name,label:f.farm_name||f.name})))
const blocks=computed(()=>(setup.value?.blocks||[]).filter(b=>b.farm===form.value?.farm).map(b=>({value:b.name,label:b.block_name||b.name})))
const items=computed(()=>(setup.value?.items||[]).map(i=>({value:i.name,label:i.item_name||i.name})))
const today=computed(()=>setup.value?.today||new Date().toISOString().slice(0,10))
const fmt=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:2})
const money=n=>fmt(n)+' đ'
const total=computed(()=>form.value?.lines.reduce((s,l)=>s+Number(l.qty||0)*Number(l.rate||0),0)||0)
const visibleRows=computed(()=>rows.value.filter(r=>[r.name,r.reason,r.farm,r.kind].join(' ').toLocaleLowerCase().includes(filter.value.toLocaleLowerCase())))
const blankLine=()=>({key:Math.random().toString(36).slice(2),item_code:'',description:'',qty:1,uom:'',rate:0})
function resetMessages(){error.value='';notice.value=''}
function go(next){screen.value=next;tab.value=next;resetMessages();window.scrollTo?.(0,0)}
function back(){if(screen.value==='form'||screen.value==='detail'){screen.value=tab.value;current.value=null;form.value=null;resetMessages()}else go('home')}
function start(kind){
 resetMessages();current.value=null
 form.value={kind, farm:setup.value?.farms?.[0]?.name||'',farm_block:'',needed_date:today.value,reason:'',lines:[blankLine()]}
 screen.value='form'
}
function chooseItem(line,code){
 const found=setup.value?.items.find(i=>i.name===code)
 line.item_code=code
 if(found){line.description=found.item_name;line.uom=found.stock_uom}
}
function addLine(){if(form.value.lines.length<30)form.value.lines.push(blankLine())}
function fromDetail(d){
 return {kind:d.kind,farm:d.farm,farm_block:d.farm_block||'',needed_date:d.needed_date,
         reason:d.reason,lines:d.lines.map(row=>({...row,key:Math.random().toString(36).slice(2)}))}
}
async function refresh(){
 if(!setup.value)return
 const token=++requestSerial
 busy.value=true
 try{
  const [mine,review]=await Promise.all([api('proposals',{view:'mine'}),setup.value.reviewer?api('proposals',{view:'review'}):Promise.resolve([])])
  if(token===requestSerial){rows.value=mine;reviewRows.value=review}
 }catch(e){if(token===requestSerial)error.value=e.message}
 finally{if(token===requestSerial)busy.value=false}
}
async function open(row){
 resetMessages();busy.value=true
 try{current.value=await api('detail',{name:row.name});reviewNote.value='';screen.value='detail'}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
function edit(){if(!current.value?.can_edit)return;form.value=fromDetail(current.value);screen.value='form';resetMessages()}
async function save(send=false){
 if(saving.value)return
 resetMessages()
 if(!form.value?.farm||!form.value.reason.trim()||form.value.lines.some(l=>!l.description.trim()||Number(l.qty)<=0)){
  error.value='Hãy chọn vườn, ghi lý do và nhập đủ từng dòng.';return
 }
 saving.value=true
 try{
  const d=await api('save',{values:{...form.value,lines:form.value.lines},
    name:current.value?.can_edit?current.value.name:null,
    modified:current.value?.can_edit?current.value.modified:null},true)
  current.value=send?await api('submit',{name:d.name,modified:d.modified},true):d
  screen.value='detail';notice.value=send?'Đã gửi quản lý xem xét.':'Đã lưu nháp.';form.value=null
  await refresh()
 }catch(e){error.value=e.message}
 finally{saving.value=false}
}
async function submitSaved(){
 if(saving.value||!current.value?.can_edit)return
 saving.value=true;resetMessages()
 try{current.value=await api('submit',{name:current.value.name,modified:current.value.modified},true)
     notice.value='Đã gửi đề xuất.';await refresh()}
 catch(e){error.value=e.message}finally{saving.value=false}
}
async function decide(decision){
 if(saving.value||!current.value?.can_review)return
 resetMessages();saving.value=true
 try{
  current.value=await api('review',{name:current.value.name,modified:current.value.modified,decision,note:reviewNote.value},true)
  notice.value='Đã cập nhật trạng thái phiếu.';await refresh()
 }catch(e){error.value=e.message}finally{saving.value=false}
}
onMounted(async()=>{
 busy.value=true
 try{
  setup.value=await api('bootstrap');setCSRF(setup.value.csrf_token);await refresh()
  const url=new URL(window.location.href)
  const name=url.searchParams.get('proposal')
  if(name){
   url.searchParams.delete('proposal')
   window.history.replaceState(window.history.state,'',url.pathname+url.search+url.hash)
   await open({name})
  }
 }
 catch(e){error.value=e.message}finally{busy.value=false}
})
</script>

<template>
 <div class="field-proposal">
  <LotusMobileShell :user="setup?.user||''" app="proposal" :tabs="phoneTabs"
    :active-tab="selectedTab" :title="title" :back="screen==='detail'||screen==='form'"
    :keyboard-open="keyboard" :disabled="saving" :notifications="true" :onboarding="false"
    :refresh="refresh" :refreshable="screen==='home'||screen==='history'||screen==='review'"
    @navigate="go" @back="back">
   <main class="field-proposal__body">
    <LotusMobileFeedback v-if="busy&&!setup" kind="loading">Đang mở ứng dụng…</LotusMobileFeedback>
    <LotusMobileFeedback v-if="error" kind="error">{{error}}</LotusMobileFeedback>
    <LotusMobileFeedback v-if="notice" kind="success">{{notice}}</LotusMobileFeedback>

    <template v-if="setup&&screen==='home'">
     <div class="field-proposal__intro"><strong>Hôm nay cần gì cho vườn?</strong><p>Gửi đề xuất trước khi mua hàng, nhận vật tư hoặc phát sinh chi phí.</p></div>
     <button class="field-proposal__choice" type="button" @click="start('Vật tư')">
      <Icon name="bag-o" size="28"/><span><strong>Đề xuất vật tư</strong><small>Phân, thuốc, túi bao, dụng cụ…</small></span><Icon name="arrow"/>
     </button>
     <button class="field-proposal__choice" type="button" @click="start('Chi phí')">
      <Icon name="balance-o" size="28"/><span><strong>Đề xuất chi phí</strong><small>Thuê máy, sửa chữa, vận chuyển…</small></span><Icon name="arrow"/>
     </button>
     <h3>Phiếu gần đây</h3>
     <button v-for="r in rows.slice(0,5)" :key="r.name" class="field-proposal__entry" @click="open(r)">
      <span><strong>{{r.kind}} · {{r.name}}</strong><small>{{r.reason}}</small></span><b>{{r.state}}</b>
     </button>
     <p v-if="!rows.length" class="field-proposal__empty">Chưa có phiếu nào. Chọn một loại đề xuất để bắt đầu.</p>
    </template>

    <template v-if="setup&&screen==='history'">
     <LotusMobileInput v-model="filter" label="Tìm phiếu của tôi" placeholder="Tìm theo mã hoặc nội dung…"/>
     <button v-for="r in visibleRows" :key="r.name" class="field-proposal__entry" @click="open(r)">
      <span><strong>{{r.kind}} · {{r.name}}</strong><small>{{r.reason}}</small><small>{{r.farm}} · {{money(r.total_estimate)}}</small></span>
      <b>{{r.state}}</b>
     </button>
     <p v-if="!visibleRows.length" class="field-proposal__empty">Chưa có phiếu phù hợp.</p>
    </template>

    <template v-if="setup&&screen==='review'">
     <p class="field-proposal__help">Các đề xuất cần quản lý xem xét. Duyệt ở đây không xuất kho hoặc chi tiền.</p>
     <button v-for="r in reviewRows.filter(r=>r.owner!==setup.user)" :key="r.name" class="field-proposal__entry" @click="open(r)">
      <span><strong>{{r.kind}} · {{r.name}}</strong><small>{{r.reason}}</small><small>{{r.farm}} · {{money(r.total_estimate)}}</small></span><b>Chờ duyệt</b>
     </button>
     <p v-if="!reviewRows.some(r=>r.owner!==setup.user)" class="field-proposal__empty">Không có phiếu chờ duyệt.</p>
    </template>

    <template v-if="setup&&screen==='form'&&form">
     <div class="field-proposal__card">
      <strong>{{form.kind==='Vật tư'?'Đề xuất vật tư':'Đề xuất chi phí'}}</strong>
      <MobileLinkField v-model="form.farm" :options="farms" label="Vườn sử dụng" :searchable="false" required @update:model-value="form.farm_block=''"/>
      <MobileLinkField v-model="form.farm_block" :options="blocks" label="Lô / khu (nếu có)" :searchable="true"/>
      <LotusMobileInput v-model="form.needed_date" type="date" :min="today" label="Ngày cần" required/>
      <LotusMobileInput v-model="form.reason" type="textarea" :rows="3" maxlength="1000" label="Lý do đề xuất" placeholder="Cần để làm việc gì, ở lô nào?" required/>
     </div>
     <section v-for="(line,i) in form.lines" :key="line.key" class="field-proposal__card">
      <div class="field-proposal__row"><strong>Khoản {{i+1}}</strong><button v-if="form.lines.length>1" type="button" @click="form.lines.splice(i,1)">Xóa</button></div>
      <MobileLinkField v-if="form.kind==='Vật tư'" :model-value="line.item_code" :options="items"
       label="Chọn vật tư có sẵn trong danh mục" :aria-label="'Vật tư '+(i+1)"
       @update:model-value="chooseItem(line,$event)"/>
      <LotusMobileInput v-if="!line.item_code||form.kind==='Chi phí'" v-model="line.description"
       :label="form.kind==='Vật tư'?'Tên vật tư chưa có trong danh mục':'Tên khoản chi'"
       placeholder="Nhập nội dung cụ thể" maxlength="140" required/>
      <p v-else class="field-proposal__selected">{{line.description}} · {{line.uom}}</p>
      <div class="field-proposal__pair">
       <LotusMobileInput v-model="line.qty" type="number" label="Số lượng" min="0.001" step="any" required/>
       <LotusMobileInput v-model="line.uom" label="Đơn vị" :disabled="!!line.item_code" placeholder="kg, bao, chuyến…" required/>
      </div>
      <LotusMobileInput v-model="line.rate" type="number" label="Giá dự kiến / đơn vị (đ)"
        min="0" step="1000" :hint="form.kind==='Vật tư'?'Chưa biết giá có thể để 0.':'Chi phí cần có số tiền dự kiến.'"/>
      <div class="field-proposal__row"><small>Thành tiền dự kiến</small><strong>{{money(Number(line.qty||0)*Number(line.rate||0))}}</strong></div>
     </section>
     <LotusMobileButton class="field-proposal__outline" block @click="addLine" :disabled="form.lines.length>=30">Thêm khoản đề xuất</LotusMobileButton>
     <div class="field-proposal__total"><span>Tổng dự kiến</span><strong>{{money(total)}}</strong></div>
     <div class="field-proposal__actions">
      <LotusMobileButton block :disabled="saving" @click="save(false)">Lưu nháp</LotusMobileButton>
      <LotusMobileButton block variant="primary" :disabled="saving" @click="save(true)">Gửi quản lý</LotusMobileButton>
     </div>
    </template>

    <template v-if="setup&&screen==='detail'&&current">
     <div class="field-proposal__card">
      <div class="field-proposal__row"><strong>{{current.name}}</strong><b>{{current.state}}</b></div>
      <p>{{current.kind}} · {{current.farm}}{{current.farm_block?' / '+current.farm_block:''}}</p>
      <p>{{current.reason}}</p><small>Cần ngày {{current.needed_date}}</small>
     </div>
     <div v-for="(line,i) in current.lines" :key="i" class="field-proposal__card">
      <strong>{{i+1}}. {{line.description}}</strong>
      <div class="field-proposal__row"><span>{{fmt(line.qty)}} {{line.uom}} × {{money(line.rate)}}</span><b>{{money(line.amount)}}</b></div>
     </div>
     <div class="field-proposal__total"><span>Tổng dự kiến</span><strong>{{money(current.total_estimate)}}</strong></div>
     <p v-if="current.review_note" class="field-proposal__help">Ý kiến quản lý: {{current.review_note}}</p>
     <template v-if="current.can_edit">
      <LotusMobileButton block @click="edit">Sửa phiếu</LotusMobileButton>
      <LotusMobileButton block :disabled="saving" @click="submitSaved">Gửi quản lý</LotusMobileButton>
     </template>
     <template v-if="current.can_review">
      <LotusMobileInput v-model="reviewNote" type="textarea" maxlength="1000" label="Ý kiến quản lý" placeholder="Ghi rõ lý do nếu trả lại hoặc từ chối"/>
      <LotusMobileButton block :disabled="saving" @click="decide('Đã duyệt')">Duyệt đề xuất</LotusMobileButton>
      <LotusMobileButton block :disabled="saving||reviewNote.trim().length<3" @click="decide('Trả lại')">Trả lại để sửa</LotusMobileButton>
      <LotusMobileButton block :disabled="saving||reviewNote.trim().length<3" @click="decide('Từ chối')">Từ chối</LotusMobileButton>
     </template>
     <p class="field-proposal__help">Phiếu được duyệt là chấp thuận nhu cầu. Xuất kho, mua hàng và thanh toán vẫn thực hiện bằng chứng từ riêng.</p>
    </template>

    <template v-if="setup&&screen==='profile'">
     <div class="field-proposal__card"><strong>{{setup.name}}</strong><p>{{setup.user}}</p><p>{{setup.reviewer?'Có quyền xem xét đề xuất':'Được gửi đề xuất vật tư, chi phí'}}</p></div>
     <LotusMobileButton block @click="logoutPwa('proposal',{csrf:setup.csrf_token,home:'/field-proposals'})">Đăng xuất</LotusMobileButton>
    </template>
   </main>
  </LotusMobileShell>
 </div>
</template>
