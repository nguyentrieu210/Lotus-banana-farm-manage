// Walk-through US5 (hóa đơn NCC) and US6 (công nợ, trả tiền) on the live-site copy: quickstart.md §3.
// Needs the receipts of uat-4: receipt1 (60 kg, 5 returned, PDF invoice photo attached) and receipt2 (40 kg), supplier A.
const L=require('./uat-lib.cjs')
const {file}=require('./uat-files.cjs')
const {step,expect,api,py,goto,shot,settle,state,save}=L
const SI='lotus_farm.finance.supplier_invoice.',SP='lotus_farm.finance.supplier_payment.',Q='lotus_farm.procurement_queries.'
const bodyText=async page=>(await page.locator('body').innerText()).replace(/\s+/g,' ')
const field=(scope,text)=>scope.getByLabel(text,{exact:false}).first()
async function confirmDesktop(page){const d=page.getByRole('dialog').filter({has:page.getByRole('button',{name:/^(Đồng ý|Xác nhận|Ký)$/})}).last();await d.waitFor({timeout:10000});await d.getByRole('button',{name:/^(Đồng ý|Xác nhận|Ký)$/}).last().click()}
const one=out=>JSON.parse(out.trim().split('\n').pop())
// One supplier invoice number per run: NCC + ký hiệu + số is unique, and an earlier run already used the last one.
const BILL='45'+String(Date.now()).slice(-6)
const gl=(account,vouchers)=>Number(py(`print(frappe.db.sql("select coalesce(sum(debit-credit),0) from \`tabGL Entry\` where account=%s and voucher_no in %s and is_cancelled=0", ('${account}', tuple(${JSON.stringify(vouchers)}+[''])))[0][0])`).trim().split('\n').pop())
;(async()=>{
 await L.start()
 const admin=await L.login('admin'),acc=await L.login('accountant'),keeper=await L.login('keeper')
 const company=state.company
 const accounts=one(py(`from lotus_farm.finance import setup
m=setup.mapping()
print(json.dumps(dict(vat=m['input_vat'],grni=m['received_not_billed'],valuation=setup.valuation_tax_account('${company}'),household=bool(setup.vat_in_cost()),payable=m['payable_supplier'])))`))
 await step('Một phiếu Mua nhanh cùng nhà cung cấp chờ hóa đơn',async()=>{
  const r=await api(keeper,'lotus_farm.warehouse.create_draft',{company,kind:'receipt',posting_date:L.days(0),lines:[{item:state.item,qty:10,rate:118000}],target:state.warehouse,
   receipt_reason:'Purchase',supplier:state.supplierA,post:1,client_event_id:'uat-quick-'+Date.now()})
  expect(r.docstatus===1,'phiếu Mua nhanh chưa ghi sổ')
  state.quick=r.name;save();return r.name+' · hộ kinh doanh: '+accounts.household
 })
 const page=await goto(acc,'/lotus/mua-hang?buying_view=invoice-queue','us5-01-hoa-don-cho-nhap')
 await step('Hóa đơn chờ nhập có 2 phiếu nhận theo đơn (một phiếu có file PDF hóa đơn) và 1 phiếu Mua nhanh',async()=>{
  const text=await bodyText(page)
  for(const n of [state.receipt1,state.receipt2,state.quick])expect(text.includes(n),'thiếu '+n)
  const row=page.locator('li',{hasText:state.receipt1}).first()
  expect(/hoa-don-ncc\.pdf/.test(await row.innerText()),'phiếu nhận không hiện file hóa đơn đã đính')
  expect(/Mua nhanh/.test(await page.locator('li',{hasText:state.quick}).first().innerText()),'phiếu Mua nhanh không mang nhãn Mua nhanh')
 },page)
 let invoice
 await step('Nhập hóa đơn cho 2 phiếu nhận: file gốc hiện cạnh biểu mẫu; đơn giá 125.000 (đơn mua 120.000) phải có lý do; thuế 5% và 8%; khớp tổng in',async()=>{
  await page.getByRole('checkbox',{name:'Chọn '+state.receipt1}).click()
  await page.getByRole('checkbox',{name:'Chọn '+state.receipt2}).click()
  await page.getByRole('button',{name:/^Nhập hóa đơn cho 2 phiếu đã chọn$/}).click();await settle(page,3000)
  const form=page.locator('dialog[open]').filter({hasText:'Nhập hóa đơn'}).last()
  expect(await form.locator('aside iframe, aside img').count(),'không có file gốc cạnh biểu mẫu')
  await field(form,'Ký hiệu hóa đơn').fill('1C26TAB')
  await field(form,'Số hóa đơn').fill(BILL)
  const lines=form.locator('.invoice-form__line')
  // line 1: price differs from the order
  await lines.nth(0).getByLabel('Đơn giá theo hóa đơn').fill('125000');await settle(page,500)
  const submit=form.getByRole('button',{name:'Ghi hóa đơn',exact:true})
  expect(await submit.isDisabled(),'lệch giá mà không cần lý do')
  await lines.nth(0).getByLabel(/^Lý do đơn giá khác phiếu nhận/).fill('NCC tăng giá theo thông báo ngày 09/11')
  // line 2: another VAT rate printed on the invoice
  const vat=lines.nth(1).getByLabel('Thuế GTGT')
  if(await vat.evaluate(e=>e.tagName)==='SELECT')await vat.selectOption({label:'8%'});else{await vat.click();await page.getByRole('option',{name:'8%',exact:true}).click()}
  await settle(page,500)
  const total=Number((await form.locator('dl.lotus-form-totals div',{hasText:'Tổng các dòng'}).locator('dd').innerText()).replace(/[^\d]/g,''))
  const tax=Number((await form.locator('dl.lotus-form-totals div',{hasText:'Thuế GTGT'}).locator('dd').innerText()).replace(/[^\d]/g,''))
  await field(form,'Tiền thuế in trên hóa đơn').fill(String(tax))
  await field(form,'Tổng thanh toán in trên hóa đơn').fill(String(total+1));await settle(page,500)
  await shot(page,'us5-02-nhap-hoa-don-file-ben-canh')
  await submit.click();await settle(page,5000)
  await shot(page,'us5-03-hoa-don-da-ghi')
  const made=one(py(`print(json.dumps(frappe.get_all('Purchase Invoice',filters={'bill_no':'${BILL}','supplier':'${state.supplierA}','docstatus':1},fields=['name','grand_total','lotus_invoice_total'])))`))
  expect(made.length===1&&Number(made[0].grand_total)===total+1,'hóa đơn: '+JSON.stringify(made)+' (tổng in '+(total+1)+')')
  invoice=made[0].name;state.invoice=invoice;save()
  return invoice+' · tổng '+(total+1)+' (lệch làm tròn 1 đ ghi theo tổng in)'
 },page)
 await step('Hộ kinh doanh: không có bút toán 1331; 33881 và 3388 về 0 sau khi ERPNext định giá lại theo giá hóa đơn',async()=>{
  // The cost adjustments post on the receipts; the VAT part moves 3388 -> 33881 in a journal entry of the invoice.
  const vouchers=[state.receipt1,state.receipt2,invoice,...one(py(`print(json.dumps(frappe.get_all('Purchase Receipt',filters={'return_against':['in',['${state.receipt1}','${state.receipt2}']],'docstatus':1},pluck='name')+frappe.get_all('Journal Entry',filters={'lotus_purchase_invoice':'${invoice}','docstatus':1},pluck='name')))`))]
  expect(gl(accounts.vat,[invoice])===0,'có bút toán 1331 trên hóa đơn')
  py(`from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import repost_entries
repost_entries()`)
  const valuation=gl(accounts.valuation,vouchers),grni=gl(accounts.grni,vouchers)
  expect(Math.abs(grni)<=2,'3388 còn '+grni)
  expect(Math.abs(valuation)<=2,'33881 (thuế tính vào giá vốn) còn '+valuation+' sau hóa đơn khác giá và khác thuế suất')
  return '33881 '+valuation+' · 3388 '+grni
 })
 await step('Nhập lại cùng NCC + ký hiệu + số ở màn Tài chính: bị chặn trùng',async()=>{
  const p=await goto(acc,'/lotus/tai-chinh?tab=pending','us5-04-tai-chinh-cho-hach-toan')
  await p.getByRole('checkbox',{name:'Chọn '+state.quick}).first().click();await settle(p,600)
  await p.getByRole('button',{name:/^Lập hóa đơn \(1\)$/}).click();await settle(p,2500)
  const form=p.locator('dialog[open]').filter({hasText:'Nhập hóa đơn'}).last()
  await field(form,'Ký hiệu hóa đơn').fill('1C26TAB')
  await field(form,'Số hóa đơn').fill(BILL)
  await form.getByRole('button',{name:'Ghi hóa đơn',exact:true}).click();await settle(p,3000)
  await shot(p,'us5-05-chan-trung-so-hoa-don')
  const text=await bodyText(p)
  expect(/đã được nhập/.test(text),'không báo trùng: '+text.slice(0,200))
  return (text.match(/Hóa đơn [^.]*đã được nhập[^.)]*\)?/)||[''])[0]
 })
 await step('Hủy hóa đơn đã có phiếu chi: bị chặn, có hướng dẫn',async()=>{
  const v=await api(acc,SP+'prepare',{supplier:state.supplierA,allocations:[{doctype:'Purchase Invoice',name:invoice,amount:1000000}],mode:'cash',posting_date:L.days(0),
   signers:{CHIEF:L.cfg.users.chief[0],APPROVE:L.cfg.users.director[0]},client_key:'uat-pay1-'+Date.now()})
  for(const who of ['chief','director'])await api(await L.login(who),'lotus_farm.finance.payments.sign_payment',{doctype:'Payment Entry',name:v.voucher})
  state.voucher1=v.voucher;save()
  const p=await goto(acc,'/lotus/mua-hang?buying_view=invoices')
  await p.getByRole('gridcell',{name:invoice,exact:true}).first().click();await settle(p,2500)
  await shot(p,'us5-06-hoa-don-da-co-phieu-chi')
  expect(!await p.getByRole('button',{name:'Hủy hóa đơn',exact:true}).count(),'vẫn cho hủy hóa đơn đã trả')
  const text=await bodyText(p)
  expect(/[Đđ]ảo phiếu chi trước/.test(text),'không có hướng dẫn')
  let refused='';try{await api(acc,SI+'cancel',{name:invoice,reason:'Thử hủy'})}catch(e){refused=e.message}
  expect(/Đảo phiếu chi trước/.test(refused),'máy chủ không chặn: '+refused)
  return v.voucher
 })
 await step('Hủy hóa đơn chưa thanh toán có lý do: phiếu Mua nhanh quay về chờ hóa đơn và lập lại được',async()=>{
  const made=await api(acc,SI+'create',{receipts:[state.quick],bill_no:'MN-'+Date.now().toString().slice(-6),bill_date:L.days(0),client_key:'uat-mn-'+Date.now()})
  const p=await goto(acc,'/lotus/mua-hang?buying_view=invoices')
  await p.getByRole('gridcell',{name:made.invoice,exact:true}).first().click();await settle(p,2500)
  await p.getByRole('button',{name:'Hủy hóa đơn',exact:true}).last().click();await settle(p,600)
  const confirm=p.getByRole('button',{name:'Hủy hóa đơn',exact:true}).first()
  expect(await confirm.isDisabled(),'hủy không cần lý do')
  await p.getByLabel('Lý do hủy hóa đơn').fill('Nhập nhầm số hóa đơn')
  await confirm.click();await confirmDesktop(p);await settle(p,3000)
  await shot(p,'us5-07-huy-hoa-don-chua-tra')
  const left=one(py(`print(json.dumps([frappe.db.get_value('Purchase Invoice','${made.invoice}','docstatus'), frappe.db.get_value('Stock Entry','${state.quick}','lotus_purchase_invoice')]))`))
  expect(left[0]===2&&!left[1],'sau hủy: '+JSON.stringify(left))
  const again=await api(acc,SI+'create',{receipts:[state.quick],bill_no:'MN2-'+Date.now().toString().slice(-6),bill_date:L.days(0),client_key:'uat-mn2-'+Date.now()})
  return 'lập lại '+again.invoice
 })
 // ---------------- US6 ----------------
 await step('Công nợ ngày chốt hôm nay trên máy tính và điện thoại: tuổi nợ, hàng chưa có hóa đơn tách riêng, đối chiếu sổ cái',async()=>{
  const p=await goto(acc,'/lotus/mua-hang?buying_view=payables','us6-01-cong-no-may-tinh')
  const text=await bodyText(p)
  for(const want of ['Phải trả','Đến hạn trong 7 ngày','Hàng đã nhận, chưa có hóa đơn','Tuổi nợ theo hạn trả'])expect(text.includes(want),'thiếu '+want)
  expect(/khớp sổ cái tài khoản phải trả/.test(text),'không khớp sổ cái 331: '+(text.match(/Số tại ngày[^.]*\./)||[''])[0])
  const phone=await L.login('accountant',{width:390,height:844,phone:true})
  const m=await goto(phone,'/buying')
  await m.getByText('Báo giá, nghiệm thu & thanh toán',{exact:true}).click();await settle(m,2000)
  return (text.match(/Số tại ngày[^.]*\./)||[''])[0]
 },page)
 await step('Chọn 2 hóa đơn, lập phiếu chi chuyển khoản có số tham chiếu và ảnh ủy nhiệm chi, ký đủ 3 bước; in giấy đề nghị chi có chữ ký và QR',async()=>{
  const second=await api(acc,SI+'create',{receipts:[],service_lines:[{description:'Bốc xếp UAT',amount:300000,cost:'admin',vat_code:'KCT'}],supplier:state.supplierA,
   bill_no:'DV-'+Date.now().toString().slice(-6),bill_date:L.days(0),client_key:'uat-dv-'+Date.now()})
  state.invoice2=second.invoice;save()
  const p=await goto(acc,'/lotus/mua-hang?buying_view=payables')
  const row=p.locator('.payables-view__list li',{hasText:(await api(admin,'frappe.client.get_value',{doctype:'Supplier',filters:{name:state.supplierA},fieldname:'supplier_name'})).supplier_name}).first()
  await row.getByRole('button',{name:'Trả tiền',exact:true}).click();await settle(p,2500)
  const form=p.locator('dialog[open]').filter({hasText:'Phiếu chi'}).last()
  const payable=async label=>form.locator('.payment-form__item',{hasText:label}).first()
  const inv1=await payable(invoice),inv2=await payable(state.invoice2)
  await inv1.getByRole('textbox').fill('500000');await inv2.getByRole('textbox').fill('300000')
  await field(form,'Số ủy nhiệm chi').fill('UNC-UAT-777')
  await form.locator('input[type=file][aria-label="Đính kèm chứng từ chi"]').setInputFiles(file('uy-nhiem-chi.png'))
  await shot(p,'us6-02-lap-phieu-chi')
  await form.getByRole('button',{name:'Lập phiếu và trình ký',exact:true}).click();await settle(p,4000)
  const v=one(py(`print(json.dumps(frappe.get_all('Payment Entry',filters={'reference_no':'UNC-UAT-777'},fields=['name','paid_amount','docstatus'],order_by='creation desc',limit=1)))`))[0]
  expect(v&&Number(v.paid_amount)===800000,'phiếu chi: '+JSON.stringify(v))
  for(const who of ['chief','director']){
   const ctx=await L.login(who),sp=await goto(ctx,'/lotus/cho-ky')
   await sp.getByRole('gridcell',{name:v.name,exact:true}).first().click();await settle(sp,2500)
   await sp.getByRole('button',{name:/^Ký: /}).first().click()
   const d=sp.getByRole('dialog').filter({hasText:'Ký chứng từ'}).last();await d.waitFor({timeout:10000})
   await d.getByRole('button',{name:'Ký',exact:true}).click();await settle(sp,4000)
  }
  const after=one(py(`print(json.dumps([frappe.db.get_value('Payment Entry','${v.name}','docstatus'), frappe.db.get_value('Purchase Invoice','${state.invoice2}','outstanding_amount')]))`))
  expect(after[0]===1&&Number(after[1])===0,'sau ký: '+JSON.stringify(after))
  const pr=await goto(acc,'/lotus/in-phieu-chi?doctype=Payment%20Entry&name='+encodeURIComponent(v.name),'us6-03-giay-de-nghi-chi')
  const text=await bodyText(pr)
  for(const want of ['UNC-UAT-777','Kế toán trưởng'])expect(text.includes(want),'bản in thiếu '+want)
  state.voucher2=v.name;save()
  return v.name+' · hóa đơn dịch vụ đã trả đủ'
 })
 await step('Biên bản đối chiếu từ 01/10 đến hôm nay: đầu kỳ, phát sinh, cuối kỳ khớp sổ chi tiết',async()=>{
  const s=await api(acc,Q+'supplier_statement',{company,supplier:state.supplierA,from_date:'2026-10-01',to_date:L.days(0)})
  expect(s.ledger_matches,'sổ chi tiết lệch sổ cái')
  const p=await goto(acc,'/lotus/in-doi-chieu?supplier='+encodeURIComponent(state.supplierA)+'&from_date=2026-10-01&to_date='+L.days(0),'us6-04-bien-ban-doi-chieu')
  const text=await bodyText(p)
  expect(text.includes('BIÊN BẢN ĐỐI CHIẾU CÔNG NỢ')&&text.includes(new Intl.NumberFormat('vi-VN').format(Math.round(s.closing))),'biên bản không có số cuối kỳ '+s.closing)
  return 'đầu kỳ '+s.opening+' · cuối kỳ '+s.closing
 })
 await step('Bấm phiếu chi trong phần tiến độ của đề xuất: mở đúng phiếu chi',async()=>{
  const prog=await api(acc,'lotus_farm.purchase_proposal.detail',{name:state.proposals[0]})
  const pays=(prog.progress?.payments||[]).map(r=>r.name)
  expect(pays.includes(state.voucher1)||pays.includes(state.voucher2),'tiến độ đề xuất không có phiếu chi: '+JSON.stringify(pays))
  const p=await goto(acc,'/lotus/mua-hang?buying_view=needs')
  await p.getByRole('gridcell',{name:state.proposals[0],exact:true}).first().click();await settle(p,3000)
  const link=p.getByRole('link',{name:new RegExp(pays[0])}).or(p.getByRole('button',{name:new RegExp(pays[0])})).first()
  await link.click();await settle(p,3000)
  await shot(p,'us6-05-mo-phieu-chi-tu-tien-do')
  const text=await bodyText(p)
  expect(/Phiếu chi/.test(text)&&text.includes(pays[0]),'không mở phiếu chi '+pays[0])
  return pays[0]
 })
 await L.browser.close()
 process.exit(L.finish('uat-5')?1:0)
})().catch(e=>{console.error(e);process.exit(2)})
