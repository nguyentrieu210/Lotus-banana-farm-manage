import {test} from 'node:test'
import assert from 'node:assert/strict'
import {retryAttempt,acceptAttempt} from '../src/attempts.js'
test('ambiguous reservation retries keep one event ID until accepted',()=>{
 const a=retryAttempt('reserve',{quantity:10,forecast:'F',client_event_id:'discarded'})
 const b=retryAttempt('reserve',{forecast:'F',quantity:10,client_event_id:'new-random'})
 assert.equal(a.args.client_event_id,b.args.client_event_id)
 assert.notEqual(a.args.client_event_id,retryAttempt('reserve',{forecast:'F',quantity:11}).args.client_event_id)
 assert.notEqual(a.args.client_event_id,retryAttempt('release',{forecast:'F',quantity:10}).args.client_event_id)
 acceptAttempt(a.key)
 assert.notEqual(a.args.client_event_id,retryAttempt('reserve',{forecast:'F',quantity:10}).args.client_event_id)
})

test('reservation attempts stay with their original account',()=>{
 let account='alice';globalThis.localStorage={getItem:()=>account}
 try{
  const a=retryAttempt('reserve',{quantity:20,forecast:'Account F'})
  account='bob'
  const b=retryAttempt('reserve',{quantity:20,forecast:'Account F'})
  assert.notEqual(a.args.client_event_id,b.args.client_event_id)
  account='alice'
  assert.equal(a.args.client_event_id,retryAttempt('reserve',{quantity:20,forecast:'Account F'}).args.client_event_id)
 }finally{delete globalThis.localStorage}
})
