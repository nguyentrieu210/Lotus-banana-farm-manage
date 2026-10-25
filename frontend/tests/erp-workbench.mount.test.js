import test from 'node:test'
import assert from 'node:assert/strict'
import {load,loadModule,mount,tick,document,window,h} from './support/mount.mjs'
import {provide,reactive} from 'vue'
import {routerKey,routeLocationKey} from 'vue-router'
const Workspace=await load('components/ErpnextWorkspace.vue')
const Editor=await load('components/erp/ErpDocumentEditor.vue')
const Form=await load('components/erp/ErpForm.vue')
const Field=await load('components/erp/ErpField.vue')
const Report=await load('components/erp/ErpReportView.vue')
const {erpDestination,erpLegacyQuery}=await loadModule('erp-locations.js')
const {erpFeatures,erpHref}=await loadModule('erpnext-navigation.js')
const rows=[{id:'s',module:'Buying',name:'Supplier',label:'Supplier',kind:'DocType',href:'/desk/supplier'},{id:'p',module:'Buying',name:'Purchase Order',label:'Purchase Order',kind:'DocType',href:'/desk/purchase-order'},{id:'r',module:'Accounts',name:'Consolidated Financial Statement',label:'Consolidated Financial Statement',kind:'Report'}]
const schema={doctype:'Supplier',title:'Supplier',fields:[{fieldname:'supplier_name',label:'Tên nhà cung cấp',fieldtype:'Data',reqd:1}],tables:{},permissions:{read:true,write:true,create:true}}
const response=message=>({ok:true,json:async()=>({message})})
test('Vietnamese ERP choices display labels while form models retain native enum values',async()=>{
 const values=[],view=mount(Field,{field:{fieldname:'status',label:'Status',fieldtype:'Select',options:'Active\nInactive'},modelValue:'Active','onUpdate:modelValue':value=>values.push(value)})
 try{
  await tick();const field=view.root.querySelector('input[role=combobox]')
  assert.equal(field.value,'Đang hoạt động');view.root.querySelector('.lotus-combobox__trigger').click();await tick()
  const option=[...document.querySelectorAll('[role=option]')].find(o=>o.textContent.includes('Không hoạt động'))
  assert.ok(option);option.dispatchEvent(new window.PointerEvent('pointerup',{bubbles:true}));option.click();await tick();assert.deepEqual(values,['Inactive'])
 }finally{view.unmount()}
})
const button=(root,text)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===text)
const input=(root,value)=>{const field=root.querySelector('input');field.value=value;field.dispatchEvent(new window.Event('input',{bubbles:true}))}
function server(calls=[]){globalThis.fetch=async(url,options={})=>{const method=String(url).split('/').pop().split('?')[0].split('.').pop(),args=options.body?JSON.parse(options.body):Object.fromEntries(new URL(url,'http://localhost').searchParams);calls.push({method,args});if(method==='catalog')return response({modules:[{value:'Buying'},{value:'Accounts'}],rows,companies:[{name:'C'}],warehouses:[]});if(method==='schema')return response(schema);if(method==='listing')return response({rows:[{name:'SUP-1',supplier_name:'Test'}],columns:[{fieldname:'name',label:'Mã'}],total_count:1});if(method==='document')return response({doc:{doctype:'Supplier',name:args.name||'new-supplier',supplier_name:args.name?'Test':'',modified:'v1',__islocal:args.name?undefined:1,docstatus:0},is_new:!args.name,permissions:schema.permissions});if(method==='approval')return response(null);if(method==='supplier_connections')return response([]);throw Error('Unexpected '+method)}}
test('independent ERP navigation keeps Vietnamese search and internal scope URLs',()=>{assert.equal(erpFeatures(rows,{search:'nha cung cap'})[0].name,'Supplier');assert.match(erpHref('Buying','C'),/company=C/)})
test('supplier list opens its own editor, with no Desk links or iframe',async()=>{
 const calls=[];server(calls);window.history.replaceState({},'', '/lotus/erpnext?module=Buying&company=C&erp_doctype=Supplier')
 const view=mount(Workspace)
 try{await tick();await tick();button(view.root,'SUP-1').click();await tick();await tick();assert.ok(view.root.querySelector('.erp-document form'));assert.match(view.root.textContent,/Tên nhà cung cấp/);assert.equal(view.root.querySelectorAll('iframe,a[href^="/desk"],a[href^="/app"]').length,0);assert.ok(calls.some(c=>c.method==='document'&&c.args.name==='SUP-1'))}finally{view.unmount()}
})
test('cached workbench cannot redirect from a different workspace',async()=>{
 server();const route=reactive({path:'/erpnext',fullPath:'/erpnext?module=Buying&company=C',query:{module:'Buying',company:'C'}}),writes=[]
 const view=mount({setup(){provide(routerKey,{beforeEach:()=>()=>{},replace:r=>writes.push(r),push:r=>writes.push(r)});provide(routeLocationKey,route);return()=>h(Workspace)}})
 try{await tick();await tick();writes.length=0;route.path='/kho';route.fullPath='/kho?company=C';route.query={company:'C'};await tick();assert.equal(writes.length,0)}finally{view.unmount()}
})
test('form validates required fields across native tabs and updates the same model',async()=>{
 const model=reactive({supplier_name:''}),formSchema={...schema,fields:[{fieldname:'basic',fieldtype:'Tab Break',label:'Thông tin'},{fieldname:'supplier_name',fieldtype:'Data',label:'Tên nhà cung cấp',reqd:1},{fieldname:'other',fieldtype:'Tab Break',label:'Khác'},{fieldname:'tax_id',fieldtype:'Data',label:'Mã số thuế'}]}
 const view=mount(Form,{schema:formSchema,model})
 try{await tick();assert.equal(view.vm.$.subTree.component.exposed.validate(),false);await tick();assert.match(view.root.textContent,/Bắt buộc/);input(view.root,'Supplier new');await tick();assert.equal(model.supplier_name,'Supplier new');assert.equal(view.vm.$.subTree.component.exposed.validate(),true)}finally{view.unmount()}
})
test('editor retries an ambiguous save with the same command key and original version',async()=>{
 const calls=[];server(calls);const original=globalThis.fetch
 globalThis.fetch=async(url,options)=>{if(String(url).includes('.action')){calls.push({method:'action',args:JSON.parse(options.body)});return {ok:false,status:504,json:async()=>({message:'Timeout'})}}return original(url,options)}
 const view=mount(Editor,{doctype:'Supplier',name:'SUP-1',company:'C'})
 try{await tick();await tick();input(view.root,'Changed');await tick();button(view.root,'Lưu').click();await tick();button(view.root,'Lưu').click();await tick();const actions=calls.filter(c=>c.method==='action');assert.equal(actions.length,2);assert.equal(actions[0].args.client_key,actions[1].args.client_key);assert.equal(actions[0].args.modified,'v1')}finally{view.unmount()}
})
test('reports show native totals, export complete filters and drill down internally',async()=>{
 globalThis.fetch=async(url)=>{if(String(url).includes('.report_definition'))return response({title:'Consolidated Financial Statement',filters:[{fieldname:'presentation_currency',label:'Tiền tệ',fieldtype:'Data'}],defaults:{presentation_currency:'VND'},can_export:true});if(String(url).includes('.run_report'))return response({columns:[{fieldname:'account',label:'Tài khoản',fieldtype:'Link',options:'Account'},{fieldname:'total',label:'Tổng',fieldtype:'Currency'}],result:[{account:'152 - C',account_name:'Nguyên vật liệu',total:8000000}],report_summary:[{label:'Tài sản',value:8000000,datatype:'Currency',currency:'VND'}]});throw Error(String(url))}
 const opened=[],view=mount(Report,{name:'Consolidated Financial Statement',company:'C','onOpen-report':v=>opened.push(v)})
 try{await tick();await tick();assert.match(view.root.textContent,/8.000.000 VND/);const link=view.root.querySelector('a[download]');assert.match(link.href,/export_report/);assert.match(decodeURIComponent(link.href),/VND/);button(view.root,'Nguyên vật liệu').click();await tick();assert.equal(opened[0].name,'General Ledger');assert.deepEqual(opened[0].filters.account,['152 - C'])}finally{view.unmount()}
})

test('legacy warehouse, buying, HR and financial URLs resolve into the shared workbench',()=>{
 assert.deepEqual(erpDestination('/kho',{stock_view:'history'}),{kind:'DocType',name:'Stock Entry',isNew:false})
 assert.equal(erpDestination('/mua-hang',{buying_view:'suppliers'}).name,'Supplier')
 assert.equal(erpDestination('/mua-hang',{action:'create_order'}).isNew,true)
 assert.deepEqual(erpDestination('/kho',{module:'Buying',erp_home:'1'}),{kind:'Workspace',name:'Buying'})
 assert.equal(erpDestination('/tai-chinh',{tab:'planning'}).kind,'Lotus')
 assert.equal(erpDestination('/nhan-su',{hr_view:'candidates'}).name,'Job Applicant')
 assert.deepEqual(erpLegacyQuery('/mua-hang',{kind:'DocType',name:'Purchase Invoice'}),{buying_view:'invoices'})
})

test('an in-flight catalog cannot redirect after leaving its cached workbench',async()=>{
 let finish;globalThis.fetch=()=>new Promise(resolve=>finish=resolve)
 const route=reactive({path:'/erpnext',fullPath:'/erpnext?module=Buying',query:{module:'Buying'}}),writes=[]
 const view=mount({setup(){provide(routerKey,{beforeEach:()=>()=>{},replace:r=>writes.push(r),push:r=>writes.push(r)});provide(routeLocationKey,route);return()=>h(Workspace)}})
 try{await tick();route.path='/kho';route.fullPath='/kho';route.query={};finish(response({modules:[{value:'Buying'}],rows,companies:[{name:'C'}],warehouses:[]}));await tick();await tick();assert.equal(writes.length,0)}finally{view.unmount()}
})
