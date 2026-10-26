<script setup>
// /lotus/tai-chinh — Tài chính – Kế toán on ERPNext's ledger: overview, documents waiting for an accountant,
// journal, payables, payment vouchers (signed accountant → chief accountant → director), reports and settings.
// Data: lotus_farm.finance.*. Payment approvers without ledger access see only the vouchers waiting for them.
import {computed,onMounted,ref,watch} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import LotusIcon from './components/LotusIcon.vue'
import LotusChart from './components/LotusChart.vue'
import WorkspaceConfirm from './components/WorkspaceConfirm.vue'
import SignerPicker from './components/SignerPicker.vue'
import DataTable from './components/DataTable.vue'
import FinanceGuide from './components/finance/FinanceGuide.vue'
import FinanceAssets from './components/finance/FinanceAssets.vue'
import FinancePlanning from './components/finance/FinancePlanning.vue'
import FinanceMasterImport from './components/finance/FinanceMasterImport.vue'
import {DateRangePicker} from './components/ui/date-picker'
import {Button as UiButton} from './components/ui/button'
import {Checkbox} from './components/ui/checkbox'
import WorkspaceTabs from './components/WorkspaceTabs.vue'
import WorkspaceSummaryStrip from './components/WorkspaceSummaryStrip.vue'
import ListPage from './components/ListPage.vue'
import ModalForm from './components/form/ModalForm.vue'
import FormGrid from './components/form/FormGrid.vue'
import FormSection from './components/form/FormSection.vue'
import LotusField from './components/form/LotusField.vue'
import LineItemsEditor from './components/form/LineItemsEditor.vue'
import ReasonDialog from './components/form/ReasonDialog.vue'
import PaymentModeFields from './components/finance/PaymentModeFields.vue'
import {useReasonDialog} from './use-reason-dialog'
import {financeNavigation,financeViewTitle} from './finance-navigation.js'
import {useWorkspaceConfirm} from './use-workspace-confirm'
import {useNoticeToast} from './use-toast'
import {call} from './api'
import {unitLabel} from './units'
import {useSession} from './store'
import './land.css'
import './finance.css'

defineProps({embedded:Boolean,navigationKey:String})
const F='lotus_farm.finance.'
const accountImportOpen=ref(false)
const TABS=[['overview','Tổng quan'],['planning','Kế hoạch tài chính'],['pending','Chờ hạch toán'],['journal','Nhật ký kế toán'],['sales','Bán hàng – Phải thu'],['payables','Công nợ phải trả'],['cash','Thu / Chi'],['assets','Tài sản cố định'],['reports','Báo cáo'],['settings','Thiết lập'],['guide','Hướng dẫn']]
const REPORTS=[['b01','B01 Tình hình tài chính'],['b02','B02 Kết quả kinh doanh'],['b03','B03 Lưu chuyển tiền tệ'],['trial_balance','Bảng cân đối phát sinh'],
 ['general_journal','Nhật ký chung'],['ledger','Sổ cái / sổ quỹ / tiền gửi'],['party','Công nợ theo đối tượng'],['stock','Nhập – xuất – tồn'],
 ['costs','Chi phí theo vườn / lô'],['costing','Giá thành theo lô'],['vat','Thuế GTGT'],['bank','Đối chiếu ngân hàng'],['reconciliation','Đối chiếu']]
const STATEMENTS=['b01','b02','b03']

const route=useRoute(),router=useRouter(),session=useSession()
const {open:confirmOpen,title:confirmTitle,message:confirmMessage,ask,finish:finishConfirm}=useWorkspaceConfirm()
const ledgerUser=computed(()=>!!session.capabilities?.finance_ledger)
const tab=computed(()=>ledgerUser.value?String(route.query.tab||'overview'):'sign')
const busy=ref(false),saving=ref(false),error=ref(''),notice=ref('')
const overview=ref(null),pendingData=ref(null),journalRows=ref([]),payData=ref(null),cash=ref(null),mine=ref([]),settings=ref(null),lookups=ref(null)
const report=ref('trial_balance'),reportData=ref(null),groupBy=ref('lotus_farm_block'),ledgerAccount=ref('')
const today=String(session.today||new Date().toISOString().slice(0,10))
const range=ref({from:today.slice(0,8)+'01',to:today})
const num=(v,d=0)=>v==null||v===''?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:d})
const vnd=v=>v==null?'—':num(Math.round(Number(v))||0)+' đ'
const vnDate=v=>v?String(v).slice(8,10)+'/'+String(v).slice(5,7)+'/'+String(v).slice(0,4):'—'
const dimLabel=(field,value)=>{if(!value)return '';if(field==='lotus_farm_block'){const b=(lookups.value?.blocks||[]).find(x=>x.name===value);return b?b.block_code:value}return value}
function go(next){router.push({path:'/tai-chinh',query:{...route.query,tab:next}})}
async function run(fn){busy.value=true;error.value='';try{return await fn()}catch(e){error.value=e.message}finally{busy.value=false}}
async function ensureLookups(){if(!lookups.value)lookups.value=await call(F+'reports.lookups')}
async function importedAccounts(result){notice.value=`Đã nhập ${result.count} tài khoản; bỏ qua ${result.skipped} tài khoản đã có.`;await run(async()=>{[settings.value,lookups.value]=await Promise.all([call(F+'api.settings'),call(F+'reports.lookups')])})}
async function load(){
 if(tab.value==='sign')return run(async()=>{mine.value=await call(F+'payments.my_vouchers')})
 return run(async()=>{
  if(!overview.value||tab.value==='overview')overview.value=await call(F+'reports.overview')
  if(tab.value==='pending')pendingData.value=await call(F+'reports.pending')
  if(tab.value==='journal'){await ensureLookups();journalRows.value=await call(F+'reports.journal',{from_date:range.value.from,to_date:range.value.to})}
  if(tab.value==='payables'){await ensureLookups();payData.value=await call(F+'reports.payables');await ensureVat()}
  if(tab.value==='sales'){await ensureLookups();await ensureVat();salesData.value=await call(F+'sales.receivables')}
  if(tab.value==='cash'){cash.value=await call(F+'payments.vouchers');mine.value=await call(F+'payments.my_vouchers')}
  if(tab.value==='reports'){await ensureLookups();await loadReport()}
  if(tab.value==='settings'){settings.value=await call(F+'api.settings');staff.value=await call(F+'api.people');await ensureLookups();await loadChecklist()}
 })
}
async function loadReport(){
 const args={from_date:range.value.from,to_date:range.value.to}
 if(reportData.value?.__report!==report.value)reportData.value=null
 if(report.value==='trial_balance')reportData.value=await call(F+'reports.trial_balance',args)
 if(report.value==='costs')reportData.value=await call(F+'reports.costs',{...args,group_by:groupBy.value})
 if(report.value==='reconciliation')reportData.value=await call(F+'reports.reconciliation',{on_date:range.value.to})
 if(report.value==='ledger')reportData.value=ledgerAccount.value?await call(F+'statements.general_ledger',{...args,account:ledgerAccount.value,party:ledgerParty.value||null}):null
 if(report.value==='b01')reportData.value=await call(F+'statements.b01',{on_date:range.value.to})
 if(report.value==='b02')reportData.value=await call(F+'statements.b02',args)
 if(report.value==='b03')reportData.value=await call(F+'statements.b03',args)
 if(report.value==='general_journal')reportData.value=await call(F+'statements.general_journal',args)
 if(report.value==='party')reportData.value=partyAccount.value?await call(F+'statements.party_summary',{...args,account:partyAccount.value}):null
 if(report.value==='stock')reportData.value=await call(F+'statements.stock_summary',args)
 if(report.value==='bank')reportData.value=bankResult.value
 if(reportData.value)reportData.value.__report=report.value
 if(report.value==='costing'){await ensureLookups();reportData.value=await call(F+'costing.preview',{month:range.value.to.slice(0,7)})}
 if(report.value==='vat'){await ensureVat();reportData.value=await call(F+'sales.vat_report',{month:range.value.to.slice(0,7)})}
}
const vatOptions=ref(null)
async function ensureVat(){if(!vatOptions.value)vatOptions.value=await call(F+'sales.vat_options',{on_date:today})}
const vatLabel=code=>(vatOptions.value?.rates||[]).find(r=>r.code===code)?.label||code||'KCT'
// Sales: customers, invoices that ship the goods, receipts
const salesData=ref(null),customerOpen=ref(false),customer=ref({}),saleOpen=ref(false),sale=ref({lines:[]}),saleStock=ref([]),receiptOpen=ref(false),receipt=ref({allocations:{}})
function openCustomer(row){customer.value=row?{name:row.customer,customer_name:row.customer_name,tax_id:row.tax_id,address:row.address,credit_days:row.credit_days}:{customer_name:'',tax_id:'',address:'',credit_days:0};customerOpen.value=true}
async function saveCustomer(){saving.value=true
 try{const r=await call(F+'sales.save_customer',{values:JSON.stringify(customer.value)},true);notice.value='Đã lưu khách hàng '+r.customer_name+'.';customerOpen.value=false;lookups.value=null;await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
function newSaleLine(){return {stock:'',qty:'',rate:'',batch_no:''}}
async function openSale(){await run(async()=>{saleStock.value=await call(F+'sales.stock_for_sale')});sale.value={customer:'',posting_date:today,due_date:'',vat_code:'KCT',einvoice_series:'',einvoice_no:'',lines:[newSaleLine()]};saleOpen.value=true}
const stockKey=s=>s.item_code+'|'+s.warehouse
const stockOf=l=>saleStock.value.find(s=>stockKey(s)===l.stock)
const saleNet=computed(()=>(sale.value.lines||[]).reduce((t,l)=>t+Math.round(Number(l.qty||0)*Number(l.rate||0)),0))
const saleTax=computed(()=>Math.round(saleNet.value*Number((vatOptions.value?.rates||[]).find(r=>r.code===sale.value.vat_code)?.rate||0)))
async function saveSale(){saving.value=true
 try{const lines=sale.value.lines.filter(l=>l.stock).map(l=>{const s=stockOf(l);return {item_code:s.item_code,warehouse:s.warehouse,qty:Number(l.qty),rate:Number(l.rate),batch_no:l.batch_no||null}})
  const r=await call(F+'sales.make_sales_invoice',{customer:sale.value.customer,posting_date:sale.value.posting_date,lines:JSON.stringify(lines),vat_code:sale.value.vat_code,
   due_date:sale.value.due_date||null,einvoice_series:sale.value.einvoice_series||null,einvoice_no:sale.value.einvoice_no||null},true)
  notice.value='Đã ghi hóa đơn bán '+r.invoice+' ('+vnd(r.amount)+', giá vốn '+vnd(r.cost)+').';saleOpen.value=false;await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
function openReceipt(row){receipt.value={customer:row.customer,customer_name:row.customer_name,mode:'bank',posting_date:today,reference_no:'',
 allocations:Object.fromEntries((salesData.value?.invoices||[]).filter(i=>i.customer===row.customer).map(i=>[i.name,Math.round(i.outstanding_amount)]))};receiptOpen.value=true}
const receiptInvoices=computed(()=>(salesData.value?.invoices||[]).filter(i=>i.customer===receipt.value.customer))
const receiptTotal=computed(()=>Object.values(receipt.value.allocations||{}).reduce((s,v)=>s+Number(v||0),0))
async function saveReceipt(){saving.value=true
 try{const allocations=Object.entries(receipt.value.allocations).filter(([,v])=>Number(v)>0).map(([invoice,amount])=>({invoice,amount:Number(amount)}))
  const r=await call(F+'sales.receive_payment',{customer:receipt.value.customer,allocations:JSON.stringify(allocations),mode:receipt.value.mode,posting_date:receipt.value.posting_date,reference_no:receipt.value.reference_no||null},true)
  notice.value='Đã ghi phiếu thu '+r.receipt+' ('+vnd(r.amount)+').';receiptOpen.value=false;await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
function exportVat(){location.href='/api/method/lotus_farm.finance.sales.export_vat?'+new URLSearchParams({month:range.value.to.slice(0,7)})}
function exportReport(kind){const q={kind,from_date:range.value.from,to_date:range.value.to};if(kind==='costs')q.group_by=groupBy.value
 const books={ledger:'general_ledger',party:'party_summary',stock:'stock_summary',general_journal:'general_journal',b01:'b01',b02:'b02',b03:'b03'}
 if(books[kind]){q.kind=books[kind];if(kind==='ledger'){q.account=ledgerAccount.value;if(ledgerParty.value)q.party=ledgerParty.value}if(kind==='party')q.account=partyAccount.value
  location.href='/api/method/lotus_farm.finance.statements.export?'+new URLSearchParams(q);return}
 location.href='/api/method/lotus_farm.finance.reports.export?'+new URLSearchParams(q)}
const ledgerParty=ref(''),partyAccount=ref(''),bankResult=ref(null)
async function readStatement(file){if(!file)return;saving.value=true
 try{const content=await new Promise((ok,fail)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=fail;r.readAsDataURL(file)})
  bankResult.value=await call(F+'statements.bank_match',{content},true);reportData.value={...bankResult.value,__report:'bank'}}
 catch(e){error.value=e.message}finally{saving.value=false}}
const indent=p=>'   '.repeat(Math.max(0,(p.data.level||1)-1))+p.data.name
const statementCell=p=>p.data?.total?'fin-cell-total':''
const statementColumns=computed(()=>{const value=(field,headerName)=>({field,headerName,minWidth:150,type:'numericColumn',cellClass:statementCell,
  valueFormatter:p=>p.value==null?'':Number(p.value)<0?'('+num(-p.value)+')':num(p.value)})
 const name={field:'name',headerName:'Chỉ tiêu',minWidth:360,flex:3,valueGetter:indent,cellClass:statementCell},code={field:'code',headerName:'Mã số',minWidth:80,maxWidth:100,cellClass:statementCell}
 if(report.value==='b01')return [name,code,value('closing','Số cuối kỳ'),value('opening','Số đầu năm')]
 if(report.value==='b02')return [name,code,value('current','Kỳ này'),value('previous','Cùng kỳ năm trước')]
 return [name,code,value('current','Kỳ này')]})
const checkColumns=computed(()=>[{field:'label',headerName:'Kiểm tra',minWidth:360,flex:3},{field:'difference',headerName:'Chênh lệch',minWidth:120,valueFormatter:p=>p.data.ok?'Khớp':num(p.value),cellClass:p=>p.data?.ok?'fin-cell-ok':'fin-cell-bad'}])
const journalBookColumns=computed(()=>[{field:'line',headerName:'STT',minWidth:70,maxWidth:80},dateCol('posting_date','Ngày'),{field:'voucher_type',headerName:'Loại chứng từ',minWidth:130},{field:'voucher_no',headerName:'Số chứng từ',minWidth:170},
 {field:'remarks',headerName:'Diễn giải',minWidth:220,flex:2},{field:'number',headerName:'TK',minWidth:80},{field:'party',headerName:'Đối tượng',minWidth:120},moneyCol('debit','Nợ'),moneyCol('credit','Có')])
const partyColumns=computed(()=>[{field:'party_name',headerName:'Đối tượng',minWidth:220,flex:2},moneyCol('opening_debit','Dư Nợ đầu kỳ'),moneyCol('opening_credit','Dư Có đầu kỳ'),moneyCol('debit','Phát sinh Nợ'),
 moneyCol('credit','Phát sinh Có'),moneyCol('closing_debit','Dư Nợ cuối kỳ'),moneyCol('closing_credit','Dư Có cuối kỳ')])
const partyTotals=computed(()=>report.value==='party'&&reportData.value?.totals?[{party:'__total',party_name:'Cộng',...reportData.value.totals}]:[])
const qty=p=>p.value?num(p.value,3):''
const stockColumns=computed(()=>[{field:'item_name',headerName:'Hàng',minWidth:200,flex:2},{field:'warehouse',headerName:'Kho',minWidth:160},{field:'stock_uom',headerName:'ĐVT',minWidth:70,valueFormatter:p=>p.data?.uom_label||unitLabel(p.value)},
 {field:'opening_qty',headerName:'Tồn đầu',minWidth:100,type:'numericColumn',valueFormatter:qty},moneyCol('opening_value','Giá trị đầu'),{field:'in_qty',headerName:'Nhập',minWidth:90,type:'numericColumn',valueFormatter:qty},
 moneyCol('in_value','Giá trị nhập'),{field:'out_qty',headerName:'Xuất',minWidth:90,type:'numericColumn',valueFormatter:qty},moneyCol('out_value','Giá trị xuất'),
 {field:'closing_qty',headerName:'Tồn cuối',minWidth:100,type:'numericColumn',valueFormatter:qty},moneyCol('closing_value','Giá trị cuối')])
const bankRows=computed(()=>report.value!=='bank'||!reportData.value?[]:[
 ...reportData.value.matched.map((x,i)=>({__key:'m'+i,state:'Khớp',date:x.statement.date,amount:x.statement.amount,reference:x.statement.reference||x.ledger.reference,description:x.statement.description||'',voucher:x.ledger.voucher})),
 ...reportData.value.statement_only.map((x,i)=>({__key:'s'+i,state:'Chỉ có trên sao kê',date:x.date,amount:x.amount,reference:x.reference,description:x.description,voucher:''})),
 ...reportData.value.ledger_only.map((x,i)=>({__key:'l'+i,state:'Chỉ có trên sổ',date:x.date,amount:x.amount,reference:x.reference,description:x.remarks,voucher:x.voucher}))])
const bankColumns=computed(()=>[{field:'state',headerName:'Kết quả',minWidth:150,cellClass:p=>p.value==='Khớp'?'fin-cell-ok':'fin-cell-warn'},dateCol('date','Ngày'),moneyCol('amount','Số tiền (+ vào / − ra)',{valueFormatter:p=>num(p.value)}),
 {field:'reference',headerName:'Tham chiếu',minWidth:130},{field:'description',headerName:'Nội dung',minWidth:220,flex:2},{field:'voucher',headerName:'Chứng từ trên sổ',minWidth:170}])

// Pending: supplier invoice from receipts, payroll preview/post
const picked=ref(new Set()),invoiceOpen=ref(false),invoice=ref({bill_no:'',bill_date:today,due_date:'',vat_code:'KCT'})
const pickedReceipts=computed(()=>(pendingData.value?.receipts||[]).filter(r=>picked.value.has(r.name)))
const pickedSupplier=computed(()=>[...new Set(pickedReceipts.value.map(r=>r.supplier))])
function togglePick(name){const next=new Set(picked.value);next.has(name)?next.delete(name):next.add(name);picked.value=next}
async function makeInvoice(){saving.value=true
 try{const r=await call(F+'payments.make_goods_invoice',{receipts:JSON.stringify([...picked.value]),bill_no:invoice.value.bill_no,bill_date:invoice.value.bill_date,due_date:invoice.value.due_date||null,vat_code:invoice.value.vat_code||'KCT'},true)
  notice.value='Đã ghi hóa đơn '+r.invoice+' ('+vnd(r.amount)+').';invoiceOpen.value=false;picked.value=new Set();await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
const payrollView=ref(null)
async function previewPayroll(name){await ensureLookups();await run(async()=>{payrollView.value=await call(F+'payroll.preview',{period:name})})}
async function postPayroll(){saving.value=true
 try{const r=await call(F+'payroll.post',{period:payrollView.value.period,source_hash:payrollView.value.source_hash},true)
  notice.value='Đã ghi sổ lương '+payrollView.value.month+': '+r.voucher+' ('+vnd(r.amount)+').';payrollView.value=null;await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
async function receiveHarvest(lot){if(!await ask('Nhập kho lô thu hoạch '+lot.name+' ('+num(lot.released_raw_kg,1)+' kg) theo giá thành tạm tính? Bút toán Nợ 155 / Có 154 theo từng lô trồng.','Nhập kho chuối thu hoạch'))return
 await run(async()=>{const r=await call(F+'costing.receive_harvest',{harvest_lot:lot.name},true);notice.value='Đã nhập kho '+num(r.kg,1)+' kg ('+vnd(r.amount)+'): '+r.stock_entry+'.';await load()})}

// Payables: supplier payment voucher, service invoice
const payOpen=ref(false),pay=ref({supplier:'',mode:'cash',posting_date:today,reference_no:'',allocations:{}}),signers=ref({}),signerOptions=ref(null)
const supplierInvoices=computed(()=>(payData.value?.invoices||[]).filter(i=>i.supplier===pay.value.supplier))
const payTotal=computed(()=>Object.values(pay.value.allocations).reduce((s,v)=>s+Number(v||0),0))
async function openPay(supplier){pay.value={supplier,mode:'cash',posting_date:today,reference_no:'',allocations:Object.fromEntries((payData.value?.invoices||[]).filter(i=>i.supplier===supplier).map(i=>[i.name,Math.max(0,i.outstanding_amount-(i.paying||0))]))}
 signerOptions.value=await call('lotus_farm.signing.candidates',{chain:'payment_voucher',company:overview.value?.company});payOpen.value=true}
async function preparePay(){saving.value=true
 try{const allocations=Object.entries(pay.value.allocations).filter(([,v])=>Number(v)>0).map(([invoice,amount])=>({invoice,amount:Number(amount)}))
  const r=await call(F+'payments.prepare_supplier_payment',{supplier:pay.value.supplier,allocations:JSON.stringify(allocations),mode:pay.value.mode,posting_date:pay.value.posting_date,
   signers:JSON.stringify(signers.value),reference_no:pay.value.reference_no||null},true)
  notice.value='Đã lập phiếu chi '+r.voucher+' và gửi Kế toán trưởng ký.';payOpen.value=false;await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
const serviceOpen=ref(false),service=ref({supplier:'',bill_no:'',bill_date:today,due_date:'',vat_code:'KCT',lines:[]})
function newServiceLine(){return {description:'',amount:'',cost:'production',lotus_farm:'',lotus_farm_block:'',lotus_work_type:''}}
function openService(){service.value={supplier:'',bill_no:'',bill_date:today,due_date:'',vat_code:'KCT',lines:[newServiceLine()]};serviceOpen.value=true}
const blocksOf=farm=>(lookups.value?.blocks||[]).filter(b=>!farm||b.farm===farm)
async function saveService(){saving.value=true
 try{const r=await call(F+'payments.make_service_invoice',{supplier:service.value.supplier,bill_no:service.value.bill_no,bill_date:service.value.bill_date,due_date:service.value.due_date||null,vat_code:service.value.vat_code||'KCT',
   lines:JSON.stringify(service.value.lines.map(l=>({...l,amount:Number(l.amount)})))},true)
  notice.value='Đã ghi hóa đơn dịch vụ '+r.invoice+' ('+vnd(r.amount)+').';serviceOpen.value=false;await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}

// Cash: sign / return vouchers, salary payment
async function sign(v){saving.value=true
 try{const r=await call(F+'payments.sign_payment',{doctype:v.doctype,name:v.name},true);notice.value=r.docstatus===1?'Đã ký đủ, phiếu chi '+v.name+' đã ghi sổ.':'Đã ký. Phiếu chuyển sang người ký tiếp theo.';await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
const returnOpen=ref(null),returnReason=ref('')
async function sendBack(){saving.value=true
 try{await call(F+'payments.return_payment',{doctype:returnOpen.value.doctype,name:returnOpen.value.name,reason:returnReason.value},true);notice.value='Đã trả lại phiếu chi cho người lập.';returnOpen.value=null;returnReason.value='';await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
async function dropDraft(v){if(!await ask('Hủy phiếu chi '+v.name+' chưa ký xong?','Hủy phiếu chi'))return
 await run(async()=>{await call(F+'payments.cancel_draft',{doctype:v.doctype,name:v.name,reason:'Hủy phiếu chi chưa ký'},true);notice.value='Đã hủy phiếu chi.';await load()})}
const advanceOpen=ref(false),advance=ref({employee:'',amount:'',month:today.slice(0,7),mode:'cash',posting_date:today,reference_no:''})
async function openAdvance(){await ensureLookups();advance.value={employee:'',amount:'',month:today.slice(0,7),mode:'cash',posting_date:today,reference_no:''}
 signerOptions.value=await call('lotus_farm.signing.candidates',{chain:'payment_voucher',company:overview.value?.company});advanceOpen.value=true}
async function prepareAdvance(){saving.value=true
 try{const r=await call(F+'payroll.prepare_advance',{...advance.value,amount:Number(advance.value.amount),signers:JSON.stringify(signers.value)},true)
  notice.value='Đã lập phiếu tạm ứng '+r.voucher+' và gửi ký.';advanceOpen.value=false;await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
const statutoryOpen=ref(false),statutory=ref({rows:[],mode:'bank',posting_date:today,reference_no:''})
async function openStatutory(){const rows=await call(F+'payroll.statutory_balances')
 statutory.value={rows:rows.map(r=>({...r,amount:r.payable||''})),mode:'bank',posting_date:today,reference_no:''}
 signerOptions.value=await call('lotus_farm.signing.candidates',{chain:'payment_voucher',company:overview.value?.company});statutoryOpen.value=true}
const statutoryTotal=computed(()=>statutory.value.rows.reduce((s,r)=>s+Number(r.amount||0),0))
async function prepareStatutory(){saving.value=true
 try{const r=await call(F+'payroll.prepare_statutory',{lines:JSON.stringify(statutory.value.rows.filter(x=>Number(x.amount)>0).map(x=>({key:x.key,amount:Number(x.amount)}))),
   mode:statutory.value.mode,posting_date:statutory.value.posting_date,reference_no:statutory.value.reference_no||null,signers:JSON.stringify(signers.value)},true)
  notice.value='Đã lập phiếu nộp '+r.voucher+' và gửi ký.';statutoryOpen.value=false;await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
function exportTransfer(period){location.href='/api/method/lotus_farm.finance.payroll.export_salary_transfer?'+new URLSearchParams({period})}
const salaryOpen=ref(null),salary=ref({mode:'bank',posting_date:today,reference_no:''})
async function openSalary(row){salary.value={mode:'bank',posting_date:today,reference_no:''};signerOptions.value=await call('lotus_farm.signing.candidates',{chain:'payment_voucher',company:overview.value?.company});salaryOpen.value=row}
async function prepareSalary(){saving.value=true
 try{const r=await call(F+'payroll.prepare_salary_payment',{period:salaryOpen.value.period,mode:salary.value.mode,posting_date:salary.value.posting_date,signers:JSON.stringify(signers.value),reference_no:salary.value.reference_no||null},true)
  notice.value='Đã lập phiếu chi lương '+r.voucher+'.';salaryOpen.value=null;await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}

// Reverse a posting (chief accountant)
async function reverse(postingName,label){if(!overview.value?.is_chief)return
 const reason=await reasonPrompt.ask('Đảo bút toán '+label,'Lý do đảo bút toán (bắt buộc)');if(!reason)return
 await run(async()=>{await call(F+'posting.reverse',{posting:postingName,reason},true);notice.value='Đã đảo bút toán '+label+'.';await load()})}

// Settings (chief accountant)
const form=ref({enabled:false,cutover_date:'',mapping:{}}),coa=ref(null),openingPreview=ref(null)
watch(settings,s=>{if(s)form.value={enabled:s.enabled,cutover_date:s.cutover_date,harvest_standard_cost:s.harvest_standard_cost||'',minimum_wage_region:s.minimum_wage_region||'',mapping:{...s.mapping}}})
const paramGroups={pit_progressive:'Thuế TNCN lũy tiến (giảm trừ gia cảnh)',pit_flat:'Thuế TNCN khấu trừ 10%',insurance:'Bảo hiểm, KPCĐ'}
const pct=v=>num(Math.round(Number(v)*1000)/10,1)+'%',sumOf=o=>Object.values(o||{}).reduce((a,b)=>a+b,0)
function paramSummary(r){if(r.group==='pit_progressive')return 'Bản thân '+num(r.self)+' · người phụ thuộc '+num(r.dependent)+' · '+r.brackets.map(b=>(b[0]?'đến '+num(b[0]/1e6)+' tr':'phần còn lại')+' '+pct(b[1])).join(', ')
 if(r.group==='pit_flat')return pct(r.rate)+' mỗi lần trả từ '+num(r.threshold)+' đ'
 return 'NLĐ '+pct(sumOf(r.employee))+' · DN '+pct(sumOf(r.employer))+' · KPCĐ '+pct(r.union_fee)+' · lương cơ sở '+num(r.base_salary)}
const accountLabel=a=>(a.account_number?a.account_number+' - ':'')+a.account_name
const accountsFor=key=>{const k=(settings.value?.keys||[]).find(x=>x.key===key);return (settings.value?.accounts||[]).filter(a=>!k||k.roots.includes(a.root_type))}
async function saveSettings(){saving.value=true
 try{settings.value=await call(F+'api.save_settings',{values:JSON.stringify(form.value)},true);notice.value=settings.value.enabled?'Đã lưu. Ghi sổ kế toán đang bật.':'Đã lưu cấu hình.';overview.value=null}
 catch(e){error.value=e.message}finally{saving.value=false}}
async function previewCoa(){await run(async()=>{coa.value=await call(F+'api.coa_preview',{on_date:today})})}
async function applyCoa(){if(!await ask('Áp dụng hệ thống tài khoản Thông tư 99: thêm '+coa.value.add.length+' tài khoản, đổi tài khoản kho và chuyển số dư cũ. Không hoàn tác bằng một nút được. Tiếp tục?','Áp dụng Thông tư 99'))return
 saving.value=true
 try{const r=await call(F+'api.coa_apply',{on_date:coa.value.on_date},true);notice.value='Đã áp dụng Thông tư 99: thêm '+r.added+' tài khoản'+(r.transfer?', chuyển số dư bằng '+r.transfer:'')+'.';coa.value=null;settings.value=await call(F+'api.settings')}
 catch(e){error.value=e.message}finally{saving.value=false}}
const year=ref(Number(today.slice(0,4)))
const months=computed(()=>Array.from({length:12},(_,i)=>year.value+'-'+String(i+1).padStart(2,'0')))
const periodOf=m=>(settings.value?.periods||[]).find(p=>String(p.start_date).slice(0,7)===m)
const closingView=ref(null)
async function previewClosing(m){await ensureLookups();await run(async()=>{closingView.value=await call(F+'closing.preview',{month:m})})}
async function postClosing(){saving.value=true
 try{const r=await call(F+'closing.post',{month:closingView.value.month},true);notice.value='Đã kết chuyển chi phí tháng '+closingView.value.month+' sang 154: '+r.voucher+' ('+vnd(r.amount)+').';closingView.value=null}
 catch(e){error.value=e.message}finally{saving.value=false}}
const checklistMonth=ref(today.slice(0,7)),checklist=ref(null)
async function loadChecklist(){checklist.value=await call(F+'api.month_checklist',{month:checklistMonth.value})}
watch(checklistMonth,()=>run(loadChecklist))
const resultView=ref(null)
async function previewResult(m){await run(async()=>{resultView.value=await call(F+'closing.result_preview',{month:m})})}
async function postResult(){saving.value=true
 try{const r=await call(F+'closing.result_post',{month:resultView.value.month},true);notice.value='Đã kết chuyển kết quả kinh doanh tháng '+resultView.value.month+': '+(r.profit>=0?'lãi ':'lỗ ')+vnd(Math.abs(r.profit))+' ('+r.voucher+').';resultView.value=null}
 catch(e){error.value=e.message}finally{saving.value=false}}
const costingView=ref(null)
async function previewCosting(m){await ensureLookups();await run(async()=>{costingView.value=await call(F+'costing.preview',{month:m})})}
async function postCosting(){saving.value=true
 try{const r=await call(F+'costing.run',{month:costingView.value.month},true)
  notice.value='Đã tính giá thành tháng '+costingView.value.month+': giá thành sản lượng thu '+vnd(r.absorbed)+', chênh lệch so với tạm tính '+vnd(r.adjustment)+(r.voucher?' ('+r.voucher+')':'')+'.';costingView.value=null}
 catch(e){error.value=e.message}finally{saving.value=false}}
async function closeMonth(m){if(!await ask('Khóa sổ tháng '+m.slice(5)+'/'+m.slice(0,4)+'? Sau khi khóa không ghi, sửa hay hủy chứng từ trong tháng được nữa.','Khóa sổ'))return
 await run(async()=>{await call(F+'posting.close_month',{month:m},true);settings.value=await call(F+'api.settings');notice.value='Đã khóa sổ tháng '+m.slice(5)+'/'+m.slice(0,4)+'.'})}
async function reopenMonth(m){const reason=await reasonPrompt.ask('Mở lại kỳ '+m,'Lý do mở lại kỳ (bắt buộc)');if(!reason)return
 await run(async()=>{await call(F+'posting.reopen_month',{month:m,reason},true);settings.value=await call(F+'api.settings');notice.value='Đã mở lại kỳ.'})}
function openWarehouse(name){location.href='/warehouse?doc='+encodeURIComponent(name)+'&doctype=Stock%20Entry'}
function downloadOpening(){location.href='/api/method/lotus_farm.finance.api.opening_template'}
async function readOpening(file){if(!file)return;saving.value=true
 try{const content=await new Promise((ok,fail)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=fail;r.readAsDataURL(file)});openingPreview.value=await call(F+'api.opening_preview',{content},true)}
 catch(e){error.value=e.message}finally{saving.value=false}}
async function commitOpening(){saving.value=true
 try{const r=await call(F+'api.opening_commit',{token:openingPreview.value.token},true);notice.value='Đã ghi số dư đầu kỳ '+r.voucher+' ('+vnd(r.amount)+').';openingPreview.value=null}
 catch(e){error.value=e.message}finally{saving.value=false}}

// Grid columns (shared DataTable). Money columns show whole đồng; action cells stop the row click.
const money=p=>p.value?num(p.value):''
const dateCol=(field,headerName)=>({field,headerName,minWidth:110,valueFormatter:p=>vnDate(p.value)})
const moneyCol=(field,headerName,extra={})=>({field,headerName,minWidth:130,type:'numericColumn',valueFormatter:p=>p.node?.rowPinned?num(p.value):money(p),...extra})
const receiptColumns=computed(()=>[...(overview.value?.can_post?[{field:'__pick',headerName:'Chọn',minWidth:70,maxWidth:80,sortable:false,hideOnMobile:true}]:[]),
 {field:'name',headerName:'Phiếu nhận',minWidth:170},{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:200,valueGetter:p=>p.data.supplier_name||p.data.supplier},dateCol('posting_date','Ngày'),moneyCol('to_bill','Chưa lập hóa đơn')])
const receiptRows=computed(()=>(pendingData.value?.receipts||[]).map(r=>({...r,__pick:picked.value.has(r.name)})))
const payrollPendingColumns=[{field:'month',headerName:'Tháng',minWidth:100,valueFormatter:p=>p.value?p.value.slice(5)+'/'+p.value.slice(0,4):''},{field:'name',headerName:'Kỳ công',minWidth:200},
 {field:'closed_at',headerName:'Đóng lúc',minWidth:120,valueFormatter:p=>vnDate(String(p.value||'').slice(0,10))},{field:'__view',headerName:'',minWidth:170,sortable:false}]
const harvestColumns=computed(()=>[{field:'name',headerName:'Lô thu hoạch',minWidth:170},{field:'farm',headerName:'Vườn',minWidth:120},dateCol('received_date','Ngày nhận'),
 {field:'released_raw_kg',headerName:'Kg',minWidth:100,type:'numericColumn',valueFormatter:p=>num(p.value,1)},{field:'reason',headerName:'Tình trạng',minWidth:240,flex:2},
 ...(overview.value?.can_post?[{field:'__receive',headerName:'',minWidth:120,sortable:false}]:[])])
const costingColumns=[{field:'label',headerName:'Lô',minWidth:170,flex:2,valueGetter:p=>p.node?.rowPinned?p.data.label:p.data.label+(p.data.lotus_farm_block&&p.data.lotus_farm?' · '+p.data.lotus_farm:'')},
 moneyCol('wip_open','Dở dang đầu kỳ'),moneyCol('cost_month','Chi phí tháng'),{field:'kg_harvested',headerName:'Kg thu',minWidth:100,type:'numericColumn',valueFormatter:p=>p.value?num(p.value,1):''},
 {field:'kg_remaining',headerName:'Kg dự thu còn lại',minWidth:130,type:'numericColumn',valueFormatter:p=>p.value?num(p.value,1):''},moneyCol('absorbed','Giá thành sản lượng'),
 {field:'cost_per_kg',headerName:'Giá thành / kg',minWidth:120,type:'numericColumn',valueFormatter:p=>p.value?num(p.value,2):''},moneyCol('provisional','Đã nhập kho (tạm tính)'),
 moneyCol('adjustment','Chênh lệch → 632'),moneyCol('wip_close','Dở dang cuối kỳ'),{field:'basis',headerName:'Cách tính',minWidth:220,flex:2}]
const costingRows=view=>(view?.rows||[]).map((r,i)=>({...r,__key:(r.lotus_farm||'')+'|'+(r.lotus_farm_block||'')+'|'+i}))
const costingTotals=view=>view?.totals?[{__key:'__total',label:'Tổng',...view.totals,cost_per_kg:view.totals.kg_harvested?view.totals.absorbed/view.totals.kg_harvested:null}]:[]
const customerColumns=computed(()=>[{field:'customer_name',headerName:'Khách hàng',minWidth:220,flex:2},{field:'tax_id',headerName:'MST',minWidth:120},moneyCol('invoiced','Đã xuất hóa đơn'),
 moneyCol('received','Đã thu'),moneyCol('owed','Còn phải thu'),moneyCol('overdue','Quá hạn'),{field:'credit_days',headerName:'Hạn nợ (ngày)',minWidth:110},
 ...(overview.value?.can_post?[{field:'__edit',headerName:'',minWidth:80,sortable:false},{field:'__receive',headerName:'',minWidth:110,sortable:false}]:[])])
const receivableColumns=[{field:'customer_name',headerName:'Khách hàng',minWidth:200},{field:'lotus_einvoice_no',headerName:'Số HĐ điện tử',minWidth:130,valueGetter:p=>[p.data.lotus_einvoice_series,p.data.lotus_einvoice_no].filter(Boolean).join(' ')||p.data.name},
 dateCol('posting_date','Ngày'),dateCol('due_date','Hạn thu'),moneyCol('grand_total','Tổng tiền'),moneyCol('outstanding_amount','Còn phải thu'),
 {field:'aging',headerName:'Tuổi nợ',minWidth:150,cellClass:p=>p.value&&p.value!=='Trong hạn'?'fin-cell-bad':''}]
const salesInvoiceColumns=[{field:'name',headerName:'Hóa đơn',minWidth:170},{field:'customer_name',headerName:'Khách hàng',minWidth:200},dateCol('posting_date','Ngày'),
 {field:'lotus_vat_code',headerName:'Thuế suất',minWidth:110,valueFormatter:p=>p.value&&p.value!=='KCT'?p.value+'%':'KCT'},moneyCol('net_total','Chưa thuế'),moneyCol('total_taxes_and_charges','Thuế GTGT'),moneyCol('grand_total','Tổng tiền'),moneyCol('outstanding_amount','Còn phải thu')]
const vatPurchaseColumns=[{field:'bill_no',headerName:'Số hóa đơn',minWidth:130},dateCol('bill_date','Ngày HĐ'),{field:'supplier_name',headerName:'Người bán',minWidth:200,flex:2},{field:'tax_id',headerName:'MST',minWidth:120},
 moneyCol('net','Chưa thuế'),{field:'code',headerName:'Thuế suất',minWidth:100,valueFormatter:p=>p.value&&p.value!=='KCT'?p.value+'%':'KCT'},moneyCol('tax','Thuế GTGT')]
const vatSalesColumns=[{field:'einvoice_no',headerName:'Số hóa đơn',minWidth:150,valueGetter:p=>[p.data.series,p.data.einvoice_no].filter(Boolean).join(' ')||p.data.name},dateCol('posting_date','Ngày'),
 {field:'customer_name',headerName:'Người mua',minWidth:200,flex:2},{field:'tax_id',headerName:'MST',minWidth:120},moneyCol('net','Doanh thu chưa thuế'),
 {field:'code',headerName:'Thuế suất',minWidth:100,valueFormatter:p=>p.value&&p.value!=='KCT'?p.value+'%':'KCT'},moneyCol('tax','Thuế GTGT')]
const vatCheckColumns=[{field:'label',headerName:'Đối chiếu',minWidth:320,flex:3},moneyCol('listing','Bảng kê',{valueFormatter:p=>num(p.value)}),moneyCol('ledger','Sổ kế toán',{valueFormatter:p=>num(p.value)}),
 {field:'ok',headerName:'Kết quả',minWidth:100,valueFormatter:p=>p.value?'Khớp':'Lệch',cellClass:p=>p.value?'fin-cell-ok':'fin-cell-bad'}]
const issueColumns=[{field:'name',headerName:'Phiếu xuất',minWidth:170},dateCol('posting_date','Ngày'),{field:'reason',headerName:'Lý do',minWidth:320,flex:3},moneyCol('amount','Giá trị')]
const lineColumns=[{field:'account',headerName:'Tài khoản',minWidth:260,flex:2,valueGetter:p=>p.data.account_label||p.data.account},moneyCol('debit','Nợ'),moneyCol('credit','Có'),{field:'party',headerName:'Đối tượng',minWidth:120},
 {field:'lotus_farm_block',headerName:'Vườn / lô',minWidth:130,valueGetter:p=>[p.data.lotus_farm,dimLabel('lotus_farm_block',p.data.lotus_farm_block)].filter(Boolean).join(' / ')},
 {field:'remarks',headerName:'Diễn giải',minWidth:180,valueGetter:p=>String(p.data.remarks||p.data.note||'').split('\n')[0]}]
const supplierColumns=computed(()=>[{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:220,flex:2},moneyCol('invoiced','Đã nhận hóa đơn'),moneyCol('paid','Đã trả'),moneyCol('owed','Còn nợ'),moneyCol('overdue','Quá hạn'),
 {field:'open_invoices',headerName:'Hóa đơn còn nợ',minWidth:110},...(overview.value?.can_post?[{field:'__pay',headerName:'',minWidth:140,sortable:false}]:[])])
const invoiceColumns=[{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:200},{field:'bill_no',headerName:'Số hóa đơn',minWidth:130,valueGetter:p=>p.data.bill_no||p.data.name},dateCol('bill_date','Ngày'),dateCol('due_date','Hạn trả'),
 moneyCol('grand_total','Tổng tiền'),moneyCol('outstanding_amount','Còn nợ'),moneyCol('paying','Đang chờ chi'),{field:'aging',headerName:'Tuổi nợ',minWidth:150,cellClass:p=>p.value&&p.value!=='Trong hạn'?'fin-cell-bad':''}]
const salaryReadyColumns=computed(()=>[{field:'month',headerName:'Tháng',minWidth:100,valueFormatter:p=>p.value?p.value.slice(5)+'/'+p.value.slice(0,4):''},moneyCol('net','Thực lĩnh'),
 moneyCol('advance','Đã tạm ứng'),moneyCol('to_pay','Còn phải chi'),{field:'payroll_voucher',headerName:'Bút toán lương',minWidth:170},
 {field:'__list',headerName:'',minWidth:190,sortable:false},
 ...(overview.value?.can_post?[{field:'__pay',headerName:'',minWidth:170,sortable:false}]:[])])
const voucherColumns=computed(()=>[{field:'name',headerName:'Phiếu',minWidth:170},{field:'kind',headerName:'Loại',minWidth:140},{field:'party_name',headerName:'Đối tượng',minWidth:180},dateCol('posting_date','Ngày'),moneyCol('amount','Số tiền'),
 {field:'state',headerName:'Trạng thái',minWidth:110,cellClass:p=>p.value==='Chờ ký'?'fin-cell-warn':''},
 {field:'signers',headerName:'Người ký',minWidth:260,flex:2,valueGetter:p=>(p.data.signing?.steps||[]).map(x=>x.title+': '+(x.name||'—')+' ('+(x.state||'—')+')').join(' · ')},
 {field:'__drop',headerName:'',minWidth:90,sortable:false},{field:'__reverse',headerName:'',minWidth:90,sortable:false}])
const tbColumns=[{field:'number',headerName:'Số TK',minWidth:90},{field:'name',headerName:'Tên tài khoản',minWidth:240,flex:2},moneyCol('opening_debit','Dư Nợ đầu kỳ'),moneyCol('opening_credit','Dư Có đầu kỳ'),
 moneyCol('debit','Phát sinh Nợ'),moneyCol('credit','Phát sinh Có'),moneyCol('closing_debit','Dư Nợ cuối kỳ'),moneyCol('closing_credit','Dư Có cuối kỳ')]
const tbTotals=computed(()=>reportData.value?.totals&&report.value==='trial_balance'?[{account:'__total',number:'',name:'Tổng cộng',...reportData.value.totals}]:[])
const ledgerColumns=[dateCol('posting_date','Ngày'),{field:'voucher_type',headerName:'Loại chứng từ',minWidth:130},{field:'voucher_no',headerName:'Số chứng từ',minWidth:170},{field:'party',headerName:'Đối tượng',minWidth:120},
 {field:'remarks',headerName:'Diễn giải',minWidth:200,flex:2,valueGetter:p=>String(p.data.remarks||'').split('\n')[0]},{field:'contra',headerName:'TK đối ứng',minWidth:110},
 moneyCol('debit','Nợ'),moneyCol('credit','Có'),moneyCol('balance','Số dư',{valueFormatter:p=>num(p.value)})]
const ledgerRows=computed(()=>(reportData.value?.lines||[]).map((l,i)=>({...l,__key:i})))
const groupLabel=computed(()=>({lotus_farm:'Vườn',lotus_farm_block:'Lô',lotus_crop_cycle:'Vụ',lotus_work_type:'Công việc'})[groupBy.value])
const costColumns=computed(()=>[{field:'label',headerName:groupLabel.value,minWidth:180,flex:2,valueGetter:p=>p.data.label+(groupBy.value!=='lotus_farm'&&p.data.farm&&!p.node?.rowPinned?' · '+p.data.farm:'')},
 moneyCol('materials','Vật tư'),moneyCol('labour','Nhân công'),moneyCol('crews','Khoán'),moneyCol('services','Dịch vụ'),moneyCol('total','Tổng'),...(groupBy.value==='lotus_farm_block'?[moneyCol('per_ha','Chi phí / ha')]:[])])
const costRows=computed(()=>(report.value==='costs'&&reportData.value?.rows||[]).map((r,i)=>({...r,__key:(r.dim||'-')+'|'+(r.farm||'')+'|'+i})))
const costTotals=computed(()=>report.value==='costs'&&reportData.value?.totals?[{__key:'__total',label:'Tổng',...reportData.value.totals}]:[])
const reconColumns=[{field:'label',headerName:'Nội dung',minWidth:320,flex:3},moneyCol('ledger','Sổ kế toán',{valueFormatter:p=>num(p.value)}),moneyCol('source','Nghiệp vụ',{valueFormatter:p=>num(p.value)}),
 {field:'difference',headerName:'Chênh lệch',minWidth:120,valueFormatter:p=>p.data.ok?'Khớp':num(p.value),cellClass:p=>p.data?.ok?'fin-cell-ok':'fin-cell-bad'}]
const transferColumns=[{field:'old',headerName:'Tài khoản cũ',minWidth:220,flex:2},{field:'new',headerName:'Chuyển sang',minWidth:240,flex:2},moneyCol('balance','Số dư',{valueFormatter:p=>num(p.value)})]
const openingColumns=[{field:'line',headerName:'Dòng',minWidth:70},{field:'number',headerName:'TK',minWidth:90},{field:'supplier',headerName:'Nhà cung cấp',minWidth:140},{field:'customer',headerName:'Khách hàng',minWidth:140},moneyCol('debit','Dư Nợ'),moneyCol('credit','Dư Có'),
 {field:'errors',headerName:'Lỗi',minWidth:260,flex:2,valueGetter:p=>(p.data.errors||[]).join('; '),cellClass:p=>p.value?'fin-cell-bad':''}]
const payrollLineColumns=[{field:'account',headerName:'Tài khoản',minWidth:260,flex:2},moneyCol('debit','Nợ'),moneyCol('credit','Có'),{field:'lotus_farm',headerName:'Vườn',minWidth:110},
 {field:'lotus_farm_block',headerName:'Lô',minWidth:90,valueGetter:p=>dimLabel('lotus_farm_block',p.data.lotus_farm_block)},{field:'lotus_work_type',headerName:'Công việc',minWidth:120},{field:'note',headerName:'Diễn giải',minWidth:140}]
const staff=ref(null)
const roleCells=[['chief','Lotus Chief Accountant'],['accountant','Lotus Accountant'],['auditor','Lotus Auditor']]
async function setRole(row,role,on){await run(async()=>{await call(F+'api.set_role',{user:row.user,role,on:on?1:0},true);staff.value=await call(F+'api.people');notice.value='Đã cập nhật vai trò của '+row.name+'.'})}
const peopleColumns=[{field:'name',headerName:'Nhân sự',minWidth:200,flex:2},{field:'designation',headerName:'Chức danh',minWidth:140},{field:'user',headerName:'Tài khoản',minWidth:200},
 {field:'chief',headerName:'Kế toán trưởng',minWidth:120,sortable:false},{field:'accountant',headerName:'Kế toán',minWidth:100,sortable:false},{field:'auditor',headerName:'Kiểm soát',minWidth:100,sortable:false},
 {field:'approver',headerName:'Ký duyệt chi',minWidth:110,valueFormatter:p=>p.value?'Có':'—'},{field:'employee',headerName:'Hồ sơ NV',minWidth:100,valueFormatter:p=>p.value?'Có':'Chưa gắn'}]
function newAdjLine(){return {account:'',debit:'',credit:'',party:'',lotus_farm_block:''}}
const adj=ref({posting_date:today,remark:'',lines:[newAdjLine(),newAdjLine()]}),adjErrors=ref([])
const adjDebit=computed(()=>adj.value.lines.reduce((t,l)=>t+Math.round(Number(l.debit||0)),0))
const adjCredit=computed(()=>adj.value.lines.reduce((t,l)=>t+Math.round(Number(l.credit||0)),0))
async function sendAdjustment(commit){saving.value=true;adjErrors.value=[]
 try{const r=await call(F+'api.adjustment',{lines:JSON.stringify(adj.value.lines.filter(l=>l.account)),posting_date:adj.value.posting_date,remark:adj.value.remark,commit},true)
  adjErrors.value=r.errors||[];if(commit&&r.voucher){notice.value='Đã ghi bút toán điều chỉnh '+r.voucher+' ('+vnd(r.total)+').';adj.value={posting_date:today,remark:'',lines:[newAdjLine(),newAdjLine()]}}
  else if(!adjErrors.value.length)notice.value='Bút toán hợp lệ, bấm Ghi sổ để ghi.'}
 catch(e){error.value=e.message}finally{saving.value=false}}
function openLedger(account){if(!account)return;ledgerAccount.value=account;report.value='ledger';range.value={from:today.slice(0,4)+'-01-01',to:today};go('reports')}
const reasonPrompt=useReasonDialog()
const tabItems=financeNavigation.map(({id,label})=>({id,label}))
function chooseReport(value){report.value=value;router.replace({query:{...route.query,report:value}})}
if(REPORTS.some(([id])=>id===route.query.report))report.value=String(route.query.report)
const vatChoices=computed(()=>(vatOptions.value?.rates||[]).map(r=>({value:r.code,label:r.label})))
function openReturn(v){returnReason.value='';returnOpen.value=v}
const allocationColumns=[{field:'bill',label:'Hóa đơn',width:'minmax(160px,1.6fr)'},{field:'due',label:'Hạn',width:'minmax(110px,1fr)'},{field:'owed',label:'Còn lại',width:'minmax(130px,1fr)'},{field:'amount',label:'Lần này',width:'minmax(150px,1.2fr)'}]
const statutoryColumns=[{field:'label',label:'Khoản',width:'minmax(200px,2fr)'},{field:'owed',label:'Còn phải nộp',width:'minmax(130px,1fr)'},{field:'pending',label:'Đang chờ ký',width:'minmax(130px,1fr)'},{field:'amount',label:'Nộp lần này',type:'money',props:{min:0},width:'minmax(150px,1.2fr)'}]
const saleColumns=computed(()=>[{field:'stock',label:'Hàng · kho',required:true,options:saleStock.value.map(s=>({value:stockKey(s),label:s.item_name+' · '+s.warehouse})),width:'minmax(220px,2.2fr)'},{field:'onhand',label:'Tồn',width:'minmax(110px,.8fr)'},
 {field:'qty',label:'Số lượng',type:'number',required:true,props:{min:0},width:'minmax(110px,.9fr)'},{field:'rate',label:'Đơn giá',type:'money',required:true,props:{min:0},width:'minmax(130px,1fr)'},
 {field:'batch_no',label:'Lô hàng (batch)',visible:row=>!!stockOf(row)?.has_batch_no,options:row=>(stockOf(row)?.batches||[]).map(b=>({value:b.name,label:b.name+' ('+num(b.qty,2)+')'})),searchable:false,width:'minmax(150px,1.1fr)'}])
const serviceColumns=computed(()=>[{field:'description',label:'Nội dung',required:true,props:{placeholder:'VD: Thuê máy cày lô A1'},width:'minmax(220px,2fr)'},{field:'amount',label:'Số tiền',type:'money',required:true,props:{min:0},width:'minmax(130px,1fr)'},
 {field:'cost',label:'Loại chi phí',options:[{value:'production',label:'Sản xuất (vào lô)'},{value:'admin',label:'Quản lý'}],searchable:false,props:{emptyOption:null},width:'minmax(150px,1fr)'},
 {field:'lotus_farm',label:'Vườn',options:(lookups.value?.farms||[]).map(f=>({value:f.name,label:f.farm_name||f.name})),width:'minmax(140px,1fr)'},
 {field:'lotus_farm_block',label:'Lô',options:row=>blocksOf(row.lotus_farm).map(b=>({value:b.name,label:b.block_code})),width:'minmax(110px,.8fr)'}])
const adjColumns=computed(()=>[{field:'account',label:'Tài khoản',required:true,options:(settings.value?.accounts||[]).map(a=>({value:a.name,label:accountLabel(a)})),width:'minmax(240px,2.4fr)'},{field:'debit',label:'Nợ',type:'money',props:{min:0},width:'minmax(130px,1fr)'},{field:'credit',label:'Có',type:'money',props:{min:0},width:'minmax(130px,1fr)'},
 {field:'party',label:'Đối tượng',props:{placeholder:'Mã NCC / KH'},width:'minmax(120px,1fr)'},{field:'lotus_farm_block',label:'Lô',options:(lookups.value?.blocks||[]).map(b=>({value:b.name,label:b.block_code})),width:'minmax(110px,.8fr)'}])
const keyed=list=>(list||[]).map((r,i)=>({...r,__key:i}))
const tiles=computed(()=>overview.value?.tiles||{})
const todos=computed(()=>{const c=overview.value?.pending_counts||{};return [
 ['receipts','phiếu nhận hàng chưa có hóa đơn','pending'],['payroll','bảng lương đã ký chưa ghi sổ','pending'],['issues','dòng xuất kho chưa gắn lô','pending'],
 ['harvests','lô thu hoạch chưa nhập kho','pending'],['vouchers','phiếu chi đang chờ ký','cash']].map(([key,label,tab])=>({count:Number(c[key]||0),label,tab}))})
const costChart=computed(()=>(report.value==='costs'&&reportData.value?.rows||[]).slice(0,12))
watch(()=>route.query.tab,load)
watch(report,()=>run(loadReport))
onMounted(load)
useNoticeToast(notice)
</script>

<template>
<section class="fin lotus-ui">
 <header class="fin-head">
  <div class="fin-title"><h2>{{embedded?financeViewTitle(tab):'Tài chính – Kế toán'}}</h2><span v-if="overview">{{overview.company}} · {{overview.coa_version?'Hệ thống tài khoản '+overview.coa_version:'Chưa áp dụng hệ thống tài khoản Thông tư 99'}}</span></div>
  <span class="land-spacer"></span>
  <span v-if="overview" class="fin-state" :class="{on:overview.enabled}">{{overview.enabled?'Đang ghi sổ từ '+vnDate(overview.cutover_date):'Ghi sổ từ Lotus đang tắt'}}</span>
 </header>
 <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
 <WorkspaceTabs v-if="ledgerUser&&!embedded" :items="tabItems" :model-value="tab" label="Tài chính – Kế toán" @update:model-value="go"/>

 <!-- Approver without ledger access -->
 <FormSection v-if="tab==='sign'" title="Phiếu chi chờ bạn ký">
  <p v-if="!mine.length&&!busy" class="lotus-form-note">Không có phiếu chi nào đang chờ bạn ký.</p>
  <article v-for="v in mine" :key="v.name" class="fin-voucher">
   <header><b>{{v.kind}} · {{v.party_name}}</b><strong>{{vnd(v.amount)}}</strong></header>
   <small>{{v.name}} · ngày {{vnDate(v.posting_date)}}{{v.reference?' · '+v.reference:''}}</small>
   <ul><li v-for="l in v.lines" :key="l.label">{{l.label}}: {{vnd(l.amount)}}</li></ul>
   <ol class="fin-steps"><li v-for="s in v.signing.steps" :key="s.key" :class="s.state==='Đã ký'?'done':s.state==='Chờ ký'?'now':''">{{s.title}}: {{s.name||'—'}} <small>{{s.state}}</small></li></ol>
   <div class="fin-actions"><UiButton v-if="v.signing.can_return" variant="outline" :disabled="saving" @click="openReturn(v)">Trả lại</UiButton><UiButton v-if="v.signing.can_sign" :disabled="saving" @click="sign(v)">Ký duyệt chi</UiButton></div>
  </article>
 </FormSection>

 <template v-else-if="tab==='overview'&&overview">
  <p v-if="!overview.enabled" class="notice" role="status">Ghi sổ kế toán từ Lotus đang tắt. Kế toán trưởng vào <UiButton variant="link" class="fin-inline-link" @click="go('settings')">Thiết lập</UiButton> để áp dụng hệ thống tài khoản Thông tư 99, chọn tài khoản, ngày bắt đầu ghi sổ rồi bật.</p>
  <p v-for="e in overview.mapping_errors.slice(0,4)" :key="e" class="land-warn">{{e}}</p>
  <WorkspaceSummaryStrip :items="[{label:'Tiền mặt',value:vnd(tiles.cash)},{label:'Tiền gửi ngân hàng',value:vnd(tiles.bank)},{label:'Phải trả nhà cung cấp',value:vnd(tiles.payable_supplier)},{label:'Hàng về chưa có hóa đơn',value:vnd(tiles.received_not_billed)},{label:'Phải trả người lao động',value:vnd(tiles.payable_employee)},{label:'Bảo hiểm phải nộp',value:vnd(tiles.insurance)},{label:'Chi phí tháng này',value:vnd(tiles.month_cost)}]"/>
  <FormSection title="Việc cần làm">
   <ul class="fin-todo">
    <li v-for="t in todos" :key="t.label"><UiButton variant="ghost" class="fin-todo__item" :class="{'is-zero':!t.count}" @click="go(t.tab)"><b class="fin-todo__count">{{t.count}}</b><span>{{t.label}}</span><LotusIcon name="chevron"/></UiButton></li>
   </ul>
  </FormSection>
 </template>

 <template v-else-if="tab==='pending'&&pendingData">
  <FormSection title="Phiếu nhận hàng chưa có hóa đơn">
   <template #actions><UiButton v-if="overview?.can_post" :disabled="!picked.size||pickedSupplier.length!==1" :title="pickedSupplier.length>1?'Chọn phiếu của cùng một nhà cung cấp':''" @click="invoice={bill_no:'',bill_date:today,due_date:'',vat_code:'KCT'};ensureVat();invoiceOpen=true">Lập hóa đơn ({{picked.size}})</UiButton></template>
   <DataTable :rows="receiptRows" :columns="receiptColumns" row-key="name" storage-key="fin-receipts" interactive empty="Mọi phiếu nhận hàng đã có hóa đơn." @open="r=>togglePick(r.name)">
    <template #cell-__pick="{row}"><Checkbox :model-value="picked.has(row.name)" :aria-label="'Chọn '+row.name" @click.stop @update:model-value="togglePick(row.name)"/></template>
   </DataTable>
  </FormSection>
  <FormSection title="Bảng lương đã ký, chưa ghi sổ">
   <DataTable :rows="pendingData.payroll" :columns="payrollPendingColumns" row-key="name" storage-key="fin-payroll-pending" interactive empty="Không có bảng lương chờ ghi sổ." @open="r=>previewPayroll(r.name)">
    <template #cell-__view="{row}"><UiButton size="sm" variant="outline" @click.stop="previewPayroll(row.name)">Xem trước bút toán</UiButton></template>
   </DataTable>
  </FormSection>
  <FormSection title="Xuất kho chưa gắn lô" description="Chi phí của các dòng này chưa vào lô nào. Sửa ô &quot;Khu vực / lô sử dụng&quot; thành mã lô trong danh sách khi lập phiếu.">
   <DataTable :rows="keyed(pendingData.issues)" :columns="issueColumns" row-key="__key" storage-key="fin-issues" interactive empty="Mọi dòng xuất kho đã gắn lô." @open="r=>openWarehouse(r.name)"/>
  </FormSection>
  <FormSection title="Lô thu hoạch chưa nhập kho" description="Nhập kho theo giá thành tạm tính / kg (giá thành thực tế tháng trước của lô, chưa có thì giá kế hoạch ở Thiết lập): Nợ 155 / Có 154. Cuối tháng tính lại giá thành thực tế.">
   <DataTable :rows="pendingData.harvests||[]" :columns="harvestColumns" row-key="name" storage-key="fin-harvests" empty="Mọi lô thu hoạch đã nhập kho.">
    <template #cell-__receive="{row}"><UiButton v-if="row.raw_item&&row.raw_warehouse&&row.raw_batch" size="sm" variant="outline" @click.stop="receiveHarvest(row)">Nhập kho</UiButton></template>
   </DataTable>
  </FormSection>
 </template>

 <ListPage v-else-if="tab==='journal'" title="Nhật ký kế toán" :rows="[]" :columns="[]" :searchable="false" :loading="busy" @refresh="load" class="fin-journal">
  <template #filters><DateRangePicker v-model:from="range.from" v-model:to="range.to" @change="load"/><span class="lotus-form-note">{{journalRows.length}} chứng từ</span></template>
  <template #before>
   <details v-for="v in journalRows" :key="v.voucher_no" class="fin-entry"><summary><span>{{vnDate(v.posting_date)}}</span><b>{{v.voucher_no}}</b><span>{{v.voucher_label||v.voucher_type}} · {{v.description}}</span><strong>{{vnd(v.amount)}}</strong></summary>
    <DataTable :rows="keyed(v.lines)" :columns="lineColumns" row-key="__key" storage-key="fin-journal-lines"/></details>
   <p v-if="!journalRows.length&&!busy" class="lotus-form-note">Không có chứng từ trong khoảng ngày này.</p>
  </template>
 </ListPage>

 <template v-else-if="tab==='sales'&&salesData">
  <WorkspaceSummaryStrip :items="[{label:'Sổ cái 131',value:vnd(salesData.gl_total)}]"/>
  <FormSection title="Khách hàng">
   <template #actions><template v-if="overview?.can_post"><UiButton @click="openSale"><LotusIcon name="plus"/>Lập hóa đơn bán</UiButton><UiButton variant="outline" @click="openCustomer()">Thêm khách hàng</UiButton></template></template>
   <DataTable :rows="salesData.customers" :columns="customerColumns" row-key="customer" storage-key="fin-customers" empty="Chưa có khách hàng. Bấm Thêm khách hàng.">
    <template #cell-__edit="{row}"><UiButton size="sm" variant="outline" @click.stop="openCustomer(row)">Sửa</UiButton></template>
    <template #cell-__receive="{row}"><UiButton v-if="row.open_invoices>0" size="sm" variant="outline" @click.stop="openReceipt(row)">Thu tiền</UiButton></template>
   </DataTable>
  </FormSection>
  <FormSection title="Hóa đơn còn phải thu"><DataTable :rows="salesData.invoices" :columns="receivableColumns" row-key="name" storage-key="fin-receivables" empty="Không có hóa đơn còn phải thu."/></FormSection>
  <FormSection title="Hóa đơn bán gần đây" description="Hóa đơn bán xuất kho luôn: Nợ 632 / Có 155 theo giá trị tồn kho, Nợ 131 / Có 511 (và 33311 nếu có thuế). Chuối của vườn tự trồng bán ra không chịu thuế GTGT (KCT).">
   <DataTable :rows="salesData.recent" :columns="salesInvoiceColumns" row-key="name" storage-key="fin-sales-invoices" empty="Chưa có hóa đơn bán."/>
  </FormSection>
 </template>

 <template v-else-if="tab==='payables'&&payData">
  <WorkspaceSummaryStrip :items="[{label:'Sổ cái 331',value:vnd(payData.gl_total)}]"/>
  <FormSection title="Theo nhà cung cấp">
   <template #actions><UiButton v-if="overview?.can_post" @click="openService"><LotusIcon name="plus"/>Hóa đơn dịch vụ / chi phí</UiButton><UiButton variant="outline" @click="exportReport('payables')"><LotusIcon name="download"/>Xuất Excel</UiButton></template>
   <DataTable :rows="payData.suppliers" :columns="supplierColumns" row-key="supplier" storage-key="fin-suppliers" empty="Chưa có công nợ nhà cung cấp.">
    <template #cell-__pay="{row}"><UiButton v-if="row.open_invoices>0" size="sm" variant="outline" @click.stop="openPay(row.supplier)">Lập phiếu chi</UiButton></template>
   </DataTable>
  </FormSection>
  <FormSection title="Hóa đơn còn nợ"><DataTable :rows="payData.invoices" :columns="invoiceColumns" row-key="name" storage-key="fin-open-invoices" empty="Không có hóa đơn còn nợ."/></FormSection>
 </template>

 <template v-else-if="tab==='cash'&&cash">
  <div v-if="overview?.can_post" class="fin-actions"><UiButton variant="outline" @click="openAdvance">Tạm ứng lương</UiButton><UiButton variant="outline" @click="openStatutory">Nộp BH, KPCĐ, thuế TNCN</UiButton></div>
  <FormSection v-if="mine.length" title="Chờ bạn ký">
   <article v-for="v in mine" :key="v.name" class="fin-voucher"><header><b>{{v.kind}} · {{v.party_name}}</b><strong>{{vnd(v.amount)}}</strong></header><small>{{v.name}} · {{vnDate(v.posting_date)}}</small>
    <div class="fin-actions"><UiButton v-if="v.signing.can_return" variant="outline" :disabled="saving" @click="openReturn(v)">Trả lại</UiButton><UiButton v-if="v.signing.can_sign" :disabled="saving" @click="sign(v)">Ký</UiButton></div></article>
  </FormSection>
  <FormSection v-if="cash.salary_ready.length" title="Lương đã ghi sổ, chưa chi">
   <DataTable :rows="cash.salary_ready" :columns="salaryReadyColumns" row-key="period" storage-key="fin-salary-ready">
    <template #cell-__list="{row}"><UiButton size="sm" variant="outline" @click.stop="exportTransfer(row.period)">Danh sách chuyển khoản</UiButton></template>
    <template #cell-__pay="{row}"><UiButton size="sm" variant="outline" @click.stop="openSalary(row)">Lập phiếu chi lương</UiButton></template>
   </DataTable>
  </FormSection>
  <FormSection title="Phiếu chi">
   <DataTable :rows="cash.vouchers" :columns="voucherColumns" row-key="name" storage-key="fin-vouchers" empty="Chưa có phiếu chi nào lập từ Lotus.">
    <template #cell-__drop="{row}"><UiButton v-if="row.state==='Chờ ký'&&overview?.can_post" size="sm" variant="outline" @click.stop="dropDraft(row)">Hủy</UiButton></template>
    <template #cell-__reverse="{row}"><UiButton v-if="row.state==='Đã chi'&&overview?.is_chief" size="sm" variant="outline" @click.stop="reverse(row.posting,row.name)">Đảo</UiButton></template>
   </DataTable>
  </FormSection>
 </template>

 <template v-else-if="tab==='reports'">
  <div class="fin-report-toolbar">
   <div class="fin-report-toolbar__filters">
    <LotusField :model-value="report" aria-label="Báo cáo" :options="REPORTS.map(([value,label])=>({value,label}))" :searchable="false" :empty-option="null" class="fin-wide" @update:model-value="chooseReport"/>
    <DateRangePicker v-model:from="range.from" v-model:to="range.to"/>
    <LotusField v-if="report==='costs'" v-model="groupBy" aria-label="Nhóm theo" :options="[{value:'lotus_farm',label:'Theo vườn'},{value:'lotus_farm_block',label:'Theo lô'},{value:'lotus_crop_cycle',label:'Theo vụ'},{value:'lotus_work_type',label:'Theo công việc'}]" :searchable="false" :empty-option="null"/>
    <LotusField v-if="report==='ledger'" v-model="ledgerAccount" aria-label="Tài khoản" :options="(lookups?.accounts||[]).map(a=>({value:a.name,label:a.name}))" placeholder="Chọn tài khoản…" class="fin-wide"/>
    <LotusField v-if="report==='ledger'" v-model="ledgerParty" aria-label="Đối tượng" placeholder="Mã đối tượng (tùy chọn)"/>
    <LotusField v-if="report==='party'" v-model="partyAccount" aria-label="Tài khoản công nợ" :options="(lookups?.accounts||[]).filter(a=>/^(131|331|334|141|1388|3388)/.test(a.account_number||'')).map(a=>({value:a.name,label:a.name}))" placeholder="Chọn tài khoản công nợ…" class="fin-wide"/>
    <LotusField v-if="report==='bank'" aria-label="Sao kê ngân hàng (.xlsx)" type="file" accept=".xlsx" :disabled="saving" @update:model-value="readStatement"/>
   </div>
   <div class="fin-report-toolbar__actions">
    <UiButton v-if="report!=='bank'" variant="outline" @click="run(loadReport)">Xem</UiButton>
    <UiButton v-if="!['reconciliation','bank','vat','costing'].includes(report)" variant="outline" :disabled="(report==='ledger'&&!ledgerAccount)||(report==='party'&&!partyAccount)" @click="exportReport(report)"><LotusIcon name="download"/>Xuất Excel</UiButton>
    <UiButton v-if="report==='vat'&&reportData?.summary" variant="outline" @click="exportVat"><LotusIcon name="download"/>Xuất bảng kê Excel</UiButton>
   </div>
  </div>
  <template v-if="STATEMENTS.includes(report)&&reportData?.rows">
   <FormSection :title="reportData.title+' · Mẫu '+reportData.form+' · '+(report==='b01'?'tại ngày '+vnDate(reportData.on_date):'từ '+vnDate(reportData.from_date)+' đến '+vnDate(reportData.to_date))" :description="report==='b01'?'Ngày báo cáo lấy theo ngày &quot;Đến&quot;; số đầu năm là số dư ngày 31/12 năm trước.':report==='b02'?'Kỳ theo ô Từ – Đến; cột so sánh là cùng kỳ năm trước. Không gồm bút toán kết chuyển 911.':'Phương pháp gián tiếp, kỳ theo ô Từ – Đến.'">
    <template #actions><span :class="reportData.checks.every(c=>c.ok)?'fin-ok':'land-bad'">{{reportData.checks.every(c=>c.ok)?'Cân, khớp sổ':'Có chênh lệch'}}</span></template>
    <div class="fin-statement"><DataTable :rows="reportData.rows" :columns="statementColumns" :totals="false" row-key="code" :storage-key="'fin-'+report" empty="Không có số liệu."/></div>
    <DataTable :rows="reportData.checks" :columns="checkColumns" :totals="false" row-key="label" :storage-key="'fin-'+report+'-checks'"/>
    <p v-for="u in reportData.uncovered||[]" :key="'u'+u.number+u.party" class="land-warn">TK {{u.number}} {{u.name}}{{u.party?' · '+u.party:''}} ({{num(u.net)}}) chưa thuộc chỉ tiêu nào{{report==='b03'?' — đã đưa vào dòng 16':''}}.</p>
    <p v-for="d in reportData.double||[]" :key="'d'+d.number" class="land-bad">TK {{d.number}} được lấy ở nhiều chỉ tiêu: {{d.lines.join(', ')}}.</p>
    <details><summary>Nguồn biểu mẫu và cách lấy số</summary><p class="lotus-form-note">{{reportData.source}}</p><ul class="fin-list"><li v-for="n in reportData.notes" :key="n">{{n}}</li></ul></details>
   </FormSection>
  </template>
  <FormSection v-else-if="report==='general_journal'&&reportData?.rows" :title="'Sổ nhật ký chung '+vnDate(reportData.from_date)+' – '+vnDate(reportData.to_date)">
   <template #actions><span :class="Math.round(reportData.debit)===Math.round(reportData.credit)?'fin-ok':'land-bad'">Nợ {{vnd(reportData.debit)}} · Có {{vnd(reportData.credit)}}</span></template>
   <DataTable :rows="reportData.rows" :columns="journalBookColumns" row-key="line" storage-key="fin-general-journal" empty="Không có phát sinh trong kỳ."/>
  </FormSection>
  <FormSection v-else-if="report==='party'" :title="reportData?'Bảng tổng hợp chi tiết công nợ '+reportData.account:'Công nợ theo đối tượng'" :description="reportData?'Bấm một đối tượng để xem sổ chi tiết công nợ của đối tượng đó.':'Chọn tài khoản công nợ (131 phải thu khách hàng, 331 phải trả người bán, 334, 141…).'">
   <DataTable v-if="reportData" :rows="reportData.rows" :columns="partyColumns" :pinned-bottom-rows="partyTotals" row-key="party" storage-key="fin-party" interactive empty="Không có công nợ trong kỳ." @open="r=>{ledgerAccount=reportData.account;ledgerParty=r.party;chooseReport('ledger')}"/>
  </FormSection>
  <FormSection v-else-if="report==='stock'&&reportData?.rows" :title="'Tổng hợp nhập – xuất – tồn '+vnDate(reportData.from_date)+' – '+vnDate(reportData.to_date)" :description="'Tồn cuối kỳ '+vnd(reportData.totals.closing_value)+' · nhập '+vnd(reportData.totals.in_value)+' · xuất '+vnd(reportData.totals.out_value)">
   <DataTable :rows="keyed(reportData.rows)" :columns="stockColumns" row-key="__key" storage-key="fin-stock-summary" empty="Không có nhập xuất trong kỳ."/>
  </FormSection>
  <FormSection v-else-if="report==='bank'" :title="reportData?'Đối chiếu sao kê '+vnDate(reportData.from_date)+' – '+vnDate(reportData.to_date):'Đối chiếu ngân hàng'" :description="reportData?'Dòng chỉ có trên sao kê (phí ngân hàng, lãi tiền gửi, tiền khách chuyển chưa ghi) cần lập chứng từ; dòng chỉ có trên sổ là giao dịch ngân hàng chưa thực hiện hoặc ghi sai ngày, số tiền.':'Tải file sao kê Excel của ngân hàng (cột Ngày, Ghi nợ / Ghi có hoặc Số tiền, Số tham chiếu, Nội dung). Lotus so với sổ tiền gửi 112 theo số tiền, tham chiếu và ngày (± 3 ngày).'">
   <template v-if="reportData" #actions><span>{{reportData.matched.length}} khớp · {{reportData.statement_only.length}} chỉ có trên sao kê · {{reportData.ledger_only.length}} chỉ có trên sổ</span></template>
   <DataTable v-if="reportData" :rows="bankRows" :columns="bankColumns" row-key="__key" storage-key="fin-bank-match"/>
  </FormSection>
  <FormSection v-else-if="report==='trial_balance'&&reportData?.rows" :title="'Bảng cân đối phát sinh '+vnDate(reportData.from_date)+' – '+vnDate(reportData.to_date)" description="Bấm một tài khoản để xem sổ chi tiết.">
   <template #actions><span :class="reportData.balanced?'fin-ok':'land-bad'">{{reportData.balanced?'Cân Nợ = Có':'Lệch Nợ / Có'}}</span></template>
   <DataTable :rows="reportData.rows" :columns="tbColumns" :pinned-bottom-rows="tbTotals" row-key="account" storage-key="fin-trial-balance" interactive empty="Không có phát sinh trong kỳ." @open="r=>{ledgerAccount=r.account;chooseReport('ledger')}"/>
  </FormSection>
  <FormSection v-else-if="report==='ledger'" :title="reportData?(/^111/.test(reportData.label)?'Sổ quỹ tiền mặt':/^112/.test(reportData.label)?'Sổ tiền gửi ngân hàng':'Sổ cái')+' · '+reportData.label+(reportData.party?' · '+reportData.party:''):'Sổ cái / sổ quỹ / tiền gửi'" :description="reportData?'Số dư đầu kỳ '+vnd(reportData.opening)+' · phát sinh Nợ '+vnd(reportData.debit)+' · phát sinh Có '+vnd(reportData.credit)+' · cuối kỳ '+vnd(reportData.closing):'Chọn một tài khoản để xem sổ chi tiết.'">
   <DataTable v-if="reportData" :rows="ledgerRows" :columns="ledgerColumns" row-key="__key" storage-key="fin-ledger" empty="Không có phát sinh trong kỳ."/>
  </FormSection>
  <template v-else-if="report==='costs'&&reportData?.rows">
   <LotusChart v-if="costChart.length" :title="'Chi phí sản xuất theo '+(groupBy==='lotus_farm'?'vườn':groupBy==='lotus_farm_block'?'lô':groupBy==='lotus_crop_cycle'?'vụ':'công việc')+' (10 lớn nhất)'" kind="hbar"
    :categories="costChart.map(r=>r.label)" :series="[{name:'Vật tư',data:costChart.map(r=>r.materials)},{name:'Nhân công',data:costChart.map(r=>Number(r.labour)+Number(r.crews))},{name:'Dịch vụ',data:costChart.map(r=>r.services)}]" unit="đ" :height="320"/>
   <FormSection><DataTable :rows="costRows" :columns="costColumns" :pinned-bottom-rows="costTotals" row-key="__key" storage-key="fin-costs" empty="Chưa có chi phí sản xuất trong khoảng ngày này."/></FormSection>
  </template>
  <FormSection v-else-if="report==='costing'&&reportData?.rows" :title="'Giá thành chuối tháng '+reportData.month.slice(5)+'/'+reportData.month.slice(0,4)" description="Tháng lấy theo ngày &quot;Đến&quot;. Bảng xem trước tính lại từ sổ cái; tháng đã tính thì bảng đã lưu nằm trong lịch sử bên dưới.">
   <template #actions><span :class="reportData.posted?'fin-ok':'land-warn'">{{reportData.posted?'Đã tính giá thành':reportData.closed?'Chưa tính giá thành':'Chưa kết chuyển chi phí'}}</span></template>
   <DataTable :rows="costingRows(reportData)" :columns="costingColumns" :pinned-bottom-rows="costingTotals(reportData)" row-key="__key" storage-key="fin-costing" empty="Tháng này không có chi phí dở dang hay sản lượng thu hoạch."/>
   <details v-if="reportData.runs?.length"><summary>Các tháng đã tính giá thành</summary><ul class="fin-list"><li v-for="r in reportData.runs" :key="r.name">{{r.month.slice(5)}}/{{r.month.slice(0,4)}} · {{num(r.kg_harvested,1)}} kg · giá thành {{vnd(r.absorbed)}} · chênh lệch {{vnd(r.adjustment)}} · {{r.state==='Posted'?'đang dùng':'đã đảo'}}{{r.voucher?' · '+r.voucher:''}}</li></ul></details>
  </FormSection>
  <template v-else-if="report==='vat'&&reportData?.summary">
   <FormSection :title="'Thuế GTGT tháng '+reportData.month.slice(5)+'/'+reportData.month.slice(0,4)" description="Tháng lấy theo ngày &quot;Đến&quot;. Số liệu tham khảo để lập tờ khai 01/GTGT trên HTKK / eTax (chưa trừ số còn được khấu trừ của kỳ trước).">
    <WorkspaceSummaryStrip :items="[{label:'Thuế GTGT đầu vào',value:vnd(reportData.summary.input_tax)},{label:'Thuế GTGT đầu ra',value:vnd(reportData.summary.output_tax)},{label:reportData.summary.payable>=0?'Phải nộp':'Còn được khấu trừ',value:vnd(Math.abs(reportData.summary.payable))},{label:'Doanh thu không chịu thuế',value:vnd(reportData.summary.exempt_sales)}]"/>
    <DataTable :rows="reportData.checks" :columns="vatCheckColumns" :totals="false" row-key="label" storage-key="fin-vat-checks"/>
   </FormSection>
   <FormSection title="Bảng kê hóa đơn mua vào"><DataTable :rows="reportData.purchases" :columns="vatPurchaseColumns" row-key="name" storage-key="fin-vat-purchases" empty="Không có hóa đơn mua trong tháng."/></FormSection>
   <FormSection title="Bảng kê hóa đơn bán ra"><DataTable :rows="reportData.sales" :columns="vatSalesColumns" row-key="name" storage-key="fin-vat-sales" empty="Không có hóa đơn bán trong tháng."/></FormSection>
  </template>
  <FormSection v-else-if="report==='reconciliation'&&reportData?.checks" :title="'Đối chiếu sổ kế toán với nghiệp vụ Lotus ('+vnDate(reportData.on_date)+')'">
   <DataTable :rows="reportData.checks" :columns="reconColumns" :totals="false" row-key="label" storage-key="fin-reconciliation"/>
  </FormSection>
 </template>

 <FinancePlanning v-else-if="tab==='planning'" @notice="notice=$event"/>
 <FinanceAssets v-else-if="tab==='assets'" :view="String(route.query.asset_view||'assets')" @view-change="router.replace({query:{...route.query,asset_view:$event}})" @go-settings="go('settings')" @notice="notice=$event"/>
 <FinanceGuide v-else-if="tab==='guide'" @go="go"/>

 <template v-else-if="tab==='settings'&&settings">
  <FormSection title="Hệ thống tài khoản" :description="settings.coa_version?'Đã áp dụng '+settings.coa_version+' lúc '+vnDate(settings.coa_applied_at.slice(0,10))+' ('+settings.coa_applied_by+').':'Chưa áp dụng. Xem trước để kiểm tra danh mục tài khoản Thông tư 99, tài khoản kho và bút toán chuyển số dư từ hệ thống tài khoản cũ.'">
   <template #actions><UiButton variant="outline" @click="previewCoa">Xem trước áp dụng Thông tư 99</UiButton><UiButton v-if="settings.is_chief" variant="outline" @click="accountImportOpen=true">Nhập tài khoản Excel</UiButton></template>
   <FinanceMasterImport v-model="accountImportOpen" kind="accounts" @imported="importedAccounts"/>
   <template v-if="coa">
    <p>{{coa.name}} — thêm <b>{{coa.add.length}}</b>, sửa tên / loại <b>{{coa.update.length}}</b>, xóa <b>{{coa.retire.filter(r=>r.action==='delete').length}}</b>, ngừng dùng <b>{{coa.retire.filter(r=>r.action==='disable').length}}</b> tài khoản (tài khoản đã có bút toán không xóa được, chỉ ngừng dùng).</p>
    <details v-if="coa.update.length"><summary>Tài khoản đổi tên theo Thông tư 99</summary><ul class="fin-list"><li v-for="u in coa.update" :key="u.account">{{u.number}}: {{u.old_name}} → <b>{{u.name}}</b></li></ul></details>
    <details v-if="coa.retire.length"><summary>Tài khoản không có trong Thông tư 99</summary><ul class="fin-list"><li v-for="r in coa.retire" :key="r.account">{{r.label}} — {{r.action==='delete'?'xóa':'ngừng dùng'}}</li></ul></details><p class="lotus-form-note">{{coa.note}}</p>
    <p v-for="e in coa.errors" :key="e" class="land-bad">{{e}}</p>
    <DataTable :rows="coa.transfer" :columns="transferColumns" row-key="old" storage-key="fin-coa-transfer" empty="Không có số dư cần chuyển."/>
    <p class="lotus-form-note">Kho: {{coa.warehouses.map(w=>w.warehouse).join(', ')}} → {{coa.warehouses[0]?.account}}</p>
    <div class="fin-actions fin-actions--end"><UiButton :disabled="saving||!!coa.errors.length||!settings.is_chief" @click="applyCoa">Áp dụng Thông tư 99</UiButton></div>
   </template>
  </FormSection>
  <FormSection title="Tài khoản theo nghiệp vụ và bật ghi sổ">
   <p v-for="e in settings.errors" :key="e" class="land-warn">{{e}}</p>
   <FormGrid :columns="3">
    <LotusField v-for="k in settings.keys" :key="k.key" v-model="form.mapping[k.key]" :label="k.label" :options="accountsFor(k.key).map(a=>({value:a.name,label:accountLabel(a)}))" empty-option="Chưa chọn" :disabled="!settings.is_chief"/>
    <LotusField v-model="form.cutover_date" label="Ngày bắt đầu ghi sổ (cutover)" type="date" :disabled="!settings.is_chief"/>
    <LotusField v-model="form.harvest_standard_cost" label="Giá thành kế hoạch chuối thu hoạch (đ / kg)" type="money" min="0" :disabled="!settings.is_chief" placeholder="Dùng khi lô chưa có giá thành thực tế"/>
    <LotusField v-model="form.minimum_wage_region" label="Vùng lương tối thiểu (trần BHTN)" :options="['I','II','III','IV'].map(v=>({value:v,label:'Vùng '+v}))" :searchable="false" empty-option="Chưa chọn (không áp trần BHTN)" :disabled="!settings.is_chief"/>
    <LotusField v-model="form.enabled" label="Bật ghi sổ kế toán từ Lotus" type="checkbox" :disabled="!settings.is_chief"/>
   </FormGrid>
   <div v-if="settings.is_chief" class="fin-actions fin-actions--end"><UiButton :disabled="saving" @click="saveSettings">Lưu cấu hình</UiButton></div>
  </FormSection>
  <FormSection title="Đóng tháng — danh sách kiểm tra" :description="checklist?'Đã xong '+checklist.done+' / '+checklist.total+' bước. Lotus tự kiểm tra từng bước từ sổ kế toán; làm theo thứ tự từ trên xuống.':''">
   <template #actions><LotusField v-model="checklistMonth" aria-label="Tháng kiểm tra" type="month"/></template>
   <ol v-if="checklist" class="fin-checklist"><li v-for="s in checklist.steps" :key="s.key" :class="'is-'+s.state">
    <span class="fin-checklist__mark" :aria-label="s.state==='done'?'Đã xong':s.state==='na'?'Không áp dụng':'Chưa xong'"><LotusIcon :name="s.state==='done'?'tick':s.state==='na'?'more':'alert'"/></span>
    <span><b>{{s.label}}</b><small v-if="s.detail"> — {{s.detail}}</small><small v-if="s.state==='na'"> — không áp dụng tháng này</small></span>
    <UiButton v-if="s.state==='todo'&&s.go&&s.go!=='settings'" size="sm" variant="ghost" @click="go(s.go)">Mở</UiButton></li></ol>
  </FormSection>
  <FormSection title="Kết chuyển và khóa sổ theo tháng">
   <template #actions><LotusField v-model="year" aria-label="Năm" :options="[Number(today.slice(0,4))-1,Number(today.slice(0,4)),Number(today.slice(0,4))+1].map(y=>({value:y,label:'Năm '+y}))" :searchable="false" :empty-option="null" @update:model-value="year=Number($event)"/></template>
   <p class="land-warn">Thứ tự cuối tháng: ghi sổ lương → kết chuyển chi phí (Kết chuyển CP) → tính giá thành (Giá thành) → kết chuyển kết quả kinh doanh (KQKD 911) → kiểm tra Đối chiếu → Khóa. Đã khóa thì không làm các bước trên được nữa.</p>
   <div class="fin-months"><div v-for="m in months" :key="m" class="fin-month" :class="{closed:periodOf(m)?.closed}"><b>{{m.slice(5)}}/{{m.slice(0,4)}}</b><small>{{periodOf(m)?.closed?'Đã khóa':'Đang mở'}}</small>
    <UiButton size="sm" variant="ghost" @click="previewClosing(m)">Kết chuyển CP</UiButton><UiButton size="sm" variant="ghost" @click="previewCosting(m)">Giá thành</UiButton><UiButton size="sm" variant="ghost" @click="previewResult(m)">KQKD 911</UiButton>
    <template v-if="settings.is_chief"><UiButton v-if="!periodOf(m)?.closed" size="sm" variant="outline" @click="closeMonth(m)">Khóa</UiButton><UiButton v-else size="sm" variant="ghost" @click="reopenMonth(m)">Mở lại</UiButton></template></div></div>
  </FormSection>
  <FormSection v-if="settings.payroll_params" title="Tham số lương theo pháp luật" :description="settings.payroll_params.note">
   <ul class="fin-list"><li v-for="r in settings.payroll_params.rows" :key="r.group+r.from" :class="{'fin-muted':r.confirmed===false}"><b>{{paramGroups[r.group]}} từ {{vnDate(r.from)}}{{r.confirmed===false?' (chưa xác nhận, chưa áp dụng)':''}}</b>: {{paramSummary(r)}}<br><small>{{r.source}}</small></li></ul>
  </FormSection>
  <FormSection title="Người làm kế toán" :description="'Kế toán: lập hóa đơn, phiếu chi, ghi sổ lương. Kế toán trưởng: ký phiếu chi, đảo bút toán, kết chuyển, khóa sổ, cấu hình. Kiểm soát: chỉ xem. '+(staff?.can_assign?'':'Chỉ Quản trị hệ thống được gán vai trò.')">
   <DataTable :rows="staff?.people||[]" :columns="peopleColumns" row-key="user" storage-key="fin-people" empty="Chưa có tài khoản nhân sự.">
    <template v-for="[key,role] in roleCells" :key="key" #[`cell-${key}`]="{row}"><Checkbox :model-value="!!row[key]" :disabled="!staff?.can_assign||saving" :aria-label="role+' cho '+row.name" @click.stop @update:model-value="value=>setRole(row,role,value)"/></template>
   </DataTable>
  </FormSection>
  <FormSection v-if="settings.is_chief" title="Bút toán điều chỉnh (phiếu kế toán khác)" description="Dùng cho nghiệp vụ không có chứng từ Lotus: phân loại lại số dư treo (VD 3381), điều chỉnh sai sót. Nợ phải bằng Có; tài khoản công nợ cần ghi mã đối tượng.">
   <template #actions><UiButton variant="ghost" size="sm" @click="openLedger(settings.mapping.stock_adjustment)">Xem sổ chi tiết 3381</UiButton></template>
   <FormGrid :columns="3"><LotusField v-model="adj.posting_date" label="Ngày hạch toán" type="date"/><LotusField v-model="adj.remark" label="Diễn giải" placeholder="VD: Phân loại lại tồn kho đầu kỳ từ 3381 sang 4111" class="lotus-form-grid__wide"/></FormGrid>
   <LineItemsEditor v-model="adj.lines" title="Dòng bút toán" add-label="Thêm dòng" :min="2" :columns="adjColumns" :new-row="newAdjLine">
    <template #footer><span class="lotus-lines__total">Tổng Nợ {{vnd(adjDebit)}} · Tổng Có {{vnd(adjCredit)}} <span :class="adjDebit===adjCredit&&adjDebit>0?'fin-ok':'land-bad'">{{adjDebit===adjCredit&&adjDebit>0?'Cân':'Chưa cân'}}</span></span></template>
   </LineItemsEditor>
   <p v-for="e in adjErrors" :key="e" class="land-bad">{{e}}</p>
   <div class="fin-actions fin-actions--end"><UiButton :disabled="saving" variant="outline" @click="sendAdjustment(0)">Xem trước</UiButton><UiButton :disabled="saving||adjDebit!==adjCredit||!adjDebit" @click="sendAdjustment(1)">Ghi sổ</UiButton></div>
  </FormSection>
  <FormSection v-if="settings.is_chief" title="Số dư đầu kỳ" description="Tải file mẫu, điền số dư từng tài khoản tại ngày bắt đầu ghi sổ (công nợ 331 ghi theo nhà cung cấp, 131 ghi theo từng khách hàng), rồi tải lên để xem trước. Tổng Dư Nợ phải bằng tổng Dư Có.">
   <template #actions><UiButton variant="outline" @click="downloadOpening"><LotusIcon name="download"/>File mẫu</UiButton></template>
   <FormGrid :columns="3"><LotusField label="Tải file số dư (.xlsx)" type="file" accept=".xlsx" :disabled="saving" @update:model-value="readOpening"/></FormGrid>
   <template v-if="openingPreview"><p>Dư Nợ {{vnd(openingPreview.debit)}} · Dư Có {{vnd(openingPreview.credit)}} · <span :class="openingPreview.balanced?'fin-ok':'land-bad'">{{openingPreview.balanced?'Cân':'Không cân'}}</span> · {{openingPreview.errors}} dòng lỗi · ngày {{vnDate(openingPreview.on_date)}}</p>
    <DataTable :rows="openingPreview.rows" :columns="openingColumns" row-key="line" storage-key="fin-opening"/>
    <div class="fin-actions fin-actions--end"><UiButton :disabled="saving||!openingPreview.balanced||openingPreview.errors>0||openingPreview.existing" :title="openingPreview.existing?'Đã có bút toán số dư đầu kỳ':''" @click="commitOpening">Ghi số dư đầu kỳ</UiButton></div></template>
  </FormSection>
 </template>

 <ModalForm v-model="invoiceOpen" title="Hóa đơn nhà cung cấp" :busy="saving" width="720px" submit-label="Ghi hóa đơn" :submit-disabled="!invoice.bill_no" :description="pickedReceipts.length+' phiếu nhận · '+(pickedReceipts[0]?.supplier_name||'')+' · '+vnd(pickedReceipts.reduce((s,r)=>s+Number(r.to_bill||0),0))" @submit="makeInvoice">
  <FormGrid><LotusField v-model="invoice.bill_no" label="Số hóa đơn" required/><LotusField v-model="invoice.bill_date" label="Ngày hóa đơn" type="date" required/><LotusField v-model="invoice.due_date" label="Hạn thanh toán" type="date"/><LotusField v-model="invoice.vat_code" label="Thuế suất GTGT" :options="vatChoices" :searchable="false" :empty-option="null"/></FormGrid>
  <p class="lotus-form-note">Ghi Nợ hàng về chưa có hóa đơn / Có phải trả người bán; thuế GTGT đầu vào Nợ 1331.</p>
 </ModalForm>

 <ModalForm :model-value="!!payrollView" title="Bút toán lương" :busy="saving" width="1080px" :readonly="!(overview?.can_post&&!payrollView?.posted)" submit-label="Ghi sổ" :submit-disabled="!!payrollView?.issues.length||!overview?.enabled" @update:model-value="v=>{if(!v)payrollView=null}" @submit="postPayroll">
  <template v-if="payrollView">
   <p>Tháng {{payrollView.month}} · {{payrollView.people}} người · {{payrollView.crews}} đội khoán · ngày hạch toán {{vnDate(payrollView.posting_date)}}</p>
   <p class="lotus-form-note">Tổng lương {{vnd(payrollView.totals.gross)}} · bảo hiểm doanh nghiệp {{vnd(payrollView.totals.employer_insurance)}} · KPCĐ {{vnd(payrollView.totals.union_fee)}} · thuế TNCN khấu trừ {{vnd(payrollView.totals.pit)}} · khoán {{vnd(payrollView.totals.crews)}} · thực nhận {{vnd(payrollView.totals.net)}}. {{payrollView.indirect.length}} người không có công ở lô nào được tính chi phí quản lý.</p>
   <p v-for="i in payrollView.issues" :key="i" class="land-bad">{{i}}</p>
   <DataTable :rows="keyed(payrollView.lines)" :columns="payrollLineColumns" row-key="__key" storage-key="fin-payroll-lines"/>
  </template>
 </ModalForm>

 <ModalForm :model-value="!!closingView" title="Kết chuyển chi phí sản xuất sang 154" :busy="saving" width="1080px" :readonly="!(settings?.is_chief&&!closingView?.posted)" submit-label="Ghi sổ kết chuyển" :submit-disabled="!closingView?.lines.length||!settings?.enabled" @update:model-value="v=>{if(!v)closingView=null}" @submit="postClosing">
  <template v-if="closingView">
   <p>Tháng {{closingView.month}} · ngày hạch toán {{vnDate(closingView.posting_date)}} · tổng kết chuyển <b>{{vnd(closingView.total)}}</b></p>
   <p v-if="closingView.posted" class="land-warn">Tháng này đã kết chuyển ({{closingView.posted.voucher}}).</p>
   <DataTable :rows="keyed(closingView.lines)" :columns="payrollLineColumns" row-key="__key" storage-key="fin-closing-lines" empty="Không có chi phí 621 / 622 / 627 trong tháng."/>
  </template>
 </ModalForm>

 <ModalForm :model-value="!!resultView" title="Kết chuyển kết quả kinh doanh (911 → 4212)" :busy="saving" width="1000px" :readonly="!(settings?.is_chief&&!resultView?.posted)" submit-label="Ghi sổ kết chuyển" :submit-disabled="!resultView?.lines.length||!!resultView?.issues.length||!settings?.enabled" @update:model-value="v=>{if(!v)resultView=null}" @submit="postResult">
  <template v-if="resultView">
   <p>Tháng {{resultView.month}} · ngày hạch toán {{vnDate(resultView.posting_date)}} · doanh thu, thu nhập {{vnd(resultView.income)}} · chi phí {{vnd(resultView.expense)}} · <b>{{resultView.profit>=0?'Lãi':'Lỗ'}} {{vnd(Math.abs(resultView.profit))}}</b></p>
   <p class="lotus-form-note">Mọi tài khoản doanh thu (5xx, 711) và chi phí (632, 635, 641, 642, 811, 821) của tháng về 911, rồi 911 về 4212. Báo cáo kết quả kinh doanh không tính bút toán này.</p>
   <p v-for="i in resultView.issues" :key="i" class="land-bad">{{i}}</p>
   <p v-if="resultView.posted" class="land-warn">Tháng này đã kết chuyển ({{resultView.posted.voucher}}).</p>
   <DataTable :rows="keyed(resultView.lines)" :columns="payrollLineColumns" row-key="__key" storage-key="fin-result-lines" empty="Không có doanh thu, chi phí trong tháng."/>
  </template>
 </ModalForm>

 <ModalForm :model-value="!!costingView" title="Tính giá thành chuối" :busy="saving" width="1180px" :readonly="!(settings?.is_chief&&!costingView?.posted?.voucher)" submit-label="Ghi sổ giá thành" :submit-disabled="!costingView?.closed||!!costingView?.issues?.length||!costingView?.rows.length||!settings?.enabled" @update:model-value="v=>{if(!v)costingView=null}" @submit="postCosting">
  <template v-if="costingView">
   <p>Tháng {{costingView.month}} · ngày hạch toán {{vnDate(costingView.posting_date)}} · {{num(costingView.totals.kg_harvested,1)}} kg thu · giá thành sản lượng <b>{{vnd(costingView.totals.absorbed)}}</b> · chênh lệch so với tạm tính <b>{{vnd(costingView.totals.adjustment)}}</b></p>
   <p class="lotus-form-note">Mỗi lô: (dở dang đầu kỳ + chi phí tháng) × kg thu ÷ (kg thu + kg dự thu còn lại). Chi phí chung của vườn (không gắn lô) chia theo kg của cả vườn. Chênh lệch dương ghi Nợ 632 / Có 154, âm ghi ngược lại.</p>
   <p v-for="issue in costingView.issues||[]" :key="issue" class="land-warn">{{issue}}</p>
   <p v-if="!costingView.closed" class="land-warn">Chưa kết chuyển chi phí 621 / 622 / 627 sang 154 của tháng này. Bấm "Kết chuyển CP" trước.</p>
   <p v-if="costingView.posted?.voucher" class="land-warn">Tháng này đã tính giá thành ({{costingView.posted.voucher}}). Đảo bút toán đó nếu cần tính lại.</p>
   <DataTable :rows="costingRows(costingView)" :columns="costingColumns" :pinned-bottom-rows="costingTotals(costingView)" row-key="__key" storage-key="fin-costing-preview" empty="Tháng này không có chi phí dở dang hay sản lượng thu hoạch."/>
   <details v-if="costingView.lines.length"><summary>Bút toán chênh lệch ({{costingView.lines.length}} dòng)</summary><DataTable :rows="keyed(costingView.lines)" :columns="payrollLineColumns" row-key="__key" storage-key="fin-costing-lines"/></details>
  </template>
 </ModalForm>

 <ModalForm v-model="payOpen" title="Phiếu chi trả nhà cung cấp" :busy="saving" width="960px" submit-label="Lập phiếu và gửi ký" :submit-disabled="!payTotal" @submit="preparePay">
  <LineItemsEditor :model-value="supplierInvoices" title="Hóa đơn còn nợ" :columns="allocationColumns" fixed empty-text="Nhà cung cấp không còn hóa đơn nợ.">
   <template #cell-bill="{row}"><b>{{row.bill_no||row.name}}</b></template>
   <template #cell-due="{row}">{{vnDate(row.due_date)}}</template>
   <template #cell-owed="{row}"><span class="fin-num">{{vnd(row.outstanding_amount-(row.paying||0))}}</span></template>
   <template #cell-amount="{row}"><LotusField v-model="pay.allocations[row.name]" type="money" min="0" :aria-label="'Trả hóa đơn '+(row.bill_no||row.name)"/></template>
   <template #footer><span class="lotus-lines__total">Tổng chi <b>{{vnd(payTotal)}}</b></span></template>
  </LineItemsEditor>
  <FormGrid :columns="3"><PaymentModeFields v-model:mode="pay.mode" v-model:date="pay.posting_date" v-model:reference="pay.reference_no" :modes="[{value:'cash',label:'Tiền mặt (phiếu chi)'},{value:'bank',label:'Chuyển khoản (ủy nhiệm chi)'}]"/></FormGrid>
  <SignerPicker v-model="signers" :options="signerOptions" :disabled="saving"/>
 </ModalForm>

 <ModalForm :model-value="!!salaryOpen" title="Phiếu chi lương" :busy="saving" width="760px" submit-label="Lập phiếu và gửi ký" :description="salaryOpen?'Tháng '+salaryOpen.month+' · thực lĩnh '+vnd(salaryOpen.net)+' · đã tạm ứng '+vnd(salaryOpen.advance)+' · chi lần này '+vnd(salaryOpen.to_pay):''" @update:model-value="v=>{if(!v)salaryOpen=null}" @submit="prepareSalary">
  <FormGrid :columns="3"><PaymentModeFields v-model:mode="salary.mode" v-model:date="salary.posting_date" v-model:reference="salary.reference_no" :modes="[{value:'bank',label:'Chuyển khoản'},{value:'cash',label:'Tiền mặt'}]" reference-label="Số ủy nhiệm chi" :reference-required="false"/></FormGrid>
  <SignerPicker v-model="signers" :options="signerOptions" :disabled="saving"/>
 </ModalForm>

 <ModalForm v-model="customerOpen" title="Khách hàng" :busy="saving" width="720px" :submit-disabled="!customer.customer_name" @submit="saveCustomer">
  <FormGrid><LotusField v-model="customer.customer_name" label="Tên khách hàng" required/><LotusField v-model="customer.tax_id" label="Mã số thuế" inputmode="numeric"/><LotusField v-model="customer.address" label="Địa chỉ" class="lotus-form-grid__wide"/><LotusField v-model="customer.credit_days" label="Hạn thanh toán (ngày)" type="number" min="0"/></FormGrid>
 </ModalForm>

 <ModalForm v-model="saleOpen" title="Hóa đơn bán hàng (xuất kho)" :busy="saving" width="1180px" submit-label="Ghi hóa đơn" :submit-disabled="!sale.customer||!saleNet" @submit="saveSale">
  <FormGrid :columns="3">
   <LotusField v-model="sale.customer" label="Khách hàng" :options="(lookups?.customers||[]).map(c=>({value:c.name,label:c.customer_name+(c.tax_id?' · '+c.tax_id:'')}))" required/>
   <LotusField v-model="sale.posting_date" label="Ngày hóa đơn" type="date" required/><LotusField v-model="sale.due_date" label="Hạn thu" type="date"/>
   <LotusField v-model="sale.vat_code" label="Thuế suất GTGT" :options="vatChoices" :searchable="false" :empty-option="null"/>
   <LotusField v-model="sale.einvoice_series" label="Ký hiệu hóa đơn điện tử" placeholder="VD: 1C26TLT"/><LotusField v-model="sale.einvoice_no" label="Số hóa đơn điện tử"/>
  </FormGrid>
  <LineItemsEditor v-model="sale.lines" title="Hàng bán" add-label="Thêm dòng" :columns="saleColumns" :new-row="newSaleLine">
   <template #cell-onhand="{row}"><span class="fin-num">{{stockOf(row)?num(stockOf(row).actual_qty,2)+' '+unitLabel(stockOf(row).stock_uom):'—'}}</span></template>
   <template #footer><span class="lotus-lines__total">Chưa thuế {{vnd(saleNet)}} · thuế GTGT {{vnd(saleTax)}} · tổng <b>{{vnd(saleNet+saleTax)}}</b></span></template>
  </LineItemsEditor>
  <p v-if="!saleStock.length" class="land-warn">Chưa có hàng trong kho thành phẩm (TK 155). Nhập kho chuối thu hoạch hoặc kết quả đóng gói trước.</p>
 </ModalForm>

 <ModalForm v-model="receiptOpen" title="Phiếu thu tiền khách hàng" :busy="saving" width="960px" submit-label="Ghi phiếu thu" :submit-disabled="!receiptTotal" :description="receipt.customer_name" @submit="saveReceipt">
  <LineItemsEditor :model-value="receiptInvoices" title="Hóa đơn còn phải thu" :columns="allocationColumns" fixed empty-text="Khách hàng không còn hóa đơn phải thu.">
   <template #cell-bill="{row}"><b>{{[row.lotus_einvoice_series,row.lotus_einvoice_no].filter(Boolean).join(' ')||row.name}}</b></template>
   <template #cell-due="{row}">{{vnDate(row.due_date)}}</template>
   <template #cell-owed="{row}"><span class="fin-num">{{vnd(row.outstanding_amount)}}</span></template>
   <template #cell-amount="{row}"><LotusField v-model="receipt.allocations[row.name]" type="money" min="0" :aria-label="'Thu hóa đơn '+row.name"/></template>
   <template #footer><span class="lotus-lines__total">Tổng thu <b>{{vnd(receiptTotal)}}</b></span></template>
  </LineItemsEditor>
  <FormGrid :columns="3"><PaymentModeFields v-model:mode="receipt.mode" v-model:date="receipt.posting_date" v-model:reference="receipt.reference_no" :modes="[{value:'bank',label:'Chuyển khoản (báo có)'},{value:'cash',label:'Tiền mặt (phiếu thu)'}]" date-label="Ngày thu" reference-label="Số giao dịch / báo có"/></FormGrid>
 </ModalForm>

 <ModalForm v-model="advanceOpen" title="Phiếu tạm ứng lương" :busy="saving" width="860px" submit-label="Lập phiếu và gửi ký" :submit-disabled="!advance.employee||!Number(advance.amount)" description="Nợ 334 / Có 111 hoặc 112. Khi chi lương tháng đó, Lotus tự trừ số đã tạm ứng." @submit="prepareAdvance">
  <FormGrid :columns="3">
   <LotusField v-model="advance.employee" label="Nhân viên" :options="(lookups?.employees||[]).map(e=>({value:e.name,label:e.employee_name+' · '+e.name}))" required/>
   <LotusField v-model="advance.amount" label="Số tiền" type="money" min="0" required/>
   <LotusField v-model="advance.month" label="Trừ vào lương tháng" type="month" required/>
   <PaymentModeFields v-model:mode="advance.mode" v-model:date="advance.posting_date" v-model:reference="advance.reference_no" reference-label="Số ủy nhiệm chi" :reference-required="false"/>
  </FormGrid>
  <SignerPicker v-model="signers" :options="signerOptions" :disabled="saving"/>
 </ModalForm>

 <ModalForm v-model="statutoryOpen" title="Nộp bảo hiểm, kinh phí công đoàn, thuế TNCN" :busy="saving" width="960px" submit-label="Lập phiếu và gửi ký" :submit-disabled="!statutoryTotal" @submit="prepareStatutory">
  <LineItemsEditor v-model="statutory.rows" title="Khoản phải nộp" :columns="statutoryColumns" fixed>
   <template #cell-label="{row}"><b>{{row.label}}</b></template>
   <template #cell-owed="{row}"><span class="fin-num">{{vnd(row.owed)}}</span></template>
   <template #cell-pending="{row}"><span class="fin-num">{{vnd(row.pending)}}</span></template>
   <template #footer><span class="lotus-lines__total">Tổng nộp <b>{{vnd(statutoryTotal)}}</b></span></template>
  </LineItemsEditor>
  <FormGrid :columns="3"><PaymentModeFields v-model:mode="statutory.mode" v-model:date="statutory.posting_date" v-model:reference="statutory.reference_no" :modes="[{value:'bank',label:'Chuyển khoản (ủy nhiệm chi)'},{value:'cash',label:'Tiền mặt'}]" date-label="Ngày nộp" reference-label="Số ủy nhiệm chi"/></FormGrid>
  <SignerPicker v-model="signers" :options="signerOptions" :disabled="saving"/>
 </ModalForm>

 <ModalForm v-model="serviceOpen" title="Hóa đơn dịch vụ / chi phí" :busy="saving" width="1180px" submit-label="Ghi hóa đơn" :submit-disabled="!service.supplier||!service.bill_no" @submit="saveService">
  <FormGrid :columns="3">
   <LotusField v-model="service.supplier" label="Nhà cung cấp" :options="(lookups?.suppliers||[]).map(s=>({value:s.name,label:s.supplier_name}))" required/>
   <LotusField v-model="service.bill_no" label="Số hóa đơn" required/><LotusField v-model="service.bill_date" label="Ngày hóa đơn" type="date"/><LotusField v-model="service.due_date" label="Hạn thanh toán" type="date"/>
   <LotusField v-model="service.vat_code" label="Thuế suất GTGT" :options="vatChoices" :searchable="false" :empty-option="null"/>
  </FormGrid>
  <LineItemsEditor v-model="service.lines" title="Nội dung hóa đơn" add-label="Thêm dòng" :columns="serviceColumns" :new-row="newServiceLine"/>
 </ModalForm>

 <ModalForm :model-value="!!returnOpen" title="Trả lại phiếu chi" :busy="saving" width="560px" submit-label="Trả lại" :submit-disabled="returnReason.trim().length<3" @update:model-value="v=>{if(!v)returnOpen=null}" @submit="sendBack">
  <LotusField v-model="returnReason" label="Lý do" type="textarea" required minlength="3"/>
 </ModalForm>
 <ReasonDialog :dialog="reasonPrompt"/>
 <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" @answer="finishConfirm"/>
</section>
</template>
