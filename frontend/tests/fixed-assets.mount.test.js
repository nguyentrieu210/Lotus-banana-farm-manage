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
const lookups={categories:[],locations:[],accounts:[],cost_centers:[],employees:[],farms:[],blocks:[],suppliers:[],customers:[],cycles:[],work_types:[]}
const text=root=>root.textContent.replace(/\s+/g,' ')
const button=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label)
async function open(data=base(),extra={}){
 calls.length=0
 routes={[API+'overview']:data,[API+'lookups']:lookups,...extra}
 const view=mount(Component)
 views.push(view)
 for(let i=0;i<5;i++)await tick()
 return view
}
async function select(root,value){const el=root.querySelector('[aria-label="Mục tài sản"]');el.value=value;el.dispatchEvent(new window.Event('change',{bubbles:true}));for(let i=0;i<3;i++)await tick()}

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
