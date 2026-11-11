<script setup>
import {tablePage} from '../table-pagination'
import {unitLabel} from '../units'
import {groupNumber} from '../grid-format'
import {stateLabel} from '../labels'
import '../procurement.css'
import {computed,inject,onMounted,onUnmounted,ref,watch} from 'vue'
import {routerKey,routeLocationKey} from 'vue-router'
import {normalizeBuyingView,buyingGroupViews} from '../procurement-navigation'
import ProcurementMasters from './ProcurementMasters.vue'
import ProcurementMasterForm from './ProcurementMasterForm.vue'
import WarehouseReceiving from './WarehouseReceiving.vue'
import ProcurementCompare from './ProcurementCompare.vue'
import StockDocumentForm from './stock/StockDocumentForm.vue'
import StockDocumentDetail from './stock/StockDocumentDetail.vue'
import {Cell,CellGroup} from 'vant'
import {call,upload,setCSRF} from '../api'
import {purchasePdfUrl} from '../purchase-document'
import {procurementApi,lotusMethod} from './procurement/use-procurement'
import NeedDetail from './procurement/NeedDetail.vue'
import OrderDetail from './procurement/OrderDetail.vue'
import ReceiptDetail from './procurement/ReceiptDetail.vue'
import InvoiceQueue from './procurement/InvoiceQueue.vue'
import InvoiceForm from './procurement/InvoiceForm.vue'
import InvoiceDetail from './procurement/InvoiceDetail.vue'
import PayablesView from './procurement/PayablesView.vue'
import PaymentForm from './procurement/PaymentForm.vue'
import VoucherDetail from './procurement/VoucherDetail.vue'
import {PROPOSAL_STAGES} from '../purchase-status'
import {Button} from './ui/button'
import {DateRangePicker} from './ui/date-picker'
import DataTable from './DataTable.vue'
import ListPage from './ListPage.vue'
import LotusField from './form/LotusField.vue'
import FormGrid from './form/FormGrid.vue'
import FormSection from './form/FormSection.vue'
import ErpSection from './erp/ErpSection.vue'
import ErpReport from './erp/ErpReport.vue'
import {erpSection} from '../erp-sections.js'
import LineItemsEditor from './form/LineItemsEditor.vue'
import ResponsiveForm from './form/ResponsiveForm.vue'
import WorkspaceConfirm from './WorkspaceConfirm.vue'
import ProcurementSigners from './ProcurementSigners.vue'
import PurchaseProgress from './PurchaseProgress.vue'
import ProcurementDocumentForm from './ProcurementDocumentForm.vue'
import MobilePurchaseOrderForm from './MobilePurchaseOrderForm.vue'
import MobilePurchaseOrderDetail from './MobilePurchaseOrderDetail.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileFeedback from './LotusMobileFeedback.vue'
import WorkspaceModal from './WorkspaceModal.vue'
import LotusMobileDialog from './LotusMobileDialog.vue'
import {newPurchaseDraft,purchasePayload,purchaseFromRequest,purchaseDraftFromOrder} from '../mobile-purchase'
import {procurementTabs,purchaseKinds,money,newKey,quoteChoices} from '../procurement'
import {toast} from '../use-toast'
import {useWorkspaceConfirm} from '../use-workspace-confirm'
import {useMobileConfirm} from '../use-mobile-confirm'

const props=defineProps({company:String,warehouse:String,today:String,mobile:Boolean,embedded:Boolean,buyingView:String,navigationKey:String,initialSupplier:String})
const api=procurementApi
const method=lotusMethod
const router=inject(routerKey,null),route=inject(routeLocationKey,null)
const masterView=ref(null),quickMaster=ref(''),quickLine=ref(0),masterDialog=ref(null),masterSaving=ref(null),receivingView=ref(null)
const queryStart=ref(0),queryPageSize=ref(50),queryTotal=ref(0),queryMore=ref(false),queryState=ref(''),fromDate=ref(''),toDate=ref(''),debt=ref(null),fundingRows=ref([]),deliveryReason=ref(''),deliveryDate=ref('')
const isPaged=computed(()=>['invoices','payments','payables'].includes(tab.value))
// Yêu cầu báo giá, Nhóm NCC & điều khoản: ERPNext documents opened inside Mua hàng; the Báo cáo screen also offers
// ERPNext's purchase reports (sổ mua hàng, theo dõi mua hàng…) in its "Loại báo cáo" picker.
const erpView=computed(()=>erpSection('buying',tab.value))
const erpReports=computed(()=>erpSection('buying','erp-reports')?.tabs||[])
const erpReportName=ref('')
const reportKinds=computed(()=>[{value:'',label:'Báo cáo mua hàng tháng'},...erpReports.value.map(t=>({value:t.name,label:t.label}))])
const erpReportSel=computed(()=>erpReports.value.find(t=>t.name===erpReportName.value)||null)
const isMaster=computed(()=>['suppliers','items'].includes(tab.value))
const button=computed(()=>props.mobile?LotusMobileButton:Button)
// Links look like buttons on desktop; the phone PWA keeps plain links.
const link=computed(()=>props.mobile?'a':Button)
const company=ref(props.company||''),session=ref(null),catalog=ref(null),tab=ref(props.buyingView?normalizeBuyingView(props.buyingView):props.embedded?'orders':'needs'),rows=ref([])
const busy=ref(false),saving=ref(false),error=ref(''),notice=ref(''),search=ref(''),form=ref(''),draft=ref(null),key=ref('')
const pendingOnly=ref(false),proposalStage=ref('')
// Bảng đề xuất (spec 003, FR-026): one stage vocabulary, each with its count; Chờ tôi ký is a filter, not a stage.
const WAITING_ME='Chờ tôi ký'
const proposalStageOptions=computed(()=>[WAITING_ME,...PROPOSAL_STAGES].map(value=>({value,label:value+' ('+rows.value.filter(r=>value===WAITING_ME?r.waiting_me:r.stage===value).length+')'})))
// Mua nhanh reuses the Kho receipt form and detail (reason Purchase, posted at once); they need the company's warehouses.
const quickForm=ref(null),quickDetail=ref(null),stockWarehouses=ref([])
const stockSession=computed(()=>({...session.value,today:asof.value,companies:[{name:company.value,default_currency:'VND'}]}))
const quickColumns=[{field:'name',headerName:'Phiếu nhập',minWidth:170},{field:'date',headerName:'Ngày'},{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:180},
 {field:'warehouse',headerName:'Kho',minWidth:120},{field:'amount',headerName:'Giá trị nhập',valueFormatter:p=>money(p.value)},{field:'status',headerName:'Tình trạng',minWidth:180},
 {field:'source_type',headerName:'Nguồn mua',minWidth:190},{field:'invoice',headerName:'Hóa đơn'},{field:'notes',headerName:'Ghi chú',minWidth:200},{field:'created_by',headerName:'Người tạo',minWidth:150}]
const current=ref(null),chain=ref(null),detailType=ref(''),signerOptions=ref(null),signers=ref({}),selections=ref({}),finance=ref(null)
const period=ref((props.today||new Date().toISOString().slice(0,10)).slice(0,7)),asof=ref(props.today||new Date().toISOString().slice(0,10)),farm=ref(''),supplier=ref(props.initialSupplier||''),kind=ref(''),report=ref(null)
const sourceType=ref('Purchase Invoice'),source=ref(''),amount=ref(''),mode=ref('bank'),reference=ref(''),date=ref(asof.value)
const payerType=ref('Employee'),payer=ref(''),classification=ref('Reimbursable'),notes=ref(''),evidence=ref(null),duplicateReason=ref(''),allocations=ref([])
const bill=ref(''),billSeries=ref(''),cqtCode=ref(''),invoiceTotal=ref(''),invoiceVat=ref(''),billdate=ref(asof.value),dueDate=ref(asof.value),quantities=ref({}),receiveInfo=ref(null),fundingName=ref('')
const file=ref(null),fileUrl=ref(''),preview=ref(null),mappings=ref({}),importWarehouse=ref(props.warehouse||'')
const workspaceConfirm=useWorkspaceConfirm(),mobileConfirm=useMobileConfirm()
const confirmOpen=workspaceConfirm.open,confirmTitle=workspaceConfirm.title,confirmMessage=workspaceConfirm.message
const mobileDialog=mobileConfirm.dialog,mobileMessage=mobileConfirm.message
const visibleTabs=computed(()=>procurementTabs.filter(([k])=>k!=='quick'||catalog.value?.can_quick&&!props.mobile).filter(([k])=>k!=='payments'||catalog.value?.can_view_finance).filter(([k])=>!['invoices','invoice-queue','payables','reports','payments'].includes(k)||catalog.value?.can_view_finance).filter(([k])=>!['invoices','invoice-queue'].includes(k)||catalog.value?.can_invoice))
const options=(values,label)=>values?.map(r=>({value:r.name,label:r[label]||r.name}))||[]
const shownRows=computed(()=>rows.value.filter(r=>(tab.value!=='needs'||!proposalStage.value||(proposalStage.value===WAITING_ME?r.waiting_me:r.stage===proposalStage.value))&&(!pendingOnly.value||tab.value!=='orders'||r.docstatus===1&&Number(r.remaining_lines)>0&&r.status!=='Đã đóng')&&(!supplier.value||['reports','payables','payments','invoices'].includes(tab.value)||r.supplier===supplier.value)&&(!search.value||Object.values(r).filter(x=>typeof x!=='object').join(' ').toLocaleLowerCase().includes(search.value.toLocaleLowerCase()))))
const columns=computed(()=>tab.value==='quick'?quickColumns:tab.value==='invoices'?[{field:'name',headerName:'Hóa đơn',minWidth:180},{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:180},{field:'bill_no',headerName:'Số hóa đơn NCC'},{field:'date',headerName:'Ngày ghi sổ'},{field:'due_date',headerName:'Hạn thanh toán'},{field:'amount',headerName:'Tổng tiền',valueFormatter:p=>money(p.value)},{field:'outstanding_amount',headerName:'Còn nợ',valueFormatter:p=>money(p.value)},{field:'status',headerName:'Trạng thái',valueFormatter:p=>stateLabel(p.value)}]:tab.value==='payments'?[{field:'name',headerName:'Chứng từ',minWidth:180,valueGetter:p=>p.data.voucher_name||p.data.name},{field:'kind',headerName:'Loại giao dịch',minWidth:180},{field:'supplier',headerName:'Nhà cung cấp'},{field:'date',headerName:'Ngày'},{field:'amount',headerName:'Số tiền',valueFormatter:p=>money(p.value)},{field:'status',headerName:'Trạng thái',valueFormatter:p=>stateLabel(p.value)}]:tab.value==='payables'?[{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:190},{field:'name',headerName:'Chứng từ',minWidth:170},{field:'bill_no',headerName:'Hóa đơn NCC'},{field:'due_date',headerName:'Hạn trả'},{field:'amount',headerName:'Còn nợ / dư trả',valueFormatter:p=>money(p.value)},{field:'overdue_days',headerName:'Ngày quá hạn'},{field:'status',headerName:'Tình trạng',valueFormatter:p=>stateLabel(p.value)}]:tab.value==='quotes'?[
 // A list to read: choosing a quote (and the reason when it is not the cheapest) happens in So sánh giá.
 {field:'item_name',headerName:'Mặt hàng',minWidth:200},{field:'supplier',headerName:'Nhà cung cấp',minWidth:140},
 {field:'quotation',headerName:'Báo giá',minWidth:150},
 {field:'stock_qty',headerName:'Số lượng',unitField:'stock_uom',valueFormatter:p=>p.value==null?'':[groupNumber(p.value),unitLabel(p.data?.stock_uom)].filter(Boolean).join(' ')},
 {field:'stock_uom',headerName:'ĐVT kho',defaultHidden:true,valueFormatter:p=>unitLabel(p.value)},
 {field:'unit_cost',headerName:'Giá đủ/ĐVT',valueFormatter:p=>money(p.value)},
 {field:'net',headerName:'Chưa thuế',defaultHidden:true,valueFormatter:p=>money(p.value)},{field:'tax',headerName:'VAT',defaultHidden:true,valueFormatter:p=>money(p.value)},
 {field:'freight',headerName:'Vận chuyển',defaultHidden:true,valueFormatter:p=>money(p.value)},{field:'gross',headerName:'Tổng trả',minWidth:120,valueFormatter:p=>money(p.value)},
 {field:'delivery_date',headerName:'Ngày giao'},{field:'valid_till',headerName:'Hiệu lực'}]:tab.value==='reports'?[
 {field:'date',headerName:'Ngày'},{field:'stage_label',headerName:'Giai đoạn',minWidth:170},{field:'name',headerName:'Chứng từ',minWidth:170},
 {field:'supplier',headerName:'Nhà cung cấp'},{field:'item_name',headerName:'Mặt hàng',minWidth:180},
 {field:'amount',headerName:'Số tiền',valueFormatter:p=>money(p.value)}]:[
 {field:'name',headerName:'Số chứng từ',minWidth:180},{field:'supplier_name',headerName:'Nhà cung cấp',valueGetter:p=>p.data.supplier_name||p.data.supplier||''},
 {field:'date',headerName:'Ngày',valueGetter:p=>p.data.date||p.data.expected_date||''},{field:'status',headerName:'Trạng thái',minWidth:150,valueGetter:p=>stateLabel(p.data.status)+(p.data.overdue?' · quá hẹn':'')},
 ...(tab.value==='orders'?[{field:'billed_percent',headerName:'Đã có hóa đơn',sum:false,valueFormatter:p=>p.data?.docstatus===1?Math.round(Number(p.value||0))+'%':''},
  {field:'paid_percent',headerName:'Đã trả tiền',sum:false,valueFormatter:p=>p.data?.docstatus===1&&p.value!=null?Math.round(Number(p.value))+'%':''},
  {field:'reject_reason',headerName:'Lý do trả lại',minWidth:180,sum:false,defaultHidden:true}]:[]),
 {field:'amount',headerName:'Giá trị',valueFormatter:p=>money(p.value)}])
const lineColumns=[{field:'item_name',headerName:'Mặt hàng',minWidth:180},{field:'qty',headerName:'Số lượng'},{field:'uom',headerName:'ĐVT',valueFormatter:p=>unitLabel(p.value)},{field:'rate',headerName:'Đơn giá',valueFormatter:p=>money(p.value)},{field:'vat_code',headerName:'VAT'},{field:'freight',headerName:'Vận chuyển',valueFormatter:p=>money(p.value)},{field:'order',headerName:'Đơn mua'},{field:'receipt',headerName:'Phiếu nhận'}]
const sourceOptions=computed(()=>form.value==='refund'?[{value:source.value,label:source.value}]:(finance.value?.sources?.[sourceType.value]||[]).map(r=>({value:r.name,label:r.name+' · '+r.supplier+' · còn '+money(r.amount)})))
const payers=computed(()=>options(payerType.value==='Employee'?finance.value?.employees:finance.value?.shareholders,payerType.value==='Employee'?'employee_name':'title'))
const companyOptions=computed(()=>options(session.value?.companies))
const supplierOptions=computed(()=>options(catalog.value?.suppliers,'supplier_name'))
const stateOptions=[{value:'0',label:'Nháp / chờ ký'},{value:'1',label:'Đã ghi sổ'},{value:'2',label:'Đã hủy'}]
// Tabs at the top of a page whose sidebar entry holds several views (Báo giá & so sánh, Đơn mua & nhận hàng, Hóa đơn & công nợ).
const groupTabs=computed(()=>buyingGroupViews(tab.value).filter(v=>visibleTabs.value.some(([k])=>k===v.id)).map(v=>[v.id,v.tab||v.label]))
const tabLabel=computed(()=>procurementTabs.find(([k])=>k===tab.value)?.[1]||'Mua hàng')
const summary=computed(()=>tab.value==='payables'&&debt.value?[{label:'Phải trả',value:money(debt.value.owed)},{label:'Tạm ứng',value:money(debt.value.advance)},{label:'Quá hạn',value:money(debt.value.overdue)},{label:'Số dư thuần',value:money(debt.value.net)}]:tab.value==='reports'&&report.value?Object.entries(report.value.stages||{}).map(([id,label])=>({label,value:money(report.value.totals[id])})):[])
const detailLabels={orders:'Đơn mua',needs:'Đề xuất mua',quotes:'Báo giá',receipts:'Phiếu nhận',invoices:'Hóa đơn',payments:'Phiếu chi',voucher:'Phiếu chi'}
const detailTitle=computed(()=>current.value?(detailLabels[detailType.value]||'Chứng từ')+' · '+(current.value.voucher_name||current.value.name):'Chứng từ')
const stageColumns=[{field:'item_name',label:'Mặt hàng',width:'minmax(220px,2fr)'},{field:'qty',label:'Số lượng',width:'minmax(140px,1fr)'}]
const importUnits=code=>[catalog.value.items.find(i=>i.name===code)?.stock_uom,...catalog.value.conversions.filter(c=>c.parent===code).map(c=>c.uom)].filter(Boolean)
const formSubmitLabel=computed(()=>({order:'Lưu nháp đơn mua',quote:'Lưu nháp báo giá',need:'Lưu nháp đề xuất',invoice:'Ghi nhận hóa đơn',credit:'Ghi nhận hóa đơn',payment:'Lập phiếu và trình ký',funding:'Lập phiếu và trình ký',reimburse:'Lập phiếu và trình ký',refund:'Lập phiếu và trình ký',accounts:'Lưu tài khoản',import:'Xác nhận tạo nháp'}[form.value]||'Lưu'))
const formDisabled=computed(()=>form.value==='import'?!preview.value?.valid:form.value==='funding'?!evidence.value||!allocations.value.length:false)
function submitForm(){
 if(['order','quote','need'].includes(form.value))return saveDocument()
 if(['invoice','credit'].includes(form.value))return submitStage()
 if(['payment','funding','reimburse','refund'].includes(form.value))return pay()
 if(form.value==='accounts')return saveAccounts()
 if(form.value==='import')return importCommit()
}
const formTitle=computed(()=>({order:'Đơn mua',quote:'Báo giá',need:'Đề xuất mua',receive:'Nhận / nghiệm thu',invoice:'Lập hóa đơn',payment:'Chi / tạm ứng NCC',funding:'Ghi nhận chi hộ',reimburse:'Hoàn tiền chi hộ',accounts:'Tài khoản chi hộ',import:'Nhập Excel',credit:'Hóa đơn điều chỉnh trả hàng',refund:'Ghi nhận NCC hoàn tiền'}[form.value]||''))

function defaultWarehouse(){return props.warehouse||(catalog.value?.warehouses?.length===1?catalog.value.warehouses[0].name:'')}
async function loadWarehouses(name=company.value){try{stockWarehouses.value=(await call('lotus_farm.warehouse.overview',{company:name,start:0})).warehouses||[]}catch{stockWarehouses.value=[]}}
async function startQuick(){if(!stockWarehouses.value.length)await loadWarehouses();quickForm.value?.openQuick()}
async function quickSaved(result){
 await load()
 success(result.docstatus===1?'Đã nhập kho '+result.name+'. Kế toán lập hóa đơn từ phiếu này ở Hóa đơn & công nợ.':'Đã lưu nháp '+result.name+', chờ thủ kho ghi sổ.')
 if(result.warning)error.value=result.warning
}
function success(text){notice.value=text;if(!props.mobile){toast.success(text);notice.value=''}}
async function run(fn){if(saving.value)return;saving.value=true;error.value='';try{return await fn()}catch(e){error.value=e.message}finally{saving.value=false}}
let loadVersion=0
async function load(){
 if(!company.value||erpSection('buying',tab.value))return
 const version=++loadVersion,view=tab.value,selectedCompany=company.value
 busy.value=true;error.value='';if(queryPageSize.value===0&&isPaged.value)rows.value=[]
 try{
  let resultRows=[],resultReport=null,resultQuery=null,resultFinance=null
  if(['compare','invoice-queue','payables'].includes(view))return  // these views load their own data
  if(view==='quick'){resultRows=await api('quick_purchases',{company:selectedCompany});if(!stockWarehouses.value.length)await loadWarehouses(selectedCompany)}
  if(view==='needs')resultRows=await api('needs',{company:selectedCompany})
  if(view==='quotes')resultRows=await api('quotations',{company:selectedCompany})
  if(view==='orders')resultRows=await method('purchasing','orders',{company:selectedCompany})
  if(view==='receipts')resultRows=await api('receipts',{company:selectedCompany})
  if(['invoices','payments','payables'].includes(view)){
   const filters={company:selectedCompany,supplier:supplier.value||null,search:search.value,start:queryStart.value,page_length:queryPageSize.value}
   if(view==='payables')filters.as_of=asof.value
   else Object.assign(filters,{state:queryState.value||null,from_date:fromDate.value||null,to_date:toDate.value||null})
   resultQuery=await tablePage(args=>method('procurement_queries',view,args),filters,{pageSize:queryPageSize.value,sizeKey:'page_length',isCurrent:()=>version===loadVersion});resultRows=resultQuery.rows
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
 try{session.value=await api('bootstrap');setCSRF(session.value.csrf_token);company.value=props.company||company.value||session.value.companies?.[0]?.name||'';if(!props.today&&session.value.today){asof.value=session.value.today;date.value=asof.value;billdate.value=asof.value;dueDate.value=asof.value;period.value=asof.value.slice(0,7)};if(company.value){await companyChanged();const query=route?.query||Object.fromEntries(new URLSearchParams(location.search));if(query.purchase_doc)await open({name:query.purchase_doc,...(query.purchase_doctype?{doctype:query.purchase_doctype}:{})},query.purchase_type||tab.value)}}
 catch(e){error.value=e.message}
}
async function companyChanged(){current.value=null;form.value='';catalog.value=await api('bootstrap',{company:company.value});importWarehouse.value=defaultWarehouse();if(!erpSection('buying',tab.value)&&!visibleTabs.value.some(([k])=>k===tab.value))tab.value='needs';await load();if(router&&route.query.company!==company.value)await router.replace({path:route.path,query:{...route.query,company:company.value}})}
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
 error.value='';current.value=null;key.value=newKey();signers.value={};quantities.value={};evidence.value=null;file.value=null;fileUrl.value='';preview.value=null;mappings.value={};duplicateReason.value='';bill.value='';billSeries.value='';cqtCode.value='';invoiceTotal.value='';invoiceVat.value='';source.value='';amount.value='';reference.value='';notes.value='';allocations.value=[];payer.value=''
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
 if(form.value==='need')answer=await method('purchase_proposal','save_proposal',{company:company.value,name:draft.value.name||null,modified:draft.value.modified||null,values:{reason:draft.value.notes,department:draft.value.department,warehouse:draft.value.warehouse,items:draft.value.items.map(r=>({...r,item_code:r.item,warehouse:r.warehouse||draft.value.warehouse,schedule_date:r.schedule_date||draft.value.expected_date}))}},true)
 else if(form.value==='quote')answer=await api('save_quotation',{company:company.value,data:draft.value,client_key:key.value,name:draft.value.name||null,modified:draft.value.modified||null},true)
 else answer=await method('warehouse_buying_lite','save_order',{company:company.value,data:purchasePayload(draft.value,catalog.value),name:draft.value.name||null,modified:draft.value.modified||null},true)
 const doctype={need:'Material Request',quote:'Supplier Quotation'}[form.value]||'Purchase Order'
 // Photos / PDFs read by AI become attachments of the saved document.
 let attachNote=''
 for(const file_url of draft.value.ai_files||[]){try{await call('lotus_farm.stock_attachments.attach',{doctype,name:answer.name,file_url},true)}catch(e){attachNote=' Chưa gắn được chứng từ AI: '+e.message}}
 const type=form.value==='need'?'needs':form.value==='quote'?'quotes':'orders';form.value='';tab.value=type;await load();if(type!=='quotes')await open({name:answer.name},type);success('Đã lưu nháp '+answer.name+(answer.warnings?.length?'. Có '+answer.warnings.length+' dòng sẽ bị chặn khi duyệt, xem trong đơn':'')+(draft.value.ai_files?.length&&!attachNote?' kèm chứng từ đã đọc.':'')+attachNote)
})}
async function fromRequest(name){await run(async()=>{const request=await method('warehouse_buying_lite','request_detail',{name,company:company.value,allow_pending:form.value==='quote'?1:0});draft.value=purchaseFromRequest(draft.value,request)})}
async function open(row,type=tab.value){error.value='';try{
 form.value='';detailType.value=type;signers.value={};chain.value=null;notes.value=''
 if(type==='payables'){if(row.doctype!=='Purchase Invoice')return;return await open(row,'invoices')}
 if(type==='quick'){await quickDetail.value?.open('Stock Entry',row.name);return}
 if(row.audit_only){current.value={...row};return}
 if(type==='orders'){
  current.value=await method('purchasing','detail',{name:row.name});chain.value=await api('chain',{name:row.name})
  signerOptions.value=await method('purchasing','approver_options',{company:company.value})
 }else if(type==='invoices')current.value=await method('procurement_queries','invoice',{company:company.value,name:row.name})
 else if(type==='needs'){
  current.value=await method('purchase_proposal','detail',{name:row.name})
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
 if(form.value==='credit')result=await method('procurement_adjustments','credit_note',{company:company.value,name:receiveInfo.value.name,posting_date:date.value,bill_no:bill.value,bill_date:billdate.value,quantities:selected,client_key:key.value},true)
 if(form.value==='invoice')result=await api('invoice_receipt',{name:receiveInfo.value.name,bill_no:bill.value,bill_date:billdate.value,posting_date:date.value,due_date:dueDate.value,quantities:selected,client_key:key.value,invoice_series:billSeries.value,cqt_code:cqtCode.value,invoice_total:invoiceTotal.value,invoice_vat:invoiceVat.value},true)
 const target=result.invoice?'invoices':'receipts';form.value='';current.value=null;await changeTab(target);await open({name:result.invoice||result.name},target);success('Đã tạo '+(result.name||result.invoice))
})}
async function chooseQuotes(){await run(async()=>{const result=await api('select_quotes',{company:company.value,selections:quoteChoices(rows.value,selections.value),client_key:key.value||=newKey()},true);key.value='';tab.value='orders';await load();ordersCreated(result)})}
// Orders from approved requests at the cheapest price are approved at once (procurement._approve_by_policy).
function ordersCreated(result){const sent=result.sent||[],draft=result.orders.filter(n=>!sent.includes(n));success([sent.length?'Đã gửi giám đốc duyệt: '+sent.join(', '):'',draft.length?'Đơn nháp chờ gửi duyệt: '+draft.join(', '):''].filter(Boolean).join(' · '))}
async function compareCreated(result){ordersCreated(result);await changeTab('orders')}
function selection(row){return selections.value[row.line_id||row.name]||=( {selected:false,reason:'',qty:row.qty})}
async function editProposal(){const d=current.value;await start('need');draft.value={...draft.value,name:d.name,modified:d.modified,edit:d.edit,department:d.department,notes:d.reason,warehouse:d.warehouse||d.items[0]?.warehouse||'',expected_date:d.items[0]?.schedule_date||asof.value,items:d.items.map(r=>({...r,item:r.item_code,kind:r.kind||r.lotus_purchase_kind}))}}
async function orderFromProposal(){const name=current.value.name;await start('order');await fromRequest(name)}
// NeedDetail performed an action: show the fresh detail and refresh the board behind it.
async function proposalChanged(detail){current.value=detail;await load()}
async function proposalDeleted(){current.value=null;await load()}
// OrderDetail performed an action: fresh detail and related documents, then the list behind it.
async function orderChanged(detail,related){current.value=detail;chain.value=related;await load()}
async function orderDeleted(){current.value=null;await load()}
// ReceiptDetail performed an action (confirm, return, cancel): keep the fresh detail, refresh the list behind it.
async function receiptChanged(detail){if(detail&&current.value?.name===detail.name)current.value=detail;await load()}
async function receiptDeleted(){current.value=null;await load()}
// Nhập hóa đơn cho các phiếu nhận đã chọn (spec 003, US5): một biểu mẫu, một lõi ghi sổ.
const invoiceForm=ref(false),invoiceReceipts=ref([])
// Phiếu chi (spec 003, US6): một biểu mẫu trả nhiều hóa đơn của một nhà cung cấp.
const paymentForm=ref(false),paymentSupplier=ref(''),paymentPreset=ref([])
function payInvoice(detail){paymentSupplier.value=detail.supplier;paymentPreset.value=[detail.name];current.value=null;paymentForm.value=true}
async function paymentCreated(result){success('Đã lập phiếu chi '+result.voucher+' và gửi người ký.');await changeTab('payments');await open({doctype:result.doctype,name:result.voucher},'payments')}
async function voucherGone(){current.value=null;await load()}
function enterInvoice(receipts){invoiceReceipts.value=receipts;current.value=null;invoiceForm.value=true}
async function invoiceCreated(result){success('Đã ghi hóa đơn '+result.invoice+'.'+(result.warnings?.length?' '+result.warnings.join(' '):''));await changeTab('invoices');await open({name:result.invoice},'invoices')}
// A return of goods that were already invoiced: go to the invoice so the adjustment invoice can be made from it.
async function creditAfterReturn(detail){const invoice=detail?.invoices?.[0];if(invoice&&catalog.value?.can_finance){await changeTab('invoices');await open({name:invoice},'invoices')}}
// Báo giá (spec 003, FR-034): a draft is edited in the same form; a confirmed quote is never edited in place — it is
// cancelled (with a reason) or cancelled and replaced by a draft copy to correct. A quote used by an order is refused by the server.
async function openQuoteForm(name){const q=await api('quotation',{name});await start('quote');draft.value={...draft.value,name:q.name,modified:q.modified,supplier:q.supplier,date:q.date,valid_till:q.valid_till||asof.value,expected_date:q.expected_date||asof.value,warehouse:q.warehouse||draft.value.warehouse,items:q.items.map(r=>({...draft.value.items[0],id:r.name,item:r.item,qty:r.qty,uom:r.uom,rate:r.rate,warehouse:r.warehouse,kind:r.kind||'',vat_code:r.vat_code||'KCT',freight:r.freight||0,material_request:r.material_request,material_request_item:r.material_request_item}))}}
async function editQuote(){const name=current.value.name;await run(()=>openQuoteForm(name))}
async function cancelQuote(amend){
 const q=current.value
 if(q.docstatus===0&&!await ask('Xóa báo giá nháp '+q.name+'?'))return
 if(amend&&!await ask('Hủy báo giá '+q.name+' và tạo bản nháp mới để sửa?'))return
 await run(async()=>{
  const result=await api('cancel_quotation',{name:q.name,modified:q.modified,reason:notes.value,amend:amend?1:0},true)
  current.value=null;await load()
  if(result.amended_from){success('Đã hủy '+q.name+', sửa bản nháp '+result.name+'.');await openQuoteForm(result.name)}
  else success(result.deleted?'Đã xóa báo giá nháp '+q.name+'.':'Đã hủy báo giá '+q.name+'.')
 })
}
// Sửa đơn nháp hoặc đơn bị trả lại trên máy tính và điện thoại (spec 003, FR-035): the same form, every line field kept.
async function editOrder(){const d=current.value;await start('order');draft.value=purchaseDraftFromOrder(d,defaultWarehouse())}
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
// openDocument: a host app (Mua hàng on the phone) opens a related document of another kind in this workspace.
async function openDocument(row,type){await initialLoad;const view=type==='needs'?'needs':type;if(tab.value!==view&&visibleTabs.value.some(([k])=>k===view)){tab.value=view;await load()}await open(row,type)}
defineExpose({hasChanges,discardChanges,scopeParams,refresh:load,createOrder,startReceiving,openDocument})
let consumingAction=false
async function consumeAction(){if(consumingAction||route?.query.action!=='create_order')return;consumingAction=true;try{await createOrder();const q={...route.query};delete q.action;await router.replace({path:route.path,query:q})}finally{consumingAction=false}}
onMounted(()=>{initialLoad=initialize();initialLoad.then(consumeAction)})
// A later link to a document (Chờ tôi ký, alerts, progress rows) opens it even though the page stays alive (KeepAlive).
let lastLinked=''
async function openLinked(){const q=route?.query||{};if(!q.purchase_doc)return;const key=[q.purchase_doc,q.purchase_doctype,q.purchase_type].join('|');if(key===lastLinked)return;lastLinked=key;await open({name:q.purchase_doc,...(q.purchase_doctype?{doctype:q.purchase_doctype}:{})},q.purchase_type||tab.value)}
watch(()=>props.navigationKey,()=>{if(catalog.value){consumeAction();openLinked()}})
watch(()=>props.buyingView,async value=>{const next=normalizeBuyingView(value);if(next!==tab.value)await changeTab(next,true)})
watch(()=>props.company,async value=>{if(value&&value!==company.value){company.value=value;await companyChanged()}})
</script>

<template><section class="procurement-workspace" :class="{'procurement-workspace--mobile':mobile}">
 <LotusMobileFeedback v-if="mobile&&error&&!form&&!current" kind="error">{{error}}</LotusMobileFeedback>
 <LotusMobileFeedback v-if="notice" kind="success">{{notice}}</LotusMobileFeedback>
 <p v-if="!mobile&&!catalog&&error" role="alert" class="lotus-list-page__error">{{error}}</p>
 <template v-if="catalog">
 <nav v-if="!embedded||mobile" class="procurement-tabs" aria-label="Mua hàng"><component :is="button" v-for="[id,label] in visibleTabs" :key="id" :aria-current="tab===id?'page':undefined" :disabled="saving" @click="changeTab(id)">{{label}}</component></nav>

 <nav v-if="!mobile&&groupTabs.length>1" class="procurement-subtabs" :aria-label="tabLabel"><button v-for="[id,label] in groupTabs" :key="id" type="button" :aria-current="tab===id?'page':undefined" :disabled="saving" @click="changeTab(id)">{{label}}</button></nav>

 <p v-if="!mobile&&error&&['payables','invoice-queue'].includes(tab)&&!form&&!current" role="alert" class="lotus-list-page__error">{{error}}</p>
 <ProcurementMasters v-if="isMaster" ref="masterView" :key="company+tab" :company="company" :kind="tab" :mobile="mobile" @navigate="navigateMaster"><template #scope><LotusField v-if="companyOptions.length>1" v-model="company" :mobile="mobile" :label="mobile?'Công ty':undefined" aria-label="Công ty" :options="companyOptions" :searchable="false" :empty-option="null" :disabled="hasChanges()" @update:model-value="companyChanged"/></template></ProcurementMasters>

 <ErpSection v-else-if="erpView" :key="erpView.id" :section="erpView" view-param="buying_view" :company="company"/>

 <section v-else-if="tab==='reports'&&erpReportSel&&!mobile" class="procurement-erp-report">
  <LotusField v-model="erpReportName" class="procurement-erp-report__kind" label="Loại báo cáo" :options="reportKinds" :searchable="false" :empty-option="null"/>
  <ErpReport :key="erpReportSel.name" :name="erpReportSel.name" :label="erpReportSel.label" :company="company" :show-back="false"/>
 </section>

 <PayablesView v-else-if="tab==='payables'&&!(mobile&&(current||form))" :key="'payables-'+company" :company="company" :mobile="mobile" :today="asof" :can-pay="!!catalog.can_finance" :suppliers="supplierOptions"
  @open="(row,type)=>open(row,type)" @notice="success" @error="value=>error=value"/>
 <InvoiceQueue v-else-if="tab==='invoice-queue'&&!(mobile&&(current||form))" :key="'invoice-queue-'+company" :company="company" :mobile="mobile" :today="asof" :can-post="!!catalog.can_finance" :suppliers="supplierOptions"
  @created="invoiceCreated" @open="row=>open(row,row.mua_nhanh?'quick':'receipts')" @notice="success" @error="value=>error=value"/>
 <ProcurementCompare v-else-if="tab==='compare'" :key="'compare-'+company" :company="company" :mobile="mobile" :can-create="catalog.can_create" :api="api" @created="compareCreated"/>

 <ListPage v-else-if="!mobile" :title="tabLabel" :rows="shownRows" :columns="columns" :loading="busy" :error="form||current?'':error" v-model:search="search" :search-placeholder="isPaged?'Tìm số chứng từ, hóa đơn…':'Tìm trong danh sách…'" :summary="summary"
   :paged="isPaged" :start="queryStart" :page-size="queryPageSize" @update:page-size="value=>{queryPageSize=value;queryReset()}" :total="queryTotal" :has-more="queryMore" @update:start="value=>{queryStart=value;load()}" @refresh="load"
   :storage-key="'procurement-'+tab" show-empty-headers :interactive="tab!=='reports'" :empty="busy?'Đang tải…':'Chưa có chứng từ phù hợp.'" @open="open">
  <template #filters><LotusField v-if="tab==='needs'" v-model="proposalStage" aria-label="Tiến độ đề xuất" :options="proposalStageOptions" empty-option="Mọi giai đoạn" :searchable="false"/>
   <LotusField v-if="companyOptions.length>1" v-model="company" aria-label="Công ty" :options="companyOptions" :searchable="false" :empty-option="null" @update:model-value="companyChanged"/>
   <template v-if="isPaged">
    <LotusField v-model="supplier" aria-label="Nhà cung cấp" :options="supplierOptions" placeholder="Tất cả nhà cung cấp" @update:model-value="queryReset"/>
    <LotusField v-if="tab==='payables'" v-model="asof" aria-label="Chốt đến" type="date" @update:model-value="queryReset"/>
    <template v-else><DateRangePicker v-model:from="fromDate" v-model:to="toDate" @change="queryReset"/><LotusField v-model="queryState" aria-label="Trạng thái" :options="stateOptions" :searchable="false" empty-option="Mọi trạng thái" @update:model-value="queryReset"/></template>
   </template>
   <template v-if="tab==='reports'">
    <LotusField v-if="erpReports.length" v-model="erpReportName" aria-label="Loại báo cáo" :options="reportKinds" :searchable="false" :empty-option="null"/>
    <LotusField v-model="period" aria-label="Tháng" type="month" :max="asof.slice(0,7)"/>
    <LotusField v-model="asof" aria-label="Chốt đến" type="date"/>
    <LotusField v-model="supplier" aria-label="Nhà cung cấp" :options="supplierOptions" placeholder="Tất cả nhà cung cấp"/>
    <LotusField v-model="kind" aria-label="Loại mua" :options="purchaseKinds" :searchable="false" empty-option="Mọi loại mua"/>
    <LotusField v-model="farm" aria-label="Vườn" :options="options(catalog.farms)" placeholder="Tất cả vườn"/>
   </template>
  </template>
  <template #actions>
   <Button v-if="tab==='quick'" @click="startQuick">Mua nhanh</Button>
   <Button v-if="tab==='needs'&&catalog.can_need" @click="start('need')">Lập đề xuất mua</Button>
   <Button v-if="tab==='quotes'&&catalog.can_quote" @click="start('quote')">Thêm báo giá</Button>
   <Button v-if="tab==='quotes'&&catalog.can_create" variant="outline" @click="changeTab('compare')">So sánh giá &amp; tạo đơn</Button>
   <Button v-if="tab==='orders'&&catalog.can_create" @click="start('order')">Thêm đơn mua</Button>
   <Button v-if="tab==='orders'" variant="outline" :aria-pressed="pendingOnly" @click="pendingOnly=!pendingOnly">{{pendingOnly?'Xem tất cả đơn':'Hàng chờ nhận'}}</Button>
   <Button v-if="['needs','quotes'].includes(tab)&&catalog.can_create" variant="outline" @click="start('import')">Nhập Excel</Button>
   <template v-if="tab==='payments'&&catalog.can_finance"><Button @click="start('payment')">Chi / tạm ứng NCC</Button><Button variant="outline" @click="start('funding')">Cá nhân chi hộ</Button><Button v-if="finance?.is_chief" variant="outline" @click="start('accounts')">Tài khoản chi hộ</Button></template>
   <template v-if="tab==='reports'"><Button @click="load">Áp dụng</Button><Button variant="outline" :disabled="saving" @click="exportReport">Xuất toàn bộ Excel</Button></template>
  </template>
  <template #before>
   <p v-if="tab==='quick'" class="lotus-form-note">Hàng mua lẻ đã về: bấm <b>Mua nhanh</b>, chụp hóa đơn, kiểm tra rồi lưu là hàng vào kho ngay, không cần đề xuất hay đơn mua. Đợt mua lớn theo kế hoạch tháng vẫn đi Đề xuất mua → So sánh giá → Đơn mua.</p>
   <p v-if="tab==='reports'&&report?.note" class="lotus-form-note">{{report.note}}</p>
   <FormSection v-if="tab==='payments'&&finance?.vouchers?.length" title="Phiếu chờ ký"><div class="procurement-actions"><Button v-for="v in finance.vouchers" :key="v.name" variant="outline" size="sm" @click="current=v;detailType='voucher'">{{v.name}} · {{money(v.amount)}} · {{v.signing?.waiting_for}}</Button></div></FormSection>
  </template>
  <template #cell-quotation="{row}"><Button variant="link" @click="open(row,'quotes')">{{row.quotation}}</Button></template>
 </ListPage>

 <template v-else-if="!form&&!current">
  <div class="procurement-toolbar">
   <LotusField v-if="companyOptions.length>1" v-model="company" mobile label="Công ty" :options="companyOptions" @update:model-value="companyChanged"/>
   <template v-if="isPaged"><LotusField v-model="supplier" mobile label="Nhà cung cấp" :options="[{value:'',label:'Tất cả'},...supplierOptions]" @update:model-value="queryReset"/><LotusField v-if="tab==='payables'" v-model="asof" mobile type="date" label="Chốt đến" @update:model-value="queryReset"/><template v-else><LotusField v-model="fromDate" mobile type="date" label="Từ ngày" @update:model-value="queryReset"/><LotusField v-model="toDate" mobile type="date" label="Đến ngày" @update:model-value="queryReset"/><LotusField v-model="queryState" mobile label="Trạng thái" :searchable="false" :options="[{value:'',label:'Tất cả'},...stateOptions]" @update:model-value="queryReset"/></template></template>
   <template v-if="tab==='reports'"><LotusField v-model="period" mobile label="Tháng" type="month"/><LotusField v-model="asof" mobile type="date" label="Chốt đến"/><LotusField v-model="supplier" mobile label="Nhà cung cấp" :options="[{value:'',label:'Tất cả'},...supplierOptions]"/><LotusField v-model="kind" mobile label="Loại mua" :options="[{value:'',label:'Tất cả'},...purchaseKinds]" :searchable="false"/></template>
   <LotusField v-else v-model="search" mobile label="Tìm kiếm" placeholder="Tìm trong danh sách…"/>
   <component :is="button" :disabled="busy||saving" @click="load">{{tab==='reports'?'Áp dụng':'Làm mới'}}</component>
   <component :is="button" v-if="tab==='needs'&&catalog.can_need" @click="start('need')">Thêm đề xuất</component>
   <component :is="button" v-if="tab==='quotes'&&catalog.can_quote" @click="start('quote')">Thêm báo giá</component>
   <component :is="button" v-if="tab==='quotes'&&catalog.can_create" :disabled="!Object.values(selections).some(r=>r.selected)||saving" @click="chooseQuotes">Tạo đơn từ dòng chọn</component>
   <component :is="button" v-if="tab==='orders'&&catalog.can_create" @click="start('order')">Thêm đơn mua</component>
   <component :is="button" v-if="tab==='orders'" :aria-pressed="pendingOnly" @click="pendingOnly=!pendingOnly">{{pendingOnly?'Xem tất cả đơn':'Hàng chờ nhận'}}</component>
   <template v-if="tab==='payments'&&catalog.can_finance"><component :is="button" @click="start('payment')">Chi / tạm ứng NCC</component><component :is="button" @click="start('funding')">Cá nhân chi hộ</component></template>
  </div>
  <dl v-if="summary.length" class="procurement-totals"><div v-for="s in summary" :key="s.label"><dt>{{s.label}}</dt><dd>{{s.value}}</dd></div></dl>
  <CellGroup :border="false"><Cell v-for="(r,i) in shownRows" :key="r.name+'-'+i" :title="r.item_name||r.voucher_name||r.name" :label="[r.supplier_name||r.supplier,r.status||r.stage_label,r.date||r.delivery_date].filter(Boolean).join(' · ')" :value="money(tab==='quotes'?r.gross:r.amount)" :is-link="tab!=='reports'" @click="open(r)"/><Cell v-if="!shownRows.length" :title="busy?'Đang tải…':'Chưa có dữ liệu.'"/></CellGroup>
  <template v-if="tab==='payments'&&finance?.vouchers?.length"><h3>Phiếu chờ ký</h3><component :is="button" v-for="v in finance.vouchers" :key="v.name" @click="current=v;detailType='voucher'">{{v.name}} · {{money(v.amount)}} · {{v.signing?.waiting_for}}</component></template>
  <div v-if="isPaged" class="procurement-actions"><span>{{queryTotal?queryStart+1:0}}–{{queryStart+rows.length}} / {{queryTotal}}</span><component :is="button" :disabled="!queryStart||busy" @click="queryStart-=queryPageSize;load()">Trước</component><component :is="button" :disabled="!queryMore||busy" @click="queryStart+=queryPageSize;load()">Sau</component></div>
 </template>

 <ResponsiveForm :mobile="mobile" :model-value="!!current&&!form" :title="detailTitle" readonly width="1080px" :busy="saving" :error="error" @update:model-value="value=>!value&&(current=null)">
  <template v-if="current">
   <MobilePurchaseOrderDetail v-if="mobile&&detailType==='orders'" :order="current" :warehouses="catalog.warehouses"/>
   <CellGroup v-else-if="mobile&&current.items&&!['receipts','invoices'].includes(detailType)" :border="false"><Cell v-for="(r,i) in current.items" :key="r.line||i" :title="r.item_name" :label="r.uom" :value="String(r.qty)"/></CellGroup>
   <DataTable v-else-if="current.items&&!['receipts','invoices'].includes(detailType)" :rows="current.items" :columns="lineColumns"/>

   <NeedDetail v-if="detailType==='needs'" :detail="current" :mobile="mobile" :company="company" :can-order="!!catalog.can_create" :saving="saving" :ask="ask"
    @changed="proposalChanged" @deleted="proposalDeleted" @edit="editProposal" @order="orderFromProposal" @open="(row,type)=>open(row,type)"
    @notice="success" @error="value=>error=value"/>
   <template v-if="detailType==='quotes'">
    <dl class="lotus-form-totals"><div><dt>Nhà cung cấp</dt><dd>{{current.supplier}}</dd></div><div><dt>Giá đủ / ĐVT kho</dt><dd>{{money(current.unit_cost)}}</dd></div><div><dt>Ngày giao</dt><dd>{{current.delivery_date||'—'}}</dd></div></dl>
    <LotusField v-if="mobile" mobile v-model="selection(current).reason" label="Lý do lựa chọn"/>
    <LotusField v-if="current.docstatus===1&&catalog.can_quote" v-model="notes" :mobile="mobile" label="Lý do hủy báo giá" placeholder="Chỉ cần khi hủy hẳn báo giá đã xác nhận"/>
   </template>
   <OrderDetail v-if="detailType==='orders'" :detail="current" :chain="chain" :mobile="mobile" :company="company" :saving="saving" :ask="ask"
    @changed="orderChanged" @deleted="orderDeleted" @edit="editOrder" @receive="prepareReceipt('receive')" @open="(row,type)=>open(row,type)"
    @notice="success" @error="value=>error=value"/>
   <InvoiceDetail v-if="detailType==='invoices'" :name="current.name" :mobile="mobile" :ask="ask" @changed="load" @open="(row,type)=>open(row,type)"
    @pay="payInvoice" @credit="prepareReceipt('credit')" @notice="success" @error="value=>error=value"/>
   <ReceiptDetail v-if="detailType==='receipts'" :name="current.name" :mobile="mobile" :today="asof" :can-invoice="!!catalog.can_finance" :ask="ask"
    @changed="receiptChanged" @deleted="receiptDeleted" @open="(row,type)=>open(row,type)" @invoice="enterInvoice([current.name])" @credit="creditAfterReturn"
    @notice="success" @error="value=>error=value"/>
   <VoucherDetail v-if="['voucher','payments'].includes(detailType)&&!current.audit_only" :doctype="current.doctype||'Journal Entry'" :name="current.voucher_name||current.name" :mobile="mobile" :ask="ask"
    @changed="load" @deleted="voucherGone" @open="(row,type)=>open(row,type)" @notice="success" @error="value=>error=value"/>
  </template>
  <template #actions><template v-if="current">
   <template v-if="detailType==='quotes'"><component :is="button" v-if="mobile&&current.docstatus===1&&current.gross!=null" type="button" @click="selection(current).selected=true;current=null">Chọn báo giá này</component><component :is="button" v-if="current.docstatus===0&&catalog.can_quote" type="button" :disabled="saving" @click="act('confirm_quotation','procurement')">Xác nhận báo giá</component><component :is="button" v-if="current.docstatus===0&&catalog.can_quote" type="button" variant="outline" :disabled="saving" @click="editQuote">Sửa báo giá</component><component :is="button" v-if="current.docstatus===0&&catalog.can_quote" type="button" variant="outline" :disabled="saving" @click="cancelQuote(false)">Xóa báo giá nháp</component><component :is="button" v-if="current.docstatus===1&&catalog.can_quote" type="button" variant="outline" :disabled="saving" @click="cancelQuote(true)">Hủy để sửa lại</component><component :is="button" v-if="current.docstatus===1&&catalog.can_quote" type="button" variant="outline" :disabled="saving||notes.trim().length<3" @click="cancelQuote(false)">Hủy báo giá</component></template>
   <template v-if="['voucher','payments'].includes(detailType)"><component :is="link" v-if="current.evidence" as="a" variant="outline" :href="current.evidence" target="_blank" rel="noopener">Chứng từ gốc</component><component :is="button" v-if="catalog.can_finance&&current.funding?.classification==='Reimbursable'&&current.funding.remaining>0&&current.docstatus===1" type="button" @click="reimburse(current.funding)">Hoàn từng phần · còn {{money(current.funding.remaining)}}</component></template>
  </template></template>
 </ResponsiveForm>

 <MobilePurchaseOrderForm v-if="mobile&&form==='order'" v-model="draft" :items="catalog.items" :conversions="catalog.conversions" :suppliers="catalog.suppliers" :farms="catalog.farms" :warehouses="catalog.warehouses" :can-create-supplier="catalog.can_create_supplier" :can-create-item="catalog.can_create_item" :saving="saving" @add-supplier="openQuickMaster('suppliers')" @add-item="openQuickMaster('items',$event)" @submit="saveDocument"/>
 <ResponsiveForm v-else :mobile="mobile" :model-value="!!form" :title="formTitle" width="1180px" :busy="saving" :error="error" :submit-label="formSubmitLabel" :submit-disabled="formDisabled" @update:model-value="value=>!value&&closeForm()" @submit="submitForm">
  <ProcurementDocumentForm v-if="['order','quote','need'].includes(form)" v-model="draft" :mobile="mobile" :catalog="catalog" :type="form" :saving="saving" @add-supplier="openQuickMaster('suppliers')" @add-item="openQuickMaster('items',$event)" @request="fromRequest"/>
  <template v-else-if="['invoice','credit'].includes(form)">
   <FormGrid :columns="mobile?1:4"><LotusField :mobile="mobile" v-model="date" label="Ngày ghi sổ" type="date" required/><template v-if="['invoice','credit'].includes(form)"><LotusField :mobile="mobile" v-model="bill" label="Số hóa đơn" required/><LotusField :mobile="mobile" v-model="billdate" label="Ngày hóa đơn" type="date" required/><LotusField v-if="form==='invoice'" :mobile="mobile" v-model="dueDate" label="Hạn thanh toán" type="date" required/></template></FormGrid>
   <FormGrid v-if="form==='invoice'" :columns="mobile?1:4"><LotusField :mobile="mobile" v-model="billSeries" label="Ký hiệu hóa đơn" placeholder="VD: 1C26TKN" maxlength="20"/><LotusField :mobile="mobile" v-model="cqtCode" label="Mã cơ quan thuế" maxlength="60"/><LotusField :mobile="mobile" v-model="invoiceVat" label="Tiền thuế trên hóa đơn" type="money" min="0"/><LotusField :mobile="mobile" v-model="invoiceTotal" label="Tổng cộng trên hóa đơn" type="money" min="0" hint="Nhập đúng số in trên hóa đơn để khớp từng đồng"/></FormGrid>
   <LineItemsEditor :model-value="receiveInfo?.items||[]" title="Số lượng lập hóa đơn" :columns="stageColumns" :mobile="mobile" fixed>
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
     <LotusField :mobile="mobile" v-model="mappings[r.key].type" label="Nguồn" :options="[{value:'Need',label:'Đề xuất mua'},{value:'Quotation',label:'Báo giá'}]" :searchable="false"/>
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
 <template v-if="!mobile&&catalog?.can_quick"><StockDocumentForm ref="quickForm" :company="company" :warehouse="props.warehouse" :warehouses="stockWarehouses" :session="stockSession" @saved="quickSaved"/>
 <StockDocumentDetail ref="quickDetail" :warehouses="stockWarehouses" :session="stockSession" @changed="load" @edit="d=>quickForm.edit(d)"/></template>
 <PaymentForm v-model="paymentForm" :supplier="paymentSupplier" :company="company" :preset="paymentPreset" :mobile="mobile" :today="asof" @created="paymentCreated"/>
 <InvoiceForm v-model="invoiceForm" :receipts="invoiceReceipts" :suppliers="supplierOptions" :mobile="mobile" :today="asof" @created="invoiceCreated"/>
 <WarehouseReceiving ref="receivingView" :company="company" :warehouse="props.warehouse" :today="asof" :mobile="mobile" :confirm="ask" :can-invoice="!!catalog?.can_finance" @changed="load" @open="(row,type)=>open(row,type)" @invoice="d=>enterInvoice([d.name])"/>
 <WorkspaceModal v-if="!mobile" :model-value="!!quickMaster" :title="quickMaster==='suppliers'?'Thêm nhà cung cấp':'Thêm hàng mua'" width="1080px" @update:model-value="value=>!value&&closeQuickMaster()"><ProcurementMasterForm v-if="quickMaster" ref="masterSaving" :company="company" :kind="quickMaster" @saved="quickMasterSaved"/></WorkspaceModal>
 <LotusMobileDialog v-else ref="masterDialog" @cancel="closeQuickMaster"><h3>{{quickMaster==='suppliers'?'Thêm nhà cung cấp':'Thêm hàng mua'}}</h3><ProcurementMasterForm v-if="quickMaster" ref="masterSaving" :company="company" :kind="quickMaster" mobile @saved="quickMasterSaved"/><LotusMobileButton @click="closeQuickMaster">Đóng</LotusMobileButton></LotusMobileDialog>
 <WorkspaceConfirm v-if="!mobile" :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" confirm-label="Xác nhận" cancel-label="Quay lại" @answer="workspaceConfirm.finish"/>
 <LotusMobileDialog v-else ref="mobileDialog" @cancel="mobileConfirm.finish(false)"><h3>Xác nhận</h3><p>{{mobileMessage}}</p><LotusMobileButton @click="mobileConfirm.finish(false)">Quay lại</LotusMobileButton><LotusMobileButton @click="mobileConfirm.finish(true)">Xác nhận</LotusMobileButton></LotusMobileDialog>
</section></template>

<style>
.procurement-erp-report{display:grid;gap:10px;min-width:0}
.procurement-erp-report__kind{max-width:360px}
</style>
