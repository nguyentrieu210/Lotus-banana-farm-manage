import test from 'node:test'
import assert from 'node:assert/strict'
import {newLine,lineFromAssignment,payload,rateFor,preview,totals,ribbonCount,boardRows} from '../src/field-report-model.js'

const rates=[
 {work_type:'CL',rate:300000,basis:'Area',norm_min:1,valid_from:'2026-10-21'},
 {work_type:'CL',rate:320000,basis:'Area',valid_from:'2026-12-01'},
 {work_type:'BB',rate:4000,basis:'Count',valid_from:'2026-10-21',valid_to:'2026-11-30'},
]
const blocks={A8:{name:'A8',area_ha:4.48,trees:10668}}
const ctx={rates,blocks,day:'2026-10-23'}
const task={name:'PG1',work_type:'CL',work_team:'T01',farm_block:'A8'}

test('price in force on the report day',()=>{
 assert.equal(rateFor(rates,'CL','2026-11-15').rate,300000)
 assert.equal(rateFor(rates,'CL','2026-12-02').rate,320000)
 assert.equal(rateFor(rates,'BB','2026-12-02'),null)
})

test('a phiếu giao row is prepared as CK when the việc has a price',()=>{
 const line=lineFromAssignment(task,ctx)
 assert.equal(line.assignment,'PG1');assert.equal(line.pay_kind,'Piece');assert.equal(line.farm_block,'A8');assert.equal(line.work_team,'T01')
 assert.equal(lineFromAssignment({...task,work_type:'XX'},ctx).pay_kind,'Daywork')
})

test('a lot priced per ha is paid once, for the whole lot, when ticked Xong',()=>{
 const line={...lineFromAssignment(task,ctx),workdays_am:9,qty:1.2}
 assert.equal(preview(line,ctx).amount,0,'progress day: nothing paid')
 assert.equal(preview({...line,qty:4},ctx).low,true,'4 ha in 9 công is below 1 ha/công')
 assert.equal(preview({...line,done:1},ctx).amount,1344000,'Xong: 4,48 ha × 300.000')
})

test('công nhật carries no money and counted bunch work is paid as reported',()=>{
 assert.equal(preview({...newLine(),work_type:'CL',pay_kind:'Daywork',farm_block:'A8',qty:2},ctx).amount,0)
 const bag=preview({...newLine('Bunch'),work_type:'BB',pay_kind:'Piece',farm_block:'A8',qty:120},ctx)
 assert.equal(bag.qty,120);assert.equal(bag.amount,480000)
 assert.equal(preview({...newLine(),work_type:'XX',pay_kind:'Piece',farm_block:'A8'},ctx).missingPrice,true)
})

test('payload drops untouched phiếu rows and sends the phiếu, Xong and the lot',()=>{
 const idle=lineFromAssignment(task,ctx)
 const worked={...lineFromAssignment({...task,name:'PG2'},ctx),workdays_am:'3',done:true,materials:[{item_code:'PHAN',qty:'3'},{item_code:'',qty:1}]}
 const other={...newLine(),editable:false}
 const sent=payload([idle,worked,other])
 assert.equal(sent.length,1)
 assert.equal(sent[0].assignment,'PG2');assert.equal(sent[0].done,1);assert.equal(sent[0].location,'Block');assert.equal(sent[0].workdays_am,3)
 assert.deepEqual(sent[0].materials,[{item_code:'PHAN',qty:3}])
 assert.ok(!('editable' in sent[0])&&!('section' in sent[0])&&!('fresh' in sent[0]))
})

test('totals add công, money and Xong, leaving out untouched rows',()=>{
 const lines=[{...lineFromAssignment(task,ctx),workdays_am:5,workdays_pm:4,done:1},lineFromAssignment({...task,name:'PG2'},ctx),
  {...newLine(),work_type:'CL',pay_kind:'Daywork',location:'Zone',zone:'A',workdays_am:3}]
 assert.deepEqual(totals(lines,ctx),{workdays:12,amount:1344000,low:0,done:1,lines:2})
})

test('bunches of a colour are counted against cắt bắp of that colour in that lô',()=>{
 const stages={CB:'Cut Bud',BB:'Bag',CD:'Prop'}
 const opts={stage:w=>stages[w],ribbon:'W44',cut:{'A8|W43':40},done:{'A8|W43|Bag':30}}
 const bag={...newLine('Bunch'),work_type:'BB',farm_block:'A8',bunch_tag:'W43',qty:10}
 assert.deepEqual(ribbonCount(bag,[bag],opts),{cut:40,total:40,over:false})
 assert.equal(ribbonCount({...bag,qty:11},[{...bag,qty:11}],opts).over,true)
 const cut={...newLine('Bunch'),work_type:'CB',farm_block:'A8',qty:20}
 const fresh={...bag,bunch_tag:'W44',qty:15}
 assert.deepEqual(ribbonCount(fresh,[cut,fresh],opts),{cut:20,total:15,over:false},'today\'s cắt bắp counts for today\'s colour')
 assert.equal(ribbonCount(cut,[cut],opts),null,'cắt bắp itself is not capped')
})

test('board rows put each phiếu under its lô and việc, latest first',()=>{
 const rows=boardRows({blocks:[{name:'A8',block_code:'A8'},{name:'A9',block_code:'A9'}],
  cells:[{farm_block:'A8',work_type:'CL',assigned_on:'2026-10-01',display:'Done'},{farm_block:'A8',work_type:'CL',assigned_on:'2026-10-20',display:'Working'},{farm_block:'B1',work_type:'CL'}]})
 assert.equal(rows.length,2)
 assert.deepEqual(rows[0].cells.CL.map(c=>c.display),['Working','Done'])
 assert.deepEqual(rows[1].cells,{})
})
