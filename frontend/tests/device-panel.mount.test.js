import test from 'node:test'
import assert from 'node:assert/strict'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,mount,tick} from './support/mount.mjs'

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
const Panel=await load('components/hr/HrDevicePanel.vue')
const D='lotus_farm.device_admin.'
const overview=manage=>({can_manage:manage,adms:{server:'lotus.gpcds.site',port:443,https:true,path:'/iclock/cdata'},
 machines:[{name:'DEV1',device_code:'CONG-A',device_name:'Cổng khu A',connection_mode:'ADMS',serial_number:'CQZ1',active:1,online:true,last_seen_at:'',last_event_at:'',punches_today:42,mapped:30},
  {name:'DEV2',device_code:'CSV-B',device_name:'Kho B',connection_mode:'File CSV',active:1,online:false,last_seen_at:'',last_event_at:'',punches_today:0,mapped:0}],
 employees:[{name:'E1',employee_name:'Thị Phiêu'},{name:'E2',employee_name:'Lìu Ní Kiệt'}],
 unmapped:[{device:'DEV1',device_user_id:'12',name_on_device:'THI PHIEU',punches:6,suggested:'E1'},{device:'DEV1',device_user_id:'77',name_on_device:'',punches:1,suggested:null}]})
const text=root=>root.textContent.replace(/\s+/g,' ')

test('clocks show their connection, and a suggested employee is ready to map',async()=>{
 calls.length=0
 routes={[D+'overview']:overview(true),[D+'map_device_user']:{identity:'ID1',remapped:6,synced:{synced:6}}}
 const view=mount(Panel,{company:'Lotus',farms:[{name:'F1',farm_name:'Vườn 222'}]});await tick();await tick()
 assert.match(text(view.root),/Cổng khu A.*Đang kết nối/)
 assert.match(text(view.root),/Kho B.*Nhập file CSV/)
 const rows=[...view.root.querySelectorAll('.hr-devices__map tbody tr')]
 assert.equal(rows[0].querySelector('select').value,'E1','the matching name is preselected')
 assert.equal(rows[1].querySelector('select').value,'')
 assert.ok([...rows[1].querySelectorAll('button')].find(b=>b.textContent.trim()==='Gắn').disabled,'nothing to map without a choice')
 ;[...rows[0].querySelectorAll('button')].find(b=>b.textContent.trim()==='Gắn').click();await tick();await tick()
 assert.deepEqual(calls.find(c=>c.method===D+'map_device_user').args,{company:'Lotus',device:'DEV1',device_user_id:'12',employee:'E1'})
 view.unmount()
})

test('readers see clocks and IDs without mapping or editing',async()=>{
 routes={[D+'overview']:overview(false)}
 const view=mount(Panel,{company:'Lotus',farms:[]});await tick();await tick()
 assert.ok(![...view.root.querySelectorAll('button')].some(b=>/Gắn|Khai báo máy|Sửa/.test(b.textContent)))
 assert.ok(view.root.querySelector('.hr-devices__map select').disabled)
 view.unmount()
})
