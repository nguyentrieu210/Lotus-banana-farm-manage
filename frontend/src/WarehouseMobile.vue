<script setup>
import DocumentReader from './components/DocumentReader.vue'
import StockEvidence from './components/stock/StockEvidence.vue'
import {formatDate} from './format'
import MobilePurchaseOrderDetail from './components/MobilePurchaseOrderDetail.vue'
import {Icon} from 'vant'
import LotusMobileFeedback from './components/LotusMobileFeedback.vue'
import {useMobileConfirm} from './use-mobile-confirm'
import MobilePurchaseOrderForm from './components/MobilePurchaseOrderForm.vue'
import MobileSupplierForm from './components/MobileSupplierForm.vue'
import StockReceiptReason from './components/StockReceiptReason.vue'
import {newPurchaseDraft,purchaseFromRequest,savePurchaseDraft,retryPurchaseQuote,purchaseLeaveMessage} from './mobile-purchase'
import LotusMobileCheck from './components/LotusMobileCheck.vue'
import LotusMobileFile from './components/LotusMobileFile.vue'
import LotusMobileDialog from './components/LotusMobileDialog.vue'
import LotusMobileSelect from './components/LotusMobileSelect.vue'
import LotusMobileButton from './components/LotusMobileButton.vue'
import LotusMobileSignatureSettings from './components/LotusMobileSignatureSettings.vue'
import LotusMobileShell from './components/LotusMobileShell.vue'
import {logoutPwa} from './mobile-push-session'
import LotusMobileInput from './components/LotusMobileInput.vue'
import LotusMobileAction from './components/LotusMobileAction.vue'
import {computed,nextTick,onMounted,onUnmounted,ref,watch} from 'vue'
import {call,setCSRF,upload} from './api'
import {unitLabel} from './units'
import {stockQuantity} from './stock-units'
import MobileLinkField from './components/MobileLinkField.vue'
import MobileLiveSearch from './components/MobileLiveSearch.vue'
import SigningPanel from './components/SigningPanel.vue'
import {useMobileViewport} from './use-mobile-viewport'
import {createTabSwipe} from './mobile-swipe'
import {validateReceiptInputs} from './warehouse-mobile-helpers'

const receiptReasonFields=ref(null)

const stockAPI=(name,args={},write=false)=>call('lotus_farm.warehouse.'+name,args,write)
const buyingAPI=(name,args={},write=false)=>call('lotus_farm.warehouse_buying_lite.'+name,args,write)
const receivingAPI=(name,args={},write=false)=>call('lotus_farm.warehouse_planning.'+name,args,write)
const employeeAPI=(name,args={},write=false)=>call('lotus_farm.warehouse_masters.'+name,args,write)

const {keyboard}=useMobileViewport()
function openSetup(){window.dispatchEvent(new Event('lotus:open-setup'))}
const session=ref(null),company=ref(''),warehouse=ref(''),setup=ref(null),employees=ref([])
const screen=ref('home'),kind=ref('receipt'),busy=ref(false),saving=ref(false)
const error=ref(''),message=ref(''),online=ref(navigator.onLine)
const installed=ref(false),form=ref(null),order=ref(null),quote=ref(null)
const requestForm=ref(null),supplierForm=ref(null),savedPurchase=ref(null),purchaseRequests=ref([]),selectedPurchaseRequest=ref('')
let supplierInitial=''
const pending=ref([]),pendingQuery=ref(''),pendingStart=ref(0),pendingMore=ref(false)
const selectedOrder=ref(null),receiveQty=ref({}),receiveDate=ref(''),receiveKey=ref('')
const postedReceipt=ref(null),confirmed=ref(false),createdDoc=ref(null),createdDocDetails=ref(null),lastPostedDocument=ref(null)
const failedQuote=ref(false),updateReady=ref(false),loadingPending=ref(false),loadingHistory=ref(false),loadingInventory=ref(false)
const historyRows=ref([]),historySearch=ref(''),historyWarehouse=ref(''),historyMode=ref('stock'),historyStart=ref(0),historyMore=ref(false),historyDetail=ref(null)
const inventoryMode=ref('stock'),inventorySearch=ref(''),inventoryWarehouse=ref(''),inventoryStart=ref(0)
const inventoryRows=ref([]),inventoryMore=ref(false),inventoryTotal=ref(0)
const movementRows=ref([]),movementStart=ref(0),movementMore=ref(false)
const baseTabs=['home','history','inventory','profile']
const mobileTabs=[
 {name:'home',label:'Trang chủ',icon:'wap-home-o'},
 {name:'history',label:'Lịch sử',icon:'orders-o'},
 {name:'inventory',label:'Xuất nhập tồn',icon:'chart-trending-o'},
 {name:'profile',label:'Tôi',icon:'user-o'}
]
const mobileTitle=computed(()=>({home:'Kho Lotus',history:'Lịch sử',inventory:'Xuất nhập tồn',profile:'Tôi',
 'stock-form':titles[kind.value], 'stock-review':'Kiểm tra phiếu',
 'request-form':'Đề nghị mua','buy-form':'Đơn mua hàng','supplier-form':'Nhà cung cấp',
 'choose-order':'Chọn đơn chờ hàng','receive-form':'Nhận hàng',
 'receive-review':'Kiểm tra hàng nhận','history-detail':'Chi tiết phiếu',done:'Hoàn tất'})[screen.value]||'Kho Lotus')

const activeTab=computed(()=>screen.value==='history-detail'?'history':baseTabs.includes(screen.value)?screen.value:'home')
const storeOptions=computed(()=>warehouses.value.map(w=>({value:w.name,label:w.warehouse_name})))
const itemOptions=computed(()=>items.value.map(i=>({value:i.name,label:i.item_name})))
const employeeOptions=computed(()=>employees.value.map(i=>({value:i.value,label:i.label})))
const companyOptions=computed(()=>session.value?.companies?.map(c=>({value:c.name,label:c.name}))||[])
const pendingSuggestions=computed(()=>(pending.value||[]).map(r=>({value:r.name,label:r.supplier_name||r.supplier||r.name,description:r.name+' · '+(r.status||'')})))
const historySuggestions=computed(()=>(historyRows.value||[]).map(r=>({value:r.name,label:r.doctype==='Purchase Order'?(r.supplier_name||r.name):r.name,description:(r.doctype==='Purchase Order'?'Đơn mua':'Phiếu kho')+' · '+r.name})))
const inventorySuggestions=computed(()=>{
 const pool=inventoryMode.value==='stock'?items.value:(movementRows.value||[]).map(r=>({name:r.item_code,item_name:r.item_name}))
 return Array.from(new Map(pool.filter(r=>r.name).map(r=>[r.name,r])).values())
  .map(r=>({value:r.name,label:r.item_name||r.name,description:r.name}))
})
function pickHistorySuggestion(row){const match=historyRows.value.find(r=>r.name===row.value);if(match)inspectHistory(match)}
function pickInventorySuggestion(row){inventorySearch.value=row.value;loadInventory(true)}
let eventNumber=0, pendingRequest=0, historyRequest=0, inventoryRequest=0, detailRequest=0
const isLoading=computed(()=>busy.value||(screen.value==='choose-order'&&loadingPending.value)||(screen.value==='history'&&loadingHistory.value)||(screen.value==='inventory'&&loadingInventory.value))
let searchTimer=null
function delayedSearch(type){
 if(type==='history')++historyRequest
 if(type==='inventory')++inventoryRequest
 if(type==='pending')++pendingRequest
 clearTimeout(searchTimer)
 searchTimer=setTimeout(()=>{
  if(type==='history'&&screen.value==='history')loadHistory(true)
  if(type==='inventory'&&screen.value==='inventory')loadInventory(true)
  if(type==='pending'&&screen.value==='choose-order')loadPending(true)
 },320)
}
watch(historySearch,()=>delayedSearch('history'))
watch(inventorySearch,()=>delayedSearch('inventory'))
watch(pendingQuery,()=>delayedSearch('pending'))
watch(error,value=>{if(value)nextTick(()=>document.querySelector('.mobile-message.danger')?.scrollIntoView({block:'nearest',behavior:'smooth'}))})
const key=()=>globalThis.crypto?.randomUUID?.()||'m-'+Date.now()+'-'+(++eventNumber)
const today=()=>session.value?.today||setup.value?.today||new Date().toISOString().slice(0,10)
const fmt=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
const warehouses=computed(()=>setup.value?.warehouses||[])
const items=computed(()=>setup.value?.items||[])
const suppliers=computed(()=>setup.value?.suppliers||[])
const titles={receipt:'Nhập không theo đơn',issue:'Xuất kho',transfer:'Chuyển kho'}
const wname=n=>warehouses.value.find(w=>w.name===n)?.warehouse_name||n||'—'
const iname=n=>items.value.find(i=>i.name===n)?.item_name||n||'—'
const allowed=type=>!!session.value?.permissions?.[type]
const selectedLines=computed(()=>selectedOrder.value?.items?.filter(r=>Number(r.remaining_qty)>0)||[])
const receiptCheck=computed(()=>validateReceiptInputs(selectedLines.value,receiveQty.value))
const receivedQuantities=computed(()=>receiptCheck.value.quantities)
const blank=()=>({_key:key(),item:'',query:'',uom:'',qty:1,rate:'',area:''})
function clear(){error.value='';message.value=''}
function safeError(e){
 const detail=String(e?.message||'Không kết nối được máy chủ')
 return /Chưa gửi được|Failed to fetch|NetworkError|Load failed|mất kết nối/i.test(detail)
  ?'Mạng bị gián đoạn, chưa rõ máy chủ đã nhận phiếu hay chưa. Hãy kiểm tra Lịch sử trước khi gửi lại.'
  :detail
}
function home(){screen.value='home';clear()}
const rootScreens=new Set(['home','history','inventory','profile'])
const formScreens=new Set(['stock-form','buy-form','receive-form','request-form','supplier-form'])
const {start:swipeStart,move:swipeMove,end:swipeEnd,cancel:swipeCancel}=createTabSwipe({enabled:()=>rootScreens.has(screen.value)&&!saving.value,ignore:'input,textarea,select,a,.mobile-link-field,.mobile-live-search,.lotus-pwa-bottom,.mobile-leave-dialog',tabs:()=>baseTabs,current:()=>screen.value,go:goTab})
let restoreFromBrowser=false, navigationReady=false
let initialFormValue=''
function rememberForm(value){initialFormValue=JSON.stringify(value)}
function dirtyForm(){
 if(screen.value==='stock-form')return JSON.stringify(form.value)!==initialFormValue
 if(screen.value==='supplier-form')return !!supplierForm.value&&JSON.stringify(supplierForm.value)!==supplierInitial
 if(screen.value==='buy-form')return order.value?.name?failedQuote.value:JSON.stringify(order.value)!==initialFormValue||!!quote.value
 if(screen.value==='request-form')return JSON.stringify(requestForm.value)!==initialFormValue
 if(screen.value==='receive-form')return Object.values(receiveQty.value).some(v=>String(v).trim()!=='')||receiveDate.value!==today()
 return false
}
const {dialog:leaveDialog,message:leaveMessage,pending:leavePending,ask:askLeave,finish:finishLeave}=useMobileConfirm()
async function confirmLeave(target=''){
 const parentDirty=screen.value==='supplier-form'&&target!=='buy-form'&&!!order.value&&(order.value.name?failedQuote.value:JSON.stringify(order.value)!==initialFormValue||!!quote.value)
 if(!formScreens.has(screen.value)||!dirtyForm()&&!parentDirty)return true
 return askLeave(purchaseLeaveMessage(screen.value==='buy-form'&&failedQuote.value))
}
function beforeUnload(event){if(saving.value||formScreens.has(screen.value)&&dirtyForm()||screen.value==='supplier-form'&&!!order.value&&(JSON.stringify(order.value)!==initialFormValue||!!quote.value)){event.preventDefault();event.returnValue=''}}
async function goTab(tab){
 if(saving.value||screen.value===tab||!await confirmLeave())return
 document.dispatchEvent(new Event('warehouse-dismiss-picker'))
 clearTimeout(searchTimer)
 clear();screen.value=tab
 if(tab==='history')loadHistory(true)
 if(tab==='inventory')loadInventory(true)
}
function appBack(){
 if(saving.value)return
 if(dismissPicker())return
 if(screen.value==='home')return
 window.history.back()
}
// Pull-to-refresh reloads the list of the tab on screen.
async function pullRefresh(){if(screen.value==='history')await loadHistory(true);else if(screen.value==='inventory')await loadInventory(true);else await loadPending(true)}
async function refreshApp(){if(await confirmLeave())window.location.reload()}
let hadWorker=!!navigator.serviceWorker?.controller
function onWorkerChange(){if(hadWorker)updateReady.value=true;hadWorker=true}
function dismissPicker(){
 if(!document.querySelector('.mobile-floating-options'))return false
 document.dispatchEvent(new Event('warehouse-dismiss-picker'))
 return true
}
async function onSystemBack(event){
 if(leavePending.value){finishLeave(false);window.history.pushState({lotusWarehouse:true,screen:screen.value},'',window.location.href);return}
 if(saving.value||dismissPicker()){
  window.history.pushState({lotusWarehouse:true,screen:screen.value},'',window.location.href)
  return
 }
 const desired=event.state?.lotusWarehouse?event.state.screen:'home'
 // A saved draft must not reopen the original form with the same request ID:
 // changing the form and submitting again could display a receipt unlike the server draft.
 if((screen.value==='stock-review'&&desired==='stock-form')||(screen.value==='receive-review'&&desired==='receive-form')){
  restoreFromBrowser=true
  screen.value='history'
  window.history.replaceState({lotusWarehouse:true,screen:'history'},'',window.location.href)
  clear();message.value='Phiếu đã lưu nháp. Xem lại ở Lịch sử để tránh tạo trùng.'
  loadHistory(true)
  restoreFromBrowser=false
  return
 }
 if(!await confirmLeave(desired)){
  window.history.pushState({lotusWarehouse:true,screen:screen.value},'',window.location.href)
  return
 }
 restoreFromBrowser=true
 const available=desired==='supplier-form'?!!supplierForm.value:desired==='stock-form'?!!form.value:desired==='buy-form'?!!order.value&&!order.value.name:desired==='request-form'?!!requestForm.value:desired==='receive-form'?!!selectedOrder.value:desired==='stock-review'?!!createdDocDetails.value:desired==='receive-review'?!!postedReceipt.value:desired==='history-detail'?!!historyDetail.value:true
 screen.value=screen.value==='done'?'home':available?desired:'home'
 clear()
 // Root guard: back gestures never leave the PWA for the previous browser page.
 if(!event.state?.lotusWarehouse||screen.value==='home'&&event.state?.lotusWarehouseRoot){
  window.history.pushState({lotusWarehouse:true,screen:'home'},'',window.location.href)
 }
 if(screen.value==='history')loadHistory(true)
 if(screen.value==='inventory')loadInventory(true)
 nextTick(()=>window.scrollTo(0,event.state?.scroll||0))
 restoreFromBrowser=false
}
watch(screen,(next,previous)=>{
 clearTimeout(searchTimer)
 if(previous==='history'){++historyRequest;loadingHistory.value=false}
 if(previous==='inventory'){++inventoryRequest;loadingInventory.value=false}
 if(previous==='choose-order'){++pendingRequest;loadingPending.value=false}
 if(!navigationReady||restoreFromBrowser)return
 window.history.replaceState({...window.history.state,scroll:window.scrollY},'',window.location.href)
 window.history.pushState({lotusWarehouse:true,screen:next},'',window.location.href)
 window.scrollTo(0,0)
},{flush:'sync'})
function connection(){online.value=navigator.onLine}
function installedEvent(){installed.value=true}
async function bootstrap(){
 busy.value=true;error.value=''
 try{
  session.value=await stockAPI('bootstrap')
  setCSRF(session.value.csrf_token)
  company.value=session.value.companies[0]?.name||''
  if(!company.value)throw Error('Tài khoản chưa được cấp công ty.')
  await reloadSetup()
 }catch(e){error.value=e.message}finally{busy.value=false}
}
async function reloadSetup(){
 setup.value=await buyingAPI('setup',{company:company.value})
 warehouse.value=warehouses.value[0]?.name||''
 historyWarehouse.value=warehouse.value
 inventoryWarehouse.value=warehouse.value
 employees.value=await employeeAPI('employee_choices',{company:company.value}).catch(()=>[])
}
async function changeCompany(next){
 if(!next||next===company.value||busy.value||saving.value||!await confirmLeave())return
 clear();busy.value=true
 const old=company.value
 try{
  const data=await buyingAPI('setup',{company:next})
  const nextEmployees=await employeeAPI('employee_choices',{company:next}).catch(()=>[])
  company.value=next;setup.value=data;employees.value=nextEmployees
  warehouse.value=data.warehouses?.[0]?.name||''
  historyWarehouse.value=warehouse.value;inventoryWarehouse.value=warehouse.value
  historyRows.value=[];inventoryRows.value=[];movementRows.value=[];pending.value=[]
  screen.value='home'
 }catch(e){company.value=old;error.value=e.message}finally{busy.value=false}
}
function changeWorkWarehouse(value){
 warehouse.value=value
 historyWarehouse.value=value;inventoryWarehouse.value=value
 warehouseChanged()
}
function start(kindName){
 clear();lastPostedDocument.value=null;order.value=null;selectedOrder.value=null
 if(!setup.value)return
 kind.value=kindName
 form.value={kind:kindName,posting_date:today(),source:warehouse.value,target:kindName==='transfer'?'':warehouse.value,
  receiver_employee:'',notes:'',receipt_reason:'',supplier:'',lines:[blank()],client_event_id:key()}
 rememberForm(form.value)
 screen.value='stock-form'
}
function startRequest(){
  lastPostedDocument.value=null
 clear();form.value=null;order.value=null;selectedOrder.value=null
 requestForm.value={warehouse:warehouse.value,expected_date:today(),notes:'',items:[blank()]}
 rememberForm(requestForm.value)
 screen.value='request-form'
}
async function saveRequest(){
 if(!online.value||saving.value||!requestForm.value)return
 const f=requestForm.value
 if(!f.warehouse||!f.expected_date||!validLines(f.items)){error.value='Chọn kho, ngày cần hàng, tên hàng và số lượng hợp lệ.';return}
 saving.value=true;clear()
 try{
  const result=await call('lotus_farm.purchasing.create_request',{company:company.value,warehouse:f.warehouse,
   expected_date:f.expected_date,notes:f.notes,items:f.items.map(r=>({item:r.item,qty:Number(r.qty),uom:r.uom}))},true)
  lastPostedDocument.value={doctype:'Material Request',name:result.name}
  requestForm.value=null;screen.value='done';message.value='Đã gửi đề xuất mua '+result.name+'. Có thể in phiếu theo mẫu mới ngay bên dưới.'
 }catch(e){error.value=safeError(e)}finally{saving.value=false}
}
async function startBuying(){
 clear();lastPostedDocument.value=null;form.value=null;selectedOrder.value=null
 order.value=newPurchaseDraft(warehouse.value,today())
 quote.value=null;failedQuote.value=false;savedPurchase.value=null;selectedPurchaseRequest.value='';purchaseRequests.value=[]
 rememberForm(order.value);screen.value='buy-form'
 const requestedCompany=company.value,requestedDraft=order.value
 try{const rows=await call('lotus_farm.purchasing.requests',{company:requestedCompany});if(company.value===requestedCompany&&order.value===requestedDraft)purchaseRequests.value=rows}
 catch(e){if(company.value===requestedCompany&&order.value===requestedDraft)error.value=safeError(e)}
}
function usePurchaseRequest(name){selectedPurchaseRequest.value=name;order.value=purchaseFromRequest(order.value,purchaseRequests.value.find(r=>r.name===name))}
function startSupplier(){
 if(!setup.value?.can_create_supplier||saving.value||!online.value)return
 supplierForm.value={name:'',supplier_id:'',phone:'',contact:'',notes:''};supplierInitial=JSON.stringify(supplierForm.value);screen.value='supplier-form'
}
async function viewSavedPurchase(){if(await confirmLeave())await inspectHistory({name:order.value.name,doctype:'Purchase Order'})}
function searchMatches(r){
 const q=String(r.query||'').trim().toLocaleLowerCase('vi')
 if(!q)return []
 return items.value.filter(i=>i.item_name.toLocaleLowerCase('vi').includes(q)||i.name.toLocaleLowerCase('vi').includes(q)).slice(0,6)
}
function queryChanged(r){if(r.item&&r.query!==iname(r.item))r.item=''}
function chooseItem(r,i){r.item=i.name;r.query=i.item_name;r.uom=i.stock_uom;r.stock_uom=i.stock_uom;r.uoms=(setup.value?.conversions||[]).filter(u=>u.parent===i.name)}
// AI-read delivery note / invoice (Nhập không theo đơn): fill supplier, reason and lines; the photo becomes evidence after saving.
function applyDocument(result,stored){
 const f=form.value;if(!f)return
 if(result.supplier.match)f.supplier=result.supplier.match.name
 if(!f.receipt_reason&&(result.supplier.match||result.supplier.text))f.receipt_reason='Purchase'
 const rows=[]
 for(const line of result.lines.filter(l=>l.item&&items.value.some(i=>i.name===l.item.code))){
  const row=blank();chooseByCode(row,line.item.code)
  row.qty=line.qty||1
  if(line.uom&&unitsFor(row.item).includes(line.uom))row.uom=line.uom
  if(line.rate!=null)row.rate=line.rate
  rows.push(row)
 }
 if(rows.length)f.lines=[...f.lines.filter(r=>r.item),...rows]
 const doc=result.document
 if(!f.notes&&(doc.number||result.supplier.text))f.notes=['Theo chứng từ',doc.number&&'số '+doc.number,doc.date&&'ngày '+doc.date.split('-').reverse().join('/'),result.supplier.text&&'của '+result.supplier.text].filter(Boolean).join(' ')
 f.ai_files=[...(f.ai_files||[]),stored.file_url]
}
function chooseByCode(row,code){
 const item=items.value.find(i=>i.name===code)
 if(item)chooseItem(row,item)
 else {row.item='';row.query='';row.uom=''}
}
function unitsFor(item){
 const base=items.value.find(i=>i.name===item)?.stock_uom
 return [base,...(setup.value?.conversions||[]).filter(i=>i.parent===item).map(i=>i.uom)].filter((x,i,a)=>x&&a.indexOf(x)===i)
}
function validLines(lines){return lines.length>0&&lines.every(r=>r.item&&unitsFor(r.item).includes(r.uom)&&String(r.qty).trim()!==''&&Number.isFinite(Number(r.qty))&&Number(r.qty)>0&&(!String(r.rate).trim()||Number.isFinite(Number(r.rate))&&Number(r.rate)>=0))}
async function saveStock(){
 if(!online.value||saving.value||!form.value)return
 const f=form.value
 if(!validLines(f.lines)){error.value='Chọn đúng tên hàng và số lượng lớn hơn 0.';return}
 if(f.kind==='transfer'&&(!f.target||f.source===f.target)){error.value='Kho nhận phải khác kho xuất.';return}
 if(f.kind==='issue'&&(!f.receiver_employee||f.lines.some(r=>!String(r.area).trim()))){error.value='Chọn người nhận và nhập lô hoặc nơi sử dụng.';return}
 error.value='';saving.value=true
 try{
  if(f.kind==='receipt'){const message=await receiptReasonFields.value.validate(f.lines);if(message)throw Error(message)}
  const result=await stockAPI('create_draft',{
   company:company.value,kind:f.kind,posting_date:f.posting_date,source:f.source,target:f.target,
   issue_mode:'Manual',receiver_employee:f.receiver_employee,notes:f.notes,client_event_id:f.client_event_id,
   receipt_reason:f.kind==='receipt'?f.receipt_reason:undefined,supplier:f.kind==='receipt'?f.supplier:undefined,
   lines:f.lines.map(r=>({item:r.item,qty:Number(r.qty),uom:r.uom,rate:Number(r.rate||0),area:r.area}))
  },true)
  createdDoc.value=result
  // The photo read by AI is kept as evidence of the new draft.
  for(const file_url of f.ai_files||[])try{await call('lotus_farm.stock_attachments.attach',{doctype:result.doctype,name:result.name,file_url},true)}catch{}
  createdDocDetails.value=await stockAPI('document',{doctype:result.doctype,name:result.name})
  confirmed.value=false;screen.value='stock-review'
 }catch(e){error.value=safeError(e)}
 finally{saving.value=false}
}
async function postStock(){
 if(!confirmed.value||!online.value||saving.value||!createdDocDetails.value)return
 saving.value=true;error.value=''
 try{
  const d=createdDocDetails.value
  await stockAPI('submit_document',{doctype:d.doctype,name:d.name,modified:d.modified},true)
   lastPostedDocument.value={doctype:d.doctype,name:d.name}
  screen.value='done';message.value='Đã ghi sổ. Số lượng trong kho được cập nhật.'
 }catch(e){error.value=safeError(e)}finally{saving.value=false}
}
async function addSupplier(){
 if(!online.value||saving.value||!supplierForm.value?.name?.trim())return
 saving.value=true;error.value=''
 try{
  const result=await call('lotus_farm.purchasing.save_supplier',supplierForm.value,true)
  supplierForm.value.supplier_id=result.name
  const data=await buyingAPI('setup',{company:company.value});setup.value=data
  order.value.supplier=result.name;supplierForm.value=null
  screen.value='buy-form'
  if(navigationReady)window.history.replaceState({lotusWarehouse:true,screen:'buy-form'},'',window.location.href)
 }catch(e){error.value=safeError(e)}finally{saving.value=false}
}
async function saveBuying(){
 if(!online.value||saving.value||!order.value||order.value.name||savedPurchase.value)return
 saving.value=true;error.value=''
 try{
  const result=await savePurchaseDraft({company:company.value,draft:order.value,catalog:setup.value,quote:quote.value,
   save:args=>buyingAPI('save_order',args,true),upload,
   onSaved:result=>{order.value.name=result.name;savedPurchase.value={...result,quoteError:''}}})
  savedPurchase.value=result;failedQuote.value=!!result.quoteError
 }catch(e){error.value=safeError(e)}finally{saving.value=false}
}
async function retryQuote(){
 if(!online.value||saving.value||!savedPurchase.value?.name||!quote.value)return
 saving.value=true;error.value=''
 try{await retryPurchaseQuote({saved:savedPurchase.value,quote:quote.value,upload});failedQuote.value=false;savedPurchase.value={...savedPurchase.value,quoteError:''}}
 catch(e){error.value='Báo giá chưa tải được: '+e.message}finally{saving.value=false}
}
async function startReceiving(){
 if(!setup.value)return
 clear();lastPostedDocument.value=null;form.value=null;order.value=null;pendingQuery.value='';pendingStart.value=0;selectedOrder.value=null
 screen.value='choose-order';await loadPending()
}
async function loadPending(reset=false){
 if(!company.value)return
 if(reset)pendingStart.value=0
 const request=++pendingRequest
 loadingPending.value=true;error.value=''
 try{
  const result=await buyingAPI('orders',{company:company.value,warehouse:warehouse.value,
   status:'pending',search:pendingQuery.value,start:pendingStart.value})
  if(request!==pendingRequest)return
  pending.value=result.rows||[];pendingMore.value=!!result.has_more
 }catch(e){if(request===pendingRequest){error.value=e.message||'Chưa tải được đơn chờ hàng.';pending.value=[]}}
 finally{if(request===pendingRequest)loadingPending.value=false}
}
async function showOrder(name){
 if(busy.value||saving.value)return
 const request=++detailRequest,origin=screen.value,scope=company.value
 busy.value=true;error.value=''
 try{
  const detail=await buyingAPI('order_detail',{name})
  if(request!==detailRequest||screen.value!==origin||company.value!==scope)return
  selectedOrder.value=detail
  receiveQty.value={};receiveDate.value=today();receiveKey.value=key()
  postedReceipt.value=null;confirmed.value=false
  screen.value='receive-form'
 }catch(e){if(screen.value===origin&&company.value===scope)error.value=e.message}finally{if(request===detailRequest)busy.value=false}
}
async function createReceipt(){
 if(!online.value||saving.value)return
 if(!receiveDate.value){error.value='Chọn ngày hàng về.';return}
 if(!receiptCheck.value.valid){error.value=receiptCheck.value.reason;return}
 if(!Object.keys(receivedQuantities.value).length){error.value='Nhập số thực nhận của ít nhất một mặt hàng.';return}
 saving.value=true;error.value=''
 try{
  const result=await receivingAPI('receive_order',{
   name:selectedOrder.value.name,posting_date:receiveDate.value,
   quantities:receivedQuantities.value,client_event_id:receiveKey.value
  },true)
  postedReceipt.value=await receivingAPI('purchase_receipt',{name:result.name})
  confirmed.value=false;screen.value='receive-review'
 }catch(e){error.value=safeError(e)}
 finally{saving.value=false}
}
async function postReceipt(){
 if(!confirmed.value||!postedReceipt.value||!online.value||saving.value)return
 saving.value=true;error.value=''
 try{
  await receivingAPI('receipt_action',{name:postedReceipt.value.name,modified:postedReceipt.value.modified,action:'submit'},true)
  lastPostedDocument.value={doctype:'Purchase Receipt',name:postedReceipt.value.name}
   screen.value='done';message.value='Đã nhập kho '+postedReceipt.value.name+'. Số còn chờ được cập nhật.'
 }catch(e){error.value=safeError(e)}finally{saving.value=false}
}
function again(){
 clear()
 if(order.value?.name&&screen.value==='done'){startBuying();return}
 if(selectedOrder.value&&screen.value==='done'){startReceiving();return}
 if(form.value&&screen.value==='done'){start(kind.value);return}
 home()
}

const stockPrintURL=(doctype,name)=>'/lotus/in-phieu?'+new URLSearchParams({doctype,name})
const statusLabel=code=>code===0?'Nháp':code===1?'Đã ghi sổ':'Đã hủy'
const shortDate=value=>formatDate(value)
async function loadHistory(reset=false){
 if(!company.value)return
 if(reset)historyStart.value=0
 const request=++historyRequest
 loadingHistory.value=true;error.value=''
 try{
  const isOrder=historyMode.value==='orders'
  const res=isOrder?await buyingAPI('orders',{company:company.value,warehouse:historyWarehouse.value,search:historySearch.value,start:historyStart.value}):await stockAPI('documents',{company:company.value,warehouse:historyWarehouse.value,search:historySearch.value,start:historyStart.value})
  if(request!==historyRequest)return
  historyRows.value=isOrder?(res.rows||[]).map(row=>({...row,doctype:'Purchase Order',kind:'Đơn mua',posting_date:row.expected_date})):(res.rows||[])
  historyMore.value=!!res.has_more
 }catch(e){if(request===historyRequest){error.value=e.message||'Chưa xem được lịch sử.';historyRows.value=[]}}
 finally{if(request===historyRequest)loadingHistory.value=false}
}
async function inspectHistory(row){
 if(busy.value||saving.value)return
 const request=++detailRequest,origin=screen.value,scope=company.value
 busy.value=true;error.value=''
 try{
  const detail=row.doctype==='Purchase Order'
   ?await buyingAPI('order_detail',{name:row.name})
   :row.doctype==='Purchase Receipt'
    ?await receivingAPI('purchase_receipt',{name:row.name})
    :await stockAPI('document',{doctype:row.doctype,name:row.name})
  if(request!==detailRequest||screen.value!==origin||company.value!==scope)return
  historyDetail.value=detail
  historyDetail.value.doctype=row.doctype
  screen.value='history-detail'
 }catch(e){if(screen.value===origin&&company.value===scope)error.value=e.message||'Chưa xem được phiếu.'}
 finally{if(request===detailRequest)busy.value=false}
}
async function loadInventory(reset=false){
 if(!company.value)return
 if(reset){inventoryStart.value=0;movementStart.value=0}
 if(inventoryMode.value==='moves')return loadMovement()
 const request=++inventoryRequest
 loadingInventory.value=true;error.value=''
 try{
  const res=await stockAPI('overview',{company:company.value,warehouse:inventoryWarehouse.value,
   search:inventorySearch.value,start:inventoryStart.value})
  if(request!==inventoryRequest)return
  inventoryRows.value=res.items||[];inventoryMore.value=!!res.has_more
  inventoryTotal.value=res.total_count||0
 }catch(e){if(request===inventoryRequest){error.value=e.message||'Chưa xem được tồn kho.';inventoryRows.value=[]}}
 finally{if(request===inventoryRequest)loadingInventory.value=false}
}
async function loadMovement(){
 const request=++inventoryRequest
 loadingInventory.value=true;error.value=''
 try{
  const res=await stockAPI('movements',{company:company.value,warehouse:inventoryWarehouse.value,
    search:inventorySearch.value,start:movementStart.value})
  if(request!==inventoryRequest)return
  movementRows.value=res.rows||[];movementMore.value=!!res.has_more
 }catch(e){if(request===inventoryRequest){error.value=e.message||'Chưa có quyền xem lịch sử xuất nhập.';movementRows.value=[]}}
 finally{if(request===inventoryRequest)loadingInventory.value=false}
}
function switchInventory(mode){if(mode===inventoryMode.value)return;inventoryMode.value=mode;inventoryStart.value=0;movementStart.value=0;loadInventory(true)}
function warehouseChanged(){if(screen.value==='history')loadHistory(true);if(screen.value==='inventory')loadInventory(true)}
function switchHistory(mode){if(historyMode.value===mode)return;historyMode.value=mode;historyRows.value=[];loadHistory(true)}
async function logout(){
 if(!await confirmLeave())return
 if(!await askLeave('Đăng xuất khỏi Kho Lotus?'))return
 saving.value=true;error.value=''
 try{
  await logoutPwa('warehouse',{csrf:session.value?.csrf_token||'',home:'/warehouse'})
 }catch(e){error.value='Không đăng xuất được: '+e.message}
 finally{saving.value=false}
}
onMounted(()=>{
 window.history.replaceState({...window.history.state,lotusWarehouseRoot:true},'',window.location.href)
 window.history.pushState({lotusWarehouse:true,screen:'home'},'',window.location.href)
 window.addEventListener('popstate',onSystemBack)
 window.addEventListener('beforeunload',beforeUnload)
 navigationReady=true
 installed.value=window.matchMedia('(display-mode:standalone)').matches||navigator.standalone===true
 window.addEventListener('online',connection);window.addEventListener('offline',connection)
 window.addEventListener('appinstalled',installedEvent)
 navigator.serviceWorker?.addEventListener('controllerchange',onWorkerChange)
 bootstrap().then(()=>{
  const qs=new URLSearchParams(location.search)
  const name=qs.get('doc'),doctype=qs.get('doctype')||'Purchase Order'
  if(session.value&&name&&['Stock Entry','Purchase Receipt','Purchase Order'].includes(doctype))
   inspectHistory({name,doctype})
 })
})
onUnmounted(()=>{
 finishLeave(false)
 navigationReady=false;clearTimeout(searchTimer)
 window.removeEventListener('popstate',onSystemBack)
 window.removeEventListener('beforeunload',beforeUnload)
 navigator.serviceWorker?.removeEventListener('controllerchange',onWorkerChange)
 window.removeEventListener('online',connection);window.removeEventListener('offline',connection)
 window.removeEventListener('appinstalled',installedEvent)
})
</script>

<template>
 <LotusMobileShell app="warehouse" :user="session?.user||''" :refresh="pullRefresh" :refreshable="rootScreens.has(screen)" class="lotus-mobile" :class="{'mobile-keyboard-open':keyboard}"
  :title="mobileTitle" :tabs="mobileTabs" :active-tab="activeTab"
  :back="!baseTabs.includes(screen)" :keyboard-open="keyboard" :disabled="saving"
  @back="appBack" @navigate="goTab"  @touchstart.passive="swipeStart" @touchmove="swipeMove" @touchend="swipeEnd" @touchcancel="swipeCancel">
<main class="mobile-container" id="lotus-content" :aria-busy="isLoading">
   <LotusMobileFeedback v-if="!online" kind="warning">Mất mạng — chưa thể lưu phiếu.</LotusMobileFeedback>
   <LotusMobileFeedback v-if="error" kind="error">{{error}}</LotusMobileFeedback>
   <LotusMobileFeedback v-if="message&&screen!=='done'" kind="success">{{message}}</LotusMobileFeedback>
   <p v-if="updateReady" class="mobile-message mobile-update" role="status">Có bản Kho Lotus mới. <LotusMobileButton type="button" @click="refreshApp">Cập nhật ngay</LotusMobileButton></p>
   <LotusMobileFeedback v-if="isLoading" kind="loading">Đang tải dữ liệu…</LotusMobileFeedback>

   <template v-if="screen==='home'">
    
    <MobileLinkField v-if="(session?.companies?.length||0)>1" label="Công ty" :model-value="company" :options="companyOptions" :searchable="false" placeholder="Chọn công ty" @update:modelValue="v=>changeCompany(v)"/>
    <MobileLinkField label="Kho đang làm việc" :model-value="warehouse" :options="storeOptions" :searchable="false" :disabled="!setup" placeholder="Tìm kho…" @update:modelValue="v=>{if(v)changeWorkWarehouse(v)}"/>
    <div class="mobile-actions" aria-label="Thao tác Kho">
     <LotusMobileAction v-if="setup?.can_create" primary icon="cart-o" title="Tạo đơn mua" :disabled="!setup" @select="startBuying"/>
     <LotusMobileAction v-if="setup?.can_request" icon="notes-o" title="Đề nghị mua" @select="startRequest"/>
     <LotusMobileAction v-if="allowed('Purchase Receipt')" icon="logistics" title="Nhập theo đơn" :disabled="!setup" @select="startReceiving"/>
     <LotusMobileAction v-if="allowed('Stock Entry')" icon="upgrade" title="Xuất kho" :disabled="!setup" @select="start('issue')"/>
     <LotusMobileAction v-if="allowed('Stock Entry')" icon="exchange" title="Chuyển kho" :disabled="!setup" @select="start('transfer')"/>
     <LotusMobileAction v-if="allowed('Stock Entry')" icon="down" title="Nhập không theo đơn" :disabled="!setup" @select="start('receipt')"/>
    </div>
    <div class="mobile-install"><LotusMobileButton v-if="!installed" type="button" @click="openSetup">＋ Thêm Kho Lotus lên màn hình chính</LotusMobileButton></div>
   </template>

   <template v-if="screen==='stock-form'&&form">
    <p v-if="kind==='receipt'" class="mobile-subtle">Chỉ dùng khi hàng về không có đơn mua. Hàng đặt mua hãy dùng Nhập theo đơn.</p>
    <form @submit.prevent="saveStock"><fieldset class="mobile-form-fields" :disabled="saving">
     <DocumentReader v-if="kind==='receipt'" mobile camera label="Chụp phiếu giao hàng / hóa đơn" :disabled="saving||!online" @read="applyDocument"/>
     <StockReceiptReason v-if="kind==='receipt'" ref="receiptReasonFields" v-model:reason="form.receipt_reason" v-model:supplier="form.supplier" mobile/>
     <LotusMobileInput label="Ngày" type="date" v-model="form.posting_date" required/>
     <MobileLinkField v-if="kind!=='receipt'" label="Kho xuất" v-model="form.source" :options="storeOptions" :searchable="false" placeholder="Chọn kho xuất…" required/>
     <MobileLinkField v-if="kind!=='issue'" :label="(kind==='transfer'?'Kho nhận':'Kho nhập')" v-model="form.target" :options="storeOptions" :searchable="false" placeholder="Chọn kho nhận…" required/>
     <MobileLinkField v-if="kind==='issue'" label="Người nhận hàng" v-model="form.receiver_employee" :options="employeeOptions" placeholder="Gõ tên người nhận…" required/>
     <h2>Hàng cần {{kind==='issue'?'xuất':kind==='transfer'?'chuyển':'nhập'}}</h2>
     <div class="mobile-line" v-for="(r,i) in form.lines" :key="r._key">
      <div class="mobile-line-title"><strong>Hàng {{i+1}}</strong><LotusMobileButton v-if="form.lines.length>1" type="button" @click="form.lines.splice(i,1)">Xóa</LotusMobileButton></div>
      <MobileLinkField label="Tên hàng" :model-value="r.item" :options="itemOptions" placeholder="Gõ tên hoặc mã hàng…" required @update:modelValue="code=>chooseByCode(r,code)"/>
      <div class="mobile-qty-grid"><LotusMobileInput label="Số lượng" v-model="r.qty" type="number" min="0.000001" step="any" inputmode="decimal" required/><LotusMobileSelect label="Đơn vị" v-model="r.uom" :disabled="kind==='transfer'||!r.item"><option v-for="u in unitsFor(r.item)" :key="u" :value="u">{{unitLabel(u)}}</option></LotusMobileSelect></div>
      <small v-if="kind==='issue'&&r.item&&r.uom!==r.stock_uom" class="mobile-subtle">Trừ tồn: {{fmt(stockQuantity(r))}} {{unitLabel(r.stock_uom)}}</small>
      <LotusMobileInput v-if="kind==='receipt'" :label="form.receipt_reason==='Purchase'?'Đơn giá mua':'Đơn giá (nếu có)'" v-model="r.rate" type="money" :required="form.receipt_reason==='Purchase'"/>
      <LotusMobileInput v-if="kind==='issue'||kind==='receipt'&&form.receipt_reason==='Recovery'" :label="(kind==='receipt'?'Lô thu hồi vật tư':'Lô / nơi sử dụng')" v-model="r.area" placeholder="Ví dụ: Lô A01" required/>
     </div>
     <LotusMobileButton type="button" class="mobile-add" @click="form.lines.push(blank())">＋ Thêm hàng</LotusMobileButton>
     <LotusMobileInput v-model="form.notes" label="Ghi chú (không bắt buộc)" type="textarea" placeholder="Ghi thêm nếu cần…"/>
     <LotusMobileButton type="submit" class="mobile-submit" :disabled="saving||!online">{{saving?'Đang lưu…':'Lưu phiếu →'}}</LotusMobileButton>
    </fieldset></form>
   </template>

   <template v-if="screen==='stock-review'&&createdDocDetails">
    
    <div class="mobile-summary"><span>Số phiếu <b>{{createdDocDetails.name}}</b></span><span>Ngày <b>{{createdDocDetails.posting_date}}</b></span></div>
    <div class="mobile-list-card" v-for="(r,i) in createdDocDetails.items" :key="i"><strong>{{r.item_name}}</strong><div class="mobile-inline"><span>{{wname(r.source)}} {{r.source&&r.target?'→':''}} {{wname(r.target)}}</span><b>{{fmt(r.qty)}} {{unitLabel(r.uom)}}</b></div><small v-if="kind==='issue'&&r.uom!==r.stock_uom">Trừ tồn: {{fmt(r.stock_qty)}} {{unitLabel(r.stock_uom)}}</small></div>
    <StockEvidence class="mobile-evidence" :doctype="createdDocDetails.doctype" :name="createdDocDetails.name" :title="createdDocDetails.kind==='Material Issue'?'Ảnh bằng chứng xuất kho':'Ảnh hàng, phiếu giao hàng'"/>
    <div class="mobile-confirm"><p>Phiếu mới chỉ là nháp. Bấm xác nhận để cập nhật tồn kho.</p><LotusMobileCheck v-model="confirmed" :disabled="saving">Đã kiểm tra đúng hàng và số lượng</LotusMobileCheck><LotusMobileButton class="mobile-submit" type="button" :disabled="!online||saving||!confirmed" @click="postStock">Ghi sổ phiếu</LotusMobileButton></div>
   </template>

   <template v-if="screen==='choose-order'">
    <p class="mobile-subtle">Chỉ hiện đơn đã xác nhận và chưa nhận đủ.</p>
    <MobileLiveSearch v-model="pendingQuery" :options="pendingSuggestions" :loading="loadingPending" placeholder="Gõ tên nhà cung cấp hoặc số đơn…" @select="r=>showOrder(r.value)"/>
    <LotusMobileButton v-for="r in pending" :key="r.name" class="mobile-list-card clickable" type="button" @click="showOrder(r.name)"><strong>{{r.supplier_name}}</strong><small>{{r.name}} · Hẹn {{r.expected_date}}</small><div class="mobile-inline"><span>{{r.remaining_lines}} mặt hàng còn chờ</span><b>Nhận hàng <Icon name="arrow" class="lotus-pwa-inline-icon" aria-hidden="true"/></b></div></LotusMobileButton>
    <p v-if="!loadingPending&&!pending.length&&!error" class="mobile-empty">Chưa có đơn nào đang chờ hàng.</p>
    <div class="mobile-pages"><LotusMobileButton type="button" :disabled="pendingStart===0||loadingPending" @click="pendingStart-=50;loadPending()">← Trước</LotusMobileButton><LotusMobileButton type="button" :disabled="!pendingMore||loadingPending" @click="pendingStart+=50;loadPending()">Sau →</LotusMobileButton></div>
   </template>

   <template v-if="screen==='receive-form'&&selectedOrder">
    <div class="mobile-summary"><span>Nhà cung cấp <b>{{selectedOrder.supplier_name}}</b></span><span>Đơn <b>{{selectedOrder.name}}</b></span></div>
    <LotusMobileInput label="Ngày hàng về" v-model="receiveDate" type="date" :disabled="saving" required/>
    <div v-for="r in selectedLines" :key="r.line" class="mobile-line"><strong>{{r.item_name}}</strong><small>Chưa nhận: {{fmt(r.remaining_qty)}} {{unitLabel(r.uom)}}</small><LotusMobileInput :label="'Số lượng thực nhận ('+(unitLabel(r.uom))+')'" v-model="receiveQty[r.line]" :disabled="saving" type="number" inputmode="decimal" min="0" :max="r.remaining_qty" step="any" placeholder="0"/></div>
    <p v-if="!receiptCheck.valid" class="mobile-message danger" role="alert">{{receiptCheck.reason}}</p>
    <LotusMobileButton type="button" class="mobile-submit" :disabled="!online||saving||!receiptCheck.valid||!Object.keys(receivedQuantities).length" @click="createReceipt">{{saving?'Đang lưu…':'Lưu hàng đã nhận →'}}</LotusMobileButton>
   </template>

   <template v-if="screen==='receive-review'&&postedReceipt">
    
    <div class="mobile-summary"><span>Phiếu <b>{{postedReceipt.name}}</b></span><span>Đơn mua <b>{{selectedOrder?.name}}</b></span></div>
    <div class="mobile-list-card" v-for="r in selectedLines.filter(r=>Number(receiveQty[r.line])>0)" :key="r.line"><strong>{{r.item_name}}</strong><div class="mobile-inline"><span>Thực nhận</span><b>{{fmt(receiveQty[r.line])}} {{unitLabel(r.uom)}}</b></div></div>
    <div class="mobile-confirm"><p>Phiếu đang là nháp, tồn kho chưa tăng.</p><LotusMobileCheck v-model="confirmed" :disabled="saving">Đã kiểm tra số thực nhận</LotusMobileCheck><LotusMobileButton type="button" class="mobile-submit" :disabled="saving||!online||!confirmed" @click="postReceipt">Ghi sổ nhập kho</LotusMobileButton></div>
   </template>

   <template v-if="screen==='request-form'&&requestForm">
    <form @submit.prevent="saveRequest"><fieldset class="mobile-form-fields" :disabled="saving">
     <MobileLinkField label="Kho cần hàng" v-model="requestForm.warehouse" :options="storeOptions" :searchable="false" required/>
     <LotusMobileInput label="Ngày cần hàng" type="date" v-model="requestForm.expected_date" required/>
     <div v-for="(r,i) in requestForm.items" :key="r._key" class="mobile-line">
      <div class="mobile-line-title"><strong>Hàng {{i+1}}</strong><LotusMobileButton v-if="requestForm.items.length>1" type="button" @click="requestForm.items.splice(i,1)">Xóa</LotusMobileButton></div>
      <MobileLinkField label="Tên hàng" :model-value="r.item" :options="itemOptions" placeholder="Gõ tên hàng…" required @update:modelValue="v=>chooseByCode(r,v)"/>
      <div class="mobile-qty-grid"><LotusMobileInput label="Số lượng" v-model="r.qty" type="number" inputmode="decimal" min="0.000001" step="any" required/>
       <LotusMobileSelect label="Đơn vị" v-model="r.uom"><option v-for="u in unitsFor(r.item)" :key="u" :value="u">{{unitLabel(u)}}</option></LotusMobileSelect></div>
     </div>
     <LotusMobileButton class="mobile-add" type="button" @click="requestForm.items.push(blank())">+ Thêm hàng</LotusMobileButton>
     <LotusMobileInput label="Ghi chú" type="textarea" v-model="requestForm.notes" rows="2" placeholder="Lý do cần mua, thời gian cần…"/>
     <LotusMobileButton type="submit" class="mobile-submit" :disabled="saving||!online">Gửi đề nghị mua</LotusMobileButton>
    </fieldset></form>
   </template>

   <template v-if="screen==='buy-form'&&order">
    <MobilePurchaseOrderForm v-model="order" v-model:quote="quote" :saved="savedPurchase" :items="items" :conversions="setup?.conversions||[]"
     :warehouses="warehouses" :suppliers="suppliers" :requests="purchaseRequests" :selected-request="selectedPurchaseRequest" :currency="setup?.currency||'VND'"
     :can-create-supplier="!!setup?.can_create_supplier" :saving="saving" :online="online"
     @update:selectedRequest="usePurchaseRequest" @submit="saveBuying" @add-supplier="startSupplier" @retry-quote="retryQuote" @view-saved="viewSavedPurchase" @new-order="startBuying"/>
   </template>
   <MobileSupplierForm v-if="screen==='supplier-form'&&supplierForm" v-model="supplierForm" :saving="saving" :online="online" @submit="addSupplier"/>

   <template v-if="screen==='history'">
    
    <div class="mobile-switcher" role="group" aria-label="Xem loại chứng từ">
     <LotusMobileButton type="button" :class="{active:historyMode==='stock'}" @click="switchHistory('stock')">Phiếu kho</LotusMobileButton>
     <LotusMobileButton type="button" :class="{active:historyMode==='orders'}" @click="switchHistory('orders')">Đơn mua</LotusMobileButton>
    </div>
    <MobileLinkField label="Chỉ xem kho" v-model="historyWarehouse" :options="[{value:'',label:'Tất cả kho'},...storeOptions]" :searchable="false" placeholder="Lọc theo kho…" @update:modelValue="loadHistory(true)"/>
    <MobileLiveSearch v-model="historySearch" :options="historySuggestions" :loading="loadingHistory" :placeholder="historyMode==='orders'?'Gõ nhà cung cấp hoặc số đơn…':'Gõ số phiếu…'" @select="pickHistorySuggestion"/>
    <LotusMobileButton v-for="entry in historyRows" :key="entry.name" class="mobile-list-card clickable" type="button" @click="inspectHistory(entry)">
     <div class="mobile-history-top"><strong>{{entry.doctype==='Purchase Order'?entry.supplier_name||'Đơn mua':entry.kind}}</strong><span :class="['mobile-status',entry.docstatus===1?'posted':'draft']">{{entry.doctype==='Purchase Order'?entry.status:statusLabel(entry.docstatus)}}</span></div>
     <small>{{entry.name}}</small>
     <div class="mobile-inline"><span>{{entry.doctype==='Purchase Order'?'Hẹn '+shortDate(entry.expected_date):shortDate(entry.posting_date)}}</span><span>Chi tiết <Icon name="arrow" class="lotus-pwa-inline-icon" aria-hidden="true"/></span></div>
    </LotusMobileButton>
    <p v-if="!loadingHistory&&!historyRows.length&&!error" class="mobile-empty">Chưa có phiếu phù hợp.</p>
    <div class="mobile-pages"><LotusMobileButton :disabled="!historyStart||loadingHistory" @click="historyStart-=50;loadHistory()">← Trước</LotusMobileButton><LotusMobileButton :disabled="!historyMore||loadingHistory" @click="historyStart+=50;loadHistory()">Sau →</LotusMobileButton></div>
   </template>

   <template v-if="screen==='history-detail'&&historyDetail">
    
    <MobilePurchaseOrderDetail v-if="historyDetail.doctype==='Purchase Order'" :order="historyDetail" :currency="setup?.currency||'VND'" :warehouses="warehouses"/>
    <template v-else>
    <div class="mobile-summary">
     <span>Số phiếu <b>{{historyDetail.name}}</b></span>
     <span>Trạng thái <b>{{historyDetail.doctype==='Purchase Order'?historyDetail.status:statusLabel(historyDetail.docstatus)}}</b></span>
     <span v-if="historyDetail.doctype==='Purchase Order'">Nhà cung cấp <b>{{historyDetail.supplier_name}}</b></span>
    </div>
    <div v-for="(line,i) in historyDetail.items||[]" :key="i" class="mobile-list-card">
     <strong>{{line.item_name}}</strong>
     <div class="mobile-inline"><span>{{wname(line.warehouse||line.source||line.target)}}</span><b>{{fmt(line.qty)}} {{unitLabel(line.uom)}}</b></div>
     <small v-if="historyDetail.doctype==='Purchase Order'">Còn chờ: {{fmt(line.remaining_qty)}} {{unitLabel(line.uom)}}</small>
    </div>
    </template>
    <SigningPanel v-if="['Stock Entry','Stock Reconciliation','Purchase Receipt'].includes(historyDetail.doctype)&&historyDetail.docstatus===1" :doctype="historyDetail.doctype" :name="historyDetail.name" :company="company" :online="online" @notice="message=$event" @error="error=$event"/>
    <a v-if="['Stock Entry','Stock Reconciliation','Purchase Receipt'].includes(historyDetail.doctype)&&historyDetail.docstatus===1" class="lotus-pwa-print-link" :href="stockPrintURL(historyDetail.doctype,historyDetail.name)" target="_blank" rel="noopener noreferrer" aria-label="In phiếu kho">In phiếu / Lưu PDF <Icon name="share-o" class="lotus-pwa-inline-icon" aria-hidden="true"/></a>
     <LotusMobileButton v-if="historyDetail.doctype==='Purchase Order'&&historyDetail.can_receive&&historyDetail.items?.some(r=>Number(r.remaining_qty)>0)" type="button" class="mobile-submit" @click="showOrder(historyDetail.name)">Nhận hàng theo đơn →</LotusMobileButton>
    <p v-if="historyDetail.doctype==='Purchase Order'&&historyDetail.docstatus===0" class="mobile-subtle">Đơn đang là nháp. Cần xác nhận đơn trước khi nhận hàng.</p>
    <LotusMobileButton class="mobile-add" type="button" @click="appBack">← Về lịch sử</LotusMobileButton>
   </template>

   <template v-if="screen==='inventory'">
    
    <div class="mobile-switcher" role="group" aria-label="Chọn nội dung">
     <LotusMobileButton type="button" :class="{active:inventoryMode==='stock'}" @click="switchInventory('stock')">Tồn kho</LotusMobileButton>
     <LotusMobileButton type="button" :class="{active:inventoryMode==='moves'}" @click="switchInventory('moves')">Nhập / Xuất</LotusMobileButton>
    </div>
    <MobileLinkField label="Chỉ xem kho" v-model="inventoryWarehouse" :options="[{value:'',label:'Tất cả kho'},...storeOptions]" :searchable="false" placeholder="Tìm kho…" @update:modelValue="loadInventory(true)"/>
    <MobileLiveSearch v-model="inventorySearch" :options="inventorySuggestions" :loading="loadingInventory" placeholder="Gõ tên hoặc mã hàng…" @select="pickInventorySuggestion"/>
    <template v-if="inventoryMode==='stock'">
     
     <div v-for="r in inventoryRows" :key="r.name" class="mobile-list-card">
      <strong>{{r.item_name}}</strong><small>{{r.name}}</small>
      <div class="mobile-inline"><span>Đang có</span><b>{{fmt(r.actual_qty)}} {{unitLabel(r.stock_uom)}}</b></div>
     </div>
     <p v-if="!loadingInventory&&!inventoryRows.length&&!error" class="mobile-empty">Chưa có hàng phù hợp.</p>
     <div class="mobile-pages"><LotusMobileButton :disabled="!inventoryStart||loadingInventory" @click="inventoryStart-=50;loadInventory()">← Trước</LotusMobileButton><LotusMobileButton :disabled="!inventoryMore||loadingInventory" @click="inventoryStart+=50;loadInventory()">Sau →</LotusMobileButton></div>
    </template>
    <template v-else>
     <div v-for="r in movementRows" :key="r.name" class="mobile-list-card">
      <strong>{{r.item_name}}</strong><small>{{shortDate(r.posting_date)}} · {{wname(r.warehouse)}}</small>
      <div class="mobile-inline">
       <span>{{r.kind}} · {{r.voucher_no}}</span>
       <b :class="Number(r.in_qty)>0?'mobile-in':'mobile-out'">{{Number(r.in_qty)>0?'+':'−'}}{{fmt(Number(r.in_qty)>0?r.in_qty:r.out_qty)}} {{unitLabel(r.stock_uom)}}</b>
      </div>
      <small>Còn lại: {{fmt(r.qty_after_transaction)}} {{unitLabel(r.stock_uom)}}</small>
     </div>
     <p v-if="!loadingInventory&&!movementRows.length&&!error" class="mobile-empty">Chưa có xuất nhập phù hợp.</p>
     <div class="mobile-pages"><LotusMobileButton :disabled="!movementStart||loadingInventory" @click="movementStart-=50;loadMovement()">← Trước</LotusMobileButton><LotusMobileButton :disabled="!movementMore||loadingInventory" @click="movementStart+=50;loadMovement()">Sau →</LotusMobileButton></div>
    </template>
   </template>

   <template v-if="screen==='profile'">
    
    <section class="mobile-account">
     <div class="mobile-avatar" aria-hidden="true">👤</div>
     <div><strong>{{session?.user||'Đang tải tài khoản…'}}</strong><small>Tài khoản Kho Lotus</small></div>
    </section>
    <div class="mobile-list-card">
     <div class="mobile-profile-row"><span>Công ty</span><strong>{{company||'—'}}</strong></div>
     <div class="mobile-profile-row"><span>Kho đang chọn</span><strong>{{wname(warehouse)}}</strong></div>
    </div>
    <MobileLinkField v-if="(session?.companies?.length||0)>1" label="Đổi công ty" :model-value="company" :options="companyOptions" :searchable="false" @update:modelValue="v=>changeCompany(v)"/>
    <MobileLinkField label="Đổi kho làm việc" :model-value="warehouse" :options="storeOptions" :searchable="false" placeholder="Tìm kho…" @update:modelValue="v=>{if(v)changeWorkWarehouse(v)}"/>
    
    <LotusMobileSignatureSettings :user="session?.user||''"/>
     <LotusMobileButton type="button" @click="openSetup">Cài ứng dụng và thông báo</LotusMobileButton>
    <LotusMobileButton class="mobile-logout" type="button" :disabled="saving" @click="logout">Đăng xuất</LotusMobileButton>
   </template>

   <template v-if="screen==='done'">
    <div class="mobile-done">
     <div class="mobile-done-icon">✓</div>
     
     <p role="status">{{message}}</p>
      <a v-if="lastPostedDocument" class="lotus-pwa-print-link" :href="stockPrintURL(lastPostedDocument.doctype,lastPostedDocument.name)" target="_blank" rel="noopener noreferrer" :aria-label="lastPostedDocument.doctype==='Material Request'?'In phiếu đề xuất mua vật tư':'In phiếu kho vừa ghi sổ'">In phiếu / Lưu PDF <Icon name="share-o" class="lotus-pwa-inline-icon" aria-hidden="true"/></a>
     <LotusMobileButton v-if="failedQuote" type="button" class="mobile-submit" :disabled="saving||!online" icon="replay" @click="retryQuote">{{saving?'Đang tải báo giá…':'Tải lại báo giá'}}</LotusMobileButton>
     <LotusMobileButton type="button" class="mobile-submit" @click="again">＋ Làm phiếu tiếp</LotusMobileButton>
     <LotusMobileButton type="button" class="mobile-add" @click="home">Về trang chủ</LotusMobileButton>
    </div>
   </template>
  </main>
  <LotusMobileDialog ref="leaveDialog" class="mobile-leave-dialog" aria-labelledby="leave-title" @cancel.prevent="finishLeave(false)">
   <div class="mobile-leave-content"><h2 id="leave-title">{{leaveMessage.startsWith('Đăng xuất')?'Đăng xuất':'Rời màn hình?'}}</h2><p>{{leaveMessage}}</p><div><LotusMobileButton type="button" autofocus @click="finishLeave(false)">Ở lại</LotusMobileButton><LotusMobileButton type="button" class="danger" @click="finishLeave(true)">{{leaveMessage.startsWith('Đăng xuất')?'Đăng xuất':'Rời đi'}}</LotusMobileButton></div></div>
  </LotusMobileDialog>

 </LotusMobileShell>
</template>
