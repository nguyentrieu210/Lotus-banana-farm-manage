#!/usr/bin/env node
// Resolve the 13 conflicts of `git merge main` into the spec 003 branch, exactly as validated on the VPS test stack
// (specs/003-mua-hang-ky-dien-tu/merge-plan.md, 11/11/2026). Run from the repository root right after the merge stops:
//   git merge main
//   node tools/merge-003-main/resolve.cjs [--release-id=2026-11-12]
//   git rm lotus_farm/public/js/material_requirement.js   (the script does it when git is available)
// It refuses to touch a file whose conflict does not look like the one it was written for.
const fs = require('fs')
const {execSync} = require('child_process')

const arg = name => (process.argv.find(a => a.startsWith('--' + name + '=')) || '').split('=')[1]
// The 003 release note must sort above main's '2026-11-11' (already seen by users), so give it the ship day.
const today = new Date(Date.now() + 7 * 3600 * 1000).toISOString().slice(0, 10)
const releaseId = arg('release-id') || (today > '2026-11-11' ? today : '2026-11-11b')
if (!(releaseId > '2026-11-11')) throw new Error('release id must sort after 2026-11-11: ' + releaseId)
const releaseDay = releaseId.slice(8, 10) + '/' + releaseId.slice(5, 7) + '/' + releaseId.slice(0, 4)

function hunks(path, resolve) {
  let text = fs.readFileSync(path, 'utf8')
  const nl = text.includes('\r\n') ? '\r\n' : '\n'
  let count = 0
  for (;;) {
    const start = text.search(/^<<<<<<< [^\r\n]*\r?$/m)
    if (start < 0) break
    const startEnd = text.indexOf(nl, start) + nl.length
    const mid = text.indexOf(nl + '=======' + nl, start)
    const endMatch = /\r?\n>>>>>>> [^\r\n]*\r?\n/g
    endMatch.lastIndex = mid
    const end = endMatch.exec(text)
    if (mid < 0 || !end) throw new Error('malformed conflict in ' + path)
    const ours = text.slice(startEnd, mid), theirs = text.slice(mid + (nl + '=======' + nl).length, end.index)
    text = text.slice(0, start) + resolve(ours, theirs, count++, nl) + nl + text.slice(end.index + end[0].length)
  }
  if (!count) { console.log('no conflict left in', path); return }
  if (/^(<<<<<<<|=======|>>>>>>>)/m.test(text)) throw new Error('markers left in ' + path)
  fs.writeFileSync(path, text)
  console.log('resolved', path, count, 'hunk(s)')
}
const must = (text, from, to) => { if (!text.includes(from)) throw new Error('unexpected conflict text: ' + from.slice(0, 70)); return text.replace(from, to) }
const lines = (nl, ...rows) => rows.join(nl)

// hooks.py: main's removal of every legacy doc_event; 003's print/open routes and keep_proposal_prices.
hunks('lotus_farm/hooks.py', (ours, theirs, i, nl) => {
  must(ours, "{'from_route':'/lotus/in-don-mua'", '')
  must(theirs, "doc_events['Material Request']={'validate':['lotus_farm.purchase_flow.validate']", '')
  return lines(nl,
    "website_route_rules = [{'from_route':'/login','to_route':'lotus_login'},{'from_route':'/lotus/in-phieu','to_route':'lotus_stock_print'},{'from_route':'/lotus/in-cong','to_route':'lotus_timekeeping_print'},{'from_route':'/lotus/in-de-xuat','to_route':'lotus_material_proposal_print'},{'from_route':'/lotus/in-luong','to_route':'lotus_payroll_print'},{'from_route':'/lotus/in-phieu-ngay','to_route':'lotus_daily_form'},{'from_route':'/hr-mobile','to_route':'hr_mobile'},{'from_route':'/lotus/in-don-mua','to_route':'lotus_purchase_order_print'},{'from_route':'/lotus/in-hoa-don','to_route':'lotus_invoice_print'},{'from_route':'/lotus/in-phieu-chi','to_route':'lotus_payment_print'},{'from_route':'/lotus/in-doi-chieu','to_route':'lotus_statement_print'},{'from_route':'/lotus/mo','to_route':'lotus_open'},{'from_route':'/lotus/<path:app_path>','to_route':'lotus'}]",
    '',
    "doc_events['Material Request']={'validate':['lotus_farm.purchase_flow.validate'],'before_submit':['lotus_farm.purchase_flow.validate']}",
    "# Runs after ERPNext's own validate (which sets the default buying price list): a proposal keeps its typed prices.",
    "doc_events['Material Request']['validate'].append('lotus_farm.purchase_flow.keep_proposal_prices')")
})

// patches.txt: main's two (already run on the live site) first, then 003's two. Never reorder existing lines.
hunks('lotus_farm/patches.txt', (ours, theirs, i, nl) => {
  must(theirs, 'lotus_farm.patches.purge_legacy_doctypes', '')
  must(ours, 'lotus_farm.patches.drop_signing_challenge', '')
  return lines(nl, 'lotus_farm.patches.purge_legacy_doctypes', 'lotus_farm.patches.work_schedule_rule_unique_per_farm',
    'lotus_farm.patches.return_unsigned_pending_orders', 'lotus_farm.patches.drop_signing_challenge')
})

// payments.py: 003's wrapper of supplier_invoice.create, docstring without the removed "Vụ" dimension.
hunks('lotus_farm/finance/payments.py', (ours, theirs, i, nl) => {
  must(ours, 'from lotus_farm.finance import supplier_invoice', '')
  return lines(nl,
    "    \"\"\"lines: [{description, amount, cost: 'production' | 'admin', lotus_farm, lotus_farm_block, lotus_work_type}].",
    '    Lớp bọc của finance.supplier_invoice.create: hộ kinh doanh cộng thuế vào chính khoản chi phí, không ghi 1331."""',
    '    from lotus_farm.finance import supplier_invoice',
    '    result = supplier_invoice.create(supplier=supplier, service_lines=_json(lines), bill_no=bill_no, bill_date=bill_date, due_date=due_date,',
    '                                     posting_date=posting_date, vat_code=vat_code)',
    "    return dict(invoice=result['invoice'], amount=result['amount'])")
})

// warehouse_issue.py: main's code (no doctype parameter any more), 003's wording.
hunks('lotus_farm/warehouse_issue.py', (ours, theirs, i, nl) => {
  must(theirs, "if doc.material_request_type != 'Material Issue':", '')
  return lines(nl,
    "    if doc.material_request_type != 'Material Issue':",
    "        frappe.throw('Chỉ dùng yêu cầu cấp vật tư, không dùng đề xuất mua hoặc chuyển kho.')",
    "    if doc.get('status') in ('Stopped', 'Closed', 'Cancelled'):")
})

// Proposal print: main's single DocType; 003's reader access for signers (FR-027) and stored signed copy (FR-014).
hunks('lotus_farm/www/lotus_material_proposal_print.py', (ours, theirs, i, nl) => {
  if (i === 0) {
    must(ours, 'as_reader', '')
    return lines(nl,
      '    # People named in the signing round see what they sign even without rights on proposals (spec 003, FR-027).',
      '    from lotus_farm.signed_copy import as_reader',
      "    return as_reader(frappe.get_doc('Material Request', name), lambda: _build(name))",
      '', '',
      'def _build(name):',
      "    doc = frappe.get_doc('Material Request', name)",
      "    doc.check_permission('read')",
      "    doc.check_permission('print')",
      "    if doc.material_request_type not in ('Purchase', 'Material Issue'):",
      "        frappe.throw('Chỉ in phiếu đề xuất mua hoặc cấp vật tư.', frappe.PermissionError)",
      "    purchase = doc.material_request_type == 'Purchase'",
      "    when = getdate(doc.get('transaction_date') or doc.creation)",
      "    reason = strip_html(doc.get('lotus_request_note') or doc.get('remarks') or '').strip()",
      "    warehouse = ', '.join(sorted({r.warehouse for r in doc.items if r.warehouse}))",
      '    rows, total, priced = _request_rows(doc)',
      "    state = 'Đã duyệt' if doc.docstatus == 1 else (doc.get('lotus_proposal_state') or pk.status_label(doc.docstatus))")
  }
  must(ours, 'signed_copy.current(doc)', '')
  return lines(nl,
    'def download_pdf(name):',
    "    if frappe.db.exists('Material Request', name):",
    '        # Once signed in full, the download is the stored signed copy (spec 003, FR-014), not a new render.',
    '        from lotus_farm import signed_copy, signing',
    "        doc = frappe.get_doc('Material Request', name)",
    '        copy = signed_copy.current(doc)',
    '        if copy and signing.can_view(doc=doc):',
    "            return signed_copy.respond(copy, 'de-xuat-mua-' + name)",
    '    p = build(name)')
})

// Stock print: main's proposal hand-off (no doctype argument), 003's stored signed copy for stock documents.
hunks('lotus_farm/www/lotus_stock_print.py', (ours, theirs, i, nl) => {
  must(ours, "('Stock Entry', 'Stock Reconciliation', 'Purchase Receipt')", '')
  return lines(nl,
    '        return proposal_pdf(name)',
    "    if doctype in ('Stock Entry', 'Stock Reconciliation', 'Purchase Receipt') and frappe.db.exists(doctype, name):",
    '        from lotus_farm import signed_copy, signing',
    '        doc = frappe.get_doc(doctype, name)',
    '        copy = signed_copy.current(doc)',
    '        if copy and signing.can_view(doc=doc):',
    '            return signed_copy.respond(copy, name)')
})

// Frontend: main's text with 003's small additions.
hunks('frontend/src/App.vue', (ours, theirs) =>
  must(theirs, "['cong-viec','mua-hang','kho'].includes(page)", "['cong-viec','mua-hang','kho','cho-ky','tai-chinh'].includes(page)"))
hunks('frontend/src/api.js', ours =>
  must(must(ours, 'upload(file,doctype,name,expectedUser)', 'upload(file,doctype,name)'),
    "if(expectedUser){form.append('method','lotus_farm.field.save_uploaded_photo');form.append('expected_user',expectedUser)}", ''))
hunks('frontend/src/domain.js', (ours, theirs) =>
  must(must(theirs, "pages.push(['mua-hang','Mua hàng'])", "pages.push(['cho-ky','Chờ tôi ký'],['mua-hang','Mua hàng'])"),
    "items:[['reports','chart','Tổng quan']]}", "items:[['reports','chart','Tổng quan'],['cho-ky','edit','Chờ tôi ký']]}"))
hunks('frontend/src/labels.js', (ours, theirs) =>
  must(theirs, "'Lotus Signing Challenge':'Phiên QR ký chứng từ'", "'Lotus Signed Copy':'Bản PDF đã ký'"))
hunks('frontend/src/components/finance/FinanceGuide.vue', (ours, theirs, i, nl) => {
  const o = ours.split(nl), t = theirs.split(nl)
  if (i === 0) return lines(nl, t[0], must(o[1], 'Mua nhanh', 'Mua nhanh'))      // main's Thủ kho row, 003's Mua hàng row
  return lines(nl, must(t[0], 'Mua ngoài', 'Mua nhanh'), t[1])                   // main's rows, "Mua nhanh"
})
hunks('frontend/src/release-notes.js', (ours, theirs, i, nl) => {
  const head = ours.split(nl)[0]
  if (!/^ \{id:'2026-11-1\d[a-z]?',title:'Mua hàng và ký điện tử/.test(head)) throw new Error('unexpected 003 release note: ' + head)
  const top = " {id:'" + releaseId + "',title:'Mua hàng và ký điện tử (cập nhật " + releaseDay + ")',items:["
  return [top, ...ours.split(nl).slice(1)].join(nl) + nl + ' ]},' + nl + theirs
})

// Found by running the merged code on the VPS test stack (11/11/2026), outside the conflicts:
function edit(path, from, to) {
  const text = fs.readFileSync(path, 'utf8')
  if (text.includes(to)) { console.log('already edited', path); return }
  if (text.split(from).length !== 2) throw new Error('expected exactly one match in ' + path + ': ' + from.slice(0, 60))
  fs.writeFileSync(path, text.replace(from, to))
  console.log('edited', path)
}
// 1. App.vue (main's own code): on a fresh load the mount code read the page before the router had resolved the URL,
//    saw "/" and jumped to the first menu page, so every deep link (/lotus/kho, /lotus/cho-ky?sign_dt=…, links in
//    notifications and e-mails) opened the wrong screen. 003's removed `await refreshOutbox()` used to hide it.
edit('frontend/src/App.vue', 'onMounted(async()=>{await run(async()=>{await session.load();',
  'onMounted(async()=>{await router.isReady();await run(async()=>{await session.load();')
// 2. main's Kho test still expects the old label of the purchase reason (now "Mua nhanh", owner decision 10/11).
edit('tests/integration/verify_kho_e2e.py', "rec.reason == 'Mua ngoài'", "rec.reason == 'Mua nhanh'")
// 3. The warehouse audit submits an order directly: spec 003 has no approval by policy, the order must be pending.
edit('tests/integration/verify_warehouse_audit.py', 'frappe.conf.lotus_purchase_flow_company=None;order.submit()',
  "frappe.conf.lotus_purchase_flow_company=None;order.db_set('lotus_approval_status','Chờ duyệt',update_modified=False);order.submit()")

// Deleted in main, reworded in 003: the DocType it served is gone.
if (fs.existsSync('lotus_farm/public/js/material_requirement.js')) {
  try { execSync('git rm -q lotus_farm/public/js/material_requirement.js', {stdio: 'inherit'}); console.log('removed lotus_farm/public/js/material_requirement.js') }
  catch { console.log('remove lotus_farm/public/js/material_requirement.js with git rm') }
}
console.log('release note id', releaseId, '- next: git diff --check, the checks of merge-plan.md, then build the frontend on the VPS')
