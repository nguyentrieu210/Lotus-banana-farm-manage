import test from 'node:test'
import assert from 'node:assert/strict'
import {newLine,payload,rateFor,preview,totals} from '../src/field-report-model.js'

const rates=[
 {work_type:'CL',rate:300000,basis:'Area',norm_min:1,valid_from:'2026-10-21'},
 {work_type:'CL',rate:320000,basis:'Area',valid_from:'2026-12-01'},
 {work_type:'BB',rate:4000,basis:'Count',valid_from:'2026-10-21',valid_to:'2026-11-30'},
]
const blocks={A8:{name:'A8',area_ha:4.48,trees:10668}}

test('price in force on the report day',()=>{
 assert.equal(rateFor(rates,'CL','2026-11-15').rate,300000)
 assert.equal(rateFor(rates,'CL','2026-12-02').rate,320000)
 assert.equal(rateFor(rates,'BB','2026-12-02'),null)
})

test('công khoán by ha defaults to the whole lot and is paid ha × price',()=>{
 const line={...newLine(),work_type:'CL',pay_kind:'Piece',farm_block:'A8',workdays_am:9}
 const p=preview(line,{rates,blocks,day:'2026-10-23'})
 assert.equal(p.qty,4.48)
 assert.equal(p.amount,1344000)
 assert.equal(p.low,true,'4,48 ha in 9 công is below 1 ha/công')
 const part=preview({...line,qty:1.18},{rates,blocks,day:'2026-10-23'})
 assert.equal(part.amount,354000,'a partly done lot pays the part')
})

test('công nhật carries no money and counted work has no whole-lot default',()=>{
 assert.equal(preview({...newLine(),work_type:'CL',pay_kind:'Daywork',farm_block:'A8',qty:2},{rates,blocks,day:'2026-10-23'}).amount,0)
 const bag=preview({...newLine('Bunch'),work_type:'BB',pay_kind:'Piece',farm_block:'A8',qty:120},{rates,blocks,day:'2026-10-23'})
 assert.equal(bag.qty,120);assert.equal(bag.amount,480000)
 assert.equal(preview({...newLine(),work_type:'XX',pay_kind:'Piece',farm_block:'A8'},{rates,blocks,day:'2026-10-23'}).missingPrice,true)
})

test('payload sends only own editable lines with numbers and a piece line pinned to one lot',()=>{
 const own={...newLine(),work_type:'CL',pay_kind:'Piece',location:'Zone',farm_block:'A8',qty:'2,5'.replace(',','.'),materials:[{item_code:'PHAN',qty:'3'},{item_code:'',qty:1}]}
 const other={...newLine(),editable:false}
 const sent=payload([own,other])
 assert.equal(sent.length,1)
 assert.equal(sent[0].location,'Block')
 assert.equal(sent[0].qty,2.5)
 assert.deepEqual(sent[0].materials,[{item_code:'PHAN',qty:3}])
 assert.ok(!('editable' in sent[0])&&!('section' in sent[0]))
})

test('totals add công and money',()=>{
 const lines=[{...newLine(),work_type:'CL',pay_kind:'Piece',farm_block:'A8',workdays_am:5,workdays_pm:4},{...newLine(),work_type:'CL',pay_kind:'Daywork',location:'Zone',zone:'A',workdays_am:3}]
 assert.deepEqual(totals(lines,{rates,blocks,day:'2026-10-23'}),{workdays:12,amount:1344000,low:1,lines:2})
})
