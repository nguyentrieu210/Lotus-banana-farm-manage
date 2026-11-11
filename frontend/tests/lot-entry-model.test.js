import test from 'node:test'
import assert from 'node:assert/strict'
import {workSchema,blankLine,linesFromLot,payloadLines,fingerprint,defaultPeople,peopleCount,colourRoom,colourChoices,colourCheck,lotSummary,saveDraft,loadDraft,clearDraft,swatch} from '../src/lot-entry-model.js'

const lot={block:'A5',code:'A5',colours:[{tag:'red',label:'Đỏ',week:43,left:40,bag_left:0},{tag:'white',label:'Trắng',week:44,left:0,bag_left:12}],
 assignments:[{kind:'Round',work_type:'CL'},{kind:'Bunch'}],quarantine_until:'2026-11-20',
 lines:[{name:'e1',state:'Draft',work_type:'CB',stage:'Cut Bud',qty:120,bunch_tag:'red',people:[{employee:'E1',morning:1,afternoon:0}],materials:[]},
  {name:'e2',state:'Confirmed',work_type:'TH',stage:'Harvest',qty:10,weight_kg:200}]}

test('each việc asks for its own inputs',()=>{
 assert.equal(workSchema({stage:'Cut Bud'}).autoColour,true)
 assert.equal(workSchema({stage:'Bag'}).pickColour,true)
 assert.deepEqual([workSchema({stage:'Harvest'}).kg,workSchema({stage:'Harvest'}).pickColour],[true,true])
 assert.equal(workSchema({stage:'Reject'}).reason,true)
 assert.equal(workSchema({stage:'Sucker Select'}).kind,'sucker')
 assert.equal(workSchema({records_disease:1,group:'Protection'}).kind,'disease')
 assert.equal(workSchema({records_disease:1,group:'Protection'}).materials,false,'sâu bệnh has no materials')
 assert.deepEqual([workSchema({group:'Protection',requires_material:1}).materials,workSchema({group:'Protection',requires_material:1}).materialsRequired],[true,true])
 assert.equal(workSchema({group:'Field'}).done,true)
 assert.equal(workSchema({stage:'Bud Injection'}).done,false,'bunch work has no "xong cả lô"')
})

test('draft lines are editable, sent and confirmed ones are not',()=>{
 const {editable,locked}=linesFromLot(lot)
 assert.equal(editable.length,1);assert.equal(locked.length,1)
 assert.deepEqual(editable[0].people,{E1:{morning:1,afternoon:0}})
 assert.equal(locked[0].state,'Confirmed')
})

test('the payload has numbers, people with a buổi and materials with an item',()=>{
 const line={...blankLine({name:'PB'}),qty:'2,5',done:true,materials:[{item_code:'THUOC',qty:'1,5',dose:'50 ml/bình'},{item_code:''}],
  people:{E1:{morning:1,afternoon:0},E2:{morning:0,afternoon:0}}}
 const [sent]=payloadLines([line,{...blankLine(),work_type:''}])
 assert.equal(sent.qty,2.5);assert.equal(sent.done,1)
 assert.deepEqual(sent.people,[{employee:'E1',morning:1,afternoon:0}])
 assert.deepEqual(sent.materials,[{item_code:'THUOC',qty:1.5,dose:'50 ml/bình',stock_entry:null}])
 assert.equal(payloadLines([{...blankLine(),work_type:''}]).length,0,'a line with no việc is not sent')
 assert.equal(fingerprint([{...line,key:'x'}]),fingerprint([{...line,key:'y'}]),'keys do not make a line dirty')
})

test('people: the tổ\'s present members on the buổi they were present',()=>{
 const people=defaultPeople([{employee:'E1',own:true,morning:true,afternoon:false},{employee:'E3',own:false,morning:true,afternoon:true}])
 assert.deepEqual(people,{E1:{morning:1,afternoon:0}})
 assert.equal(peopleCount({E1:{morning:1,afternoon:1},E2:{morning:1}}),3)
})

test('colours: bao buồng picks unbagged colours, thu hoạch colours still on the plants; a line keeps its own',()=>{
 assert.deepEqual(colourChoices(lot,'Bag','').map(c=>c.value),['white'])
 assert.deepEqual(colourChoices(lot,'Harvest','').map(c=>c.value),['red'])
 assert.deepEqual(colourChoices(lot,'Harvest','white').map(c=>c.value),['red','white'])
})
test('colours: two batches of one colour and week are told apart by their lần',()=>{
 const twice={colours:[{tag:'tim45-1',label:'Tím',code:'TIM',week:45,lan:1,left:21,bag_left:21},{tag:'tim45-2',label:'Tím',code:'TIM',week:45,lan:2,left:31,bag_left:31}],lines:[]}
 const choices=colourChoices(twice,'Harvest','')
 assert.deepEqual(choices.map(c=>c.label),['Tím · tuần 45 lần 1 · còn 21','Tím · tuần 45 lần 2 · còn 31'])
 assert.deepEqual(choices.map(c=>[c.code,c.lan,c.left]),[['TIM',1,21],['TIM',2,31]],'the phone ribbon picker gets the colour, lần and what is left')
})
test('buồng left: own drafts come back, every line of the dialog on the colour is taken off, too many is an error',()=>{
 const harvested={...lot,lines:[{name:'d1',state:'Draft',stage:'Harvest',qty:15,bunch_tag:'red'},{name:'s1',state:'Sent',stage:'Harvest',qty:5,bunch_tag:'red'}]}
 const room=colourRoom(harvested)
 assert.equal(room.red.left,55,'the server count of 40 already took the draft of 15 off; the sent 5 stays off')
 assert.match(colourChoices(harvested,'Harvest','',room)[0].label,/còn 55/)
 const stageOf=l=>({TH:'Harvest',HB:'Reject',BB:'Bag'})[l.work_type]
 const lines=[{work_type:'TH',bunch_tag:'red',qty:50},{work_type:'HB',bunch_tag:'red',reject_stage:'After Cut',qty:3},{work_type:'HB',bunch_tag:'red',reject_stage:'Before Cut',qty:9}]
 assert.deepEqual(colourCheck(room,lines,stageOf,lines[0]),{hint:'Còn 55 buồng trên cây, lưu xong còn 2',error:''},'hủy trước cắt bắp takes nothing off a colour')
 lines[0].qty=60
 assert.match(colourCheck(room,lines,stageOf,lines[0]).error,/Vượt 8 buồng: màu này chỉ còn 55 buồng trên cây/)
 assert.match(colourCheck(room,[{work_type:'BB',bunch_tag:'white',qty:13}],stageOf,{work_type:'BB',bunch_tag:'white',qty:13}).error,/Vượt 1 buồng.*12 buồng chưa bao/)
 assert.deepEqual(colourCheck(room,lines,stageOf,{work_type:'TH',bunch_tag:''}),{hint:'',error:''})
})

test('a lô card says what was entered and what holds the lô',()=>{
 const s=lotSummary(lot)
 assert.equal(s.count,2);assert.equal(s.state,'Draft');assert.equal(s.due,1);assert.equal(s.held,true)
 assert.equal(lotSummary({lines:[]}).state,'')
})

test('a draft survives on the phone until it is cleared, and a broken storage is ignored',()=>{
 const store={};globalThis.localStorage={getItem:k=>store[k]??null,setItem:(k,v)=>{store[k]=v},removeItem:k=>{delete store[k]}}
 saveDraft('R1','A5',[{work_type:'CB',qty:3}],'m1')
 assert.equal(loadDraft('R1','A5','m1').lines[0].qty,3)
 assert.equal(loadDraft('R1','A5','m2'),null,'a report changed on the server since the draft wins')
 clearDraft('R1','A5')
 assert.equal(loadDraft('R1','A5'),null)
 globalThis.localStorage={getItem(){throw new Error('blocked')},setItem(){throw new Error('blocked')},removeItem(){throw new Error('blocked')}}
 assert.doesNotThrow(()=>saveDraft('R1','A5',[]));assert.equal(loadDraft('R1','A5'),null);assert.doesNotThrow(()=>clearDraft('R1','A5'))
 delete globalThis.localStorage
})

test('ribbon codes become colours; two-colour ribbons show half each',()=>{
 // Spec 004: colours are tokens (lotus-tokens.css --lotus-ribbon-*), so dark and outdoor modes follow.
 assert.equal(swatch('CAM'),'var(--lotus-ribbon-cam)')
 assert.equal(swatch('DO_XANH_LA'),'linear-gradient(90deg,var(--lotus-ribbon-do) 0% 50%,var(--lotus-ribbon-xanh-la) 50% 100%)')
 assert.equal(swatch('XANH_LA_XANH_DUONG'),'linear-gradient(90deg,var(--lotus-ribbon-xanh-la) 0% 50%,var(--lotus-ribbon-xanh-duong) 50% 100%)')
 assert.equal(swatch('#123456'),'#123456')
 assert.equal(swatch('LA'),'transparent');assert.equal(swatch(''),'transparent')
})
