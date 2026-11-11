// Shared driver for the spec 003 walk-through on the live-site copy (VPS test stack only).
// Each role logs in with its own browser context; setup that is not under test goes through the API as that role.
const {chromium}=require('playwright-core')
const fs=require('fs')
const {execFileSync}=require('child_process')
const base=process.env.UAT_BASE||'http://172.28.0.4:8000'
const cfg=JSON.parse(fs.readFileSync(__dirname+'/.uat','utf8'))
const out=__dirname+'/uat';fs.mkdirSync(out,{recursive:true})
const statePath=out+'/state.json'
const state=fs.existsSync(statePath)?JSON.parse(fs.readFileSync(statePath,'utf8')):{}
const save=()=>fs.writeFileSync(statePath,JSON.stringify(state,null,1))
const results=[]
const PHONE_UA='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
let browser
async function start(){browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']});return browser}
async function login(user,{width=1440,height=900,phone=false}={}){
 const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1,...(phone?{isMobile:true,hasTouch:true,userAgent:PHONE_UA}:{})})
 const [usr,pwd]=cfg.users[user]
 const r=await context.request.post(base+'/api/method/login',{form:{usr,pwd}})
 if(!r.ok())throw new Error('login '+user+' '+r.status())
 context.user=user;context.email=usr
 return context
}
function messageOf(body){
 try{if(body._server_messages)return JSON.parse(body._server_messages).map(m=>{try{return JSON.parse(m).message}catch{return m}}).join(' | ').replace(/<[^>]+>/g,'')}catch{}
 return String(body.exception||body.exc_type||JSON.stringify(body)).slice(0,400)
}
async function api(context,method,args={}){
 const r=await context.request.post(base+'/api/method/'+method,{data:args,timeout:120000})
 let body={};try{body=await r.json()}catch{}
 if(!r.ok()){const e=new Error(method+': '+messageOf(body));e.status=r.status();throw e}
 return body.message
}
// Run on the bench of the test container, for checks that need the database directly (read only unless stated).
function py(code){
 return execFileSync('docker',['exec','-i','lotus-003-proc-backend-1','bash','-lc','cd /home/frappe/frappe-bench/sites && ../env/bin/python -'],
  {input:"import frappe,json\nfrappe.init(site='mua.test',sites_path='/home/frappe/frappe-bench/sites')\nfrappe.connect()\nfrappe.set_user('Administrator')\n"+code+"\nfrappe.db.commit()\nfrappe.destroy()\n",encoding:'utf8'})
  .split('\n').filter(l=>l&&!/RuntimeWarning/.test(l)).join('\n')
}
async function shot(page,name){const path=out+'/'+name+'.png';await page.screenshot({path});return path}
async function settle(page,ms=1200){await page.waitForLoadState('networkidle').catch(()=>{});await page.waitForTimeout(ms)}
// First-visit dialogs that are by design: "Có gì mới" on desktop, first-run setup in the phone apps.
async function dismiss(page){
 const news=page.locator('dialog[open][aria-label="Có gì mới"]')
 if(await news.count())await news.getByRole('button',{name:'Đóng',exact:true}).first().click().catch(()=>{})
 const skip=page.getByRole('button',{name:'Bỏ qua thiết lập',exact:true})
 if(await skip.count()&&await skip.first().isVisible().catch(()=>false))await skip.first().click().catch(()=>{})
 await page.waitForTimeout(400)
}
async function goto(context,url,name){
 const page=await context.newPage();page.errors=[]
 page.on('pageerror',e=>page.errors.push(String(e.message).slice(0,200)))
 page.on('console',m=>{if(m.type()==='error'&&!/socket\.io|WebSocket|Failed to load resource/.test(m.text()))page.errors.push(m.text().slice(0,200))})
 await page.goto(base+url,{waitUntil:'networkidle',timeout:90000});await page.waitForTimeout(1500);await dismiss(page)
 if(name)await shot(page,name)
 return page
}
async function step(name,fn,page){
 const t0=Date.now()
 try{const detail=await fn();results.push({name,ok:true,detail:detail??'',ms:Date.now()-t0});console.log('PASS',name,detail?'· '+String(detail).slice(0,300):'')}
 catch(e){results.push({name,ok:false,detail:String(e.message).slice(0,600)});console.log('FAIL',name,'·',String(e.message).split('\n').slice(0,6).join(' / ').slice(0,700))
  if(page)await shot(page,'FAIL-'+name.replace(/[^a-z0-9]+/gi,'-').slice(0,60)).catch(()=>{})}
}
function expect(cond,message){if(!cond)throw new Error(message)}
function finish(phase){
 save()
 fs.writeFileSync(out+'/'+phase+'-results.json',JSON.stringify(results,null,1))
 const bad=results.filter(r=>!r.ok)
 console.log(phase+': '+(results.length-bad.length)+'/'+results.length+' bước qua')
 return bad.length
}
// Dates as the site sees them (Asia/Ho_Chi_Minh, UTC+7, no daylight saving): the VPS clock runs in UTC, and after
// midnight in Việt Nam a UTC date is the day before the orders made by the site.
const days=n=>{const d=new Date(Date.now()+7*3600e3+n*864e5);return d.toISOString().slice(0,10)}
module.exports={start,login,api,py,shot,settle,dismiss,goto,step,expect,finish,state,save,base,cfg,days,get browser(){return browser}}
