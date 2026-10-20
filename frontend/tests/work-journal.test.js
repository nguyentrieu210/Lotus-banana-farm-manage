import test from 'node:test'
import assert from 'node:assert/strict'
import {loadModule,mount,tick,h} from './support/mount.mjs'
import {blankJournalRow,cloneJournalRow,rowErrors,draftKey,duplicateRows,labelledRows,fold,journalTotals} from '../src/journal-model.js'
const {useWorkJournal}=await loadModule('use-work-journal.js')
test('journal distinguishes blank/zero, preserves IDs, scopes drafts and finds duplicate work',()=>{
 const row={...blankJournalRow(),work_team:'T',farm_block:'B',work_type:'W',workdays:0}
 assert.deepEqual(rowErrors(row),{})
 assert.ok(rowErrors({...row,workdays:null}).quantity)
 assert.ok(rowErrors({...row,workdays:-1}).workdays)
 assert.notEqual(cloneJournalRow(row).row_id,row.row_id)
 assert.equal(duplicateRows([row,cloneJournalRow(row)]).length,1)
 assert.notEqual(draftKey('a','F','2026-01-01'),draftKey('b','F','2026-01-01'))
 assert.notEqual(draftKey('a','F','2026-01-01'),draftKey('a','F','2026-01-02'))
 assert.match(fold(labelledRows([row],{teams:[{name:'T',team_name:'Đội đỏ'}]})[0].team_label),/doi do/)
 const totals=journalTotals([{work_type:'A',uom:'Tree',quantity:10,workdays:1},{work_type:'A',uom:'Kg',quantity:2,workdays:0.5},{work_type:'B',uom:'Tree',quantity:3,workdays:null}])
 assert.equal(totals.groups.length,3);assert.equal(totals.total_workdays,1.5)
})
test('conflicting server version keeps local rows until an explicit reconciliation',async()=>{
 localStorage.clear();let model,gets=0
 const row={...blankJournalRow(),work_team:'T',farm_block:'B',work_type:'W',workdays:1,notes:'server'}
 globalThis.fetch=async(url)=>{const method=new URL(url,'http://localhost').pathname.split('.').at(-1);if(method==='save')return {ok:false,status:409,json:async()=>({exc_type:'TimestampMismatchError',message:'Changed elsewhere'})};if(method==='get')gets++;const data={bootstrap:{user:'a',today:'2026-10-20',farms:[{name:'F'}]},catalogue:{teams:[],blocks:[],works:[]},get:{name:'J',modified:gets===1?'v1':'v2',rows:[row],can_write:true}};return {ok:true,json:async()=>({message:data[method]})}}
 const view=mount({setup(){model=useWorkJournal();return()=>h('div')}})
 try{await model.init();model.rows.value[0].notes='local edit';await model.save();assert.equal(model.rows.value[0].notes,'local edit');assert.equal(model.conflict.value.modified,'v2');assert.equal(model.record.value.modified,'v1');model.resolveConflict(false);assert.equal(model.record.value.modified,'v2');assert.equal(model.rows.value[0].notes,'local edit');assert.ok(model.dirty.value)}finally{view.unmount()}
})
test('real journal model keeps failed save draft, retries same request and isolates accounts',async()=>{
 localStorage.clear()
 let model,user='a',writes=[],fail=true
 const row={...blankJournalRow(),work_team:'T',farm_block:'B',work_type:'W',workdays:0}
 globalThis.fetch=async(url,options={})=>{
  const method=new URL(url,'http://localhost').pathname.split('.').at(-1)
  let message
  if(method==='bootstrap')message={user,today:'2026-10-20',farms:[{name:'F'}],capabilities:{'work_journal.write':true}}
  if(method==='catalogue')message={teams:[],blocks:[],works:[]}
  if(method==='get')message={name:null,modified:null,rows:[],can_write:true}
  if(method==='save'){const args=JSON.parse(options.body);writes.push(args);if(fail)throw Error('lost response');message={name:'J',rows:args.rows,modified:'m1',can_write:true}}
  return {ok:true,json:async()=>({message})}
 }
 const view=mount({setup(){model=useWorkJournal();return()=>h('div')}})
 try{
  await model.init();model.rows.value.push(row);await tick();await model.save()
  assert.ok(model.attempt.value)
  assert.ok(localStorage.getItem(draftKey('a','F','2026-10-20')))
  fail=false;await model.save()
  assert.equal(writes[0].request_id,writes[1].request_id)
  assert.equal(model.dirty.value,false)
  model.rows.value[0].notes='changed';await tick();await model.load()
  assert.equal(model.rows.value[0].notes,'changed')
  user='b';await model.init()
  assert.equal(model.rows.value.length,0)
  assert.ok(localStorage.getItem(draftKey('a','F','2026-10-20')))
 }finally{view.unmount()}
})
