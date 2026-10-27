import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,window,ref,h} from './support/mount.mjs'

const Chat=await load('components/InternalChat.vue')
const people=[{user:'two',label:'Nguyễn Hai',online:true},{user:'three',label:'Trần Ba',online:false}]
const room={name:'room-1',kind:'Direct',title:'Nguyễn Hai',members:[{user:'one',label:'Một',last_read_seq:0},{...people[0],last_read_seq:0}],last_seq:0,unread:0}
const response=value=>({ok:true,json:async()=>({message:value})})
const action=(view,label)=>view.root.querySelector(`button[aria-label="${label}"]`)
function client(){return {rooms:ref([structuredClone(room)]),unread:ref(0),loading:ref(false),error:ref(''),event:ref(null),refresh:async()=>{}}}
function mock(t,run){const original=globalThis.fetch;globalThis.fetch=async(url,options)=>run(url,options?.body?JSON.parse(options.body):{});t.after(()=>globalThis.fetch=original)}
async function input(element,value){element.value=value;element.dispatchEvent(new window.Event('input',{bubbles:true}));await tick()}

test('direct chat renders plain text, prevents double send and marks only newly read messages',async t=>{
 let finish,sends=0,reads=0
 const state=client()
 mock(t,(url,body)=>{
  if(url.includes('.history'))return response({room,messages:[],has_more:false})
  if(url.includes('.mark_read')){reads++;return response({seq:body.seq})}
  if(url.includes('.typing'))return response(null)
  if(url.includes('.send')){sends++;return new Promise(resolve=>finish=resolve)}
  throw Error(url)
 })
 const view=mount(Chat,{user:'one',client:state,active:true});t.after(view.unmount)
 action(view,'Mở chat Nguyễn Hai').click();await tick();await tick()
 await input(view.root.querySelector('textarea'),'Xin chào')
 view.root.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick()
 assert.equal(action(view,'Gửi tin nhắn').disabled,true)
 view.root.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick();assert.equal(sends,1)
 finish(response({name:'m1',room:room.name,seq:1,sender:'one',body:'<img src=x onerror=alert(1)>',creation:'2026-10-26 12:00:00'}));await tick();await tick()
 assert.equal(view.root.querySelector('.lotus-chat__bubble img'),null)
 assert.match(view.root.querySelector('.lotus-chat__bubble').textContent,/<img src=x/)
 view.root.querySelector('.lotus-chat__messages').dispatchEvent(new window.Event('scroll'));await tick()
 view.root.querySelector('.lotus-chat__messages').dispatchEvent(new window.Event('scroll'));await tick()
 assert.equal(reads,1,'scroll/read synchronization does not loop')
})

test('group creation sends only the selected people and group title',async t=>{
 let created
 mock(t,(url,body)=>{
  if(url.includes('.people'))return response(people)
  if(url.includes('.create')){created=body;return response({...room,kind:'Group',title:body.title})}
  if(url.includes('.history'))return response({room:{...room,kind:'Group'},messages:[],has_more:false})
  throw Error(url)
 })
 const view=mount(Chat,{user:'one',client:client(),active:true});t.after(view.unmount)
 action(view,'Cuộc trò chuyện mới').click();await tick()
 ;[...view.root.querySelectorAll('button')].find(b=>b.textContent==='Tạo nhóm').click();await tick()
 await input(view.root.querySelector('input[maxlength="80"]'),'Đội kho')
 action(view,'Chọn Nguyễn Hai').click();await tick()
 assert.equal(action(view,'Chọn Nguyễn Hai').getAttribute('aria-pressed'),'true')
 view.root.querySelector('.lotus-chat__create button').click();await tick();await tick()
 assert.deepEqual(created,{members:['two'],kind:'Group',title:'Đội kho'})
})

test('file retry reuses the uploaded file and the same message id',async t=>{
 let uploads=0,sends=0;const ids=[]
 const original=globalThis.fetch
 globalThis.fetch=async(url,options)=>{
  if(url.includes('upload_file')){uploads++;return response({file_url:'/private/files/chat-test.txt'})}
  const body=options?.body?JSON.parse(options.body):{}
  if(url.includes('.history'))return response({room,messages:[],has_more:false})
  if(url.includes('.mark_read'))return response({seq:1})
  if(url.includes('.send')){ids.push(body.client_id);sends++;if(sends===1)throw Error('offline');return response({name:'f1',room:room.name,seq:1,sender:'one',body:'',creation:'2026-10-26 12:00:00',file:{url:'/api/method/lotus_farm.chat.download?message=f1',name:'note.txt',size:4}})}
  throw Error(url)
 }
 t.after(()=>globalThis.fetch=original)
 const view=mount(Chat,{user:'one',client:client(),active:true});t.after(view.unmount)
 action(view,'Mở chat Nguyễn Hai').click();await tick()
 const file=view.root.querySelector('input[type=file]')
 Object.defineProperty(file,'files',{configurable:true,value:[new File(['note'],'note.txt',{type:'text/plain'})]})
 file.dispatchEvent(new window.Event('change'));await tick()
 action(view,'Gửi tin nhắn').click();await tick();await tick()
 // Native submit is not synthesized by Happy DOM for every component wrapper.
 if(!sends){view.root.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()}
 assert.match(view.root.querySelector('[role=alert]').textContent,/Chưa gửi xong/)
 view.root.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()
 assert.equal(uploads,1);assert.equal(sends,2);assert.equal(ids[0],ids[1])
 assert.ok(view.root.querySelector('a[aria-label="Tải note.txt"]'))
})

test('mobile chat offers notification setup without auto-requesting permission',async t=>{
 const view=mount(Chat,{user:'one',client:client(),active:true,mobile:true,pushApp:'work'});t.after(view.unmount)
 const button=[...view.root.querySelectorAll('button')].find(node=>node.textContent.includes('Bật thông báo tin nhắn'))
 assert.ok(button,'user chooses when to enable device push notifications')
 assert.equal(view.root.querySelectorAll('.lotus-chat__push-setup').length,1)
})

test('mobile composer uses a native submit button and preserves IME input',async t=>{
 let sends=0
 mock(t,url=>{
  if(url.includes('.history'))return response({room,messages:[],has_more:false})
  if(url.includes('.typing'))return response(null)
  if(url.includes('.send')){sends++;throw Error('unexpected send')}
  throw Error(url)
 })
 const view=mount(Chat,{user:'one',client:client(),active:true,mobile:true});t.after(view.unmount)
 action(view,'Mở chat Nguyễn Hai').click();await tick()
 const text=view.root.querySelector('textarea');await input(text,'Xin chào')
 assert.equal(action(view,'Gửi tin nhắn').type,'submit')
 text.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Enter',isComposing:true,bubbles:true,cancelable:true}));await tick()
 assert.equal(sends,0)
})

test('changing account during a send clears the old room and ignores its completion',async t=>{
 let finish
 const user=ref('one'),state=client()
 mock(t,url=>{
  if(url.includes('.history'))return response({room,messages:[],has_more:false})
  if(url.includes('.typing'))return response(null)
  if(url.includes('.send'))return new Promise(resolve=>finish=resolve)
  throw Error(url)
 })
 const view=mount({setup:()=>()=>h(Chat,{user:user.value,client:state,active:true})});t.after(view.unmount)
 action(view,'Mở chat Nguyễn Hai').click();await tick()
 await input(view.root.querySelector('textarea'),'Tin riêng')
 view.root.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick()
 user.value='second';state.rooms.value=[];await tick()
 assert.equal(view.root.querySelector('.lotus-chat__heading'),null)
 finish(response({name:'old',seq:1,sender:'one',body:'Tin riêng',creation:'2026-10-26 12:00:00'}));await tick()
 assert.doesNotMatch(view.root.textContent,/Tin riêng/)
})

test('links are clickable, recall needs a second tap and recalled text disappears',async t=>{
 let recalled=0
 const mine={name:'m1',room:room.name,seq:1,sender:'one',body:'Xem https://lotus.example/kho?x=1. Rồi báo',creation:new Date().toISOString().replace('T',' ').slice(0,19)}
 mock(t,(url,body)=>{
  if(url.includes('.history'))return response({room,messages:[mine],has_more:false})
  if(url.includes('.mark_read'))return response({seq:body.seq})
  if(url.includes('.recall')){recalled++;return response({...mine,body:'',recalled:true})}
  throw Error(url)
 })
 const view=mount(Chat,{user:'one',client:client(),active:true});t.after(view.unmount)
 action(view,'Mở chat Nguyễn Hai').click();await tick();await tick()
 const link=view.root.querySelector('.lotus-chat__bubble a')
 assert.equal(link.getAttribute('href'),'https://lotus.example/kho?x=1','trailing punctuation stays outside the link')
 assert.equal(link.getAttribute('rel'),'noopener noreferrer')
 const recall=[...view.root.querySelectorAll('button')].find(b=>b.textContent==='Thu hồi')
 recall.click();await tick();assert.equal(recalled,0,'first tap only arms the action')
 assert.match(recall.textContent,/Bấm lần nữa/)
 recall.click();await tick();await tick();assert.equal(recalled,1)
 assert.match(view.root.querySelector('.lotus-chat__bubble').textContent,/Tin nhắn đã thu hồi/)
})

test('group tools rename and leave; the inbox search filters rooms',async t=>{
 const group={...room,name:'g1',kind:'Group',title:'Tổ A',owner:'one',is_owner:true,members:[...room.members,{user:'three',label:'Trần Ba',last_read_seq:0}]}
 const calls=[]
 mock(t,(url,body)=>{
  if(url.includes('.history'))return response({room:group,messages:[],has_more:false})
  if(url.includes('.rename')){calls.push(['rename',body.title]);return response({...group,title:body.title})}
  if(url.includes('.remove_member')){calls.push(['remove',body.member]);return response({left:true,room:null})}
  throw Error(url)
 })
 const state=client();state.rooms.value=[group,...Array.from({length:6},(_,i)=>({...room,name:'r'+i,title:'Người '+i,preview:'',members:room.members}))]
 const view=mount(Chat,{user:'one',client:state,active:true});t.after(view.unmount)
 await input(view.root.querySelector('input[aria-label="Tìm cuộc trò chuyện"]'),'to a')
 assert.equal(view.root.querySelectorAll('.lotus-chat__room').length,1,'search ignores accents and case')
 action(view,'Mở chat Tổ A').click();await tick();await tick()
 action(view,'Xem thành viên').click();await tick()
 await input(view.root.querySelector('input[aria-label="Đổi tên nhóm"]'),'Tổ bao buồng')
 ;[...view.root.querySelectorAll('button')].find(b=>b.textContent==='Đổi tên').click();await tick();await tick()
 const leave=()=>[...view.root.querySelectorAll('button')].find(b=>/rời nhóm/i.test(b.textContent))
 leave().click();await tick();leave().click();await tick();await tick()
 assert.deepEqual(calls,[['rename','Tổ bao buồng'],['remove','one']])
})
