<script setup>
const props=defineProps({embedded:Boolean,navigationKey:String,stockView:String,company:String,warehouse:String})
import {formatDate} from './format'
import WorkspaceModal from './components/WorkspaceModal.vue'
import {unitLabel,stockItemUomOptions} from './units'
import {updateColumnFilter,shiftISODate,hasStockSearchFilters,stockEmptyKind} from './stock-filter-state'
import WorkspaceTabs from './components/WorkspaceTabs.vue'
import LotusIcon from './components/LotusIcon.vue'
import {useDesktopWorkspace} from './use-desktop-workspace'
import {sidebarCollapsed} from './workspace'
import {computed,inject,nextTick,onMounted,onUnmounted,provide,reactive,ref,watch} from 'vue'
import {call,setCSRF} from './api'
import DataTable from './components/DataTable.vue'
import WarehousePlanning from './components/WarehousePlanning.vue'
import WarehouseReceiving from './components/WarehouseReceiving.vue'
import ProcurementField from './components/ProcurementField.vue'
import {erpHref} from './erpnext-navigation'
import StockDocumentForm from './components/StockDocumentForm.vue'
import {stockDraft,stockDraftRequest} from './stock-document'
import {stockViews,normalizeStockView} from './procurement-navigation.js'
import {routerKey,routeLocationKey} from 'vue-router'
import WorkspaceConfirm from './components/WorkspaceConfirm.vue'
import {useWorkspaceConfirm} from './use-workspace-confirm'
import WarehouseInstall from './components/WarehouseInstall.vue'
import {dismissOnBackdrop} from './dialogs'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import {Textarea as UiTextarea} from './components/ui/textarea'
import UiSelect from './components/ui/select/Select.vue'
import SigningPanel from './components/SigningPanel.vue'

const masterAPI=(name,args={},write=false)=>call('lotus_farm.warehouse_masters.'+name,args,write)
const {desktop,density,gridDensity}=useDesktopWorkspace({embedded:props.embedded})
provide('lotusDesktopDensity',gridDensity)
const router=inject(routerKey,null),route=inject(routeLocationKey,null),receivingView=ref(null)
const confirm=useWorkspaceConfirm()
const confirmOpen=confirm.open,confirmTitle=confirm.title,confirmMessage=confirm.message
const api=(name,args={},write=false)=>call('lotus_farm.warehouse.'+name,args,write)
const session=ref(null),data=ref(null),company=ref(''),warehouse=ref(''),search=ref(''),searchDraft=ref(''),start=ref(0),tab=ref(normalizeStockView(props.stockView))
const sortStock=ref([]),sortMovement=ref([]),sortDocument=ref([])
const columnFilters=ref({}),demandFrom=ref(''),demandTo=ref('')
const movementData=ref(null),movementFilters=ref({}),movementStart=ref(0),documentStart=ref(0),movementFrom=ref(''),movementTo=ref('')
const documentData=ref(null),documentFilters=ref({}),planningView=ref(null)
const busy=ref(false),saving=ref(false),error=ref(''),saved=ref(null),dialog=ref(null)
const masterEditing=ref(null),masterDeleting=ref(false),masterLists=ref({groups:[],warehouses:[]}),draftDeleting=ref(false)
const masterClearDefaults=ref(false)
const masterDialog=ref(null),masterKind=ref('item'),masterBusy=ref(false),masterError=ref(''),catalog=ref({groups:[],uoms:[],parents:[]})
const hrEmployees=ref([])
const master=reactive({name:'',code:'',group:'',uom:'',parent:'',description:'',new_group:'',group_parent:'',minimum_stock:0,pack_uom:'',pack_factor:0,lotus_address:'',lotus_contact_employee:'',lotus_contact_name:'',lotus_contact_phone:'',lotus_receiving_hours:'',lotus_default_lead_days:0,lotus_delivery_note:''})
const warehouseCode=computed(()=>{const n=String(master.name||'').trim();const abbr=session.value?.companies.find(c=>c.name===company.value)?.abbr;return n&&abbr?(n.endsWith(' - '+abbr)?n:n+' - '+abbr):n})
const employeeName=id=>hrEmployees.value.find(e=>e.value===id)?.label||''
async function loadHREmployees(){hrEmployees.value=await masterAPI('employee_choices',{company:company.value})}
const masterTitles={item:'Thêm vật tư',group:'Thêm nhóm vật tư',warehouse:'Thêm kho'}
const visibleUoms=computed(()=>stockItemUomOptions(catalog.value.uoms,[master.uom,master.pack_uom]))
const selectablePackUoms=computed(()=>visibleUoms.value.filter(u=>u.name!==master.uom))

const detailDialog=ref(null),detail=ref(null),detailError=ref(''),posting=ref(false),confirmPost=ref(false)
const kinds={receipt:'Nhập kho',issue:'Xuất kho',transfer:'Chuyển kho',count:'Kiểm kê kho'}
const quickStockActions=[{kind:'receipt',label:'Nhập kho',icon:'↓'},{kind:'issue',label:'Xuất kho',icon:'↑'},{kind:'transfer',label:'Chuyển kho',icon:'⇄'},{kind:'count',label:'Kiểm kê kho',icon:'✓'}]
const form=reactive({receipt_reason:'',supplier:'',kind:'receipt',count_purpose:'Stock Reconciliation',posting_date:'',source:'',target:'',notes:'',lines:[],issue_mode:'Manual',work_plan:'',receiver:'',receiver_employee:'',additional_costs:[],existing_name:'',base_modified:'',client_event_id:''})
// Lot codes suggested for 'Khu vực / lô sử dụng' (lotus_farm.finance.stock.block_codes): the issue's cost goes to that lot.
const blockCodes=ref([])
// Why goods come in decides the accounting (lotus_farm.finance.stock): purchase without an order waits for its invoice.
watch(()=>[form.kind,form.source],async([kind,source])=>{if(kind!=='issue')return;try{blockCodes.value=await call('lotus_farm.finance.stock.block_codes',{warehouse:source||undefined})}catch{blockCodes.value=[]}})
const issueTabs={Manual:'Thủ công',Plan:'Theo kế hoạch đã duyệt',Request:'Theo yêu cầu đã duyệt'}
const issueSources=ref([]),issueSource=ref(''),issueNote=ref(''),issueLoading=ref(false)
let issueVersion=0
const fmt=n=>Number(n||0).toLocaleString('vi-VN',{maximumFractionDigits:3})
const canCreate=computed(()=>!!company.value&&!!data.value?.warehouses.length&&!!data.value?.catalogue_count)
const stocks=computed(()=>data.value?.items||[])
const money=computed(()=>data.value?.currency||'VND')
const cash=n=>Number(n||0).toLocaleString('vi-VN',{style:'currency',currency:money.value})
const warehouseLabel=id=>data.value?.warehouses?.find(w=>w.name===id)?.warehouse_name||id||'—'

let version=0
const demandWindowDays=7
const hasStockFilters=computed(()=>hasStockSearchFilters(search.value,columnFilters.value)||!!warehouse.value)
const activeTabFilters=computed(()=>tab.value==='stock'?hasStockFilters.value:tab.value==='history'?hasStockSearchFilters(search.value,documentFilters.value)||!!movementFrom.value||!!movementTo.value||!!warehouse.value:tab.value==='movements'?hasStockSearchFilters(search.value,movementFilters.value)||!!movementFrom.value||!!movementTo.value||!!warehouse.value:false)
function clearTabFilters(){
 if(tab.value==='stock'){resetStockFilters();return}
 search.value='';searchDraft.value='';warehouse.value='';movementFrom.value='';movementTo.value=''
 if(tab.value==='history') {documentFilters.value={};sortDocument.value=[]}
 if(tab.value==='movements'){movementFilters.value={};sortMovement.value=[]}
 refresh(true)
}
const stockState=computed(()=>stockEmptyKind({
 company:company.value,warehouseCount:data.value?.warehouses?.length||0,
 catalogueCount:data.value?.catalogue_count||0,filteredCount:data.value?.total_count||0,
 loading:busy.value||!session.value||(!data.value&&!!company.value)
}))
let searchTimer=null
watch(searchDraft,value=>{
  clearTimeout(searchTimer)
  searchTimer=setTimeout(()=>{
    const term=String(value||'').trim()
    if(term!==search.value){search.value=term;refresh(true)}
  },220)
})
onUnmounted(()=>clearTimeout(searchTimer))
function applySearch(){clearTimeout(searchTimer);const term=searchDraft.value.trim();if(term!==search.value){search.value=term;refresh(true)}}
function resetStockFilters(){
 columnFilters.value={}
 search.value=''
 searchDraft.value=''
 warehouse.value=''
 sortStock.value=[]
 demandFrom.value=session.value?.today||''
 demandTo.value=shiftISODate(demandFrom.value,demandWindowDays-1)
 refresh(true)
}
function warehouseChanged(){
 columnFilters.value={}
 refresh(true)
}
async function refresh(reset=false){
 if(reset){start.value=0;movementStart.value=0;documentStart.value=0}
 if(!company.value){version++;busy.value=false;data.value=null;movementData.value=null;documentData.value=null;return}
 if(demandFrom.value&&demandTo.value&&demandFrom.value>demandTo.value){
  version++;busy.value=false
  error.value='Ngày bắt đầu phải trước hoặc bằng ngày kết thúc kỳ nhu cầu. Dữ liệu hiện tại chưa được cập nhật.'
  return
 }
 const request=++version
 busy.value=true
 error.value=''
 try{
  const result=await api('overview',{
   company:company.value,warehouse:warehouse.value,
   search:tab.value==='stock'?search.value:'',
   start:start.value,
   sort_model:JSON.stringify(sortStock.value),
   column_filters:JSON.stringify(columnFilters.value),
   from_date:demandFrom.value,to_date:demandTo.value
  })
  if(request!==version)return
  data.value=result
  if(tab.value==='stock'&&start.value>0&&!result.items?.length&&result.total_count>0){
   start.value=Math.floor((result.total_count-1)/50)*50
   return await refresh()
  }
  if(tab.value==='movements'){
   const ledger=await api('movements',{
    company:company.value,warehouse:warehouse.value,search:search.value,
    from_date:movementFrom.value,to_date:movementTo.value,
    start:movementStart.value,sort_model:JSON.stringify(sortMovement.value),
    column_filters:JSON.stringify(movementFilters.value)
   })
   if(request===version)movementData.value=ledger
  }
  if(tab.value==='history'){
   const records=await api('documents',{
    company:company.value,warehouse:warehouse.value,search:search.value,
    from_date:movementFrom.value,to_date:movementTo.value,
    start:documentStart.value,sort_model:JSON.stringify(sortDocument.value),
    column_filters:JSON.stringify(documentFilters.value)
   })
   if(request===version)documentData.value=records
  }
 }catch(e){
  // Retain the last verified response on network/validation failure, with an error.
  if(request===version)error.value='Không tải được dữ liệu mới: '+e.message
 }finally{
  if(request===version)busy.value=false
 }
}
async function initialize(){
 busy.value=true
 try{
  session.value=await api('bootstrap')
  setCSRF(session.value.csrf_token)
  company.value=props.company||session.value.companies[0]?.name||'';warehouse.value=props.warehouse||''
  if(props.stockView==='buying'){const q={company:company.value,warehouse:warehouse.value||undefined,buying_view:'orders'};if(router)await router.replace({path:'/mua-hang',query:q});else location.assign('/lotus/mua-hang?'+new URLSearchParams(Object.fromEntries(Object.entries(q).filter(([,v])=>v))));return}
  form.posting_date=session.value.today
  demandFrom.value=session.value.today
  demandTo.value=shiftISODate(session.value.today,demandWindowDays-1)
  await refresh()
 }catch(e){error.value=e.message}finally{busy.value=false}
}
function companyChanged(){
 columnFilters.value={}
 movementFilters.value={}
 documentFilters.value={}
 documentData.value=null
 movementData.value=null
 warehouse.value=''
 search.value=''
 searchDraft.value=''
 sortStock.value=[]
 saved.value=null
 data.value=null
 refresh(true)
}
let formSnapshot=''
async function closeStock(event){event?.preventDefault?.();if(saving.value)return;if(JSON.stringify(form)!==formSnapshot&&!await confirm.ask('Bỏ phiếu kho chưa lưu và đóng?'))return;dialog.value?.close()}
async function open(kind){if(kind==='issue'){try{await loadHREmployees()}catch(e){error.value=e.message;return}}issueVersion++;error.value='';saved.value=null;Object.assign(form,stockDraft(kind,{date:session.value.today,warehouse:warehouse.value||data.value.warehouses[0]?.name||''}));issueSource.value='';issueSources.value=[];issueNote.value='';issueLoading.value=false;formSnapshot=JSON.stringify(form);await nextTick();dialog.value.showModal()}
async function searchItems(search){const result=await api('overview',{company:company.value,warehouse:warehouse.value,search});return result.items.map(item=>({value:item.name,label:item.item_name,uom:item.stock_uom,uoms:item.uoms,pack_uom:item.pack_uom,pack_factor:item.pack_factor,actual_qty:item.actual_qty}))}
async function changeIssueMode(mode){const version=++issueVersion;form.issue_mode=mode;form.work_plan='';issueSource.value='';issueSources.value=[];issueNote.value='';error.value='';form.lines=mode==='Manual'?[{item:'',qty:1,area:''}]:[];issueLoading.value=mode!=='Manual';if(mode==='Manual')return;try{const result=await api('issue_sources',{company:company.value,mode});if(version===issueVersion){issueSources.value=result.rows;issueNote.value=result.note}}catch(e){if(version===issueVersion)error.value=e.message}finally{if(version===issueVersion)issueLoading.value=false}}
async function selectIssueSource(){const version=++issueVersion;form.lines=[];form.work_plan=form.issue_mode==='Plan'?issueSource.value:'';if(!issueSource.value)return;issueLoading.value=true;error.value='';try{const result=await api('issue_lines',{company:company.value,mode:form.issue_mode,name:issueSource.value});if(version===issueVersion){form.lines=result.rows.map(r=>({...r,qty:r.remaining_qty,fixed_area:!!r.area}));issueNote.value=result.note}}catch(e){if(version===issueVersion)error.value=e.message}finally{if(version===issueVersion)issueLoading.value=false}}
async function save(){
 if(saving.value)return
 saving.value=true;error.value=''
 try{saved.value=await api('create_draft',stockDraftRequest(company.value,form),true);dialog.value.close();await chooseStockTab('history');await refresh();await openDocument(saved.value.doctype,saved.value.name)}
 catch(e){error.value=e.message}
 finally{saving.value=false}
}
const status=s=>['Nháp','Đã ghi sổ','Đã hủy'][s]||s
const dateLabel=value=>formatDate(value)
const type=t=>({'Material Receipt':'Nhập kho','Material Issue':'Xuất dùng','Material Transfer':'Chuyển kho','Repack':'Đóng gói','Opening Stock':'Tồn đầu kỳ','Stock Reconciliation':'Kiểm kê'})[t]||t
async function openMaster(kind){
 if(kind==='warehouse'){try{await loadHREmployees()}catch(e){error.value=e.message;return}}
 masterError.value='';error.value='';masterKind.value=kind;masterEditing.value=null;masterDeleting.value=false;masterClearDefaults.value=false
 try{catalog.value=await api('catalogue',{company:company.value});const root=catalog.value.groups.find(g=>g.is_group&&!g.parent_item_group)?.name||catalog.value.groups.find(g=>g.is_group)?.name||''
 Object.assign(master,{name:'',code:'',group:'',uom:catalog.value.uoms.find(u=>u.name==='Kg')?.name||catalog.value.uoms[0]?.name||'',parent:kind==='warehouse'?catalog.value.parents[0]?.name||'':root,description:'',new_group:'',group_parent:root,minimum_stock:0,pack_uom:'',pack_factor:0,lotus_address:'',lotus_contact_employee:'',lotus_contact_name:'',lotus_contact_phone:'',lotus_receiving_hours:'',lotus_default_lead_days:0,lotus_delivery_note:''});await nextTick();masterDialog.value.showModal()}
 catch(e){error.value=e.message}
}
async function saveMaster(){if(masterBusy.value)return;masterBusy.value=true;masterError.value=''
 try{const result=masterEditing.value?await masterAPI('save_master',{company:company.value,kind:masterKind.value,name:masterEditing.value.id,modified:masterEditing.value.modified,values:{...master}},true):await api('create_master',{company:company.value,kind:masterKind.value,values:{...master}},true);masterDialog.value.close();saved.value={name:result.name,master:true};if(masterKind.value==='item'){search.value='';searchDraft.value='';start.value=0}await refresh();catalog.value=await api('catalogue',{company:company.value});await loadMasterLists()}
 catch(e){masterError.value=e.message}finally{masterBusy.value=false}
}
async function loadMasterLists(){if(!company.value)return;try{masterLists.value=await masterAPI('master_lists',{company:company.value})}catch(e){error.value=e.message}}
watch(tab,(value,previous)=>{if(value==='setup')loadMasterLists();if(['movements','history'].includes(value)||['movements','history'].includes(previous)){search.value='';searchDraft.value='';refresh(true)}})
async function editMaster(kind,name){await openMaster(kind);try{const result=await masterAPI('read_master',{company:company.value,kind,name});masterEditing.value=result;Object.assign(master,{name:result.name,code:result.code,group:result.group||'',uom:result.uom||'',parent:result.parent||'',description:result.description||'',minimum_stock:result.minimum_stock||0,pack_uom:result.pack_uom||'',pack_factor:result.pack_factor||0,...Object.fromEntries(['lotus_address','lotus_contact_employee','lotus_contact_name','lotus_contact_phone','lotus_receiving_hours','lotus_default_lead_days','lotus_delivery_note'].map(k=>[k,result[k]]))})}catch(e){masterError.value=e.message}}
async function deleteMaster(){if(!masterEditing.value||masterBusy.value)return;masterBusy.value=true;try{await masterAPI('delete_master',{company:company.value,kind:masterKind.value,name:masterEditing.value.id,modified:masterEditing.value.modified,clear_defaults:masterClearDefaults.value},true);masterDialog.value.close();saved.value=null;await refresh();await loadMasterLists()}catch(e){masterError.value=e.message}finally{masterBusy.value=false}}
async function editDocument(){const current=detail.value;detailDialog.value.close();const kind={'Material Receipt':'receipt','Material Issue':'issue','Material Transfer':'transfer'}[current.kind]||'count';await open(kind);Object.assign(form,{receipt_reason:current.receipt_reason||'',supplier:current.supplier||'',existing_name:current.name,base_modified:current.modified,posting_date:current.posting_date,count_purpose:current.kind,source:current.items[0]?.source||'',target:current.items[0]?.target||'',notes:current.notes||'',receiver:current.receiver||'',receiver_employee:current.receiver_employee||'',issue_mode:current.issue_mode||'Manual',additional_costs:(current.additional_costs||[]).map(row=>({...row})),lines:current.items.map(row=>({...row,rate:row.rate||0}))});formSnapshot=JSON.stringify(form)}
async function deleteDraft(){if(posting.value)return;posting.value=true;try{await api('delete_draft',{doctype:detail.value.doctype,name:detail.value.name,modified:detail.value.modified},true);detailDialog.value.close();saved.value=null;draftDeleting.value=false;await refresh()}catch(e){detailError.value=e.message}finally{posting.value=false}}
const groupColumns=[{field:'name',headerName:'Nhóm hàng'},{field:'parent_item_group',headerName:'Thuộc nhóm'}]
const warehouseColumns=[{field:'warehouse_name',headerName:'Tên kho'},{field:'name',headerName:'Mã kho'},{field:'lotus_address',headerName:'Địa chỉ kho',minWidth:220},{field:'lotus_contact_name',headerName:'Người phụ trách'},{field:'lotus_contact_phone',headerName:'Liên hệ'},{field:'lotus_default_lead_days',headerName:'Chờ hàng (ngày)'}]

async function openDocument(doctype,name){error.value='';detailError.value='';confirmPost.value=false;draftDeleting.value=false;try{detail.value=await api('document',{doctype,name});await nextTick();detailDialog.value.showModal()}catch(e){error.value=e.message}}
async function postDocument(){if(posting.value||!confirmPost.value)return;posting.value=true;detailError.value='';try{await api('submit_document',{doctype:detail.value.doctype,name:detail.value.name,modified:detail.value.modified},true);detail.value=await api('document',{doctype:detail.value.doctype,name:detail.value.name});confirmPost.value=false;await refresh()}catch(e){detailError.value=e.message}finally{posting.value=false}}

const stockNumber=(field,headerName,minWidth=100)=>({field,headerName,minWidth,type:'numericColumn',valueFormatter:p=>p.value==null?'—':fmt(p.value)})
// Natural reading order: item identity → actual stock → global minimum → demand/arrival.
const stockColumns=[
 {field:'name',valueGetter:p=>p.data.item_name,headerName:'Tên hàng',minWidth:200,flex:1.6,cellRenderer:itemCell,tooltipValueGetter:p=>p.data.item_name+' · '+p.data.name,mobileValue:r=>r.item_name+' · '+r.name},
 {field:'item_group',headerName:'Nhóm hàng',minWidth:130},
 {field:'stock_uom',headerName:'ĐVT',minWidth:78,valueFormatter:p=>unitLabel(p.value)},
 stockNumber('actual_qty','Tồn kho',105),
 {field:'pack_actual_qty',headerName:'Tồn quy đổi',minWidth:132,tooltipValueGetter:p=>p.data?.pack_uom&&p.data?.pack_factor?'1 '+unitLabel(p.data.pack_uom)+' = '+fmt(p.data.pack_factor)+' '+unitLabel(p.data.stock_uom):'Chưa có đơn vị quy đổi',valueFormatter:p=>p.data?.pack_uom&&p.value!=null?fmt(p.value)+' '+unitLabel(p.data.pack_uom):'—'},
 stockNumber('minimum_stock','Tối thiểu chung',135),
 stockNumber('shortage_qty','Thiếu tối thiểu',125),
 {field:'stock_status',headerName:'Cảnh báo tồn',minWidth:125},
 stockNumber('demand_qty','Cần dùng',100),
 stockNumber('available_qty','Có thể dùng',115),
 stockNumber('demand_shortage_qty','Thiếu theo nhu cầu',145),
 stockNumber('incoming_qty','Sắp về',95),
 stockNumber('to_buy_qty','Cần mua',100),
 {field:'coverage_status',headerName:'Tình trạng nhu cầu',minWidth:150,cellClass:p=>'lotus-coverage-state '+({'Đủ hàng':'is-covered','Chờ nhập':'is-incoming','Cần mua':'is-short'}[p.value]||'')}
]

const historyRows=computed(()=>documentData.value?.rows||[])
const historyColumns=[{field:'posting_date',headerName:'Ngày',minWidth:110,valueFormatter:p=>dateLabel(p.value)},{field:'name',headerName:'Số phiếu',minWidth:215,flex:1.5},{field:'kind',headerName:'Loại phiếu',minWidth:125},{field:'warehouses',headerName:'Kho liên quan',minWidth:210,valueFormatter:p=>String(p.value||'').split(' → ').map(warehouseLabel).join(' → ')},{field:'docstatus',headerName:'Trạng thái',minWidth:120,valueFormatter:p=>status(p.value)}]
function filterDocument({field,values}){documentFilters.value=updateColumnFilter(documentFilters.value,field,values);refresh(true)}
const movementColumns=[{field:'posting_date',headerName:'Ngày',minWidth:105,valueFormatter:p=>dateLabel(p.value)},{field:'item_code',headerName:'Tên hàng',minWidth:200,flex:1.6,valueFormatter:p=>p.data?p.data.item_name+' · '+p.value:p.value},{field:'warehouse',headerName:'Kho',minWidth:130,valueFormatter:p=>warehouseLabel(p.value)},{field:'opening_qty',headerName:'Tồn trước',minWidth:80,type:'numericColumn',valueFormatter:p=>fmt(p.value)},{field:'in_qty',headerName:'Nhập',minWidth:75,type:'numericColumn',valueFormatter:p=>fmt(p.value)},{field:'out_qty',headerName:'Xuất',minWidth:75,type:'numericColumn',valueFormatter:p=>fmt(p.value)},{field:'qty_after_transaction',headerName:'Tồn sau',minWidth:85,type:'numericColumn',valueFormatter:p=>fmt(p.value)},{field:'stock_uom',headerName:'ĐVT',minWidth:65,valueFormatter:p=>unitLabel(p.value)},{field:'voucher_no',headerName:'Số phiếu',minWidth:170},{field:'kind',headerName:'Loại biến động',minWidth:95}]
async function openStockDocument(doctype,name){if(doctype==='Purchase Receipt'){await chooseStockTab('history');await receivingView.value?.openReceipt(name)}else await openDocument(doctype,name)}
function openMovement(row){if(['Stock Entry','Stock Reconciliation','Purchase Receipt'].includes(row.voucher_type))openStockDocument(row.voucher_type,row.voucher_no);else error.value='Loại phiếu này chưa có form chi tiết trong màn hình kho.'}
const printURL=(doctype,name)=>'/lotus/in-phieu?'+new URLSearchParams({doctype,name})
const detailColumns=[{headerName:'Vật tư',minWidth:220,flex:2,valueGetter:p=>p.data.item_name||p.data.item},{field:'item',headerName:'Mã vật tư'},{field:'qty',headerName:'Số lượng',type:'numericColumn',valueFormatter:p=>fmt(p.value)},{field:'uom',headerName:'Đơn vị',valueFormatter:p=>unitLabel(p.value)},{field:'area',headerName:'Khu vực / lô'},{headerName:'Kho xuất / nhận',minWidth:220,valueGetter:p=>[p.data.source,p.data.target].filter(Boolean).map(warehouseLabel).join(' → ')}]

const receiptDetailColumns=[{field:'rate',headerName:'Đơn giá',type:'numericColumn',valueFormatter:p=>cash(p.value)},{field:'additional_cost',headerName:'Chi phí phân bổ',type:'numericColumn',valueFormatter:p=>cash(p.value)},{field:'amount',headerName:'Thành tiền',type:'numericColumn',valueFormatter:p=>cash(p.value)}]
onMounted(initialize)
function filterStock({field,values}){columnFilters.value=updateColumnFilter(columnFilters.value,field,values);refresh(true)}
const stockTabs=stockViews
const canSetup=computed(()=>['Item','Item Group','Warehouse'].some(dt=>session.value?.permissions?.[dt]))
async function chooseStockTab(value){if(hasChanges()&&!await confirm.ask('Bỏ phần chưa lưu và chuyển mục?'))return;discardChanges();tab.value=normalizeStockView(value);if(router)await router.push({path:'/kho',query:{...route.query,stock_view:tab.value,company:company.value,warehouse:warehouse.value||undefined}})}
function hasChanges(){return !!dialog.value?.open||!!masterDialog.value?.open||!!receivingView.value?.hasChanges()||!!planningView.value?.hasChanges()}
function discardChanges(){dialog.value?.close();masterDialog.value?.close();receivingView.value?.discardChanges();planningView.value?.discardChanges()}
defineExpose({hasChanges,discardChanges,scopeParams:()=>({company:company.value,warehouse:warehouse.value||undefined})})
watch(()=>props.stockView,value=>{const next=normalizeStockView(value);if(next!==tab.value)tab.value=next})
watch(()=>props.company,value=>{if(value&&value!==company.value){company.value=value;companyChanged()}})
watch(()=>props.warehouse,value=>{if((value||'')!==warehouse.value){warehouse.value=value||'';refresh(true)}})
const desktopNavIcons={stock:'boxes',planning:'list',buying:'cart',history:'document',movements:'transfer',setup:'settings'}
const desktopActionIcons={receipt:'receive',issue:'issue',transfer:'transfer',count:'check'}
async function createPurchase(){const query={company:company.value,warehouse:warehouse.value||undefined,buying_view:'orders',action:'create_order'};if(router)await router.push({path:'/mua-hang',query});else location.assign('/lotus/mua-hang?'+new URLSearchParams(Object.fromEntries(Object.entries(query).filter(([,v])=>v))))}
async function quickAction(kind){if(kind==='receipt'){await receivingView.value.openPicker();return}return open(kind)}

const warehousePwa=window.location.pathname.replace(/\/$/,'')==='/warehouse'
function itemCell(params){const cell=document.createElement('span');cell.className='lotus-item-cell';for(const [cls,text] of [['name',params.data.item_name],['code',params.data.name]]){const span=document.createElement('span');span.className=cls;span.textContent=text;cell.append(span)}return cell}
</script>

<template>
 <div class="stock-shell lotus-ui" :class="{'embedded-workspace':embedded,'sidebar-collapsed':sidebarCollapsed,'warehouse-pwa':warehousePwa,'lotus-desktop':desktop,'desktop-compact':density==='compact'}">


  <component :is="embedded?'section':'main'" class="stock-main"><div class="stock-navigation"><WorkspaceTabs v-if="embedded" :items="Object.entries(stockTabs).map(([id,label])=>({id,label}))" :model-value="tab" @update:model-value="chooseStockTab"/><UiButton v-if="canSetup" variant="outline" @click="chooseStockTab(tab==='setup'?'stock':'setup')">{{tab==='setup'?'Về tồn kho':'Thiết lập kho'}}</UiButton><UiButton as="a" variant="outline" :href="erpHref('Stock',company,warehouse)">ERPNext Kho</UiButton></div><WarehouseInstall v-if="warehousePwa"/>

   <p v-if="error&&!dialog?.open" class="stock-error" role="alert">{{error}}</p>
   <p v-if="saved" class="stock-success" role="status">{{saved.master?"Đã lưu danh mục":"Đã lưu nháp"}} <strong>{{saved.name}}</strong>. <UiButton variant="ghost" v-if="!saved.master" class="stock-text-button" @click="openDocument(saved.doctype,saved.name)">Xem phiếu →</UiButton></p>
   <div v-if="tab!=='buying'&&(!desktop||tab!=='planning')" class="stock-scope"><label v-if="tab!=='setup'">Kho<UiSelect v-model="warehouse" :disabled="!company||busy" @change="warehouseChanged()"><option value="">Tất cả kho được phân quyền</option><option v-for="w in data?.warehouses" :key="w.name" :value="w.name">{{w.warehouse_name}}</option></UiSelect></label><label v-if="(session?.companies?.length||0)>1">Công ty<UiSelect v-model="company" @change="companyChanged"><option v-if="!session?.companies.length" value="">Chưa có công ty</option><option v-for="c in session?.companies" :key="c.name" :value="c.name">{{c.name}}</option></UiSelect></label><UiButton v-if="['stock','history','movements'].includes(tab)&&activeTabFilters" variant="outline" class="stock-button" @click="clearTabFilters">Bỏ lọc</UiButton><div v-if="tab==='history'||tab==='movements'" class="stock-date-filters"><label>Từ ngày<UiInput v-model="movementFrom" type="date" @change="refresh(true)"/></label><label>Đến ngày<UiInput v-model="movementTo" type="date" @change="refresh(true)"/></label></div><UiButton v-if="tab!=='stock'" variant="outline" class="stock-button" :disabled="busy" @click="tab==='planning'?planningView?.refresh():refresh()">{{busy?'Đang tải':'Làm mới'}}</UiButton><div v-if="['stock','movements','history'].includes(tab)" class="stock-search stock-search--instant"><UiInput v-model="searchDraft" aria-label="Tìm vật tư" :placeholder="tab==='stock'?'Tìm vật tư…':tab==='history'?'Tìm phiếu…':'Tìm vật tư/phiếu…'" /></div></div>
   <div v-if="['stock','history'].includes(tab)" class="stock-quick-actions" role="group" aria-label="Thao tác kho nhanh">
    <UiButton v-if="desktop||embedded" variant="outline" class="stock-quick-action desktop-purchase-action" :disabled="!company||busy||!session?.permissions['Purchase Order']" @click="createPurchase"><span class="stock-quick-action-icon" aria-hidden="true"><LotusIcon name="cart"/></span><span>Tạo đơn mua</span></UiButton>
    <UiButton v-for="action in quickStockActions" :key="action.kind" variant="outline" class="stock-quick-action"
      :disabled="!canCreate||busy||!session?.permissions[action.kind==='receipt'?'Purchase Receipt':action.kind==='count'?'Stock Reconciliation':'Stock Entry']"
      @click="quickAction(action.kind)"><span class="stock-quick-action-icon" aria-hidden="true"><LotusIcon :name="desktopActionIcons[action.kind]"/></span><span>{{action.kind==='receipt'?'Nhập theo đơn':action.label}}</span></UiButton>
    <UiButton variant="outline" class="stock-quick-action" :disabled="!canCreate||busy||!session?.permissions['Stock Entry']" @click="open('receipt')"><LotusIcon name="download"/>Nhập không theo đơn</UiButton>
   </div>
   <section v-if="tab==='stock'" class="stock-panel stock-inventory-table">
    <DataTable :rows="stocks" :columns="stockColumns" :show-empty-headers="(data?.catalogue_count??0)>0"
      server-sort @sort="model=>{sortStock=model;refresh(true)}" interactive @open="row=>editMaster('item',row.name)"
      :filter-values="data?.filter_values" :server-filters="columnFilters" @filter="filterStock" :loading="busy"
      :empty="stockState==='no-company'?'Chọn công ty để xem tồn kho.':stockState==='no-warehouse'?'Chưa có kho hoạt động.':stockState==='no-items'?'Chưa có vật tư trong danh mục.':'Không có vật tư khớp bộ lọc. Bỏ lọc để xem lại danh sách.'" />
    <footer class="stock-pagination">
      <span>{{data?.total_count?start+1:0}}–{{start+(stocks.length||0)}} / {{data?.total_count??0}} vật tư</span>
      <div>
        <UiButton variant="outline" class="stock-button" :disabled="!start||busy" @click="start-=50;refresh()">← Trước</UiButton>
        <UiButton variant="outline" class="stock-button" :disabled="!data?.has_more||busy" @click="start+=50;refresh()">Sau →</UiButton>
      </div>
    </footer>
   </section>
   <WarehousePlanning v-if="tab==='planning'" ref="planningView" :company="company" :warehouse="warehouse" :today="session?.today" :confirm="confirm.ask">
    <template v-if="desktop" #scope><label class="desktop-warehouse-scope">Kho<UiSelect v-model="warehouse" :disabled="!company||busy" @change="warehouseChanged()"><option value="">Tất cả kho được phân quyền</option><option v-for="w in data?.warehouses" :key="w.name" :value="w.name">{{w.warehouse_name}}</option></UiSelect></label><label v-if="(session?.companies?.length||0)>1">Công ty<UiSelect v-model="company" @change="companyChanged"><option v-for="c in session?.companies" :key="c.name" :value="c.name">{{c.name}}</option></UiSelect></label></template>
    <template v-if="desktop" #actions><UiButton variant="outline" :disabled="busy" @click="planningView?.refresh()">Làm mới</UiButton></template>
   </WarehousePlanning>
   <section v-if="tab==='history'" class="stock-panel"><DataTable :rows="historyRows" :columns="historyColumns" show-empty-headers empty="Không có phiếu phù hợp. Thử bỏ lọc hoặc thay đổi khoảng ngày." server-sort @sort="model=>{sortDocument=model;refresh(true)}" :loading="busy" :filter-values="documentData?.filter_values" :server-filters="documentFilters" @filter="filterDocument" interactive @open="row=>openStockDocument(row.doctype,row.name)"/><footer class="stock-pagination"><span>{{documentData?.total_count?documentStart+1:0}}–{{documentStart+(documentData?.rows?.length||0)}} / {{documentData?.total_count||0}} phiếu</span><div><UiButton variant="outline" :disabled="!documentStart||busy" @click="documentStart-=50;refresh()">← Trước</UiButton><UiButton variant="outline" :disabled="!documentData?.has_more||busy" @click="documentStart+=50;refresh()">Sau →</UiButton></div></footer></section>
   <template v-if="tab==='movements'">
    <section class="stock-panel"><DataTable :rows="movementData?.rows||[]" :columns="movementColumns" show-empty-headers server-sort @sort="model=>{sortMovement=model;refresh(true)}" :loading="busy" :filter-values="movementData?.filter_values" :server-filters="movementFilters" @filter="filterMovement" interactive @open="openMovement" empty="Không có phát sinh nhập xuất phù hợp. Thử bỏ lọc hoặc thay đổi ngày."/><footer class="stock-pagination"><span>{{movementData?.total_count?movementStart+1:0}}–{{movementStart+(movementData?.rows.length||0)}} / {{movementData?.total_count||0}} phát sinh</span><div><UiButton variant="outline" class="stock-button" :disabled="!movementStart||busy" @click="movementStart-=50;refresh()">← Trước</UiButton><UiButton variant="outline" class="stock-button" :disabled="!movementData?.has_more||busy" @click="movementStart+=50;refresh()">Sau →</UiButton></div></footer></section>
   </template>
   <div v-if="tab==='setup'" class="stock-setup-toolbar" role="group" aria-label="Quản lý danh mục kho">
    <UiButton variant="outline" :disabled="!company||!session?.permissions['Item Group']" @click="openMaster('group')">+ Thêm nhóm hàng</UiButton>
    <UiButton variant="outline" :disabled="!company||!session?.permissions.Item" @click="openMaster('item')">+ Thêm vật tư</UiButton>
    <UiButton variant="outline" :disabled="!company||!session?.permissions.Warehouse" @click="openMaster('warehouse')">+ Thêm kho</UiButton>
   </div>
   <div v-if="tab==='setup'" class="stock-setup-grids">
    <section class="stock-panel">
     <header class="stock-list-heading"><h2>Nhóm hàng</h2><span>{{masterLists.groups?.length||0}} nhóm</span></header>
     <DataTable :rows="masterLists.groups||[]" :columns="groupColumns" show-empty-headers interactive @open="row=>editMaster('group',row.name)" empty="Chưa có nhóm hàng."/>
    </section>
    <section class="stock-panel">
     <header class="stock-list-heading"><h2>Danh sách kho</h2><span>{{masterLists.warehouses?.length||0}} kho</span></header>
     <DataTable :rows="masterLists.warehouses||[]" :columns="warehouseColumns" show-empty-headers interactive @open="row=>editMaster('warehouse',row.name)" empty="Chưa khai báo kho."/>
    </section>
   </div>

   <nav v-if="warehousePwa" class="warehouse-pwa-bottom-nav" aria-label="Điều hướng Kho điện thoại">
    <button v-for="(label,id) in stockTabs"
      :key="id" type="button" :class="{active:tab===id}" @click="chooseStockTab(id)">{{label}}</button>
   </nav>
  </component>
  <WarehouseReceiving ref="receivingView" :company="company" :warehouse="warehouse" :today="session?.today" :confirm="confirm.ask" @changed="refresh"/>
  <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" @answer="confirm.finish"/>
  <WorkspaceModal bare title="Phiếu kho" :busy="saving" ref="dialog" class="stock-dialog stock-document-dialog" @cancel="closeStock">
   <header><div><h2>{{kinds[form.kind]}}</h2></div><UiButton variant="outline" type="button" class="stock-button" aria-label="Đóng" :disabled="saving" @click="closeStock">✕</UiButton></header><p v-if="error" class="stock-error" role="alert">{{error}}</p>
   <StockDocumentForm :model-value="form" :company="company" :items="stocks" :warehouses="data?.warehouses||[]" :employees="hrEmployees" :blocks="blockCodes" :fetch-items="searchItems" :currency="money" :saving="saving" :loading="issueLoading" @update:model-value="Object.assign(form,$event)" @submit="save" @error="error=$event">
    <template #source><section v-if="form.kind==='issue'" class="stock-issue-picker">
     <div class="stock-issue-tabs" role="tablist" aria-label="Hình thức xuất kho"><UiButton variant="outline" v-for="(title,mode) in issueTabs" :key="mode" type="button" role="tab" :aria-selected="form.issue_mode===mode" :class="{active:form.issue_mode===mode}" :disabled="saving" @click="changeIssueMode(mode)">{{title}}</UiButton></div>

     <ProcurementField v-if="form.issue_mode!=='Manual'" v-model="issueSource" :label="form.issue_mode==='Plan'?'Kế hoạch đã duyệt':'Yêu cầu vật tư đã duyệt'" :options="issueSources.map(r=>({value:r.name,label:r.name+' · '+r.date}))" :disabled="issueLoading||saving" required @update:model-value="selectIssueSource"/>
     <p v-if="form.issue_mode!=='Manual'&&!issueLoading&&!issueSources.length" class="stock-source-empty">{{form.issue_mode==='Plan'?'Chưa có kế hoạch đã duyệt trong công ty này.':'Chưa có yêu cầu cấp vật tư đã duyệt trong công ty này.'}}</p>
     <p v-if="issueNote" class="stock-muted">{{issueNote}}</p>
    </section></template>
    <template #empty><p v-if="form.kind==='issue'&&form.issue_mode!=='Manual'&&issueSource&&!issueLoading&&!form.lines.length" class="stock-source-empty">Nguồn này không còn nhu cầu vật tư được cấp.</p></template>
   </StockDocumentForm>
  </WorkspaceModal>
  <WorkspaceModal bare title="Danh mục kho" :busy="masterBusy" ref="masterDialog" class="stock-dialog stock-master-dialog" @cancel="masterError=''">
   <form @submit.prevent="saveMaster"><header><div><h2>{{masterEditing?masterTitles[masterKind].replace('Thêm','Sửa'):masterTitles[masterKind]}}</h2></div><UiButton variant="outline" type="button" class="stock-button" aria-label="Đóng form danh mục" :disabled="masterBusy" @click="masterDialog.close()">✕</UiButton></header>
    <div v-if="masterDeleting" class="delete-confirm"><p>Xóa danh mục này? Hệ thống chỉ cho xóa khi chưa được sử dụng.</p><label v-if="masterKind==='warehouse'&&(masterEditing?.default_item_count||masterEditing?.stock_default)" class="stock-confirm"><input v-model="masterClearDefaults" type="checkbox">Gỡ kho mặc định của {{masterEditing?.default_item_count||0}} vật tư{{masterEditing?.stock_default?' và thiết lập kho chung':''}} trước khi xóa</label><UiButton variant="outline" @click="masterDeleting=false">Giữ lại</UiButton><UiButton variant="destructive" :disabled="masterBusy||(masterKind==='warehouse'&&(masterEditing?.default_item_count||masterEditing?.stock_default)&&!masterClearDefaults)" @click="deleteMaster">Xác nhận xóa</UiButton></div><p v-if="masterError" role="alert" class="stock-error">{{masterError}}</p>
    <fieldset class="stock-master-fields" :disabled="masterBusy||(masterEditing&&!masterEditing.can_write)"><label v-if="masterKind==='item'">Mã vật tư<UiInput :readonly="!!masterEditing" v-model="master.code" maxlength="140" placeholder="VD: PB-NPK-001" required /></label><label>{{masterKind==='item'?'Tên vật tư':masterKind==='group'?'Tên nhóm vật tư':'Tên kho'}}<UiInput v-model="master.name" maxlength="140" :placeholder="masterKind==='item'?'VD: Phân NPK 16-16-8':masterKind==='group'?'VD: Phân bón':'VD: Kho phân bón farm'" required /></label>
     <template v-if="masterKind==='item'"><label>Nhóm vật tư<UiSelect v-model="master.group" :required="!master.new_group" :disabled="!!master.new_group"><option value="">Chọn nhóm</option><option v-for="g in catalog.groups" :key="g.name" :value="g.name">{{g.name}}</option></UiSelect></label><label v-if="!masterEditing&&session?.permissions['Item Group']">Hoặc tạo nhóm mới<UiInput v-model="master.new_group" maxlength="140" placeholder="Để trống nếu dùng nhóm đã có" /></label><label>Đơn vị tồn kho gốc<UiSelect v-model="master.uom" required><option value="">Chọn đơn vị</option><option v-for="u in visibleUoms" :key="u.name" :value="u.name">{{unitLabel(u.name)}}</option></UiSelect></label><label>Tồn tối thiểu chung toàn bộ kho ({{unitLabel(master.uom)}})<UiInput v-model.number="master.minimum_stock" type="number" min="0" step="any" required/><small>Áp dụng trên tổng tồn các kho của công ty, không chọn kho riêng.</small></label><label>Đơn vị đóng gói / quy đổi<UiSelect v-model="master.pack_uom"><option value="">Không sử dụng đơn vị phụ</option><option v-for="u in selectablePackUoms" :key="u.name" :value="u.name">{{unitLabel(u.name)}}</option></UiSelect></label><label v-if="master.pack_uom">1 {{unitLabel(master.pack_uom)}} = bao nhiêu {{unitLabel(master.uom)}}?<UiInput v-model.number="master.pack_factor" type="number" min="0.000001" step="any" required/><small v-if="Number(master.pack_factor)>0">Ví dụ: 1 {{unitLabel(master.pack_uom)}} = {{fmt(master.pack_factor)}} {{unitLabel(master.uom)}}. Quy đổi theo từng vật tư.</small></label><label>Ghi chú (không bắt buộc)<UiTextarea v-model="master.description" maxlength="2000" placeholder="Quy cách đóng gói, thông tin nhận biết…"></UiTextarea></label></template>
     <label v-if="!masterEditing&&masterKind==='group'&&catalog.groups.filter(g=>g.is_group).length>1">Nhóm cha<UiSelect v-model="master.parent" required><option v-for="g in catalog.groups.filter(g=>g.is_group)" :key="g.name" :value="g.name">{{g.name}}</option></UiSelect></label>
     <template v-if="masterKind==='warehouse'">
      <label>Mã kho (tự sinh theo tên)<UiInput :model-value="warehouseCode" readonly/><small>Mã theo tên kho và viết tắt công ty; khi đổi tên kho, ERPNext cập nhật liên kết liên quan.</small></label>
      <label>Địa chỉ kho / điểm nhận hàng<UiTextarea v-model="master.lotus_address" maxlength="500" placeholder="Địa chỉ giao hàng, xã, tỉnh, hướng dẫn đến cổng kho"/></label>
      <label>Người phụ trách kho (nhân sự HRMS)<UiSelect v-model="master.lotus_contact_employee"><option value="">Chưa phân công</option><option v-for="employee in hrEmployees" :key="employee.value" :value="employee.value">{{employee.label}}</option></UiSelect><small v-if="master.lotus_contact_employee">{{employeeName(master.lotus_contact_employee)}}</small><small v-if="!hrEmployees.length">Chưa có nhân sự đang làm việc, cần tiếp nhận tại module Nhân sự.</small></label>
      <label>Số điện thoại người phụ trách<UiInput :model-value="master.lotus_contact_phone" readonly placeholder="Tự lấy từ hồ sơ HRMS"/><small>Đồng bộ theo hồ sơ nhân sự khi lưu; không nhập thủ công.</small></label>
      <label>Giờ nhận hàng<UiInput v-model="master.lotus_receiving_hours" maxlength="140" placeholder="Ví dụ: Thứ Hai–Thứ Bảy, 7:00–17:00"/></label>
      <label>Thời gian chờ hàng mặc định (ngày)<UiInput v-model.number="master.lotus_default_lead_days" type="number" min="0" max="365" step="1"/><small>Chỉ dùng để gợi ý, ngày giao do NCC xác nhận sẽ được ưu tiên.</small></label>
      <label>Ghi chú giao nhận<UiTextarea v-model="master.lotus_delivery_note" maxlength="500" placeholder="Cổng giao hàng, giờ nghỉ, yêu cầu bốc dỡ…"/></label>
     </template>
     <label v-if="!masterEditing&&masterKind==='warehouse'&&catalog.parents.length>1">Thuộc nhóm kho<UiSelect v-model="master.parent" required><option value="">Chọn nhóm kho</option><option v-for="w in catalog.parents" :key="w.name" :value="w.name">{{w.warehouse_name}}</option></UiSelect></label>
    </fieldset><footer><UiButton v-if="masterEditing?.can_delete" variant="destructive" :disabled="masterBusy" @click="masterDeleting=true">Xóa danh mục</UiButton><UiButton v-if="!masterEditing||masterEditing.can_write" variant="default" type="submit" class="stock-button primary" :disabled="masterBusy">{{masterBusy?'Đang lưu…':'Lưu '+(masterKind==='item'?'vật tư':masterKind==='group'?'nhóm':'kho')}}</UiButton></footer>
   </form>
  </WorkspaceModal>
  <WorkspaceModal bare title="Chi tiết phiếu kho" :busy="posting" ref="detailDialog" class="stock-dialog" @cancel="detailError=''">
   <form v-if="detail" @submit.prevent="postDocument"><header><div><h2>{{detail.name}}</h2></div><UiButton variant="outline" type="button" class="stock-button" aria-label="Đóng chi tiết phiếu" :disabled="posting" @click="detailDialog.close()">✕</UiButton></header><div class="actions"><a :href="printURL(detail.doctype,detail.name)" target="_blank" rel="noopener" class="stock-button">In phiếu</a></div><div v-if="detail.docstatus===0" class="actions"><UiButton v-if="detail.can_write&&(detail.kind!=='Material Issue'||!detail.issue_mode||detail.issue_mode==='Manual')" variant="outline" :disabled="posting" @click="editDocument">Sửa phiếu nháp</UiButton><UiButton v-if="detail.can_delete" variant="destructive" :disabled="posting" @click="draftDeleting=true">Xóa phiếu nháp</UiButton></div><div v-if="draftDeleting" class="delete-confirm"><span>Xác nhận xóa phiếu nháp?</span><UiButton variant="outline" @click="draftDeleting=false">Giữ lại</UiButton><UiButton variant="destructive" :disabled="posting" @click="deleteDraft">Xác nhận xóa</UiButton></div><p class="stock-muted">{{type(detail.kind)}} · {{detail.posting_date}} · {{detail.company}} · {{status(detail.docstatus)}}</p><p v-if="detailError" class="stock-error" role="alert">{{detailError}}</p><p v-if="detail.docstatus===1" class="stock-success" role="status">Phiếu đã ghi sổ. Tồn kho đã được cập nhật.</p><SigningPanel v-if="detail.docstatus===1" :doctype="detail.doctype" :name="detail.name" :company="detail.company" @notice="detailError=''" @error="detailError=$event"/>
   <DataTable :rows="detail.items" :columns="detail.kind==='Material Receipt'?[...detailColumns,...receiptDetailColumns]:detailColumns" /><template v-if="detail.kind==='Material Receipt'"><div class="receipt-totals"><span>Tiền vật tư <strong>{{cash(detail.basic_total)}}</strong></span><span>Chi phí <strong>{{cash(detail.additional_total)}}</strong></span><span>Giá trị nhập <strong>{{cash(detail.incoming_total)}}</strong></span></div><div v-if="detail.additional_costs?.length" class="receipt-detail-costs"><div v-for="(cost,index) in detail.additional_costs" :key="index"><span>{{cost.description}}</span><strong>{{cash(cost.amount)}}</strong></div></div><p class="stock-muted">Giá trị nhập gồm chi phí phân bổ. Công nợ nhà cung cấp ghi nhận bằng hóa đơn mua hàng.</p></template><p v-if="detail.receiver" class="stock-muted">Người nhận: {{detail.receiver}} · {{issueTabs[detail.issue_mode]}}</p><p v-if="detail.notes" class="stock-muted">{{detail.notes}}</p>
   <footer v-if="detail.can_submit"><label class="stock-confirm"><input v-model="confirmPost" type="checkbox" required> Tôi đã kiểm tra phiếu. Ghi sổ sẽ cập nhật tồn kho.</label><UiButton variant="default" type="submit" class="stock-button primary" :disabled="posting||!confirmPost">{{posting?'Đang ghi sổ…':'Ghi sổ phiếu'}}</UiButton></footer><p v-else-if="detail.docstatus===0" class="stock-muted">Tài khoản chưa có quyền ghi sổ hoặc phiếu thuộc nghiệp vụ nâng cao chưa hỗ trợ ở đây.</p>
   </form>
  </WorkspaceModal>
 </div>
</template>
