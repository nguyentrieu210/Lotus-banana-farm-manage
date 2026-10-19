import test from 'node:test'
import assert from 'node:assert/strict'
import {saveDraft,loadDraft,clearDraft} from '../src/form-drafts.js'

test('drafts of new documents survive a reload, then expire or clear',()=>{
 const store=new Map()
 globalThis.localStorage={getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)}
 saveDraft('Work Type',{work_name:'Cắt lá khô'})
 assert.equal(loadDraft('Work Type').values.work_name,'Cắt lá khô')
 store.set('lotus-draft:Old',JSON.stringify({savedAt:Date.now()-8*24*3600*1000,values:{a:1}}))
 assert.equal(loadDraft('Old'),null,'older than 7 days is dropped')
 clearDraft('Work Type')
 assert.equal(loadDraft('Work Type'),null)
 delete globalThis.localStorage
})
