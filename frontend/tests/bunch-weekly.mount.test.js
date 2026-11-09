import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document,window} from './support/mount.mjs'

const empty={cut:0,inject:0,sucker:0,tree:0}
const layers={cut:97,inject:0,sucker:0,tree:0}
const money=l=>({layers:l,layer_kg:{...l,cut:l.cut*20},layer_cartons:{...l,cut:l.cut*2},layer_containers:{...l,cut:l.cut/10}})
const data={horizon:13,months:[{month:'2026-12',bunches:97,kg:1940,cartons:194,containers:9.7,...money(layers)}],unconfirmed:{'Cut Bud':120},coverage:{with_data:13,total:64},
 zones:[{zone:'A',bunches:97,kg:1940,cartons:194,containers:9.7,...money(layers)}],zone_starts:{A:'2026-12-20',B:'2027-02-25'},block_starts:{B1:{code:'A1',zone:'A',first:'2026-12-20'},B9:{code:'B3',zone:'B',first:'2027-02-25'}},
 blocks:[{block:'B1',bunches:97,kg:1940,cartons:194,containers:9.7}],totals:{bunches:97,kg:1940,cartons:194,containers:9.7,...money(layers)},warnings:['A1 màu Đỏ: 3 buồng đã qua 70 ngày mà chưa ghi thu hoạch.'],
 pace:{last_actual:{number:45,actual:298},next_need:{number:48,needed:3200},alert:true,times:11,weeks:[{week:'2026-W45',number:45,start:'2026-11-02',actual:298,needed:null,future:false},{week:'2026-W48',number:48,start:'2026-11-23',actual:0,needed:3200,future:true}]},
 weeks:[{week:'2026-W46',number:46,start:'2026-11-09',end:'2026-11-15',bunches:0,kg:0,cartons:0,containers:0,...money(empty)},{week:'2026-W52',number:52,start:'2026-12-21',end:'2026-12-27',bunches:97,kg:1940,cartons:194,containers:9.7,...money(layers)}],
 rows:[{week:'2026-W52',block:'B1',block_code:'A1',tag:'T1',ribbon:'Đỏ',cycle:2,layer:'cut',confidence:'high',bunches:60,kg:1176,cartons:90,overdue:false},{week:'2026-W52',block:'B5',block_code:'A5',tag:null,ribbon:'',cycle:2,layer:'tree',confidence:'low',bunches:37,kg:725.2,cartons:56.2,overdue:true}]}
const trace={week:'2026-W52',block:'B1',block_code:'A1',layer:'cut',note:'Mức tin cậy cao: buồng đã cắt bắp.',groups:[{key:'T1',ribbon:'Đỏ',in_week:60,facts:[['Đã cắt bắp',62],['Dự kiến còn thu',60],['Thu từ – đến','20/12 – 30/12']]}],
 lines:[{name:'x',bunch_tag:'T1',event_type:'Cut Bud',event_date:'2026-10-21',qty:62,source_type:'Opening Import',source_name:'so.xlsx'}],
 params:{profile:'LBFP-1',version:1,min_days:60,max_days:70,harvest_rate:.97,pack_rate:.98,kg_per_carton:13}}
let calls=[],replies={}
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.replace('/api/method/lotus_farm.','')
 calls.push({method,query:u.search,body:opts.body?JSON.parse(opts.body):null})
 if(!(method in replies))return {ok:false,status:404,json:async()=>({message:'Missing '+method})}
 return {ok:true,status:200,json:async()=>({message:replies[method]})}
}
const Weekly=await load('components/BunchWeeklyForecast.vue')
async function settle(){for(let i=0;i<8;i++)await tick()}
const open=(props={})=>{calls=[];return mount({setup:()=>()=>h(Weekly,{data,farm:'F',zones:['A','B'],...props})})}
const dialog=()=>document.querySelector('dialog[open]')
const button=(root,text)=>[...root.querySelectorAll('button')].find(b=>b.textContent.includes(text))
const column=(root,number)=>[...root.querySelectorAll('.bunch-col')].find(c=>c.querySelector('.bunch-col__name').textContent===String(number))

test('real numbers and estimates are separate figures, with no single total on top',async()=>{
 const view=open();await settle()
 const tiles=[...view.root.querySelectorAll('.land-stats>div')].map(t=>t.textContent)
 assert.equal(tiles.length,3)
 assert.match(tiles[0],/Chắc chắn\s*97 buồng/);assert.match(tiles[1],/Ước tính\s*0 buồng/)
 assert.match(tiles[2],/13\/64 lô.*Còn 51 lô chỉ có ước tính/)
 assert.match(view.root.textContent,/Chưa xác nhận, chưa tính vào dự thu: cắt bắp 120/)
 view.unmount()
})
test('one column per week; an empty week opens nothing and says so',async()=>{
 const view=open();await settle()
 assert.equal(view.root.querySelectorAll('.bunch-col').length,2)
 assert.equal(column(view.root,46).tagName,'DIV')
 assert.match(column(view.root,46).getAttribute('aria-label'),/Tuần 46.*chưa có số/)
 assert.match(column(view.root,52).getAttribute('aria-label'),/97 buồng, đã cắt 97/)
 assert.equal(view.root.querySelectorAll('.bunch-col__cap').length,1,'a number only on the tallest column')
 view.unmount()
})
test('hovering a column names every part',async()=>{
 const view=open();await settle()
 column(view.root,52).dispatchEvent(new window.Event('mouseenter'));await settle()
 assert.match(view.root.querySelector('.bunch-chart__tip').textContent,/Tuần 52.*97.*đã cắt/)
 column(view.root,52).dispatchEvent(new window.Event('mouseleave'));await settle()
 assert.equal(view.root.querySelector('.bunch-chart__tip'),null)
 view.unmount()
})
test('the unit changes the figures and the columns',async()=>{
 const view=open();await settle()
 button(view.root,'Cont').click();await settle()
 assert.match(view.root.querySelector('.land-stats').textContent,/9,7 cont/)
 assert.match(column(view.root,52).getAttribute('aria-label'),/9,7 cont/)
 button(view.root,'Kg').click();await settle()
 assert.match(view.root.querySelector('.land-stats').textContent,/1\.940 kg/)
 view.unmount()
})
test('khu buttons ask the page to filter',async()=>{
 const seen=[];const view=mount({setup:()=>()=>h(Weekly,{data,farm:'F',zones:['A','B'],zone:'',onZone:z=>seen.push(z)})});await settle()
 view.root.querySelector('[aria-label="Lọc theo khu"] button:nth-child(3)').click();await settle()
 assert.deepEqual(seen,['B'])
 view.unmount()
})
test('a khu with nothing in the weeks shows when it starts, and opens its lô',async()=>{
 const view=open();await settle()
 const rows=[...view.root.querySelectorAll('.bunch-zones button')]
 assert.match(rows[0].textContent,/Khu A.*97 buồng/);assert.match(rows[1].textContent,/Khu B.*Thu từ 25\/02/)
 rows[1].click();await settle()
 assert.match(dialog().textContent,/Khu B/);assert.match(dialog().textContent,/B3.*Thu từ 25\/02/)
 view.unmount()
})
test('with a khu chosen, the list of khu steps aside',async()=>{
 const view=open({zone:'A'});await settle()
 assert.equal(view.root.querySelector('.bunch-zones'),null)
 view.unmount()
})
test('the pace line warns, and opens week by week',async()=>{
 const view=open();await settle()
 const pace=view.root.querySelector('.bunch-pace')
 assert.match(pace.textContent,/Tuần 45: cắt thật 298/);assert.match(pace.textContent,/Tuần 48 cần: khoảng 3\.200/);assert.match(pace.textContent,/Gấp 11 lần/)
 pace.click();await settle()
 assert.match(dialog().textContent,/Tuần 45.*Cắt thật 298/);assert.match(dialog().textContent,/Tuần 48.*Cần 3\.200/)
 view.unmount()
})
test('a week opens in a dialog by lô and colour',async()=>{
 const view=open();await settle()
 column(view.root,52).click();await settle()
 assert.match(dialog().textContent,/Tuần 52 · 21\/12 – 27\/12/)
 assert.equal(dialog().querySelectorAll('.bunch-lines button').length,2)
 assert.match(dialog().textContent,/A1 · Đỏ.*Tin cậy cao/)
 assert.match(dialog().textContent,/A5.*Theo số cây · Tin cậy thấp.*quá hạn/)
 view.unmount()
})
test('a line shows where its number comes from, and comes back',async()=>{
 replies={'block_forecast.trace':trace}
 const view=open();await settle()
 column(view.root,52).click();await settle()
 dialog().querySelector('.bunch-lines button').click();await settle()
 assert.ok(calls[0].query.includes('week=2026-W52')&&calls[0].query.includes('layer=cut')&&calls[0].query.includes('tag=T1'))
 const text=dialog().textContent
 assert.match(text,/Đã cắt bắp\s*62/);assert.match(text,/Dự kiến còn thu\s*60/)
 assert.match(text,/21\/10\/2026 · Cắt bắp · 62 buồng · Sổ cắt bắp \(so\.xlsx\)/)
 assert.match(text,/LBFP-1 bản 1.*60–70 ngày/)
 button(dialog(),'Quay lại').click();await settle()
 assert.equal(dialog().querySelectorAll('.bunch-lines button').length,2)
 view.unmount()
})
test('the months view has the same chart, without weeks to open or the pace line',async()=>{
 const view=open({view:'months'});await settle()
 assert.equal(view.root.querySelectorAll('.bunch-col').length,1)
 assert.equal(view.root.querySelector('button.bunch-col'),null)
 assert.equal(view.root.querySelector('.bunch-pace'),null)
 assert.match(view.root.textContent,/12 tháng tới/)
 view.unmount()
})
test('the import button is for those who may import',async()=>{
 const none=open();await settle()
 assert.equal(button(none.root,'Nạp sổ cắt bắp'),undefined)
 none.unmount()
 const view=open({canImport:true});await settle()
 button(view.root,'Nạp sổ cắt bắp').click();await settle()
 assert.match(dialog().textContent,/File sổ cắt bắp/)
 assert.equal(dialog().querySelector('button[type=submit]').disabled,true,'nothing to write before a file is read')
 view.unmount()
})
test('the numbers stay reachable as a table, closed until asked for',async()=>{
 const view=open();await settle()
 const details=view.root.querySelector('details.bunch-chart__table')
 assert.equal(details.open,false);assert.equal(details.children.length,1)
 details.open=true;details.dispatchEvent(new window.Event('toggle'));await settle()
 assert.equal(details.children.length,2,'the shared data table appears')
 view.unmount()
})
