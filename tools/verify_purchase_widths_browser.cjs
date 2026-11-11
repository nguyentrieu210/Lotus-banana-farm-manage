// Usage on the VPS test folder (playwright-core + /usr/bin/chromium): node tools/verify_purchase_widths_browser.cjs http://<test-container-ip>:8000 <admin-password> <out-dir>
// Real-browser check of the spec 003 screens at 320 / 390 / 844 / 1440 px (T103, T106) against the test copy site.
// node widths.cjs <base-url> <admin-password> <out-dir>
const {chromium}=require('playwright-core')
const fs=require('fs')
const [base,password,out]=process.argv.slice(2)
const desktop=[['de-xuat','/lotus/mua-hang?buying_view=needs'],['don-mua','/lotus/mua-hang?buying_view=orders'],['phieu-nhan','/lotus/mua-hang?buying_view=receipts'],
 ['hoa-don','/lotus/mua-hang?buying_view=invoices'],['hoa-don-cho-nhap','/lotus/mua-hang?buying_view=invoice-queue'],['cong-no','/lotus/mua-hang?buying_view=payables'],
 ['thanh-toan','/lotus/mua-hang?buying_view=payments'],['cho-ky','/lotus/cho-ky'],['kho-nhap','/lotus/kho?stock_view=receipts'],['tai-chinh-cho-hach-toan','/lotus/tai-chinh?tab=pending']]
const phone=[['pwa-mua-hang','/buying'],['pwa-kho','/warehouse']]
const actions={
 'cong-no':[['so-chi-tiet','Sổ chi tiết'],['tra-tien','Trả tiền']],
 'hoa-don-cho-nhap':[['hoa-don-dich-vu','Hóa đơn dịch vụ (không phiếu nhận)']],
}
const results=[]
async function measure(page){
 return page.evaluate(()=>{
  const doc=document.documentElement
  const wide=[...document.querySelectorAll('dialog[open],.lotus-mobile-form,.van-popup')].filter(e=>e.scrollWidth>e.clientWidth+2).map(e=>e.className||e.tagName)
  return {overflow:Math.max(0,doc.scrollWidth-window.innerWidth),dialogs:wide,text:document.body.innerText.length}
 })
}
;(async()=>{
 fs.mkdirSync(out,{recursive:true})
 const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']})
 for(const [width,height,list] of [[1440,900,desktop],[844,1180,[...desktop,...phone]],[390,844,phone],[320,700,phone]]){
  const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1})
  const login=await context.request.post(base+'/api/method/login',{form:{usr:'Administrator',pwd:password}})
  if(!login.ok())throw new Error('login failed '+login.status())
  for(const [id,url] of list){
   const page=await context.newPage(),errors=[]
   page.on('pageerror',e=>errors.push(String(e.message).slice(0,160)))
   // The test stack runs no socket.io server: its connection errors are not page errors.
   page.on('console',m=>{if(m.type()==='error'&&!/socket\.io|WebSocket/.test(m.text()))errors.push(m.text().slice(0,160))})
   try{
    await page.goto(base+url,{waitUntil:'networkidle',timeout:60000})
    await page.waitForTimeout(1500)
    // "Có gì mới" opens once for a user who has not read the new release notes; close it like a person would.
    const news=page.locator('dialog[open][aria-label="Có gì mới"]')
    if(await news.count()){await news.getByRole('button',{name:'Đóng',exact:true}).first().click();await page.waitForTimeout(500)}
    const m=await measure(page)
    results.push({width,id,...m,errors:errors.slice(0,3)})
    if([1440,390].includes(width)||width===844&&phone.some(p=>p[0]===id))await page.screenshot({path:out+'/'+width+'-'+id+'.png'})
    for(const [name,label] of actions[id]||[]){
     const button=page.getByRole('button',{name:label,exact:true}).first()
     if(!await button.count()){results.push({width,id:id+'/'+name,skipped:'no button'});continue}
     await button.click();await page.waitForTimeout(1800)
     const inner=await measure(page)
     results.push({width,id:id+'/'+name,...inner,errors:errors.slice(0,3)})
     if(width===1440)await page.screenshot({path:out+'/'+width+'-'+id+'-'+name+'.png'})
     await page.keyboard.press('Escape');await page.waitForTimeout(400)
     const close=page.getByRole('button',{name:/^(Đóng|Hủy)$/}).first()
     if(await close.count()&&await close.isVisible().catch(()=>false)){await close.click().catch(()=>{});await page.waitForTimeout(300)}
    }
   }catch(e){results.push({width,id,failed:String(e.message).slice(0,200),errors:errors.slice(0,3)})}
   await page.close()
  }
  await context.close()
 }
 await browser.close()
 fs.writeFileSync(out+'/results.json',JSON.stringify(results,null,1))
 const bad=results.filter(r=>r.failed||r.overflow>2||r.dialogs?.length||r.errors?.length)
 for(const r of results)console.log([r.width,r.id,r.failed?'FAILED '+r.failed:r.skipped?'skipped: '+r.skipped:'overflow '+r.overflow+'px'+(r.dialogs?.length?' dialog-overflow':'')+(r.errors?.length?' errors: '+r.errors.join(' | '):'')+' text '+r.text].join('  '))
 console.log(bad.length?bad.length+' finding(s)':'no horizontal overflow, no page errors')
})().catch(e=>{console.error(e);process.exit(1)})
