import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document,window} from './support/mount.mjs'

const works=[{name:'CB',label:'Cắt bắp',stage:'Cut Bud'},{name:'CL',label:'Cắt lá',stage:'',uom:'Ha'}]
const machine=(extra={})=>({name:'e1',work_type:'CB',stage:'Cut Bud',qty:12,state:'Draft',machine_read:1,review_flags:'Máy đọc, chưa kiểm',...extra})
const data=(extra={})=>({report:{name:'R1',state:'Draft',modified:'m1'},works,rights:{write:true},
 lots:[{block:'b1',code:'A1',lines:[machine(),machine({name:'e2',work_type:'CL',stage:'',qty:1.2,done:1,review_flags:'Máy đọc, chưa kiểm'})]},
  {block:'b2',code:'A2',lines:[machine({name:'e3',machine_read:0,review_flags:null})]}],
 paper:{printed_at:'2026-11-10 06:00:00',photo:'/private/files/phieu.jpg',read_at:'2026-11-10 17:05:00',notes:['Phiếu có lô "Z9" không in sẵn: kiểm ảnh rồi nhập tay.']},...extra})

let calls=[],replies={}
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.replace('/api/method/','')
 calls.push({method,body:opts.body&&typeof opts.body==='string'?JSON.parse(opts.body):null})
 if(!(method in replies))return {ok:false,status:404,json:async()=>({message:'Missing '+method})}
 return {ok:true,status:200,json:async()=>({message:typeof replies[method]==='function'?replies[method]():replies[method]})}
}
const Review=await load('components/field/PaperPhotoReview.vue')
async function settle(){for(let i=0;i<8;i++)await tick()}
const button=(root,text)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(text))
function show(props={},events={}){calls=[];return mount({setup:()=>()=>h(Review,{data:data(),farm:'F',team:'T1',date:'2026-11-10',editable:true,...props,...events})})}

test('the photo sits next to the lô still to check, with what the reader noted',async()=>{
 const view=show();await settle()
 assert.match(view.root.textContent,/Đã đọc ảnh lúc 10\/11\/2026 17:05 · còn 1 lô chưa kiểm/)
 assert.equal(view.root.querySelector('.paper-review__photo img').getAttribute('src'),'/private/files/phieu.jpg')
 const lots=[...view.root.querySelectorAll('.paper-review__lot')]
 assert.equal(lots.length,1,'a lô entered by hand is not listed')
 assert.match(lots[0].textContent,/Lô A1.*Cắt bắp · 12.*Máy đọc, chưa kiểm.*Cắt lá · 1,2 · xong cả lô/)
 assert.match(view.root.querySelector('.paper-review__notes').textContent,/Z9/)
 view.unmount()
})

test('checking a lô opens it',async()=>{
 let opened=null
 const view=show({},{'onOpen-lot':lot=>{opened=lot}});await settle()
 button(view.root,'Kiểm lô này').click();await settle()
 assert.equal(opened?.code,'A1')
 view.unmount()
})

test('printing fixes the form on the server and opens the print page',async()=>{
 replies={'lotus_farm.lot_paper_form.form_url':()=>({url:'/lotus/in-phieu-ngay?report=R1',report:{name:'R1'}})}
 const tab={location:'',close(){}}
 const before=window.open;window.open=()=>tab
 let changed=0
 const view=show({data:data({paper:null})},{onChanged:()=>{changed++}});await settle()
 assert.match(view.root.textContent,/In phiếu cho tổ ghi tay, rồi chụp ảnh để máy điền sẵn/)
 button(view.root,'In phiếu giấy').click();await settle()
 assert.deepEqual(calls.find(c=>c.method==='lotus_farm.lot_paper_form.form_url').body,{farm:'F',team:'T1',date:'2026-11-10'})
 assert.equal(tab.location,'/lotus/in-phieu-ngay?report=R1')
 assert.equal(changed,1,'the day is read again: the report changed')
 window.open=before
 view.unmount()
})

test('a sent report cannot read a photo any more',async()=>{
 const open=show();await settle()
 assert.ok(button(open.root,'Đọc ảnh phiếu'),'a draft report can read a photo')
 open.unmount()
 const view=show({editable:false});await settle()
 assert.equal(button(view.root,'Đọc ảnh phiếu'),undefined)
 assert.ok(button(view.root,'In phiếu giấy'),'the form can still be printed')
 view.unmount()
})
