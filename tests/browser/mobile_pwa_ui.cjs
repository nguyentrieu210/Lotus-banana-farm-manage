/* Headless Chromium smoke: 3 PWAs x 320/390/landscape, mock API (no ERP writes). */
const fs=require('fs'),path=require('path'),http=require('http'),assert=require('assert/strict');
const {chromium}=require('playwright');
const repo=path.resolve(__dirname,'../..'),build=path.resolve(repo,process.env.LOTUS_MOBILE_BUILD_DIR||'lotus_farm/public/frontend');
const screenshotDir=process.env.LOTUS_BROWSER_ARTIFACTS||path.join(repo,'frontend/temp-mobile-ui-screenshots');
const entries={'/warehouse':'warehouse.html','/buying':'buying.html','/work':'work-mobile.html'};
const mime={'.html':'text/html','.js':'application/javascript','.css':'text/css','.png':'image/png','.svg':'image/svg+xml'};
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost').pathname;
 if(u.startsWith('/api/')){
   const method=u.slice('/api/method/'.length),last=method.split('.').pop();
   if(/service_worker$/.test(method)){res.writeHead(200,{'Content-Type':'application/javascript','Service-Worker-Allowed':'/'});res.end("self.addEventListener('install',()=>self.skipWaiting());");return}
   const bootstrap={user:'test@example.invalid',csrf_token:'mock',today:'2026-10-17',companies:[{name:'Lotus Test'}],farms:[{name:'Vườn Test',farm_name:'Vườn Test'}],can_create:false,can_approve:false,commands:{},creatable:{},permissions:{}};
   const catalog={warehouses:[],items:[],suppliers:[],can_create:false,can_request:false,today:'2026-10-17'};
   let message;
   if(last==='bootstrap'||last==='session_info')message=bootstrap;
   else if(last==='catalog'||last==='setup')message=catalog;
   else if(['orders','requests','suppliers','teams','items'].includes(last))message=[];
   else if(last==='day')message={tasks:[],plans:[]};
   else if(last==='history')message={rows:[]};
   else message=[];
   res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({message}));return
 }
 let file,base;
 if(entries[u]){base=build;file=path.resolve(base,entries[u])}
 else if(u.startsWith('/assets/lotus_farm/frontend/')){base=build;file=path.resolve(base,u.slice('/assets/lotus_farm/frontend/'.length))}
 else if(u.startsWith('/assets/lotus_farm/images/')){base=path.join(repo,'lotus_farm/public/images');file=path.resolve(base,u.slice('/assets/lotus_farm/images/'.length))}
 else {res.writeHead(404);res.end();return}
 if(!file.startsWith(base+path.sep)||!fs.existsSync(file)){res.writeHead(404);res.end();return}
 res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});
 fs.createReadStream(file).pipe(res);
});
(async()=>{
 fs.mkdirSync(screenshotDir,{recursive:true});
 await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
  const origin='http://127.0.0.1:'+server.address().port;
  for(const app of ['warehouse','buying','work']){
   for(const viewport of [{width:320,height:740,name:'320'},{width:390,height:844,name:'390'},{width:844,height:390,name:'landscape'}]){
    const ctx=await browser.newContext({viewport,deviceScaleFactor:1,isMobile:true,hasTouch:true});
    await ctx.addInitScript(()=>['warehouse','buying','work'].forEach(a=>localStorage.setItem('lotus-pwa-setup-v1:'+a,'done')));
    const page=await ctx.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',msg=>{if(msg.type()==='error'||msg.type()==='warning')console.error('BROWSER '+app+' '+msg.type()+' '+msg.text().slice(0,800))});
    await page.goto(origin+'/'+app,{waitUntil:'domcontentloaded'});
    try { await page.locator('.lotus-pwa-header').waitFor({timeout:10000}) }
    catch(e) { console.error('DEBUG '+app+' '+viewport.name, 'URL',page.url(),'HEADERS',await page.locator('.lotus-pwa-header').count(),'BODY', (await page.locator('body').innerText()).slice(0,1200),'JS',errors,'HTMLTAIL',(await page.content()).slice(-800)); throw e }
    await page.waitForTimeout(600);
    const info=await page.evaluate(()=>{
     const rect=s=>{const x=document.querySelector(s)?.getBoundingClientRect();return x&&{left:x.left,right:x.right,width:x.width}};
     return {width:document.documentElement.scrollWidth,viewport:innerWidth,logoWidth:document.querySelector('.lotus-pwa-logo')?.naturalWidth||0,logo:rect('.lotus-pwa-logo-frame'),bell:rect('.lotus-notification-trigger'),tabs:document.querySelectorAll('.lotus-pwa-bottom .van-tabbar-item').length}
    });
    await page.screenshot({path:path.join(screenshotDir,'lotus-'+app+'-'+viewport.name+'.png'),fullPage:true});
    assert.ok(info.width<=viewport.width+1,app+' '+viewport.name+' horizontal overflow '+info.width);
    assert.ok(info.logoWidth>0,app+' logo did not load');
    assert.ok(info.logo.width>=85,app+' logo frame too small');
    assert.ok(info.bell&&info.logo.right<=info.bell.left+1,app+' header overlap');
    assert.equal(info.tabs,4,app+' tabs mismatch');
    assert.deepEqual(errors,[],app+' script errors');
    console.log('PASS '+app+' '+viewport.name+' '+JSON.stringify(info));
    await ctx.close();
   }
  }
 }finally{await browser.close();server.close()}
})().catch(e=>{console.error(e);server.close();process.exitCode=1});
