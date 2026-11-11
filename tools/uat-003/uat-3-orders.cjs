// Walk-through US3 (đơn mua) on the live-site copy: quickstart.md §3 US3. Needs the state of uat-1 (approved proposals).
const L=require('./uat-lib.cjs')
const {step,expect,api,py,goto,shot,settle,state,save}=L
const PR='lotus_farm.procurement.',PU='lotus_farm.purchasing.',WB='lotus_farm.warehouse_buying_lite.'
async function confirmDesktop(page){const d=page.getByRole('dialog').filter({has:page.getByRole('button',{name:/^(Đồng ý|Ký|Xác nhận)$/})}).last();await d.waitFor({timeout:10000});await d.getByRole('button',{name:/^(Đồng ý|Ký|Xác nhận)$/}).last().click();await settle(page,2500)}
async function openOrderDesktop(context,name,shotName){
 const page=await goto(context,'/lotus/mua-hang?buying_view=orders')
 await page.getByRole('gridcell',{name,exact:true}).first().click();await settle(page,2500)
 if(shotName)await shot(page,shotName)
 return page
}
;(async()=>{
 await L.start()
 const admin=await L.login('admin'),buyer=await L.login('buyer'),director=await L.login('director')
 const company=state.company,email=k=>L.cfg.users[k][0]
 const [P1,P2]=state.proposals
 let line,QA,QB
 await step('Mua hàng nhập 2 báo giá cho đề xuất đã duyệt (NCC A 120.000 đ, NCC B 110.000 đ)',async()=>{
  const d=await api(buyer,'lotus_farm.purchase_proposal.detail',{name:P1});line=d.items[0].name
  const quote=async(supplier,rate,key)=>{
   const r=await api(buyer,PR+'save_quotation',{company,client_key:'uat-q-'+key+'-'+Date.now(),data:{supplier,warehouse:state.warehouse,expected_date:L.days(5),valid_till:L.days(20),
    items:[{item:state.item,qty:100,rate,uom:state.uom,kind:'Material',vat_code:'5',material_request:P1,material_request_item:line}]}})
   await api(buyer,PR+'confirm_quotation',{name:r.name,modified:r.modified})
   const q=await api(buyer,PR+'quotation',{name:r.name});return {name:q.name,line:q.items[0].name}
  }
  QA=await quote(state.supplierA,120000,'a');QB=await quote(state.supplierB,110000,'b')
  Object.assign(state,{P1line:line,QA,QB});save()
  return QA.name+' · '+QB.name
 })
 await step('Chọn NCC A (không rẻ nhất) bắt buộc lý do; lựa chọn lưu trên dòng đề xuất',async()=>{
  let refused=''
  try{await api(buyer,PR+'choose_quote',{company,request:P1,request_item:line,quotation:QA.name,quotation_item:QA.line})}catch(e){refused=e.message}
  expect(/lý do/i.test(refused),'chọn giá cao không hỏi lý do: '+refused)
  await api(buyer,PR+'choose_quote',{company,request:P1,request_item:line,quotation:QA.name,quotation_item:QA.line,reason:'NCC A giao ngay trong ngày'})
  return refused.replace(/^.*?: /,'')
 })
 // ---- Điện thoại: lập đơn từ đề xuất, đơn có sẵn NCC A và 120.000 đ
 const phone=await L.login('buyer',{width:390,height:844,phone:true})
 let page=await goto(phone,'/buying','us3-01-app-mua-hang')
 await step('Trên điện thoại: Đề xuất mua chờ đặt hàng → Lập đơn mua từ đề xuất: có sẵn NCC A và giá 120.000 đ',async()=>{
  await page.getByText('Đề xuất mua chờ đặt hàng',{exact:true}).click();await settle(page,2000)
  const card=page.locator('.buy-card',{hasText:P1})
  await card.waitFor({timeout:15000})
  await shot(page,'us3-02-de-xuat-cho-dat-hang')
  await card.getByRole('button',{name:'Lập đơn mua từ đề xuất này'}).click();await settle(page,2500)
  await shot(page,'us3-03-don-tu-de-xuat')
  // selects and inputs keep their values out of innerText: read what the fields show
  const form=(await page.evaluate(()=>[...document.querySelectorAll('select')].map(s=>s.selectedOptions[0]?.textContent||'').concat([...document.querySelectorAll('input')].map(i=>i.value)).join(' · ')+' · '+document.body.innerText)).replace(/\s+/g,' ')
  const supplierName=(await api(admin,'frappe.client.get_value',{doctype:'Supplier',filters:{name:state.supplierA},fieldname:'supplier_name'})).supplier_name
  expect(form.includes(supplierName),'form không có NCC A ('+supplierName+')')
  expect(/120[.,]?000/.test(form),'form không có giá 120.000')
  await page.getByRole('button',{name:'Lưu đơn nháp',exact:true}).click();await settle(page,3000)
  await shot(page,'us3-04-da-luu-don-nhap')
  const rows=py(`print(json.dumps(frappe.db.sql("""select po.name, po.supplier, poi.rate, poi.supplier_quotation from \`tabPurchase Order\` po join \`tabPurchase Order Item\` poi on poi.parent=po.name where poi.material_request=%s and po.docstatus=0 order by po.creation desc limit 1""", '${P1}', as_dict=True), default=str))`)
  const po=JSON.parse(rows.trim().split('\n').pop())[0];expect(po,'không có đơn nháp từ '+P1)
  expect(po.supplier===state.supplierA&&Number(po.rate)===120000&&po.supplier_quotation===QA.name,'đơn lưu sai: '+JSON.stringify(po))
  state.order=po.name;save();return po.name+' · '+po.supplier+' · '+po.rate
 },page)
 await step('Thêm một dòng ngoài đề xuất rồi lưu: máy tính hiện cảnh báo ngay, chưa gửi duyệt được',async()=>{
  const d=await api(buyer,PU+'detail',{name:state.order})
  const lines=d.items.map(r=>({item:r.item,qty:r.qty,rate:r.rate,uom:r.uom,warehouse:r.warehouse,kind:r.kind,vat_code:r.vat_code,freight:r.freight,
   supplier_quotation:r.supplier_quotation,supplier_quotation_item:r.supplier_quotation_item,material_request:r.material_request,material_request_item:r.material_request_item}))
  const saved=await api(buyer,WB+'save_order',{company,name:state.order,modified:d.modified,data:{supplier:d.supplier,warehouse:state.warehouse,expected_date:L.days(5),mode:d.mode,
   items:[...lines,{item:state.item,qty:5,rate:120000,uom:state.uom,warehouse:state.warehouse,kind:'Material',vat_code:'5'}]}})
  expect(saved.warnings?.length,'lưu đơn không trả cảnh báo')
  const p=await openOrderDesktop(buyer,state.order,'us3-05-canh-bao-dong-ngoai-de-xuat')
  const alert=await p.locator('[role=alert][aria-label="Dòng sẽ bị chặn khi duyệt"]').innerText()
  expect(/không lấy từ đề xuất mua đã duyệt/.test(alert),'không thấy cảnh báo: '+alert)
  expect(await p.getByRole('button',{name:'Gửi duyệt đơn',exact:true}).isDisabled(),'nút gửi duyệt vẫn bật')
  const again=await api(buyer,PU+'detail',{name:state.order})
  await api(buyer,WB+'save_order',{company,name:state.order,modified:again.modified,data:{supplier:d.supplier,warehouse:state.warehouse,expected_date:L.days(5),mode:d.mode,items:lines}})
  return alert.replace(/\s+/g,' ').slice(0,160)
 })
 await step('Gửi duyệt cho giám đốc; giám đốc trả lại trên máy tính, có lý do',async()=>{
  const d=await api(buyer,PU+'detail',{name:state.order})
  await api(buyer,PU+'request_approval',{name:state.order,modified:d.modified,approver:email('director')})
  const p=await openOrderDesktop(director,state.order)
  await p.getByRole('button',{name:'Trả lại',exact:true}).click();await settle(p,600)
  const back=p.getByRole('button',{name:'Trả lại đơn',exact:true})
  expect(await back.isDisabled(),'trả lại không cần lý do')
  await p.locator('textarea').first().fill('Giá NCC A cao hơn NCC B, ghi rõ lý do giao gấp trong đơn')
  await shot(p,'us3-06-giam-doc-tra-lai')
  await back.click();await settle(p,3000)
  const s=await api(buyer,PU+'detail',{name:state.order})
  expect(s.status==='Bị trả lại'&&/giao gấp/.test(s.reject_reason),'sau trả lại: '+s.status+' · '+s.reject_reason)
  await shot(p,'us3-07-don-bi-tra-lai-may-tinh')
 })
 await step('Người lập thấy lý do trả lại trên điện thoại',async()=>{
  const p=await goto(phone,'/buying')
  await p.getByRole('tab',{name:'Đơn mua'}).or(p.getByText('Đơn mua',{exact:true})).first().click();await settle(p,2000)
  await p.getByRole('button',{name:'Mở đơn '+state.order}).first().click();await settle(p,2500)
  await shot(p,'us3-08-ly-do-tra-lai-dien-thoai')
  const text=(await p.locator('body').innerText()).replace(/\s+/g,' ')
  expect(/giao gấp/.test(text),'điện thoại không hiện lý do trả lại')
 })
 await step('Sửa và gửi lại; giám đốc duyệt trên điện thoại từ Chờ tôi ký; đơn duyệt có PDF lưu và In đơn mua mở bản đó',async()=>{
  const d=await api(buyer,PU+'detail',{name:state.order})
  await api(buyer,PU+'request_approval',{name:state.order,modified:d.modified,approver:email('director')})
  const dp=await L.login('director',{width:390,height:844,phone:true})
  const p=await goto(dp,'/buying')
  await p.getByRole('button',{name:/^Chờ tôi ký/}).first().click();await settle(p)
  const panel=p.locator('section[aria-label="Chờ tôi ký"]')
  await panel.locator('.van-cell',{hasText:state.order}).locator('.van-cell__title').first().click()
  const sheet=p.locator('section[aria-label="Ký '+state.order+'"]');await sheet.waitFor({timeout:15000});await settle(p,2500)
  await shot(p,'us3-09-giam-doc-duyet-dien-thoai')
  await sheet.getByRole('button',{name:/^Ký: /}).click()
  const dialog=p.locator('[role=dialog]').filter({hasText:'Ký chứng từ'}).last();await dialog.waitFor({timeout:10000})
  await dialog.getByRole('button',{name:'Ký',exact:true}).click();await settle(p,5000)
  const s=await api(buyer,PU+'detail',{name:state.order})
  expect(s.docstatus===1&&s.status==='Đã duyệt'&&s.signed_copy?.pdf_sha256,'sau duyệt: '+s.status+' · '+JSON.stringify(s.signed_copy))
  const r=await buyer.request.get(L.base+s.print_url)
  const type=r.headers()['content-type']||''
  expect(type.startsWith('application/pdf'),'In đơn mua của đơn đã duyệt không mở bản PDF đã ký: '+type)
  return 'In đơn mua → '+type.split(';')[0]
 })
 await step('Tạo đơn từ so sánh giá (giá rẻ nhất): đơn chờ người duyệt, không tự duyệt',async()=>{
  const d=await api(buyer,'lotus_farm.purchase_proposal.detail',{name:P2})
  const r=await api(buyer,PR+'save_quotation',{company,client_key:'uat-q2-'+Date.now(),data:{supplier:state.supplierB,warehouse:state.warehouse,expected_date:L.days(5),valid_till:L.days(20),
   items:[{item:state.item,qty:100,rate:110000,uom:state.uom,kind:'Material',vat_code:'5',material_request:P2,material_request_item:d.items[0].name}]}})
  const q=await api(buyer,PR+'quotation',{name:r.name})
  const made=await api(buyer,PR+'select_quotes',{company,client_key:'uat-sel-'+Date.now(),approver:email('director'),selections:[{quotation:q.name,line:q.items[0].name,modified:q.modified,qty:100}]})
  state.order2=made.orders[0];save()
  const s=await api(buyer,PU+'detail',{name:state.order2})
  expect(s.docstatus===0&&s.status==='Chờ duyệt','đơn từ so sánh giá: '+s.status)
  return state.order2+' · '+s.status
 })
 await step('Duyệt qua REST bằng tài khoản có vai trò duyệt nhưng không được chỉ định: bị chặn',async()=>{
  const deputy=await L.login('director2')
  const doc=await api(admin,'frappe.client.get',{doctype:'Purchase Order',name:state.order2})
  let refused=''
  try{await api(deputy,'frappe.client.submit',{doc})}catch(e){refused=e.message}
  expect(refused,'REST submit không bị chặn')
  const ds=(await api(admin,'frappe.client.get_value',{doctype:'Purchase Order',filters:{name:state.order2},fieldname:'docstatus'})).docstatus
  expect(ds===0,'đơn đã bị ghi sổ: '+ds)
  return refused.replace(/^.*?: /,'').slice(0,160)
 })
 await step('Máy tính: Đã gửi NCC rồi NCC đã xác nhận; danh sách hiện đúng trạng thái',async()=>{
  const p=await openOrderDesktop(buyer,state.order)
  await p.getByRole('button',{name:'Đã gửi NCC',exact:true}).click();await settle(p,2500)
  await p.getByRole('button',{name:'NCC đã xác nhận',exact:true}).click();await settle(p,2500)
  await shot(p,'us3-10-ncc-da-xac-nhan')
  const list=await goto(buyer,'/lotus/mua-hang?buying_view=orders','us3-11-danh-sach-don-trang-thai')
  const row=await list.getByRole('row').filter({hasText:state.order}).first().innerText()
  expect(/NCC đã xác nhận/.test(row),'danh sách: '+row.replace(/\s+/g,' '))
  return row.replace(/\s+/g,' ').slice(0,200)
 })
 await step('Giám đốc duyệt đơn thứ hai rồi hủy khi chưa nhận hàng, có lý do: dòng đề xuất về Chờ mua',async()=>{
  let d=await api(director,PU+'detail',{name:state.order2})
  await api(director,PU+'approve_order',{name:state.order2,modified:d.modified})
  const p=await openOrderDesktop(director,state.order2)
  await p.getByRole('button',{name:'Hủy đơn',exact:true}).click();await settle(p,600)
  await p.locator('textarea').first().fill('NCC B báo hết hàng')
  await p.getByRole('button',{name:'Hủy đơn mua',exact:true}).click();await p.waitForTimeout(1500)
  await shot(p,'us3-12a-hoi-xac-nhan-huy')
  await confirmDesktop(p)
  await shot(p,'us3-12-huy-don-co-ly-do')
  d=await api(director,PU+'detail',{name:state.order2})
  const stage=(await api(admin,'lotus_farm.purchase_proposal.detail',{name:P2})).stage
  expect(d.status==='Đã hủy'&&stage==='Chờ mua','sau hủy: đơn '+d.status+', đề xuất '+stage)
  return d.cancel_reason
 })
 await L.browser.close()
 process.exit(L.finish('uat-3')?1:0)
})().catch(e=>{console.error(e);process.exit(2)})
