import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document,window} from './support/mount.mjs'

const card=(key,extra={})=>({key,title:'Thẻ '+key,value:3,unit:'tổ',tone:'info',note:'',rows:[{code:'A5',qty:2,day:'2026-11-09'},{code:'A6',qty:1,day:'2026-11-10'}],
 columns:[{field:'code',label:'Lô'},{field:'qty',label:'Số',kind:'number'},{field:'day',label:'Ngày',kind:'date'}],...extra})
const morning={date:'2026-11-09',today:'2026-11-10',crews:['C'],cards:[card('not_sent',{title:'Tổ chưa gửi báo cáo 09/11',tone:'bad'}),card('waiting',{value:0,rows:[],tone:'good'})]}
const week={week:'2026-W46',from:'2026-11-09',to:'2026-11-15',cards:[card('harvest',{title:'Thu hoạch',value:140,unit:'buồng',note:'3.000 kg'})],
 lots:[{block:'b5',code:'A5',status:'harvest'},{block:'b6',code:'A6',status:'held'}]}
const month={month:'2026-11',from:'2026-11-01',to:'2026-11-30',cards:[card('pay',{title:'Tiền khoán theo lô',value:1500000,unit:'đ'})]}

let calls=[],replies={}
globalThis.fetch=async(url)=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.replace('/api/method/','')
 calls.push({method,query:Object.fromEntries(u.searchParams)})
 if(!(method in replies))return {ok:false,status:404,json:async()=>({message:'Missing '+method})}
 return {ok:true,status:200,json:async()=>({message:typeof replies[method]==='function'?replies[method]():replies[method]})}
}
const Reports=await load('components/report/FieldReports.vue')
async function settle(){for(let i=0;i<10;i++)await tick()}
const dialog=()=>document.querySelector('dialog[open]')
const tab=(root,text)=>[...root.querySelectorAll('[role=tab]')].find(b=>b.textContent.trim()===text)
function show(events={}){calls=[];return mount({setup:()=>()=>h(Reports,{farm:'F',user:'u',...events})})}
replies={'lotus_farm.field_reports.morning':()=>morning,'lotus_farm.field_reports.week':()=>week,'lotus_farm.field_reports.month':()=>month,
 'lotus_farm.field.map_block_data':()=>({features:[]})}

test('sáng nay: one card per question, the worst marked',async()=>{
 const view=show();await settle()
 assert.equal(calls[0].method,'lotus_farm.field_reports.morning')
 const cards=[...view.root.querySelectorAll('.report-card')]
 assert.equal(cards.length,2)
 assert.match(cards[0].textContent,/Tổ chưa gửi báo cáo 09\/11\s*3\s*tổ.*Xem 2 dòng/)
 assert.ok(cards[0].classList.contains('is-bad'))
 assert.match(cards[1].textContent,/Không có dòng nào/)
 view.unmount()
})

test('a card opens its rows in a table that can be exported',async()=>{
 const view=show();await settle()
 view.root.querySelector('.report-card').click();await settle()
 await new Promise(r=>setTimeout(r,300));await settle()
 assert.match(dialog().textContent,/Tổ chưa gửi báo cáo 09\/11/)
 assert.ok(dialog().querySelector('.ag-row[row-id="0"]')&&dialog().querySelector('.ag-row[row-id="1"]'),'one row per detail line')
 assert.ok([...dialog().querySelectorAll('button')].some(b=>/Xuất Excel/.test(b.textContent)),'the rows export to Excel')
 view.unmount()
})

test('tuần and tháng ask the server for their period',async()=>{
 const view=show();await settle()
 tab(view.root,'Tuần').click();await settle()
 const asked=calls.find(c=>c.method==='lotus_farm.field_reports.week')
 assert.ok(asked&&/^\d{4}-\d{2}-\d{2}$/.test(asked.query.week))
 assert.match(view.root.textContent,/Tuần 46: 09\/11\/2026 – 15\/11\/2026/)
 assert.match(view.root.querySelector('.report-card').textContent,/Thu hoạch\s*140\s*buồng.*3\.000 kg/)
 assert.match(view.root.textContent,/Tình trạng lô trong tuần.*Đang cách ly thuốc/)
 tab(view.root,'Tháng').click();await settle()
 assert.ok(calls.some(c=>c.method==='lotus_farm.field_reports.month'&&/^\d{4}-\d{2}$/.test(c.query.month)))
 assert.match(view.root.querySelector('.report-card').textContent,/Tiền khoán theo lô\s*1\.500\.000\s*đ/)
 view.unmount()
})

test('tháng links to tiền khoán theo người',async()=>{
 let opened=null
 const view=show({onPayable:m=>{opened=m}});await settle()
 tab(view.root,'Tháng').click();await settle()
 ;[...view.root.querySelectorAll('a')].find(a=>a.textContent.includes('Tiền khoán theo người')).click();await settle()
 assert.match(opened||'',/^\d{4}-\d{2}$/)
 view.unmount()
})
