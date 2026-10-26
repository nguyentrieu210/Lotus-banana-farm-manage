<script setup>
import {unitLabel} from '../units'
import {stateLabel} from '../labels'
import '../procurement.css'
import {computed,inject,onMounted,onUnmounted,ref,watch} from 'vue'
import {routerKey,routeLocationKey} from 'vue-router'
import {normalizeBuyingView} from '../procurement-navigation'
import ProcurementMasters from './ProcurementMasters.vue'
import ProcurementMasterForm from './ProcurementMasterForm.vue'
import WarehouseReceiving from './WarehouseReceiving.vue'
import {Cell,CellGroup} from 'vant'
import {call,upload,setCSRF} from '../api'
import {Button} from './ui/button'
import {Checkbox} from './ui/checkbox'
import {DateRangePicker} from './ui/date-picker'
import DataTable from './DataTable.vue'
import ListPage from './ListPage.vue'
import LotusField from './form/LotusField.vue'
import FormGrid from './form/FormGrid.vue'
import FormSection from './form/FormSection.vue'
import LineItemsEditor from './form/LineItemsEditor.vue'
import ResponsiveForm from './form/ResponsiveForm.vue'
import WorkspaceConfirm from './WorkspaceConfirm.vue'
import ProcurementSigners from './ProcurementSigners.vue'
import ProcurementDocumentForm from './ProcurementDocumentForm.vue'
import MobilePurchaseOrderForm from './MobilePurchaseOrderForm.vue'
import MobilePurchaseOrderDetail from './MobilePurchaseOrderDetail.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileFeedback from './LotusMobileFeedback.vue'
import WorkspaceModal from './WorkspaceModal.vue'
import LotusMobileDialog from './LotusMobileDialog.vue'
import {newPurchaseDraft,purchasePayload,purchaseFromRequest} from '../mobile-purchase'
import {procurementTabs,purchaseKinds,money,newKey,quoteChoices,docUrl,purchaseRequest} from '../procurement'
import {toast} from '../use-toast'
import {useWorkspaceConfirm} from '../use-workspace-confirm'
import {useMobileConfirm} from '../use-mobile-confirm'

const props=defineProps({company:String,warehouse:String,today:String,mobile:Boolean,embedded:Boolean,buyingView:String,navigationKey:String,initialSupplier:String})
const api=(method,args={},write=false)=>purchaseRequest(call,'lotus_farm.procurement.'+method,args,write)
const method=(module,name,args={},write=false)=>purchaseRequest(call,'lotus_farm.'+module+'.'+name,args,write)
const router=inject(routerKey,null),route=inject(routeLocationKey,null)
const masterView=ref(null),quickMaster=ref(''),quickLine=ref(0),masterDialog=ref(null),masterSaving=ref(null),receivingView=ref(null)
const queryStart=ref(0),queryTotal=ref(0),queryMore=ref(false),queryState=ref(''),fromDate=ref(''),toDate=ref(''),debt=ref(null),fundingRows=ref([]),deliveryReason=ref(''),deliveryDate=ref('')
const isPaged=computed(()=>['invoices','payments','payables'].includes(tab.value))
const isMaster=computed(()=>['suppliers','items'].includes(tab.value))
const button=computed(()=>props.mobile?LotusMobileButton:Button)
// Links look like buttons on desktop; the phone PWA keeps plain links.
const link=computed(()=>props.mobile?'a':Button)
const company=ref(props.company||''),session=ref(null),catalog=ref(null),tab=ref(props.buyingView?normalizeBuyingView(props.buyingView):props.embedded?'orders':'needs'),rows=ref([])
const busy=ref(false),saving=ref(false),error=ref(''),notice=ref(''),search=ref(''),form=ref(''),draft=ref(null),key=ref('')
const pendingOnly=ref(false)
const current=ref(null),chain=ref(null),detailType=ref(''),signerOptions=ref(null),signers=ref({}),selections=ref({}),finance=ref(null)
const period=ref((props.today||new Date().toISOString().slice(0,10)).slice(0,7)),asof=ref(props.today||new Date().toISOString().slice(0,10)),farm=ref(''),supplier=ref(props.initialSupplier||''),kind=ref(''),report=ref(null)
const sourceType=ref('Purchase Invoice'),source=ref(''),amount=ref(''),mode=ref('bank'),reference=ref(''),date=ref(asof.value)
const payerType=ref('Employee'),payer=ref(''),classification=ref('Reimbursable'),notes=ref(''),evidence=ref(null),duplicateReason=ref(''),allocations=ref([])
const bill=ref(''),billdate=ref(asof.value),dueDate=ref(asof.value),quantities=ref({}),receiveInfo=ref(null),fundingName=ref('')
const file=ref(null),fileUrl=ref(''),preview=ref(null),mappings=ref({}),importWarehouse=ref(props.warehouse||'')
const workspaceConfirm=useWorkspaceConfirm(),mobileConfirm=useMobileConfirm()
const confirmOpen=workspaceConfirm.open,confirmTitle=workspaceConfirm.title,confirmMessage=workspaceConfirm.message
const mobileDialog=mobileConfirm.dialog,mobileMessage=mobileConfirm.message
const visibleTabs=computed(()=>procurementTabs.filter(([k])=>k!=='payments'||catalog.value?.can_view_finance).filter(([k])=>!['invoices','payables','reports','payments'].includes(k)||catalog.value?.can_view_finance).filter(([k])=>k!=='invoices'||catalog.value?.can_invoice))
const options=(values,label)=>values?.map(r=>({value:r.name,label:r[label]||r.name}))||[]
const shownRows=computed(()=>rows.value.filter(r=>(!pendingOnly.value||tab.value!=='orders'||r.docstatus===1&&Number(r.remaining_lines)>0&&r.status!=='Đã đóng')&&(!supplier.value||['reports','payables','payments','invoices'].includes(tab.value)||r.supplier===supplier.value)&&(!search.value||Object.values(r).filter(x=>typeof x!=='object').join(' ').toLocaleLowerCase().includes(search.value.toLocaleLowerCase()))))
const columns=computed(()=>tab.value==='invoices'?[{field:'name',headerName:'Hóa đơn',minWidth:180},{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:180},{field:'bill_no',headerName:'Số hóa đơn NCC'},{field:'date',headerName:'Ngày ghi sổ'},{field:'due_date',headerName:'Hạn thanh toán'},{field:'amount',headerName:'Tổng tiền',valueFormatter:p=>money(p.value)},{field:'outstanding_amount',headerName:'Còn nợ',valueFormatter:p=>money(p.value)},{field:'status',headerName:'Trạng thái',valueFormatter:p=>stateLabel(p.value)}]:tab.value==='payments'?[{field:'name',headerName:'Chứng từ',minWidth:180,valueGetter:p=>p.data.voucher_name||p.data.name},{field:'kind',headerName:'Loại giao dịch',minWidth:180},{field:'supplier',headerName:'Nhà cung cấp'},{field:'date',headerName:'Ngày'},{field:'amount',headerName:'Số tiền',valueFormatter:p=>money(p.value)},{field:'status',headerName:'Trạng thái',valueFormatter:p=>stateLabel(p.value)}]:tab.value==='payables'?[{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:190},{field:'name',headerName:'Chứng từ',minWidth:170},{field:'bill_no',headerName:'Hóa đơn NCC'},{field:'due_date',headerName:'Hạn trả'},{field:'amount',headerName:'Còn nợ / dư trả',valueFormatter:p=>money(p.value)},{field:'overdue_days',headerName:'Ngày quá hạn'},{field:'status',headerName:'Tình trạng',valueFormatter:p=>stateLabel(p.value)}]:tab.value==='quotes'?[
 {field:'choice',headerName:'Chọn',width:85},{field:'item_name',headerName:'Mặt hàng',minWidth:170},{field:'supplier',headerName:'Nhà cung cấp',minWidth:150},
 {field:'quotation',headerName:'Báo giá'},{field:'stock_qty',headerName:'SL ĐVT kho'},{field:'stock_uom',headerName:'ĐVT kho',valueFormatter:p=>unitLabel(p.value)},
 {field:'unit_cost',headerName:'Giá đủ/ĐVT kho',valueFormatter:p=>money(p.value)},
 {field:'net',headerName:'Chưa thuế',valueFormatter:p=>money(p.value)},{field:'tax',headerName:'VAT',valueFormatter:p=>money(p.value)},
 {field:'freight',headerName:'Vận chuyển',valueFormatter:p=>money(p.value)},{field:'gross',headerName:'Tổng trả',valueFormatter:p=>money(p.value)},
 {field:'delivery_date',headerName:'Ngày giao'},{field:'valid_till',headerName:'Hiệu lực'},
 {field:'reason',headerName:'Lý do chọn',minWidth:210}]:tab.value==='reports'?[
 {field:'date',headerName:'Ngày'},{field:'stage_label',headerName:'Giai đoạn',minWidth:170},{field:'name',headerName:'Chứng từ',minWidth:170},
 {field:'supplier',headerName:'Nhà cung cấp'},{field:'item_name',headerName:'Mặt hàng',minWidth:180},
 {field:'amount',headerName:'Số tiền',valueFormatter:p=>money(p.value)}]:[
 {field:'name',headerName:'Số chứng từ',minWidth:180},{field:'supplier_name',headerName:'Nhà cung cấp',valueGetter:p=>p.data.supplier_name||p.data.supplier||''},
 {field:'date',headerName:'Ngày',valueGetter:p=>p.data.date||p.data.expected_date||''},{field:'status',headerName:'Trạng thái',valueFormatter:p=>stateLabel(p.value)},
 {field:'amount',headerName:'Giá trị',valueFormatter:p=>money(p.value)}])
const lineColumns=[{field:'item_name',headerName:'Mặt hàng',minWidth:180},{field:'qty',headerName:'Số lượng'},{field:'uom',headerName:'ĐVT',valueFormatter:p=>unitLabel(p.value)},{field:'rate',headerName:'Đơn giá',valueFormatter:p=>money(p.value)},{field:'vat_code',headerName:'VAT'},{field:'freight',headerName:'Vận chuyển',valueFormatter:p=>money(p.value)},{field:'order',headerName:'Đơn mua'},{field:'receipt',headerName:'Phiếu nhận'}]
const sourceOptions=computed(()=>form.value==='refund'?[{value:source.value,label:source.value}]:(finance.value?.sources?.[sourceType.value]||[]).map(r=>({value:r.name,label:r.name+' · '+r.supplier+' · còn '+money(r.amount)})))
const payers=computed(()=>options(payerType.value==='Employee'?finance.value?.employees:finance.value?.shareholders,payerType.value==='Employee'?'employee_name':'title'))
const companyOptions=computed(()=>options(session.value?.companies))
const supplierOptions=computed(()=>options(catalog.value?.suppliers,'supplier_name'))
const stateOptions=[{value:'0',label:'Nháp / chờ ký'},{value:'1',label:'Đã ghi sổ'},{value:'2',label:'Đã hủy'}]
const tabLabel=computed(()=>procurementTabs.find(([k])=>k===tab.value)?.[1]||'Mua hàng')
const summary=computed(()=>tab.value==='payables'&&debt.value?[{label:'Phải trả',value:money(debt.value.owed)},{label:'Tạm ứng',value:money(debt.value.advance)},{label:'Quá hạn',value:money(debt.value.overdue)},{label:'Số dư thuần',value:money(debt.value.net)}]:tab.value==='reports'&&report.value?Object.entries(report.value.stages||{}).map(([id,label])=>({label,value:money(report.value.totals[id])})):[])
const detailLabels={orders:'Đơn mua',needs:'Đề nghị mua',quotes:'Báo giá',receipts:'Phiếu nhận',invoices:'Hóa đơn',payments:'Phiếu chi',voucher:'Phiếu chi'}
const detailTitle=computed(()=>current.value?(detailLabels[detailType.value]||'Chứng từ')+' · '+(current.value.voucher_name||current.value.name):'Chứng từ')
const detailUrl=computed(()=>current.value&&detailType.value!=='quotes'&&!current.value.audit_only?docUrl(detailType.value==='orders'?'Purchase Order':detailType.value==='needs'?'Material Request':detailType.value==='invoices'?'Purchase Invoice':current.value.doctype||'Purchase Receipt',current.value.name):'')
const stageColumns=[{field:'item_name',label:'Mặt hàng',width:'minmax(220px,2fr)'},{field:'qty',label:'Số lượng',width:'minmax(140px,1fr)'}]
const importUnits=code=>[catalog.value.items.find(i=>i.name===code)?.stock_uom,...catalog.value.conversions.filter(c=>c.parent===code).map(c=>c.uom)].filter(Boolean)
const formSubmitLabel=computed(()=>({order:'Lưu nháp đơn mua',quote:'Lưu nháp báo giá',need:'Lưu nháp đề nghị',invoice:'Ghi nhận hóa đơn',credit:'Ghi nhận hóa đơn',return:'Tạo phiếu nháp',payment:'Lập phiếu và trình ký',funding:'Lập phiếu và trình ký',reimburse:'Lập phiếu và trình ký',refund:'Lập phiếu và trình ký',accounts:'Lưu tài khoản',import:'Xác nhận tạo nháp'}[form.value]||'Lưu'))
const formDisabled=computed(()=>form.value==='import'?!preview.value?.valid:form.value==='funding'?!evidence.value||!allocations.value.length:false)
function submitForm(){
 if(['order','quote','need'].includes(form.value))return saveDocument()
 if(['return','invoice','credit'].includes(form.value))return submitStage()
 if(['payment','funding','reimburse','refund'].includes(form.value))return pay()
 if(form.value==='accounts')return saveAccounts()
 if(form.value==='import')return importCommit()
}
const formTitle=computed(()=>({order:'Đơn mua',quote:'Báo giá',need:'Đề nghị mua',receive:'Nhận / nghiệm thu',invoice:'Lập hóa đơn',payment:'Chi / tạm ứng NCC',funding:'Ghi nhận chi hộ',reimburse:'Hoàn tiền chi hộ',accounts:'Tài khoản chi hộ',import:'Nhập Excel',return:'Trả hàng',credit:'Hóa đơn điều chỉnh trả hàng',refund:'Ghi nhận NCC hoàn tiền'}[form.value]||''))

function defaultWarehouse(){return props.warehouse||(catalog.value?.warehouses?.length===1?catalog.value.warehouses[0].name:'')}
function success(text){notice.value=text;if(!props.mobile){toast.success(text);notice.value=''}}
async function run(fn){if(saving.value)return;saving.value=true;error.value='';try{return await fn()}catch(e){error.value=e.message}finally{saving.value=false}}
let loadVersion=0
async function load(){
 if(!company.value)return
 const version=++loadVersion,view=tab.value,selectedCompany=company.value
 busy.value=true;error.value=''
 try{
  let resultRows=[],resultReport=null,resultQuery=null,resultFinance=null
  if(view==='needs')resultRows=await api('needs',{company:selectedCompany})
  if(view==='quotes')resultRows=await api('quotations',{company:selectedCompany})
  if(view==='orders')resultRows=await method('purchasing','orders',{company:selectedCompany})
  if(view==='receipts')resultRows=await api('receipts',{company:selectedCompany})
  if(['invoices','payments','payables'].includes(view)){
   const filters={company:selectedCompany,supplier:supplier.value||null,search:search.value,start:queryStart.value}
   if(view==='payables')filters.as_of=asof.value
   else Object.assign(filters,{state:queryState.value||null,from_date:fromDate.value||null,to_date:toDate.value||null})
   resultQuery=await method('procurement_queries',view,filters);resultRows=resultQuery.rows
   if(view==='payments'&&catalog.value.can_finance)resultFinance=await api('payment_data',{company:selectedCompany})
  }
  if(view==='reports'){resultReport=await method('procurement_reports','report',reportFilters());resultRows=resultReport.rows}
  if(version!==loadVersion)return
  rows.value=resultRows
  if(view==='quotes')selections.value={}
  if(resultQuery){queryTotal.value=resultQuery.total_count;queryMore.value=resultQuery.has_more;if(view==='payables')debt.value=resultQuery}
  if(resultFinance){finance.value=resultFinance;fundingRows.value=resultFinance.funding||[]}
  if(resultReport)report.value=resultReport
 }catch(e){if(version===loadVersion)error.value=e.message}finally{if(version===loadVersion)busy.value=false}
}

function reportFilters(){return {company:company.value,month:period.value,as_of:asof.value,farm:farm.value,supplier:supplier.value,kind:kind.value}}
async function initialize(){
 try{session.value=await api('bootstrap');setCSRF(session.value.csrf_token);company.value=props.company||company.value||session.value.companies?.[0]?.name||'';if(!props.today&&session.value.today){asof.value=session.value.today;date.value=asof.value;billdate.value=asof.value;dueDate.value=asof.value;period.value=asof.value.slice(0,7)};if(company.value)await companyChanged()}
 catch(e){error.value=e.message}
}
async function companyChanged(){current.value=null;form.value='';catalog.value=await api('bootstrap',{company:company.value});importWarehouse.value=defaultWarehouse();if(!visibleTabs.value.some(([k])=>k===tab.value))tab.value='needs';await load();if(router&&route.query.company!==company.value)await router.replace({path:route.path,query:{...route.query,company:company.value}})}
async function ask(text){return props.mobile?mobileConfirm.ask(text):workspaceConfirm.ask(text)}
async function closeForm(){if(saving.value||!await ask('Đóng biểu mẫu và bỏ phần chưa lưu?'))return;form.value='';draft.value=null}
async function changeTab(next,fromRoute=false){
 if(!fromRoute&&hasChanges()&&!await ask('Bỏ phần chưa lưu và chuyển mục?'))return false
 discardChanges();current.value=null;pendingOnly.value=false;queryStart.value=0;tab.value=normalizeBuyingView(next)
 if(!fromRoute&&router)await router.push({path:'/mua-hang',query:{...route.query,buying_view:tab.value,company:company.value,warehouse:props.warehouse||undefined}})
 else if(props.mobile){const url=new URL(location.href);url.searchParams.set('buying_view',tab.value);history.replaceState(history.state,'',url)}
 await load();return true
}
function scopeParams(){return {company:company.value,warehouse:props.warehouse||undefined}}
function discardChanges(){form.value='';draft.value=null;quickMaster.value='';masterView.value?.close();receivingView.value?.discardChanges()}
async function navigateMaster(next,party,row){if(next==='close-master'){if(!hasChanges()||await ask('Bỏ phần chưa lưu và đóng hồ sơ?'))masterView.value?.close();return}if(!await changeTab(next))return;supplier.value=party||'';await load();if(row)await open(row,next)}
async function openQuickMaster(kind,index=0){quickLine.value=index;quickMaster.value=kind;if(props.mobile){await import('vue').then(m=>m.nextTick());masterDialog.value?.showModal()}}
async function closeQuickMaster(){if(masterSaving.value?.isSaving())return;if(!await ask('Đóng và bỏ hồ sơ chưa lưu?'))return;quickMaster.value='';masterDialog.value?.close()}
async function quickMasterSaved(result){const kind=quickMaster.value;catalog.value=await api('bootstrap',{company:company.value});if(kind==='suppliers')draft.value.supplier=result.name;else{const r=draft.value.items[quickLine.value];r.item=result.name;r.uom=result.uom;r.kind=result.kind}quickMaster.value='';masterDialog.value?.close()}
async function queryReset(){queryStart.value=0;await load()}
let queryTimer
watch(search,()=>{if(isPaged.value){clearTimeout(queryTimer);queryTimer=setTimeout(queryReset,220)}})
onUnmounted(()=>clearTimeout(queryTimer))

async function start(type){
 const selectedInvoice=current.value?.doctype==='Purchase Invoice'?current.value.name:''
 error.value='';current.value=null;key.value=newKey();signers.value={};quantities.value={};evidence.value=null;file.value=null;fileUrl.value='';preview.value=null;mappings.value={};duplicateReason.value='';bill.value='';source.value='';amount.value='';reference.value='';notes.value='';allocations.value=[];payer.value=''
 date.value=asof.value
 if(['order','quote','need'].includes(type)){draft.value=newPurchaseDraft(defaultWarehouse(),asof.value);draft.value.valid_till=asof.value}
 if(['payment','funding','reimburse','refund','accounts'].includes(type)){
  if(['payment','refund'].includes(type)&&selectedInvoice){sourceType.value='Purchase Invoice';source.value=selectedInvoice}
  finance.value=await api('payment_data',{company:company.value})
  signerOptions.value=await method('signing','candidates',{chain:'payment_voucher',company:company.value})
 }
 form.value=type
}
async function saveDocument(){await run(async()=>{
 let answer
 if(form.value==='need')answer=await method('purchase_proposal','save_proposal',{company:company.value,values:{reason:draft.value.notes,warehouse:draft.value.warehouse,items:draft.value.items.map(r=>({...r,item_code:r.item,warehouse:r.warehouse||draft.value.warehouse,schedule_date:draft.value.expected_date}))}},true)
 else if(form.value==='quote')answer=await api('save_quotation',{company:company.value,data:draft.value,client_key:key.value},true)
 else answer=await method('warehouse_buying_lite','save_order',{company:company.value,data:purchasePayload(draft.value,catalog.value),name:draft.value.name||null,modified:draft.value.modified||null},true)
 const type=form.value==='need'?'needs':form.value==='quote'?'quotes':'orders';form.value='';tab.value=type;await load();success('Đã lưu nháp '+answer.name)
})}
async function fromRequest(name){await run(async()=>{const request=await method('warehouse_buying_lite','request_detail',{name,company:company.value});draft.value=purchaseFromRequest(draft.value,request)})}
async function open(row,type=tab.value){error.value='';try{
 form.value='';detailType.value=type;signers.value={};chain.value=null
 if(type==='payables'){if(row.doctype!=='Purchase Invoice')return;return await open(row,'invoices')}
 if(row.audit_only){current.value={...row};return}
 if(type==='orders'){
  current.value=await method('purchasing','detail',{name:row.name});chain.value=await api('chain',{name:row.name})
  signerOptions.value=await method('purchasing','approver_options',{company:company.value})
 }else if(type==='invoices')current.value=await method('procurement_queries','invoice',{company:company.value,name:row.name})
 else if(type==='needs'){
  current.value=await method('purchase_proposal','detail',{name:row.name});signerOptions.value=await method('purchase_proposal','signer_options',{company:company.value})
 }else if(type==='receipts')current.value=await api('receipt',{name:row.name})
 else if(type==='quotes')current.value={...row,line_id:row.name,name:row.quotation}
 else if(type==='payments'){current.value=await api('voucher',{doctype:row.doctype||'Journal Entry',name:row.journal_entry||row.name});if(row.lotus_purchase_funding)current.value.funding=fundingRows.value.find(r=>r.name===row.lotus_purchase_funding)}
}catch(e){error.value=e.message}}
async function act(name,module='purchasing',extra={}){await run(async()=>{
 const d=current.value
 const result=await method(module,name,{name:d.name,modified:d.modified,...extra},true)
 success('Đã cập nhật '+d.name);if(detailType.value==='quotes')current.value=null;else await open({name:d.name},detailType.value);await load();return result
})}
async function prepareReceipt(type){
 if(type==='receive'){await receivingView.value.openOrder(current.value.name);return}
 key.value=newKey();date.value=asof.value;quantities.value={}
 if(['invoice','credit'].includes(type))receiveInfo.value=await api('billing_source',{company:company.value,name:current.value.name,kind:type})
 else receiveInfo.value={name:current.value.name,items:current.value.items}
 for(const r of receiveInfo.value.items)quantities.value[r.line]=r.remaining_qty??r.qty
 form.value=type
}
async function submitStage(){await run(async()=>{
 const selected=Object.fromEntries(Object.entries(quantities.value).filter(([,q])=>Number(q)>0))
 let result
 if(form.value==='return')result=await api('return_receipt',{name:receiveInfo.value.name,posting_date:date.value,quantities:selected,client_key:key.value},true)
 if(form.value==='credit')result=await method('procurement_adjustments','credit_note',{company:company.value,name:receiveInfo.value.name,posting_date:date.value,bill_no:bill.value,bill_date:billdate.value,quantities:selected,client_key:key.value},true)
 if(form.value==='invoice')result=await api('invoice_receipt',{name:receiveInfo.value.name,bill_no:bill.value,bill_date:billdate.value,posting_date:date.value,due_date:dueDate.value,quantities:selected,client_key:key.value},true)
 const target=result.invoice?'invoices':'receipts';form.value='';current.value=null;await changeTab(target);await open({name:result.invoice||result.name},target);success('Đã tạo '+(result.name||result.invoice))
})}
async function chooseQuotes(){await run(async()=>{const result=await api('select_quotes',{company:company.value,selections:quoteChoices(rows.value,selections.value),client_key:key.value||=newKey()},true);key.value='';tab.value='orders';await load();success('Đã tạo đơn nháp: '+result.orders.join(', '))})}
function selection(row){return selections.value[row.line_id||row.name]||=( {selected:false,reason:'',qty:row.qty})}
async function proposalSign(){await act('sign','purchase_proposal',{signers:signers.value})}
async function pay(){await run(async()=>{
 let result
 if(form.value==='refund')result=await method('procurement_adjustments','refund',{company:company.value,name:source.value,amount:amount.value,mode:mode.value,posting_date:date.value,reference_no:reference.value,signers:signers.value,client_key:key.value},true)
 else if(form.value==='payment')result=await api('supplier_payment',{company:company.value,reference_type:sourceType.value,reference_name:source.value,amount:amount.value,mode:mode.value,posting_date:date.value,reference_no:reference.value,signers:signers.value,client_key:key.value},true)
 else if(form.value==='funding'){
  let url=evidence.value?.file_url
  if(!url){const f=await upload(evidence.value);url=f.file_url;evidence.value=f}
  result=await method('purchase_funding','prepare',{company:company.value,client_key:key.value,signers:signers.value,data:{supplier:supplier.value,posting_date:date.value,payer_type:payerType.value,payer:payer.value,classification:classification.value,amount:amount.value,evidence:url,external_reference:reference.value,notes:notes.value,duplicate_reason:duplicateReason.value,allocations:allocations.value}},true)
 }else result=await method('purchase_funding','reimburse',{name:fundingName.value,amount:amount.value,posting_date:date.value,mode:mode.value,signers:signers.value,client_key:key.value,reference_no:reference.value},true)
 form.value='';current.value=await api('voucher',{doctype:result.doctype,name:result.voucher});detailType.value='voucher';tab.value='payments';await load();success('Đã trình ký '+result.voucher)
})}
async function signVoucher(){await run(async()=>{await method('finance.payments','sign_payment',{doctype:current.value.doctype,name:current.value.name},true);current.value=await api('voucher',{doctype:current.value.doctype,name:current.value.name});await load();success('Đã ký phiếu')})}
async function returnVoucher(){await run(async()=>{await method('finance.payments','return_payment',{doctype:current.value.doctype,name:current.value.name,reason:notes.value},true);current.value=await api('voucher',{doctype:current.value.doctype,name:current.value.name});success('Đã trả lại phiếu')})}
async function cancelVoucher(){if(!await ask('Hủy phiếu nháp và giải phóng số tiền đang giữ?'))return;await run(async()=>{await method('finance.payments','cancel_draft',{doctype:current.value.doctype,name:current.value.name,reason:notes.value},true);current.value=null;await load();success('Đã hủy phiếu chưa ghi sổ')})}
async function reimburse(row){fundingName.value=row.name;await start('reimburse');amount.value=row.remaining}
async function importPreview(){await run(async()=>{
 if(!fileUrl.value){const f=await upload(file.value);fileUrl.value=f.file_url}
 preview.value=await method('procurement_import','preview',{company:company.value,file_url:fileUrl.value,mappings:mappings.value},true)
 for(const row of preview.value.rows){if(!mappings.value[row.key])mappings.value[row.key]={item:row.item,qty:row.qty,rate:row.source_rate??row.rate,uom:row.uom,month:row.month,supplier:row.supplier,warehouse:importWarehouse.value,type:row.type,kind:row.lotus_purchase_kind||''}}
})}
async function importCommit(){await run(async()=>{const result=await method('procurement_import','commit',{company:company.value,file_url:fileUrl.value,mappings:mappings.value,fingerprint:preview.value.fingerprint,client_key:key.value,duplicate_reason:duplicateReason.value},true);form.value='';tab.value='needs';await load();success('Đã tạo '+result.documents.length+' chứng từ nháp')})}
async function saveAccounts(){await run(async()=>{await method('purchase_funding','save_accounts',{company:company.value,mapping:finance.value.mapping},true);form.value='';success('Đã lưu tài khoản chi hộ')})}
function exportReport(){window.location.href='/api/method/lotus_farm.procurement_reports.export?'+new URLSearchParams(reportFilters())}
function hasChanges(){return !!form.value||!!quickMaster.value||!!masterView.value?.hasChanges()||!!receivingView.value?.hasChanges()}
let initialLoad=Promise.resolve()
async function createOrder(){await initialLoad;if(!catalog.value?.can_create)return;if(!await changeTab('orders'))return;await start('order')}
async function startReceiving(){await initialLoad;if(!await changeTab('orders'))return;search.value='';pendingOnly.value=true}
defineExpose({hasChanges,discardChanges,scopeParams,refresh:load,createOrder,startReceiving})
let consumingAction=false
async function consumeAction(){if(consumingAction||route?.query.action!=='create_order')return;consumingAction=true;try{await createOrder();const q={...route.query};delete q.action;await router.replace({path:route.path,query:q})}finally{consumingAction=false}}
onMounted(()=>{initialLoad=initialize();initialLoad.then(consumeAction)})
watch(()=>props.navigationKey,()=>{if(catalog.value)consumeAction()})
watch(()=>props.buyingView,async value=>{const next=normalizeBuyingView(value);if(next!==tab.value)await changeTab(next,true)})
watch(()=>props.company,async value=>{if(value&&value!==company.value){company.value=value;await companyChanged()}})
</script>

<template><section class="procurement-workspace" :class="{'procurement-workspace--mobile':mobile}">
 <LotusMobileFeedback v-if="mobile&&error&&!form&&!current" kind="error">{{error}}</LotusMobileFeedback>
 <LotusMobileFeedback v-if="notice" kind="success">{{notice}}</LotusMobileFeedback>
 <p v-if="!mobile&&!catalog&&error" role="alert" class="lotus-list-page__error">{{error}}</p>
 <template v-if="catalog">
 <nav v-if="!embedded||mobile" class="procurement-tabs" aria-label="Mua hàng"><component :is="button" v-for="[id,label] in visibleTabs" :key="id" :aria-current="tab===id?'page':undefined" :disabled="saving" @click="changeTab(id)">{{label}}</component></nav>

 <ProcurementMasters v-if="isMaster" ref="masterView" :key="company+tab" :company="company" :kind="tab" :mobile="mobile" @navigate="navigateMaster"><template #scope><LotusField v-if="companyOptions.length>1" v-model="company" :mobile="mobile" :label="mobile?'Công ty':undefined" aria-label="Công ty" :options="companyOptions" :searchable="false" :empty-option="null" :disabled="hasChanges()" @update:model-value="companyChanged"/></template></ProcurementMasters>

 <ListPage v-else-if="!mobile" :title="tabLabel" :rows="shownRows" :columns="columns" :loading="busy" :error="form||current?'':error" v-model:search="search" :search-placeholder="isPaged?'Tìm số chứng từ, hóa đơn…':'Tìm trong danh sách…'" :summary="summary"
   :paged="isPaged" :start="queryStart" :total="queryTotal" :has-more="queryMore" @update:start="value=>{queryStart=value;load()}" @refresh="load"
   :storage-key="'procurement-'+tab" show-empty-headers :interactive="tab!=='reports'&&tab!=='quotes'" :empty="busy?'Đang tải…':'Chưa có chứng từ phù hợp.'" @open="open">
  <template #filters>
   <LotusField v-if="companyOptions.length>1" v-model="company" aria-label="Công ty" :options="companyOptions" :searchable="false" :empty-option="null" @update:model-value="companyChanged"/>
   <template v-if="isPaged">
    <LotusField v-model="supplier" aria-label="Nhà cung cấp" :options="supplierOptions" placeholder="Tất cả nhà cung cấp" @update:model-value="queryReset"/>
    <LotusField v-if="tab==='payables'" v-model="asof" aria-label="Chốt đến" type="date" @update:model-value="queryReset"/>
    <template v-else><DateRangePicker v-model:from="fromDate" v-model:to="toDate" @change="queryReset"/><LotusField v-model="queryState" aria-label="Trạng thái" :options="stateOptions" :searchable="false" empty-option="Mọi trạng thái" @update:model-value="queryReset"/></template>
   </template>
   <template v-if="tab==='reports'">
    <LotusField v-model="period" aria-label="Tháng" type="month" :max="asof.slice(0,7)"/>
    <LotusField v-model="asof" aria-label="Chốt đến" type="date"/>
    <LotusField v-model="supplier" aria-label="Nhà cung cấp" :options="supplierOptions" placeholder="Tất cả nhà cung cấp"/>
    <LotusField v-model="kind" aria-label="Loại mua" :options="purchaseKinds" :searchable="false" empty-option="Mọi loại mua"/>
    <LotusField v-model="farm" aria-label="Vườn" :options="options(catalog.farms)" placeholder="Tất cả vườn"/>
   </template>
  </template>
  <template #actions>
   <Button v-if="tab==='needs'&&catalog.can_need" @click="start('need')">Thêm đề nghị</Button>
   <Button v-if="tab==='quotes'&&catalog.can_quote" @click="start('quote')">Thêm báo giá</Button>
   <Button v-if="tab==='quotes'&&catalog.can_create" variant="outline" :disabled="!Object.values(selections).some(r=>r.selected)||saving" @click="chooseQuotes">Tạo đơn từ dòng chọn</Button>
   <Button v-if="tab==='orders'&&catalog.can_create" @click="start('order')">Thêm đơn mua</Button>
   <Button v-if="tab==='orders'" variant="outline" :aria-pressed="pendingOnly" @click="pendingOnly=!pendingOnly">{{pendingOnly?'Xem tất cả đơn':'Hàng chờ nhận'}}</Button>
   <Button v-if="['needs','quotes'].includes(tab)&&catalog.can_create" variant="outline" @click="start('import')">Nhập Excel</Button>
   <template v-if="tab==='payments'&&catalog.can_finance"><Button @click="start('payment')">Chi / tạm ứng NCC</Button><Button variant="outline" @click="start('funding')">Cá nhân chi hộ</Button><Button v-if="finance?.is_chief" variant="outline" @click="start('accounts')">Tài khoản chi hộ</Button></template>
   <template v-if="tab==='reports'"><Button @click="load">Áp dụng</Button><Button variant="outline" :disabled="saving" @click="exportReport">Xuất toàn bộ Excel</Button></template>
  </template>
  <template #before>
   <p v-if="tab==='reports'&&report?.note" class="lotus-form-note">{{report.note}}</p>
   <FormSection v-if="tab==='payments'&&finance?.vouchers?.length" title="Phiếu chờ ký"><div class="procurement-actions"><Button v-for="v in finance.vouchers" :key="v.name" variant="outline" size="sm" @click="current=v;detailType='voucher'">{{v.name}} · {{money(v.amount)}} · {{v.signing?.waiting_for}}</Button></div></FormSection>
  </template>
  <template #cell-quotation="{row}"><Button variant="link" @click="open(row,'quotes')">{{row.quotation}}</Button></template>
  <template #cell-choice="{row}"><Checkbox :model-value="selection(row).selected" :disabled="row.docstatus!==1||row.gross==null" :aria-label="'Chọn '+row.item_name+' từ '+row.supplier" @update:model-value="value=>selection(row).selected=value"/></template>
  <template #cell-reason="{row}"><LotusField v-model="selection(row).reason" :aria-label="'Lý do chọn '+row.quotation"/></template>
 </ListPage>

 <template v-else-if="!form&&!current">
  <div class="procurement-toolbar">
   <LotusField v-if="companyOptions.length>1" v-model="company" mobile label="Công ty" :options="companyOptions" @update:model-value="companyChanged"/>
   <template v-if="isPaged"><LotusField v-model="supplier" mobile label="Nhà cung cấp" :options="[{value:'',label:'Tất cả'},...supplierOptions]" @update:model-value="queryReset"/><LotusField v-if="tab==='payables'" v-model="asof" mobile type="date" label="Chốt đến" @update:model-value="queryReset"/><template v-else><LotusField v-model="fromDate" mobile type="date" label="Từ ngày" @update:model-value="queryReset"/><LotusField v-model="toDate" mobile type="date" label="Đến ngày" @update:model-value="queryReset"/><LotusField v-model="queryState" mobile label="Trạng thái" :searchable="false" :options="[{value:'',label:'Tất cả'},...stateOptions]" @update:model-value="queryReset"/></template></template>
   <template v-if="tab==='reports'"><LotusField v-model="period" mobile label="Tháng" type="month"/><LotusField v-model="asof" mobile type="date" label="Chốt đến"/><LotusField v-model="supplier" mobile label="Nhà cung cấp" :options="[{value:'',label:'Tất cả'},...supplierOptions]"/><LotusField v-model="kind" mobile label="Loại mua" :options="[{value:'',label:'Tất cả'},...purchaseKinds]" :searchable="false"/></template>
   <LotusField v-else v-model="search" mobile label="Tìm kiếm" placeholder="Tìm trong danh sách…"/>
   <component :is="button" :disabled="busy||saving" @click="load">{{tab==='reports'?'Áp dụng':'Làm mới'}}</component>
   <component :is="button" v-if="tab==='needs'&&catalog.can_need" @click="start('need')">Thêm đề nghị</component>
   <component :is="button" v-if="tab==='quotes'&&catalog.can_quote" @click="start('quote')">Thêm báo giá</component>
   <component :is="button" v-if="tab==='quotes'&&catalog.can_create" :disabled="!Object.values(selections).some(r=>r.selected)||saving" @click="chooseQuotes">Tạo đơn từ dòng chọn</component>
   <component :is="button" v-if="tab==='orders'&&catalog.can_create" @click="start('order')">Thêm đơn mua</component>
   <component :is="button" v-if="tab==='orders'" :aria-pressed="pendingOnly" @click="pendingOnly=!pendingOnly">{{pendingOnly?'Xem tất cả đơn':'Hàng chờ nhận'}}</component>
   <template v-if="tab==='payments'&&catalog.can_finance"><component :is="button" @click="start('payment')">Chi / tạm ứng NCC</component><component :is="button" @click="start('funding')">Cá nhân chi hộ</component></template>
  </div>
  <dl v-if="summary.length" class="procurement-totals"><div v-for="s in summary" :key="s.label"><dt>{{s.label}}</dt><dd>{{s.value}}</dd></div></dl>
  <CellGroup :border="false"><Cell v-for="(r,i) in shownRows" :key="r.name+'-'+i" :title="r.item_name||r.voucher_name||r.name" :label="[r.supplier_name||r.supplier,r.status||r.stage_label,r.date||r.delivery_date].filter(Boolean).join(' · ')" :value="money(tab==='quotes'?r.gross:r.amount)" :is-link="tab!=='reports'" @click="open(r)"/><Cell v-if="!shownRows.length" :title="busy?'Đang tải…':'Chưa có dữ liệu.'"/></CellGroup>
  <template v-if="tab==='payments'&&finance?.vouchers?.length"><h3>Phiếu chờ ký</h3><component :is="button" v-for="v in finance.vouchers" :key="v.name" @click="current=v;detailType='voucher'">{{v.name}} · {{money(v.amount)}} · {{v.signing?.waiting_for}}</component></template>
  <div v-if="isPaged" class="procurement-actions"><span>{{queryTotal?queryStart+1:0}}–{{queryStart+rows.length}} / {{queryTotal}}</span><component :is="button" :disabled="!queryStart||busy" @click="queryStart-=50;load()">Trước</component><component :is="button" :disabled="!queryMore||busy" @click="queryStart+=50;load()">Sau</component></div>
 </template>

 <ResponsiveForm :mobile="mobile" :model-value="!!current&&!form" :title="detailTitle" readonly width="1080px" :busy="saving" :error="error" @update:model-value="value=>!value&&(current=null)">
  <template v-if="current">
   <MobilePurchaseOrderDetail v-if="mobile&&detailType==='orders'" :order="current" :warehouses="catalog.warehouses"/>
   <CellGroup v-else-if="mobile&&current.items" :border="false"><Cell v-for="(r,i) in current.items" :key="r.line||i" :title="r.item_name" :label="r.uom" :value="String(r.qty)"/></CellGroup>
   <DataTable v-else-if="current.items" :rows="current.items" :columns="lineColumns"/>

   <template v-if="detailType==='needs'">
    <p class="lotus-form-note">{{current.state||current.status}} · {{current.reason}}</p>
    <ProcurementSigners v-if="current.can_send||current.can_sign||current.can_submit" :mobile="mobile" v-model="signers" :options="signerOptions"/>
   </template>
   <template v-if="detailType==='quotes'">
    <dl class="lotus-form-totals"><div><dt>Nhà cung cấp</dt><dd>{{current.supplier}}</dd></div><div><dt>Giá đủ / ĐVT kho</dt><dd>{{money(current.unit_cost)}}</dd></div><div><dt>Ngày giao</dt><dd>{{current.delivery_date||'—'}}</dd></div></dl>
    <LotusField v-if="mobile" mobile v-model="selection(current).reason" label="Lý do lựa chọn"/>
   </template>
   <template v-if="detailType==='orders'">
    <FormSection v-if="current.can_manage||current.can_close" title="Hẹn giao / đóng phần còn lại">
     <FormGrid :columns="mobile?1:2"><LotusField v-model="deliveryDate" :mobile="mobile" type="date" label="Ngày giao hẹn lại"/><LotusField v-model="deliveryReason" :mobile="mobile" label="Lý do đổi hẹn / đóng phần còn lại"/></FormGrid>
    </FormSection>
    <ProcurementSigners v-if="current.can_request_approval" :mobile="mobile" v-model="signers" :options="signerOptions"/>
    <FormSection v-if="chain&&(chain.receipts?.length||chain.invoices?.length||chain.payments?.length||chain.funding?.length)" title="Chứng từ liên quan">
     <div class="procurement-actions"><component :is="button" v-for="r in chain.receipts" :key="r.name" type="button" variant="outline" size="sm" @click="open(r,'receipts')">{{r.name}} · {{r.date}} · {{r.docstatus===1?'Đã xác nhận':r.docstatus===2?'Đã hủy':'Nháp'}}</component><component :is="button" v-for="r in chain.invoices" :key="r.name" type="button" variant="outline" size="sm" @click="open(r,'invoices')">{{r.name}} · {{money(r.amount)}}</component></div>
     <p v-for="r in chain.payments" :key="r.name" class="lotus-form-note">{{r.name}} · {{r.docstatus===1?'Đã trả':'Chờ ký'}} · {{money(r.amount)}}</p>
     <p v-for="r in chain.funding" :key="r.name" class="lotus-form-note">{{r.name}} · {{r.status}} · Chi hộ {{money(r.amount)}} · Còn hoàn {{money(r.remaining)}}</p>
    </FormSection>
   </template>
   <template v-if="detailType==='invoices'">
    <dl class="lotus-form-totals"><div><dt>Nhà cung cấp</dt><dd>{{current.supplier}}</dd></div><div><dt>Hóa đơn</dt><dd>{{current.bill_no}}</dd></div><div><dt>Hạn trả</dt><dd>{{current.due_date}}</dd></div><div><dt>Tổng</dt><dd>{{money(current.amount)}}</dd></div><div><dt>Còn nợ</dt><dd>{{money(current.outstanding_amount)}}</dd></div></dl>
    <p v-for="t in current.taxes" :key="t.description" class="lotus-form-note">{{t.description}} · {{money(t.amount)}}</p>
    <div class="procurement-actions"><template v-for="r in current.items" :key="r.line"><component :is="button" v-if="r.order" type="button" variant="outline" size="sm" @click="open({name:r.order},'orders')">Đơn {{r.order}}</component><component :is="button" v-if="r.receipt" type="button" variant="outline" size="sm" @click="open({name:r.receipt},'receipts')">Phiếu nhận {{r.receipt}}</component></template></div>
   </template>
   <template v-if="detailType==='receipts'">
    <dl v-if="current.incoming_total!=null" class="lotus-form-totals"><div><dt>Tiền hàng</dt><dd>{{money(current.goods_total)}}</dd></div><div><dt>Chi phí phân bổ</dt><dd>{{money(current.valuation_charges)}}</dd></div><div><dt>Giá trị nhập</dt><dd>{{money(current.incoming_total)}}</dd></div></dl>
    <p class="lotus-form-note">{{current.docstatus===1?'Đã xác nhận':current.docstatus===2?'Đã hủy':'Nháp'}} · {{current.supplier}}</p>
   </template>
   <template v-if="['voucher','payments'].includes(detailType)">
    <p v-if="current.reason" class="lotus-form-note">{{current.reason}}</p>
    <dl class="lotus-form-totals"><div><dt>Loại</dt><dd>{{current.kind||current.classification}}</dd></div><div><dt>Số tiền</dt><dd>{{money(current.amount)}}</dd></div><div><dt>Chờ ký</dt><dd>{{current.signing?.waiting_for||'—'}}</dd></div></dl>
    <p v-for="s in current.signing?.steps||[]" :key="s.key" class="lotus-form-note">{{s.title}} · {{s.name}} · {{s.state}}</p>
    <LotusField v-if="current.signing?.can_sign||catalog.can_finance&&current.docstatus===0" :mobile="mobile" v-model="notes" label="Lý do trả lại / hủy phiếu nháp"/>
   </template>
  </template>
  <template #actions><template v-if="current">
   <component :is="link" v-if="detailUrl&&!mobile" as="a" variant="outline" :href="detailUrl" target="_blank" rel="noopener">Chứng từ gốc</component>
   <template v-if="detailType==='needs'"><component :is="button" v-if="current.can_send||current.can_sign||current.can_submit" type="button" :disabled="saving" @click="proposalSign">Ký / gửi duyệt đề nghị</component><component :is="link" as="a" variant="outline" :href="'/buying?proposal='+encodeURIComponent(current.name)">Mở quy trình đề nghị</component></template>
   <template v-if="detailType==='quotes'"><component :is="button" v-if="mobile&&current.docstatus===1&&current.gross!=null" type="button" @click="selection(current).selected=true;current=null">Chọn báo giá này</component><component :is="button" v-if="current.docstatus===0&&catalog.can_quote" type="button" :disabled="saving" @click="act('confirm_quotation','procurement')">Xác nhận báo giá</component></template>
   <template v-if="detailType==='orders'">
    <component :is="link" as="a" variant="outline" :href="'/lotus/in-phieu?'+new URLSearchParams({doctype:'Purchase Order',name:current.name})" target="_blank" rel="noopener">In đơn mua</component>
    <component :is="button" v-if="current.can_manage&&!current.sent_at" type="button" variant="outline" :disabled="saving" @click="act('mark_order_sent')">Đã gửi NCC</component>
    <component :is="button" v-if="current.can_manage&&current.sent_at&&!current.supplier_confirmed_at" type="button" variant="outline" :disabled="saving" @click="act('confirm_supplier_order')">NCC đã xác nhận</component>
    <component :is="button" v-if="current.can_manage" type="button" variant="outline" :disabled="saving||!deliveryDate||!deliveryReason.trim()" @click="act('reschedule_order','purchasing',{expected_date:deliveryDate,reason:deliveryReason})">Đổi hẹn giao</component>
    <component :is="button" v-if="current.can_close" type="button" variant="outline" :disabled="saving||!deliveryReason.trim()" @click="act('close_order','purchasing',{reason:deliveryReason})">Đóng phần chưa giao</component>
    <component :is="button" v-if="current.can_request_approval" type="button" :disabled="saving" @click="act('request_approval','purchasing',{approver:signers.APPROVE})">Trình duyệt đơn</component>
    <component :is="button" v-if="current.can_approve" type="button" :disabled="saving" @click="act('approve_order')">Duyệt đơn</component>
    <component :is="button" v-if="current.can_receive" type="button" @click="prepareReceipt('receive')">Nhận / nghiệm thu từng phần</component>
   </template>
   <template v-if="detailType==='invoices'&&catalog.can_finance&&current.docstatus===1"><component :is="button" v-if="!current.is_return" type="button" @click="start('payment')">Thanh toán hóa đơn</component><component :is="button" v-if="!current.is_return" type="button" variant="outline" @click="prepareReceipt('credit')">Lập hóa đơn điều chỉnh trả hàng</component><component :is="button" v-if="current.is_return&&current.outstanding_amount<0" type="button" @click="start('refund')">Ghi nhận NCC hoàn tiền</component></template>
   <template v-if="detailType==='receipts'"><component :is="button" v-if="current.can_submit" type="button" :disabled="saving" @click="act('receipt_action','warehouse_planning',{action:'submit'})">Xác nhận nhận / nghiệm thu</component><component :is="button" v-if="current.docstatus===1&&!current.is_return&&catalog.can_finance" type="button" @click="prepareReceipt('invoice')">Lập hóa đơn</component><component :is="button" v-if="current.docstatus===1&&!current.is_return" type="button" variant="outline" @click="prepareReceipt('return')">Lập phiếu trả hàng</component><component :is="button" v-if="current.can_cancel" type="button" variant="destructive" :disabled="saving" @click="ask('Hủy phiếu nhận và đảo sổ kho?').then(ok=>ok&&act('receipt_action','warehouse_planning',{action:'cancel'}))">Hủy phiếu nhận</component><component :is="link" v-if="current.is_return&&current.docstatus===0" as="a" variant="outline" :href="docUrl('Purchase Receipt',current.name)" target="_blank" rel="noopener">Xác nhận phiếu trả trên ERP</component></template>
   <template v-if="['voucher','payments'].includes(detailType)"><component :is="link" v-if="current.evidence" as="a" variant="outline" :href="current.evidence" target="_blank" rel="noopener">Chứng từ gốc</component><component :is="button" v-if="current.signing?.can_sign&&current.docstatus===0" type="button" :disabled="saving" @click="signVoucher">Ký duyệt</component><component :is="button" v-if="current.signing?.can_sign" type="button" variant="outline" :disabled="saving||!notes.trim()" @click="returnVoucher">Trả lại</component><component :is="button" v-if="catalog.can_finance&&current.docstatus===0" type="button" variant="destructive" :disabled="saving||!notes.trim()" @click="cancelVoucher">Hủy phiếu chưa ghi sổ</component><component :is="button" v-if="catalog.can_finance&&current.funding?.classification==='Reimbursable'&&current.funding.remaining>0&&current.docstatus===1" type="button" @click="reimburse(current.funding)">Hoàn từng phần · còn {{money(current.funding.remaining)}}</component></template>
  </template></template>
 </ResponsiveForm>

 <MobilePurchaseOrderForm v-if="mobile&&form==='order'" v-model="draft" :items="catalog.items" :conversions="catalog.conversions" :suppliers="catalog.suppliers" :farms="catalog.farms" :warehouses="catalog.warehouses" :can-create-supplier="catalog.can_create_supplier" :can-create-item="catalog.can_create_item" :saving="saving" @add-supplier="openQuickMaster('suppliers')" @add-item="openQuickMaster('items',$event)" @submit="saveDocument"/>
 <ResponsiveForm v-else :mobile="mobile" :model-value="!!form" :title="formTitle" width="1180px" :busy="saving" :error="error" :submit-label="formSubmitLabel" :submit-disabled="formDisabled" @update:model-value="value=>!value&&closeForm()" @submit="submitForm">
  <ProcurementDocumentForm v-if="['order','quote','need'].includes(form)" v-model="draft" :mobile="mobile" :catalog="catalog" :type="form" :saving="saving" @add-supplier="openQuickMaster('suppliers')" @add-item="openQuickMaster('items',$event)" @request="fromRequest"/>
  <template v-else-if="['return','invoice','credit'].includes(form)">
   <FormGrid :columns="mobile?1:4"><LotusField :mobile="mobile" v-model="date" label="Ngày ghi sổ" type="date" required/><template v-if="['invoice','credit'].includes(form)"><LotusField :mobile="mobile" v-model="bill" label="Số hóa đơn" required/><LotusField :mobile="mobile" v-model="billdate" label="Ngày hóa đơn" type="date" required/><LotusField v-if="form==='invoice'" :mobile="mobile" v-model="dueDate" label="Hạn thanh toán" type="date" required/></template></FormGrid>
   <LineItemsEditor :model-value="receiveInfo?.items||[]" :title="form==='return'?'Số lượng trả':'Số lượng lập hóa đơn'" :columns="stageColumns" :mobile="mobile" fixed>
    <template #cell-item_name="{row}"><span class="receiving-line"><strong>{{row.item_name}}</strong><small>{{unitLabel(row.uom)}} · tối đa {{row.remaining_qty??row.qty}}</small></span></template>
    <template #cell-qty="{row}"><LotusField v-model="quantities[row.line]" :mobile="mobile" :aria-label="'Số lượng '+row.item_name" type="number" min="0" :max="row.remaining_qty??row.qty"/></template>
   </LineItemsEditor>
  </template>
  <template v-else-if="['payment','funding','reimburse','refund'].includes(form)">
   <FormGrid :columns="mobile?1:3">
    <template v-if="form!=='reimburse'"><LotusField :mobile="mobile" v-model="sourceType" label="Nguồn mua" :options="[{value:'Purchase Invoice',label:'Hóa đơn'},{value:'Purchase Order',label:'Đơn mua (tạm ứng)'}]" :searchable="false" :empty-option="null" @update:model-value="source=''"/><LotusField :mobile="mobile" v-model="source" label="Chứng từ nguồn" :options="sourceOptions" :required="form==='payment'"/></template>
    <LotusField :mobile="mobile" v-model="amount" label="Số tiền" type="money" min="1" required/>
    <LotusField :mobile="mobile" v-model="date" :label="form==='funding'?'Ngày thực trả NCC':'Ngày công ty chi'" type="date" required/>
    <LotusField v-if="form!=='funding'" :mobile="mobile" v-model="mode" label="Phương thức" :options="[{value:'bank',label:'Chuyển khoản'},{value:'cash',label:'Tiền mặt'}]" :searchable="false" :empty-option="null"/>
    <LotusField :mobile="mobile" v-model="reference" :label="form==='funding'?'Số chứng từ gốc':'Số giao dịch ngân hàng'" :required="form==='funding'||mode==='bank'"/>
    <template v-if="form==='funding'">
     <LotusField :mobile="mobile" v-model="supplier" label="Nhà cung cấp được trả" :options="supplierOptions" required/>
     <LotusField :mobile="mobile" v-model="payerType" label="Người chi" :options="[{value:'Employee',label:'Nhân viên'},{value:'Shareholder',label:'Chủ đầu tư / cổ đông'}]" :searchable="false" :empty-option="null" @update:model-value="payer=''"/>
     <LotusField :mobile="mobile" v-model="payer" label="Tên người chi hộ" :options="payers" required/>
     <LotusField :mobile="mobile" v-model="classification" label="Phân loại khoản chi" :options="[{value:'Reimbursable',label:'Công ty phải hoàn'},{value:'Equity',label:'Vốn góp, không hoàn'}]" :searchable="false" :empty-option="null" required/>
     <LotusField :mobile="mobile" v-model="evidence" label="Chứng từ gốc riêng tư" type="file" accept="image/*,.pdf" required/>
     <LotusField :mobile="mobile" v-model="notes" label="Nội dung và căn cứ phân loại" type="textarea" wide required/>
     <LotusField :mobile="mobile" v-model="duplicateReason" label="Giải thích nếu trùng chứng từ" type="textarea" wide/>
    </template>
   </FormGrid>
   <FormSection v-if="form==='funding'" title="Phân bổ cho chứng từ mua">
    <template #actions><component :is="button" type="button" variant="outline" size="sm" :disabled="!source||!amount" @click="allocations.push({reference_type:sourceType,reference_name:source,amount:Number(amount)})">Thêm phân bổ nguồn đang chọn</component></template>
    <p v-if="!allocations.length" class="lotus-form-note">Chọn chứng từ nguồn và số tiền ở trên rồi bấm thêm phân bổ.</p>
    <div v-for="(a,i) in allocations" :key="i" class="procurement-actions"><span>{{a.reference_name}} · {{money(a.amount)}}</span><component :is="button" type="button" variant="ghost" size="sm" @click="allocations.splice(i,1)">Xóa</component></div>
   </FormSection>
   <ProcurementSigners :mobile="mobile" v-model="signers" :options="signerOptions"/>
  </template>
  <FormGrid v-else-if="form==='accounts'" :columns="mobile?1:2"><LotusField v-for="(label,k) in {purchase_funding_liability:'Phải hoàn cá nhân chi hộ',purchase_funding_equity:'Vốn góp bằng chi hộ'}" :key="k" :mobile="mobile" v-model="finance.mapping[k]" :label="label" :options="options(finance.accounts.filter(a=>a.root_type===(k.endsWith('equity')?'Equity':'Liability')&&!['Payable','Receivable'].includes(a.account_type)),'account_name')"/></FormGrid>
  <template v-else-if="form==='import'">
   <FormGrid :columns="mobile?1:3">
    <LotusField :mobile="mobile" :model-value="file" label="File Excel gốc" type="file" accept=".xlsx" hint="Dùng đúng mẫu Excel của Lotus." @update:model-value="value=>{file=value;fileUrl='';preview=null;mappings={}}"/>
    <LotusField :mobile="mobile" v-model="importWarehouse" label="Kho mặc định" :options="options(catalog.warehouses,'warehouse_name')"/>
    <LotusField v-if="preview?.previous?.length" :mobile="mobile" v-model="duplicateReason" label="Lý do tạo thêm chứng từ từ file này" :hint="'File đã nhập: '+preview.previous.join(', ')"/>
   </FormGrid>
   <details v-for="r in preview?.rows||[]" :key="r.key" class="procurement-line"><summary>{{r.sheet}} · dòng {{r.row}} · {{r.item_label||r.source.slice(0,5).join(' · ')}} · {{r.errors.join('; ')||'Hợp lệ'}}</summary>
    <FormGrid v-if="mappings[r.key]" :columns="mobile?1:4">
     <LotusField :mobile="mobile" v-model="mappings[r.key].item" label="Mặt hàng" :options="options(catalog.items,'item_name')"/>
     <LotusField :mobile="mobile" v-model="mappings[r.key].type" label="Nguồn" :options="[{value:'Need',label:'Đề nghị'},{value:'Quotation',label:'Báo giá'}]" :searchable="false"/>
     <LotusField :mobile="mobile" v-model="mappings[r.key].qty" label="Số lượng" type="number"/>
     <LotusField :mobile="mobile" v-model="mappings[r.key].uom" label="ĐVT" :options="importUnits(mappings[r.key].item)" :searchable="false"/>
     <LotusField :mobile="mobile" v-model="mappings[r.key].rate" label="Đơn giá" type="money"/>
     <LotusField :mobile="mobile" v-model="mappings[r.key].month" label="Tháng gốc" type="month"/>
     <LotusField :mobile="mobile" v-model="mappings[r.key].date" label="Ngày cần hàng / giao hàng đã xác nhận" type="date"/>
     <LotusField :mobile="mobile" v-model="mappings[r.key].vat_code" label="VAT của đơn giá nguồn" :options="['KCT','0','5','8','10']" :searchable="false"/>
     <LotusField :mobile="mobile" v-model="mappings[r.key].supplier" label="NCC báo giá" :options="supplierOptions"/>
     <LotusField :mobile="mobile" v-model="mappings[r.key].warehouse" label="Kho" :options="options(catalog.warehouses,'warehouse_name')"/>
     <LotusField :mobile="mobile" :model-value="!!mappings[r.key].skip" label="Bỏ qua dòng này" type="checkbox" @update:model-value="value=>mappings[r.key].skip=value"/>
    </FormGrid>
   </details>
  </template>
  <template #actions><template v-if="form==='import'"><component :is="link" as="a" variant="outline" href="/api/method/lotus_farm.procurement_import.template">Tải mẫu Excel</component><component :is="button" type="button" variant="outline" :disabled="!file||saving" @click="importPreview">Xem trước / kiểm tra lại</component></template></template>
 </ResponsiveForm>
 </template>
 <WarehouseReceiving ref="receivingView" :company="company" :warehouse="props.warehouse" :today="asof" :mobile="mobile" :confirm="ask" @changed="load"/>
 <WorkspaceModal v-if="!mobile" :model-value="!!quickMaster" :title="quickMaster==='suppliers'?'Thêm nhà cung cấp':'Thêm hàng mua'" width="1080px" @update:model-value="value=>!value&&closeQuickMaster()"><ProcurementMasterForm v-if="quickMaster" ref="masterSaving" :company="company" :kind="quickMaster" @saved="quickMasterSaved"/></WorkspaceModal>
 <LotusMobileDialog v-else ref="masterDialog" @cancel="closeQuickMaster"><h3>{{quickMaster==='suppliers'?'Thêm nhà cung cấp':'Thêm hàng mua'}}</h3><ProcurementMasterForm v-if="quickMaster" ref="masterSaving" :company="company" :kind="quickMaster" mobile @saved="quickMasterSaved"/><LotusMobileButton @click="closeQuickMaster">Đóng</LotusMobileButton></LotusMobileDialog>
 <WorkspaceConfirm v-if="!mobile" :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" confirm-label="Xác nhận" cancel-label="Quay lại" @answer="workspaceConfirm.finish"/>
 <LotusMobileDialog v-else ref="mobileDialog" @cancel="mobileConfirm.finish(false)"><h3>Xác nhận</h3><p>{{mobileMessage}}</p><LotusMobileButton @click="mobileConfirm.finish(false)">Quay lại</LotusMobileButton><LotusMobileButton @click="mobileConfirm.finish(true)">Xác nhận</LotusMobileButton></LotusMobileDialog>
</section></template>
