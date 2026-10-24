// Set MOBILE_UX_HAPPY_DOM to an isolated happy-dom/lib/index.js installation.
const {Window}=await import(process.env.MOBILE_UX_HAPPY_DOM||'happy-dom')
import fs from 'node:fs'
import path from 'node:path'
import {pathToFileURL,fileURLToPath} from 'node:url'
import assert from 'node:assert/strict'
const project=fileURLToPath(new URL('../frontend',import.meta.url))
const runtime=project+'/node_modules/.mobile-ux-audit'
fs.mkdirSync(runtime,{recursive:true})
const window=new Window({url:'http://localhost:8080/warehouse',width:390,height:844})
const viewport=new window.EventTarget();Object.assign(viewport,{width:390,height:844,offsetTop:0,offsetLeft:0});Object.defineProperty(window,'visualViewport',{value:viewport,configurable:true})
for(const name of ['window','document','navigator','location','Element','HTMLElement','SVGElement','Node','Event','CustomEvent','KeyboardEvent','MouseEvent','ResizeObserver','getComputedStyle','requestAnimationFrame','cancelAnimationFrame'])Object.defineProperty(globalThis,name,{value:typeof window[name]==='function'&&['getComputedStyle','requestAnimationFrame','cancelAnimationFrame'].includes(name)?window[name].bind(window):window[name],configurable:true})
window.HTMLElement.prototype.scrollIntoView=function(){}
// Cropper registers its custom elements when the shared signature settings are imported.
Object.defineProperty(globalThis,'customElements',{value:window.customElements,configurable:true})
const {parse,compileScript}=await import(pathToFileURL(project+'/node_modules/@vue/compiler-sfc/dist/compiler-sfc.esm-browser.js'))
const {createApp,nextTick}=await import(pathToFileURL(project+'/node_modules/vue/dist/vue.runtime.esm-bundler.js'))
const generated=new Map()
function compile(filename){
 const absolute=path.resolve(filename)
 if(generated.has(absolute))return generated.get(absolute)
 const out=path.join(runtime,path.relative(project,absolute).replace(/[\\/]/g,'__').replace(/\.vue$/,'.mjs').replace(/\.js$/,'.mjs'))
 generated.set(absolute,out)
 let code=fs.readFileSync(filename,'utf8')
 code=code.replace(/import\.meta\.env/g,'({DEV:false,PROD:true,MODE:"test"})')
 code=code.replace(/^import ['"][^'"]*(?:\.css|register-[^'"]*)['"];?\s*$/gm,'')
 if(filename.endsWith('.vue'))code=compileScript(parse(code).descriptor,{id:path.basename(filename),inlineTemplate:true}).content
 code=code.replace(/(from\s+|^import\s+)(['"])(\.[^'"]+|@\/[^'"]+)\2/gm,(match,keyword,quote,relative)=>{
  let target=relative.startsWith('@/')?path.join(project,'src',relative.slice(2)):path.resolve(path.dirname(filename),relative)
  if(!path.extname(target))target=fs.existsSync(target+'.js')?target+'.js':path.join(target,'index.js')
  if(path.basename(target)==='api.js')target=runtime+'/api.js'
  else target=compile(target)
  return keyword+JSON.stringify(pathToFileURL(target).href)
 })
 fs.writeFileSync(out,code)
 return out
}
fs.writeFileSync(runtime+'/api.js',`export const calls=[];export let releaseDetail;
export const stores=[{name:'K1',warehouse_name:'Kho 1'},{name:'K2',warehouse_name:'Kho 2'}];
export const items=Array.from({length:12},(_,i)=>({name:'I'+i,item_name:i===0?'Dây cột buồng':'Vật tư '+i,stock_uom:'Kg'}));
export const providers=[{name:'S1',supplier_name:'NCC 1'}];
export function setCSRF(){};export async function upload(){};
export async function call(method,args={},write=false){calls.push({method,args,write});const name=method.split('.').pop();
if(name==='bootstrap')return {user:'audit@example.invalid',companies:[{name:'Lotus'}],today:'2026-10-16',can_create:true,permissions:{'Stock Entry':true,'Purchase Receipt':true}};
if(name==='setup'||name==='catalog')return {warehouses:stores,items,suppliers:providers.map(r=>({...r})),conversions:[],can_create:true,can_create_supplier:true,currency:'VND'};
if(name==='suppliers')return providers.map(r=>({...r}));
if(name==='save_supplier'){const name=args.supplier_id||'S'+(providers.length+1);const row={name,supplier_name:args.name};if(!providers.some(r=>r.name===name))providers.push(row);return row};
if(name==='orders'&&method.includes('.purchasing.'))return [];
if(name==='employee_choices'||name==='requests')return [];
if(name==='documents')return {rows:[{name:'DOC1',doctype:'Stock Entry',kind:'Nhập kho',posting_date:'2026-10-16',docstatus:0}],has_more:false};
if(name==='document')return new Promise(resolve=>releaseDetail=()=>resolve({name:'DOC1',items:[],docstatus:0}));
if(name==='receipt_accounts')return {accounts:[]};if(name==='receipt_options')return {enabled:false};if(name==='overview')return {items,total_count:items.length};if(name==='orders')return {rows:[{name:'PO1',supplier_name:'NCC 1',remaining_lines:1,expected_date:'2026-10-16'}]};if(name==='order_detail'||name==='purchase_order')return {name:'PO1',supplier_name:'NCC 1',can_receive:true,items:[{line:'L1',item_name:'Dây cột buồng',remaining_qty:5,conversion_factor:1,uom:'Kg'}]};if(name==='movements')return {rows:[]};throw Error('Unexpected API '+name)};`)
const Link=(await import(pathToFileURL(compile(project+'/src/components/MobileLinkField.vue')))).default
const Main=(await import(pathToFileURL(compile(project+'/src/WarehouseMobile.vue')))).default
const api=await import(pathToFileURL(runtime+'/api.js'))
const tick=async()=>{await nextTick();await new Promise(resolve=>setTimeout(resolve,30));await nextTick()}
function mount(component,props={}){const root=document.createElement('div');document.body.append(root);const app=createApp(component,props);app.mount(root);return {root,app}}
function button(root,text){const norm=s=>String(s||'').replace(/[^\p{L}\p{N}]/gu,'');const e=[...document.querySelectorAll('button,[role=tab]')].find(e=>norm(e.textContent)===norm(text)||norm(e.getAttribute('aria-label'))===norm(text));assert.ok(e,'Missing button '+text);return e}
function input(root,value){root.value=value;root.dispatchEvent(new window.Event('input',{bubbles:true}))}
const results=[]
async function check(name,fn){await fn();results.push(name);console.log('PASS '+name)}
let mounted=mount(Link,{searchable:false,modelValue:'K1',options:api.stores.map(r=>({value:r.name,label:r.warehouse_name})),'onUpdate:modelValue':v=>results.push('selected:'+v)})
await check('small catalog renders native select without a text input',async()=>{assert.equal(mounted.root.querySelectorAll('input').length,0);assert.equal(mounted.root.querySelector('select').value,'K1');mounted.root.querySelector('select').value='K2';mounted.root.querySelector('select').dispatchEvent(new Event('change',{bubbles:true}));assert.ok(results.includes('selected:K2'))})
mounted.app.unmount();mounted.root.remove()
const changes=[]
mounted=mount(Link,{modelValue:'I0',options:api.items.map(r=>({value:r.name,label:r.item_name})),'onUpdate:modelValue':v=>changes.push(v)})
await check('large catalog opens a portal directly under body',async()=>{mounted.root.querySelector('input').focus();await tick();assert.equal(document.querySelector('[role=listbox]').parentElement,document.body)})
await check('editing Vietnamese search preserves the selected link until confirmation',async()=>{input(mounted.root.querySelector('input'),'buong');await tick();assert.equal(document.querySelectorAll('[role=option]').length,1);assert.equal(changes.length,0);document.querySelector('[role=option]').click();await tick();assert.deepEqual(changes,['I0']);assert.equal(document.querySelector('[role=listbox]'),null)})
await check('IME Enter never commits a partially composed search',async()=>{mounted.root.querySelector('input').focus();await tick();mounted.root.querySelector('input').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',isComposing:true,bubbles:true}));await tick();assert.equal(changes.length,1);assert.ok(document.querySelector('[role=listbox]'))})
await check('touch on options is not prevented, so native vertical scroll remains available',async()=>{const e=new window.Event('pointerdown',{bubbles:true,cancelable:true});Object.assign(e,{pointerType:'touch',clientX:40,clientY:140});document.querySelector('[role=option]').dispatchEvent(e);assert.equal(e.defaultPrevented,false)})
await check('Escape dismisses the picker',async()=>{mounted.root.querySelector('input').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));await tick();assert.equal(document.querySelector('[role=listbox]'),null)})
mounted.app.unmount();mounted.root.remove()
mounted=mount(Main);await tick();await tick()
await check('warehouse form uses OS selectors and supports multiple lines',async()=>{button(mounted.root,'🛒Tạo đơn mua›').click();await tick();assert.ok(mounted.root.querySelector('select[aria-label="Kho nhận mặc định"]'));assert.equal(mounted.root.querySelectorAll('input[role=combobox]').length,2);button(mounted.root,'+ Thêm mặt hàng').click();await tick();assert.equal(mounted.root.querySelectorAll('input[role=combobox]').length,3)})
await check('keyboard viewport changes hide the bottom bar and restore it on dismissal',async()=>{
 const field=mounted.root.querySelector('input[role=combobox]');field.focus();await tick();viewport.height=400;viewport.dispatchEvent(new Event('resize'));await tick()
 assert.ok(mounted.root.querySelector('.mobile-keyboard-open'))
 field.blur();viewport.height=844;viewport.dispatchEvent(new Event('resize'));await tick();assert.equal(mounted.root.querySelector('.mobile-keyboard-open'),null)
 document.dispatchEvent(new Event('warehouse-dismiss-picker'));await tick()
})
await check('dirty navigation opens an in-page dialog and Stay preserves the form',async()=>{button(mounted.root,'Trang chủ').click();await tick();assert.equal(document.querySelector('.van-dialog').style.display!=='none',true);button(mounted.root,'Ở lại').click();await tick();assert.equal(mounted.root.querySelectorAll('.mobile-line').length,2);assert.equal(document.querySelector('.van-dialog').style.display!=='none',false)})
await check('confirmed navigation leaves the form without a browser-blocking confirm',async()=>{button(mounted.root,'Trang chủ').click();await tick();button(mounted.root,'Rời đi').click();await tick();assert.ok(mounted.root.querySelector('.mobile-actions'))})
await check('tapping the current list tab does not reload or reset the list',async()=>{button(mounted.root,'Lịch sử').click();await tick();const before=api.calls.length;button(mounted.root,'Lịch sử').click();await tick();assert.equal(api.calls.length,before)})
await check('a late detail response cannot pull the user out of another tab',async()=>{button(mounted.root,'Nhập khoNhápDOC116/10/2026Chi tiết ›').click();await tick();assert.equal(typeof api.releaseDetail,'function');button(mounted.root,'Xuất nhập tồn').click();await tick();api.releaseDetail();await tick();assert.ok(mounted.root.querySelector('.mobile-switcher[aria-label="Chọn nội dung"]'));assert.equal(mounted.root.querySelector('.mobile-summary'),null)})
await check('vertical touch scroll and OS edge gesture never switch tabs',async()=>{
 const root=mounted.root.querySelector('.lotus-mobile')
 function touch(name,x,y){const e=new window.Event(name,{bubbles:true,cancelable:true});e.touches=name==='touchend'?[]:[{clientX:x,clientY:y}];e.changedTouches=[{clientX:x,clientY:y}];root.dispatchEvent(e)}
 touch('touchstart',200,300);touch('touchmove',190,450);touch('touchend',180,470);await tick();assert.ok(mounted.root.querySelector('.mobile-switcher[aria-label="Chọn nội dung"]'))
 touch('touchstart',10,300);touch('touchmove',150,300);touch('touchend',200,300);await tick();assert.ok(mounted.root.querySelector('.mobile-switcher[aria-label="Chọn nội dung"]'))
 touch('touchstart',240,300);touch('touchmove',140,310);touch('touchend',100,310);await tick();assert.ok(mounted.root.querySelector('.mobile-account'))
})
await check('all three stock entry forms open with native warehouse controls',async()=>{
 for(const label of ['⬆Xuất kho›','⇄Chuyển kho›','⬇Nhập không theo đơn›']){
  button(mounted.root,'Trang chủ').click();await tick();button(mounted.root,label).click();await tick()
  assert.ok(mounted.root.querySelector('form'));assert.ok(mounted.root.querySelector('.lotus-pwa-select select'))
  button(mounted.root,'Quay lại').click();await tick();await tick()
 }
})
await check('receipt input rejects an empty date before making a write request',async()=>{
 button(mounted.root,'Trang chủ').click();await tick();button(mounted.root,'📦Nhập theo đơn›').click();await tick()
 mounted.root.querySelector('input[aria-label="Đơn mua chờ nhận"]').focus();await tick();document.querySelector('[role=option]').click();await tick();button(mounted.root,'Mở đơn nhận hàng').click();await tick()
 input(mounted.root.querySelector('input[inputmode=decimal]'),'2');input(mounted.root.querySelector('input[type=date]'),'');await tick()
 const before=api.calls.filter(c=>c.write).length
 mounted.root.querySelector('.warehouse-receiving form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick()
 assert.equal(api.calls.filter(c=>c.write).length,before);assert.match(mounted.root.querySelector('[role=alert]').textContent,/Chọn ngày/)
})
mounted.app.unmount();mounted.root.remove()
console.log(JSON.stringify({passed:results.filter(r=>!r.startsWith('selected:')).length,results},null,2))
if(process.argv[1]&&pathToFileURL(process.argv[1]).href===import.meta.url)await window.happyDOM.close()

export {compile,project,mount,tick,button,input,api,check,results};
