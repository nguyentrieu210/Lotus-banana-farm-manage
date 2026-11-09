import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document,window} from './support/mount.mjs'
import {formFromRows,sheetRows,sheetFingerprint,colourOptions,kindOf} from '../src/bunch-sheet-model.js'

const T1='team-1',A1='block-a1',A5='block-a5'
const sheet=(rows=[],extra={})=>({date:'2026-11-09',farm:'F',crew:'C',user:'leader@x',
 blocks:[{name:A1,code:'A1',zone:'A',trees:100,cycle:2},{name:A5,code:'A5',zone:'A',trees:100,cycle:2}],
 ribbon:{name:'tag-w',label:'Trắng',code:'#fff',week:46},tags:[{name:'tag-w',label:'Trắng',code:'#fff',week:46}],
 reasons:[{name:'r1',reason_name:'Gãy đổ'}],teams:[{name:T1,label:'Tổ 01'}],rows,suckers:[],cut_left:{[A5+'|tag-w']:120},rights:{supervisor:true},...extra})
const line=(values)=>({name:'e'+Math.random(),work_team:T1,source_type:'Manual',state:'Draft',farm_block:A1,block_code:'A1',team_name:'Tổ 01',entered_by:'to@x',entered_name:'Tổ trưởng',qty:5,event_type:'Bud Injection',...values})

let calls=[],replies={}
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.replace('/api/method/lotus_farm.bunch_posting.','')
 calls.push({method,body:opts.body?JSON.parse(opts.body):null})
 if(method==='day_status'&&!(method in replies))return {ok:true,status:200,json:async()=>({message:{date:'2026-11-08',pending:0,not_reported:[],anomalies:[]}})}
 if(!(method in replies))return {ok:false,status:404,json:async()=>({message:'Missing '+method})}
 return {ok:true,status:200,json:async()=>({message:typeof replies[method]==='function'?replies[method]():replies[method]})}
}
const Page=await load('components/field/WorkBunch.vue')
async function settle(){for(let i=0;i<8;i++)await tick()}
const button=(root,text)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(text))
function type(input,value){input.value=value;input.dispatchEvent(new window.Event('input',{bubbles:true}));input.dispatchEvent(new window.Event('change',{bubbles:true}))}
const dialog=()=>document.querySelector('dialog.work-bunch-modal[open]')
const lots=()=>[...dialog().querySelectorAll('.work-bunch__grid input')]
function open(){calls=[];return mount({setup:()=>()=>h(Page,{farm:'F',crew:'C',setup:{supervised_crews:['C']},date:'2026-11-09','onUpdate:date':()=>{}})})}
async function openKind(view,label){button(view.root,label).click();await settle();assert.ok(dialog(),'the việc opens in a dialog')}
const submit=()=>dialog().querySelector('button[type=submit]')

test('model: open lines go back to the server, confirmed ones never do',()=>{
 const form=formFromRows([line({qty:5}),line({farm_block:A5,qty:9,state:'Confirmed'}),line({event_type:'Cut Bud',qty:3,bunch_tag:'tag-w'})],T1)
 assert.deepEqual(form.inject,{[A1]:5});assert.deepEqual(form.locked.inject,{[A5]:9})
 const rows=sheetRows(form)
 assert.equal(rows.length,2);assert.ok(rows.every(r=>r.block===A1))
 assert.equal(sheetFingerprint(formFromRows([line({qty:5})],T1)),sheetFingerprint(formFromRows([line({qty:'5'})],T1)))
})
test('model: another tổ and empty numbers are left out',()=>{
 assert.deepEqual(sheetRows(formFromRows([line({work_team:'other'})],T1)),[])
 const form=formFromRows([],T1);form.inject[A1]='';form.cut[A5]=0
 assert.deepEqual(sheetRows(form),[])
})
test('model: only colours still on the lô are offered',()=>{
 const s=sheet()
 assert.equal(colourOptions(s,A5,'').length,1)
 assert.equal(colourOptions(s,A1,'').length,0)
 assert.equal(colourOptions(s,A1,'tag-w').length,1,'a line already on a colour keeps it')
})
test('model: a line maps to its dialog; Chọn F from a phiếu has none',()=>{
 assert.equal(kindOf(line({})),'inject');assert.equal(kindOf(line({event_type:'Harvest'})),'harvest')
 assert.equal(kindOf(line({event_type:'Sucker Select',source_type:'Work Entry'})),null)
})

test('page has no entry grid until a việc is opened',async()=>{
 replies={day_sheet:()=>sheet()}
 const view=open();await settle()
 assert.equal(view.root.querySelectorAll('.work-bunch__grid').length,0)
 assert.equal(dialog(),null)
 view.unmount()
})
test('entry: numbers for many lô are saved from the dialog, which then closes',async()=>{
 replies={day_sheet:()=>sheet(),save_day:{saved:2,removed:0,errors:[]}}
 const view=open();await settle()
 await openKind(view,'Chích bắp')
 assert.equal(lots().length,2,'one field per lô')
 assert.equal(submit().disabled,true,'nothing to save yet')
 type(lots()[0],'12');type(lots()[1],'8');await settle()
 submit().click();await settle()
 const saved=calls.find(c=>c.method==='save_day')
 assert.equal(saved.body.team,T1)
 assert.deepEqual(saved.body.rows.map(r=>[r.block,r.event_type,Number(r.qty)]),[[A1,'Bud Injection',12],[A5,'Bud Injection',8]])
 assert.equal(dialog(),null);assert.match(view.root.textContent,/Đã lưu/)
 view.unmount()
})
test('entry: saving one việc keeps the open lines of the others',async()=>{
 replies={day_sheet:()=>sheet([line({event_type:'Cut Bud',farm_block:A5,qty:40,bunch_tag:'tag-w'})]),save_day:{saved:1,removed:0,errors:[]}}
 const view=open();await settle()
 await openKind(view,'Chích bắp')
 type(lots()[0],'3');await settle()
 submit().click();await settle()
 assert.deepEqual(calls.find(c=>c.method==='save_day').body.rows.map(r=>r.event_type).sort(),['Bud Injection','Cut Bud'])
 view.unmount()
})
test('entry: server errors stay in the dialog with the numbers typed',async()=>{
 replies={day_sheet:()=>sheet(),save_day:{saved:0,removed:0,errors:[{index:0,block:'A1',message:'Số buồng phải là số nguyên lớn hơn 0.'}]}}
 const view=open();await settle()
 await openKind(view,'Chích bắp')
 type(lots()[0],'2.5');await settle()
 submit().click();await settle()
 assert.match(dialog().querySelector('.work-bunch__errors').textContent,/A1:.*số nguyên/)
 assert.equal(lots()[0].value,'2.5')
 view.unmount()
})
test('entry: closing with unsaved numbers asks first',async()=>{
 replies={day_sheet:()=>sheet()}
 const view=open();await settle()
 await openKind(view,'Chích bắp')
 type(lots()[0],'7');await settle()
 button(dialog(),'Hủy').click();await settle()
 assert.ok(dialog(),'still open');assert.match(dialog().textContent,/chưa được lưu/)
 button(dialog(),'Bỏ thay đổi').click();await settle()
 assert.equal(dialog(),null)
 view.unmount()
})
test('entry: a confirmed lô is locked; the ribbon shows on cắt bắp',async()=>{
 replies={day_sheet:()=>sheet([line({event_type:'Cut Bud',farm_block:A5,qty:120,state:'Confirmed',bunch_tag:'tag-w'})])}
 const view=open();await settle()
 await openKind(view,'Cắt bắp')
 assert.match(dialog().querySelector('.work-bunch__ribbon').textContent,/Trắng.*tuần 46/)
 assert.equal(lots()[1].disabled,true);assert.equal(lots()[1].value,'120');assert.equal(lots()[0].disabled,false)
 view.unmount()
})
test('entry: cắt bắp is closed when the day has no ribbon',async()=>{
 replies={day_sheet:()=>sheet([],{ribbon:null})}
 const view=open();await settle()
 await openKind(view,'Cắt bắp')
 assert.match(dialog().textContent,/chưa có màu dây/)
 assert.ok(lots().every(i=>i.disabled))
 view.unmount()
})
test('entry: reject and harvest open with a first line, lines can be removed',async()=>{
 replies={day_sheet:()=>sheet()}
 const view=open();await settle()
 await openKind(view,'Hủy buồng')
 assert.equal(dialog().querySelectorAll('.work-bunch__line').length,1)
 button(dialog(),'Thêm dòng').click();await settle()
 assert.equal(dialog().querySelectorAll('.work-bunch__line').length,2)
 button(dialog(),'Bỏ dòng').click();await settle()
 assert.equal(dialog().querySelectorAll('.work-bunch__line').length,1)
 button(dialog(),'Hủy').click();await settle()
 await openKind(view,'Thu hoạch')
 assert.match(dialog().textContent,/Khối lượng/)
 view.unmount()
})

test('confirm: counts only lines the đội trưởng did not enter',async()=>{
 replies={day_sheet:()=>sheet([line({}),line({entered_by:'leader@x',farm_block:A5,block_code:'A5'})]),confirm_day:{confirmed:1,suckers:0,errors:[{block:'A5',message:'bạn đã tự nhập'}]}}
 const view=open();await settle()
 const go=button(view.root,'Xác nhận 1 dòng')
 assert.ok(go,'one line can be confirmed');go.click();await settle()
 assert.ok(calls.some(c=>c.method==='confirm_day'))
 assert.match(view.root.textContent,/Đã xác nhận 1 dòng/)
 assert.match(view.root.querySelector('.work-bunch__errors').textContent,/A5/)
 view.unmount()
})
test('checks: the đội trưởng sees yesterday\'s list in a dialog',async()=>{
 replies={day_sheet:()=>sheet(),day_status:{date:'2026-11-08',pending:0,not_reported:[{block:'B3',team:'Tổ 2'}],anomalies:[{block:'A5',kind:'inject',message:'Chích bắp lũy kế 9.200 vượt số cây 9.118.'}]}}
 const view=open();await settle()
 assert.ok(calls.find(c=>c.method.startsWith('day_status')))
 button(view.root,'Cần kiểm tra').click();await settle()
 assert.match(dialog().textContent,/B3 · Tổ 2/);assert.match(dialog().textContent,/A5:.*vượt số cây/)
 view.unmount()
})
test('checks: a tổ trưởng is not asked for the list',async()=>{
 replies={day_sheet:()=>sheet([],{rights:{supervisor:false}})}
 const view=open();await settle()
 assert.ok(!calls.some(c=>c.method.startsWith('day_status')));assert.equal(button(view.root,'Cần kiểm tra'),undefined)
 view.unmount()
})
test('confirm: a warning about the numbers is shown after confirming',async()=>{
 replies={day_sheet:()=>sheet([line({})]),day_status:{date:'x',pending:1,not_reported:[],anomalies:[]},confirm_day:{confirmed:1,suckers:0,errors:[],warnings:[{block:'A1',kind:'inject',message:'Chích bắp lũy kế 200 vượt số cây 100.'}]}}
 const view=open();await settle()
 button(view.root,'Xác nhận 1 dòng').click();await settle()
 assert.match(view.root.textContent,/A1:.*vượt số cây 100/)
 view.unmount()
})
test('confirm: a tổ trưởng has no confirm button',async()=>{
 replies={day_sheet:()=>sheet([line({})],{rights:{supervisor:false}})}
 const view=open();await settle()
 assert.equal(button(view.root,'Xác nhận'),undefined)
 view.unmount()
})
test('confirm: nothing to confirm keeps the button off',async()=>{
 replies={day_sheet:()=>sheet([line({state:'Confirmed'})])}
 const view=open();await settle()
 assert.equal(button(view.root,'Xác nhận 0 dòng').disabled,true)
 view.unmount()
})
test('confirm: the pending Chọn F shows with its estimate',async()=>{
 replies={day_sheet:()=>sheet([],{suckers:[{name:'x',block_code:'A6',qty:2,estimate:4000,team_name:'Tổ 01',entered_name:'T',entered_by:'to@x'}]})}
 const view=open();await settle()
 assert.match(view.root.textContent,/A6.*Chọn chồi.*2 ha.*4\.000/)
 assert.ok(button(view.root,'Xác nhận 1 dòng'))
 view.unmount()
})
