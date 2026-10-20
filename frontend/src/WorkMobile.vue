<script setup>
import {formatDate} from './format'
import LotusMobileFeedback from './components/LotusMobileFeedback.vue'
import {Icon} from 'vant'
import {useMobileConfirm} from './use-mobile-confirm'
import LotusMobileFile from './components/LotusMobileFile.vue'
import LotusMobileDialog from './components/LotusMobileDialog.vue'
import LotusMobileSelect from './components/LotusMobileSelect.vue'
import LotusMobileInput from './components/LotusMobileInput.vue'
import LotusMobileButton from './components/LotusMobileButton.vue'
import LotusMobileSignatureSettings from './components/LotusMobileSignatureSettings.vue'
import LotusMobileShell from './components/LotusMobileShell.vue'
import {logoutPwa} from './mobile-push-session'
import LotusMobileAction from './components/LotusMobileAction.vue'
import {computed,onBeforeUnmount,onMounted,ref,watch} from 'vue'
import MobileLinkField from './components/MobileLinkField.vue'
import MobileLiveSearch from './components/MobileLiveSearch.vue'
import {call,consoleAPI,setCSRF,upload} from './api'
import {queueCapture,queueRows,syncCaptures,reconcileCapture,clearSent} from './offline'
import {unitLabel} from './units'
import {stateLabel} from './labels'
import {useMobileViewport} from './use-mobile-viewport'
import {createTabSwipe} from './mobile-swipe'

const {keyboard}=useMobileViewport()
function openSetup(){window.dispatchEvent(new Event('lotus:open-setup'))}
const screen=ref('home'),session=ref(null),farm=ref(''),date=ref(''),day=ref({tasks:[],plans:[]}),history=ref([])
const busy=ref(false),saving=ref(false),loadingHistory=ref(false),error=ref(''),message=ref('')
const online=ref(navigator.onLine),search=ref(''),status=ref('all'),historySearch=ref('')
const selected=ref(null),resultForm=ref(null),photo=ref(null),blockReason=ref(''),assignOptions=ref(null)
const assignTeam=ref(''),assignLines=ref([]),preview=ref(null),rateReason=ref(''),queue=ref([])
const rejection=ref(''),rejectReason=ref('')
const installed=ref(false),discardDialog=ref(null),discardReason=ref(''),discardEntry=ref(null)
const {dialog:leaveDialog,message:leaveMessage,pending:leavePending,ask:askLeave,finish:finishLeave}=useMobileConfirm()
let requestId=0,historyId=0,restoring=false,navigationReady=false
const tabs=['home','history','tasks','profile']
const mobileTabs=[
 {name:'home',label:'Trang chủ',icon:'wap-home-o'},
 {name:'history',label:'Lịch sử',icon:'orders-o'},
 {name:'tasks',label:'Công việc',icon:'todo-list-o'},
 {name:'profile',label:'Tôi',icon:'user-o'}
]
const mobileTitle=computed(()=>screen.value==='home'?'Công việc ngoài vườn':screenTitle.value)

const screenTitle=computed(()=>({home:'Trang chủ',tasks:'Công việc',history:'Lịch sử',profile:'Tôi',detail:'Chi tiết công việc',result:'Ghi kết quả',block:'Báo vướng mắc',assign:'Lập kế hoạch / Giao việc','assign-preview':'Xem lại kế hoạch',queue:'Hàng chờ',done:'Hoàn tất'})[screen.value]||'Công việc ngoài vườn')
const shortDate=value=>formatDate(value)
const rootTab=computed(()=>tabs.includes(screen.value)?screen.value:['detail','result','block'].includes(screen.value)?'tasks':screen.value.startsWith('assign')?'home':'profile')
const farms=computed(()=>(session.value?.farms||[]).map(f=>({value:f.name,label:f.farm_name||f.name})))
const canAssign=computed(()=>!!session.value?.abilities?.['work.assign'])
const canPrepare=computed(()=>!!session.value?.abilities?.['work.prepare'])
const canCapture=computed(()=>!!session.value?.abilities?.['work.result.capture'])
const canVerify=computed(()=>!!session.value?.abilities?.['work.result.verify'])
const canFinalize=computed(()=>!!session.value?.abilities?.['work.result.approve'])
const reviewNote=ref('')
const canApprove=computed(()=>!!session.value?.abilities?.['work.rate.approve'])
const tasks=computed(()=>day.value?.tasks||[])
const needingReview=computed(()=>tasks.value.filter(t=>(t.result_state==='Pending'&&canVerify.value)||(t.result_state==='Verified'&&canFinalize.value)))
const planRows=computed(()=>day.value?.plans||[])
const done=computed(()=>tasks.value.filter(t=>t.status==='Completed').length)
const blocked=computed(()=>tasks.value.filter(t=>t.status==='Blocked').length)
const remaining=computed(()=>tasks.value.length-done.value)
const drafts=computed(()=>planRows.value.filter(p=>p.rate_approval_state==='Pending').length)
const pendingCount=computed(()=>queue.value.filter(r=>!['Sent','Discarded'].includes(r.status)).length)
const pendingLines=computed(()=>new Set(queue.value.filter(r=>!['Sent','Discarded'].includes(r.status)).map(r=>r.event?.values?.work_plan_line).filter(Boolean)))
const fold=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').toLowerCase()
const filteredTasks=computed(()=>tasks.value.filter(t=>{
 if(status.value==='open'&&['Completed','Pending Review','Pending Approval'].includes(t.status))return false
 if(status.value==='review'&&!needingReview.value.some(row=>row.line===t.line))return false
 if(status.value==='blocked'&&t.status!=='Blocked')return false
 if(status.value==='done'&&t.status!=='Completed')return false
 return !search.value||fold([t.work_name,t.plot_code,t.farm_plot,t.work_team,t.plan,t.status].join(' ')).includes(fold(search.value))
}))
const filteredHistory=computed(()=>(history.value||[]).filter(r=>!historySearch.value||fold([r.work_name,r.block_code||r.plot_code,r.work_plan,r.name].join(' ')).includes(fold(historySearch.value))))
const summaryName=computed(()=>(session.value?.farms||[]).find(f=>f.name===farm.value)?.farm_name||farm.value||'Chọn vườn')
const blockOptions=computed(()=>(assignOptions.value?.blocks||[]).map(b=>({value:'block:'+b.name,label:'Lô '+(b.block_code||b.block_name||b.name)})))
const locationOptions=computed(()=>blockOptions.value)
const teamOptions=computed(()=>(assignOptions.value?.teams||[]).map(t=>({value:t.name,label:t.team_name||t.team_code||t.name})))
const workOptions=computed(()=>(assignOptions.value?.works||[]).map(w=>({value:w.name,label:w.work_name||w.name})))
const taskSuggestions=computed(()=>filteredTasks.value.map(t=>({value:t.line,label:t.work_name||t.work_type,description:(t.block_code||t.farm_block||t.plot_code||t.farm_plot)+' · '+(t.work_team||'Chưa chọn tổ')})))
const histSuggestions=computed(()=>filteredHistory.value.map(r=>({value:r.name,label:r.work_name,description:r.block_code||r.plot_code+' · '+r.posting_date})))
const fmt=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:2})
const unit=x=>unitLabel(x)||x||''
const labelState=s=>({Planned:'Chưa bắt đầu',Ready:'Sẵn sàng','In Progress':'Đang làm',Blocked:'Đang vướng',Completed:'Đã duyệt','Pending Review':'Chờ đội trưởng kiểm tra','Pending Approval':'Chờ quản lý duyệt','Changes Requested':'Cần sửa báo cáo'})[s]||stateLabel(s)||s||'Chưa bắt đầu'
const badgeState=s=>({Planned:'neutral',Ready:'soft','In Progress':'running',Blocked:'warning',Completed:'success','Pending Review':'soft','Pending Approval':'running','Changes Requested':'warning'})[s]||'neutral'
function clear(){error.value='';message.value=''}
function messageFor(e){return String(e?.message||'Không kết nối được máy chủ.')}
function go(next){
 clear()
 if(screen.value===next)return
 screen.value=next
 window.scrollTo({top:0,behavior:'instant'})
}
function appBack(){
 if(saving.value)return
 if(document.querySelector('.mobile-floating-options')){
  document.dispatchEvent(new Event('warehouse-dismiss-picker'));return
 }
 if(screen.value!=='home')window.history.back()
}
function isDirty(){
 if(screen.value==='result')
  return !!resultForm.value&&(Object.values(resultForm.value).some(v=>String(v||'').trim()!=='')||!!photo.value)
 if(screen.value==='block')return !!blockReason.value.trim()
 if(['assign','assign-preview'].includes(screen.value))
  return !!assignTeam.value||assignLines.value.some(row=>Object.values(row).some(v=>String(v||'').trim()!==''))
 return false
}
function confirmLeave(){
 if(!isDirty())return Promise.resolve(true)
 return askLeave('Bạn đang nhập dữ liệu chưa lưu. Rời màn hình sẽ mất phần đang nhập.')
}
async function changeTab(tab){
 if(saving.value||!tabs.includes(tab)||screen.value===tab||!await confirmLeave())return
 document.dispatchEvent(new Event('warehouse-dismiss-picker'))
 go(tab)
 if(tab==='history')await loadHistory()
 if(tab==='profile')await refreshQueue()
}
const {start:swipeStart,move:swipeMove,end:swipeEnd,cancel:swipeCancel}=createTabSwipe({enabled:()=>tabs.includes(screen.value)&&!saving.value,ignore:'input,textarea,button,select,a,.mobile-link-field,.mobile-live-search,.lotus-pwa-bottom,.mobile-leave-dialog',tabs:()=>tabs,current:()=>screen.value,go:changeTab})
function beforeUnload(e){
 if(saving.value||isDirty()){e.preventDefault();e.returnValue=''}
}
function connection(){online.value=navigator.onLine}
async function refreshQueue(){
 if(!session.value?.user)return
 try{queue.value=await queueRows(session.value.user)}catch(e){error.value=messageFor(e)}
}
async function loadDay(){
 const id=++requestId
 if(!farm.value){day.value={tasks:[],plans:[]};return}
 busy.value=true;error.value=''
 try{
  const result=await call('lotus_farm.work_mobile.day',{farm:farm.value,posting_date:date.value})
  if(id!==requestId)return
  day.value=result
  const url=new URL(location.href);url.searchParams.set('farm',farm.value);historyStateUrl(url)
  await refreshQueue()
 }catch(e){if(id===requestId){day.value={tasks:[],plans:[]};error.value=messageFor(e)}}
 finally{if(id===requestId)busy.value=false}
}
function historyStateUrl(url){window.history.replaceState(window.history.state,'',url.pathname+url.search)}
async function loadHistory(){
 const id=++historyId
 if(!farm.value)return
 loadingHistory.value=true;error.value=''
 try{
  const result=await call('lotus_farm.work_mobile.history',{farm:farm.value,to_date:date.value,days:14})
  if(id===historyId)history.value=result?.rows||[]
 }catch(e){if(id===historyId){history.value=[];error.value=messageFor(e)}}
 finally{if(id===historyId)loadingHistory.value=false}
}
async function changeFarm(value){
 farm.value=value
 day.value={tasks:[],plans:[]};history.value=[];assignOptions.value=null
 await loadDay()
 if(screen.value==='history')await loadHistory()
}
async function changeDate(){await loadDay();if(screen.value==='history')await loadHistory()}
async function bootstrap(){
 busy.value=true;error.value=''
 try{
  const s=await consoleAPI('bootstrap')
  session.value=s;setCSRF(s.csrf_token)
  date.value=s.today
  const requested=new URLSearchParams(location.search).get('farm')
  farm.value=s.farms?.some(f=>f.name===requested)?requested:(s.farms?.[0]?.name||'')
  if(!farm.value)throw Error('Tài khoản chưa được phân quyền vườn.')
  await loadDay()
  if(new URLSearchParams(location.search).get('action')==='assign'&&canAssign.value){
   const url=new URL(location.href);url.searchParams.delete('action');historyStateUrl(url)
   await openAssign()
  }
 }catch(e){error.value=messageFor(e)}
 finally{busy.value=false}
}
function openTask(t){selected.value={...t};reviewNote.value='';go('detail')}
function canRevise(t){return t?.result_state==='Changes Requested'&&t.result_owner===session.value?.user}
function openResult(){
 if(!canCapture.value||!selected.value||(selected.value.result&&!canRevise(selected.value))||pendingLines.value.has(selected.value.line))return
 const old=canRevise(selected.value)?selected.value:null
 resultForm.value={completed_qty:old?String(old.completed_qty):'',actual_workdays:old?String(old.actual_workdays):'',unfinished_reason:old?.unfinished_reason||''}
 photo.value=null
 go('result')
}
function pickPhoto(event){
 const file=event.target.files?.[0]||null
 if(file&&file.size>10*1024*1024){error.value='Ảnh tối đa 10 MB.';event.target.value='';return}
 if(file&&!file.type.startsWith('image/')){error.value='Chỉ nhận tệp ảnh.';event.target.value='';return}
 photo.value=file
}
async function gps(){
 if(!navigator.geolocation||!navigator.onLine)return {}
 return new Promise(resolve=>navigator.geolocation.getCurrentPosition(
  p=>resolve({latitude:p.coords.latitude,longitude:p.coords.longitude,gps_accuracy_m:p.coords.accuracy}),
  ()=>resolve({}),{timeout:5000,maximumAge:0,enableHighAccuracy:true}
 ))
}
async function saveResult(){
 if(!canCapture.value||saving.value||!resultForm.value||!selected.value)return
 const f=resultForm.value,t=selected.value
 const qty=Number(f.completed_qty),days=Number(f.actual_workdays)
 if(String(f.completed_qty).trim()===''||String(f.actual_workdays).trim()===''||
    !Number.isFinite(qty)||!Number.isFinite(days)||qty<0||days<0){
  error.value='Nhập đúng số lượng đã làm và số công thực tế.';return
 }
 if(qty>Number(t.planned_qty)+0.000001){error.value='Số lượng lớn hơn kế hoạch. Nhờ quản lý kiểm tra trước khi ghi.';return}
 if(qty<Number(t.planned_qty)&&!f.unfinished_reason.trim()){error.value='Chưa làm đủ thì cần ghi lý do.';return}
 saving.value=true;error.value=''
 try{
  const position=await gps()
  const event={client_event_id:crypto.randomUUID(),farm:farm.value,
   ...(canRevise(t)?{revision_of:t.result}:{}),
   target_doctype:'Daily Work Result',captured_at:new Date().toISOString(),...position,
   values:{farm_block:t.farm_block,farm_plot:t.farm_plot,crop_cycle:t.crop_cycle,
    sucker_selection_batch:t.cohort||null,posting_date:t.posting_date||date.value,
    work_plan:t.plan,work_plan_line:t.line,completed_qty:qty,
    actual_workdays:days,unfinished_reason:f.unfinished_reason.trim()}}
  await queueCapture(session.value.user,event,photo.value)
  await refreshQueue()
  resultForm.value=null;photo.value=null;go('tasks')
  message.value='Đã lưu báo cáo trên điện thoại. Khi đồng bộ xong, báo cáo sẽ chờ đội trưởng kiểm tra, chưa tính là đã duyệt.'
  saving.value=false
  if(online.value)await syncQueue(false)
 }catch(e){error.value=messageFor(e)}
 finally{saving.value=false}
}
async function prepareSelected(){
 if(!canPrepare.value||!selected.value||!online.value||saving.value)return
 saving.value=true;clear()
 try{
  const t=selected.value
  const r=await call('lotus_farm.work_prepare.prepare',{plan:t.plan,line:t.line},true)
  message.value=r.note||'Đã chuẩn bị công dự kiến và nhu cầu vật tư. Kiểm tra cấp vật tư ở app Kho.'
  await loadDay()
  const updated=tasks.value.find(x=>x.line===t.line)
  if(updated)selected.value={...updated}
 }catch(e){error.value=messageFor(e)}
 finally{saving.value=false}
}
async function decideResult(decision){
 if(!selected.value?.result||saving.value||!online.value)return
 if(decision==='Request Changes'&&!reviewNote.value.trim()){
  error.value='Nhập lý do yêu cầu sửa báo cáo.';return
 }
 saving.value=true;clear()
 try{
  const r=await call('lotus_farm.work_review.decide',{
   result:selected.value.result,decision,reason:reviewNote.value.trim()
  },true)
  reviewNote.value=''
  message.value=decision==='Verify'?'Đã kiểm tra, chuyển quản lý duyệt.':decision==='Approve'?'Đã duyệt kết quả chính thức.':'Đã trả lại báo cáo để tổ trưởng sửa.'
  await loadDay()
  const updated=tasks.value.find(t=>t.line===selected.value.line)
  if(updated)selected.value={...updated}
 }catch(e){error.value=messageFor(e)}
 finally{saving.value=false}
}
async function syncQueue(showMessage=true){
 if(!session.value?.user||!online.value||saving.value)return
 saving.value=true;error.value=''
 try{
  const result=await syncCaptures(session.value.user,{
   call:async (...args)=>{const value=await call(...args);if(args[0]==='lotus_farm.field.session_info')setCSRF(value.csrf_token);return value},
   upload:(file,user)=>upload(file,null,null,user)
  })
  await refreshQueue()
  if(result?.some(r=>r.status==='Error')){
   error.value='Có bản ghi chưa được máy chủ nhận. Mở Hàng chờ để xem lỗi, không nhập lại bản khác.'
  }else if(showMessage)message.value='Đã kiểm tra và gửi các bản ghi hợp lệ.'
  await loadDay()
  if(screen.value==='history')await loadHistory()
 }catch(e){error.value=messageFor(e)}
 finally{saving.value=false}
}
async function checkQueue(entry){
 if(saving.value||!online.value)return
 saving.value=true;clear()
 try{
  const result=await reconcileCapture(session.value.user,entry.key,{call})
  if(!result.received){
   message.value='Máy chủ chưa nhận. Kiểm tra lỗi rồi chọn Gửi lại hoặc nhập lý do để bỏ bản này.'
  }else message.value='Máy chủ đã nhận bản ghi.'
  await refreshQueue()
 }catch(e){error.value=messageFor(e)}
 finally{saving.value=false}
}
function startDiscard(entry){
 discardEntry.value=entry;discardReason.value=''
 discardDialog.value?.showModal()
}
function closeDiscard(){discardDialog.value?.close();discardEntry.value=null;discardReason.value=''}
async function confirmDiscard(){
 if(!discardEntry.value||!discardReason.value.trim()||saving.value||!online.value)return
 saving.value=true;clear()
 try{
  const result=await reconcileCapture(session.value.user,discardEntry.value.key,{call},discardReason.value.trim())
  message.value=result.received?'Máy chủ đã nhận báo cáo, không thể bỏ.':'Đã bỏ bản nháp chưa gửi.'
  closeDiscard();await refreshQueue()
 }catch(e){error.value=messageFor(e)}
 finally{saving.value=false}
}
async function logout(){
 if(saving.value||!await confirmLeave()||!await askLeave('Đăng xuất khỏi Công việc ngoài vườn?'))return
 saving.value=true;error.value=''
 try{
  await logoutPwa('work',{csrf:session.value?.csrf_token||'',home:'/work'})
 }catch(e){error.value='Không đăng xuất được: '+messageFor(e)}
 finally{saving.value=false}
}
async function changeState(next,reason=''){
 if(!canAssign.value||!selected.value||saving.value||!online.value)return
 saving.value=true;clear()
 try{
  await consoleAPI('work_state',{plan:selected.value.plan,line:selected.value.line,state:next,reason},true)
  message.value='Đã cập nhật trạng thái: '+labelState(next)+'.'
  selected.value={...selected.value,status:next,blocked_reason:next==='Blocked'?reason:''}
  go('detail');await loadDay()
 }catch(e){error.value=messageFor(e)}
 finally{saving.value=false}
}
function openBlock(){blockReason.value='';go('block')}
function blankLine(){return {location:'',work_type:'',qty:'',payment_mode:'',piecework_rate:''}}
function editAssign(){preview.value=null}
async function openAssign(){
 if(!canAssign.value||!online.value)return
 saving.value=true;clear()
 try{
  assignOptions.value=await call('lotus_farm.mobile_assignment.options',{farm:farm.value})
  assignTeam.value='';assignLines.value=[blankLine()];preview.value=null;rateReason.value=''
  go('assign')
 }catch(e){error.value=messageFor(e)}
 finally{saving.value=false}
}
function modeOptions(name){
 const w=assignOptions.value?.works?.find(x=>x.name===name)
 const result=[{value:'',label:'Theo thiết lập'}]
 if(w?.allow_daywork)result.push({value:'Daywork',label:'Công nhật'})
 if(w?.allow_piecework)result.push({value:'Piece',label:'Công khoán'})
 if(w?.allow_daywork&&w?.allow_piecework)result.push({value:'Both',label:'Cả hai'})
 return result
}
function currentRate(name){return assignOptions.value?.works?.find(w=>w.name===name)?.piecework_rate||0}
function assignPayload(){return assignLines.value.map(r=>({
 location:r.location,work_type:r.work_type,qty:Number(r.qty),payment_mode:r.payment_mode||'',
 ...(String(r.piecework_rate).trim()!==''?{piecework_rate:Number(r.piecework_rate)}:{})
}))}
async function previewAssign(){
 if(!assignTeam.value||!assignLines.value.length||assignLines.value.some(r=>!r.location||!r.work_type||String(r.qty).trim()===''||!Number.isFinite(Number(r.qty))||Number(r.qty)<=0)){
  error.value='Chọn tổ, lô/thửa, công việc và số lượng cần làm.';return
 }
 if(assignLines.value.some(r=>String(r.piecework_rate).trim()!==''&&(!Number.isFinite(Number(r.piecework_rate))||Number(r.piecework_rate)<0))){
  error.value='Đơn giá khoán phải là số hợp lệ.';return
 }
 saving.value=true;clear()
 try{
  preview.value=await call('lotus_farm.mobile_assignment.preview',{
   farm:farm.value,posting_date:date.value,work_team:assignTeam.value,items:assignPayload()},true)
  go('assign-preview')
 }catch(e){error.value=messageFor(e)}
 finally{saving.value=false}
}
async function createAssign(){
 if(!preview.value||saving.value||!online.value)return
 if(preview.value.approval_required&&!rateReason.value.trim()){error.value='Nhập lý do đề nghị giá cao hơn giá chuẩn.';return}
 saving.value=true;clear()
 try{
  const result=await call('lotus_farm.mobile_assignment.create',{
   farm:farm.value,posting_date:date.value,work_team:assignTeam.value,
   items:assignPayload(),rate_request_reason:rateReason.value.trim()
  },true)
  go('home')
  message.value=result.status==='Pending'?'Đã tạo '+result.plan+' và gửi chờ duyệt giá. Chưa giao cho tổ.':'Đã giao '+result.count+' việc trong kế hoạch '+result.plan+'.'
  await loadDay()
 }catch(e){error.value=messageFor(e)}
 finally{saving.value=false}
}
async function approve(p,decision){
 if(!canApprove.value||saving.value||!online.value)return
 if(decision==='Reject'&&!rejectReason.value.trim()){error.value='Nhập lý do từ chối.';return}
 saving.value=true;clear()
 try{
  await call('lotus_farm.rate_approval.decide',{plan:p.name,decision,reason:decision==='Reject'?rejectReason.value.trim():''},true)
  rejection.value='';rejectReason.value=''
  message.value=decision==='Approve'?'Đã duyệt giá và giao kế hoạch '+p.name:'Đã từ chối kế hoạch '+p.name
  await loadDay()
 }catch(e){error.value=messageFor(e)}
 finally{saving.value=false}
}
function chooseSuggestion(row){const t=tasks.value.find(r=>r.line===row.value);if(t)openTask(t)}
function chooseHistorical(row){historySearch.value=row.label}
async function onPopstate(e){
 if(!navigationReady)return
 if(leavePending.value){
  finishLeave(false)
  window.history.pushState({lotusWork:{screen:screen.value}},'',location.href);return
 }
 if(saving.value||document.querySelector('.mobile-floating-options')){
  document.dispatchEvent(new Event('warehouse-dismiss-picker'))
  window.history.pushState({lotusWork:{screen:screen.value}},'',location.href);return
 }
 if(!await confirmLeave()){
  window.history.pushState({lotusWork:{screen:screen.value}},'',location.href);return
 }
 const wanted=e.state?.lotusWork?.screen
 let next=['home','tasks','history','profile','detail','result','block','assign','assign-preview','queue','done'].includes(wanted)?wanted:'home'
 if(next==='result'&&!resultForm.value)next='tasks'
 if(next==='detail'&&!selected.value)next='tasks'
 if(next==='assign-preview'&&!preview.value)next='assign'
 if(next==='assign'&&!assignOptions.value)next='home'
 restoring=true
 screen.value=next
 restoring=false
 if(next==='history')loadHistory()
 if(next==='profile'||next==='queue')refreshQueue()
 // Hardware Back must navigate within this app, never to the previous browser site.
 if(!e.state?.lotusWork||next==='home'&&e.state?.lotusWorkRoot){
  window.history.pushState({lotusWork:{screen:'home'}},'',location.href)
 }
}
watch(screen,(next,prev)=>{
 if(!navigationReady||restoring)return
 document.dispatchEvent(new Event('warehouse-dismiss-picker'))
 window.history.replaceState({...window.history.state,scroll:window.scrollY},'',location.href)
 window.history.pushState({lotusWork:{screen:next}},'',location.href)
 window.scrollTo(0,0)
},{flush:'sync'})
watch(error,value=>{
 if(value)requestAnimationFrame(()=>document.querySelector('.mobile-message.danger')?.scrollIntoView({block:'nearest',behavior:'smooth'}))
})
function onInstalled(){installed.value=true}
function installApp(){openSetup()}
onMounted(async()=>{
 window.history.replaceState({...window.history.state,lotusWorkRoot:true},'',location.href)
 window.history.pushState({lotusWork:{screen:'home'}},'',location.href)
 window.addEventListener('popstate',onPopstate)
 window.addEventListener('online',connection);window.addEventListener('offline',connection)
 window.addEventListener('beforeunload',beforeUnload)
 window.addEventListener('appinstalled',onInstalled)
 installed.value=window.matchMedia('(display-mode:standalone)').matches||navigator.standalone===true
 navigationReady=true
 await bootstrap()
 const target=new URLSearchParams(location.search).get('tab')
 if(session.value&&['tasks','history'].includes(target))changeTab(target)
})
onBeforeUnmount(()=>{
 finishLeave(false);navigationReady=false
 window.removeEventListener('popstate',onPopstate)
 window.removeEventListener('online',connection);window.removeEventListener('offline',connection)
 window.removeEventListener('beforeunload',beforeUnload)
 window.removeEventListener('appinstalled',onInstalled)
})

</script>

<template>
 <LotusMobileShell app="work" :refresh="loadDay" :refreshable="tabs.includes(screen)" class="lotus-mobile lotus-work" :class="{'mobile-keyboard-open':keyboard}"
  :title="mobileTitle" :tabs="mobileTabs" :active-tab="rootTab"
  :back="!tabs.includes(screen)" :keyboard-open="keyboard" :disabled="saving"
  @back="appBack" @navigate="changeTab" 
   @touchstart.passive="swipeStart" @touchmove="swipeMove" @touchend="swipeEnd" @touchcancel="swipeCancel">
<main class="mobile-container" id="lotus-content" :aria-busy="busy||saving">
   <LotusMobileFeedback v-if="!online" kind="warning">Mất mạng. Báo cáo có thể lưu vào Hàng chờ; giao việc cần có mạng.</LotusMobileFeedback>
   <LotusMobileFeedback v-if="error" kind="error">{{error}}</LotusMobileFeedback>
   <LotusMobileFeedback v-if="message&&screen!=='done'" kind="success">{{message}}</LotusMobileFeedback>
   <LotusMobileFeedback v-if="busy||loadingHistory" kind="loading">Đang tải dữ liệu…</LotusMobileFeedback>

   <template v-if="session">
    <template v-if="screen==='home'">
     <h1>Chọn công việc</h1>
     <div class="work-scope">
      <div class="mobile-field"><label>Vườn đang làm việc</label>
       <MobileLinkField :model-value="farm" :options="farms" :searchable="false" placeholder="Chọn vườn" @update:modelValue="changeFarm"/>
      </div>
      <div class="mobile-field"><label>Ngày làm việc</label>
       <LotusMobileInput aria-label="Ngày làm việc" v-model="date" type="date" @change="changeDate"/>
      </div>
     </div>
     <div class="mobile-actions" aria-label="Thao tác Công việc ngoài vườn">
      <LotusMobileAction v-if="canAssign" primary icon="edit" title="Lập kế hoạch / Giao việc" :disabled="!online||busy" @select="openAssign"/>
      <LotusMobileAction v-if="canCapture" icon="completed" title="Báo kết quả" @select="status='open';go('tasks')"/>
      <LotusMobileAction icon="apps-o" title="Công việc đã giao" @select="status='all';go('tasks')"/>
      <LotusMobileAction icon="flag-o" title="Việc vướng mắc" @select="status='blocked';go('tasks')"/>
      <LotusMobileAction v-if="needingReview.length" icon="passed" :title="'Chờ tôi kiểm / duyệt ('+needingReview.length+')'" @select="status='review';go('tasks')"/>
      <LotusMobileAction icon="clock-o" title="Kết quả đã ghi" @select="changeTab('history')"/>
     </div>
     <div class="work-summary">Ngày {{shortDate(date)}}: <strong>{{remaining}}</strong> việc chưa xong · <strong>{{done}}</strong> đã ghi kết quả
      <span v-if="blocked"> · <strong>{{blocked}}</strong> vướng mắc</span>
     </div>
     <div v-if="pendingCount" class="mobile-message work-warning">
      Có {{pendingCount}} báo cáo chưa gửi xong.
      <LotusMobileButton type="button" class="work-link" @click="go('queue')">Mở hàng chờ <Icon name="arrow" class="lotus-pwa-inline-icon" aria-hidden="true"/></LotusMobileButton>
     </div>
     <div class="work-section">
      <h2>Việc trong ngày</h2><LotusMobileButton type="button" @click="status='all';go('tasks')">Xem tất cả <Icon name="arrow" class="lotus-pwa-inline-icon" aria-hidden="true"/></LotusMobileButton>
     </div>
     <LotusMobileButton v-for="task in tasks.filter(t=>t.status!=='Completed').slice(0,4)" :key="task.line" class="work-list-row" type="button" @click="openTask(task)">
      <div><strong>{{task.work_name||task.work_type}}</strong><span class="work-status" :class="badgeState(task.status)">{{labelState(task.status)}}</span></div>
      <small>{{task.block_code||task.farm_block||task.plot_code||task.farm_plot}} · {{task.team_label||task.work_team||'Chưa phân tổ'}}</small>
      <div class="mobile-inline"><span>Đã làm / Kế hoạch</span><b>{{fmt(task.completed_qty)}} / {{fmt(task.planned_qty)}} {{unit(task.uom)}}</b></div>
     </LotusMobileButton>
     <p v-if="!tasks.length&&!busy" class="mobile-empty">Ngày này chưa có việc được giao.</p>
     <p v-if="drafts" class="work-muted">{{drafts}} phiếu đang chờ duyệt giá, chưa tính là đã giao.</p>
     <div class="mobile-install"><LotusMobileButton v-if="!installed" type="button" @click="installApp">＋ Thêm Công việc ngoài vườn lên màn hình chính</LotusMobileButton>

     </div>
    </template>

    <template v-else-if="screen==='tasks'">
     <h1>Công việc đã giao</h1>
     <div class="work-date-row">
      <div class="mobile-field"><label>Vườn</label><MobileLinkField aria-label="Vườn" :model-value="farm" :options="farms" :searchable="false" @update:modelValue="changeFarm"/></div>
      <div class="mobile-field"><label>Ngày</label><LotusMobileInput aria-label="Ngày" v-model="date" type="date" @change="changeDate"/></div>
     </div>
     <MobileLiveSearch v-model="search" :options="taskSuggestions" placeholder="Gõ tên việc, lô hoặc tổ…" @select="chooseSuggestion"/>
     <div class="work-chips" role="group" aria-label="Lọc trạng thái">
      <LotusMobileButton v-for="item in [{value:'all',label:'Tất cả'},{value:'open',label:'Chưa xong'},{value:'blocked',label:'Vướng'},{value:'done',label:'Đã ghi'}]" :key="item.value" :class="{active:status===item.value}" @click="status=item.value">{{item.label}}</LotusMobileButton>
     </div>
     <p class="work-summary">{{filteredTasks.length}} công việc</p>
     <LotusMobileButton v-for="task in filteredTasks" :key="task.line" type="button" class="work-list-row" @click="openTask(task)">
      <div><strong>{{task.work_name||task.work_type}}</strong><span class="work-status" :class="badgeState(task.status)">{{pendingLines.has(task.line)?'Chờ gửi':labelState(task.status)}}</span></div>
      <small>{{task.block_code||task.farm_block||task.plot_code||task.farm_plot}} · {{task.team_label||task.work_team||'Chưa phân tổ'}}</small>
      <div class="mobile-inline"><span>Thực hiện</span><b>{{fmt(task.completed_qty)}} / {{fmt(task.planned_qty)}} {{unit(task.uom)}}</b></div>
     </LotusMobileButton>
     <p v-if="!filteredTasks.length&&!busy" class="mobile-empty">Không có việc phù hợp. Thử đổi ngày hoặc bộ lọc.</p>
    </template>

    <template v-else-if="screen==='history'">
     <h1>Lịch sử kết quả</h1>
     <div class="work-date-row">
      <div class="mobile-field"><label>Vườn</label><MobileLinkField aria-label="Vườn" :model-value="farm" :options="farms" :searchable="false" @update:modelValue="changeFarm"/></div>
      <div class="mobile-field"><label>Đến ngày</label><LotusMobileInput aria-label="Đến ngày" v-model="date" type="date" @change="changeDate"/></div>
     </div>
     <MobileLiveSearch v-model="historySearch" :options="histSuggestions" :loading="loadingHistory" placeholder="Gõ tên việc hoặc lô…" @select="chooseHistorical"/>
     <p class="work-summary">Kết quả 14 ngày đến {{shortDate(date)}}</p>
     <div v-for="item in filteredHistory" :key="item.name" class="mobile-list-card">
      <strong>{{item.work_name||'Công việc'}}</strong>
      <small>{{item.block_code||item.farm_block||item.plot_code||item.farm_plot}} · {{shortDate(item.posting_date)}}</small>
      <div class="mobile-inline"><span>Khối lượng thực tế</span><b>{{fmt(item.completed_qty)}}</b></div>
      <small>{{fmt(item.actual_workdays)}} công <span v-if="item.unfinished_reason"> · {{item.unfinished_reason}}</span></small>
     </div>
     <p v-if="!filteredHistory.length&&!loadingHistory&&!error" class="mobile-empty">Chưa có kết quả phù hợp trong khoảng thời gian này.</p>
    </template>

    <template v-else-if="screen==='profile'">
     <h1>Tôi</h1>
     <section class="mobile-account"><div class="mobile-avatar" aria-hidden="true">👤</div><div><strong>{{session.user}}</strong><small>Tài khoản Công việc ngoài vườn</small></div></section>
     <div class="mobile-list-card">
      <div class="mobile-profile-row"><span>Vườn</span><strong>{{summaryName}}</strong></div>
      <div class="mobile-profile-row"><span>Báo cáo chưa gửi</span><strong>{{pendingCount}}</strong></div>
     </div>
     <div class="mobile-field"><label>Đổi vườn</label>
      <MobileLinkField aria-label="Đổi vườn" :model-value="farm" :options="farms" :searchable="false" @update:modelValue="changeFarm"/>
     </div>
     <LotusMobileButton type="button" class="work-outline" @click="go('queue')">Hàng chờ báo cáo <b>{{pendingCount}} <Icon name="arrow" class="lotus-pwa-inline-icon" aria-hidden="true"/></b></LotusMobileButton>
     <a class="work-outline" href="/lotus/cong-viec">Mở trên máy tính <b><Icon name="share-o" class="lotus-pwa-inline-icon" aria-hidden="true"/></b></a>
     <a class="work-outline" href="/warehouse">Kho Lotus <b><Icon name="share-o" class="lotus-pwa-inline-icon" aria-hidden="true"/></b></a>
     <div class="mobile-install"><LotusMobileButton v-if="!installed" type="button" @click="installApp">Cài Công việc ngoài vườn lên điện thoại</LotusMobileButton>

     </div>
     <LotusMobileSignatureSettings :user="session?.user||''"/>
      <LotusMobileButton type="button" @click="openSetup">Cài ứng dụng và thông báo</LotusMobileButton>
     <LotusMobileButton class="mobile-logout" type="button" :disabled="saving" @click="logout">Đăng xuất</LotusMobileButton>
    </template>

    <template v-else-if="screen==='detail'&&selected">
     <div class="mobile-summary">
      <span>Công việc <b>{{selected.work_name||selected.work_type}}</b></span>
      <span>Trạng thái <b>{{labelState(selected.status)}}</b></span>
      <span>Lô <b>{{selected.block_code||selected.farm_block||selected.plot_code||selected.farm_plot}}</b></span>
      <span>Tổ thực hiện <b>{{selected.team_label||selected.work_team||'Chưa phân tổ'}}</b></span>
      <span>Chỉ tiêu <b>{{fmt(selected.planned_qty)}} {{unit(selected.uom)}}</b></span>
      <span>Đã ghi <b>{{fmt(selected.completed_qty)}} {{unit(selected.uom)}}</b></span>
      <span>Công dự kiến <b>{{fmt(selected.required_workdays)}}</b></span>
      <span>Ngày <b>{{shortDate(selected.posting_date||date)}}</b></span>
     </div>
     <p v-if="selected.blocked_reason" class="mobile-message work-warning">Vướng mắc: {{selected.blocked_reason}}</p>
     <p v-if="pendingLines.has(selected.line)" class="mobile-message work-warning">Việc này đã có báo cáo lưu trên điện thoại. Mở hàng chờ thay vì ghi trùng.</p>
     <div v-if="['Planned','Blocked','Ready'].includes(selected.status)" class="mobile-list-card">
      <strong>Điều kiện chuẩn bị công việc</strong>
      <div class="mobile-inline"><span>Đã phân / Cần phân</span><b>{{fmt(selected.allocated_workdays)}} / {{fmt(selected.required_workdays)}} công</b></div>
      <p v-if="selected.has_material_norm" class="work-muted">Phiếu nhu cầu vật tư: {{selected.material_requirement_ready?'Đã có':'Chưa có'}}</p>
      <a v-if="canPrepare&&selected.material_requirement" class="work-outline" style="display:inline-flex;padding:10px 12px;text-decoration:none;margin:6px 0;color:inherit;border:1px solid currentColor;border-radius:8px" :href="'/lotus_material_proposal_print?doctype=Material%20Requirement&name='+encodeURIComponent(selected.material_requirement)" target="_blank" rel="noopener noreferrer">In phiếu đề xuất cấp vật tư / PDF ↗</a>
      <p v-else class="work-muted">Việc này chưa có định mức vật tư hoặc không cần vật tư theo kế hoạch.</p>
      <LotusMobileButton v-if="canPrepare" type="button" class="work-outline" :disabled="saving||!online" @click="prepareSelected">Chuẩn bị tổng công và phiếu vật tư</LotusMobileButton>
      <small class="work-muted">Chuẩn bị không phải là xuất kho hay chấm công thực tế. Nếu có vật tư, cần kiểm tra cấp phát trên app Kho.</small>
     </div>
     <div class="work-actions">
      <LotusMobileButton v-if="canAssign&&['Planned','Blocked'].includes(selected.status)" type="button" class="work-outline" :disabled="saving||!online" @click="changeState('Ready')">Sẵn sàng làm <b><Icon name="arrow" class="lotus-pwa-inline-icon" aria-hidden="true"/></b></LotusMobileButton>
      <LotusMobileButton v-if="canAssign&&['Ready','Blocked'].includes(selected.status)" type="button" class="work-outline" :disabled="saving||!online" @click="changeState('In Progress')">Bắt đầu làm <b><Icon name="arrow" class="lotus-pwa-inline-icon" aria-hidden="true"/></b></LotusMobileButton>
      <LotusMobileButton v-if="canAssign&&selected.status!=='Blocked'&&selected.status!=='Completed'" type="button" class="work-outline" :disabled="saving||!online" @click="openBlock">Báo vướng mắc <b><Icon name="arrow" class="lotus-pwa-inline-icon" aria-hidden="true"/></b></LotusMobileButton>
      <LotusMobileButton v-if="canCapture&&(!selected.result||canRevise(selected))&&!pendingLines.has(selected.line)" type="button" class="mobile-submit" :disabled="saving" @click="openResult">{{canRevise(selected)?'Sửa và gửi lại kết quả →':'Gửi báo cáo kết quả →'}}</LotusMobileButton>
      <p v-if="selected.result" class="mobile-message" :class="selected.result_state==='Approved'?'success':'work-warning'">Phiếu {{selected.result}} · {{labelState(selected.status)}}.</p>
      <p v-if="selected.review_note" class="mobile-message work-warning">Nhận xét: {{selected.review_note}}</p>
      <div v-if="canVerify&&selected.result_state==='Pending'">
       <div class="mobile-field"><label>Nhận xét kiểm tra (nếu có)</label><LotusMobileInput aria-label="Nhận xét kiểm tra (nếu có)" type="textarea" v-model="reviewNote" rows="2"/></div>
       <LotusMobileButton type="button" class="mobile-submit" :disabled="saving||!online" @click="decideResult('Verify')">Kiểm tra đạt → Chờ quản lý duyệt</LotusMobileButton>
       <LotusMobileButton type="button" class="work-outline" :disabled="saving||!online||!reviewNote.trim()" @click="decideResult('Request Changes')">Yêu cầu tổ trưởng sửa</LotusMobileButton>
      </div>
      <div v-if="canVerify&&selected.result_state==='Verified'">
       <div class="mobile-field"><label>Nhận xét duyệt (nếu có)</label><LotusMobileInput aria-label="Nhận xét duyệt (nếu có)" type="textarea" v-model="reviewNote" rows="2"/></div>
       <LotusMobileButton v-if="canFinalize" type="button" class="mobile-submit" :disabled="saving||!online" @click="decideResult('Approve')">Duyệt kết quả chính thức</LotusMobileButton>
       <LotusMobileButton type="button" class="work-outline" :disabled="saving||!online||!reviewNote.trim()" @click="decideResult('Request Changes')">Yêu cầu kiểm tra lại</LotusMobileButton>
      </div>
     </div>
    </template>

    <template v-else-if="screen==='result'&&selected&&resultForm">
     <div class="mobile-summary">
      <span>Công việc <b>{{selected.work_name||selected.work_type}}</b></span>
      <span>Lô <b>{{selected.block_code||selected.farm_block||selected.plot_code||selected.farm_plot}}</b></span>
      <span>Được giao <b>{{fmt(selected.planned_qty)}} {{unit(selected.uom)}}</b></span>
     </div>
     <form @submit.prevent="saveResult"><fieldset class="mobile-form-fields" :disabled="saving">
      <div class="mobile-field"><label>Số lượng thực tế ({{unit(selected.uom)}})</label><LotusMobileInput v-model="resultForm.completed_qty" type="number" min="0" step="any" inputmode="decimal" placeholder="Nhập số đã làm" required/></div>
      <div class="mobile-field"><label>Tổng số công thực tế</label><LotusMobileInput v-model="resultForm.actual_workdays" type="number" min="0" step="any" inputmode="decimal" placeholder="Ví dụ: 10" required/></div>
      <div class="mobile-field"><label>Lý do chưa đạt chỉ tiêu (nếu có)</label><LotusMobileInput type="textarea" v-model="resultForm.unfinished_reason" rows="2" placeholder="Ví dụ: trời mưa, thiếu vật tư…"/></div>
      <div class="mobile-field"><label>Ảnh hiện trường (nếu có)</label><LotusMobileFile aria-label="Ảnh hiện trường (nếu có)" accept="image/*" capture="environment" @change="pickPhoto"/></div>
      <p v-if="photo" class="mobile-message success">Đã chọn ảnh: {{photo.name}}</p>
      <p class="work-muted">Ghi công theo tổng công của tổ, không tự chia cho từng người. Báo cáo gửi lên sẽ chờ đội trưởng kiểm tra và quản lý duyệt; chưa tính công chính thức. Khi mất mạng, báo cáo được giữ trong Hàng chờ.</p>
      <LotusMobileButton type="submit" class="mobile-submit">{{saving?'Đang lưu…':'Lưu báo cáo →'}}</LotusMobileButton>
     </fieldset></form>
    </template>

    <template v-else-if="screen==='block'&&selected">
     <div class="mobile-summary"><span>Việc <b>{{selected.work_name||selected.work_type}}</b></span><span>Lô <b>{{selected.block_code||selected.farm_block||selected.plot_code||selected.farm_plot}}</b></span></div>
     <form @submit.prevent="changeState('Blocked',blockReason.trim())"><fieldset class="mobile-form-fields" :disabled="saving">
      <div class="mobile-field"><label>Lý do vướng mắc</label><LotusMobileInput type="textarea" v-model="blockReason" rows="3" required placeholder="Ví dụ: thiếu người, thiếu vật tư hoặc trời mưa…"/></div>
      <LotusMobileButton type="submit" class="mobile-submit" :disabled="!online||!blockReason.trim()">Lưu vướng mắc →</LotusMobileButton>
     </fieldset></form>
    </template>

    <template v-else-if="screen==='assign'">
     <form @submit.prevent="previewAssign"><fieldset class="mobile-form-fields" :disabled="saving">
      <div class="mobile-field"><label>Vườn</label><MobileLinkField aria-label="Vườn" :model-value="farm" :options="farms" :searchable="false" :disabled="true"/></div>
      <div class="mobile-field"><label>Ngày thực hiện</label><LotusMobileInput aria-label="Ngày thực hiện" v-model="date" type="date" required @change="editAssign"/></div>
      <div class="mobile-field"><label>Giao cho tổ</label><MobileLinkField v-model="assignTeam" :options="teamOptions" :searchable="true" placeholder="Gõ tên tổ" required @update:modelValue="editAssign"/></div>
      <h2>Danh sách công việc</h2>
      <div v-for="(line,i) in assignLines" :key="i" class="mobile-line">
       <div class="mobile-line-title"><strong>Việc {{i+1}}</strong><LotusMobileButton v-if="assignLines.length>1" type="button" @click="assignLines.splice(i,1);editAssign()">Xóa</LotusMobileButton></div>
       <div class="mobile-field"><label>Lô lớn</label><MobileLinkField v-model="line.location" :options="locationOptions" :searchable="true" placeholder="Gõ mã Lô…" required @update:modelValue="editAssign"/></div>
       <div class="mobile-field"><label>Loại công việc</label><MobileLinkField v-model="line.work_type" :options="workOptions" :searchable="true" placeholder="Gõ tên công việc…" required @update:modelValue="line.payment_mode='';line.piecework_rate='';editAssign()"/></div>
       <div class="mobile-field"><label>Số lượng giao</label><LotusMobileInput aria-label="Số lượng giao" v-model="line.qty" type="number" min="0.000001" step="any" inputmode="decimal" required @input="editAssign"/></div>
       <div v-if="line.work_type" class="mobile-field"><label>Hình thức công</label><MobileLinkField aria-label="Hình thức công" v-model="line.payment_mode" :options="modeOptions(line.work_type)" :searchable="false" @update:modelValue="editAssign"/></div>
       <div v-if="line.work_type&&modeOptions(line.work_type).some(m=>['Piece','Both'].includes(m.value))" class="mobile-field"><label>Đơn giá khoán (đ/đơn vị, giá chuẩn {{fmt(currentRate(line.work_type))}})</label>
        <LotusMobileInput v-model="line.piecework_rate" type="number" min="0" step="any" inputmode="decimal" :placeholder="'Giá chuẩn '+fmt(currentRate(line.work_type))" @input="editAssign"/></div>
      </div>
      <LotusMobileButton type="button" class="mobile-add" :disabled="assignLines.length>=50" @click="assignLines.push(blankLine());editAssign()">＋ Thêm công việc</LotusMobileButton>
      <LotusMobileButton type="submit" class="mobile-submit" :disabled="!online">{{saving?'Đang kiểm tra…':'Xem lại kế hoạch →'}}</LotusMobileButton>
     </fieldset></form>
    </template>

    <template v-else-if="screen==='assign-preview'&&preview">
     <div class="mobile-summary">
      <span>Ngày giao <b>{{shortDate(date)}}</b></span>
      <span>Vườn <b>{{summaryName}}</b></span>
      <span>Tổ <b>{{teamOptions.find(t=>t.value===assignTeam)?.label||assignTeam}}</b></span>
      <span>Dòng giao việc <b>{{preview.lines?.length||0}}</b></span>
     </div>
     <div v-for="(line,i) in preview.lines" :key="i" class="mobile-list-card">
      <strong>{{line.work_name}}</strong><small>{{line.block_code||line.plot_code}}</small>
      <div class="mobile-inline"><span>Cần làm</span><b>{{fmt(line.planned_qty)}} {{unit(line.uom)}}</b></div>
      <small>Khoảng {{fmt(line.required_workdays)}} công dự kiến</small>
      <small v-if="line.estimated_piecework_amount">Khoán dự tính {{fmt(line.estimated_piecework_amount)}} đ</small>
      <p v-if="line.requires_approval" class="work-alert">Đơn giá cao hơn giá chuẩn: cần duyệt.</p>
     </div>
     <h2 v-if="preview.materials?.length">Vật tư dự tính</h2>
     <div v-for="m in preview.materials" :key="m.item" class="mobile-list-card"><strong>{{m.item}}</strong><div class="mobile-inline"><span>Nhu cầu</span><b>{{fmt(m.required_qty)}} {{unit(m.uom)}}</b></div></div>
     <p v-if="preview.missing_norms?.length" class="mobile-message work-warning">Chưa có định mức vật tư: {{preview.missing_norms.join(', ')}}.</p>
     <div v-if="preview.approval_required" class="mobile-field"><label>Lý do xin giá cao hơn mức chuẩn</label><LotusMobileInput type="textarea" v-model="rateReason" rows="3" required placeholder="Ghi lý do đề nghị…"/></div>
     <LotusMobileButton type="button" class="mobile-submit" :disabled="saving||!online" @click="createAssign">{{saving?'Đang lưu…':preview.approval_required?'Gửi chờ duyệt giá →':'Xác nhận giao việc →'}}</LotusMobileButton>
     <LotusMobileButton type="button" class="mobile-add" :disabled="saving" @click="go('assign')">‹ Sửa kế hoạch</LotusMobileButton>
    </template>

    <template v-else-if="screen==='queue'">
     <p class="work-muted">Chỉ những báo cáo được máy chủ nhận mới tính vào kết quả vườn.</p>
     <LotusMobileButton type="button" class="mobile-submit" :disabled="!online||saving||!pendingCount" @click="syncQueue()">{{saving?'Đang gửi…':'Gửi '+pendingCount+' báo cáo đang chờ'}}</LotusMobileButton>
     <div class="work-section"><h2>Các bản ghi trên điện thoại</h2><LotusMobileButton type="button" @click="clearSent(session.user).then(refreshQueue)">Dọn bản đã gửi</LotusMobileButton></div>
     <div v-for="r in queue" :key="r.key" class="mobile-list-card">
      <strong>{{r.event?.values?.work_plan||'Báo cáo hiện trường'}}</strong>
      <small>{{shortDate(r.event?.values?.posting_date)}} · {{r.status==='Sent'?'Đã nhận':r.status==='Discarded'?'Đã bỏ':r.status==='Error'?'Cần xử lý':'Đang chờ'}}</small>
      <p v-if="r.error" class="work-alert">{{r.error}}</p>
      <small v-if="r.result?.document">Phiếu {{r.result.document}}</small>
      <div v-if="r.status==='Error'&&online" class="work-queue-actions"><LotusMobileButton @click="checkQueue(r)">Kiểm tra đã nhận</LotusMobileButton><LotusMobileButton @click="startDiscard(r)">Bỏ bản sai</LotusMobileButton></div>
     </div>
     <p v-if="!queue.length" class="mobile-empty">Không có bản ghi trong hàng chờ.</p>
    </template>

    <template v-else-if="screen==='done'">
     <div class="mobile-done"><div class="mobile-done-icon">✓</div><h1>Hoàn tất!</h1><p>{{message}}</p><LotusMobileButton class="mobile-submit" @click="go('home')">Về trang chủ</LotusMobileButton></div>
    </template>

    <section v-if="screen==='home'&&canApprove&&planRows.some(p=>p.rate_approval_state==='Pending')">
     <div class="work-section"><h2>Cần duyệt đơn giá</h2></div>
     <div v-for="p in planRows.filter(p=>p.rate_approval_state==='Pending')" :key="p.name" class="mobile-list-card">
      <strong>{{p.name}}</strong><small>{{shortDate(p.posting_date)}} · {{p.owner}}</small>
      <div class="work-queue-actions"><LotusMobileButton :disabled="saving||!online" @click="approve(p,'Approve')">Duyệt và giao</LotusMobileButton><LotusMobileButton @click="rejection=rejection===p.name?'':p.name">Từ chối</LotusMobileButton></div>
      <div v-if="rejection===p.name" class="mobile-field"><label>Lý do từ chối</label><LotusMobileInput aria-label="Lý do từ chối" type="textarea" v-model="rejectReason" rows="2"/><LotusMobileButton class="work-outline" @click="approve(p,'Reject')">Xác nhận</LotusMobileButton></div>
     </div>
    </section>
   </template>
  </main>

  <LotusMobileDialog ref="leaveDialog" class="mobile-leave-dialog" @cancel.prevent="finishLeave(false)">
   <div class="mobile-leave-content"><h2>Rời màn hình?</h2><p>{{leaveMessage}}</p><div><LotusMobileButton type="button" autofocus @click="finishLeave(false)">Ở lại</LotusMobileButton><LotusMobileButton type="button" class="danger" @click="finishLeave(true)">Rời đi</LotusMobileButton></div></div>
  </LotusMobileDialog>
  <LotusMobileDialog ref="discardDialog" class="mobile-leave-dialog" @cancel.prevent="closeDiscard">
   <form class="mobile-leave-content" @submit.prevent="confirmDiscard">
    <h2>Bỏ báo cáo chưa nhận?</h2><p>Máy chủ phải được kiểm tra trước khi bỏ. Nhập lý do để ghi nhận.</p>
    <div class="mobile-field"><label>Lý do bỏ</label><LotusMobileInput aria-label="Lý do bỏ" type="textarea" v-model="discardReason" rows="3" required/></div>
    <div><LotusMobileButton type="button" @click="closeDiscard">Ở lại</LotusMobileButton><LotusMobileButton class="danger" type="submit" :disabled="!discardReason.trim()||saving">Xác nhận bỏ</LotusMobileButton></div>
   </form>
  </LotusMobileDialog>

 </LotusMobileShell>
</template>