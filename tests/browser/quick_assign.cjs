/* Mobile UI smoke with real compiled Vue assets and a mock Frappe API. */
const {chromium}=require('playwright'),http=require('node:http'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict')
const root=path.resolve(__dirname,'../../lotus_farm/public/frontend')
const entry=JSON.parse(fs.readFileSync(path.join(root,'.vite/manifest.json')))['assign.html']
const output=process.env.LOTUS_BROWSER_ARTIFACTS||'/tmp/lotus-console-browser'
fs.mkdirSync(output,{recursive:true})
let submitted=null, previewCalls=0
const server=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://localhost')
 if(url.pathname.startsWith('/api/method/')){
  let body='';for await(const chunk of req)body+=chunk
  const args=body?JSON.parse(body):Object.fromEntries(url.searchParams)
  const method=url.pathname.split('/').pop()
  let result
  if(method==='lotus_farm.console.bootstrap')result={user:'mobile-manager',csrf_token:'demo-csrf',today:'2026-10-11',commands:{work:true},farms:[{name:'LOTUS-DEMO-222',farm_name:'Lotus 222 ha · Demo',company:'DEMO'}]}
  else if(method==='lotus_farm.mobile_assignment.options')result={blocks:[{name:'B1',block_code:'A01',block_name:'A01'}],
   plots:[1,2,3,4].map(i=>({name:'P'+i,plot_code:'A01-0'+i,farm_block:'B1',area_ha:20})),
   teams:[{name:'T1',team_name:'Tổ bao buồng 01'}],
   works:[{name:'W1',work_name:'Bao buồng',uom:'Bunch'},{name:'W2',work_name:'Cắt lá',uom:'Ha'}]}
  else if(method==='lotus_farm.mobile_assignment.preview'){previewCalls++;assert.equal(req.headers['x-frappe-csrf-token'],'demo-csrf');result={note:'Chia theo diện tích các thửa',lines:args.items.flatMap(x=>x.location==='block:B1'?[1,2,3,4].map(i=>({plot_code:'A01-0'+i,work_name:'Bao buồng',planned_qty:Number(x.qty)/4,uom:'Bunch'})):[{plot_code:'A01-02',work_name:'Cắt lá',planned_qty:x.qty,uom:'Ha'}])}}
  else if(method==='lotus_farm.mobile_assignment.create'){assert.equal(req.headers['x-frappe-csrf-token'],'demo-csrf');submitted=args;result={plan:'DEMO-PLAN-1',count:5}}
  else {res.writeHead(404);res.end('unknown method: '+method);return}
  res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({message:result}));return
 }
 if(url.pathname.startsWith('/lotus/')){res.writeHead(200,{'Content-Type':'text/html'});res.end(`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">${(entry.css||[]).map(f=>`<link rel="stylesheet" href="/assets/lotus_farm/frontend/${f}">`).join('')}</head><body><div id="app"></div><script type="module" src="/assets/lotus_farm/frontend/${entry.file}"></script></body></html>`);return}
 const file=path.resolve(root,'.'+url.pathname.replace('/assets/lotus_farm/frontend',''))
 if(!file.startsWith(root+path.sep)||!fs.existsSync(file)){res.writeHead(404);res.end('missing');return}
 res.writeHead(200,{'Content-Type':{'.html':'text/html','.js':'application/javascript','.css':'text/css','.woff2':'font/woff2'}[path.extname(file)]||'application/octet-stream'})
 res.end(fs.readFileSync(file))
})
;(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r))
 const origin='http://127.0.0.1:'+server.address().port
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']})
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:1})
  const errors=[];page.on('pageerror',e=>errors.push(e.message))
  await page.goto(origin+'/lotus/giao-viec?farm=LOTUS-DEMO-222')
  await page.getByRole('heading',{name:'Giao việc nhanh'}).waitFor()
  await page.locator('section.panel select').filter({has:page.locator('option[value="T1"]')}).selectOption('T1')
  await page.getByLabel('Vị trí thực hiện').first().selectOption('block:B1')
  await page.getByLabel('Công việc').first().selectOption('W1')
  await page.getByLabel('Số lượng giao').first().fill('800')
  await page.getByRole('button',{name:'Thêm công việc / lô khác'}).click()
  await page.getByLabel('Vị trí thực hiện').last().selectOption('plot:P2')
  await page.getByLabel('Công việc').last().selectOption('W2')
  await page.getByLabel('Số lượng giao').last().fill('1.5')
  await page.getByRole('button',{name:'Xem trước giao việc'}).click()
  await page.getByText('Xem trước 5 dòng giao').waitFor()
  assert.equal(previewCalls,1)
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
  await page.screenshot({path:path.join(output,'lotus-mobile-giao-viec.png'),fullPage:true})
  await page.getByRole('button',{name:'Xác nhận giao việc'}).click()
  await page.getByText('Đã giao 5 dòng công việc.',{exact:false}).waitFor()
  assert.equal(submitted.farm,'LOTUS-DEMO-222')
  assert.equal(submitted.work_team,'T1')
  assert.deepEqual(submitted.items.map(x=>x.location),['block:B1','plot:P2'])
  assert.deepEqual(errors,[])
  console.log('PASS: mobile preview → block expansion → multiple jobs → real POST with CSRF → confirmation')
 }finally{await browser.close();server.close()}
})().catch(e=>{console.error(e);server.close();process.exitCode=1})
