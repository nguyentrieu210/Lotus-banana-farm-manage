/* Real Frappe mobile entry smoke test, sharing CI's disposable browser seed. */
const {chromium}=require('playwright')
const assert=require('node:assert/strict')
const fs=require('node:fs')
const path=require('node:path')
const seed=JSON.parse(fs.readFileSync(process.env.LOTUS_REAL_SEED||'/tmp/lotus-console-seed.json'))
const origin=process.env.LOTUS_REAL_ORIGIN||'http://127.0.0.1:8000'
const output=process.env.LOTUS_BROWSER_ARTIFACTS||'/tmp/lotus-console-real'
fs.mkdirSync(output,{recursive:true})

;(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']})
 try{
  const context=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:1})
  const login=await context.request.post(origin+'/api/method/login',{form:{usr:'Administrator',pwd:'ci-only'}})
  assert.equal(login.status(),200)
  const page=await context.newPage(),errors=[]
  page.on('pageerror',e=>errors.push(e.message))
  await page.goto(origin+'/lotus/mobile?farm='+encodeURIComponent(seed.farm))
  await page.getByRole('heading',{name:'Hôm nay'}).waitFor()
  await page.locator('.stat').first().waitFor()
  await page.getByRole('button',{name:'Công việc',exact:true}).click()
  await page.getByRole('heading',{name:/Việc ngày/}).waitFor()
  await page.getByText('Bag bunches').first().waitFor()
  await page.getByRole('button',{name:'Ghi nhận',exact:true}).click()
  await page.getByRole('heading',{name:'Giao công việc mới'}).waitFor()
  await page.getByRole('heading',{name:'Ghi nhận sâu bệnh'}).waitFor()
  await page.getByRole('button',{name:'Tài khoản',exact:true}).click()
  await page.getByText('Quản trị viên').waitFor()
  await page.screenshot({path:path.join(output,'lotus-mobile-real.png'),fullPage:true})
  assert.deepEqual(errors,[])
  console.log('PASS: mobile entry loads on real Frappe with scope, tasks, actions and account tabs.')
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1})
