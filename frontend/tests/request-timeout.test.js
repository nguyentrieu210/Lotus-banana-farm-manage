import test from 'node:test'
import assert from 'node:assert/strict'
import {requestJSON} from '../src/request-timeout.js'
test('slow headers and slow bodies terminate without issuing a second request',async()=>{
 for(const body of [false,true]){let calls=0;globalThis.fetch=async()=>{calls++;return body?{json:()=>new Promise(()=>{})}:new Promise(()=>{})};await assert.rejects(requestJSON('/test',{method:'POST'},8),e=>e.code==='RequestTimeout');assert.equal(calls,1)}
})
test('successful response retains response status and payload',async()=>{
 globalThis.fetch=async()=>({status:200,json:async()=>({message:1})});const r=await requestJSON('/test',{},100);assert.equal(r.response.status,200);assert.equal(r.data.message,1)
})
