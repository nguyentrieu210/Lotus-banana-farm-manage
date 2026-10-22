<script setup>
// /lotus/tai-chinh — Tài chính – Kế toán on ERPNext's ledger: overview, documents waiting for an accountant,
// journal, payables, payment vouchers (signed accountant → chief accountant → director), reports and settings.
// Data: lotus_farm.finance.*. Payment approvers without ledger access see only the vouchers waiting for them.
import {computed,onMounted,ref,watch} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import LotusIcon from './components/LotusIcon.vue'
import LotusChart from './components/LotusChart.vue'
import WorkspaceModal from './components/WorkspaceModal.vue'
import WorkspaceConfirm from './components/WorkspaceConfirm.vue'
import SignerPicker from './components/SignerPicker.vue'
import DataTable from './components/DataTable.vue'
import FinanceGuide from './components/finance/FinanceGuide.vue'
import {DatePicker} from './components/ui/date-picker'
import {Button as UiButton} from './components/ui/button'
import {Input as UiInput} from './components/ui/input'
import UiSelect from './components/ui/select/Select.vue'
import {useWorkspaceConfirm} from './use-workspace-confirm'
import {useNoticeToast} from './use-toast'
import {call} from './api'
import {useSession} from './store'
import './land.css'
import './finance.css'

defineProps({embedded:Boolean,navigationKey:String})
const F='lotus_farm.finance.'
const TABS=[['overview','Tổng quan'],['pending','Chờ hạch toán'],['journal','Nhật ký kế toán'],['sales','Bán hàng – Phải thu'],['payables','Công nợ phải trả'],['cash','Thu / Chi'],['reports','Báo cáo'],['settings','Thiết lập'],['guide','Hướng dẫn']]
const REPORTS=[['trial_balance','Bảng cân đối phát sinh'],['ledger','Sổ chi tiết tài khoản'],['costs','Chi phí theo vườn / lô'],['costing','Giá thành theo lô'],['vat','Thuế GTGT'],['reconciliation','Đối chiếu']]
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
const vnd=v=>v==null?'—':num(Math.round(Number(v)))+' đ'
const vnDate=v=>v?String(v).slice(8,10)+'/'+String(v).slice(5,7)+'/'+String(v).slice(0,4):'—'
const dimLabel=(field,value)=>{if(!value)return '';if(field==='lotus_farm_block'){const b=(lookups.value?.blocks||[]).find(x=>x.name===value);return b?b.block_code:value}return value}
function go(next){router.push({path:'/tai-chinh',query:{...route.query,tab:next}})}
async function run(fn){busy.value=true;error.value='';try{return await fn()}catch(e){error.value=e.message}finally{busy.value=false}}
async function ensureLookups(){if(!lookups.value)lookups.value=await call(F+'reports.lookups')}
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
  if(tab.value==='settings'){settings.value=await call(F+'api.settings');staff.value=await call(F+'api.people');await ensureLookups()}
 })
}
async function loadReport(){
 const args={from_date:range.value.from,to_date:range.value.to}
 if(report.value==='trial_balance')reportData.value=await call(F+'reports.trial_balance',args)
 if(report.value==='costs')reportData.value=await call(F+'reports.costs',{...args,group_by:groupBy.value})
 if(report.value==='reconciliation')reportData.value=await call(F+'reports.reconciliation',{on_date:range.value.to})
 if(report.value==='ledger')reportData.value=ledgerAccount.value?await call(F+'reports.ledger',{...args,account:ledgerAccount.value}):null
 if(report.value==='costing'){await ensureLookups();reportData.value=await call(F+'costing.preview',{month:range.value.to.slice(0,7)})}
 if(report.value==='vat'){await ensureVat();reportData.value=await call(F+'sales.vat_report',{month:range.value.to.slice(0,7)})}
}
const vatOptions=ref(null)
async function ensureVat(){if(!vatOptions.value)vatOptions.value=await call(F+'sales.vat_options',{on_date:today})}
const vatLabel=code=>(vatOptions.value?.rates||[]).find(r=>r.code===code)?.label||code||'KCT'
// Sales: customers, invoices that ship the goods, receipts
const salesData=ref(null),customerOpen=ref(false),customer=ref({}),saleOpen=ref(false),sale=ref({}),saleStock=ref([]),receiptOpen=ref(false),receipt=ref({})
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
function exportReport(kind){const q={kind,from_date:range.value.from,to_date:range.value.to};if(kind==='costs')q.group_by=groupBy.value;if(kind==='ledger')q.account=ledgerAccount.value
 location.href='/api/method/lotus_farm.finance.reports.export?'+new URLSearchParams(q)}

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
 const reason=window.prompt('Lý do đảo bút toán '+label+' (bắt buộc):');if(!reason)return
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
const costingView=ref(null)
async function previewCosting(m){await ensureLookups();await run(async()=>{costingView.value=await call(F+'costing.preview',{month:m})})}
async function postCosting(){saving.value=true
 try{const r=await call(F+'costing.run',{month:costingView.value.month},true)
  notice.value='Đã tính giá thành tháng '+costingView.value.month+': giá thành sản lượng thu '+vnd(r.absorbed)+', chênh lệch so với tạm tính '+vnd(r.adjustment)+(r.voucher?' ('+r.voucher+')':'')+'.';costingView.value=null}
 catch(e){error.value=e.message}finally{saving.value=false}}
async function closeMonth(m){if(!await ask('Khóa sổ tháng '+m.slice(5)+'/'+m.slice(0,4)+'? Sau khi khóa không ghi, sửa hay hủy chứng từ trong tháng được nữa.','Khóa sổ'))return
 await run(async()=>{await call(F+'posting.close_month',{month:m},true);settings.value=await call(F+'api.settings');notice.value='Đã khóa sổ tháng '+m.slice(5)+'/'+m.slice(0,4)+'.'})}
async function reopenMonth(m){const reason=window.prompt('Lý do mở lại kỳ '+m+' (bắt buộc):');if(!reason)return
 await run(async()=>{await call(F+'posting.reopen_month',{month:m,reason},true);settings.value=await call(F+'api.settings');notice.value='Đã mở lại kỳ.'})}
function openWarehouse(name){location.href='/warehouse?doc='+encodeURIComponent(name)+'&doctype=Stock%20Entry'}
function downloadOpening(){location.href='/api/method/lotus_farm.finance.api.opening_template'}
async function readOpening(event){const file=event.target.files?.[0];if(!file)return;saving.value=true
 try{const content=await new Promise((ok,fail)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=fail;r.readAsDataURL(file)});openingPreview.value=await call(F+'api.opening_preview',{content},true)}
 catch(e){error.value=e.message}finally{saving.value=false;event.target.value=''}}
async function commitOpening(){saving.value=true
 try{const r=await call(F+'api.opening_commit',{token:openingPreview.value.token},true);notice.value='Đã ghi số dư đầu kỳ '+r.voucher+' ('+vnd(r.amount)+').';openingPreview.value=null}
 catch(e){error.value=e.message}finally{saving.value=false}}

// Grid columns (shared DataTable). Money columns show whole đồng; action cells stop the row click.
const money=p=>p.value?num(p.value):''
const dateCol=(field,headerName)=>({field,headerName,minWidth:110,valueFormatter:p=>vnDate(p.value)})
const moneyCol=(field,headerName,extra={})=>({field,headerName,minWidth:130,type:'numericColumn',valueFormatter:p=>p.node?.rowPinned?num(p.value):money(p),...extra})
function cellButton(label,fn,show=()=>true){return params=>{if(!params.data||params.node?.rowPinned||!show(params.data))return '';const b=document.createElement('button');b.type='button';b.className='fin-cell-action';b.textContent=label
 b.addEventListener('click',e=>{e.stopPropagation();fn(params.data)});return b}}
function pickCell(params){if(!params.data)return '';const input=document.createElement('input');input.type='checkbox';input.checked=picked.value.has(params.data.name);input.setAttribute('aria-label','Chọn '+params.data.name)
 input.addEventListener('click',e=>e.stopPropagation());input.addEventListener('change',e=>{e.stopPropagation();togglePick(params.data.name)});return input}
const receiptColumns=computed(()=>[...(overview.value?.can_post?[{field:'__pick',headerName:'Chọn',minWidth:70,maxWidth:80,sortable:false,hideOnMobile:true,cellRenderer:pickCell}]:[]),
 {field:'name',headerName:'Phiếu nhận',minWidth:170},{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:200,valueGetter:p=>p.data.supplier_name||p.data.supplier},dateCol('posting_date','Ngày'),moneyCol('to_bill','Chưa lập hóa đơn')])
const receiptRows=computed(()=>(pendingData.value?.receipts||[]).map(r=>({...r,__pick:picked.value.has(r.name)})))
const payrollPendingColumns=[{field:'month',headerName:'Tháng',minWidth:100,valueFormatter:p=>p.value?p.value.slice(5)+'/'+p.value.slice(0,4):''},{field:'name',headerName:'Kỳ công',minWidth:200},
 {field:'closed_at',headerName:'Đóng lúc',minWidth:120,valueFormatter:p=>vnDate(String(p.value||'').slice(0,10))},{field:'__view',headerName:'',minWidth:170,sortable:false,cellRenderer:cellButton('Xem trước bút toán',r=>previewPayroll(r.name))}]
const harvestColumns=computed(()=>[{field:'name',headerName:'Lô thu hoạch',minWidth:170},{field:'farm',headerName:'Vườn',minWidth:120},dateCol('received_date','Ngày nhận'),
 {field:'released_raw_kg',headerName:'Kg',minWidth:100,type:'numericColumn',valueFormatter:p=>num(p.value,1)},{field:'reason',headerName:'Tình trạng',minWidth:240,flex:2},
 ...(overview.value?.can_post?[{field:'__receive',headerName:'',minWidth:120,sortable:false,cellRenderer:cellButton('Nhập kho',receiveHarvest,r=>r.raw_item&&r.raw_warehouse&&r.raw_batch)}]:[])])
const costingColumns=[{field:'label',headerName:'Lô',minWidth:170,flex:2,valueGetter:p=>p.node?.rowPinned?p.data.label:p.data.label+(p.data.lotus_farm_block&&p.data.lotus_farm?' · '+p.data.lotus_farm:'')},
 moneyCol('wip_open','Dở dang đầu kỳ'),moneyCol('cost_month','Chi phí tháng'),{field:'kg_harvested',headerName:'Kg thu',minWidth:100,type:'numericColumn',valueFormatter:p=>p.value?num(p.value,1):''},
 {field:'kg_remaining',headerName:'Kg dự thu còn lại',minWidth:130,type:'numericColumn',valueFormatter:p=>p.value?num(p.value,1):''},moneyCol('absorbed','Giá thành sản lượng'),
 {field:'cost_per_kg',headerName:'Giá thành / kg',minWidth:120,type:'numericColumn',valueFormatter:p=>p.value?num(p.value,2):''},moneyCol('provisional','Đã nhập kho (tạm tính)'),
 moneyCol('adjustment','Chênh lệch → 632'),moneyCol('wip_close','Dở dang cuối kỳ'),{field:'basis',headerName:'Cách tính',minWidth:220,flex:2}]
const costingRows=view=>(view?.rows||[]).map((r,i)=>({...r,__key:(r.lotus_farm||'')+'|'+(r.lotus_farm_block||'')+'|'+i}))
const costingTotals=view=>view?.totals?[{__key:'__total',label:'Tổng',...view.totals,cost_per_kg:view.totals.kg_harvested?view.totals.absorbed/view.totals.kg_harvested:null}]:[]
const customerColumns=computed(()=>[{field:'customer_name',headerName:'Khách hàng',minWidth:220,flex:2},{field:'tax_id',headerName:'MST',minWidth:120},moneyCol('invoiced','Đã xuất hóa đơn'),
 moneyCol('received','Đã thu'),moneyCol('owed','Còn phải thu'),moneyCol('overdue','Quá hạn'),{field:'credit_days',headerName:'Hạn nợ (ngày)',minWidth:110},
 ...(overview.value?.can_post?[{field:'__edit',headerName:'',minWidth:80,sortable:false,cellRenderer:cellButton('Sửa',openCustomer)},
  {field:'__receive',headerName:'',minWidth:110,sortable:false,cellRenderer:cellButton('Thu tiền',openReceipt,r=>r.open_invoices>0)}]:[])])
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
 {field:'open_invoices',headerName:'Hóa đơn còn nợ',minWidth:110},...(overview.value?.can_post?[{field:'__pay',headerName:'',minWidth:140,sortable:false,cellRenderer:cellButton('Lập phiếu chi',r=>openPay(r.supplier),r=>r.open_invoices>0)}]:[])])
const invoiceColumns=[{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:200},{field:'bill_no',headerName:'Số hóa đơn',minWidth:130,valueGetter:p=>p.data.bill_no||p.data.name},dateCol('bill_date','Ngày'),dateCol('due_date','Hạn trả'),
 moneyCol('grand_total','Tổng tiền'),moneyCol('outstanding_amount','Còn nợ'),moneyCol('paying','Đang chờ chi'),{field:'aging',headerName:'Tuổi nợ',minWidth:150,cellClass:p=>p.value&&p.value!=='Trong hạn'?'fin-cell-bad':''}]
const salaryReadyColumns=computed(()=>[{field:'month',headerName:'Tháng',minWidth:100,valueFormatter:p=>p.value?p.value.slice(5)+'/'+p.value.slice(0,4):''},moneyCol('net','Thực lĩnh'),
 moneyCol('advance','Đã tạm ứng'),moneyCol('to_pay','Còn phải chi'),{field:'payroll_voucher',headerName:'Bút toán lương',minWidth:170},
 {field:'__list',headerName:'',minWidth:170,sortable:false,cellRenderer:cellButton('Danh sách chuyển khoản',r=>exportTransfer(r.period))},
 ...(overview.value?.can_post?[{field:'__pay',headerName:'',minWidth:170,sortable:false,cellRenderer:cellButton('Lập phiếu chi lương',openSalary)}]:[])])
const voucherColumns=computed(()=>[{field:'name',headerName:'Phiếu',minWidth:170},{field:'kind',headerName:'Loại',minWidth:140},{field:'party_name',headerName:'Đối tượng',minWidth:180},dateCol('posting_date','Ngày'),moneyCol('amount','Số tiền'),
 {field:'state',headerName:'Trạng thái',minWidth:110,cellClass:p=>p.value==='Chờ ký'?'fin-cell-warn':''},
 {field:'signers',headerName:'Người ký',minWidth:260,flex:2,valueGetter:p=>(p.data.signing?.steps||[]).map(x=>x.title+': '+(x.name||'—')+' ('+(x.state||'—')+')').join(' · ')},
 {field:'__drop',headerName:'',minWidth:90,sortable:false,cellRenderer:cellButton('Hủy',dropDraft,v=>v.state==='Chờ ký'&&overview.value?.can_post)},
 {field:'__reverse',headerName:'',minWidth:90,sortable:false,cellRenderer:cellButton('Đảo',v=>reverse(v.posting,v.name),v=>v.state==='Đã chi'&&overview.value?.is_chief)}])
const tbColumns=[{field:'number',headerName:'Số TK',minWidth:90},{field:'name',headerName:'Tên tài khoản',minWidth:240,flex:2},moneyCol('opening_debit','Dư Nợ đầu kỳ'),moneyCol('opening_credit','Dư Có đầu kỳ'),
 moneyCol('debit','Phát sinh Nợ'),moneyCol('credit','Phát sinh Có'),moneyCol('closing_debit','Dư Nợ cuối kỳ'),moneyCol('closing_credit','Dư Có cuối kỳ')]
const tbTotals=computed(()=>reportData.value?.totals&&report.value==='trial_balance'?[{account:'__total',number:'',name:'Tổng cộng',...reportData.value.totals}]:[])
const ledgerColumns=[dateCol('posting_date','Ngày'),{field:'voucher_no',headerName:'Chứng từ',minWidth:170},{field:'party',headerName:'Đối tượng',minWidth:120},
 {field:'remarks',headerName:'Diễn giải',minWidth:200,flex:2,valueGetter:p=>String(p.data.remarks||'').split('\n')[0]},moneyCol('debit','Nợ'),moneyCol('credit','Có'),moneyCol('balance','Số dư',{valueFormatter:p=>num(p.value)})]
const ledgerRows=computed(()=>(reportData.value?.lines||[]).map((l,i)=>({...l,__key:i})))
const groupLabel=computed(()=>({lotus_farm:'Vườn',lotus_farm_block:'Lô',lotus_crop_cycle:'Vụ',lotus_work_type:'Công việc'})[groupBy.value])
const costColumns=computed(()=>[{field:'label',headerName:groupLabel.value,minWidth:180,flex:2,valueGetter:p=>p.data.label+(groupBy.value!=='lotus_farm'&&p.data.farm&&!p.node?.rowPinned?' · '+p.data.farm:'')},
 moneyCol('materials','Vật tư'),moneyCol('labour','Nhân công'),moneyCol('crews','Khoán'),moneyCol('services','Dịch vụ'),moneyCol('total','Tổng'),...(groupBy.value==='lotus_farm_block'?[moneyCol('per_ha','Chi phí / ha')]:[])])
const costRows=computed(()=>(report.value==='costs'&&reportData.value?.rows||[]).map((r,i)=>({...r,__key:(r.dim||'-')+'|'+(r.farm||'')+'|'+i})))
const costTotals=computed(()=>report.value==='costs'&&reportData.value?.totals?[{__key:'__total',label:'Tổng',...reportData.value.totals}]:[])
const reconColumns=[{field:'label',headerName:'Nội dung',minWidth:320,flex:3},moneyCol('ledger','Sổ kế toán',{valueFormatter:p=>num(p.value)}),moneyCol('source','Nghiệp vụ',{valueFormatter:p=>num(p.value)}),
 {field:'difference',headerName:'Chênh lệch',minWidth:120,valueFormatter:p=>p.data.ok?'Khớp':num(p.value),cellClass:p=>p.data?.ok?'fin-cell-ok':'fin-cell-bad'}]
const transferColumns=[{field:'old',headerName:'Tài khoản cũ',minWidth:220,flex:2},{field:'new',headerName:'Chuyển sang',minWidth:240,flex:2},moneyCol('balance','Số dư',{valueFormatter:p=>num(p.value)})]
const openingColumns=[{field:'line',headerName:'Dòng',minWidth:70},{field:'number',headerName:'TK',minWidth:90},{field:'supplier',headerName:'Nhà cung cấp',minWidth:140},moneyCol('debit','Dư Nợ'),moneyCol('credit','Dư Có'),
 {field:'errors',headerName:'Lỗi',minWidth:260,flex:2,valueGetter:p=>(p.data.errors||[]).join('; '),cellClass:p=>p.value?'fin-cell-bad':''}]
const payrollLineColumns=[{field:'account',headerName:'Tài khoản',minWidth:260,flex:2},moneyCol('debit','Nợ'),moneyCol('credit','Có'),{field:'lotus_farm',headerName:'Vườn',minWidth:110},
 {field:'lotus_farm_block',headerName:'Lô',minWidth:90,valueGetter:p=>dimLabel('lotus_farm_block',p.data.lotus_farm_block)},{field:'lotus_work_type',headerName:'Công việc',minWidth:120},{field:'note',headerName:'Diễn giải',minWidth:140}]
const staff=ref(null)
function roleCell(key,role){return params=>{if(!params.data)return '';const input=document.createElement('input');input.type='checkbox';input.checked=!!params.data[key];input.disabled=!staff.value?.can_assign
 input.setAttribute('aria-label',role+' cho '+params.data.name);input.addEventListener('click',e=>e.stopPropagation())
 input.addEventListener('change',async e=>{e.stopPropagation();await run(async()=>{await call(F+'api.set_role',{user:params.data.user,role,on:input.checked?1:0},true);staff.value=await call(F+'api.people');notice.value='Đã cập nhật vai trò của '+params.data.name+'.'})});return input}}
const peopleColumns=[{field:'name',headerName:'Nhân sự',minWidth:200,flex:2},{field:'designation',headerName:'Chức danh',minWidth:140},{field:'user',headerName:'Tài khoản',minWidth:200},
 {field:'chief',headerName:'Kế toán trưởng',minWidth:120,sortable:false,cellRenderer:roleCell('chief','Lotus Chief Accountant')},
 {field:'accountant',headerName:'Kế toán',minWidth:100,sortable:false,cellRenderer:roleCell('accountant','Lotus Accountant')},
 {field:'auditor',headerName:'Kiểm soát',minWidth:100,sortable:false,cellRenderer:roleCell('auditor','Lotus Auditor')},
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
const keyed=list=>(list||[]).map((r,i)=>({...r,__key:i}))
const tiles=computed(()=>overview.value?.tiles||{})
const costChart=computed(()=>(report.value==='costs'&&reportData.value?.rows||[]).slice(0,12))
watch(()=>route.query.tab,load)
watch(report,()=>run(loadReport))
onMounted(load)
useNoticeToast(notice)
</script>

<template>
<section class="fin lotus-ui">
 <header class="fin-head">
  <div class="fin-title"><h2>Tài chính – Kế toán</h2><span v-if="overview">{{overview.company}} · {{overview.coa_version?'Hệ thống tài khoản '+overview.coa_version:'Chưa áp dụng hệ thống tài khoản Thông tư 99'}}</span></div>
  <span class="land-spacer"></span>
  <span v-if="overview" class="fin-state" :class="{on:overview.enabled}">{{overview.enabled?'Đang ghi sổ từ '+vnDate(overview.cutover_date):'Ghi sổ từ Lotus đang tắt'}}</span>
 </header>
 <p v-if="error" class="stock-error" role="alert">{{error}}</p>
 <nav v-if="ledgerUser" class="workspace-tabs" aria-label="Tài chính – Kế toán"><button v-for="[id,label] in TABS" :key="id" type="button" :class="{active:tab===id,selected:tab===id}" :aria-current="tab===id?'page':undefined" @click="go(id)">{{label}}<b v-if="id==='pending'&&overview?.pending_counts" class="fin-badge">{{Object.values(overview.pending_counts).reduce((a,b)=>a+b,0)||''}}</b></button></nav>

 <!-- Approver without ledger access -->
 <section v-if="tab==='sign'" class="land-card">
  <h3>Phiếu chi chờ bạn ký</h3>
  <p v-if="!mine.length&&!busy" class="land-empty">Không có phiếu chi nào đang chờ bạn ký.</p>
  <article v-for="v in mine" :key="v.name" class="fin-voucher">
   <header><b>{{v.kind}} · {{v.party_name}}</b><strong>{{vnd(v.amount)}}</strong></header>
   <small>{{v.name}} · ngày {{vnDate(v.posting_date)}}{{v.reference?' · '+v.reference:''}}</small>
   <ul><li v-for="l in v.lines" :key="l.label">{{l.label}}: {{vnd(l.amount)}}</li></ul>
   <ol class="fin-steps"><li v-for="s in v.signing.steps" :key="s.key" :class="s.state==='Đã ký'?'done':s.state==='Chờ ký'?'now':''">{{s.title}}: {{s.name||'—'}} <small>{{s.state}}</small></li></ol>
   <div class="land-actions"><UiButton v-if="v.signing.can_return" variant="outline" :disabled="saving" @click="returnOpen=v">Trả lại</UiButton><UiButton v-if="v.signing.can_sign" :disabled="saving" @click="sign(v)">Ký duyệt chi</UiButton></div>
  </article>
 </section>

 <template v-else-if="tab==='overview'&&overview">
  <p v-if="!overview.enabled" class="notice" role="status">Ghi sổ kế toán từ Lotus đang tắt. Kế toán trưởng vào <a href="#" @click.prevent="go('settings')">Thiết lập</a> để áp dụng hệ thống tài khoản Thông tư 99, chọn tài khoản, ngày bắt đầu ghi sổ rồi bật.</p>
  <p v-for="e in overview.mapping_errors.slice(0,4)" :key="e" class="land-warn">{{e}}</p>
  <div class="land-stats fin-stats">
   <div><span>Tiền mặt</span><strong>{{vnd(tiles.cash)}}</strong></div>
   <div><span>Tiền gửi ngân hàng</span><strong>{{vnd(tiles.bank)}}</strong></div>
   <button type="button" @click="go('payables')"><span>Phải trả nhà cung cấp</span><strong>{{vnd(tiles.payable_supplier)}}</strong><small>hàng về chưa có hóa đơn {{vnd(tiles.received_not_billed)}}</small></button>
   <div><span>Phải trả người lao động</span><strong>{{vnd(tiles.payable_employee)}}</strong><small>bảo hiểm phải nộp {{vnd(tiles.insurance)}}</small></div>
   <div><span>Chi phí tháng này</span><strong>{{vnd(tiles.month_cost)}}</strong><small>sản xuất + quản lý</small></div>
  </div>
  <section class="land-card"><h3>Việc cần làm</h3>
   <ul class="fin-todo">
    <li><button type="button" @click="go('pending')"><b>{{overview.pending_counts.receipts}}</b> phiếu nhận hàng chưa có hóa đơn</button></li>
    <li><button type="button" @click="go('pending')"><b>{{overview.pending_counts.payroll}}</b> bảng lương đã ký chưa ghi sổ</button></li>
    <li><button type="button" @click="go('pending')"><b>{{overview.pending_counts.issues}}</b> dòng xuất kho chưa gắn lô</button></li>
    <li><button type="button" @click="go('pending')"><b>{{overview.pending_counts.harvests||0}}</b> lô thu hoạch chưa nhập kho</button></li>
    <li><button type="button" @click="go('cash')"><b>{{overview.pending_counts.vouchers}}</b> phiếu chi đang chờ ký</button></li>
   </ul></section>
 </template>

 <template v-else-if="tab==='pending'&&pendingData">
  <section class="land-card">
   <div class="land-card__head"><h3>Phiếu nhận hàng chưa có hóa đơn</h3><UiButton v-if="overview?.can_post" :disabled="!picked.size||pickedSupplier.length!==1" :title="pickedSupplier.length>1?'Chọn phiếu của cùng một nhà cung cấp':''" @click="invoice={bill_no:'',bill_date:today,due_date:'',vat_code:'KCT'};ensureVat();invoiceOpen=true">Lập hóa đơn ({{picked.size}})</UiButton></div>
   <div class="land-table fin-table"><DataTable :rows="receiptRows" :columns="receiptColumns" row-key="name" storage-key="fin-receipts" interactive empty="Mọi phiếu nhận hàng đã có hóa đơn." @open="r=>togglePick(r.name)"/></div>
  </section>
  <section class="land-card"><h3>Bảng lương đã ký, chưa ghi sổ</h3>
   <div class="land-table fin-table"><DataTable :rows="pendingData.payroll" :columns="payrollPendingColumns" row-key="name" storage-key="fin-payroll-pending" interactive empty="Không có bảng lương chờ ghi sổ." @open="r=>previewPayroll(r.name)"/></div>
  </section>
  <section class="land-card"><h3>Xuất kho chưa gắn lô</h3><p class="land-note">Chi phí của các dòng này chưa vào lô nào. Sửa ô "Khu vực / lô sử dụng" thành mã lô trong danh sách khi lập phiếu.</p>
   <div class="land-table fin-table"><DataTable :rows="keyed(pendingData.issues)" :columns="issueColumns" row-key="__key" storage-key="fin-issues" interactive empty="Mọi dòng xuất kho đã gắn lô." @open="r=>openWarehouse(r.name)"/></div>
  </section>
  <section class="land-card"><h3>Lô thu hoạch chưa nhập kho</h3><p class="land-note">Nhập kho theo giá thành tạm tính / kg (giá thành thực tế tháng trước của lô, chưa có thì giá kế hoạch ở Thiết lập): Nợ 155 / Có 154. Cuối tháng tính lại giá thành thực tế.</p>
   <div class="land-table fin-table"><DataTable :rows="pendingData.harvests||[]" :columns="harvestColumns" row-key="name" storage-key="fin-harvests" empty="Mọi lô thu hoạch đã nhập kho."/></div>
  </section>
 </template>

 <section v-else-if="tab==='journal'" class="land-card">
  <div class="land-filters"><label>Từ<DatePicker v-model="range.from"/></label><label>Đến<DatePicker v-model="range.to"/></label><UiButton variant="outline" @click="load">Xem</UiButton><span class="land-spacer"></span><span class="land-count">{{journalRows.length}} chứng từ</span></div>
  <details v-for="v in journalRows" :key="v.voucher_no" class="fin-entry"><summary><span>{{vnDate(v.posting_date)}}</span><b>{{v.voucher_no}}</b><span>{{v.source.purpose?v.source.doctype+' '+v.source.name:v.voucher_type}}</span><strong>{{vnd(v.amount)}}</strong></summary>
   <DataTable :rows="keyed(v.lines)" :columns="lineColumns" row-key="__key" storage-key="fin-journal-lines"/></details>
  <p v-if="!journalRows.length&&!busy" class="land-empty">Không có chứng từ trong khoảng ngày này.</p>
 </section>

 <template v-else-if="tab==='sales'&&salesData">
  <div class="land-filters"><span class="land-count">Sổ cái 131: {{vnd(salesData.gl_total)}}</span><span class="land-spacer"></span>
   <template v-if="overview?.can_post"><UiButton variant="outline" @click="openCustomer()">Thêm khách hàng</UiButton><UiButton @click="openSale">Lập hóa đơn bán</UiButton></template></div>
  <section class="land-card"><h3>Khách hàng</h3>
   <div class="land-table fin-table"><DataTable :rows="salesData.customers" :columns="customerColumns" row-key="customer" storage-key="fin-customers" empty="Chưa có khách hàng. Bấm Thêm khách hàng."/></div>
  </section>
  <section class="land-card"><h3>Hóa đơn còn phải thu</h3>
   <div class="land-table fin-table"><DataTable :rows="salesData.invoices" :columns="receivableColumns" row-key="name" storage-key="fin-receivables" empty="Không có hóa đơn còn phải thu."/></div>
  </section>
  <section class="land-card"><h3>Hóa đơn bán gần đây</h3><p class="land-note">Hóa đơn bán xuất kho luôn: Nợ 632 / Có 155 theo giá trị tồn kho, Nợ 131 / Có 511 (và 33311 nếu có thuế). Chuối của vườn tự trồng bán ra không chịu thuế GTGT (KCT).</p>
   <div class="land-table fin-table"><DataTable :rows="salesData.recent" :columns="salesInvoiceColumns" row-key="name" storage-key="fin-sales-invoices" empty="Chưa có hóa đơn bán."/></div>
  </section>
 </template>

 <template v-else-if="tab==='payables'&&payData">
  <div class="land-filters"><span class="land-count">Sổ cái 331: {{vnd(payData.gl_total)}}</span><span class="land-spacer"></span><UiButton variant="outline" @click="exportReport('payables')"><LotusIcon name="download"/>Xuất Excel</UiButton><UiButton v-if="overview?.can_post" variant="outline" @click="openService">Hóa đơn dịch vụ / chi phí</UiButton></div>
  <section class="land-card"><h3>Theo nhà cung cấp</h3>
   <div class="land-table fin-table"><DataTable :rows="payData.suppliers" :columns="supplierColumns" row-key="supplier" storage-key="fin-suppliers" empty="Chưa có công nợ nhà cung cấp."/></div>
  </section>
  <section class="land-card"><h3>Hóa đơn còn nợ</h3>
   <div class="land-table fin-table"><DataTable :rows="payData.invoices" :columns="invoiceColumns" row-key="name" storage-key="fin-open-invoices" empty="Không có hóa đơn còn nợ."/></div>
  </section>
 </template>

 <template v-else-if="tab==='cash'&&cash">
  <div v-if="overview?.can_post" class="land-filters"><span class="land-spacer"></span><UiButton variant="outline" @click="openAdvance">Tạm ứng lương</UiButton><UiButton variant="outline" @click="openStatutory">Nộp BH, KPCĐ, thuế TNCN</UiButton></div>
  <section v-if="mine.length" class="land-card"><h3>Chờ bạn ký</h3>
   <article v-for="v in mine" :key="v.name" class="fin-voucher"><header><b>{{v.kind}} · {{v.party_name}}</b><strong>{{vnd(v.amount)}}</strong></header><small>{{v.name}} · {{vnDate(v.posting_date)}}</small>
    <div class="land-actions"><UiButton v-if="v.signing.can_return" variant="outline" :disabled="saving" @click="returnOpen=v">Trả lại</UiButton><UiButton v-if="v.signing.can_sign" :disabled="saving" @click="sign(v)">Ký</UiButton></div></article>
  </section>
  <section v-if="cash.salary_ready.length" class="land-card"><h3>Lương đã ghi sổ, chưa chi</h3>
   <div class="land-table fin-table"><DataTable :rows="cash.salary_ready" :columns="salaryReadyColumns" row-key="period" storage-key="fin-salary-ready"/></div>
  </section>
  <section class="land-card"><h3>Phiếu chi</h3>
   <div class="land-table fin-table"><DataTable :rows="cash.vouchers" :columns="voucherColumns" row-key="name" storage-key="fin-vouchers" empty="Chưa có phiếu chi nào lập từ Lotus."/></div>
  </section>
 </template>

 <template v-else-if="tab==='reports'">
  <div class="land-filters">
   <div class="land-views" role="group" aria-label="Báo cáo"><button v-for="[id,label] in REPORTS" :key="id" type="button" :class="{on:report===id}" :aria-pressed="report===id" @click="report=id">{{label}}</button></div>
   <label>Từ<DatePicker v-model="range.from"/></label><label>Đến<DatePicker v-model="range.to"/></label>
   <UiSelect v-if="report==='costs'" v-model="groupBy" aria-label="Nhóm theo" class="fin-narrow"><option value="lotus_farm">Theo vườn</option><option value="lotus_farm_block">Theo lô</option><option value="lotus_crop_cycle">Theo vụ</option><option value="lotus_work_type">Theo công việc</option></UiSelect>
   <UiSelect v-if="report==='ledger'" v-model="ledgerAccount" aria-label="Tài khoản" class="fin-wide"><option value="">Chọn tài khoản…</option><option v-for="a in lookups?.accounts||[]" :key="a.name" :value="a.name">{{a.name}}</option></UiSelect>
   <UiButton variant="outline" @click="run(loadReport)">Xem</UiButton>
   <UiButton v-if="report!=='reconciliation'" variant="outline" :disabled="report==='ledger'&&!ledgerAccount" @click="exportReport(report)"><LotusIcon name="download"/>Xuất Excel</UiButton>
  </div>
  <section v-if="report==='trial_balance'&&reportData?.rows" class="land-card">
   <div class="land-card__head"><h3>Bảng cân đối phát sinh {{vnDate(reportData.from_date)}} – {{vnDate(reportData.to_date)}}</h3><span :class="reportData.balanced?'fin-ok':'land-bad'">{{reportData.balanced?'Cân Nợ = Có':'Lệch Nợ / Có'}}</span></div>
   <div class="land-table fin-table"><DataTable :rows="reportData.rows" :columns="tbColumns" :pinned-bottom-rows="tbTotals" row-key="account" storage-key="fin-trial-balance" interactive empty="Không có phát sinh trong kỳ." @open="r=>{ledgerAccount=r.account;report='ledger'}"/></div>
   <p class="land-note">Bấm một tài khoản để xem sổ chi tiết.</p>
  </section>
  <section v-else-if="report==='ledger'" class="land-card">
   <p v-if="!reportData" class="land-empty">Chọn một tài khoản để xem sổ chi tiết.</p>
   <template v-else><h3>{{reportData.account_label||reportData.account}}</h3><p class="land-note">Số dư đầu kỳ {{vnd(reportData.opening)}} · cuối kỳ {{vnd(reportData.closing)}}</p>
    <div class="land-table fin-table"><DataTable :rows="ledgerRows" :columns="ledgerColumns" row-key="__key" storage-key="fin-ledger" empty="Không có phát sinh trong kỳ."/></div></template>
  </section>
  <template v-else-if="report==='costs'&&reportData?.rows">
   <LotusChart v-if="costChart.length" :title="'Chi phí sản xuất theo '+(groupBy==='lotus_farm'?'vườn':groupBy==='lotus_farm_block'?'lô':groupBy==='lotus_crop_cycle'?'vụ':'công việc')+' (10 lớn nhất)'" kind="hbar"
    :categories="costChart.map(r=>r.label)" :series="[{name:'Vật tư',data:costChart.map(r=>r.materials)},{name:'Nhân công',data:costChart.map(r=>Number(r.labour)+Number(r.crews))},{name:'Dịch vụ',data:costChart.map(r=>r.services)}]" unit="đ" :height="320"/>
   <section class="land-card"><div class="land-table fin-table"><DataTable :rows="costRows" :columns="costColumns" :pinned-bottom-rows="costTotals" row-key="__key" storage-key="fin-costs" empty="Chưa có chi phí sản xuất trong khoảng ngày này."/></div></section>
  </template>
  <section v-else-if="report==='costing'&&reportData?.rows" class="land-card">
   <div class="land-card__head"><h3>Giá thành chuối tháng {{reportData.month.slice(5)}}/{{reportData.month.slice(0,4)}}</h3><span :class="reportData.posted?'fin-ok':'land-warn'">{{reportData.posted?'Đã tính giá thành':reportData.closed?'Chưa tính giá thành':'Chưa kết chuyển chi phí'}}</span></div>
   <p class="land-note">Tháng lấy theo ngày "Đến". Bảng xem trước tính lại từ sổ cái; tháng đã tính thì bảng đã lưu nằm trong lịch sử bên dưới.</p>
   <div class="land-table fin-table"><DataTable :rows="costingRows(reportData)" :columns="costingColumns" :pinned-bottom-rows="costingTotals(reportData)" row-key="__key" storage-key="fin-costing" empty="Tháng này không có chi phí dở dang hay sản lượng thu hoạch."/></div>
   <details v-if="reportData.runs?.length"><summary>Các tháng đã tính giá thành</summary><ul class="fin-list"><li v-for="r in reportData.runs" :key="r.name">{{r.month.slice(5)}}/{{r.month.slice(0,4)}} · {{num(r.kg_harvested,1)}} kg · giá thành {{vnd(r.absorbed)}} · chênh lệch {{vnd(r.adjustment)}} · {{r.state==='Posted'?'đang dùng':'đã đảo'}}{{r.voucher?' · '+r.voucher:''}}</li></ul></details>
  </section>
  <template v-else-if="report==='vat'&&reportData?.summary">
   <section class="land-card"><div class="land-card__head"><h3>Thuế GTGT tháng {{reportData.month.slice(5)}}/{{reportData.month.slice(0,4)}}</h3><UiButton variant="outline" @click="exportVat"><LotusIcon name="download"/>Xuất bảng kê Excel</UiButton></div>
    <div class="land-stats fin-stats"><div><span>Thuế GTGT đầu vào</span><strong>{{vnd(reportData.summary.input_tax)}}</strong></div><div><span>Thuế GTGT đầu ra</span><strong>{{vnd(reportData.summary.output_tax)}}</strong></div>
     <div><span>{{reportData.summary.payable>=0?'Phải nộp':'Còn được khấu trừ'}}</span><strong>{{vnd(Math.abs(reportData.summary.payable))}}</strong></div><div><span>Doanh thu không chịu thuế</span><strong>{{vnd(reportData.summary.exempt_sales)}}</strong></div></div>
    <p class="land-note">Tháng lấy theo ngày "Đến". Số liệu tham khảo để lập tờ khai 01/GTGT trên HTKK / eTax (chưa trừ số còn được khấu trừ của kỳ trước).</p>
    <div class="land-table fin-table"><DataTable :rows="reportData.checks" :columns="vatCheckColumns" row-key="label" storage-key="fin-vat-checks"/></div></section>
   <section class="land-card"><h3>Bảng kê hóa đơn mua vào</h3><div class="land-table fin-table"><DataTable :rows="reportData.purchases" :columns="vatPurchaseColumns" row-key="name" storage-key="fin-vat-purchases" empty="Không có hóa đơn mua trong tháng."/></div></section>
   <section class="land-card"><h3>Bảng kê hóa đơn bán ra</h3><div class="land-table fin-table"><DataTable :rows="reportData.sales" :columns="vatSalesColumns" row-key="name" storage-key="fin-vat-sales" empty="Không có hóa đơn bán trong tháng."/></div></section>
  </template>
  <section v-else-if="report==='reconciliation'&&reportData?.checks" class="land-card"><h3>Đối chiếu sổ kế toán với nghiệp vụ Lotus ({{vnDate(reportData.on_date)}})</h3>
   <div class="land-table fin-table"><DataTable :rows="reportData.checks" :columns="reconColumns" row-key="label" storage-key="fin-reconciliation"/></div>
  </section>
 </template>

 <FinanceGuide v-else-if="tab==='guide'" @go="go"/>

 <template v-else-if="tab==='settings'&&settings">
  <section class="land-card"><h3>Hệ thống tài khoản</h3>
   <p v-if="settings.coa_version" class="land-note">Đã áp dụng {{settings.coa_version}} lúc {{vnDate(settings.coa_applied_at.slice(0,10))}} ({{settings.coa_applied_by}}).</p>
   <p v-else class="land-note">Chưa áp dụng. Xem trước để kiểm tra danh mục tài khoản Thông tư 99, tài khoản kho và bút toán chuyển số dư từ hệ thống tài khoản cũ.</p>
   <div class="land-actions fin-left"><UiButton variant="outline" @click="previewCoa">Xem trước áp dụng Thông tư 99</UiButton></div>
   <template v-if="coa">
    <p>{{coa.name}} — thêm <b>{{coa.add.length}}</b>, sửa tên / loại <b>{{coa.update.length}}</b>, xóa <b>{{coa.retire.filter(r=>r.action==='delete').length}}</b>, ngừng dùng <b>{{coa.retire.filter(r=>r.action==='disable').length}}</b> tài khoản (tài khoản đã có bút toán không xóa được, chỉ ngừng dùng).</p>
    <details v-if="coa.update.length"><summary>Tài khoản đổi tên theo Thông tư 99</summary><ul class="fin-list"><li v-for="u in coa.update" :key="u.account">{{u.number}}: {{u.old_name}} → <b>{{u.name}}</b></li></ul></details>
    <details v-if="coa.retire.length"><summary>Tài khoản không có trong Thông tư 99</summary><ul class="fin-list"><li v-for="r in coa.retire" :key="r.account">{{r.label}} — {{r.action==='delete'?'xóa':'ngừng dùng'}}</li></ul></details><p class="land-note">{{coa.note}}</p>
    <p v-for="e in coa.errors" :key="e" class="land-bad">{{e}}</p>
    <div class="land-table land-preview"><DataTable :rows="coa.transfer" :columns="transferColumns" row-key="old" storage-key="fin-coa-transfer" empty="Không có số dư cần chuyển."/></div>
    <p class="land-note">Kho: {{coa.warehouses.map(w=>w.warehouse).join(', ')}} → {{coa.warehouses[0]?.account}}</p>
    <div class="land-actions"><UiButton :disabled="saving||!!coa.errors.length||!settings.is_chief" @click="applyCoa">Áp dụng Thông tư 99</UiButton></div>
   </template>
  </section>
  <section class="land-card"><h3>Tài khoản theo nghiệp vụ và bật ghi sổ</h3>
   <p v-for="e in settings.errors" :key="e" class="land-warn">{{e}}</p>
   <form class="land-form--grid" @submit.prevent="saveSettings">
    <label v-for="k in settings.keys" :key="k.key">{{k.label}}<UiSelect v-model="form.mapping[k.key]" :disabled="!settings.is_chief"><option value="">Chưa chọn</option><option v-for="a in accountsFor(k.key)" :key="a.name" :value="a.name">{{accountLabel(a)}}</option></UiSelect></label>
    <label>Ngày bắt đầu ghi sổ (cutover)<DatePicker v-model="form.cutover_date" :disabled="!settings.is_chief"/></label>
    <label>Giá thành kế hoạch chuối thu hoạch (đ / kg)<UiInput v-model="form.harvest_standard_cost" type="number" min="0" :disabled="!settings.is_chief" placeholder="Dùng khi lô chưa có giá thành thực tế"/></label>
    <label>Vùng lương tối thiểu (trần BHTN)<UiSelect v-model="form.minimum_wage_region" :disabled="!settings.is_chief"><option value="">Chưa chọn (không áp trần BHTN)</option><option v-for="v in ['I','II','III','IV']" :key="v" :value="v">Vùng {{v}}</option></UiSelect></label>
    <label class="fin-check"><input v-model="form.enabled" type="checkbox" :disabled="!settings.is_chief">Bật ghi sổ kế toán từ Lotus</label>
    <div v-if="settings.is_chief" class="land-actions land-form__full"><UiButton type="submit" :disabled="saving">Lưu</UiButton></div>
   </form>
  </section>
  <section class="land-card"><div class="land-card__head"><h3>Kết chuyển và khóa sổ theo tháng</h3><UiSelect v-model.number="year" aria-label="Năm" class="fin-narrow"><option v-for="y in [Number(today.slice(0,4))-1,Number(today.slice(0,4)),Number(today.slice(0,4))+1]" :key="y" :value="y">Năm {{y}}</option></UiSelect></div>
   <p class="land-warn">Thứ tự cuối tháng: ghi sổ lương → kết chuyển chi phí (Kết chuyển CP) → tính giá thành (Giá thành) → kiểm tra Đối chiếu → Khóa. Đã khóa thì không kết chuyển hay tính giá thành được nữa.</p>
   <div class="fin-months"><div v-for="m in months" :key="m" class="fin-month" :class="{closed:periodOf(m)?.closed}"><b>{{m.slice(5)}}/{{m.slice(0,4)}}</b><small>{{periodOf(m)?.closed?'Đã khóa':'Đang mở'}}</small>
    <UiButton size="sm" variant="ghost" @click="previewClosing(m)">Kết chuyển CP</UiButton><UiButton size="sm" variant="ghost" @click="previewCosting(m)">Giá thành</UiButton>
    <template v-if="settings.is_chief"><UiButton v-if="!periodOf(m)?.closed" size="sm" variant="outline" @click="closeMonth(m)">Khóa</UiButton><UiButton v-else size="sm" variant="ghost" @click="reopenMonth(m)">Mở lại</UiButton></template></div></div>
  </section>
  <section v-if="settings.payroll_params" class="land-card"><h3>Tham số lương theo pháp luật</h3>
   <p class="land-note">{{settings.payroll_params.note}}</p>
   <ul class="fin-list"><li v-for="r in settings.payroll_params.rows" :key="r.group+r.from" :class="{'fin-muted':r.confirmed===false}"><b>{{paramGroups[r.group]}} từ {{vnDate(r.from)}}{{r.confirmed===false?' (chưa xác nhận, chưa áp dụng)':''}}</b>: {{paramSummary(r)}}<br><small>{{r.source}}</small></li></ul>
  </section>
  <section class="land-card"><h3>Người làm kế toán</h3>
   <p class="land-note">Kế toán: lập hóa đơn, phiếu chi, ghi sổ lương. Kế toán trưởng: ký phiếu chi, đảo bút toán, kết chuyển, khóa sổ, cấu hình. Kiểm soát: chỉ xem. {{staff?.can_assign?'':'Chỉ Quản trị hệ thống được gán vai trò.'}}</p>
   <div class="land-table fin-table"><DataTable :rows="staff?.people||[]" :columns="peopleColumns" row-key="user" storage-key="fin-people" empty="Chưa có tài khoản nhân sự."/></div>
  </section>
  <section v-if="settings.is_chief" class="land-card"><div class="land-card__head"><h3>Bút toán điều chỉnh (phiếu kế toán khác)</h3><UiButton variant="ghost" size="sm" @click="openLedger(settings.mapping.stock_adjustment)">Xem sổ chi tiết 3381</UiButton></div>
   <p class="land-note">Dùng cho nghiệp vụ không có chứng từ Lotus: phân loại lại số dư treo (VD 3381), điều chỉnh sai sót. Nợ phải bằng Có; tài khoản công nợ cần ghi mã đối tượng.</p>
   <div class="land-form--grid"><label>Ngày hạch toán<DatePicker v-model="adj.posting_date"/></label><label>Diễn giải<UiInput v-model="adj.remark" placeholder="VD: Phân loại lại tồn kho đầu kỳ từ 3381 sang 4111"/></label></div>
   <div class="fin-form-rows" role="list"><div class="fin-form-row fin-form-row--adj fin-form-row--head" aria-hidden="true"><span>Tài khoản</span><span>Nợ</span><span>Có</span><span>Đối tượng</span><span>Lô</span><span></span></div>
    <div v-for="(l,i) in adj.lines" :key="i" class="fin-form-row fin-form-row--adj" role="listitem">
     <UiSelect v-model="l.account" :aria-label="'Tài khoản dòng '+(i+1)"><option value="">Chọn…</option><option v-for="a in settings.accounts" :key="a.name" :value="a.name">{{accountLabel(a)}}</option></UiSelect>
     <UiInput v-model="l.debit" type="number" min="0" :aria-label="'Nợ dòng '+(i+1)"/><UiInput v-model="l.credit" type="number" min="0" :aria-label="'Có dòng '+(i+1)"/>
     <UiInput v-model="l.party" placeholder="Mã NCC / KH" :aria-label="'Đối tượng dòng '+(i+1)"/>
     <UiSelect v-model="l.lotus_farm_block" :aria-label="'Lô dòng '+(i+1)"><option value="">—</option><option v-for="b in lookups?.blocks||[]" :key="b.name" :value="b.name">{{b.block_code}}</option></UiSelect>
     <UiButton type="button" size="sm" variant="ghost" :disabled="adj.lines.length<3" @click="adj.lines.splice(i,1)">Xóa</UiButton></div></div>
   <p>Tổng Nợ {{vnd(adjDebit)}} · Tổng Có {{vnd(adjCredit)}} <span :class="adjDebit===adjCredit&&adjDebit>0?'fin-ok':'land-bad'">{{adjDebit===adjCredit&&adjDebit>0?'Cân':'Chưa cân'}}</span></p>
   <p v-for="e in adjErrors" :key="e" class="land-bad">{{e}}</p>
   <div class="land-actions fin-left"><UiButton type="button" variant="outline" @click="adj.lines.push(newAdjLine())">Thêm dòng</UiButton><span class="land-spacer"></span><UiButton :disabled="saving" variant="outline" @click="sendAdjustment(0)">Xem trước</UiButton><UiButton :disabled="saving||adjDebit!==adjCredit||!adjDebit" @click="sendAdjustment(1)">Ghi sổ</UiButton></div>
  </section>
  <section v-if="settings.is_chief" class="land-card"><h3>Số dư đầu kỳ</h3>
   <p class="land-note">Tải file mẫu, điền số dư từng tài khoản tại ngày bắt đầu ghi sổ (công nợ 331 ghi theo từng nhà cung cấp), rồi tải lên để xem trước. Tổng Dư Nợ phải bằng tổng Dư Có.</p>
   <div class="land-actions fin-left"><UiButton variant="outline" @click="downloadOpening"><LotusIcon name="download"/>File mẫu</UiButton><label class="land-file">Tải file số dư<input type="file" accept=".xlsx" :disabled="saving" @change="readOpening"></label></div>
   <template v-if="openingPreview"><p>Dư Nợ {{vnd(openingPreview.debit)}} · Dư Có {{vnd(openingPreview.credit)}} · <span :class="openingPreview.balanced?'fin-ok':'land-bad'">{{openingPreview.balanced?'Cân':'Không cân'}}</span> · {{openingPreview.errors}} dòng lỗi · ngày {{vnDate(openingPreview.on_date)}}</p>
    <div class="land-table land-preview"><DataTable :rows="openingPreview.rows" :columns="openingColumns" row-key="line" storage-key="fin-opening"/></div>
    <div class="land-actions"><UiButton :disabled="saving||!openingPreview.balanced||openingPreview.errors>0||openingPreview.existing" :title="openingPreview.existing?'Đã có bút toán số dư đầu kỳ':''" @click="commitOpening">Ghi số dư đầu kỳ</UiButton></div></template>
  </section>
 </template>

 <WorkspaceModal v-model="invoiceOpen" title="Hóa đơn nhà cung cấp" :busy="saving" width="560px">
  <form class="land-form" @submit.prevent="makeInvoice"><p>{{pickedReceipts.length}} phiếu nhận · {{pickedReceipts[0]?.supplier_name}} · {{vnd(pickedReceipts.reduce((s,r)=>s+Number(r.to_bill||0),0))}}</p>
   <label>Số hóa đơn<UiInput v-model="invoice.bill_no" required/></label><label>Ngày hóa đơn<DatePicker v-model="invoice.bill_date" required/></label><label>Hạn thanh toán<DatePicker v-model="invoice.due_date"/></label>
   <label>Thuế suất GTGT<UiSelect v-model="invoice.vat_code"><option v-for="r in vatOptions?.rates||[]" :key="r.code" :value="r.code">{{r.label}}</option></UiSelect></label>
   <p class="land-note">Ghi Nợ hàng về chưa có hóa đơn / Có phải trả người bán; thuế GTGT đầu vào Nợ 1331.</p>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="invoiceOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!invoice.bill_no">Ghi hóa đơn</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal :model-value="!!payrollView" title="Bút toán lương" :busy="saving" width="980px" @update:model-value="v=>{if(!v)payrollView=null}">
  <div v-if="payrollView" class="land-form">
   <p>Tháng {{payrollView.month}} · {{payrollView.people}} người · {{payrollView.crews}} đội khoán · ngày hạch toán {{vnDate(payrollView.posting_date)}}</p>
   <p class="land-note">Tổng lương {{vnd(payrollView.totals.gross)}} · bảo hiểm doanh nghiệp {{vnd(payrollView.totals.employer_insurance)}} · KPCĐ {{vnd(payrollView.totals.union_fee)}} · thuế TNCN khấu trừ {{vnd(payrollView.totals.pit)}} · khoán {{vnd(payrollView.totals.crews)}} · thực nhận {{vnd(payrollView.totals.net)}}. {{payrollView.indirect.length}} người không có công ở lô nào được tính chi phí quản lý.</p>
   <p v-for="i in payrollView.issues" :key="i" class="land-bad">{{i}}</p>
   <div class="land-table land-preview"><DataTable :rows="keyed(payrollView.lines)" :columns="payrollLineColumns" row-key="__key" storage-key="fin-payroll-lines"/></div>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="payrollView=null">Đóng</UiButton><UiButton v-if="overview?.can_post&&!payrollView.posted" :disabled="saving||!!payrollView.issues.length||!overview?.enabled" @click="postPayroll">Ghi sổ</UiButton></div>
  </div>
 </WorkspaceModal>

 <WorkspaceModal :model-value="!!closingView" title="Kết chuyển chi phí sản xuất sang 154" :busy="saving" width="980px" @update:model-value="v=>{if(!v)closingView=null}">
  <div v-if="closingView" class="land-form">
   <p>Tháng {{closingView.month}} · ngày hạch toán {{vnDate(closingView.posting_date)}} · tổng kết chuyển <b>{{vnd(closingView.total)}}</b></p>
   <p v-if="closingView.posted" class="land-warn">Tháng này đã kết chuyển ({{closingView.posted.voucher}}).</p>
   <div class="land-table land-preview"><DataTable :rows="keyed(closingView.lines)" :columns="payrollLineColumns" row-key="__key" storage-key="fin-closing-lines" empty="Không có chi phí 621 / 622 / 627 trong tháng."/></div>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="closingView=null">Đóng</UiButton><UiButton v-if="settings?.is_chief&&!closingView.posted" :disabled="saving||!closingView.lines.length||!settings?.enabled" @click="postClosing">Ghi sổ kết chuyển</UiButton></div>
  </div>
 </WorkspaceModal>

 <WorkspaceModal :model-value="!!costingView" title="Tính giá thành chuối" :busy="saving" width="1180px" @update:model-value="v=>{if(!v)costingView=null}">
  <div v-if="costingView" class="land-form">
   <p>Tháng {{costingView.month}} · ngày hạch toán {{vnDate(costingView.posting_date)}} · {{num(costingView.totals.kg_harvested,1)}} kg thu · giá thành sản lượng <b>{{vnd(costingView.totals.absorbed)}}</b> · chênh lệch so với tạm tính <b>{{vnd(costingView.totals.adjustment)}}</b></p>
   <p class="land-note">Mỗi lô: (dở dang đầu kỳ + chi phí tháng) × kg thu ÷ (kg thu + kg dự thu còn lại). Chi phí chung của vườn (không gắn lô) chia theo kg của cả vườn. Chênh lệch dương ghi Nợ 632 / Có 154, âm ghi ngược lại.</p>
   <p v-if="!costingView.closed" class="land-warn">Chưa kết chuyển chi phí 621 / 622 / 627 sang 154 của tháng này. Bấm "Kết chuyển CP" trước.</p>
   <p v-if="costingView.posted?.voucher" class="land-warn">Tháng này đã tính giá thành ({{costingView.posted.voucher}}). Đảo bút toán đó nếu cần tính lại.</p>
   <div class="land-table land-preview"><DataTable :rows="costingRows(costingView)" :columns="costingColumns" :pinned-bottom-rows="costingTotals(costingView)" row-key="__key" storage-key="fin-costing-preview" empty="Tháng này không có chi phí dở dang hay sản lượng thu hoạch."/></div>
   <details v-if="costingView.lines.length"><summary>Bút toán chênh lệch ({{costingView.lines.length}} dòng)</summary><DataTable :rows="keyed(costingView.lines)" :columns="payrollLineColumns" row-key="__key" storage-key="fin-costing-lines"/></details>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="costingView=null">Đóng</UiButton><UiButton v-if="settings?.is_chief&&!costingView.posted?.voucher" :disabled="saving||!costingView.closed||!costingView.rows.length||!settings?.enabled" @click="postCosting">Ghi sổ giá thành</UiButton></div>
  </div>
 </WorkspaceModal>

 <WorkspaceModal v-model="payOpen" title="Phiếu chi trả nhà cung cấp" :busy="saving" width="760px">
  <form class="land-form" @submit.prevent="preparePay">
   <div class="fin-form-rows" role="list"><div class="fin-form-row fin-form-row--head" aria-hidden="true"><span>Hóa đơn</span><span>Hạn</span><span class="num">Còn nợ</span><span class="num">Trả lần này</span></div>
    <div v-for="i in supplierInvoices" :key="i.name" class="fin-form-row" role="listitem"><b>{{i.bill_no||i.name}}</b><span>{{vnDate(i.due_date)}}</span><span class="num">{{vnd(i.outstanding_amount-(i.paying||0))}}</span><UiInput v-model="pay.allocations[i.name]" type="number" min="0" :aria-label="'Trả hóa đơn '+(i.bill_no||i.name)"/></div></div>
   <p>Tổng chi: <b>{{vnd(payTotal)}}</b></p>
   <div class="land-form--grid"><label>Hình thức<UiSelect v-model="pay.mode"><option value="cash">Tiền mặt (phiếu chi)</option><option value="bank">Chuyển khoản (ủy nhiệm chi)</option></UiSelect></label><label>Ngày chi<DatePicker v-model="pay.posting_date"/></label>
    <label v-if="pay.mode==='bank'" class="land-form__full">Số ủy nhiệm chi / giao dịch<UiInput v-model="pay.reference_no" required/></label></div>
   <SignerPicker v-model="signers" :options="signerOptions" :disabled="saving"/>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="payOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!payTotal">Lập phiếu và gửi ký</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal :model-value="!!salaryOpen" title="Phiếu chi lương" :busy="saving" width="640px" @update:model-value="v=>{if(!v)salaryOpen=null}">
  <form v-if="salaryOpen" class="land-form" @submit.prevent="prepareSalary"><p>Tháng {{salaryOpen.month}} · thực lĩnh {{vnd(salaryOpen.net)}} · đã tạm ứng {{vnd(salaryOpen.advance)}} · chi lần này <b>{{vnd(salaryOpen.to_pay)}}</b></p>
   <div class="land-form--grid"><label>Hình thức<UiSelect v-model="salary.mode"><option value="bank">Chuyển khoản</option><option value="cash">Tiền mặt</option></UiSelect></label><label>Ngày chi<DatePicker v-model="salary.posting_date"/></label>
    <label v-if="salary.mode==='bank'" class="land-form__full">Số ủy nhiệm chi<UiInput v-model="salary.reference_no"/></label></div>
   <SignerPicker v-model="signers" :options="signerOptions" :disabled="saving"/>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="salaryOpen=null">Hủy</UiButton><UiButton type="submit" :disabled="saving">Lập phiếu và gửi ký</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal v-model="customerOpen" title="Khách hàng" :busy="saving" width="560px">
  <form class="land-form" @submit.prevent="saveCustomer">
   <label>Tên khách hàng<UiInput v-model="customer.customer_name" required/></label><label>Mã số thuế<UiInput v-model="customer.tax_id" inputmode="numeric"/></label>
   <label>Địa chỉ<UiInput v-model="customer.address"/></label><label>Hạn thanh toán (ngày)<UiInput v-model="customer.credit_days" type="number" min="0"/></label>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="customerOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!customer.customer_name">Lưu</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal v-model="saleOpen" title="Hóa đơn bán hàng (xuất kho)" :busy="saving" width="1080px">
  <form class="land-form" @submit.prevent="saveSale">
   <div class="land-form--grid"><label>Khách hàng<UiSelect v-model="sale.customer" required><option value="">Chọn…</option><option v-for="c in lookups?.customers||[]" :key="c.name" :value="c.name">{{c.customer_name}}{{c.tax_id?' · '+c.tax_id:''}}</option></UiSelect></label>
    <label>Ngày hóa đơn<DatePicker v-model="sale.posting_date"/></label><label>Hạn thu<DatePicker v-model="sale.due_date"/></label>
    <label>Thuế suất GTGT<UiSelect v-model="sale.vat_code"><option v-for="r in vatOptions?.rates||[]" :key="r.code" :value="r.code">{{r.label}}</option></UiSelect></label>
    <label>Ký hiệu hóa đơn điện tử<UiInput v-model="sale.einvoice_series" placeholder="VD: 1C26TLT"/></label><label>Số hóa đơn điện tử<UiInput v-model="sale.einvoice_no"/></label></div>
   <div class="fin-form-rows" role="list"><div class="fin-form-row fin-form-row--sale fin-form-row--head" aria-hidden="true"><span>Hàng · kho</span><span class="num">Tồn</span><span>Số lượng</span><span>Đơn giá</span><span>Lô hàng (batch)</span><span></span></div>
    <div v-for="(l,i) in sale.lines" :key="i" class="fin-form-row fin-form-row--sale" role="listitem">
     <UiSelect v-model="l.stock" :aria-label="'Hàng dòng '+(i+1)"><option value="">Chọn…</option><option v-for="s in saleStock" :key="stockKey(s)" :value="stockKey(s)">{{s.item_name}} · {{s.warehouse}}</option></UiSelect>
     <span class="num">{{stockOf(l)?num(stockOf(l).actual_qty,2)+' '+stockOf(l).stock_uom:'—'}}</span>
     <UiInput v-model="l.qty" type="number" min="0" step="any" :aria-label="'Số lượng dòng '+(i+1)"/><UiInput v-model="l.rate" type="number" min="0" :aria-label="'Đơn giá dòng '+(i+1)"/>
     <UiSelect v-if="stockOf(l)?.has_batch_no" v-model="l.batch_no" :aria-label="'Batch dòng '+(i+1)"><option value="">Chọn…</option><option v-for="b in stockOf(l).batches||[]" :key="b.name" :value="b.name">{{b.name}} ({{num(b.qty,2)}})</option></UiSelect><span v-else>—</span>
     <UiButton type="button" size="sm" variant="ghost" :disabled="sale.lines.length<2" @click="sale.lines.splice(i,1)">Xóa</UiButton></div></div>
   <p v-if="!saleStock.length" class="land-warn">Chưa có hàng trong kho thành phẩm (TK 155). Nhập kho chuối thu hoạch hoặc kết quả đóng gói trước.</p>
   <p>Chưa thuế {{vnd(saleNet)}} · thuế GTGT {{vnd(saleTax)}} · tổng <b>{{vnd(saleNet+saleTax)}}</b></p>
   <div class="land-actions fin-left"><UiButton type="button" variant="outline" @click="sale.lines.push(newSaleLine())">Thêm dòng</UiButton><span class="land-spacer"></span>
    <UiButton type="button" variant="outline" :disabled="saving" @click="saleOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!sale.customer||!saleNet">Ghi hóa đơn</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal v-model="receiptOpen" title="Phiếu thu tiền khách hàng" :busy="saving" width="760px">
  <form class="land-form" @submit.prevent="saveReceipt"><p>{{receipt.customer_name}}</p>
   <div class="fin-form-rows" role="list"><div class="fin-form-row fin-form-row--head" aria-hidden="true"><span>Hóa đơn</span><span>Hạn</span><span class="num">Còn phải thu</span><span class="num">Thu lần này</span></div>
    <div v-for="i in receiptInvoices" :key="i.name" class="fin-form-row" role="listitem"><b>{{[i.lotus_einvoice_series,i.lotus_einvoice_no].filter(Boolean).join(' ')||i.name}}</b><span>{{vnDate(i.due_date)}}</span><span class="num">{{vnd(i.outstanding_amount)}}</span><UiInput v-model="receipt.allocations[i.name]" type="number" min="0" :aria-label="'Thu hóa đơn '+i.name"/></div></div>
   <p>Tổng thu: <b>{{vnd(receiptTotal)}}</b></p>
   <div class="land-form--grid"><label>Hình thức<UiSelect v-model="receipt.mode"><option value="bank">Chuyển khoản (báo có)</option><option value="cash">Tiền mặt (phiếu thu)</option></UiSelect></label><label>Ngày thu<DatePicker v-model="receipt.posting_date"/></label>
    <label v-if="receipt.mode==='bank'" class="land-form__full">Số giao dịch / báo có<UiInput v-model="receipt.reference_no" required/></label></div>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="receiptOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!receiptTotal">Ghi phiếu thu</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal v-model="advanceOpen" title="Phiếu tạm ứng lương" :busy="saving" width="640px">
  <form class="land-form" @submit.prevent="prepareAdvance">
   <div class="land-form--grid"><label>Nhân viên<UiSelect v-model="advance.employee" required><option value="">Chọn…</option><option v-for="e in lookups?.employees||[]" :key="e.name" :value="e.name">{{e.employee_name}} · {{e.name}}</option></UiSelect></label>
    <label>Số tiền<UiInput v-model="advance.amount" type="number" min="0" required/></label>
    <label>Trừ vào lương tháng<UiInput v-model="advance.month" type="month" required/></label>
    <label>Hình thức<UiSelect v-model="advance.mode"><option value="cash">Tiền mặt</option><option value="bank">Chuyển khoản</option></UiSelect></label>
    <label>Ngày chi<DatePicker v-model="advance.posting_date"/></label>
    <label v-if="advance.mode==='bank'">Số ủy nhiệm chi<UiInput v-model="advance.reference_no"/></label></div>
   <p class="land-note">Nợ 334 / Có 111 hoặc 112. Khi chi lương tháng đó, Lotus tự trừ số đã tạm ứng.</p>
   <SignerPicker v-model="signers" :options="signerOptions" :disabled="saving"/>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="advanceOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!advance.employee||!Number(advance.amount)">Lập phiếu và gửi ký</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal v-model="statutoryOpen" title="Nộp bảo hiểm, kinh phí công đoàn, thuế TNCN" :busy="saving" width="760px">
  <form class="land-form" @submit.prevent="prepareStatutory">
   <div class="fin-form-rows" role="list"><div class="fin-form-row fin-form-row--head" aria-hidden="true"><span>Khoản</span><span class="num">Còn phải nộp</span><span class="num">Đang chờ ký</span><span class="num">Nộp lần này</span></div>
    <div v-for="r in statutory.rows" :key="r.key" class="fin-form-row" role="listitem"><b>{{r.label}}</b><span class="num">{{vnd(r.owed)}}</span><span class="num">{{vnd(r.pending)}}</span><UiInput v-model="r.amount" type="number" min="0" :aria-label="'Nộp '+r.label"/></div></div>
   <p>Tổng nộp: <b>{{vnd(statutoryTotal)}}</b></p>
   <div class="land-form--grid"><label>Hình thức<UiSelect v-model="statutory.mode"><option value="bank">Chuyển khoản (ủy nhiệm chi)</option><option value="cash">Tiền mặt</option></UiSelect></label><label>Ngày nộp<DatePicker v-model="statutory.posting_date"/></label>
    <label v-if="statutory.mode==='bank'" class="land-form__full">Số ủy nhiệm chi<UiInput v-model="statutory.reference_no" required/></label></div>
   <SignerPicker v-model="signers" :options="signerOptions" :disabled="saving"/>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="statutoryOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!statutoryTotal">Lập phiếu và gửi ký</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal v-model="serviceOpen" title="Hóa đơn dịch vụ / chi phí" :busy="saving" width="980px">
  <form class="land-form" @submit.prevent="saveService">
   <div class="land-form--grid"><label>Nhà cung cấp<UiSelect v-model="service.supplier" required><option value="">Chọn…</option><option v-for="s in lookups?.suppliers||[]" :key="s.name" :value="s.name">{{s.supplier_name}}</option></UiSelect></label>
    <label>Số hóa đơn<UiInput v-model="service.bill_no" required/></label><label>Ngày hóa đơn<DatePicker v-model="service.bill_date"/></label><label>Hạn thanh toán<DatePicker v-model="service.due_date"/></label>
    <label>Thuế suất GTGT<UiSelect v-model="service.vat_code"><option v-for="r in vatOptions?.rates||[]" :key="r.code" :value="r.code">{{r.label}}</option></UiSelect></label></div>
   <div class="fin-form-rows" role="list"><div class="fin-form-row fin-form-row--service fin-form-row--head" aria-hidden="true"><span>Nội dung</span><span>Số tiền</span><span>Loại chi phí</span><span>Vườn</span><span>Lô</span><span></span></div>
    <div v-for="(l,i) in service.lines" :key="i" class="fin-form-row fin-form-row--service" role="listitem"><UiInput v-model="l.description" placeholder="VD: Thuê máy cày lô A1" :aria-label="'Nội dung dòng '+(i+1)"/><UiInput v-model="l.amount" type="number" min="0" :aria-label="'Số tiền dòng '+(i+1)"/>
     <UiSelect v-model="l.cost" :aria-label="'Loại chi phí dòng '+(i+1)"><option value="production">Sản xuất (vào lô)</option><option value="admin">Quản lý</option></UiSelect>
     <UiSelect v-model="l.lotus_farm" :aria-label="'Vườn dòng '+(i+1)"><option value="">—</option><option v-for="f in lookups?.farms||[]" :key="f.name" :value="f.name">{{f.farm_name||f.name}}</option></UiSelect>
     <UiSelect v-model="l.lotus_farm_block" :aria-label="'Lô dòng '+(i+1)"><option value="">—</option><option v-for="b in blocksOf(l.lotus_farm)" :key="b.name" :value="b.name">{{b.block_code}}</option></UiSelect>
     <UiButton type="button" size="sm" variant="ghost" :disabled="service.lines.length<2" @click="service.lines.splice(i,1)">Xóa</UiButton></div></div>
   <div class="land-actions fin-left"><UiButton type="button" variant="outline" @click="service.lines.push(newServiceLine())">Thêm dòng</UiButton></div>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="serviceOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!service.supplier||!service.bill_no">Ghi hóa đơn</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal :model-value="!!returnOpen" title="Trả lại phiếu chi" :busy="saving" width="520px" @update:model-value="v=>{if(!v)returnOpen=null}">
  <form class="land-form" @submit.prevent="sendBack"><label>Lý do<UiInput v-model="returnReason" required minlength="3"/></label>
   <div class="land-actions"><UiButton type="button" variant="outline" @click="returnOpen=null">Hủy</UiButton><UiButton type="submit" :disabled="saving||returnReason.trim().length<3">Trả lại</UiButton></div></form>
 </WorkspaceModal>
 <WorkspaceConfirm :open="confirmOpen" :title="confirmTitle" :message="confirmMessage" @answer="finishConfirm"/>
</section>
</template>
