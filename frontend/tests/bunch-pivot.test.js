import test from 'node:test'
import assert from 'node:assert/strict'
import {categories,chart,dimensionsFor,heat,kgPerBunch,label,lots,notApplicable,pivotChart,ribbonColour,table,total} from '../src/bunch-pivot.js'

const row=(s,z,b,q,extra={})=>({w:'2026-W45',m:'2026-11',z,b,t:'Tổ 01',c:'Đỏ',l:'1',s,q,k:0,...extra})
const rows=[row('cut','A','A1',10),row('cut','A','A10',5),row('cut','B','B2',7,{w:'2026-W46',t:'Tổ 02'}),row('inject','A','A1',3,{c:''})]

test('khu always shows every khu, even with nothing yet',()=>{
 assert.deepEqual(categories(rows,'z',['A','B','C']),['A','B','C'])
})
test('weeks stay in calendar order',()=>{
 assert.deepEqual(categories([row('cut','A','A1',1,{w:'2026-W46'}),row('cut','A','A1',1,{w:'2026-W43'})],'w'),['2026-W43','2026-W46'])
})
test('months keep the empty ones in between, across a new year',()=>{
 assert.deepEqual(categories([row('cut','A','A1',1,{m:'2026-11'}),row('cut','A','A1',1,{m:'2027-02'})],'m'),['2026-11','2026-12','2027-01','2027-02'])
})
test('labels are for people',()=>{
 assert.equal(label('w','2026-W05'),'T5');assert.equal(label('m','2026-11'),'Tháng 11/26');assert.equal(label('z','A'),'Khu A');assert.equal(label('c',''),'(Không có)')
})
test('a stage adds up per column',()=>{
 const c=chart(rows,'cut','z','',['A','B','C'])
 assert.deepEqual(c.series[0].data,[15,7,0]);assert.equal(c.stacked,false)
})
test('splitting stacks each column and keeps the total',()=>{
 const c=chart(rows,'cut','w','z',['2026-W45','2026-W46'])
 assert.equal(c.stacked,true)
 assert.deepEqual(c.series.map(s=>[s.name,s.data]),[['Khu A',[15,0]],['Khu B',[0,7]]])
})
test('splitting by the shown dimension is no split',()=>{
 assert.equal(chart(rows,'cut','z','z',['A','B']).stacked,false)
})
test('more than five tổ fold into Khác',()=>{
 const many=[1,2,3,4,5,6,7].map(n=>row('cut','A','A1',n,{t:'Tổ '+n}))
 const c=chart(many,'cut','z','t',['A'])
 assert.equal(c.series.length,6)
 assert.deepEqual(c.series.at(-1),{name:'Khác',data:[3],other:true},'the two smallest')
 assert.equal(c.series.reduce((n,s)=>n+s.data[0],0),28)
})
test('all five khu keep their own colour',()=>{
 const five=['A','B','C','D','E'].map((z,i)=>row('cut',z,z+'1',i+1))
 assert.deepEqual(chart(five,'cut','w','z',['2026-W45']).series.map(s=>s.name),['Khu A','Khu B','Khu C','Khu D','Khu E'])
})
test('lần cắt names read as lần',()=>{
 assert.deepEqual(chart(rows,'cut','z','l',['A','B']).series.map(s=>s.name),['Lần 1'])
})
test('a column opens its lô in natural order',()=>{
 assert.deepEqual(lots(rows,'cut','z','A').map(l=>[l.code,l.qty]),[['A1',10],['A10',5]])
})
test('stages with no ribbon or no tổ say so',()=>{
 assert.equal(notApplicable('inject','c'),true);assert.equal(notApplicable('prop','c'),true);assert.equal(notApplicable('cut','c'),false)
 assert.equal(notApplicable('left','t'),true);assert.equal(notApplicable('inject','z'),false)
})
test('kg per bunch per column, none where nothing was harvested',()=>{
 assert.deepEqual(kgPerBunch([row('harvest','A','A1',10,{k:205})],'z',['A','B']),[20.5,null])
})
test('the table has one row per column and one figure per stage',()=>{
 const t=table(rows,'z',['A','B'])
 assert.deepEqual([t[0].name,t[0].cut,t[0].inject,t[1].cut],['Khu A',15,3,7])
 assert.equal(total(rows,'cut'),22)
})
test('what each công đoạn can be cut by',()=>{
 assert.deepEqual(dimensionsFor('inject').map(d=>d.id),['z','w','m','t','b'])
 assert.ok(dimensionsFor('reject').some(d=>d.id==='r'));assert.ok(!dimensionsFor('cut').some(d=>d.id==='r'))
 assert.ok(!dimensionsFor('left').some(d=>d.id==='t'))
})
test('a chart by lô shows the largest fifteen and folds the rest',()=>{
 const many=Array.from({length:20},(_,i)=>row('cut','A','L'+i,i+1))
 const c=pivotChart(many,{stage:'cut',dim:'b'})
 assert.equal(c.keys.length,16);assert.equal(c.keys[0],'L19');assert.equal(c.names.at(-1),'Khác')
 assert.equal(c.series[0].data.reduce((n,v)=>n+v,0),210,'nothing lost')
})
test('khu stays in order and shows the empty ones',()=>{
 assert.deepEqual(pivotChart(rows,{stage:'cut',dim:'z',baseline:{z:['A','B','C']}}).names,['Khu A','Khu B','Khu C'])
})
test('a round chart goes largest first and drops what is empty',()=>{
 const c=pivotChart(rows,{stage:'cut',dim:'z',sorted:true,baseline:{z:['A','B','C']}})
 assert.deepEqual(c.names.slice(0,2),['Khu A','Khu B'])
 const w=pivotChart(rows,{stage:'cut',dim:'w',sorted:true,baseline:{w:['2026-W44','2026-W45','2026-W46']}})
 assert.deepEqual(w.keys,['2026-W45','2026-W46'])
})
test('kg per bunch is its own measure',()=>{
 const c=pivotChart([row('harvest','A','A1',10,{k:205})],{stage:'harvest',dim:'z',metric:'kg_per'})
 assert.deepEqual(c.series[0].data,[20.5])
})
test('the grid has lô down the side and weeks across',()=>{
 const g=heat(rows,'cut',['2026-W45','2026-W46'])
 assert.deepEqual(g.columns.map(c=>c.name),['T45','T46'])
 assert.deepEqual(g.rows.map(r=>[r.key,r.values]),[['A1',[10,0]],['B2',[0,7]],['A10',[5,0]]])
})
test('a chart of ribbon colours is drawn in those colours',()=>{
 assert.equal(ribbonColour('Đỏ'),'#c43224');assert.equal(ribbonColour('TÍM'),'#7a4fa3');assert.equal(ribbonColour('Xanh dương'),'#2f5c9f')
 assert.equal(ribbonColour('Đỏ-Xanh lá'),'#c43224','a two-colour ribbon takes its first');assert.equal(ribbonColour('Lạ'),null)
 assert.deepEqual(pivotChart(rows,{stage:'cut',dim:'c'}).pointColors,['#c43224'])
 assert.equal(pivotChart(rows,{stage:'cut',dim:'z'}).pointColors,null,'only for colours')
})
