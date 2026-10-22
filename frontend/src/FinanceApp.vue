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
const TABS=[['overview','Tổng quan'],['pending','Chờ hạch toán'],['journal','Nhật ký kế toán'],['payables','Công nợ phải trả'],['cash','Thu / Chi'],['reports','Báo cáo'],['settings','Thiết lập']]
const REPORTS=[['trial_balance','Bảng cân đối phát sinh'],['ledger','Sổ chi tiết tài khoản'],['costs','Chi phí theo vườn / lô'],['reconciliation','Đối chiếu']]
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
  if(tab.value==='payables'){await ensureLookups();payData.value=await call(F+'reports.payables')}
  if(tab.value==='cash'){cash.value=await call(F+'payments.vouchers');mine.value=await call(F+'payments.my_vouchers')}
  if(tab.value==='reports'){await ensureLookups();await loadReport()}
  if(tab.value==='settings')settings.value=await call(F+'api.settings')
 })
}
async function loadReport(){
 const args={from_date:range.value.from,to_date:range.value.to}
 if(report.value==='trial_balance')reportData.value=await call(F+'reports.trial_balance',args)
 if(report.value==='costs')reportData.value=await call(F+'reports.costs',{...args,group_by:groupBy.value})
 if(report.value==='reconciliation')reportData.value=await call(F+'reports.reconciliation',{on_date:range.value.to})
 if(report.value==='ledger')reportData.value=ledgerAccount.value?await call(F+'reports.ledger',{...args,account:ledgerAccount.value}):null
}
function exportReport(kind){const q={kind,from_date:range.value.from,to_date:range.value.to};if(kind==='costs')q.group_by=groupBy.value;if(kind==='ledger')q.account=ledgerAccount.value
 location.href='/api/method/lotus_farm.finance.reports.export?'+new URLSearchParams(q)}

// Pending: supplier invoice from receipts, payroll preview/post
const picked=ref(new Set()),invoiceOpen=ref(false),invoice=ref({bill_no:'',bill_date:today,due_date:''})
const pickedReceipts=computed(()=>(pendingData.value?.receipts||[]).filter(r=>picked.value.has(r.name)))
const pickedSupplier=computed(()=>[...new Set(pickedReceipts.value.map(r=>r.supplier))])
function togglePick(name){const next=new Set(picked.value);next.has(name)?next.delete(name):next.add(name);picked.value=next}
async function makeInvoice(){saving.value=true
 try{const r=await call(F+'payments.make_goods_invoice',{receipts:JSON.stringify([...picked.value]),bill_no:invoice.value.bill_no,bill_date:invoice.value.bill_date,due_date:invoice.value.due_date||null},true)
  notice.value='Đã ghi hóa đơn '+r.invoice+' ('+vnd(r.amount)+').';invoiceOpen.value=false;picked.value=new Set();await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}
const payrollView=ref(null)
async function previewPayroll(name){await ensureLookups();await run(async()=>{payrollView.value=await call(F+'payroll.preview',{period:name})})}
async function postPayroll(){saving.value=true
 try{const r=await call(F+'payroll.post',{period:payrollView.value.period,source_hash:payrollView.value.source_hash},true)
  notice.value='Đã ghi sổ lương '+payrollView.value.month+': '+r.voucher+' ('+vnd(r.amount)+').';payrollView.value=null;await load()}
 catch(e){error.value=e.message}finally{saving.value=false}}

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
const serviceOpen=ref(false),service=ref({supplier:'',bill_no:'',bill_date:today,due_date:'',lines:[]})
function newServiceLine(){return {description:'',amount:'',cost:'production',lotus_farm:'',lotus_farm_block:'',lotus_work_type:''}}
function openService(){service.value={supplier:'',bill_no:'',bill_date:today,due_date:'',lines:[newServiceLine()]};serviceOpen.value=true}
const blocksOf=farm=>(lookups.value?.blocks||[]).filter(b=>!farm||b.farm===farm)
async function saveService(){saving.value=true
 try{const r=await call(F+'payments.make_service_invoice',{supplier:service.value.supplier,bill_no:service.value.bill_no,bill_date:service.value.bill_date,due_date:service.value.due_date||null,
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
watch(settings,s=>{if(s)form.value={enabled:s.enabled,cutover_date:s.cutover_date,mapping:{...s.mapping}}})
const accountsFor=key=>{const k=(settings.value?.keys||[]).find(x=>x.key===key);return (settings.value?.accounts||[]).filter(a=>!k||k.roots.includes(a.root_type))}
async function saveSettings(){saving.value=true
 try{settings.value=await call(F+'api.save_settings',{values:JSON.stringify(form.value)},true);notice.value=settings.value.enabled?'Đã lưu. Ghi sổ kế toán đang bật.':'Đã lưu cấu hình.';overview.value=null}
 catch(e){error.value=e.message}finally{saving.value=false}}
async function previewCoa(){await run(async()=>{coa.value=await call(F+'api.coa_preview',{on_date:today})})}
async function applyCoa(){if(!await ask('Áp dụng hệ thống tài khoản Thông tư 99: thêm '+coa.value.add.length+' tài khoản, đổi tài khoản kho và chuyển số dư cũ. Không hoàn tác bằng một nút được. Tiếp tục?','Áp dụng Thông tư 99'))return
 saving.value=true
 try{const r=await call(F+'api.coa_apply',{on_date:coa.value.on_date},true);notice.value='Đã áp dụng Thông tư 99: thêm '+r.added+' tài khoản'+(r.transfer?', chuyển số dư bằng '+r.transfer:'')+'.';coa.value=null;settings.value=await call(F+'api.settings')}
 catch(e){error.value=e.message}finally{saving.value=false}}
const months=computed(()=>{const y=Number(today.slice(0,4));return Array.from({length:12},(_,i)=>y+'-'+String(i+1).padStart(2,'0'))})
const periodOf=m=>(settings.value?.periods||[]).find(p=>String(p.start_date).slice(0,7)===m)
const closingView=ref(null)
async function previewClosing(m){await ensureLookups();await run(async()=>{closingView.value=await call(F+'closing.preview',{month:m})})}
async function postClosing(){saving.value=true
 try{const r=await call(F+'closing.post',{month:closingView.value.month},true);notice.value='Đã kết chuyển chi phí tháng '+closingView.value.month+' sang 154: '+r.voucher+' ('+vnd(r.amount)+').';closingView.value=null}
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
const issueColumns=[{field:'name',headerName:'Phiếu xuất',minWidth:170},dateCol('posting_date','Ngày'),{field:'reason',headerName:'Lý do',minWidth:320,flex:3},moneyCol('amount','Giá trị')]
const lineColumns=[{field:'account',headerName:'Tài khoản',minWidth:260,flex:2,valueGetter:p=>p.data.account_label||p.data.account},moneyCol('debit','Nợ'),moneyCol('credit','Có'),{field:'party',headerName:'Đối tượng',minWidth:120},
 {field:'lotus_farm_block',headerName:'Vườn / lô',minWidth:130,valueGetter:p=>[p.data.lotus_farm,dimLabel('lotus_farm_block',p.data.lotus_farm_block)].filter(Boolean).join(' / ')},
 {field:'remarks',headerName:'Diễn giải',minWidth:180,valueGetter:p=>String(p.data.remarks||p.data.note||'').split('\n')[0]}]
const supplierColumns=computed(()=>[{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:220,flex:2},moneyCol('invoiced','Đã nhận hóa đơn'),moneyCol('paid','Đã trả'),moneyCol('owed','Còn nợ'),moneyCol('overdue','Quá hạn'),
 {field:'open_invoices',headerName:'Hóa đơn còn nợ',minWidth:110},...(overview.value?.can_post?[{field:'__pay',headerName:'',minWidth:140,sortable:false,cellRenderer:cellButton('Lập phiếu chi',r=>openPay(r.supplier),r=>r.open_invoices>0)}]:[])])
const invoiceColumns=[{field:'supplier_name',headerName:'Nhà cung cấp',minWidth:200},{field:'bill_no',headerName:'Số hóa đơn',minWidth:130,valueGetter:p=>p.data.bill_no||p.data.name},dateCol('bill_date','Ngày'),dateCol('due_date','Hạn trả'),
 moneyCol('grand_total','Tổng tiền'),moneyCol('outstanding_amount','Còn nợ'),moneyCol('paying','Đang chờ chi'),{field:'aging',headerName:'Tuổi nợ',minWidth:150,cellClass:p=>p.value&&p.value!=='Trong hạn'?'fin-cell-bad':''}]
const salaryReadyColumns=computed(()=>[{field:'month',headerName:'Tháng',minWidth:100,valueFormatter:p=>p.value?p.value.slice(5)+'/'+p.value.slice(0,4):''},moneyCol('net','Thực nhận'),{field:'payroll_voucher',headerName:'Bút toán lương',minWidth:170},
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
    <li><button type="button" @click="go('cash')"><b>{{overview.pending_counts.vouchers}}</b> phiếu chi đang chờ ký</button></li>
   </ul></section>
 </template>

 <template v-else-if="tab==='pending'&&pendingData">
  <section class="land-card">
   <div class="land-card__head"><h3>Phiếu nhận hàng chưa có hóa đơn</h3><UiButton v-if="overview?.can_post" :disabled="!picked.size||pickedSupplier.length!==1" :title="pickedSupplier.length>1?'Chọn phiếu của cùng một nhà cung cấp':''" @click="invoice={bill_no:'',bill_date:today,due_date:''};invoiceOpen=true">Lập hóa đơn ({{picked.size}})</UiButton></div>
   <div class="land-table fin-table"><DataTable :rows="receiptRows" :columns="receiptColumns" row-key="name" storage-key="fin-receipts" interactive empty="Mọi phiếu nhận hàng đã có hóa đơn." @open="r=>togglePick(r.name)"/></div>
  </section>
  <section class="land-card"><h3>Bảng lương đã ký, chưa ghi sổ</h3>
   <div class="land-table fin-table"><DataTable :rows="pendingData.payroll" :columns="payrollPendingColumns" row-key="name" storage-key="fin-payroll-pending" interactive empty="Không có bảng lương chờ ghi sổ." @open="r=>previewPayroll(r.name)"/></div>
  </section>
  <section class="land-card"><h3>Xuất kho chưa gắn lô</h3><p class="land-note">Chi phí của các dòng này chưa vào lô nào. Sửa ô "Khu vực / lô sử dụng" thành mã lô trong danh sách khi lập phiếu.</p>
   <div class="land-table fin-table"><DataTable :rows="keyed(pendingData.issues)" :columns="issueColumns" row-key="__key" storage-key="fin-issues" interactive empty="Mọi dòng xuất kho đã gắn lô." @open="r=>openWarehouse(r.name)"/></div>
  </section>
 </template>

 <section v-else-if="tab==='journal'" class="land-card">
  <div class="land-filters"><label>Từ<UiInput v-model="range.from" type="date"/></label><label>Đến<UiInput v-model="range.to" type="date"/></label><UiButton variant="outline" @click="load">Xem</UiButton><span class="land-spacer"></span><span class="land-count">{{journalRows.length}} chứng từ</span></div>
  <details v-for="v in journalRows" :key="v.voucher_no" class="fin-entry"><summary><span>{{vnDate(v.posting_date)}}</span><b>{{v.voucher_no}}</b><span>{{v.source.purpose?v.source.doctype+' '+v.source.name:v.voucher_type}}</span><strong>{{vnd(v.amount)}}</strong></summary>
   <DataTable :rows="keyed(v.lines)" :columns="lineColumns" row-key="__key" storage-key="fin-journal-lines"/></details>
  <p v-if="!journalRows.length&&!busy" class="land-empty">Không có chứng từ trong khoảng ngày này.</p>
 </section>

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
   <label>Từ<UiInput v-model="range.from" type="date"/></label><label>Đến<UiInput v-model="range.to" type="date"/></label>
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
  <section v-else-if="report==='reconciliation'&&reportData?.checks" class="land-card"><h3>Đối chiếu sổ kế toán với nghiệp vụ Lotus ({{vnDate(reportData.on_date)}})</h3>
   <div class="land-table fin-table"><DataTable :rows="reportData.checks" :columns="reconColumns" row-key="label" storage-key="fin-reconciliation"/></div>
  </section>
 </template>

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
    <label v-for="k in settings.keys" :key="k.key">{{k.label}}<UiSelect v-model="form.mapping[k.key]" :disabled="!settings.is_chief"><option value="">Chưa chọn</option><option v-for="a in accountsFor(k.key)" :key="a.name" :value="a.name">{{a.name}}</option></UiSelect></label>
    <label>Ngày bắt đầu ghi sổ (cutover)<UiInput v-model="form.cutover_date" type="date" :disabled="!settings.is_chief"/></label>
    <label class="fin-check"><input v-model="form.enabled" type="checkbox" :disabled="!settings.is_chief">Bật ghi sổ kế toán từ Lotus</label>
    <div v-if="settings.is_chief" class="land-actions land-form__full"><UiButton type="submit" :disabled="saving">Lưu</UiButton></div>
   </form>
  </section>
  <section class="land-card"><h3>Kết chuyển và khóa sổ theo tháng ({{today.slice(0,4)}})</h3>
   <p class="land-note">Cuối tháng: kết chuyển chi phí 621 / 622 / 627 sang 154 theo từng vườn, lô (giữ nguyên chiều phân tích), rồi khóa sổ.</p>
   <div class="fin-months"><div v-for="m in months" :key="m" class="fin-month" :class="{closed:periodOf(m)?.closed}"><b>{{m.slice(5)}}/{{m.slice(0,4)}}</b><small>{{periodOf(m)?.closed?'Đã khóa':'Đang mở'}}</small>
    <UiButton size="sm" variant="ghost" @click="previewClosing(m)">Kết chuyển CP</UiButton>
    <template v-if="settings.is_chief"><UiButton v-if="!periodOf(m)?.closed" size="sm" variant="outline" @click="closeMonth(m)">Khóa</UiButton><UiButton v-else size="sm" variant="ghost" @click="reopenMonth(m)">Mở lại</UiButton></template></div></div>
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
   <label>Số hóa đơn<UiInput v-model="invoice.bill_no" required/></label><label>Ngày hóa đơn<UiInput v-model="invoice.bill_date" type="date" required/></label><label>Hạn thanh toán<UiInput v-model="invoice.due_date" type="date"/></label>
   <p class="land-note">Ghi Nợ hàng về chưa có hóa đơn / Có phải trả người bán. Chưa tính VAT ở phiên bản này.</p>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="invoiceOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!invoice.bill_no">Ghi hóa đơn</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal :model-value="!!payrollView" title="Bút toán lương" :busy="saving" width="980px" @update:model-value="v=>{if(!v)payrollView=null}">
  <div v-if="payrollView" class="land-form">
   <p>Tháng {{payrollView.month}} · {{payrollView.people}} người · {{payrollView.crews}} đội khoán · ngày hạch toán {{vnDate(payrollView.posting_date)}}</p>
   <p class="land-note">Tổng lương {{vnd(payrollView.totals.gross)}} · bảo hiểm doanh nghiệp {{vnd(payrollView.totals.employer_insurance)}} · khoán {{vnd(payrollView.totals.crews)}} · thực nhận {{vnd(payrollView.totals.net)}}. {{payrollView.indirect.length}} người không có công ở lô nào được tính chi phí quản lý.</p>
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

 <WorkspaceModal v-model="payOpen" title="Phiếu chi trả nhà cung cấp" :busy="saving" width="760px">
  <form class="land-form" @submit.prevent="preparePay">
   <div class="fin-form-rows" role="list"><div class="fin-form-row fin-form-row--head" aria-hidden="true"><span>Hóa đơn</span><span>Hạn</span><span class="num">Còn nợ</span><span class="num">Trả lần này</span></div>
    <div v-for="i in supplierInvoices" :key="i.name" class="fin-form-row" role="listitem"><b>{{i.bill_no||i.name}}</b><span>{{vnDate(i.due_date)}}</span><span class="num">{{vnd(i.outstanding_amount-(i.paying||0))}}</span><UiInput v-model="pay.allocations[i.name]" type="number" min="0" :aria-label="'Trả hóa đơn '+(i.bill_no||i.name)"/></div></div>
   <p>Tổng chi: <b>{{vnd(payTotal)}}</b></p>
   <div class="land-form--grid"><label>Hình thức<UiSelect v-model="pay.mode"><option value="cash">Tiền mặt (phiếu chi)</option><option value="bank">Chuyển khoản (ủy nhiệm chi)</option></UiSelect></label><label>Ngày chi<UiInput v-model="pay.posting_date" type="date"/></label>
    <label v-if="pay.mode==='bank'" class="land-form__full">Số ủy nhiệm chi / giao dịch<UiInput v-model="pay.reference_no" required/></label></div>
   <SignerPicker v-model="signers" :options="signerOptions" :disabled="saving"/>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="payOpen=false">Hủy</UiButton><UiButton type="submit" :disabled="saving||!payTotal">Lập phiếu và gửi ký</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal :model-value="!!salaryOpen" title="Phiếu chi lương" :busy="saving" width="640px" @update:model-value="v=>{if(!v)salaryOpen=null}">
  <form v-if="salaryOpen" class="land-form" @submit.prevent="prepareSalary"><p>Tháng {{salaryOpen.month}} · thực nhận {{vnd(salaryOpen.net)}}</p>
   <div class="land-form--grid"><label>Hình thức<UiSelect v-model="salary.mode"><option value="bank">Chuyển khoản</option><option value="cash">Tiền mặt</option></UiSelect></label><label>Ngày chi<UiInput v-model="salary.posting_date" type="date"/></label>
    <label v-if="salary.mode==='bank'" class="land-form__full">Số ủy nhiệm chi<UiInput v-model="salary.reference_no"/></label></div>
   <SignerPicker v-model="signers" :options="signerOptions" :disabled="saving"/>
   <div class="land-actions"><UiButton type="button" variant="outline" :disabled="saving" @click="salaryOpen=null">Hủy</UiButton><UiButton type="submit" :disabled="saving">Lập phiếu và gửi ký</UiButton></div></form>
 </WorkspaceModal>

 <WorkspaceModal v-model="serviceOpen" title="Hóa đơn dịch vụ / chi phí" :busy="saving" width="980px">
  <form class="land-form" @submit.prevent="saveService">
   <div class="land-form--grid"><label>Nhà cung cấp<UiSelect v-model="service.supplier" required><option value="">Chọn…</option><option v-for="s in lookups?.suppliers||[]" :key="s.name" :value="s.name">{{s.supplier_name}}</option></UiSelect></label>
    <label>Số hóa đơn<UiInput v-model="service.bill_no" required/></label><label>Ngày hóa đơn<UiInput v-model="service.bill_date" type="date"/></label><label>Hạn thanh toán<UiInput v-model="service.due_date" type="date"/></label></div>
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
