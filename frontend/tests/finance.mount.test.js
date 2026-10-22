import test from 'node:test'
import assert from 'node:assert/strict'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,loadModule,createApp,h,tick,document,window} from './support/mount.mjs'
import {createPinia,setActivePinia} from 'pinia'
import {createRouter,createMemoryHistory} from 'vue-router'

globalThis.history??=window.history
const calls=[]
let routes={}
globalThis.fetch=async(url,options={})=>{
 const target=new URL(url,'http://localhost:8080'),method=target.pathname.replace('/api/method/','')
 const args=options.body?JSON.parse(options.body):Object.fromEntries(target.searchParams)
 calls.push({method,args})
 const handler=routes[method]
 if(!handler)return {ok:false,status:404,json:async()=>({exc_type:'DoesNotExistError',message:method})}
 return {ok:true,status:200,json:async()=>({message:typeof handler==='function'?handler(args):handler})}
}
const pinia=createPinia();setActivePinia(pinia)
const FinanceApp=await load('FinanceApp.vue')
const {useSession}=await loadModule('store.js')
const F='lotus_farm.finance.'
const overview=(o={})=>({company:'Lotus Agritech',currency:'VND',on_date:'2026-10-22',enabled:true,cutover_date:'2026-10-01',coa_version:'tt133-2016-lotus-1',mapping_errors:[],
 tiles:{cash:50000000,bank:120000000,payable_supplier:1500000,payable_employee:0,insurance:0,received_not_billed:300000,month_cost:8000000},
 pending_counts:{receipts:1,payroll:1,issues:0,vouchers:0},can_post:true,is_chief:false,dims:[],keys:[],...o})
const pending={receipts:[{name:'PR-1',supplier:'S1',supplier_name:'NCC Phân bón',posting_date:'2026-10-20',to_bill:1500000},{name:'PR-2',supplier:'S2',supplier_name:'NCC Khác',posting_date:'2026-10-21',to_bill:200000}],
 payroll:[{name:'LT-2026-09',month:'2026-09',closed_at:'2026-10-02 10:00:00'}],issues:[],vouchers:[]}
const lookups={suppliers:[],farms:[{name:'LOTUS-222',farm_name:'Vườn 222'}],blocks:[{name:'B1',block_code:'A-1',farm:'LOTUS-222'}],work_types:[],accounts:[]}
async function open(path,caps={finance:true,finance_ledger:true}){
 Object.assign(useSession(),{user:'acc@lotus',today:'2026-10-22',ready:true,farms:[],modules:{},capabilities:caps,commands:{}})
 const router=createRouter({history:createMemoryHistory('/lotus'),routes:[{path:'/:p(.*)*',component:{render:()=>null}}]})
 await router.push(path);await router.isReady()
 const root=document.createElement('div');document.body.append(root)
 const app=createApp({render:()=>h(FinanceApp,{embedded:true})});app.use(pinia);app.use(router);app.mount(root)
 for(let i=0;i<4;i++)await tick()
 return {root,router,unmount:()=>{app.unmount();root.remove()}}
}
const text=root=>root.textContent.replace(/\s+/g,' ')
const button=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.includes(label))

test('overview shows money, payables and what waits for the accountant',async()=>{
 routes={[F+'reports.overview']:overview()}
 const view=await open('/tai-chinh')
 const page=text(view.root)
 assert.match(page,/Tiền mặt\s*50\.000\.000 đ/)
 assert.match(page,/Phải trả nhà cung cấp\s*1\.500\.000 đ/)
 assert.match(page,/1\s*phiếu nhận hàng chưa có hóa đơn/)
 assert.match(page,/Đang ghi sổ từ 01\/10\/2026/)
 view.unmount()
})

test('receipts of one supplier become one invoice; mixing suppliers is not allowed',async()=>{
 calls.length=0
 routes={[F+'reports.overview']:overview(),[F+'reports.pending']:pending,[F+'payments.make_goods_invoice']:{invoice:'PINV-1',amount:1500000}}
 const view=await open('/tai-chinh?tab=pending')
 const rows=[...view.root.querySelectorAll('.fin-table tbody tr')]
 rows[0].click();rows[1].click();await tick()
 assert.ok(button(view.root,'Lập hóa đơn (2)').disabled,'two suppliers cannot share one invoice')
 rows[1].click();await tick()
 const make=button(view.root,'Lập hóa đơn (1)');assert.ok(!make.disabled);make.click();await tick()
 const modal=document.body.querySelector('.land-form')
 const input=modal.querySelector('input');input.value='HD-001';input.dispatchEvent(new window.Event('input'));await tick()
 modal.dispatchEvent(new window.Event('submit',{cancelable:true}));for(let i=0;i<4;i++)await tick()
 const sent=calls.find(c=>c.method===F+'payments.make_goods_invoice')
 assert.deepEqual([JSON.parse(sent.args.receipts),sent.args.bill_no],[['PR-1'],'HD-001'])
 view.unmount()
})

test('payroll preview shows the lines by lot and posts with the previewed hash',async()=>{
 calls.length=0
 routes={[F+'reports.overview']:overview(),[F+'reports.pending']:pending,[F+'reports.lookups']:lookups,
  [F+'payroll.preview']:{period:'LT-2026-09',month:'2026-09',posting_date:'2026-09-30',source_hash:'H1',people:2,crews:0,indirect:[],issues:[],posted:null,
   totals:{gross:12000000,net:11000000,employer_insurance:2000000,crews:0},
   lines:[{account:'154 - Chi phí SXKD dở dang - LT',debit:14000000,credit:0,lotus_farm:'LOTUS-222',lotus_farm_block:'B1',note:'Lương'},{account:'334 - Phải trả người lao động - LT',debit:0,credit:11000000,note:'Thực nhận'},{account:'3383 - Bảo hiểm xã hội - LT',debit:0,credit:3000000,note:'Bảo hiểm'}]},
  [F+'payroll.post']:{voucher:'JV-1',amount:14000000}}
 const view=await open('/tai-chinh?tab=pending')
 button(view.root,'Xem trước bút toán').click();for(let i=0;i<4;i++)await tick()
 assert.match(text(document.body),/154 - Chi phí SXKD dở dang - LT\s*14\.000\.000\s*LOTUS-222\s*A-1/)
 ;[...document.body.querySelectorAll('button')].find(b=>b.textContent.trim()==='Ghi sổ').click();for(let i=0;i<4;i++)await tick()
 assert.deepEqual(calls.find(c=>c.method===F+'payroll.post').args,{period:'LT-2026-09',source_hash:'H1'})
 view.unmount()
})

test('an approver without ledger access only sees and signs the vouchers waiting for them',async()=>{
 calls.length=0
 routes={[F+'payments.my_vouchers']:[{doctype:'Payment Entry',name:'PAY-1',kind:'Trả nhà cung cấp',party_name:'NCC Phân bón',amount:600000,posting_date:'2026-10-22',reference:'',lines:[{label:'HD-001',amount:600000}],
  signing:{steps:[{key:'PREPARE',title:'Kế toán lập phiếu',name:'Kế toán',state:'Đã ký'},{key:'CHIEF',title:'Kế toán trưởng',name:'KTT',state:'Đã ký'},{key:'APPROVE',title:'Giám đốc duyệt chi',name:'GĐ',state:'Chờ ký'}],can_sign:true,can_return:true}}],
  [F+'payments.sign_payment']:{docstatus:1,signing:{done:true}}}
 const view=await open('/tai-chinh',{finance:true,finance_ledger:false})
 assert.ok(!view.root.querySelector('.workspace-tabs'),'no ledger tabs for an approver')
 assert.ok(!calls.some(c=>c.method===F+'reports.overview'),'the ledger is not requested')
 assert.match(text(view.root),/Trả nhà cung cấp · NCC Phân bón\s*600\.000 đ/)
 button(view.root,'Ký duyệt chi').click();for(let i=0;i<4;i++)await tick()
 assert.deepEqual(calls.find(c=>c.method===F+'payments.sign_payment').args,{doctype:'Payment Entry',name:'PAY-1'})
 view.unmount()
})

test('cost report by lot lists materials, labour and services',async()=>{
 routes={[F+'reports.overview']:overview(),[F+'reports.lookups']:lookups,[F+'reports.trial_balance']:{rows:[],totals:{},balanced:true},
  [F+'reports.costs']:{group_by:'lotus_farm_block',rows:[{dim:'B1',farm:'LOTUS-222',label:'A-1',materials:300000,labour:2000000,crews:500000,services:100000,total:2900000,per_ha:1000000}],
   totals:{materials:300000,labour:2000000,crews:500000,services:100000,total:2900000}}}
 const view=await open('/tai-chinh?tab=reports')
 button(view.root,'Chi phí theo vườn / lô').click();for(let i=0;i<4;i++)await tick()
 assert.match(text(view.root),/A-1\s*LOTUS-222\s*300\.000\s*2\.000\.000\s*500\.000\s*100\.000\s*2\.900\.000\s*1\.000\.000/)
 view.unmount()
})
