<script setup>
import {computed,inject,onMounted,onUnmounted,ref,watch} from 'vue'
import {routerKey,routeLocationKey} from 'vue-router'
import {normalizeBuyingView} from '../procurement-navigation'
import ProcurementMasters from './ProcurementMasters.vue'
import ProcurementMasterForm from './ProcurementMasterForm.vue'
import WarehouseReceiving from './WarehouseReceiving.vue'
import {Cell,CellGroup} from 'vant'
import {call,upload,setCSRF} from '../api'
import {Button} from './ui/button'
import {Input} from './ui/input'
import {FormField} from './ui/form-field'
import DataTable from './DataTable.vue'
import ProcurementField from './ProcurementField.vue'
import ProcurementSigners from './ProcurementSigners.vue'
import ProcurementDocumentForm from './ProcurementDocumentForm.vue'
import MobilePurchaseOrderForm from './MobilePurchaseOrderForm.vue'
import MobilePurchaseOrderDetail from './MobilePurchaseOrderDetail.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileFile from './LotusMobileFile.vue'
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
const company=ref(props.company||''),session=ref(null),catalog=ref(null),tab=ref(props.buyingView?normalizeBuyingView(props.buyingView):props.embedded?'orders':'needs'),rows=ref([])
const busy=ref(false),saving=ref(false),error=ref(''),notice=ref(''),search=ref(''),form=ref(''),draft=ref(null),key=ref('')
const pendingOnly=ref(false)
const current=ref(null),chain=ref(null),detailType=ref(''),signerOptions=ref(null),signers=ref({}),selections=ref({}),finance=ref(null)
const period=ref((props.today||new Date().toISOString().slice(0,10)).slice(0,7)),asof=ref(props.today||new Date().toISOString().slice(0,10)),farm=ref(''),supplier=ref(props.initialSupplier||''),kind=ref(''),report=ref(null)
const sourceType=ref('Purchase Invoice'),source=ref(''),amount=ref(''),mode=ref('bank'),reference=ref(''),date=ref(asof.value)
const payerType=ref('Employee'),payer=ref(''),classification=ref('Reimbursable'),notes=ref(''),evidence=ref(null),duplicateReason=ref(''),allocations=ref([])
const bill=ref(''),billdate=ref(asof.value),quantities=ref({}),receiveInfo=ref(null),fundingName=ref('')
const file=ref(null),fileUrl=ref(''),preview=ref(null),mappings=ref({}),importWarehouse=ref(props.warehouse||'')
const workspaceConfirm=useWorkspaceConfirm(),mobileConfirm=useMobileConfirm()
const confirmOpen=workspaceConfirm.open,confirmTitle=workspaceConfirm.title,confirmMessage=workspaceConfirm.message
const mobileDialog=mobileConfirm.dialog,mobileMessage=mobileConfirm.message
const visibleTabs=computed(()=>procurementTabs.filter(([k])=>k!=='payments'||catalog.value?.can_view_finance).filter(([k])=>!['invoices','payables','reports','payments'].includes(k)||catalog.value?.can_view_finance).filter(([k])=>k!=='invoices'||catalog.value?.can_invoice))
const options=(values,label)=>values?.map(r=>({value:r.name,label:r[label]||r.name}))||[]
const shownRows=computed(()=>rows.value.filter(r=>(!pendingOnly.value||tab.value!=='orders'||r.docstatus===1&&Number(r.remaining_lines)>0&&r.status!=='Đã đóng')&&(!supplier.value||['reports','payables','payments','invoices'].includes(tab.value)||r.supplier===supplier.value)&&(!search.value||Object.values(r).filter(x=>typeof x!=='object').join(' ').toLocaleLowerCase().includes(search.value.toLocaleLowerCase()))))
const columns=computed(()=>tab.value==='payables'?[{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:190},{field:'name',headerName:'Chứng từ',minWidth:170},{field:'bill_no',headerName:'Hóa đơn NCC'},{field:'due_date',headerName:'Hạn trả'},{field:'amount',headerName:'Còn nợ / dư trả',valueFormatter:p=>money(p.value)},{field:'overdue_days',headerName:'Ngày quá hạn'},{field:'status',headerName:'Tình trạng'}]:tab.value==='quotes'?[
 {field:'choice',headerName:'Chọn',width:85},{field:'item_name',headerName:'Mặt hàng',minWidth:170},{field:'supplier',headerName:'Nhà cung cấp',minWidth:150},
 {field:'quotation',headerName:'Báo giá'},{field:'stock_qty',headerName:'SL ĐVT kho'},{field:'stock_uom',headerName:'ĐVT kho'},
 {field:'unit_cost',headerName:'Giá đủ/ĐVT kho',valueFormatter:p=>money(p.value)},
 {field:'net',headerName:'Chưa thuế',valueFormatter:p=>money(p.value)},{field:'tax',headerName:'VAT',valueFormatter:p=>money(p.value)},
 {field:'freight',headerName:'Vận chuyển',valueFormatter:p=>money(p.value)},{field:'gross',headerName:'Tổng trả',valueFormatter:p=>money(p.value)},
 {field:'delivery_date',headerName:'Ngày giao'},{field:'valid_till',headerName:'Hiệu lực'},
 {field:'reason',headerName:'Lý do chọn',minWidth:210}]:tab.value==='reports'?[
 {field:'date',headerName:'Ngày'},{field:'stage_label',headerName:'Giai đoạn',minWidth:170},{field:'name',headerName:'Chứng từ',minWidth:170},
 {field:'supplier',headerName:'Nhà cung cấp'},{field:'item_name',headerName:'Mặt hàng',minWidth:180},
 {field:'amount',headerName:'Số tiền',valueFormatter:p=>money(p.value)}]:[
 {field:'name',headerName:'Số chứng từ',minWidth:180},{field:'supplier_name',headerName:'Nhà cung cấp',valueGetter:p=>p.data.supplier_name||p.data.supplier||''},
 {field:'date',headerName:'Ngày',valueGetter:p=>p.data.date||p.data.expected_date||''},{field:'status',headerName:'Trạng thái'},
 {field:'amount',headerName:'Giá trị',valueFormatter:p=>money(p.value)}])
const lineColumns=[{field:'item_name',headerName:'Mặt hàng',minWidth:180},{field:'qty',headerName:'Số lượng'},{field:'uom',headerName:'ĐVT'},{field:'rate',headerName:'Đơn giá',valueFormatter:p=>money(p.value)}]
const sourceOptions=computed(()=>form.value==='refund'?[{value:source.value,label:source.value}]:(finance.value?.sources?.[sourceType.value]||[]).map(r=>({value:r.name,label:r.name+' · '+r.supplier+' · còn '+money(r.amount)})))
const payers=computed(()=>options(payerType.value==='Employee'?finance.value?.employees:finance.value?.shareholders,payerType.value==='Employee'?'employee_name':'title'))
const formTitle=computed(()=>({order:'Đơn mua',quote:'Báo giá',need:'Đề nghị mua',receive:'Nhận / nghiệm thu',invoice:'Lập hóa đơn',payment:'Chi / tạm ứng NCC',funding:'Ghi nhận chi hộ',reimburse:'Hoàn tiền chi hộ',accounts:'Tài khoản chi hộ',import:'Nhập Excel',return:'Trả hàng'}[form.value]||''))

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
 try{session.value=await api('bootstrap');setCSRF(session.value.csrf_token);company.value=props.company||company.value||session.value.companies?.[0]?.name||'';if(company.value)await companyChanged()}
 catch(e){error.value=e.message}
}
async function companyChanged(){current.value=null;form.value='';catalog.value=await api('bootstrap',{company:company.value});importWarehouse.value=props.warehouse||catalog.value.warehouses?.[0]?.name||'';if(!visibleTabs.value.some(([k])=>k===tab.value))tab.value='needs';await load()}
async function ask(text){return props.mobile?mobileConfirm.ask(text):workspaceConfirm.ask(text)}
async function closeForm(){if(saving.value||!await ask('Đóng biểu mẫu và bỏ phần chưa lưu?'))return;form.value='';draft.value=null}
async function changeTab(next,fromRoute=false){
 if(!fromRoute&&hasChanges()&&!await ask('Bỏ phần chưa lưu và chuyển mục?'))return false
 discardChanges();current.value=null;pendingOnly.value=false;queryStart.value=0;tab.value=normalizeBuyingView(next)
 if(!fromRoute&&router)await router.push({path:'/mua-hang',query:{...route.query,buying_view:tab.value,company:company.value,warehouse:props.warehouse||undefined}})
 else if(props.mobile){const url=new URL(location.href);url.searchParams.set('buying_view',tab.value);history.replaceState(history.state,'',url)}
 await load();return true
}
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
 if(['order','quote','need'].includes(type)){draft.value=newPurchaseDraft(props.warehouse||catalog.value.warehouses?.[0]?.name,asof.value);draft.value.valid_till=asof.value}
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
 if(type==='receive'){
  receiveInfo.value=await method('warehouse_planning','purchase_order',{name:current.value.name})
  for(const r of receiveInfo.value.items)quantities.value[r.line]=r.remaining_qty
 }else{
  receiveInfo.value={name:current.value.name,items:current.value.items}
  for(const r of current.value.items)quantities.value[r.line]=r.qty
 }
 form.value=type
}
async function submitStage(){await run(async()=>{
 const selected=Object.fromEntries(Object.entries(quantities.value).filter(([,q])=>Number(q)>0))
 let result
 if(form.value==='receive')result=await method('warehouse_planning','receive_order',{name:receiveInfo.value.name,posting_date:date.value,quantities:JSON.stringify(selected),client_event_id:key.value},true)
 if(form.value==='return')result=await api('return_receipt',{name:receiveInfo.value.name,posting_date:date.value,quantities:selected,client_key:key.value},true)
 if(form.value==='credit')result=await method('procurement_adjustments','credit_note',{company:company.value,name:receiveInfo.value.name,posting_date:date.value,bill_no:bill.value,bill_date:billdate.value,quantities:selected,client_key:key.value},true)
 if(form.value==='invoice')result=await api('invoice_receipt',{name:receiveInfo.value.name,bill_no:bill.value,bill_date:billdate.value,posting_date:date.value,quantities:selected,client_key:key.value},true)
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
defineExpose({hasChanges,discardChanges,refresh:load,createOrder,startReceiving})
let consumingAction=false
async function consumeAction(){if(consumingAction||route?.query.action!=='create_order')return;consumingAction=true;try{await createOrder();const q={...route.query};delete q.action;await router.replace({path:route.path,query:q})}finally{consumingAction=false}}
onMounted(()=>{initialLoad=initialize();initialLoad.then(consumeAction)})
watch(()=>props.navigationKey,()=>{if(catalog.value)consumeAction()})
watch(()=>props.buyingView,async value=>{const next=normalizeBuyingView(value);if(next!==tab.value)await changeTab(next,true)})
watch(()=>props.company,async value=>{if(value&&value!==company.value){company.value=value;await companyChanged()}})
</script>

<template><section class="procurement-workspace" :class="{'procurement-workspace--mobile':mobile}">
 <LotusMobileFeedback v-if="mobile&&error" kind="error">{{error}}</LotusMobileFeedback><p v-else-if="error" role="alert" class="procurement-error">{{error}}</p>
 <LotusMobileFeedback v-if="notice" kind="success">{{notice}}</LotusMobileFeedback>
 <template v-if="catalog">
 <nav v-if="!embedded||mobile" class="procurement-tabs" aria-label="Mua hàng"><component :is="button" v-for="[id,label] in visibleTabs" :key="id" :aria-current="tab===id?'page':undefined" :disabled="saving" @click="changeTab(id)">{{label}}</component></nav>
 <div v-if="!form&&tab!=='reports'" class="procurement-toolbar">
  <ProcurementField v-if="!props.company" v-model="company" :mobile="mobile" label="Công ty" :options="options(session?.companies)" @update:model-value="companyChanged"/>
  <ProcurementField v-if="!isMaster" v-model="search" :mobile="mobile" label="Tìm kiếm" placeholder="Tìm trong danh sách…"/>
  <component :is="button" :disabled="busy||saving" @click="load">Làm mới</component>
  <component :is="button" v-if="tab==='needs'&&catalog.can_need" @click="start('need')">Thêm đề nghị</component>
  <component :is="button" v-if="tab==='quotes'&&catalog.can_quote" @click="start('quote')">Thêm báo giá</component>
  <component :is="button" v-if="tab==='quotes'&&catalog.can_create" :disabled="!Object.values(selections).some(r=>r.selected)||saving" @click="chooseQuotes">Tạo đơn từ dòng chọn</component>
  <component :is="button" v-if="tab==='orders'&&catalog.can_create" @click="start('order')">Thêm đơn mua</component>
  <component :is="button" v-if="tab==='orders'" :aria-pressed="pendingOnly" @click="pendingOnly=!pendingOnly">{{pendingOnly?'Xem tất cả đơn':'Hàng chờ nhận'}}</component>
  <component :is="button" v-if="['needs','quotes'].includes(tab)&&catalog.can_create" @click="start('import')">Nhập Excel</component>
  <template v-if="tab==='payments'&&catalog.can_finance"><component :is="button" @click="start('payment')">Chi / tạm ứng NCC</component><component :is="button" @click="start('funding')">Cá nhân chi hộ</component><component :is="button" v-if="finance?.is_chief" @click="start('accounts')">Tài khoản chi hộ</component></template>
 </div>
 <template v-if="!form&&tab==='reports'">
  <div class="procurement-toolbar"><ProcurementField v-model="period" :mobile="mobile" label="Tháng YYYY-MM"/><ProcurementField v-model="asof" :mobile="mobile" type="date" label="Chốt đến"/><ProcurementField v-model="supplier" :mobile="mobile" label="Nhà cung cấp" :options="[{value:'',label:'Tất cả'},...options(catalog.suppliers,'supplier_name')]"/><ProcurementField v-model="kind" :mobile="mobile" label="Loại mua" :options="[{value:'',label:'Tất cả'},...purchaseKinds]" :searchable="false"/><ProcurementField v-model="farm" :mobile="mobile" label="Vườn" :options="[{value:'',label:'Tất cả'},...options(catalog.farms)]"/><component :is="button" @click="load">Áp dụng</component><component :is="button" :disabled="saving" @click="exportReport">Xuất toàn bộ Excel</component></div>
  <dl v-if="report" class="procurement-totals"><div v-for="(label,id) in report.stages" :key="id"><dt>{{label}}</dt><dd>{{money(report.totals[id])}}</dd></div></dl><p v-if="report" class="procurement-note">{{report.note}}</p>
 </template>
 <div v-if="isPaged&&!form&&!current" class="procurement-toolbar">
 <ProcurementField v-model="supplier" :mobile="mobile" label="Nhà cung cấp" :options="[{value:'',label:'Tất cả'},...options(catalog.suppliers,'supplier_name')]" @update:model-value="queryReset"/>
 <ProcurementField v-if="tab==='payables'" v-model="asof" :mobile="mobile" type="date" label="Chốt đến" @update:model-value="queryReset"/>
 <template v-else><ProcurementField v-model="fromDate" :mobile="mobile" type="date" label="Từ ngày" @update:model-value="queryReset"/><ProcurementField v-model="toDate" :mobile="mobile" type="date" label="Đến ngày" @update:model-value="queryReset"/><ProcurementField v-model="queryState" :mobile="mobile" label="Trạng thái" :searchable="false" :options="[{value:'',label:'Tất cả'},{value:'0',label:'Nháp / chờ ký'},{value:'1',label:'Đã ghi sổ'},{value:'2',label:'Đã hủy'}]" @update:model-value="queryReset"/></template>
 </div>
 <p v-if="tab==='payables'&&debt">Phải trả {{money(debt.owed)}} · Tạm ứng {{money(debt.advance)}} · Quá hạn {{money(debt.overdue)}} · Số dư thuần {{money(debt.net)}}</p>
 <ProcurementMasters v-if="isMaster" ref="masterView" :key="company+tab" :company="company" :kind="tab" :mobile="mobile" @navigate="navigateMaster"/>
 <template v-if="!form&&!current&&!isMaster">
  <DataTable v-if="!mobile" :rows="shownRows" :columns="columns" :loading="busy" :interactive="tab!=='reports'&&tab!=='quotes'" :storage-key="'procurement-'+tab" @open="open">
   <template #cell-quotation="{row}"><Button variant="link" @click="open(row,'quotes')">{{row.quotation}}</Button></template><template #cell-choice="{row}"><Input type="checkbox" :checked="selection(row).selected" :disabled="row.docstatus!==1||row.gross==null" :aria-label="'Chọn '+row.item_name+' từ '+row.supplier" @change="selection(row).selected=$event.target.checked"/></template>
   <template #cell-reason="{row}"><ProcurementField v-model="selection(row).reason" :aria-label="'Lý do chọn '+row.quotation"/></template>
  </DataTable>
  <CellGroup v-else :border="false"><Cell v-for="(r,i) in shownRows" :key="r.name+'-'+i" :title="r.item_name||r.name" :label="[r.supplier_name||r.supplier,r.status||r.stage_label,r.date||r.delivery_date].filter(Boolean).join(' · ')" :value="money(tab==='quotes'?r.gross:r.amount)" :is-link="tab!=='reports'" @click="open(r)"/><Cell v-if="!shownRows.length" :title="busy?'Đang tải…':'Chưa có dữ liệu.'"/></CellGroup>
  <template v-if="tab==='payments'&&finance?.vouchers?.length"><h3>Phiếu chờ ký</h3><component :is="button" v-for="v in finance.vouchers" :key="v.name" @click="current=v;detailType='voucher'">{{v.name}} · {{money(v.amount)}} · {{v.signing?.waiting_for}}</component></template>
 </template>
 <div v-if="isPaged&&!form&&!current" class="procurement-actions"><span>{{queryTotal?queryStart+1:0}}–{{queryStart+rows.length}} / {{queryTotal}}</span><component :is="button" :disabled="!queryStart||busy" @click="queryStart-=50;load()">Trước</component><component :is="button" :disabled="!queryMore||busy" @click="queryStart+=50;load()">Sau</component></div>
 <section v-if="current&&!form" class="procurement-detail">
  <div class="procurement-actions"><strong>{{current.name}}</strong><component :is="button" @click="current=null">Đóng chi tiết</component><a v-if="detailType!=='quotes'&&!current.audit_only" :href="docUrl(detailType==='orders'?'Purchase Order':detailType==='needs'?'Material Request':detailType==='invoices'?'Purchase Invoice':current.doctype||'Purchase Receipt',current.name)" target="_blank" rel="noopener">Chứng từ ERP</a></div>
  <MobilePurchaseOrderDetail v-if="mobile&&detailType==='orders'" :order="current" :warehouses="catalog.warehouses"/>
  <CellGroup v-else-if="mobile&&current.items" :border="false"><Cell v-for="(r,i) in current.items" :key="r.line||i" :title="r.item_name" :label="r.uom" :value="String(r.qty)"/></CellGroup><DataTable v-else-if="current.items" :rows="current.items" :columns="lineColumns"/>
  <template v-if="detailType==='needs'"><p>{{current.state||current.status}} · {{current.reason}}</p><ProcurementSigners v-if="current.can_send||current.can_sign||current.can_submit" :mobile="mobile" v-model="signers" :options="signerOptions"/><component :is="button" v-if="current.can_send||current.can_sign||current.can_submit" :disabled="saving" @click="proposalSign">Ký / gửi duyệt đề nghị</component><a :href="'/buying?proposal='+encodeURIComponent(current.name)">Mở quy trình đề nghị</a></template>
  <template v-if="detailType==='quotes'"><p>{{current.supplier}} · Giá đủ/ĐVT kho: {{money(current.unit_cost)}} · Giao {{current.delivery_date}}</p><ProcurementField v-if="mobile" :mobile="mobile" v-model="selection(current).reason" label="Lý do lựa chọn"/><component :is="button" v-if="mobile&&current.docstatus===1&&current.gross!=null" @click="selection(current).selected=true;current=null">Chọn báo giá này</component><component :is="button" v-if="current.docstatus===0&&catalog.can_quote" :disabled="saving" @click="act('confirm_quotation','procurement')">Xác nhận báo giá</component></template>
  <template v-if="detailType==='orders'">
 <a :href="'/lotus/in-phieu?'+new URLSearchParams({doctype:'Purchase Order',name:current.name})" target="_blank" rel="noopener">In đơn mua</a>
 <div class="procurement-actions"><component :is="button" v-if="current.can_manage&&!current.sent_at" :disabled="saving" @click="act('mark_order_sent')">Đã gửi NCC</component><component :is="button" v-if="current.can_manage&&current.sent_at&&!current.supplier_confirmed_at" :disabled="saving" @click="act('confirm_supplier_order')">NCC đã xác nhận</component></div>
 <div v-if="current.can_manage||current.can_close" class="procurement-actions"><ProcurementField v-model="deliveryDate" :mobile="mobile" type="date" label="Ngày giao hẹn lại"/><ProcurementField v-model="deliveryReason" :mobile="mobile" label="Lý do đổi hẹn / đóng phần còn lại"/><component :is="button" v-if="current.can_manage" :disabled="saving||!deliveryDate||!deliveryReason.trim()" @click="act('reschedule_order','purchasing',{expected_date:deliveryDate,reason:deliveryReason})">Đổi hẹn giao</component><component :is="button" v-if="current.can_close" :disabled="saving||!deliveryReason.trim()" @click="act('close_order','purchasing',{reason:deliveryReason})">Đóng phần chưa giao</component></div>
   <ProcurementSigners v-if="current.can_request_approval" :mobile="mobile" v-model="signers" :options="signerOptions"/>
   <component :is="button" v-if="current.can_request_approval" :disabled="saving" @click="act('request_approval','purchasing',{approver:signers.APPROVE})">Trình duyệt đơn</component>
   <component :is="button" v-if="current.can_approve" :disabled="saving" @click="act('approve_order')">Duyệt đơn</component>
   <component :is="button" v-if="current.can_receive" @click="prepareReceipt('receive')">Nhận / nghiệm thu từng phần</component>
   <section v-if="chain" class="procurement-chain"><h3>Chứng từ liên quan</h3><p v-for="r in chain.receipts" :key="r.name"><component :is="button" @click="open(r,'receipts')">{{r.name}} · {{r.date}} · {{r.docstatus===1?'Đã xác nhận':r.docstatus===2?'Đã hủy':'Nháp'}}</component></p><p v-for="r in chain.invoices" :key="r.name"><component :is="button" @click="open(r,'invoices')">{{r.name}}</component> · {{money(r.amount)}}</p><p v-for="r in chain.payments" :key="r.name">{{r.name}} · {{r.docstatus===1?'Đã trả':'Chờ ký'}} · {{money(r.amount)}}</p><p v-for="r in chain.funding" :key="r.name">{{r.name}} · {{r.status}} · Chi hộ {{money(r.amount)}} · Còn hoàn {{money(r.remaining)}}</p></section>
  </template>
  <template v-if="detailType==='invoices'"><p>{{current.supplier}} · Hóa đơn {{current.bill_no}} · Hạn {{current.due_date}} · Tổng {{money(current.amount)}} · Còn nợ {{money(current.outstanding_amount)}}</p><p v-for="t in current.taxes" :key="t.description">{{t.description}} · {{money(t.amount)}}</p><div class="procurement-actions"><component :is="button" v-if="catalog.can_finance&&current.docstatus===1&&!current.is_return" @click="start('payment')">Thanh toán hóa đơn</component><component :is="button" v-if="catalog.can_finance&&current.docstatus===1&&!current.is_return" @click="prepareReceipt('credit')">Lập hóa đơn điều chỉnh trả hàng</component><component :is="button" v-if="catalog.can_finance&&current.docstatus===1&&current.is_return&&current.outstanding_amount<0" @click="start('refund')">Ghi nhận NCC hoàn tiền</component></div></template>
  <template v-if="detailType==='receipts'"><p>{{current.docstatus===1?'Đã xác nhận':current.docstatus===2?'Đã hủy':'Nháp'}} · {{current.supplier}}</p><component :is="button" v-if="current.can_submit" :disabled="saving" @click="act('receipt_action','warehouse_planning',{action:'submit'})">Xác nhận nhận / nghiệm thu</component><component :is="button" v-if="current.docstatus===1&&!current.is_return&&catalog.can_finance" @click="prepareReceipt('invoice')">Lập hóa đơn</component><component :is="button" v-if="current.docstatus===1&&!current.is_return" @click="prepareReceipt('return')">Lập phiếu trả hàng</component><component :is="button" v-if="current.can_cancel" :disabled="saving" @click="ask('Hủy phiếu nhận và đảo sổ kho?').then(ok=>ok&&act('receipt_action','warehouse_planning',{action:'cancel'}))">Hủy phiếu nhận</component><a v-if="current.is_return&&current.docstatus===0" :href="docUrl('Purchase Receipt',current.name)" target="_blank" rel="noopener">Kiểm tra và xác nhận phiếu trả trên ERP</a></template>
  <template v-if="['voucher','payments'].includes(detailType)"><p v-if="current.reason">{{current.reason}}</p><a v-if="current.evidence" :href="current.evidence" target="_blank" rel="noopener">Chứng từ gốc</a><p>{{current.kind||current.classification}} · {{money(current.amount)}} · {{current.signing?.waiting_for}}</p><p v-for="s in current.signing?.steps||[]" :key="s.key">{{s.title}} · {{s.name}} · {{s.state}}</p><component :is="button" v-if="current.signing?.can_sign&&current.docstatus===0" :disabled="saving" @click="signVoucher">Ký duyệt</component><ProcurementField v-if="current.signing?.can_sign||catalog.can_finance&&current.docstatus===0" :mobile="mobile" v-model="notes" label="Lý do trả lại / hủy phiếu nháp"/><component :is="button" v-if="current.signing?.can_sign" :disabled="saving||!notes.trim()" @click="returnVoucher">Trả lại</component><component :is="button" v-if="catalog.can_finance&&current.docstatus===0" :disabled="saving||!notes.trim()" @click="cancelVoucher">Hủy phiếu chưa ghi sổ</component><component :is="button" v-if="catalog.can_finance&&current.funding?.classification==='Reimbursable'&&current.funding.remaining>0&&current.docstatus===1" @click="reimburse(current.funding)">Hoàn từng phần · còn {{money(current.funding.remaining)}}</component></template>
 </section>
 <section v-if="form" class="procurement-editor"><div class="procurement-actions"><strong>{{formTitle}}</strong><component :is="button" :disabled="saving" @click="closeForm">Đóng</component></div>
  <MobilePurchaseOrderForm v-if="mobile&&form==='order'" v-model="draft" :items="catalog.items" :conversions="catalog.conversions" :suppliers="catalog.suppliers" :farms="catalog.farms" :warehouses="catalog.warehouses" :can-create-supplier="catalog.can_create_supplier" :can-create-item="catalog.can_create_item" :saving="saving" @add-supplier="openQuickMaster('suppliers')" @add-item="openQuickMaster('items',$event)" @submit="saveDocument"/>
  <ProcurementDocumentForm @add-supplier="openQuickMaster('suppliers')" @add-item="openQuickMaster('items',$event)" v-else-if="['order','quote','need'].includes(form)" v-model="draft" :mobile="mobile" :catalog="catalog" :type="form" :saving="saving" @submit="saveDocument" @cancel="closeForm" @request="fromRequest"/>
  <form v-else-if="['receive','return','invoice','credit'].includes(form)" @submit.prevent="submitStage"><fieldset :disabled="saving"><ProcurementField :mobile="mobile" v-model="date" label="Ngày ghi sổ" type="date" required/><template v-if="['invoice','credit'].includes(form)"><ProcurementField :mobile="mobile" v-model="bill" label="Số hóa đơn" required/><ProcurementField :mobile="mobile" v-model="billdate" label="Ngày hóa đơn" type="date" required/></template><ProcurementField v-for="r in receiveInfo?.items||[]" :key="r.line" :mobile="mobile" v-model="quantities[r.line]" :label="r.item_name+' ('+r.uom+')'" type="number" min="0" :max="r.remaining_qty??r.qty" step="any"/><component :is="button" type="submit" :disabled="saving">{{['invoice','credit'].includes(form)?'Ghi nhận hóa đơn':'Tạo phiếu nháp'}}</component></fieldset></form>
  <form v-else-if="['payment','funding','reimburse','refund'].includes(form)" @submit.prevent="pay"><fieldset :disabled="saving"><div class="procurement-fields">
   <template v-if="form!=='reimburse'"><ProcurementField :mobile="mobile" v-model="sourceType" label="Nguồn mua" :options="['Purchase Invoice','Purchase Order'].map(v=>({value:v,label:v==='Purchase Order'?'Đơn mua (tạm ứng)':'Hóa đơn'}))" :searchable="false" @update:model-value="source=''"/><ProcurementField :mobile="mobile" v-model="source" label="Chứng từ nguồn" :options="sourceOptions" :required="form==='payment'"/></template>
   <ProcurementField :mobile="mobile" v-model="amount" label="Số tiền" type="number" min="1" step="any" required/><ProcurementField :mobile="mobile" v-model="date" :label="form==='funding'?'Ngày thực trả NCC':'Ngày công ty chi'" type="date" required/>
   <ProcurementField v-if="form!=='funding'" :mobile="mobile" v-model="mode" label="Phương thức" :options="[{value:'bank',label:'Chuyển khoản'},{value:'cash',label:'Tiền mặt'}]" :searchable="false"/>
   <ProcurementField :mobile="mobile" v-model="reference" :label="form==='funding'?'Số chứng từ gốc':'Số giao dịch ngân hàng'" :required="form==='funding'||mode==='bank'"/>
   <template v-if="form==='funding'"><ProcurementField :mobile="mobile" v-model="supplier" label="Nhà cung cấp được trả" :options="options(catalog.suppliers,'supplier_name')" required/><ProcurementField :mobile="mobile" v-model="payerType" label="Người chi" :options="[{value:'Employee',label:'Nhân viên'},{value:'Shareholder',label:'Chủ đầu tư / cổ đông'}]" :searchable="false" @update:model-value="payer=''"/><ProcurementField :mobile="mobile" v-model="payer" label="Tên người chi hộ" :options="payers" required/><ProcurementField :mobile="mobile" v-model="classification" label="Phân loại khoản chi" :options="[{value:'Reimbursable',label:'Công ty phải hoàn'},{value:'Equity',label:'Vốn góp, không hoàn'}]" :searchable="false" required/><ProcurementField :mobile="mobile" v-model="notes" label="Nội dung và căn cứ phân loại" type="textarea" required/><ProcurementField :mobile="mobile" v-model="duplicateReason" label="Giải thích nếu trùng chứng từ" type="textarea"/></template>
  </div><template v-if="form==='funding'"><FormField label="Chứng từ gốc riêng tư" required><component :is="mobile?LotusMobileFile:Input" type="file" accept="image/*,.pdf" required @change="evidence=$event.target.files?.[0]"/></FormField><component :is="button" type="button" :disabled="!source||!amount" @click="allocations.push({reference_type:sourceType,reference_name:source,amount:Number(amount)})">Thêm phân bổ nguồn đang chọn</component><p v-for="(a,i) in allocations" :key="i">{{a.reference_name}} · {{money(a.amount)}} <component :is="button" type="button" @click="allocations.splice(i,1)">Xóa</component></p></template><ProcurementSigners :mobile="mobile" v-model="signers" :options="signerOptions"/><component :is="button" type="submit" :disabled="saving||form==='funding'&&(!evidence||!allocations.length)">Lập phiếu và trình ký</component></fieldset></form>
  <form v-else-if="form==='accounts'" @submit.prevent="saveAccounts"><ProcurementField v-for="(label,k) in {purchase_funding_liability:'Phải hoàn cá nhân chi hộ',purchase_funding_equity:'Vốn góp bằng chi hộ'}" :key="k" :mobile="mobile" v-model="finance.mapping[k]" :label="label" :options="options(finance.accounts.filter(a=>a.root_type===(k.endsWith('equity')?'Equity':'Liability')&&!['Payable','Receivable'].includes(a.account_type)),'account_name')"/><component :is="button" type="submit" :disabled="saving">Lưu tài khoản</component></form>
  <template v-else-if="form==='import'"><a href="/api/method/lotus_farm.procurement_import.template">Tải mẫu Excel</a><FormField label="File Excel gốc"><component :is="mobile?LotusMobileFile:Input" type="file" accept=".xlsx" @change="file=$event.target.files?.[0];fileUrl='';preview=null;mappings={}"/></FormField><ProcurementField :mobile="mobile" v-model="importWarehouse" label="Kho mặc định" :options="options(catalog.warehouses,'warehouse_name')"/><component :is="button" :disabled="!file||saving" @click="importPreview">Xem trước / kiểm tra lại</component>
   <p v-if="preview?.previous?.length" role="alert">File đã nhập: {{preview.previous.join(', ')}}</p><ProcurementField v-if="preview?.previous?.length" :mobile="mobile" v-model="duplicateReason" label="Lý do tạo thêm chứng từ từ file này"/>
   <details v-for="r in preview?.rows||[]" :key="r.key" class="procurement-line"><summary>{{r.sheet}} · dòng {{r.row}} · {{r.item_label||r.source.slice(0,5).join(' · ')}} · {{r.errors.join('; ')||'Hợp lệ'}}</summary><div v-if="mappings[r.key]" class="procurement-fields"><ProcurementField :mobile="mobile" v-model="mappings[r.key].item" label="Mặt hàng" :options="options(catalog.items,'item_name')"/><ProcurementField :mobile="mobile" v-model="mappings[r.key].type" label="Nguồn" :options="[{value:'Need',label:'Đề nghị'},{value:'Quotation',label:'Báo giá'}]" :searchable="false"/><ProcurementField :mobile="mobile" v-model="mappings[r.key].qty" label="Số lượng" type="number"/><ProcurementField :mobile="mobile" v-model="mappings[r.key].uom" label="ĐVT" :options="[{value:catalog.items.find(i=>i.name===mappings[r.key].item)?.stock_uom,label:catalog.items.find(i=>i.name===mappings[r.key].item)?.stock_uom},...catalog.conversions.filter(c=>c.parent===mappings[r.key].item).map(c=>({value:c.uom,label:c.uom}))].filter(c=>c.value)"/><ProcurementField :mobile="mobile" v-model="mappings[r.key].rate" label="Đơn giá" type="number"/><ProcurementField :mobile="mobile" v-model="mappings[r.key].month" label="Tháng gốc YYYY-MM"/><ProcurementField :mobile="mobile" v-model="mappings[r.key].date" label="Ngày cần hàng / giao hàng đã xác nhận" type="date"/><ProcurementField :mobile="mobile" v-model="mappings[r.key].vat_code" label="VAT của đơn giá nguồn" :options="['KCT','0','5','8','10'].map(v=>({value:v,label:v}))" :searchable="false"/><ProcurementField :mobile="mobile" v-model="mappings[r.key].supplier" label="NCC báo giá" :options="options(catalog.suppliers,'supplier_name')"/><ProcurementField :mobile="mobile" v-model="mappings[r.key].warehouse" label="Kho" :options="options(catalog.warehouses,'warehouse_name')"/><ProcurementField :mobile="mobile" :model-value="mappings[r.key].skip?'yes':'no'" label="Bỏ qua dòng" :options="[{value:'no',label:'Nhập dòng này'},{value:'yes',label:'Bỏ qua'}]" :searchable="false" @update:model-value="mappings[r.key].skip=$event==='yes'"/></div></details>
   <component :is="button" v-if="preview" :disabled="saving||!preview.valid" @click="importCommit">Xác nhận tạo nháp</component>
  </template>
 </section>
 </template>
 <WarehouseReceiving ref="receivingView" :company="company" :warehouse="props.warehouse" :today="asof" :mobile="mobile" :confirm="ask" @changed="load"/>
 <WorkspaceModal v-if="!mobile" :model-value="!!quickMaster" :title="quickMaster==='suppliers'?'Thêm nhà cung cấp':'Thêm hàng mua'" @update:model-value="value=>!value&&closeQuickMaster()"><ProcurementMasterForm v-if="quickMaster" ref="masterSaving" :company="company" :kind="quickMaster" @saved="quickMasterSaved"/></WorkspaceModal>
 <LotusMobileDialog v-else ref="masterDialog" @cancel="closeQuickMaster"><h3>{{quickMaster==='suppliers'?'Thêm nhà cung cấp':'Thêm hàng mua'}}</h3><ProcurementMasterForm v-if="quickMaster" ref="masterSaving" :company="company" :kind="quickMaster" mobile @saved="quickMasterSaved"/><LotusMobileButton @click="closeQuickMaster">Đóng</LotusMobileButton></LotusMobileDialog>
 <WorkspaceModal v-if="!mobile" v-model="confirmOpen" :title="confirmTitle" width="480px"><p>{{confirmMessage}}</p><Button @click="workspaceConfirm.finish(false)">Quay lại</Button><Button @click="workspaceConfirm.finish(true)">Xác nhận</Button></WorkspaceModal>
 <LotusMobileDialog v-else ref="mobileDialog" @cancel="mobileConfirm.finish(false)"><h3>Xác nhận</h3><p>{{mobileMessage}}</p><LotusMobileButton @click="mobileConfirm.finish(false)">Quay lại</LotusMobileButton><LotusMobileButton @click="mobileConfirm.finish(true)">Xác nhận</LotusMobileButton></LotusMobileDialog>
</section></template>

<style>
.procurement-workspace{display:grid;gap:var(--lotus-space-3);min-width:0}.procurement-tabs,.procurement-toolbar,.procurement-actions{display:flex;align-items:end;gap:var(--lotus-space-2);overflow-x:auto;padding:var(--lotus-space-2) 0}.procurement-tabs>*{flex-shrink:0}.procurement-tabs [aria-current=page]{box-shadow:inset 0 -3px var(--lotus-primary)}.procurement-toolbar>*{min-width:140px;flex-shrink:0}.procurement-toolbar .lotus-field{width:180px}.procurement-fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:var(--lotus-space-3)}.procurement-form fieldset,.procurement-editor fieldset{border:0;min-width:0;padding:0;display:grid;gap:var(--lotus-space-3)}.procurement-line,.procurement-detail,.procurement-editor{padding:var(--lotus-space-3);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius);min-width:0}.procurement-line{margin-block:var(--lotus-space-2)}.procurement-totals{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:var(--lotus-space-2);margin:0}.procurement-totals>div{padding:var(--lotus-space-2);background:var(--lotus-soft)}.procurement-totals dd{margin:0;font-weight:600}.procurement-error{color:var(--lotus-danger)}.procurement-note{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}.procurement-workspace--mobile .procurement-fields{grid-template-columns:minmax(0,1fr)}.procurement-workspace--mobile .procurement-toolbar>*{min-width:140px}.procurement-workspace--mobile .procurement-actions{align-items:center;flex-wrap:wrap}.procurement-workspace--mobile .procurement-editor{padding:var(--lotus-space-2)}.procurement-workspace--mobile .procurement-detail{overflow-wrap:anywhere}.procurement-signers{border:0;display:grid;gap:var(--lotus-space-2);min-width:0;padding:var(--lotus-space-2) 0}.procurement-workspace--mobile .van-cell__title{min-width:0}.procurement-workspace--mobile .van-cell__value{flex:0 0 100px}.procurement-workspace--mobile .van-button{max-width:100%}
</style>
