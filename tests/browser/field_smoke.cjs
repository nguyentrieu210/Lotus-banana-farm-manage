/* Local browser contracts: offline reload, queued evidence, account boundaries, replay. */
const {chromium}=require('playwright');
const http=require('node:http');const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const output=process.env.LOTUS_BROWSER_ARTIFACTS||require('node:os').tmpdir();fs.mkdirSync(output,{recursive:true});
const root=path.resolve(__dirname,'../../lotus_farm/public/field');let user='operator@example.invalid';const events=new Map();
const farm='Farm A';const cycle={name:'Cycle 1',farm_block:'Block 33',farm_plot:'Plot 33.1',cycle_type:'Plant Crop'};
const task={plan:'PLAN-1',line:'LINE-1',farm_block:cycle.farm_block,farm_plot:cycle.farm_plot,plot_code:'33.1',crop_cycle:cycle.name,cohort:null,work_type:'Bag',work_name:'Bao buồng',uom:'buồng',planned_qty:100,completed_qty:0,required_workdays:3,allocated_workdays:2,actual_workdays:0};
const feature={type:'Feature',geometry:{type:'Polygon',coordinates:[[[106,10],[107,10],[107,11],[106,11],[106,10]]]},properties:{plot:'Plot 33.1',version:1}};
const bootstrap=()=>({user,farm,tasks:[task],labor:[],cancellations:[],reasons:[{name:'Wind',reason_name:'Gió làm đổ'}],diseases:[],cycles:[cycle],cohorts:[],geometries:[feature]});
const summary={farms:[{farm,work_completion_percent:0,labor_gap_workdays:-1,harvest_kg:0,packout_percent:null,outstanding_material:[]}],forecast:[]};
const server=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://localhost');
 if(url.pathname.startsWith('/api/method/')){
  let body='';for await(const chunk of req)body+=chunk;
  const method=url.pathname.split('/').pop();let result;
  if(method==='lotus_farm.field.session_info')result={user,csrf_token:'test-csrf',farms:[{name:farm,farm_name:farm}]};
  else if(method==='lotus_farm.field.bootstrap')result=bootstrap();
  else if(method==='lotus_farm.reporting.dashboard')result=summary;
  else if(method==='lotus_farm.field.capture'){
   assert.equal(req.headers['x-frappe-csrf-token'],'test-csrf');const value=JSON.parse(body);events.set(value.client_event_id,value);result={document:'RESULT-1',capture:'CAPTURE-1'};
  }else result=[];
  res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({message:result}));return;
 }
 const file=path.resolve(root,'.'+decodeURIComponent(url.pathname.replace('/assets/lotus_farm/field','')));
 if(!file.startsWith(root+path.sep)||!fs.existsSync(file)){res.writeHead(404);res.end();return;}
 const mime={'.html':'text/html','.js':'application/javascript','.css':'text/css','.svg':'image/svg+xml','.webmanifest':'application/manifest+json'};
 res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream'});res.end(fs.readFileSync(file));
});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const origin='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
  const context=await browser.newContext({viewport:{width:1280,height:900},geolocation:{latitude:10.5,longitude:106.5,accuracy:5},permissions:['geolocation']});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(origin+'/assets/lotus_farm/field/index.html');await page.getByText('Số liệu đã cập nhật.',{exact:true}).waitFor();
  await page.evaluate(()=>navigator.serviceWorker.ready);await page.screenshot({path:path.join(output,'lotus-ui-desktop.png'),fullPage:true});
  await page.locator('[data-tab="field"]').click();await context.setOffline(true);await page.locator('[data-task="LINE-1"]').click();
  await page.locator('#doneqty').fill('80');await page.locator('#days').fill('2');await page.locator('#unfinished').fill('Mưa');await page.locator('#saveresult').click();
  await page.getByText('1 đang chờ',{exact:true}).waitFor();await page.reload();await page.locator('[data-tab="field"]').click();await page.getByText('1 đang chờ',{exact:true}).waitFor();
  await context.setOffline(false);await page.locator('#sync').click();await page.getByText('0 đang chờ',{exact:true}).waitFor();
  assert.equal(events.size,1);assert.equal([...events.values()][0].values.completed_qty,80);
  await page.locator('#sync').click();assert.equal(events.size,1);
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'lotus-ui-mobile.png'),fullPage:true});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  user='other@example.invalid';await page.reload();await page.getByText('Số liệu đã cập nhật.',{exact:true}).waitFor();
  await page.locator('[data-tab="field"]').click();assert.equal(await page.locator('#queue').textContent(),'');assert.deepEqual(errors,[]);
  console.log('PASS: offline reload, queue synchronization, no duplicate send, account isolation and mobile width.');
 }finally{await browser.close();server.close();}
})().catch(error=>{console.error(error);server.close();process.exitCode=1;});
