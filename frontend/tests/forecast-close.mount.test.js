import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick} from './support/mount.mjs'

const Close=await load('components/ForecastCloseAction.vue')
const Form=await load('components/ForecastForm.vue')
const button=(root,text)=>[...root.querySelectorAll('button')].find(el=>el.textContent.trim()===text)
const dialog=()=>document.querySelector('dialog[aria-label="Kết thúc dự thu"]')
const forecast={doctype:'Harvest Forecast',name:'HF-1',supply_state:'Released',modified:'2026-10-21 10:00:00',source_claims:[{source_cut_operation:'CUT-1'}],snapshot_hash:'FROZEN'}
function typeReason(text){const input=dialog().querySelector('textarea');input.value=text;input.dispatchEvent(new Event('input',{bubbles:true}))}

test('closing future supply requires a reason and sends the reviewed document version',async()=>{
 const calls=[],closed=[],busy=[]
 globalThis.fetch=async(url,options)=>{calls.push({url,options,args:JSON.parse(options.body)});return {ok:true,json:async()=>({message:{forecast:'HF-1',supply_state:'Closed'}})}}
 const view=mount(Close,{forecast,canClose:true,onClosed:result=>closed.push(result),onBusy:value=>busy.push(value)})
 try{
  button(view.root,'Kết thúc dự thu').click();await tick()
  assert.equal(dialog().open,true);assert.ok(button(dialog(),'Xác nhận kết thúc').disabled)
  typeReason('  Đã thu và đối soát hết vụ  ');await tick();button(dialog(),'Xác nhận kết thúc').click();await tick();await tick()
  assert.equal(calls.length,1);assert.ok(calls[0].url.endsWith('lotus_farm.onedrive_supply.close_forecast'));assert.equal(calls[0].options.method,'POST')
  assert.deepEqual(calls[0].args,{forecast:'HF-1',reason:'Đã thu và đối soát hết vụ',base_modified:forecast.modified})
  assert.deepEqual(closed,[{forecast:'HF-1',supply_state:'Closed'}]);assert.deepEqual(busy,[true,false])
  assert.equal(dialog().open,false);assert.equal(forecast.snapshot_hash,'FROZEN');assert.equal(forecast.supply_state,'Released','server response is reloaded by editor, not patched into frozen client data')
 }finally{view.unmount()}
})

test('server rejection keeps the close reason and source evidence available for reconciliation',async()=>{
 globalThis.fetch=async()=>({ok:false,json:async()=>({message:'Còn phần đang giữ cho đơn bán.'})})
 const closed=[],view=mount(Close,{forecast,canClose:true,onClosed:r=>closed.push(r)})
 try{
  button(view.root,'Kết thúc dự thu').click();await tick();typeReason('Kết thúc');await tick();button(dialog(),'Xác nhận kết thúc').click();await tick();await tick()
  assert.equal(dialog().open,true);assert.match(dialog().querySelector('[role=alert]').textContent,/Còn phần đang giữ/)
  assert.equal(dialog().querySelector('textarea').value,'Kết thúc');assert.equal(closed.length,0)
 }finally{view.unmount()}
})

test('closing is available only for permitted released supply and cancellation sends nothing',async()=>{
 let count=0;globalThis.fetch=async()=>{count++;throw new Error('unexpected request')}
 for(const props of [{forecast,canClose:false},{forecast:{...forecast,supply_state:'Draft'},canClose:true},{forecast:{...forecast,supply_state:'Closed'},canClose:true}]){
  const view=mount(Close,props);try{assert.equal(button(view.root,'Kết thúc dự thu'),undefined)}finally{view.unmount()}
 }
 const view=mount(Close,{forecast,canClose:true})
 try{button(view.root,'Kết thúc dự thu').click();await tick();typeReason('Chưa đối soát');await tick();button(dialog(),'Không thực hiện').click();await tick();assert.equal(dialog().open,false);assert.equal(count,0)}finally{view.unmount()}
})

test('native draft review exposes frozen OneDrive source claims',()=>{
 const schema={fields:[{fieldname:'process_adoption',fieldtype:'Link',options:'Lotus Process Adoption',read_only:1},{fieldname:'source_claims',fieldtype:'Table',options:'Forecast Source Claim',read_only:1}],tables:{'Forecast Source Claim':[{fieldname:'source_cut_operation',fieldtype:'Link',options:'Bunch Operation',read_only:1}]}}
 const view=mount(Form,{schema,model:{...forecast,process_adoption:'ADOPT-1'},scope:{farm:'F'},readonly:true})
 try{assert.match(view.root.textContent,/Nguồn OneDrive đã đối chiếu/);assert.match(view.root.textContent,/ADOPT-1/);assert.match(view.root.textContent,/Các phần nguồn cắt bắp/);assert.equal(view.root.querySelector('input'),null);assert.equal(button(view.root,'Thêm dòng'),undefined)}finally{view.unmount()}
})
