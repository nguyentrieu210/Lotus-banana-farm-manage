import test from 'node:test'
import assert from 'node:assert/strict'
import {load,loadModule,mount,tick,document,window,h} from './support/mount.mjs'
import {provide,reactive} from 'vue'
import {routerKey,routeLocationKey} from 'vue-router'
import {erpFeatures,erpHref} from '../src/erpnext-navigation.js'
const {permittedRoute}=await loadModule('router.js')
const Workspace=await load('components/ErpnextWorkspace.vue')
const rows=[{id:'1',module:'Stock',module_label:'Stock',name:'Stock Ledger',label:'Stock Ledger',kind:'Report',href:'/desk/query-report/Stock%20Ledger'},{id:'2',module:'Buying',name:'Purchase Order',label:'Purchase Order',kind:'DocType',href:'/desk/purchase-order'}]
test('ERP directory searches Vietnamese and native names and filters module/type',()=>{
 assert.equal(erpFeatures(rows,{search:'so kho'})[0].name,'Stock Ledger');assert.equal(erpFeatures(rows,{module:'Buying',kind:'Report'}).length,0);assert.equal(erpFeatures(rows,{search:'purchase order'})[0].module,'Buying');assert.match(erpHref('Stock','C','K'),/module=Stock&company=C&warehouse=K/)
 assert.equal(permittedRoute('/erpnext',{capabilities:{native_erp:true}}),true);assert.equal(permittedRoute('/erpnext',{capabilities:{}}),false)
})
test('directory renders native links and retains searches in URL',async()=>{
 window.history.replaceState({},'', '/lotus/erpnext?module=Stock');globalThis.fetch=async()=>({ok:true,json:async()=>({message:{modules:[{value:'Stock',label:'Stock'},{value:'Buying',label:'Buying'}],rows,companies:[],warehouses:[]}})})
 const view=mount(Workspace);try{await tick();await tick();assert.match(view.root.textContent,/Sổ kho/);assert.doesNotMatch(view.root.textContent,/Đơn mua/);const a=view.root.querySelector('a[href*="query-report"]');assert.ok(view.root.querySelector('.lotus-mobile-record a[href*="query-report"]'));assert.equal(a.target,'_blank');assert.equal(a.getAttribute('rel'),'noopener');const input=view.root.querySelector('input[type=search]');input.value='không tồn tại';input.dispatchEvent(new window.Event('input',{bubbles:true}));await tick();assert.match(location.search,/search=/);assert.match(view.root.textContent,/Không có chức năng/)}finally{view.unmount()}
})
test('cached ERP directory cannot redirect after navigating to another workspace',async()=>{
 const route=reactive({path:'/erpnext',query:{module:'Stock'}}),replacements=[]
 globalThis.fetch=async()=>({ok:true,json:async()=>({message:{modules:[{value:'Stock',label:'Stock'}],rows,companies:[],warehouses:[]}})})
 const view=mount({setup(){provide(routerKey,{replace:r=>replacements.push(r)});provide(routeLocationKey,route);return()=>h(Workspace)}})
 try{await tick();await tick();replacements.length=0;route.path='/kho';route.query={company:'C'};await tick();await tick();assert.equal(replacements.length,0)}finally{view.unmount()}
})
