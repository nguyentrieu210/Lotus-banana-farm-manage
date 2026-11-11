import test from 'node:test'
import assert from 'node:assert/strict'
import {Window} from 'happy-dom'
const window=new Window()
Object.defineProperty(globalThis,'localStorage',{value:window.localStorage,configurable:true})
const m=await import('../src/issue-request-model.js')

test('the nine state codes of the server have a Vietnamese label and a tone',()=>{
 assert.deepEqual(m.STATES,['draft','sent','returned','waiting','picking','partial','done','closed','cancelled'])
 for(const key of m.STATES){assert.ok(m.STATE_LABELS[key],key);assert.ok(m.STATE_TONES[key],key)}
 assert.equal(m.stateLabel('sent'),'Chờ duyệt')
 assert.equal(m.stateKey({state:'Chờ cấp',state_code:'waiting'}),'waiting','state_code first')
 assert.equal(m.stateKey({state:'Kho đang lập phiếu'}),'picking','the label alone is enough')
 assert.equal(m.stateKey('Đã huỷ'),'cancelled')
 assert.equal(m.stateLabel({state:'Đã đóng',state_code:'closed'}),'Đã đóng')
 assert.equal(m.stateTone('returned'),'danger')
 assert.equal(m.stateTone({state_code:'done'}),'success')
})

test('"Quá hạn chưa cấp" only after approval, before the request is issued',()=>{
 assert.equal(m.isOverdue({state_code:'waiting',needed:'2026-11-10'},'2026-11-11'),true)
 assert.equal(m.isOverdue({state_code:'partial',needed:'2026-11-10'},'2026-11-11'),true)
 assert.equal(m.isOverdue({state_code:'done',needed:'2026-11-10'},'2026-11-11'),false)
 assert.equal(m.isOverdue({state_code:'sent',needed:'2026-11-10'},'2026-11-11'),false)
 assert.equal(m.isOverdue({state_code:'waiting',needed:'2026-11-11'},'2026-11-11'),false)
 assert.equal(m.isOverdue({state_code:'sent',overdue:true}),true,'the server flag wins')
})

test('count cards come from the server counts or from the rows',()=>{
 const rows=[{state_code:'sent',can_approve:true},{state_code:'sent'},{state_code:'returned'},{state_code:'waiting'},{state_code:'picking'},{state_code:'partial'},{state_code:'done'}]
 assert.deepEqual(m.countRequests(rows),{approve:1,sent:2,returned:1,waiting:1,issuing:2,done:1})
 const server={draft:1,sent:9,returned:0,waiting:2,picking:1,partial:3,done:4,closed:0,cancelled:0,approve:5,overdue:1}
 assert.deepEqual(m.countRequests(rows,server),{approve:5,sent:9,returned:0,waiting:2,issuing:4,done:4})
})

test('detail lines, stock and warnings as the server sends them',()=>{
 assert.deepEqual(m.detailLines({lines:2,items:[{name:'L1'}]}),[{name:'L1'}])
 assert.deepEqual(m.stockFor({ANVIL:{available:12,approved_waiting:5}},'ANVIL'),{available:12,waiting:5})
 assert.equal(m.stockFor({},'X'),null)
 assert.equal(m.warningText({kind:'stock',message:'Kho còn 1'}),'Kho còn 1')
})

test('split by area keeps the total exactly',()=>{
 const blocks=[{key:'A',area:1},{key:'B',area:2},{key:'C',area:3}]
 const r=m.splitByArea(6,blocks)
 assert.deepEqual(r.qty,{A:1,B:2,C:3})
 const odd=m.splitByArea(1,[{key:'A',area:1},{key:'B',area:1},{key:'C',area:1}])
 assert.equal(m.sumQty(odd.qty),1)
 assert.ok(Object.values(odd.qty).every(v=>Math.round(v*1000)===v*1000),'thousandths only')
})

test('whole units split by largest remainder and still add up',()=>{
 const r=m.splitByArea(5,[{key:'A',area:1.2},{key:'B',area:1.3},{key:'C',area:2.5}],true)
 assert.ok(Object.values(r.qty).every(Number.isInteger))
 assert.equal(m.sumQty(r.qty),5)
 assert.deepEqual(r.qty,{A:1,B:1,C:3})
 const tiny=m.splitByArea(1,[{key:'A',area:1},{key:'B',area:3}],true)
 assert.deepEqual(tiny.qty,{B:1});assert.deepEqual(tiny.dropped,['A'],'a lô left with 0 is reported, not given a line')
 assert.ok(m.isWholeUnit('Chai'));assert.ok(m.isWholeUnit('Gói'));assert.ok(!m.isWholeUnit('Litre'));assert.ok(m.isWholeUnit('Litre',true))
})

test('a lô without area takes no share and is named',()=>{
 const r=m.splitByArea(6,[{key:'A',area:2},{key:'B',area:0}])
 assert.deepEqual(r.qty,{A:6});assert.deepEqual(r.missing,['B'])
})

test('lines are one per vật tư × lô with a quantity; more than 100 is refused',()=>{
 const lines=m.buildLines([{item_code:'ANVIL',qty:{A12:1.5,A13:1.5,A14:0},notes:' 0,5 l/ha '}],['A12','A13','A14'],{A12:'WA-1'})
 assert.deepEqual(lines,[{item_code:'ANVIL',farm_block:'A12',qty:1.5,notes:'0,5 l/ha',assignment:'WA-1'},{item_code:'ANVIL',farm_block:'A13',qty:1.5,notes:'0,5 l/ha',assignment:null}])
 assert.match(m.linesProblem([]),/ít nhất một lô/)
 assert.match(m.linesProblem(Array.from({length:101},()=>({}))),/Tách thành hai yêu cầu/)
 assert.equal(m.linesProblem(lines),'')
 const values=m.requestValues({team:'T3',work_type:'PHUN',needed:'2026-11-12',warehouse:'K',receiver:'EMP',note:' phun '},lines)
 assert.deepEqual(Object.keys(values),['team','work_type','needed','warehouse','receiver','note','lines'])
 assert.equal(values.note,'phun')
})

test('saved lines rebuild the materials of the form',()=>{
 const mats=m.materialsFromLines([{item_code:'X',item_name:'Anvil',stock_uom:'Litre',farm_block:'A12',qty:1.5,notes:'liều'},{item_code:'X',farm_block:'A13',qty:1}])
 assert.equal(mats.length,1);assert.deepEqual(mats[0].qty,{A12:1.5,A13:1});assert.equal(mats[0].notes,'liều')
})

test('the approver may only lower or drop a line',()=>{
 const old=[{name:'L1',item_code:'X',farm_block:'A12',qty:1.5},{name:'L2',item_code:'X',farm_block:'A13',qty:1.5}]
 assert.deepEqual(m.lowered(old,{L1:1.5,L2:1}),{error:'',lines:[{name:'L2',qty:1}]})
 assert.deepEqual(m.lowered(old,{L1:0,L2:1.5}).lines,[{name:'L1',qty:0}])
 assert.match(m.lowered(old,{L1:2}).error,/Trả lại/)
 assert.match(m.lowered(old,{L1:-1}).error,/không hợp lệ/)
})

test('a retry of the same command reuses its client_event_id; another body gets a new one',()=>{
 const first=m.eventFor(null,{a:1})
 assert.equal(m.eventFor(first,{a:1}),first)
 assert.notEqual(m.eventFor(first,{a:2}).id,first.id)
})

test('the form being typed is kept on the device per farm, đội and request',()=>{
 const key=m.draftKey('F','C','')
 assert.equal(key,'issue-request:F:C:new')
 m.keepLocal(key,{work_type:'PHUN'})
 assert.deepEqual(m.readLocal(key),{work_type:'PHUN'})
 m.dropLocal(key)
 assert.equal(m.readLocal(key),null)
})

test('short labels',()=>{
 assert.equal(m.shortDate('2026-11-05'),'05/11')
 assert.equal(m.blockList({blocks:['A12',{block_code:'A13'}]}),'A12, A13')
 assert.equal(m.crewTeam({crew_name:'Đội A + B',team_name:'Tổ 3'}),'Đội A + B · Tổ 3')
 assert.equal(m.crewTeam({crew_name:'Đội A + B'}),'Đội A + B · Cả đội')
})
