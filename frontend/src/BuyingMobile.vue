<script setup>
import BuyingOrderCard from './components/BuyingOrderCard.vue'
import {Icon} from 'vant'
import MobilePurchaseOrderDetail from './components/MobilePurchaseOrderDetail.vue'
import LotusMobileFeedback from './components/LotusMobileFeedback.vue'
import MobilePurchaseOrderForm from './components/MobilePurchaseOrderForm.vue'
import MobileSupplierForm from './components/MobileSupplierForm.vue'
import {newPurchaseDraft,purchaseFromRequest,savePurchaseDraft,retryPurchaseQuote,purchaseLeaveMessage} from './mobile-purchase'
import {purchasePdfUrl,sharePurchasePdf} from './purchase-document'
import {useMobileConfirm} from './use-mobile-confirm'
import LotusMobileDialog from './components/LotusMobileDialog.vue'
import LotusMobileSelect from './components/LotusMobileSelect.vue'
import LotusMobileButton from './components/LotusMobileButton.vue'
import LotusMobileShell from './components/LotusMobileShell.vue'
import {logoutPwa} from './mobile-push-session'
import LotusMobileAction from './components/LotusMobileAction.vue'
import LotusMobileInput from './components/LotusMobileInput.vue'
import {computed, onMounted, onUnmounted, ref, watch} from 'vue'
import {call, setCSRF, upload} from './api'
import MobileLinkField from './components/MobileLinkField.vue'
import {unitLabel} from './units'
import {useMobileViewport} from './use-mobile-viewport'
import './buying-mobile.css'
import './register-buying-worker'

const api=(name,args={},write=false)=>call('lotus_farm.purchasing.'+name,args,write)
const purchase=(name,args={},write=false)=>call('lotus_farm.warehouse_buying_lite.'+name,args,write)
const {keyboard}=useMobileViewport()
function openSetup(){window.dispatchEvent(new Event('lotus:open-setup'))}
const session=ref(null),company=ref(''),catalog=ref(null),orders=ref([]),requests=ref([]),suppliers=ref([])
const tab=ref('home'),view=ref(''),busy=ref(false),saving=ref(false),error=ref(''),notice=ref('')
const filter=ref(''),status=ref('Tất cả'),detail=ref(null),draft=ref(null),quote=ref(null),rejectReason=ref('')
const savedPurchase=ref(null)
const newEta=ref(''),deliveryReason=ref(''),closeReason=ref(''),cancelReason=ref('')
const showReschedule=ref(false),pendingFinalAction=ref(''),finalDialog=ref(null)
const supplierForm=ref(null),supplierSearch=ref(''),selectedRequest=ref('')
const {dialog:leaveDialog,message:leaveMessage,pending:leavePending,ask:askLeave,finish:finishLeave}=useMobileConfirm()
let initialDraft='',initialSupplier=''
function dirtyPurchase(){return !!draft.value&&(savedPurchase.value?!!savedPurchase.value.quoteError:JSON.stringify(draft.value)!==initialDraft||!!quote.value)}
function confirmLeave(target=''){
 const dirtySupplier=view.value==='supplier'&&!!supplierForm.value&&JSON.stringify(supplierForm.value)!==initialSupplier
 const dirtyOrder=(view.value==='form'||view.value==='supplier'&&supplierReturn==='form'&&target!=='form')&&dirtyPurchase()
 return dirtySupplier||dirtyOrder?askLeave(purchaseLeaveMessage(!!savedPurchase.value?.quoteError)):Promise.resolve(true)
}
function beforeUnload(event){if(saving.value||view.value==='form'&&dirtyPurchase()||view.value==='supplier'&&(JSON.stringify(supplierForm.value)!==initialSupplier||supplierReturn==='form'&&dirtyPurchase())){event.preventDefault();event.returnValue=''}}
const online=ref(navigator.onLine)
let navigationReady=false, restoring=false
const baseTabs=['home','orders','suppliers','profile']
const mobileTabs=[
 {name:'home',label:'Trang chủ',icon:'wap-home-o'},
 {name:'orders',label:'Đơn mua',icon:'orders-o'},
 {name:'suppliers',label:'Nhà cung cấp',icon:'shop-o'},
 {name:'profile',label:'Tôi',icon:'user-o'}
]
const mobileTitle=computed(()=>view.value?({form:'Đơn mua hàng',detail:'Chi tiết đơn mua',supplier:'Nhà cung cấp',requests:'Đề nghị mua'})[view.value]||'Mua hàng Lotus':
 ({home:'Mua hàng Lotus',orders:'Đơn mua hàng',suppliers:'Nhà cung cấp',profile:'Tôi'})[tab.value])

const canCreate=computed(()=>session.value?.can_create)
const warehouses=computed(()=>catalog.value?.warehouses||[])
const items=computed(()=>catalog.value?.items||[])
const money=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:0})+' '+(catalog.value?.currency||'VND')
const number=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
const counts=computed(()=>({
 pending:orders.value.filter(r=>r.approval_status==='Chờ duyệt').length,
 shipping:orders.value.filter(r=>r.docstatus===1&&['Chờ hàng','Về một phần','Quá hẹn'].includes(r.status)).length,
 requests:requests.value.length
}))
const visibleOrders=computed(()=>orders.value.filter(r=>(status.value==='Tất cả'||status.value===r.approval_status||status.value===r.status)&&
  (!filter.value||(r.name+' '+r.supplier_name+' '+r.status).toLocaleLowerCase().includes(filter.value.toLocaleLowerCase()))))
const visibleSuppliers=computed(()=>suppliers.value.filter(r=>!supplierSearch.value||
 (r.supplier_name+' '+(r.lotus_supplier_phone||'')).toLocaleLowerCase().includes(supplierSearch.value.toLocaleLowerCase())))
const blank=()=>({id:Math.random().toString(36).slice(2),item:'',qty:1,uom:'',rate:'',warehouse:'',material_request:'',material_request_item:''})
function resetFeedback(){error.value='';notice.value=''}
async function changeTab(next){
 if(saving.value||!view.value&&tab.value===next||!await confirmLeave())return
 resetFeedback();view.value='';detail.value=null;tab.value=next
 if(navigationReady&&!restoring)window.history.pushState({lotusBuying:true,tab:next,view:''},'',location.href)
}
function openView(next){
 resetFeedback();view.value=next
 if(next==='form')initialDraft=JSON.stringify(draft.value)
 if(next==='supplier')initialSupplier=JSON.stringify(supplierForm.value)
 if(navigationReady&&!restoring)window.history.pushState({lotusBuying:true,tab:tab.value,view:next},'',location.href)
}
async function back(){
 const target=view.value==='supplier'&&supplierReturn==='form'?'form':''
 if(saving.value||!await confirmLeave(target))return
 if(target){view.value='form';supplierForm.value=null;window.history.replaceState({lotusBuying:true,tab:tab.value,view:'form'},'',location.href);return}
 if(view.value){view.value='';detail.value=null;draft.value=null;quote.value=null}
 else changeTab('home')
}
async function browserBack(e){
 const s=e.state
 if(leavePending.value){finishLeave(false);window.history.pushState({lotusBuying:true,tab:tab.value,view:view.value},'',location.href);return}
 if(saving.value||!await confirmLeave(s?.view||'')){window.history.pushState({lotusBuying:true,tab:tab.value,view:view.value},'',location.href);return}
 restoring=true
 tab.value=baseTabs.includes(s?.tab)?s.tab:'home'
 view.value=s?.view||''
 if(view.value==='detail'&&!detail.value)view.value=''
 if(view.value==='form'&&!draft.value||view.value==='supplier'&&!supplierForm.value)view.value=''
 if(!s?.lotusBuying)window.history.pushState({lotusBuying:true,tab:tab.value,view:view.value},'',location.href)
 restoring=false
}
function refreshNetwork(){online.value=navigator.onLine}
async function run(task){
 if(saving.value||!online.value)return
 saving.value=true;resetFeedback()
 try{await task()}catch(e){error.value=e?.message||'Không thực hiện được. Kiểm tra kết nối rồi thử lại.'}
 finally{saving.value=false}
}
async function refresh(){
 busy.value=true
 try{
  const [list,req,providers]=await Promise.all([
   api('orders',{company:company.value}),api('requests',{company:company.value}),api('suppliers')
  ])
  orders.value=list;requests.value=req;suppliers.value=providers
 }finally{busy.value=false}
}
async function initialize(){
 busy.value=true;resetFeedback()
 try{
  session.value=await api('bootstrap')
  setCSRF(session.value.csrf_token)
  company.value=session.value.companies?.[0]?.name||''
  if(!company.value)throw Error('Tài khoản chưa được cấp công ty.')
  catalog.value=await api('catalog',{company:company.value})
  await refresh()
  if(new URLSearchParams(location.search).get('request')==='1')newOrder(true)
 }catch(e){error.value=e.message}finally{busy.value=false}
}
async function switchCompany(value){
 if(!value||value===company.value||saving.value||!await confirmLeave())return
 busy.value=true;resetFeedback()
 try{
  const next=await api('catalog',{company:value})
  company.value=value;catalog.value=next;tab.value='home';view.value=''
  await refresh()
 }catch(e){error.value=e.message}finally{busy.value=false}
}
function newOrder(fromRequest=false){
 if(!canCreate.value)return
 selectedRequest.value=''
 draft.value=newPurchaseDraft(warehouses.value[0]?.name||'',session.value?.today||'')
 savedPurchase.value=null
 quote.value=null;openView('form')
 if(fromRequest&&requests.value.length)selectedRequest.value=requests.value[0].name
 if(selectedRequest.value)useRequest(selectedRequest.value)
 initialDraft=JSON.stringify(draft.value)
}
function useRequest(name){
 selectedRequest.value=name
 draft.value=purchaseFromRequest(draft.value,requests.value.find(r=>r.name===name))
}
async function openOrder(name){
 busy.value=true;resetFeedback()
 try{detail.value=await api('detail',{name});rejectReason.value='';newEta.value=detail.value.revised_delivery_date||detail.value.expected_date||'';deliveryReason.value='';closeReason.value='';cancelReason.value='';showReschedule.value=false;openView('detail')}
 catch(e){error.value=e.message}finally{busy.value=false}
}
function editOrder(){
 if(!detail.value?.can_write||!['Nháp','Từ chối'].includes(detail.value?.approval_status))return
 const d=detail.value
 draft.value={name:d.name,modified:d.modified,supplier:d.supplier,mode:d.mode,warehouse:d.items[0]?.warehouse||warehouses.value[0]?.name||'',
   expected_date:d.expected_date,notes:d.notes,items:d.items.map(r=>({...blank(),item:r.item,qty:r.qty,
   rate:r.rate,uom:r.uom,warehouse:r.warehouse,material_request:r.material_request,material_request_item:r.material_request_item}))}
 quote.value=null;savedPurchase.value=null;openView('form')
}
async function saveOrder(){
 if(savedPurchase.value)return
 await run(async()=>{
  const result=await savePurchaseDraft({company:company.value,draft:draft.value,catalog:catalog.value,quote:quote.value,
   save:args=>purchase('save_order',args,true),upload,onSaved:result=>{savedPurchase.value={...result,quoteError:''}}})
  savedPurchase.value=result
 })
}
async function retryQuote(){
 await run(async()=>{await retryPurchaseQuote({saved:savedPurchase.value,quote:quote.value,upload});savedPurchase.value={...savedPurchase.value,quoteError:''}})
}
async function viewSavedPurchase(){
 if(savedPurchase.value?.quoteError&&!await confirmLeave())return
 await run(async()=>{await refresh();await openOrder(savedPurchase.value.name)})
}
async function applyAction(action){
 await run(async()=>{
  if(!detail.value)return
  const d=detail.value
  const args={name:d.name,modified:d.modified}
  if(action==='reject_order')args.reason=rejectReason.value.trim()
  if(action==='reschedule_order'){args.expected_date=newEta.value;args.reason=deliveryReason.value.trim()}
  if(action==='close_order')args.reason=closeReason.value.trim()
  if(action==='cancel_order')args.reason=cancelReason.value.trim()
  await api(action,args,true)
  await refresh();await openOrder(d.name)
  notice.value={
   request_approval:'Đã gửi cho người duyệt.',approve_order:'Đã duyệt đơn mua.',reject_order:'Đã trả lại đơn để sửa.',
   mark_order_sent:'Đã ghi nhận gửi đơn cho nhà cung cấp.',confirm_supplier_order:'Đã ghi nhận NCC xác nhận.',
   reschedule_order:'Đã cập nhật ngày giao mới.',close_order:'Đã đóng phần hàng không giao.',
   cancel_order:'Đã hủy đơn mua.'
  }[action]||'Đã cập nhật.'
 })
}
function confirmFinalAction(action){
 if(action==='close_order'&&closeReason.value.trim().length<3||action==='cancel_order'&&cancelReason.value.trim().length<3){
  error.value='Nhập lý do ít nhất 3 ký tự trước khi tiếp tục.';return
 }
 pendingFinalAction.value=action;finalDialog.value?.showModal()
}
function commitFinalAction(){
 const action=pendingFinalAction.value
 finalDialog.value?.close();pendingFinalAction.value=''
 if(action)applyAction(action)
}
function openPurchasePdf(){if(detail.value?.name)window.open(purchasePdfUrl(detail.value.name),'_blank','noopener')}
async function sharePdf(){
 if(!detail.value?.name||saving.value||!online.value)return
 await run(async()=>{
  const status=await sharePurchasePdf(detail.value.name)
  if(status==='shared')notice.value='Đã mở chia sẻ PDF. Sau khi gửi cho NCC, hãy bấm “Đã gửi NCC”.'
  if(status==='downloaded')notice.value='Đã tải PDF. Có thể gửi qua Zalo hoặc email, rồi xác nhận đã gửi NCC.'
 })
}
let supplierReturn=''
function addSupplier(){
 supplierReturn=view.value==='form'?'form':''
 supplierForm.value={name:'',supplier_id:'',phone:'',contact:'',notes:''};openView('supplier')
}
function editSupplier(s){
 supplierReturn=''
 supplierForm.value={supplier_id:s.name,name:s.supplier_name,
  phone:s.lotus_supplier_phone||'',contact:s.lotus_supplier_contact||'',notes:s.lotus_supplier_note||''}
 openView('supplier')
}
async function saveSupplier(){
 await run(async()=>{
  if(!supplierForm.value.name?.trim())throw Error('Nhập tên nhà cung cấp.')
  const result=await api('save_supplier',supplierForm.value,true)
  supplierForm.value.supplier_id=result.name
  await refresh()
  if(supplierReturn==='form'&&draft.value)draft.value.supplier=result.name
  view.value=supplierReturn;supplierForm.value=null
  window.history.replaceState({lotusBuying:true,tab:tab.value,view:view.value},'',location.href)
  notice.value='Đã lưu nhà cung cấp.'
 })
}
async function logout(){
 if(saving.value||!await confirmLeave()||!await askLeave('Đăng xuất khỏi Mua hàng Lotus?'))return
 saving.value=true;error.value=''
 try{await logoutPwa('buying',{csrf:session.value?.csrf_token||'',home:'/buying'})}
 catch(e){error.value='Không đăng xuất được: '+e.message}
 finally{saving.value=false}
}
onMounted(()=>{window.history.replaceState({lotusBuying:true,tab:'home',view:''},'',location.href);
 navigationReady=true;window.addEventListener('popstate',browserBack)
 window.addEventListener('beforeunload',beforeUnload)
 window.addEventListener('online',refreshNetwork);window.addEventListener('offline',refreshNetwork)
 initialize().then(()=>{
 const doc=new URLSearchParams(location.search).get('doc')
 if(session.value&&doc)openOrder(doc)
})})
onUnmounted(()=>{window.removeEventListener('popstate',browserBack);window.removeEventListener('online',refreshNetwork);
 window.removeEventListener('beforeunload',beforeUnload)
 window.removeEventListener('offline',refreshNetwork)})
</script>

<template>
<LotusMobileShell app="buying" :refresh="refresh" :refreshable="!view" class="buy-app" :class="{'buy-keyboard':keyboard}"
 :title="mobileTitle" :tabs="mobileTabs" :active-tab="tab" :back="!!view"
 :keyboard-open="keyboard" :disabled="saving" @back="back" @navigate="changeTab">
<main class="buy-main">
  <LotusMobileFeedback v-if="!online" kind="warning">Mất mạng. Không thể gửi đơn hoặc duyệt lúc này.</LotusMobileFeedback>
  <LotusMobileFeedback v-if="error" kind="error">{{error}}</LotusMobileFeedback>
  <LotusMobileFeedback v-if="notice" kind="success">{{notice}}</LotusMobileFeedback>
  <LotusMobileFeedback v-if="busy" kind="loading">Đang tải dữ liệu…</LotusMobileFeedback>

  <template v-if="!view&&tab==='home'">
   <div v-if="session?.companies?.length>1" class="buy-field"><label>Công ty</label>
    <MobileLinkField aria-label="Công ty" :model-value="company" :searchable="false" :options="session.companies.map(r=>({value:r.name,label:r.name}))" @update:modelValue="switchCompany"/></div>
   <div class="buy-summary">
    <LotusMobileButton @click="status='Chờ duyệt';changeTab('orders')"><b>{{counts.pending}}</b><small>Chờ duyệt</small></LotusMobileButton>
    <LotusMobileButton @click="status='Tất cả';changeTab('orders')"><b>{{counts.shipping}}</b><small>Chờ giao</small></LotusMobileButton>
    <LotusMobileButton @click="openView('requests')"><b>{{counts.requests}}</b><small>Đề nghị mua</small></LotusMobileButton>
   </div>
   <div class="mobile-actions" aria-label="Thao tác Mua hàng">
    <LotusMobileAction v-if="canCreate" primary icon="cart-o" title="Tạo đơn mua" @select="newOrder()"/>
    <LotusMobileAction icon="notes-o" title="Đề nghị mua" @select="openView('requests')"/>
    <LotusMobileAction v-if="session?.can_approve" icon="passed" title="Duyệt đơn" @select="status='Chờ duyệt';changeTab('orders')"/>
    <LotusMobileAction icon="shop-o" title="Nhà cung cấp" @select="changeTab('suppliers')"/>
   </div>
   <h2>Đơn gần đây</h2>
   <BuyingOrderCard v-for="r in orders.slice(0,5)" :key="r.name" :order="r" :currency="catalog?.currency||'VND'" @select="openOrder"/>
   <p v-if="!orders.length&&!busy" class="mobile-empty">Chưa có đơn mua.</p>
  </template>

  <template v-if="!view&&tab==='orders'">
   <div class="buy-toolbar"><LotusMobileInput v-model="filter" type="search" placeholder="Tìm số đơn, nhà cung cấp…" aria-label="Tìm đơn mua"/>
    <LotusMobileSelect v-model="status" aria-label="Lọc đơn mua"><option>Tất cả</option><option>Nháp</option><option>Chờ duyệt</option><option>Đã duyệt</option><option>Từ chối</option><option>Đã đóng</option><option>Đã hủy</option><option>Quá hẹn</option><option>Về một phần</option><option>Đã nhận đủ</option></LotusMobileSelect></div>
   <LotusMobileButton v-if="canCreate" class="buy-primary" @click="newOrder()">+ Tạo đơn mua</LotusMobileButton>
   <BuyingOrderCard v-for="r in visibleOrders" :key="r.name" :order="r" :currency="catalog?.currency||'VND'" show-date @select="openOrder"/>
   <p v-if="!visibleOrders.length&&!busy" class="mobile-empty">Không tìm thấy đơn phù hợp.</p>
  </template>

  <template v-if="!view&&tab==='suppliers'">
   <LotusMobileInput v-model="supplierSearch" class="buy-search" type="search" placeholder="Gõ tên hoặc số điện thoại NCC…" aria-label="Tìm nhà cung cấp"/>
   <LotusMobileButton v-if="catalog?.can_create_supplier" class="buy-primary" @click="addSupplier()">+ Thêm nhà cung cấp</LotusMobileButton>
   <LotusMobileButton v-for="s in visibleSuppliers" :key="s.name" class="buy-card" @click="editSupplier(s)">
    <div class="buy-line"><strong>{{s.supplier_name}}</strong><span class="buy-pill">{{s.disabled?'Ngừng dùng':'Đang dùng'}}</span></div>
    <small>{{s.lotus_supplier_contact||'Chưa có người liên hệ'}}</small>
    <div class="buy-line"><span>{{s.lotus_supplier_phone||'Chưa có số điện thoại'}}</span><span>Chi tiết <Icon name="arrow" class="lotus-pwa-inline-icon" aria-hidden="true"/></span></div>
   </LotusMobileButton>
  </template>

  <template v-if="!view&&tab==='profile'">
   <div class="buy-card"><strong>{{session?.user||'—'}}</strong><small>{{company}}</small>
    <p>Quyền: {{session?.can_approve?'Duyệt đơn mua':'Không có quyền duyệt'}} · {{canCreate?'Lập đơn':'Chỉ xem'}}</p></div>
   <LotusMobileButton class="buy-outline" type="button" @click="openSetup()">Cài ứng dụng và thông báo</LotusMobileButton>
   <LotusMobileButton class="buy-outline" type="button" @click="refresh()">Làm mới</LotusMobileButton>
   <LotusMobileButton class="buy-outline" type="button" @click="logout()">Đăng xuất</LotusMobileButton>
  </template>

  <template v-if="view==='requests'">
   <div v-for="r in requests" :key="r.name" class="buy-card">
    <div class="buy-line"><strong>{{r.name}}</strong><span class="buy-pill">{{r.items.length}} mặt hàng</span></div>
    <small>Ngày cần {{r.expected_date}} · Người gửi {{r.owner}}</small>
    <p v-for="(line,i) in r.items.slice(0,5)" :key="i" class="buy-request-line">{{line.item_name}} · {{number(line.qty)}} {{unitLabel(line.uom)}}</p>
    <LotusMobileButton class="buy-outline" :disabled="!canCreate" @click="newOrder(true);useRequest(r.name)">Lập đơn mua từ đề nghị này</LotusMobileButton>
   </div>
   <p v-if="!requests.length&&!busy" class="mobile-empty">Chưa có đề nghị mua còn thiếu hàng.</p>
  </template>

  <template v-if="view==='form'&&draft">
   <MobilePurchaseOrderForm v-model="draft" v-model:quote="quote" :saved="savedPurchase" :items="items" :conversions="catalog?.conversions||[]"
    :warehouses="warehouses" :suppliers="suppliers" :requests="requests" :selected-request="selectedRequest" :currency="catalog?.currency||'VND'"
    :can-create-supplier="!!catalog?.can_create_supplier" :saving="saving" :online="online"
    @update:selectedRequest="useRequest" @submit="saveOrder" @add-supplier="addSupplier" @retry-quote="retryQuote" @view-saved="viewSavedPurchase" @new-order="newOrder()"/>
  </template>

  <template v-if="view==='detail'&&detail">
   <MobilePurchaseOrderDetail :order="detail" :currency="catalog?.currency||'VND'" :warehouses="warehouses"/>
   <div v-if="detail.can_write&&['Nháp','Từ chối'].includes(detail.approval_status)">
    <LotusMobileButton class="buy-outline" @click="editOrder()">Sửa đơn</LotusMobileButton></div>
   <LotusMobileButton v-if="detail.can_request_approval" class="buy-primary" :disabled="saving||!online" @click="applyAction('request_approval')">Gửi duyệt đơn mua</LotusMobileButton>
   <div v-if="detail.can_approve">
    <LotusMobileButton class="buy-primary" :disabled="saving||!online" @click="applyAction('approve_order')">Duyệt đơn mua</LotusMobileButton>
    <div class="buy-field"><label>Lý do từ chối</label><LotusMobileInput type="textarea" v-model="rejectReason" rows="2" placeholder="Nêu lý do để người lập sửa lại…"/></div>
    <LotusMobileButton class="buy-danger" :disabled="saving||!online||rejectReason.trim().length<3" @click="applyAction('reject_order')">Trả lại đơn</LotusMobileButton>
   </div>
   <p v-if="detail.approval_status==='Chờ duyệt'&&!detail.can_approve" class="buy-muted">Đơn đang chờ người khác có quyền duyệt. Người lập đơn không được tự duyệt.</p>
   <section v-if="detail.docstatus===1" class="buy-order-actions">
    <LotusMobileButton v-if="detail.can_print" class="buy-outline" :disabled="saving" @click="openPurchasePdf()">Xem / in đơn PDF</LotusMobileButton>
    <LotusMobileButton v-if="detail.can_print" class="buy-outline" :disabled="saving||!online" @click="sharePdf()">Chia sẻ PDF qua Zalo / ứng dụng khác</LotusMobileButton>
    <p v-if="detail.can_manage&&!detail.sent_at" class="buy-muted">Sau khi thực sự gửi đơn cho nhà cung cấp, bấm xác nhận bên dưới.</p>
    <LotusMobileButton v-if="detail.can_manage&&!detail.sent_at" class="buy-primary" :disabled="saving||!online" @click="applyAction('mark_order_sent')">Đã gửi NCC</LotusMobileButton>
    <LotusMobileButton v-if="detail.can_manage&&detail.sent_at&&!detail.supplier_confirmed_at" class="buy-outline" :disabled="saving||!online" @click="applyAction('confirm_supplier_order')">NCC đã xác nhận nhận đơn</LotusMobileButton>
    <LotusMobileButton v-if="detail.can_manage" class="buy-outline" :disabled="saving||!online" @click="showReschedule=!showReschedule">Đổi ngày giao dự kiến</LotusMobileButton>
    <section v-if="detail.can_manage&&showReschedule" class="buy-card">
     <LotusMobileInput v-model="newEta" label="Ngày NCC hẹn lại" type="date" :min="session?.today" required/>
     <LotusMobileInput v-model="deliveryReason" label="Lý do đổi ngày" type="textarea" :rows="2" maxlength="500" placeholder="Ví dụ: xe giao hàng đến trễ"/>
     <LotusMobileButton class="buy-primary" :disabled="saving||!online||!newEta||deliveryReason.trim().length<3" @click="applyAction('reschedule_order')">Lưu ngày hẹn mới</LotusMobileButton>
    </section>
    <section v-if="detail.can_close" class="buy-card">
     <LotusMobileInput v-model="closeReason" label="Đóng phần hàng NCC không giao" type="textarea" :rows="2" maxlength="500" placeholder="Ví dụ: NCC chỉ giao được 70/100 bao"/>
     <LotusMobileButton class="buy-outline" :disabled="saving||!online||closeReason.trim().length<3" @click="confirmFinalAction('close_order')">Đóng phần còn lại</LotusMobileButton>
    </section>
    <section v-if="detail.can_cancel" class="buy-card">
     <LotusMobileInput v-model="cancelReason" label="Lý do hủy đơn" type="textarea" :rows="2" maxlength="500" placeholder="Chỉ khi đơn chưa có phiếu nhận hoặc chứng từ liên quan"/>
     <LotusMobileButton class="buy-danger" :disabled="saving||!online||cancelReason.trim().length<3" @click="confirmFinalAction('cancel_order')">Hủy đơn mua</LotusMobileButton>
    </section>
   </section>
  </template>

  <MobileSupplierForm v-if="view==='supplier'&&supplierForm" v-model="supplierForm" :saving="saving" :online="online" @submit="saveSupplier"/>
 </main>
 <LotusMobileDialog ref="finalDialog" class="mobile-leave-dialog">
  <div class="mobile-leave-content"><h2>{{pendingFinalAction==='cancel_order'?'Xác nhận hủy đơn?':'Xác nhận đóng đơn?'}}</h2>
   <p>{{pendingFinalAction==='cancel_order'?'Không thể hủy nếu đơn có phiếu nhập hoặc chứng từ liên quan.':'Phần chưa giao sẽ không còn nằm trong hàng chờ về.'}}</p>
   <div><LotusMobileButton @click="finalDialog?.close()">Ở lại</LotusMobileButton><LotusMobileButton class="danger" :disabled="saving" @click="commitFinalAction()">Xác nhận</LotusMobileButton></div>
  </div>
 </LotusMobileDialog>
 <LotusMobileDialog ref="leaveDialog" class="mobile-leave-dialog" @cancel.prevent="finishLeave(false)">
  <div class="mobile-leave-content"><h2>Rời màn hình?</h2><p>{{leaveMessage}}</p><div><LotusMobileButton type="button" @click="finishLeave(false)">Ở lại</LotusMobileButton><LotusMobileButton type="button" class="danger" @click="finishLeave(true)">Rời đi</LotusMobileButton></div></div>
 </LotusMobileDialog>
</LotusMobileShell>
</template>