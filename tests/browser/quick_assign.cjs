/* Mobile UI smoke with real compiled Vue assets and a mock Frappe API. */
const {chromium}=require('playwright'),http=require('node:http'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict')
const root=path.resolve(__dirname,'../../lotus_farm/public/frontend')
// Quick assignment lives inside the workspace (Công việc → giao việc) since the standalone assign.html entry was retired.
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
  if(method==='lotus_farm.console.bootstrap')result={user:'mobile-manager',csrf_token:'demo-csrf',today:'2026-10-11',commands:{work:true},capabilities:{home:true},modules:{work:['Daily Work Plan','Daily Work Result']},creatable:{},farms:[{name:'LOTUS-DEMO-222',farm_name:'Lotus 222 ha · Demo',company:'DEMO'}]}
  else if(method==='lotus_farm.mobile_assignment.options')result={blocks:[{name:'B1',block_code:'A01',block_name:'A01'},{name:'B2',block_code:'A02',block_name:'A02'}],
   plots:[1,2,3,4].map(i=>({name:'P'+i,plot_code:'A01-0'+i,farm_block:'B1',area_ha:20})),
   teams:[{name:'T1',team_name:'Tổ bao buồng 01'}],
   works:[{name:'W1',work_name:'Bao buồng',uom:'Bunch'},{name:'W2',work_name:'Cắt lá',uom:'Ha'}]}
  else if(method==='lotus_farm.mobile_assignment.preview'){previewCalls++;assert.equal(req.headers['x-frappe-csrf-token'],'demo-csrf');result={note:'Chia theo diện tích các thửa',lines:args.items.flatMap(x=>x.location==='block:B1'?[1,2,3,4].map(i=>({plot_code:'A01-0'+i,work_name:'Bao buồng',planned_qty:Number(x.qty)/4,uom:'Bunch'})):[{plot_code:'A01-02',work_name:'Cắt lá',planned_qty:x.qty,uom:'Ha'}])}}
  else if(method==='lotus_farm.mobile_assignment.create'){assert.equal(req.headers['x-frappe-csrf-token'],'demo-csrf');submitted=args;result={plan:'DEMO-PLAN-1',count:5}}
  // The Công việc screen around the assignment dialog: empty farm data.
  else if(method==='lotus_farm.farm_workspace.load')result={plans:[],teams:[],works:[],categories:[],bases:[],blocks:[],plots:[],cycles:[],varieties:[],norms:[],zones:[],permissions:{},readiness:{}}
  else if(method==='lotus_farm.daily_api.daily_overview')result={tasks:[]}
  // Other workspace reads (alerts…) are not under test: answer empty.
  else result={}
  res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({message:result}));return
 }
 if(url.pathname.startsWith('/lotus/')){res.writeHead(200,{'Content-Type':'text/html'});res.end(fs.readFileSync(path.join(root,'index.html')));return}
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
  await page.goto(origin+'/lotus/cong-viec?farm=LOTUS-DEMO-222&action=assign')
  await page.getByRole('heading',{name:'Lập kế hoạch và giao việc'}).waitFor()
  // Searchable pickers: open, type, pick the matching suggestion.
  const choose=async(field,text)=>{await field.click();await page.keyboard.type(text);await page.getByRole('option',{name:new RegExp(text)}).first().click()}
  const team=page.getByRole('combobox',{name:'Giao cho tổ'})
  // The only team is picked by default; choose it only when the field is still empty.
  if(!/Tổ bao buồng 01/.test(await team.evaluate(e=>e.value||e.textContent||'')))await choose(team,'Tổ bao buồng 01')
  await choose(page.getByRole('combobox',{name:'Lô thực hiện'}).first(),'A01')
  await choose(page.getByRole('combobox',{name:'Công việc',exact:true}).first(),'Bao buồng')
  await page.getByLabel('Số lượng giao').first().fill('800')
  await page.getByRole('button',{name:'Thêm công việc / lô khác'}).click()
  await choose(page.getByRole('combobox',{name:'Lô thực hiện'}).last(),'A02')
  await choose(page.getByRole('combobox',{name:'Công việc',exact:true}).last(),'Cắt lá')
  await page.getByLabel('Số lượng giao').last().fill('1.5')
  await page.getByRole('button',{name:'Xem trước giao việc'}).click()
  await page.getByText('Xem trước 5 dòng giao').waitFor()
  assert.equal(previewCalls,1)
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
  await page.screenshot({path:path.join(output,'lotus-mobile-giao-viec.png'),fullPage:true})
  await page.getByRole('button',{name:'Xác nhận giao việc'}).click()
  await page.getByText('Đã giao việc theo kế hoạch: DEMO-PLAN-1',{exact:false}).waitFor()
  assert.equal(submitted.farm,'LOTUS-DEMO-222')
  assert.equal(submitted.work_team,'T1')
  assert.deepEqual(submitted.items.map(x=>x.location),['block:B1','block:B2'])
  assert.deepEqual(errors,[])
  console.log('PASS: Công việc → giao việc (390px): block expansion → two jobs → real POST with CSRF → plan notice')
 }finally{await browser.close();server.close()}
})().catch(e=>{console.error(e);server.close();process.exitCode=1})
