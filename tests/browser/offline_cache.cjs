/* Native IndexedDB regression test of the read cache (frontend/src/offline-cache.js), without a Frappe server or API mocks. */
const {chromium}=require('playwright'),http=require('node:http'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict')
const cacheSource=fs.readFileSync(path.resolve(__dirname,'../../frontend/src/offline-cache.js'))
const server=http.createServer((req,res)=>{res.writeHead(200,{'Content-Type':req.url.endsWith('.js')?'application/javascript':'text/html'});res.end(req.url==='/offline-cache.js'?cacheSource:'<!doctype html><title>Read cache regression</title>')})
;(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,args:['--no-sandbox']});try{
 const page=await browser.newPage();await page.goto('http://127.0.0.1:'+server.address().port)
 const result=await page.evaluate(async()=>{
  const cache=await import('/offline-cache.js'),check=(ok,message)=>{if(!ok)throw Error(message)}
  cache.setActiveUser('alice');
  await cache.saveRead('alice','lotus_farm.console.bootstrap',{}, {user:'alice',csrf_token:'secret',farms:['A']});
  const cached=await cache.cachedRead('alice','lotus_farm.console.bootstrap',{});
  check(cached.user==='alice'&&!cached.csrf_token,'Cached credentials persisted');
  check(await cache.cachedRead('bob','lotus_farm.console.bootstrap',{})===null,'Cross-account read cache');
  check(await cache.cachedRead('alice','lotus_farm.console.save',{})===null,'Write API cached');
  await cache.saveRead('alice','lotus_farm.console.scope_options',{farm:'A',company:'C'},{scope:{farm:'A'}});
  check((await cache.cachedRead('alice','lotus_farm.console.scope_options',{company:'C',farm:'A'})).scope.farm==='A','Cache key depends on argument ordering');
  check(await cache.cachedRead('alice','lotus_farm.console.scope_options',{farm:'B',company:'C'})===null,'Cross-scope read cache');
  return {checks:'read-cache account, scope and CSRF isolation; write APIs never cached'}
 })
 assert.ok(result.checks);console.log('PASS: '+result.checks)
 }finally{await browser.close();server.close()}
})().catch(e=>{console.error(e);server.close();process.exitCode=1})
