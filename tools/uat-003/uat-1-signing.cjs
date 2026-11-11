// Walk-through US1 (ký điện tử) and US2 (đề xuất mua) on the live-site copy: quickstart.md §3.
const L=require('./uat-lib.cjs')
const {step,expect,api,py,goto,shot,settle,state,save}=L
const P='lotus_farm.purchase_proposal.',S='lotus_farm.signing.'
async function inboxList(page){
 for(const close of await page.locator('.van-popup .van-popup__close-icon').all())if(await close.isVisible().catch(()=>false)){await close.click().catch(()=>{});await page.waitForTimeout(500)}
 await page.getByRole('button',{name:/^Chờ tôi ký/}).first().click();await settle(page)
 return page.locator('section[aria-label="Chờ tôi ký"]')
}
;(async()=>{
 await L.start()
 const admin=await L.login('admin')
 const company=L.cfg.company
 const email=k=>L.cfg.users[k][0]
 await step('Chọn dữ liệu nền (kho, mặt hàng, nhà cung cấp) trên bản sao',async()=>{
  const stores=await api(admin,'frappe.client.get_list',{doctype:'Warehouse',filters:{company,is_group:0,disabled:0},fields:['name'],limit_page_length:50})
  const items=await api(admin,'frappe.client.get_list',{doctype:'Item',filters:{is_stock_item:1,is_purchase_item:1,disabled:0,has_batch_no:0,has_serial_no:0,is_fixed_asset:0},
   fields:['name','item_name','stock_uom'],limit_page_length:200})
  const sups=await api(admin,'frappe.client.get_list',{doctype:'Supplier',filters:{disabled:0},fields:['name','supplier_name'],limit_page_length:20})
  const item=items.find(i=>['Bao','Kg','Can','Chai','Lít'].includes(i.stock_uom))||items[0]
  Object.assign(state,{company,warehouse:stores.find(s=>/222/.test(s.name))?.name||stores[0].name,item:item.name,item_name:item.item_name,uom:item.stock_uom,supplierA:sups[0].name,supplierB:sups[1].name})
  save()
  return [state.warehouse,state.item+' ('+state.uom+')',state.supplierA,state.supplierB].join(' · ')
 })
 const proposer=await L.login('proposer')
 const signers={DEPARTMENT:email('head'),PURCHASING:email('buyer'),APPROVE:email('director')}
 await step('Tổ trưởng lập 4 đề xuất và gửi ký (3 người ký được chỉ định)',async()=>{
  state.proposals=[]
  for(let i=1;i<=4;i++){
   const d=await api(proposer,P+'save_proposal',{company,values:{reason:'UAT '+i+': mua vật tư cho lô thử',department:'Tổ UAT',warehouse:state.warehouse,
    items:[{item_code:state.item,qty:100,rate:120000,uom:state.uom,schedule_date:L.days(7)}]}})
   const s=await api(proposer,P+'sign',{name:d.name,modified:d.modified,signers})
   expect(s.state&&s.name,'gửi ký không trả về trạng thái')
   const rate=py(`print(frappe.db.get_value('Material Request Item',{'parent':'${d.name}'},'rate'))`).trim().split('\n').pop()
   expect(Number(rate)===120000,d.name+': đơn giá sau khi lưu là '+rate+', không phải 120000 người đề xuất gõ')
   state.proposals.push(d.name)
  }
  save();return state.proposals.join(', ')
 })
 // ---- Trưởng bộ phận: chỉ có vai trò phụ trách, ký trên điện thoại từ Chờ tôi ký của app Công việc
 const head=await L.login('head',{width:390,height:844,phone:true})
 let page=await goto(head,'/work','us1-01-truong-bo-phan-app-cong-viec')
 await step('Trưởng bộ phận (không có quyền xem danh sách đề xuất) thấy 4 đề xuất trong Chờ tôi ký trên điện thoại',async()=>{
  const bell=page.getByRole('button',{name:/^Chờ tôi ký: \d+ chứng từ$/})
  await bell.waitFor({timeout:20000})
  const label=await bell.getAttribute('aria-label')
  await bell.click();await settle(page)
  await shot(page,'us1-02-cho-toi-ky-dien-thoai')
  const panel=page.locator('section[aria-label="Chờ tôi ký"]')
  for(const n of state.proposals)expect(await panel.getByText(n).count(),'thiếu '+n+' trong danh sách')
  return label
 },page)
 await step('Mở một đề xuất, xem bản in, ký sau hộp xác nhận',async()=>{
  const panel=page.locator('section[aria-label="Chờ tôi ký"]')
  await panel.locator('.van-cell',{hasText:state.proposals[0]}).locator('.van-cell__title, .van-cell__value').first().click()
  const sheet=page.locator('section[aria-label="Ký '+state.proposals[0]+'"]')
  await sheet.waitFor({timeout:15000});await settle(page,2500)
  await shot(page,'us1-03-tam-ky-dien-thoai')
  await sheet.getByRole('button',{name:/^Ký: /}).click()
  const dialog=page.locator('[role=dialog]').filter({hasText:'Ký chứng từ'}).last()
  await dialog.waitFor({timeout:10000})
  const text=(await dialog.innerText()).replace(/\s+/g,' ')
  await shot(page,'us1-04-hop-xac-nhan-ky')
  await dialog.getByRole('button',{name:'Ký',exact:true}).click();await settle(page,2500)
  const st=await api(admin,S+'chain_status',{doctype:'Material Request',name:state.proposals[0]})
  expect(st.steps[1].state==='Đã ký','bước phụ trách chưa ký: '+st.steps[1].state)
  return text.slice(0,160)
 },page)
 await step('Ký nhiều trên điện thoại: chọn 2 đề xuất, xác nhận một lần',async()=>{
  const panel=await inboxList(page)
  for(const n of state.proposals.slice(1,3))await panel.getByRole('checkbox',{name:'Chọn '+n}).click()
  await panel.getByRole('button',{name:/^Ký \d+ chứng từ đã chọn$/}).click()
  const dialog=page.locator('[role=dialog]').filter({hasText:'Ký nhiều chứng từ'}).last();await dialog.waitFor({timeout:10000})
  await shot(page,'us1-05-ky-nhieu-dien-thoai')
  await dialog.getByRole('button',{name:'Ký',exact:true}).click();await settle(page,3000)
  await shot(page,'us1-06-ky-nhieu-xong')
  for(const n of state.proposals.slice(1,3)){
   const st=await api(admin,S+'chain_status',{doctype:'Material Request',name:n})
   expect(st.steps[1].state==='Đã ký',n+': bước phụ trách chưa ký')
  }
 },page)
 // ---- Chuyển người ký bước 2 có lý do (US1.5)
 await step('Trưởng bộ phận chuyển bước của mình sang người khác, có lý do; lịch sử có REASSIGN',async()=>{
  const panel=await inboxList(page)
  await panel.locator('.van-cell',{hasText:state.proposals[3]}).locator('.van-cell__title, .van-cell__value').first().click()
  const sheet=page.locator('section[aria-label="Ký '+state.proposals[3]+'"]');await sheet.waitFor({timeout:15000});await settle(page,1500)
  await sheet.getByRole('button',{name:'Chuyển người ký',exact:true}).click();await settle(page,1500)
  await shot(page,'us1-07-chuyen-nguoi-ky')
  // Người ký thay: a select of eligible people; the reason is free text.
  const who=sheet.locator('select').first()
  if(await who.count()){const opts=await who.locator('option').allTextContents();const pick=opts.find(o=>/thay UAT/.test(o));expect(pick,'không có người thay trong danh sách: '+opts.join(', '));await who.selectOption({label:pick})}
  else{await sheet.getByText('Người ký thay').click();await page.getByText('Trưởng bộ phận thay UAT').first().click()}
  await sheet.getByPlaceholder('Ví dụ: người ký đang nghỉ phép').fill('Trưởng bộ phận nghỉ phép tuần này')
  await shot(page,'us1-08-chuyen-nguoi-ky-dien')
  await sheet.getByRole('button',{name:/^Chuyển/}).last().click();await settle(page,2500)
  const moved=py(`print(json.dumps(frappe.get_all('Lotus Signature Event',filters={'document_name':'${state.proposals[3]}','action':'REASSIGN'},pluck='details'),ensure_ascii=False))`)
  expect(/nghỉ phép/.test(moved)&&moved.includes(email('head2')),'không thấy sự kiện REASSIGN: '+moved)
  return 'đã chuyển cho '+email('head2')
 },page)
 // ---- Mua hàng ký nhiều trên máy tính
 const buyer=await L.login('buyer')
 page=await goto(buyer,'/lotus/cho-ky','us1-09-cho-toi-ky-may-tinh')
 await step('Mua hàng ký nhiều trên máy tính (/lotus/cho-ky)',async()=>{
  for(const n of state.proposals.slice(0,3))expect(await page.getByText(n,{exact:true}).count(),'thiếu '+n)
  await page.getByRole('button',{name:'Chọn tất cả dòng trang này'}).click()
  await page.getByRole('button',{name:/^Ký \d+ chứng từ đã chọn$/}).click()
  const dialog=page.getByRole('dialog').filter({hasText:'Ký nhiều chứng từ'}).last();await dialog.waitFor({timeout:10000})
  await shot(page,'us1-10-xac-nhan-ky-nhieu-may-tinh')
  await dialog.getByRole('button',{name:'Ký',exact:true}).click();await settle(page,4000)
  for(const n of state.proposals.slice(0,3)){const st=await api(admin,S+'chain_status',{doctype:'Material Request',name:n});expect(st.steps[2].state==='Đã ký',n+': bước mua hàng chưa ký')}
 },page)
 // ---- Hai phiếu chi chờ giám đốc (US1.3): kế toán lập, kế toán trưởng ký trên điện thoại app Mua hàng
 const acc=await L.login('accountant')
 await step('Kế toán lập 2 phiếu chi trả một hóa đơn đang nợ',async()=>{
  const open=py(`from lotus_farm.finance import setup
rows=frappe.db.sql("""select name,supplier,outstanding_amount from \`tabPurchase Invoice\` where docstatus=1 and is_return=0 and company=%s and outstanding_amount>5000000 order by outstanding_amount desc limit 1""",setup.company(),as_dict=True)
print(json.dumps(rows,default=str))`)
  const inv=JSON.parse(open.trim().split('\n').pop())[0];expect(inv,'không có hóa đơn đang nợ')
  state.vouchers=[]
  for(const [i,amount] of [[1,100000],[2,200000]]){
   const v=await api(acc,'lotus_farm.finance.supplier_payment.prepare',{supplier:inv.supplier,allocations:[{doctype:'Purchase Invoice',name:inv.name,amount}],
    mode:'bank',reference_no:'UNC-UAT-'+i,signers:{CHIEF:email('chief'),APPROVE:email('director')},client_key:'uat-v'+i+'-'+Date.now()})
   state.vouchers.push(v.voucher)
  }
  state.paid_invoice=inv.name;save();return state.vouchers.join(', ')+' cho '+inv.name
 })
 const chief=await L.login('chief',{width:390,height:844,phone:true})
 let cpage=await goto(chief,'/buying','us1-11-ke-toan-truong-app-mua-hang')
 await step('Kế toán trưởng ký 2 phiếu chi trên điện thoại (app Mua hàng, nơi thông báo phiếu chi tới)',async()=>{
  const bell=cpage.getByRole('button',{name:/^Chờ tôi ký: \d+ chứng từ$/})
  await bell.waitFor({timeout:20000});await bell.click();await settle(cpage)
  const panel=cpage.locator('section[aria-label="Chờ tôi ký"]')
  for(const n of state.vouchers)await panel.getByRole('checkbox',{name:'Chọn '+n}).click()
  await panel.getByRole('button',{name:/^Ký \d+ chứng từ đã chọn$/}).click()
  const dialog=cpage.locator('[role=dialog]').filter({hasText:'Ký nhiều chứng từ'}).last();await dialog.waitFor({timeout:10000})
  await shot(cpage,'us1-12-ky-truong-ky-phieu-chi')
  await dialog.getByRole('button',{name:'Ký',exact:true}).click();await settle(cpage,3000)
  for(const n of state.vouchers){const st=await api(admin,S+'chain_status',{doctype:'Payment Entry',name:n});expect(st.steps[1].state==='Đã ký',n+': kế toán trưởng chưa ký')}
 },cpage)
 // ---- Giám đốc: 5 chứng từ, một chứng từ bị sửa ở nơi khác trong lúc đang ký nhiều
 const director=await L.login('director')
 page=await goto(director,'/lotus/cho-ky','us1-13-giam-doc-cho-toi-ky')
 await step('Giám đốc thấy 5 chứng từ (3 đề xuất, 2 phiếu chi); ký nhiều, một phiếu bị sửa thì báo riêng',async()=>{
  for(const n of [...state.proposals.slice(0,3),...state.vouchers])expect(await page.getByText(n,{exact:true}).count(),'thiếu '+n)
  await page.getByRole('button',{name:'Chọn tất cả dòng trang này'}).click()
  // Someone changes the second voucher after the list was opened (only its version stamp: content unchanged).
  py(`frappe.db.sql("update \`tabPayment Entry\` set modified=now(6) where name=%s", '${state.vouchers[1]}')`)
  await page.getByRole('button',{name:/^Ký \d+ chứng từ đã chọn$/}).click()
  const dialog=page.getByRole('dialog').filter({hasText:'Ký nhiều chứng từ'}).last();await dialog.waitFor({timeout:10000})
  await dialog.getByRole('button',{name:'Ký',exact:true}).click();await settle(page,6000)
  await shot(page,'us1-14-ky-nhieu-mot-dong-loi')
  const failures=await page.locator('ul[aria-label="Chứng từ chưa ký được"]').innerText()
  expect(failures.includes(state.vouchers[1]),'không báo phiếu bị sửa: '+failures)
  const done=py(`print(json.dumps({n:frappe.db.get_value(dt,n,'docstatus') for dt,n in [${[...state.proposals.slice(0,3).map(n=>"('Material Request','"+n+"')"),...state.vouchers.map(n=>"('Payment Entry','"+n+"')")].join(',')}]}))`)
  const s=JSON.parse(done.trim().split('\n').pop())
  expect(state.proposals.slice(0,3).every(n=>s[n]===1)&&s[state.vouchers[0]]===1&&s[state.vouchers[1]]===0,'trạng thái sau ký: '+JSON.stringify(s))
  return failures.replace(/\s+/g,' ').slice(0,200)
 },page)
 await step('Giám đốc mở lại phiếu bị sửa và ký riêng',async()=>{
  await page.getByRole('button',{name:'Làm mới',exact:true}).click();await settle(page,2500)
  await page.getByRole('gridcell',{name:state.vouchers[1],exact:true}).first().click();await settle(page,2500)
  await shot(page,'us1-15-tam-ky-may-tinh')
  await page.getByRole('button',{name:/^Ký: /}).first().click()
  const dialog=page.getByRole('dialog').filter({hasText:'Ký chứng từ'}).last();await dialog.waitFor({timeout:10000})
  await dialog.getByRole('button',{name:'Ký',exact:true}).click();await settle(page,5000)
  const ds=py(`print(frappe.db.get_value('Payment Entry','${state.vouchers[1]}','docstatus'))`).trim().split('\n').pop()
  expect(ds==='1','phiếu chi chưa ghi sổ: '+ds)
 },page)
 await step('Ký đủ thì có bản PDF lưu; trang /verify/lotus báo khớp bản lưu (đường QR in trên phiếu)',async()=>{
  const st=await api(admin,S+'chain_status',{doctype:'Payment Entry',name:state.vouchers[0]})
  expect(st.signed_copy?.pdf_sha256,'không có bản PDF đã ký')
  const url=py(`from lotus_farm import signing
d=frappe.get_doc('Payment Entry','${state.vouchers[0]}')
print(signing.verify_url(d))`).trim().split('\n').pop()
  const v=await goto(director,url.replace(/^https?:\/\/[^/]+/,''),'us1-16-trang-doi-chieu-qr')
  const text=await v.locator('body').innerText()
  expect(/Khớp bản lưu/.test(text),'trang đối chiếu không báo khớp bản lưu: '+text.slice(0,300))
  return url.replace(/t=[^&]+/,'t=…')
 })
 await step('Đổi ảnh chữ ký sau khi đã ký: bản PDF đã lưu và ảnh ở bước đã ký không đổi',async()=>{
  const before=await api(admin,S+'chain_status',{doctype:'Material Request',name:state.proposals[3]})
  const shaBefore=(await api(admin,S+'chain_status',{doctype:'Payment Entry',name:state.vouchers[0]})).signed_copy.pdf_sha256
  py(`from PIL import Image, ImageDraw
from io import BytesIO
from base64 import b64encode
import random
from lotus_farm import digital_signature
for u in ('${email('proposer')}','${email('director')}'):
    im=Image.new('RGB',(400,140),'white');ImageDraw.Draw(im).line([(10,120),(390,random.randint(5,60))],fill='black',width=6)
    b=BytesIO();im.save(b,format='PNG')
    frappe.set_user(u);digital_signature.save_my_signature_image('data:image/png;base64,'+b64encode(b.getvalue()).decode())
frappe.set_user('Administrator')`)
  const after=await api(admin,S+'chain_status',{doctype:'Material Request',name:state.proposals[3]})
  expect(before.steps[0].image&&before.steps[0].image===after.steps[0].image,'ảnh chữ ký bước 1 đổi theo hồ sơ')
  const r=await director.request.get(L.base+'/api/method/lotus_farm.signing.signed_pdf?doctype=Payment%20Entry&name='+encodeURIComponent(state.vouchers[0]))
  const buf=await r.body();const crypto=require('crypto');const sha=crypto.createHash('sha256').update(buf).digest('hex')
  expect(sha===shaBefore,'PDF tải về khác bản lưu')
  return 'pdf '+sha.slice(0,12)
 })
 await step('Email "Đến lượt bạn ký": link /lotus/mo mở màn máy tính, cùng link mở app trên điện thoại',async()=>{
  const q=py(`names=frappe.get_all('Email Queue Recipient',filters={'recipient':['in',['${email('head2')}','${email('head')}']]},pluck='parent')
rows=frappe.get_all('Email Queue',filters={'name':['in',names or ['']]},fields=['name','message'],order_by='creation desc',limit=200)
import re, quopri
for r in rows: r.message=quopri.decodestring((r.message or '').encode()).decode('utf-8','ignore')
links=[]
for r in rows:
    m=re.search(r'/lotus/mo\\?[^"\\s<]+',r.message or '')
    if m: links.append(m.group(0).replace('&amp;','&'))
print(json.dumps(links[:5]))`)
  const links=JSON.parse(q.trim().split('\n').pop())
  expect(links.length,'không có email nào trong hàng đợi chứa link /lotus/mo')
  const link=links.find(l=>l.includes(state.proposals[0]))||links[0]
  const head2=await L.login('head'),phone2=await L.login('head',{width:390,height:844,phone:true})
  const d=await goto(head2,link,'us1-17-link-email-may-tinh'),m=await goto(phone2,link,'us1-18-link-email-dien-thoai')
  const du=new URL(d.url()).pathname+new URL(d.url()).search,mu=new URL(m.url()).pathname+new URL(m.url()).search
  expect(!du.startsWith('/lotus/mo')&&!mu.startsWith('/lotus/mo'),'link không chuyển tiếp: '+du+' / '+mu)
  expect(du!==mu,'máy tính và điện thoại mở cùng một chỗ: '+du)
  return 'máy tính → '+decodeURIComponent(du)+' · điện thoại → '+decodeURIComponent(mu)
 })
 // ---- US2: bảng đề xuất; hủy đề xuất nháp có lý do qua giao diện
 await step('Bảng đề xuất mua trên máy tính có số đếm theo giai đoạn',async()=>{
  const p=await goto(buyer,'/lotus/mua-hang?buying_view=needs','us2-01-bang-de-xuat')
  const text=(await p.locator('body').innerText()).replace(/\s+/g,' ')
  expect(/Chờ mua/.test(text),'không thấy giai đoạn Chờ mua')
  const counts=await api(buyer,P+'proposals',{company,view:'all'})
  return JSON.stringify(counts.counts)
 })
 await step('Tổ trưởng hủy một đề xuất đã duyệt chưa có đơn: bắt buộc lý do, sang Đã hủy',async()=>{
  const d={name:state.proposals[2]};state.cancelled=d.name;save()
  const p=await goto(proposer,'/lotus/mua-hang?buying_view=needs')
  await p.getByText(d.name,{exact:true}).first().click();await settle(p,2500)
  await p.getByRole('button',{name:'Hủy đề xuất',exact:true}).first().click();await settle(p,800)
  const confirm=p.getByRole('button',{name:'Hủy đề xuất',exact:true}).first()
  expect(await confirm.isDisabled(),'nút hủy bật khi chưa có lý do')
  await p.getByLabel('Lý do hủy đề xuất').fill('Đã mua đủ ở đợt trước')
  await shot(p,'us2-02-huy-de-xuat-co-ly-do')
  await confirm.click();await settle(p,1000)
  const ask=p.getByRole('dialog').filter({hasText:/Hủy/}).last()
  if(await ask.count())await ask.getByRole('button',{name:/^(Đồng ý|Hủy đề xuất|Xác nhận)$/}).last().click().catch(()=>{})
  await settle(p,3000)
  const s=await api(admin,P+'detail',{name:d.name})
  expect(s.stage==='Đã hủy','giai đoạn sau khi hủy: '+s.stage)
  await shot(p,'us2-03-de-xuat-da-huy')
 })
 await L.browser.close()
 process.exit(L.finish('uat-1')?1:0)
})().catch(e=>{console.error(e);process.exit(2)})
