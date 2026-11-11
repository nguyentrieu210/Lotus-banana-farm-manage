// Walk-through US4 (nhập kho) on the live-site copy: quickstart.md §3 US4. Needs the approved order of uat-3 (100 kg).
const L=require('./uat-lib.cjs')
const {file}=require('./uat-files.cjs')
const {step,expect,api,py,goto,shot,settle,state,save}=L
const PH={width:390,height:844,phone:true}
const bodyText=async page=>(await page.locator('body').innerText()).replace(/\s+/g,' ')
async function confirmPhone(page){const d=page.locator('[role=dialog]').filter({has:page.getByRole('button',{name:'Đồng ý',exact:true})}).last();await d.waitFor({timeout:10000});await d.getByRole('button',{name:'Đồng ý',exact:true}).click()}
async function draw(page,canvas){
 const box=await canvas.boundingBox();expect(box,'không thấy khung ký')
 await page.mouse.move(box.x+20,box.y+box.height*0.7);await page.mouse.down()
 for(let i=1;i<=24;i++)await page.mouse.move(box.x+20+i*(box.width-40)/24,box.y+box.height*(0.3+0.4*Math.abs(Math.sin(i/3))),{steps:2})
 await page.mouse.up()
}
// Phone Kho: home → Nhập theo đơn → the order → the receive form
async function openReceiveForm(context,label){
 const page=await goto(context,'/warehouse')
 const store=page.locator('select').first()
 if(await store.count()){const opts=await store.locator('option').allTextContents();const pick=opts.find(o=>/Văn Phòng 222/.test(o));if(pick)await store.selectOption({label:pick}).catch(()=>{})}
 await settle(page,800)
 await page.getByText('Nhập theo đơn',{exact:true}).first().click();await settle(page,2500)
 await page.locator('button',{hasText:state.order}).first().click();await settle(page,2500)
 if(label)await shot(page,label)
 return page
}
;(async()=>{
 await L.start()
 const admin=await L.login('admin'),keeper=await L.login('keeper',PH)
 const receipts=()=>JSON.parse(py(`print(json.dumps(frappe.db.sql("""select distinct pr.name, pr.docstatus, pri.qty from \`tabPurchase Receipt\` pr join \`tabPurchase Receipt Item\` pri on pri.parent=pr.name where pri.purchase_order=%s and pr.is_return=0 order by pr.creation""", '${state.order}', as_dict=True), default=str))`).trim().split('\n').pop())
 let page
 await step('Thủ kho nhận 60/100 kg trên điện thoại: 2 ảnh hàng và ảnh hóa đơn PDF, người giao ký trên màn hình kèm họ tên',async()=>{
  page=await openReceiveForm(keeper,'us4-01-form-nhan-hang-dien-thoai')
  await page.getByLabel(/Số lượng thực nhận/).first().fill('60')
  await page.getByLabel('Họ tên người giao hàng').fill('Trần Văn Giao (xe NCC A)')
  await page.getByRole('button',{name:'Người giao ký trên màn hình'}).click();await settle(page,800)
  await draw(page,page.locator('.lotus-signature-draw canvas'))
  await shot(page,'us4-02-nguoi-giao-ky')
  await page.getByRole('button',{name:'Dùng chữ ký này'}).click();await settle(page,600)
  await page.locator('input[type=file][aria-label="Thêm ảnh hàng, hóa đơn"]').setInputFiles([file('hang-1.png'),file('hang-2.png'),file('hoa-don-ncc.pdf','pdf','Hoa don NCC A 0001234')])
  await settle(page,600)
  await shot(page,'us4-03-du-thong-tin-nguoi-giao')
  return 'đủ người giao và 3 tệp'
 },page)
 await step('Mạng rớt đúng lúc xác nhận (máy chủ đã ghi, điện thoại không nhận được trả lời); bấm lại chỉ có một phiếu',async()=>{
  let cut=true
  await page.route('**/api/method/lotus_farm.warehouse_planning.receive_order',async route=>{
   if(!cut)return route.continue()
   cut=false
   await route.fetch()             // the server receives and posts the receipt
   await route.abort('internetdisconnected')   // the answer never reaches the phone
  })
  await page.getByRole('button',{name:'Xác nhận nhập kho',exact:true}).click()
  await confirmPhone(page);await settle(page,3000)
  await shot(page,'us4-04-mat-mang-luc-xac-nhan')
  const first=await bodyText(page)
  expect(receipts().length===1,'sau lần đầu đã có '+receipts().length+' phiếu')
  await page.getByRole('button',{name:'Xác nhận nhập kho',exact:true}).click()
  await confirmPhone(page);await settle(page,4000)
  await shot(page,'us4-05-bam-lai-sau-khi-co-mang')
  const rows=receipts()
  expect(rows.length===1&&rows[0].docstatus===1&&Number(rows[0].qty)===60,'phiếu sau khi bấm lại: '+JSON.stringify(rows))
  state.receipt1=rows[0].name;save()
  const done=await bodyText(page)
  expect(/Đã nhập kho/.test(done),'không báo đã nhập kho: '+done.slice(0,200))
  return (first.match(/Mạng[^.]*\./)||[''])[0]+' → '+(done.match(/Đã nhập kho[^.]*\./)||[''])[0]
 },page)
 await step('Phiếu mang chữ ký thủ kho, có bản PDF lưu; đơn còn chờ 40 kg',async()=>{
  const st=await api(admin,'lotus_farm.signing.chain_status',{doctype:'Purchase Receipt',name:state.receipt1})
  expect(st.chain==='purchase_receipt'&&st.steps[0].state==='Đã ký'&&st.signed_copy?.pdf_sha256,'chữ ký phiếu nhập: '+JSON.stringify({chain:st.chain,steps:st.steps.map(s=>s.state),copy:!!st.signed_copy}))
  const left=py(`print(frappe.db.sql("select qty-received_qty from \`tabPurchase Order Item\` where parent=%s",'${state.order}')[0][0])`).trim().split('\n').pop()
  expect(Number(left)===40,'đơn còn chờ '+left)
  const files=py(`print(frappe.db.count('File',{'attached_to_doctype':'Purchase Receipt','attached_to_name':'${state.receipt1}'}))`).trim().split('\n').pop()
  return 'ký bởi '+st.steps[0].name+' · '+files+' tệp gắn phiếu'
 })
 await step('Bản in phiếu nhập có chữ ký người giao, họ tên và chữ ký thủ kho',async()=>{
  const desk=await L.login('keeper')
  const p=await goto(desk,'/lotus/in-phieu?doctype=Purchase%20Receipt&name='+encodeURIComponent(state.receipt1),'us4-06-ban-in-phieu-nhap')
  const text=await bodyText(p)
  for(const want of ['Người giao hàng','Trần Văn Giao','Thủ kho nhận hàng'])expect(text.includes(want),'bản in thiếu "'+want+'"')
  expect(await p.locator('img[alt^="Chữ ký"]').count()>=2,'bản in thiếu ảnh chữ ký')
 })
 await step('Nhận 40 kg còn lại khi chưa có chữ ký và chưa có ảnh phiếu giao: nút xác nhận khóa, có lời nhắc',async()=>{
  page=await openReceiveForm(keeper)
  await page.getByLabel(/Số lượng thực nhận/).first().fill('40');await settle(page,600)
  await shot(page,'us4-07-thieu-nguoi-giao')
  const button=page.getByRole('button',{name:'Xác nhận nhập kho',exact:true})
  expect(await button.isDisabled(),'nút xác nhận vẫn bật')
  const text=await bodyText(page)
  expect(/Cần chữ ký kèm họ tên của người giao hàng, hoặc ảnh phiếu giao hàng có chữ ký/.test(text),'không có lời nhắc')
  let refused=''
  try{await api(keeper,'lotus_farm.warehouse_planning.receive_order',{name:state.order,posting_date:L.days(0),quantities:{[(await api(admin,'lotus_farm.warehouse_planning.purchase_order',{name:state.order})).items[0].line]:40},client_event_id:'uat-noev-'+Date.now(),post:1})}catch(e){refused=e.message}
  expect(/người giao hàng/.test(refused),'máy chủ không chặn: '+refused)
  return refused.replace(/^.*?: /,'')
 },page)
 await step('Hai người cùng nhận 40 kg còn lại (điện thoại và máy tính): chỉ một bên được, bên kia biết còn nhận được 0',async()=>{
  // Phone: keeper, with the photographed delivery note.
  const a=page
  await a.locator('input[type=file][aria-label="Chụp phiếu giao hàng có chữ ký"]').setInputFiles(file('phieu-giao-a.png'));await settle(a,500)
  // Desktop: the second storekeeper, Kho › Phiếu nhập kho › Nhập theo đơn mua › pick the order.
  const k2=await L.login('keeper2')
  const b=await goto(k2,'/lotus/kho?stock_view=receipts')
  await b.getByRole('button',{name:'Nhập theo đơn mua'}).first().click();await settle(b,2000)
  const field=b.getByRole('combobox',{name:/Đơn mua chờ nhận/}).or(b.getByLabel('Đơn mua chờ nhận')).first()
  await field.click();await settle(b,500)
  await b.keyboard.type(state.order);await settle(b,800)
  await b.getByRole('option',{name:new RegExp(state.order)}).first().click()
  await b.getByRole('button',{name:'Mở đơn nhận hàng'}).click();await settle(b,2500)
  await b.getByLabel(/^Thực nhận dòng 1/).fill('40')
  await b.locator('input[type=file][aria-label="Ảnh phiếu giao hàng có chữ ký"]').setInputFiles(file('phieu-giao-b.png'));await settle(b,500)
  await shot(b,'us4-08-may-tinh-nhan-cung-luc')
  // Both press at the same moment.
  await Promise.all([
   (async()=>{await a.getByRole('button',{name:'Xác nhận nhập kho',exact:true}).click();await confirmPhone(a)})(),
   (async()=>{await b.getByRole('button',{name:'Xác nhận nhập kho',exact:true}).click();const dlg=b.getByRole('dialog').filter({has:b.getByRole('button',{name:/^(Đồng ý|Xác nhận)$/})}).last();await dlg.waitFor({timeout:10000});await dlg.getByRole('button',{name:/^(Đồng ý|Xác nhận)$/}).last().click()})()
  ])
  await Promise.all([settle(a,5000),settle(b,5000)])
  await shot(a,'us4-09-ket-qua-dien-thoai');await shot(b,'us4-10-ket-qua-may-tinh')
  const rows=receipts()
  expect(rows.length===2&&rows.every(r=>r.docstatus===1)&&rows.reduce((s,r)=>s+Number(r.qty),0)===100,'phiếu nhận: '+JSON.stringify(rows))
  const ta=await bodyText(a),tb=await bodyText(b)
  const loser=/còn nhận được 0/.test(ta)?'điện thoại':/còn nhận được 0/.test(tb)?'máy tính':''
  expect(loser,'không bên nào được báo "còn nhận được 0": '+ta.slice(0,160)+' | '+tb.slice(0,160))
  state.receipt2=rows[1].name;save()
  return 'bên chậm hơn: '+loser
 })
 await step('Trả 5 kg trong app điện thoại từ Lịch sử: phiếu trả ghi sổ ngay',async()=>{
  const p=await goto(keeper,'/warehouse')
  await p.getByRole('button',{name:'Lịch sử'}).or(p.getByLabel('Lịch sử')).first().click();await settle(p,2500)
  await p.locator('button',{hasText:state.receipt1}).first().click();await settle(p,3000)
  await shot(p,'us4-11-chi-tiet-phieu-nhap-dien-thoai')
  await p.getByRole('button',{name:'Trả hàng',exact:true}).click();await settle(p,800)
  await p.getByLabel(/^Trả lại · /).first().fill('5')
  await p.getByLabel('Lý do trả hàng').fill('Bao rách, ẩm')
  await p.getByRole('button',{name:'Xác nhận trả hàng',exact:true}).click()
  await confirmPhone(p);await settle(p,4000)
  await shot(p,'us4-12-da-tra-hang')
  const back=JSON.parse(py(`print(json.dumps(frappe.get_all('Purchase Receipt',filters={'return_against':'${state.receipt1}'},fields=['name','docstatus'])))`).trim().split('\n').pop())
  expect(back.length===1&&back[0].docstatus===1,'phiếu trả: '+JSON.stringify(back))
  const text=await bodyText(p)
  return (text.match(/Đã trả hàng[^.]*\./)||[back[0].name])[0]
 })
 await L.browser.close()
 process.exit(L.finish('uat-4')?1:0)
})().catch(e=>{console.error(e);process.exit(2)})
