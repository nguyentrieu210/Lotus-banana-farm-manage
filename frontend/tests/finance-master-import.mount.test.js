import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,window,document} from './support/mount.mjs'

const API='lotus_farm.finance.master_imports.'
const Component=await load('components/finance/FinanceMasterImport.vue')
const button=label=>[...document.querySelectorAll('dialog[open] button')].find(b=>b.textContent.trim()===label)
let handler,calls=[],view,imported
const previousReader=globalThis.FileReader
globalThis.fetch=async(url,options={})=>{
 const method=new URL(url,'http://localhost').pathname.replace('/api/method/','')
 const args=JSON.parse(options.body||'{}')
 calls.push({method,args,write:options.method==='POST'})
 const data=await handler(method,args)
 return {ok:!data.exc_type,status:data.exc_type?417:200,json:async()=>data.exc_type?data:{message:data}}
}
test.beforeEach(()=>{calls=[];imported=null;globalThis.FileReader=class{readAsDataURL(file){this.result=file.content||'data:application/octet-stream;base64,d29ya2Jvb2s=';this.onload()}}})
test.afterEach(()=>{view?.unmount();globalThis.FileReader=previousReader})
async function open(kind='categories'){
 view=mount(Component,{modelValue:true,kind,onImported:value=>{imported=value}});await tick();return view
}
async function file(kind='categories',value={size:20}){
 const input=document.querySelector(`[aria-label="${kind==='categories'?'File nhóm tài sản':'File hệ thống tài khoản'}"]`)
 Object.defineProperty(input,'files',{value:[value],configurable:true})
 input.dispatchEvent(new window.Event('change',{bubbles:true}));await tick()
}
async function click(label){button(label).click();for(let i=0;i<4;i++)await tick()}
const preview={valid:true,fingerprint:'reviewed-v1',create_count:1,skip_count:0,rows:[{line:2,action:'create',values:{asset_category_name:'Máy bơm'},errors:{}}]}

test('category import previews in POST, requires review and confirms the same fingerprint',async()=>{
 handler=async method=>method.endsWith('preview')?preview:{count:1,skipped:0}
 await open()
 assert.equal(button('Xác nhận nhập nhóm'),undefined)
 await file();await click('Xem trước')
 assert.equal(calls[0].method,API+'preview');assert.ok(calls[0].write)
 assert.equal(calls[0].args.kind,'categories')
 assert.match(document.querySelector('dialog[open]').textContent,/Máy bơm/)
 await click('Xác nhận nhập nhóm')
 assert.equal(calls[1].args.fingerprint,'reviewed-v1')
 assert.equal(calls[1].args.content,calls[0].args.content)
 assert.ok(calls[1].write)
 assert.equal(imported.count,1)
})

test('account import shows row errors and blocks confirmation',async()=>{
 handler=async()=>({...preview,valid:false,rows:[{line:3,action:'create',values:{account_number:'21101',account_name:'Máy'},errors:{parent_account:'Tài khoản cha không có'}}]})
 await open('accounts');await file('accounts');await click('Xem trước')
 assert.equal(calls[0].args.kind,'accounts')
 assert.match(document.querySelector('dialog[open]').textContent,/Tài khoản cha không có/)
 assert.equal(button('Xác nhận nhập tài khoản').disabled,true)
})

test('changing the file clears review and an oversized upload never reaches the API',async()=>{
 handler=async()=>preview
 await open();await file();await click('Xem trước')
 await file('categories',{size:5_000_001})
 assert.equal(button('Xác nhận nhập nhóm'),undefined)
 assert.equal(button('Xem trước').disabled,true)
 assert.match(document.querySelector('dialog[open]').textContent,/5 MB/)
 assert.equal(calls.length,1)
})

test('stale confirmation stays in the dialog and requires a fresh preview',async()=>{
 handler=async method=>method.endsWith('preview')?preview:{exc_type:'ValidationError',message:'Danh mục đã thay đổi. Xem trước lại.'}
 await open();await file();await click('Xem trước');await click('Xác nhận nhập nhóm')
 assert.match(document.querySelector('dialog[open]').textContent,/Danh mục đã thay đổi/)
 assert.equal(button('Xác nhận nhập nhóm'),undefined)
 await click('Xem trước');assert.equal(button('Xác nhận nhập nhóm').disabled,false)
})
