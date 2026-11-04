import test from 'node:test'
import assert from 'node:assert/strict'
import {evaluate,layout,visible,required,readonly,control,selectOptions,display,childColumns,docstatusLabel} from '../src/erp-meta.js'

test('depends_on: eval expressions, plain fieldnames, helpers, and failures stay visible',()=>{
 assert.equal(evaluate('eval:doc.is_return==1',{is_return:1}),true)
 assert.equal(evaluate('eval:doc.is_return==1',{is_return:0}),false)
 assert.equal(evaluate('eval:in_list(["Purchase","Transfer"], doc.purpose)',{purpose:'Transfer'}),true)
 assert.equal(evaluate('eval:cint(doc.qty) > 2',{qty:'3'}),true)
 assert.equal(evaluate('eval:parent.docstatus==0',{},{docstatus:0}),true)
 assert.equal(evaluate('update_stock',{update_stock:1}),true)
 assert.equal(evaluate('update_stock',{}),false)
 assert.equal(evaluate('eval:cur_frm.doc.x',{}),true,'a script Lotus cannot run never hides a field')
 assert.equal(evaluate('',{}),true)
})

test('layout groups fields into tabs, sections and columns like Desk and drops empty parts and Desk-only widgets',()=>{
 const tabs=layout([
  {fieldname:'customer',fieldtype:'Link'},{fieldname:'cb',fieldtype:'Column Break'},{fieldname:'posting_date',fieldtype:'Date'},
  {fieldname:'sec',fieldtype:'Section Break',label:'Hàng hóa',collapsible:1},{fieldname:'items',fieldtype:'Table'},{fieldname:'btn',fieldtype:'Button'},
  {fieldname:'tab',fieldtype:'Tab Break',label:'Khác'},{fieldname:'html',fieldtype:'HTML'},
  {fieldname:'tab2',fieldtype:'Tab Break',label:'Ghi chú'},{fieldname:'remarks',fieldtype:'Small Text'}
 ])
 assert.deepEqual(tabs.map(t=>t.label),['Thông tin','Ghi chú'])
 assert.deepEqual(tabs[0].sections[0].columns.map(c=>c.map(f=>f.fieldname)),[['customer'],['posting_date']])
 assert.equal(tabs[0].sections[1].label,'Hàng hóa');assert.equal(tabs[0].sections[1].collapsible,true)
 assert.deepEqual(tabs[0].sections[1].columns.map(c=>c.map(f=>f.fieldname)),[['items']])
})

test('visibility, mandatory and read-only follow the field flags, submit lock and allow_on_submit',()=>{
 const f={fieldname:'x',depends_on:'eval:doc.a',mandatory_depends_on:'eval:doc.b'}
 assert.equal(visible(f,{a:1}),true);assert.equal(visible({...f,hidden:1},{a:1}),false)
 assert.equal(required(f,{b:0}),false);assert.equal(required(f,{b:1}),true);assert.equal(required({reqd:1},{}),true)
 assert.equal(readonly({},{},{locked:true}),true);assert.equal(readonly({allow_on_submit:1},{},{locked:true}),false)
 assert.equal(readonly({read_only_depends_on:'eval:doc.docstatus==0'},{docstatus:0}),true)
 assert.equal(readonly({fieldtype:'Read Only'},{}),true)
})

test('controls map ERPNext field types to the shared fields',()=>{
 assert.deepEqual(['Check','Date','Currency','Float','Select','Link','Dynamic Link','Small Text','Attach','Table','Data','Datetime'].map(t=>control({fieldtype:t})),
  ['checkbox','date','money','number','select','link','link','textarea','attach','table','text','datetime'])
})

test('select options and values read in Vietnamese while keeping the stored value',()=>{
 const options=selectOptions({options:'\nDraft\nPaid\nOverdue\nPaid'})
 assert.deepEqual(options.map(o=>o.value),['Draft','Paid','Overdue'])
 assert.equal(options[0].label,'Bản nháp');assert.equal(options[2].label,'Quá hạn')
 assert.equal(display('Overdue',{fieldtype:'Select'}),'Quá hạn')
})

test('display formats dates, money, checks and numbers for lists and locked forms',()=>{
 assert.equal(display('2026-11-04',{fieldtype:'Date'}),'04/11/2026')
 assert.equal(display('2026-11-04 07:30:00',{fieldtype:'Datetime'}),'04/11/2026 07:30:00')
 assert.match(display(1250000,{fieldtype:'Currency'},'VND'),/1\.250\.000/)
 assert.equal(display(1,{fieldtype:'Check'}),'Có');assert.equal(display(null,{fieldtype:'Data'}),'—')
 assert.equal(docstatusLabel(1),'Đã ghi sổ')
})

test('child grid shows the Desk grid columns (in_list_view), else the first data fields',()=>{
 const fields=[{fieldname:'item_code',fieldtype:'Link',in_list_view:1},{fieldname:'description',fieldtype:'Text Editor'},{fieldname:'qty',fieldtype:'Float',in_list_view:1},{fieldname:'sb',fieldtype:'Section Break'},{fieldname:'secret',fieldtype:'Data',hidden:1}]
 assert.deepEqual(childColumns(fields).map(f=>f.fieldname),['item_code','qty'])
 assert.deepEqual(childColumns(fields.map(f=>({...f,in_list_view:0}))).map(f=>f.fieldname),['item_code','description','qty'])
})
