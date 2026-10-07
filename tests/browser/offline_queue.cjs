/* Native IndexedDB regression tests, without a Frappe server or API mocks. */
const {chromium}=require('playwright'),http=require('node:http'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict')
const source=fs.readFileSync(path.resolve(__dirname,'../../frontend/src/offline.js'))
const server=http.createServer((req,res)=>{res.writeHead(200,{'Content-Type':req.url==='/offline.js'?'application/javascript':'text/html'});res.end(req.url==='/offline.js'?source:'<!doctype html><title>Queue regression</title>')})
;(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,args:['--no-sandbox']});try{
 const page=await browser.newPage();await page.goto('http://127.0.0.1:'+server.address().port)
 const result=await page.evaluate(async()=>{
  const queue=await import('/offline.js'),check=(ok,message)=>{if(!ok)throw Error(message)}
  const event={client_event_id:'event-1',farm:'Farm A',target_doctype:'Bunch Cancellation',captured_at:'2026-10-07T10:00:00Z',values:{bunch_qty:3}}
  await queue.queueCapture('alice',event,new Blob(['photo-bytes'],{type:'image/jpeg'}))
  let rows=await queue.queueRows('alice');check(rows.length===1&&rows[0].photo.size===11,'Committed event/photo missing')
  check((await queue.queueRows('bob')).length===0,'Cross-account queue visibility')
  let duplicate=false;try{await queue.queueCapture('alice',{...event,values:{bunch_qty:999}})}catch{duplicate=true}
  check(duplicate&&(await queue.queueRows('alice'))[0].event.values.bunch_qty===3,'Duplicate event overwritten')
  let fail=true,uploads=0,writes=0;const payloads=[]
  const api={upload:async()=>{uploads++;return {file_url:'/private/files/photo.jpg'}},call:async(method,args)=>{
   if(method.endsWith('session_info'))return {user:'alice'}
   writes++;payloads.push(JSON.stringify(args));if(fail)throw Error('Response lost');return {document:'actual-1'}
  }}
  await queue.syncCaptures('alice',api)
  rows=await queue.queueRows('alice');check(rows[0].status==='Error'&&rows[0].photo&&rows[0].event.photo,'Retry evidence lost')
  fail=false;await Promise.all([queue.syncCaptures('alice',api),queue.syncCaptures('alice',api)])
  rows=await queue.queueRows('alice');check(writes===2&&uploads===1,'Repeated sync/upload')
  check(payloads[0]===payloads[1]&&rows[0].status==='Sent'&&rows[0].photo===null,'Retry payload changed')
  await queue.queueCapture('alice',{...event,client_event_id:'event-2'},new Blob(['private-photo']))
  await queue.syncCaptures('alice',{call:async()=>({user:'bob'}),upload:async()=>{throw Error('Private photo uploaded as bob')}})
  rows=await queue.queueRows('alice');check(rows[1].status==='Error'&&rows[1].photo&&!rows[1].event.photo,'Account switch lost/leaked evidence')
  // Request success is not transaction success. Force an abort after a successful add.
  const original=IDBObjectStore.prototype.add
  IDBObjectStore.prototype.add=function(...args){const req=original.apply(this,args),transaction=this.transaction;req.addEventListener('success',()=>transaction.abort());return req}
  let aborted=false;try{await queue.queueCapture('alice',{...event,client_event_id:'event-aborted'})}catch{aborted=true}
  IDBObjectStore.prototype.add=original
  check(aborted&&!(await queue.queueRows('alice')).some(r=>r.event.client_event_id==='event-aborted'),'Aborted write reported saved')
  await queue.clearSent('alice');check((await queue.queueRows('alice')).length===1,'Unsent row cleared')
  return {uploads,writes,checks:'commit/abort, immutable identity, retry/photo, concurrent sync, account isolation'}
 })
 assert.equal(result.uploads,1);assert.equal(result.writes,2);console.log('PASS: '+result.checks)
 }finally{await browser.close();server.close()}
})().catch(e=>{console.error(e);server.close();process.exitCode=1})
