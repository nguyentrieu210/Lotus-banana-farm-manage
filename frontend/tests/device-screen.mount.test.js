import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,createApp,h,ref,document} from './support/mount.mjs'

const DevicePanel=await load('components/hr/HrDevicePanel.vue')
const HrOperations=await load('components/HrOperations.vue')

test('Máy chấm công shows an explicit empty state instead of a blank panel',async()=>{
 globalThis.fetch=async()=>({ok:true,json:async()=>({message:{machines:[],unmapped:[],employees:[],can_manage:true,adms:{}}})})
 const ui=mount(DevicePanel,{company:'Lotus Agritech',farms:[]})
 try{
  await tick()
  assert.match(ui.root.textContent,/Máy chấm công/)
  assert.match(ui.root.textContent,/Chưa khai báo máy chấm công/)
  assert.match(ui.root.textContent,/Khai báo máy/)
 }finally{ui.unmount()}
})

test('Máy chấm công reports an API error and offers retry',async()=>{
 globalThis.fetch=async()=>({ok:false,status:503,json:async()=>({exception:'Máy chủ không trả lời'})})
 const ui=mount(DevicePanel,{company:'Lotus Agritech',farms:[]})
 try{
  await tick()
  assert.ok(ui.root.querySelector('[role="alert"]'))
  assert.match(ui.root.textContent,/Thử lại/)
  assert.doesNotMatch(ui.root.textContent,/Chưa khai báo máy chấm công/)
 }finally{ui.unmount()}
})

test('A directly opened machines view displays its panel before company selection',async()=>{
 const ui=mount(HrOperations,{view:'devices',company:'',manager:true})
 try{
  await tick()
  assert.match(ui.root.textContent,/Máy chấm công/)
  assert.match(ui.root.textContent,/Chưa chọn công ty/)
 }finally{ui.unmount()}
})
test('A machine registered with LAN SDK is shown, not mislabelled as CSV or ADMS',async()=>{
 globalThis.fetch=async()=>({ok:true,json:async()=>({message:{
  machines:[{name:'device-1',device_code:'FARM222',device_name:'FARM 222',active:1,connection_mode:'LAN SDK',punches_today:0,mapped:0,last_event_at:null}],
  unmapped:[],employees:[],can_manage:true,adms:{}
 }})})
 const ui=mount(DevicePanel,{company:'Lotus Agritech',farms:[]})
 try{
  await tick()
  assert.match(ui.root.textContent,/FARM 222/)
  assert.match(ui.root.textContent,/LAN SDK \(chưa xác nhận tự động\)/)
 }finally{ui.unmount()}
})

test('Switching from import to devices updates the visible section without recreating the parent',async()=>{
 const view=ref('import')
 const root=document.createElement('div');document.body.append(root)
 const app=createApp({render:()=>h(HrOperations,{view:view.value,company:'',manager:true})})
 app.mount(root)
 try{
  await tick()
  assert.match(root.textContent,/Nhập nhân sự/)
  view.value='devices';await tick()
  assert.match(root.textContent,/Máy chấm công/)
  assert.match(root.textContent,/Chưa chọn công ty/)
 }finally{app.unmount();root.remove()}
})
