import test from 'node:test'
import assert from 'node:assert/strict'
import {tablePage} from '../src/table-pagination.js'

test('all rows reads bounded pages from the first row and preserves filters',async()=>{
 const calls=[],records=Array.from({length:235},(_,name)=>({name}))
 const result=await tablePage(async args=>{
  calls.push(args)
  return {items:records.slice(args.start,args.start+args.length),has_more:args.start+args.length<records.length,total_count:235,filter_values:{name:['N']}}
 },{start:50,search:'same',column_filters:'same'},{pageSize:0,rowsKey:'items'})
 assert.deepEqual(calls.map(args=>[args.start,args.length,args.search,args.column_filters]),[[0,100,'same','same'],[100,100,'same','same'],[200,100,'same','same']])
 assert.deepEqual(result.items,records)
 assert.equal(result.has_more,false)
 assert.equal(result.start,0)
 assert.equal(result.total_count,235)
 assert.deepEqual(result.filter_values,{name:['N']})
})

test('a normal page preserves its offset and API-specific limit name',async()=>{
 let args
 await tablePage(async request=>{args=request;return {rows:[]}},{start:40,company:'C'},{pageSize:20,sizeKey:'page_length'})
 assert.deepEqual(args,{start:40,company:'C',page_length:20})
})

test('all rows does not return partial data when a later request fails',async()=>{
 let requests=0
 await assert.rejects(tablePage(async()=>{
  if(++requests===2)throw new Error('connection lost')
  return {rows:[{name:'A'}],has_more:true}
 },{},{pageSize:0}),/connection lost/)
 assert.equal(requests,2)
})

test('an empty unfinished page stops with an error instead of silently truncating',async()=>{
 await assert.rejects(tablePage(async()=>({rows:[],has_more:true}),{},{pageSize:0}),/Không tải đủ/)
})

test('changing the screen cancels the remaining requests',async()=>{
 let current=true,requests=0
 await assert.rejects(tablePage(async()=>{
  requests++;current=false;return {rows:[{name:'A'}],has_more:true}
 },{},{pageSize:0,isCurrent:()=>current}),error=>error.stale===true)
 assert.equal(requests,1)
})
