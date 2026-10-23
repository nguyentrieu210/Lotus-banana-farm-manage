import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,window,document} from './support/mount.mjs'

const API='lotus_farm.finance.assets.'
const calls=[]
const views=[]
test.afterEach(()=>{for(const view of views.splice(0))view.unmount()})
let routes={}
globalThis.fetch=async(url,options={})=>{
 const target=new URL(url,'http://localhost:8080'),method=target.pathname.replace('/api/method/','')
 const args=options.body?JSON.parse(options.body):Object.fromEntries(target.searchParams)
 calls.push({method,args,write:options.method==='POST'})
 const handler=routes[method]
 if(!handler)return {ok:false,status:404,json:async()=>({message:method,exc_type:'DoesNotExistError'})}
 const result=typeof handler==='function'?handler(args):handler
 if(result?.exc_type)return {ok:false,status:417,json:async()=>result}
 return {ok:true,status:200,json:async()=>({message:result})}
}
const Component=await load('components/finance/FinanceAssets.vue')
const base=(overrides={})=>({enabled:true,permissions:{write:true,approve:false},assets:[],operations:[],runs:[],...overrides})
const catalog={categories:[],locations:[],accounts:[]}
const lookups={categories:[],locations:[],accounts:[],cost_centers:[],employees:[],farms:[],blocks:[],suppliers:[],customers:[],cycles:[],work_types:[]}
const text=root=>root.textContent.replace(/\s+/g,' ')
const button=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label)
async function open(data=base(),extra={},props={}){
 calls.length=0
 routes={[API+'overview']:data,[API+'lookups']:lookups,[API+'catalogs']:catalog,...extra}
 const view=mount(Component,props)
 views.push(view)
 for(let i=0;i<5;i++)await tick()
 return view
}
async function select(root,value){const labels={assets:'Tài sản',categories:'Nhóm tài sản',locations:'Vị trí',accounts:'Tài khoản',depreciation:'Khấu hao',operations:'Biến động',report:'Báo cáo'};root.querySelector('nav[aria-label="Các mục tài sản cố định"] button[aria-label="'+labels[value]+'"]').click();for(let i=0;i<3;i++)await tick()}
async function menu(trigger,label){trigger.dispatchEvent(new window.MouseEvent('click',{bubbles:true,button:0,ctrlKey:false}));for(let i=0;i<3;i++)await tick();const item=[...document.querySelectorAll('[role="menuitem"]')].find(b=>b.textContent.trim()===label);assert.ok(item,'menu item '+label);item.click();for(let i=0;i<3;i++)await tick()}

test('activation is available only to the chief and explicitly switches to reviewed depreciation',async()=>{
 const view=await open(base({enabled:false,permissions:{write:true,approve:true}}),{[API+'activate']:base()})
 assert.match(text(view.root),/không tự tạo tài sản hay ghi số dư/)
 button(view.root,'Bật quản lý tài sản').click();for(let i=0;i<4;i++)await tick()
 assert.ok(calls.some(c=>c.method===API+'activate'&&c.write&&c.args.on===1))
 view.unmount()
 const readonly=await open(base({enabled:false,permissions:{write:false,approve:false}}))
 assert.equal(button(readonly.root,'Bật quản lý tài sản'),undefined)
 readonly.unmount()
})

test('chief can import category setup before activation; accountants cannot open it',async()=>{
 const view=await open(base({enabled:false,permissions:{write:true,approve:true}}))
 await select(view.root,'categories');button(view.root,'Nhập nhóm Excel').click();await tick()
 assert.match(document.querySelector('dialog[open]').textContent,/Nhập nhóm tài sản từ Excel/)
 view.unmount()
 const accountant=await open(base());await select(accountant.root,'categories')
 assert.equal(button(accountant.root,'Nhập nhóm Excel'),undefined)
 assert.equal(button(accountant.root,'Thêm nhóm'),undefined)
})

test('new asset supports purchasing and server field errors stay inside the modal',async()=>{
 const view=await open(base(),{[API+'save_asset']:{errors:{code:'Mã tài sản bị trùng.'}}})
 button(view.root,'Thêm tài sản').click();await tick()
 const source=document.querySelector('[aria-label="Nguồn tài sản"]')
 source.value='0';source.dispatchEvent(new window.Event('change',{bubbles:true}));await tick()
 assert.match(text(document.body),/Nhà cung cấp/)
 const form=document.querySelector('dialog[open] form');form.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));for(let i=0;i<4;i++)await tick()
 assert.match(form.textContent,/Mã tài sản bị trùng/)
 const save=calls.find(c=>c.method===API+'save_asset')
 assert.equal(JSON.parse(save.args.values).existing,false)
 view.unmount()
})

test('accountant can review but cannot approve a pending operation',async()=>{
 const op={name:'OP-1',kind:'Create',state:'Pending',posting_date:'2026-09-01',asset:null}
 const view=await open(base({operations:[op]}),{[API+'operation_preview']:{...op,summary:{values:{asset_name:'Máy bơm',amount:120000000}},errors:[],warnings:[],fingerprint:'version-one'}})
 await select(view.root,'operations');button(view.root,'Xem trước').click();for(let i=0;i<4;i++)await tick()
 assert.match(text(document.body),/Máy bơm/)
 assert.equal(button(document.body,'Duyệt và ghi sổ'),undefined)
 view.unmount()
})

test('chief sends the reviewed fingerprint and sees stale-preview errors in the approval dialog',async()=>{
 const op={name:'OP-1',kind:'Scrap',state:'Pending',posting_date:'2026-09-01',asset:'ASSET-1'}
 const view=await open(base({permissions:{write:true,approve:true},operations:[op]}),{
  [API+'operation_preview']:{...op,summary:{values:{},remaining:10000000},errors:[],warnings:[],fingerprint:'version-one'},
  [API+'operation_post']:{exc_type:'ValidationError',message:'Dữ liệu đã thay đổi. Xem trước lại.'}})
 await select(view.root,'operations');button(view.root,'Xem trước').click();for(let i=0;i<3;i++)await tick()
 button(document.body,'Duyệt và ghi sổ').click();for(let i=0;i<4;i++)await tick()
 const approval=calls.find(c=>c.method===API+'operation_post')
 assert.equal(approval.args.fingerprint,'version-one')
 assert.ok([...document.querySelectorAll('dialog')].some(d=>d.textContent.includes('Dữ liệu đã thay đổi')))
 view.unmount()
})

test('monthly depreciation shows allocation amounts before chief approval',async()=>{
 const view=await open(base({permissions:{write:true,approve:true}}),{[API+'depreciation_preview']:{month:'2026-09',total:4931506.85,errors:[],posted:null,fingerprint:'month-version',rows:[{schedule_row:'S1',asset_name:'Máy bơm',amount:4931506.85,schedule_date:'2026-09-30',allocations:[{lotus_farm:'F1',percent:60,amount:2958904.11},{lotus_farm:'F2',percent:40,amount:1972602.74}]}]}})
 await select(view.root,'depreciation');button(view.root,'Lập bảng khấu hao').click();for(let i=0;i<4;i++)await tick()
 assert.match(text(document.body),/4\.931\.506,85/)
 assert.ok(button(document.body,'Duyệt và ghi sổ'))
 assert.equal(calls.filter(c=>c.method===API+'depreciation_post').length,0)
 view.unmount()
})

test('Excel preview uploads in a POST body and shows row errors inside the modal',async()=>{
 const previous=globalThis.FileReader
 globalThis.FileReader=class{readAsDataURL(){this.result='data:application/octet-stream;base64,YXNzZXQ=';this.onload()}}
 try{
  const view=await open(base(),{[API+'import_preview']:{valid:false,rows:[{line:2,values:{code:'TS1',asset_name:'Máy bơm'},errors:{code:'Mã đã có'}}]}})
  button(view.root,'Nhập Excel').click();await tick()
  const input=document.querySelector('[aria-label="File tài sản đầu kỳ"]')
  Object.defineProperty(input,'files',{value:[{size:10}],configurable:true})
  input.dispatchEvent(new window.Event('change',{bubbles:true}));await tick()
  button(document.body,'Xem trước').click();for(let i=0;i<4;i++)await tick()
  const upload=calls.find(c=>c.method===API+'import_preview')
  assert.ok(upload.write)
  assert.match(upload.args.content,/base64,YXNzZXQ=/)
  assert.match(document.querySelector('dialog[open]').textContent,/Mã đã có/)
 }finally{globalThis.FileReader=previous}
})

test('catalogs are visible independently of an empty asset register',async()=>{
 const groups=Array.from({length:8},(_,i)=>({name:'G'+i,asset_category_name:'Nhóm '+i,asset_count:0,pending_count:0,can_edit:false}))
 const view=await open(base({permissions:{write:false,approve:false}}),{[API+'catalogs']:{categories:groups,locations:[{name:'FARM 222',location_name:'FARM 222',asset_count:0,pending_count:0}],accounts:[]}})
 assert.match(text(view.root),/Đã có 8 nhóm và 1 vị trí/)
 assert.equal(view.root.querySelectorAll('nav[aria-label="Các mục tài sản cố định"] button').length,7)
 await select(view.root,'categories');assert.match(text(view.root),/Nhóm 7/)
 assert.equal(button(view.root,'Thêm nhóm'),undefined)
 await select(view.root,'locations');assert.match(text(view.root),/FARM 222/)
 assert.equal(button(view.root,'Thêm vị trí'),undefined)
})

test('pending assets edit through their operation and never call native asset detail',async()=>{
 const pending={name:'OP1',operation:'OP1',modified:'v1',posting_date:'2026-10-01',lotus_asset_code:'TS1',asset_name:'Máy bơm chờ duyệt',status:'Pending',values:{code:'TS1',asset_name:'Máy bơm chờ duyệt',existing:true}}
 const view=await open(base({pending_assets:[pending],totals:{original:0,remaining:0}}),{[API+'save_asset']:{name:'OP1'}})
 assert.match(text(view.root),/Máy bơm chờ duyệt/)
 assert.match(text(view.root),/1 chờ duyệt/)
 await menu(view.root.querySelector('[aria-label="Thao tác TS1"]'),'Sửa hồ sơ')
 const form=document.querySelector('dialog[open] form');assert.match(form.textContent,/Giá trị đầu kỳ/)
 form.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));for(let i=0;i<5;i++)await tick()
 const saved=JSON.parse(calls.find(c=>c.method===API+'save_asset').args.values)
 assert.equal(saved.operation,'OP1');assert.equal(saved.modified,'v1');assert.equal(saved.name,undefined)
 assert.ok(!calls.some(c=>c.method===API+'detail'))
})

test('chief can review a pending registration directly from the register',async()=>{
 const pending={operation:'OP1',name:'OP1',lotus_asset_code:'TS1',asset_name:'Máy bơm',values:{existing:true},status:'Pending'}
 const view=await open(base({pending_assets:[pending],permissions:{write:true,approve:true}}),{[API+'operation_preview']:{name:'OP1',kind:'Create',state:'Pending',summary:{values:{}},errors:[],fingerprint:'v1'}})
 await menu(view.root.querySelector('[aria-label="Thao tác TS1"]'),'Xem trước')
 assert.ok(button(document.body,'Duyệt và ghi sổ'))
 assert.equal(calls.find(c=>c.method===API+'operation_preview').args.name,'OP1')
})

test('group detail shows existing mappings and blocks policy editing after assets are posted',async()=>{
 const group={name:'Máy',asset_category_name:'Máy',configured:true,can_edit:false,asset_count:1,pending_count:0,fixed_asset_account:'211',accumulated_depreciation_account:'2141',depreciation_expense_account:'6274',capital_work_in_progress_account:'2411'}
 const view=await open(base({permissions:{write:true,approve:true}}),{[API+'catalogs']:{...catalog,categories:[group]}})
 await select(view.root,'categories')
 await menu(view.root.querySelector('[aria-label="Thao tác nhóm Máy"]'),'Chi tiết')
 const detail=document.querySelector('dialog[open]')
 assert.match(detail.textContent,/2141/);assert.match(detail.textContent,/Nhóm đã có tài sản được duyệt/)
 assert.equal(button(detail,'Chỉnh sửa'),undefined)
})

test('account list includes groups and hides retired accounts until explicitly requested',async()=>{
 const view=await open(base(),{[API+'catalogs']:{...catalog,accounts:[{name:'2',account_number:'2',account_name:'Tài sản dài hạn',is_group:1,disabled:0},{name:'211',account_number:'211',account_name:'Tài sản cố định',is_group:0,disabled:0},{name:'old',account_number:'',account_name:'Tài khoản cũ',disabled:1}]}})
 await select(view.root,'accounts');assert.match(text(view.root),/Tài sản dài hạn/);assert.doesNotMatch(text(view.root),/Tài khoản cũ/)
 const scope=view.root.querySelector('[aria-label="Phạm vi tài khoản"]');scope.value='all';scope.dispatchEvent(new window.Event('change',{bubbles:true}));await tick()
 assert.match(text(view.root),/Tài khoản cũ/)
 assert.equal(button(view.root,'Nhập tài khoản Excel'),undefined)
})

test('empty filter results can be reset and do not suggest that the register has no records',async()=>{
 const view=await open(base({assets:[{name:'A1',lotus_asset_code:'TS1',asset_name:'Máy bơm',docstatus:1,status:'Submitted'}]}))
 const input=view.root.querySelector('[aria-label="Tìm tài sản"]');input.value='không có';input.dispatchEvent(new window.Event('input',{bubbles:true}));await tick()
 assert.match(text(view.root),/Không có tài sản khớp bộ lọc/)
 assert.doesNotMatch(text(view.root),/Đã có 0 nhóm và 0 vị trí/)
 button(view.root,'Xóa bộ lọc').click();await tick();assert.match(text(view.root),/Máy bơm/)
})

test('requested section initializes correctly and navigation emits URL state',async()=>{
 const changes=[]
 const view=await open(base(),{}, {view:'locations',onViewChange:value=>changes.push(value)})
 assert.equal(view.root.querySelector('nav button[aria-current="page"]').getAttribute('aria-label'),'Vị trí')
 await select(view.root,'accounts');assert.deepEqual(changes,['accounts'])
})
