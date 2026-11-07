// Run against Vite with API fixtures. All write requests are rejected.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const {chromium} = require(process.env.PLAYWRIGHT_PATH || 'playwright')
const base = process.env.LOTUS_UI_TEST_URL || 'http://127.0.0.1:5173/assets/lotus_farm/frontend/'
const output = path.join(os.tmpdir(), 'lotus-purchase-flow-qa')
const items = [{name:'UREA',item_name:'Phân urê',stock_uom:'Kg',is_stock_item:1}]
const warehouses = [{name:'WH',warehouse_name:'Kho chính'}]
const suppliers = [{name:'SUP',supplier_name:'Nhà cung cấp kiểm thử'}]
const session = {user:'qa@example.invalid',csrf_token:'test',today:'2026-11-07',companies:[{name:'Lotus Agritech'}],
 can_create:true,can_request:true,can_approve:true,permissions:{'Stock Entry':true,'Purchase Receipt':true},farms:[]}
const catalog = {warehouses,items,suppliers,requests:[],conversions:[],can_create:true,can_request:true,can_create_supplier:true,currency:'VND'}

async function main() {
 fs.mkdirSync(output,{recursive:true})
 const browser = await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})})
 const results = []
 try {
  for (const width of [320,390,844]) {
   for (const app of ['warehouse','buying','work-mobile']) {
    const page = await browser.newPage({viewport:{width,height:width===844?390:844},serviceWorkers:'block'})
    const errors = []
    page.on('pageerror',error=>errors.push(error.message))
    await page.addInitScript(()=>{for(const app of ['warehouse','buying','work'])localStorage.setItem('lotus-pwa-setup-v1:'+app,'done')})
    await page.route('**/api/method/**',async route=>{
     const request=route.request(),method=new URL(request.url()).pathname.split('/').pop(),name=method.split('.').pop()
     assert.equal(request.method(),'GET','UI review must not submit business documents')
     let value={}
     if(name==='bootstrap')value=session
     else if(['setup','catalog','form_data'].includes(name))value={...catalog,proposer:'Người kiểm thử',department:'Kho'}
     else if(name==='overview')value={items:[],rows:[],warehouses,total_count:0}
     else if(name==='inbox')value={items:[],unread:0}
     else if(name==='config')value={enabled:false}
     else if(['orders','requests','suppliers','proposals','employee_choices'].includes(name))value=name==='suppliers'?suppliers:[]
     else if(name==='signer_options')value={steps:[{key:'PROPOSE',title:'Người đề xuất'},{key:'DEPARTMENT',title:'Phụ trách bộ phận'},{key:'PURCHASING',title:'Kế toán / mua hàng'},{key:'APPROVE',title:'Giám đốc'}],candidates:{},diagnostics:{}}
     await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({message:value})})
    })
    await page.goto(base+app+'.html')
    await page.waitForLoadState('networkidle')
    if(app==='buying') {
     await page.getByText('Đề xuất mua vật tư',{exact:true}).first().click()
     await page.getByRole('button',{name:/Lập đề xuất mua vật tư/}).click()
     await page.getByText('Kho nhận hàng',{exact:true}).waitFor()
    }
    if(app==='warehouse') {
     await page.getByText('Tạo đơn mua',{exact:true}).first().click()
     await page.getByRole('button',{name:/Thêm mặt hàng/}).click()
    }
    const dimensions=await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth}))
    assert.ok(dimensions.content<=width+1,`${app} overflows at ${width}px: ${dimensions.content}`)
    assert.deepEqual(errors,[],`${app} browser errors`)
    await page.screenshot({path:path.join(output,`${app}-${width}.png`),fullPage:true})
    results.push({app,width,...dimensions})
    await page.close()
   }
  }
  console.log(JSON.stringify({ok:true,results,screenshots:output},null,2))
 } finally {await browser.close()}
}
main().catch(error=>{console.error(error);process.exitCode=1})
