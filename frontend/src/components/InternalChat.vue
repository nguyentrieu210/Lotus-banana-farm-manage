<script setup>
import {computed,nextTick,onBeforeUnmount,ref,watch} from 'vue'
import {Button as UiButton} from './ui/button'
import {Input} from './ui/input'
import {Textarea} from './ui/textarea'
import {FormField} from './ui/form-field'
import {Tooltip} from './ui/tooltip'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileInput from './LotusMobileInput.vue'
import LotusIcon from './LotusIcon.vue'
import {chatAPI} from '../chat-client'
import {upload} from '../api'

const props=defineProps({user:{type:String,required:true},client:{type:Object,required:true},active:Boolean,mobile:Boolean})
const emit=defineEmits(['busy'])
const selected=ref(''),detail=ref(null),messages=ref([]),draft=ref(''),files=ref([]),error=ref(''),busy=ref(false),loading=ref(false)
const mode=ref('list'),group=ref(false),title=ref(''),search=ref(''),people=ref([]),chosen=ref([]),hasMore=ref(false),showMembers=ref(false)
const list=ref(null),fileInput=ref(null),textInput=ref(null),typingNames=ref({})
let generation=0,peopleVersion=0,searchTimer,typingTimer,lastTyping=0,sendId='',syncPending=false,readSeq=0
const Action=computed(()=>props.mobile?LotusMobileButton:UiButton)
const primary=computed(()=>props.mobile?'primary':'default')
const neutral=computed(()=>props.mobile?'default':'ghost')
const rooms=computed(()=>props.client.rooms.value)
const current=computed(()=>detail.value||rooms.value.find(r=>r.name===selected.value))
const typingLabel=computed(()=>Object.values(typingNames.value).join(', '))
const initials=name=>String(name||'?').split(/\s+/).filter(Boolean).slice(-2).map(s=>s[0]).join('').toUpperCase()
const time=value=>String(value||'').slice(11,16)
const size=value=>value>=1048576?(value/1048576).toFixed(1)+' MB':Math.max(1,Math.round(value/1024))+' KB'
const id=()=>globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+'-'+Math.random().toString(36).slice(2)
const atBottom=()=>!list.value||list.value.scrollHeight-list.value.scrollTop-list.value.clientHeight<90
const focus=()=>nextTick(()=>{const el=textInput.value?.$el;(el?.matches?.('textarea')?el:el?.querySelector?.('textarea'))?.focus()})
async function bottom(){await nextTick();if(list.value)list.value.scrollTop=list.value.scrollHeight}
async function mark(){
 if(!props.active||document.hidden||!messages.value.length||!atBottom())return
 const seq=messages.value.at(-1).seq
 if(seq<=readSeq)return
 const previous=readSeq;readSeq=seq
 try{await chatAPI('mark_read',{room:selected.value,seq},true);props.client.refresh()}catch{readSeq=previous}
}
function merge(rows){const map=new Map(messages.value.map(r=>[r.name,r]));for(const row of rows)map.set(row.name,row);messages.value=[...map.values()].sort((a,b)=>a.seq-b.seq)}
async function open(room){
 if(busy.value)return
 const token=++generation;selected.value=room.name;detail.value=room;mode.value='room';messages.value=[];error.value='';draft.value='';files.value=[];sendId='';showMembers.value=false;typingNames.value={};loading.value=true;syncPending=false;readSeq=room.members?.find(m=>m.user===props.user)?.last_read_seq||0
 try{const result=await chatAPI('history',{room:room.name});if(token!==generation)return;messages.value=result.messages;detail.value=result.room;hasMore.value=result.has_more;await bottom();mark();focus()}
 catch(e){if(token===generation)error.value=e.message}
 finally{if(token===generation)loading.value=false}
}
async function sync(){
 if(mode.value!=='room'||!props.active||syncPending||loading.value||document.hidden)return
 const token=generation,room=selected.value,scroll=atBottom();syncPending=true
 try{
  const result=await chatAPI('history',{room,after:messages.value.at(-1)?.seq||0})
  if(token!==generation)return
  merge(result.messages);detail.value=result.room
  if(scroll){await bottom();mark()}
 }catch(e){if(token===generation)error.value=e.message}
 finally{if(token===generation)syncPending=false}
}
async function older(){
 if(loading.value)return
 const token=generation,height=list.value?.scrollHeight||0;loading.value=true
 try{const result=await chatAPI('history',{room:selected.value,before:messages.value[0]?.seq});if(token!==generation)return;merge(result.messages);hasMore.value=result.has_more;await nextTick();if(list.value)list.value.scrollTop+=list.value.scrollHeight-height}
 catch(e){if(token===generation)error.value=e.message}
 finally{if(token===generation)loading.value=false}
}
function back(){if(busy.value)return;generation++;mode.value='list';selected.value='';error.value='';syncPending=false;typingNames.value={}}
async function loadPeople(){
 const token=++peopleVersion
 try{const rows=await chatAPI('people',{search:search.value});if(token===peopleVersion)people.value=rows}
 catch(e){if(token===peopleVersion)error.value=e.message}
}
function start(){if(busy.value)return;mode.value='new';group.value=false;title.value='';chosen.value=[];search.value='';error.value='';loadPeople()}
async function choose(person){
 if(busy.value)return
 if(group.value){chosen.value=chosen.value.includes(person.user)?chosen.value.filter(u=>u!==person.user):[...chosen.value,person.user];return}
 await create([person.user])
}
async function create(members=chosen.value){
 if(busy.value)return
 busy.value=true;emit('busy',true);error.value=''
 try{const room=await chatAPI('create',{members,kind:group.value?'Group':'Direct',title:title.value},true);await props.client.refresh();busy.value=false;open(room)}
 catch(e){error.value=e.message}
 finally{busy.value=false;emit('busy',false)}
}
function picked(event){
 error.value=''
 for(const file of event.target.files||[]){
  if(files.value.length>=5){error.value='Mỗi lần chọn tối đa 5 tệp.';break}
  if(!file.size||file.size>20*1024*1024){error.value='Mỗi tệp phải có dữ liệu và không quá 20 MB.';continue}
  files.value.push({file,id:id(),stored:null})
 }
 event.target.value=''
}
async function send(){
 if(busy.value||(!draft.value.trim()&&!files.value.length)||!selected.value)return
 if(navigator.onLine===false){error.value='Đang mất mạng. Tin nhắn chưa được gửi.';return}
 const token=generation,room=selected.value;busy.value=true;emit('busy',true);error.value='';sendId ||=id()
 try{
  do{
   const pending=files.value[0]
   if(pending&&!pending.stored)pending.stored=await upload(pending.file)
   if(token!==generation)return
   const result=await chatAPI('send',{room,client_id:pending?.id||sendId,body:draft.value.trim(),file_url:pending?.stored?.file_url||'',file_id:pending?.stored?.name||''},true)
   if(token!==generation)return
   merge([result]);draft.value='';sendId='';if(pending)files.value.shift();await bottom()
  }while(files.value.length)
  await props.client.refresh();mark();focus()
 }catch(e){if(token===generation)error.value='Chưa gửi xong. '+e.message}
 finally{if(token===generation){busy.value=false;emit('busy',false)}}
}
function keydown(event){if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();send()}}
function typing(){
 if(Date.now()-lastTyping<3000||!draft.value.trim()||!selected.value)return
 lastTyping=Date.now();chatAPI('typing',{room:selected.value},true).catch(()=>{})
}
function seen(message){const count=(current.value?.members||[]).filter(m=>m.user!==props.user&&m.last_read_seq>=message.seq).length;return count?(current.value?.kind==='Direct'?'Đã xem':count+' người đã xem'):'Đã gửi'}
watch(search,()=>{clearTimeout(searchTimer);searchTimer=setTimeout(loadPeople,180)})
watch(draft,typing)
watch(()=>props.client.event.value,value=>{
 if(!value)return
 if(value.kind==='typing'&&value.room===selected.value&&value.user!==props.user){typingNames.value={...typingNames.value,[value.user]:value.label};clearTimeout(typingTimer);typingTimer=setTimeout(()=>typingNames.value={},6000)}
 else if(value.kind!=='typing'&&(!value.room||value.room===selected.value))sync()
})
watch(()=>props.active,active=>{if(active){props.client.refresh();sync();focus()}})
watch(()=>props.user,()=>{generation++;peopleVersion++;mode.value='list';selected.value='';detail.value=null;syncPending=false;typingNames.value={};draft.value='';files.value=[];messages.value=[];people.value=[];chosen.value=[];busy.value=false;emit('busy',false)},{flush:'sync'})
onBeforeUnmount(()=>{generation++;peopleVersion++;clearTimeout(searchTimer);clearTimeout(typingTimer)})
</script>

<template>
 <div class="lotus-chat" :class="{'is-mobile':mobile}" :aria-busy="busy" :data-realtime="client.connected?.value?'connected':'fallback'">
  <template v-if="mode==='list'">
   <div class="lotus-chat__toolbar"><strong>Tin nhắn</strong><component :is="Action" :variant="primary" class="lotus-chat__new" aria-label="Cuộc trò chuyện mới" @click="start"><LotusIcon name="plus"/>Chat mới</component></div>
   <p v-if="client.error.value" class="lotus-chat__error" role="alert">{{client.error.value}} <component :is="Action" :variant="neutral" @click="client.refresh">Thử lại</component></p>
   <div class="lotus-chat__rooms">
    <p v-if="client.loading.value" class="lotus-chat__empty" role="status">Đang tải tin nhắn…</p>
    <p v-else-if="!rooms.length" class="lotus-chat__empty">Chưa có cuộc trò chuyện. Chọn Chat mới để nhắn riêng hoặc tạo nhóm.</p>
    <component :is="Action" v-for="room in rooms" :key="room.name" :variant="neutral" class="lotus-chat__room" :aria-label="'Mở chat '+room.title" @click="open(room)">
     <span class="lotus-chat__avatar" :class="{'is-group':room.kind==='Group'}"><LotusIcon v-if="room.kind==='Group'" name="users"/><template v-else>{{initials(room.title)}}</template><i v-if="room.kind==='Direct'&&room.members.some(m=>m.user!==user&&m.online)" class="lotus-chat__online" aria-label="Đang online"/></span>
     <span class="lotus-chat__room-text"><strong>{{room.title}}</strong><small>{{room.preview||'Bắt đầu trò chuyện'}}</small></span>
     <span class="lotus-chat__room-meta"><small>{{time(room.last_activity)}}</small><b v-if="room.unread" class="lotus-chat__count">{{room.unread>99?'99+':room.unread}}</b></span>
    </component>
   </div>
  </template>
  <template v-else-if="mode==='new'">
   <div class="lotus-chat__toolbar"><Tooltip content="Quay lại"><component :is="Action" :variant="neutral" :disabled="busy" aria-label="Quay lại danh sách chat" @click="back"><LotusIcon name="arrow-left"/></component></Tooltip><strong>Cuộc trò chuyện mới</strong></div>
   <div class="lotus-chat__new-form">
    <div class="lotus-chat__switch" role="group" aria-label="Loại cuộc trò chuyện"><component :is="Action" :variant="!group?primary:neutral" :aria-pressed="!group" :disabled="busy" @click="group=false;chosen=[]">Chat riêng</component><component :is="Action" :variant="group?primary:neutral" :aria-pressed="group" :disabled="busy" @click="group=true;chosen=[]">Tạo nhóm</component></div>
    <template v-if="group"><LotusMobileInput v-if="mobile" v-model="title" label="Tên nhóm" maxlength="80" :disabled="busy"/><FormField v-else label="Tên nhóm" v-slot="f"><Input v-bind="f" v-model="title" maxlength="80" :disabled="busy"/></FormField></template>
    <LotusMobileInput v-if="mobile" v-model="search" label="Tìm người" placeholder="Tên hoặc tài khoản…" :disabled="busy"/><FormField v-else label="Tìm người" v-slot="f"><Input v-bind="f" v-model="search" placeholder="Tên hoặc tài khoản…" :disabled="busy"/></FormField>
   </div>
   <div class="lotus-chat__people">
    <component :is="Action" v-for="person in people" :key="person.user" :variant="neutral" class="lotus-chat__person" :aria-label="'Chọn '+person.label" :aria-pressed="chosen.includes(person.user)" :disabled="busy" @click="choose(person)"><span class="lotus-chat__avatar">{{initials(person.label)}}<i v-if="person.online" class="lotus-chat__online"/></span><span class="lotus-chat__room-text"><strong>{{person.label}}</strong><small>{{person.user}}</small></span><LotusIcon v-if="chosen.includes(person.user)" name="check"/></component>
    <p v-if="!people.length" class="lotus-chat__empty">Không tìm thấy tài khoản phù hợp.</p>
   </div>
   <div v-if="group" class="lotus-chat__create"><component :is="Action" :variant="primary" :disabled="busy||!title.trim()||!chosen.length" @click="create()">Tạo nhóm · {{chosen.length+1}} thành viên</component></div>
  </template>
  <template v-else>
   <div class="lotus-chat__toolbar lotus-chat__conversation-head"><Tooltip content="Quay lại"><component :is="Action" :variant="neutral" :disabled="busy" aria-label="Quay lại danh sách chat" @click="back"><LotusIcon name="arrow-left"/></component></Tooltip><div class="lotus-chat__heading"><strong>{{current?.title}}</strong><small v-if="current?.kind==='Direct'">{{current?.members.some(m=>m.user!==user&&m.online)?'Đang online':'Ngoại tuyến'}}</small><small v-else>{{current?.members.length}} thành viên</small></div><Tooltip content="Thành viên"><component :is="Action" :variant="neutral" aria-label="Xem thành viên" :aria-expanded="showMembers" @click="showMembers=!showMembers"><LotusIcon name="users"/></component></Tooltip></div>
   <div v-if="showMembers" class="lotus-chat__members"><span v-for="member in current?.members" :key="member.user">{{member.label}}{{member.user===user?' (Bạn)':''}}<small>{{member.online?' · Online':''}}</small></span></div>
   <div ref="list" class="lotus-chat__messages" role="log" aria-label="Tin nhắn hội thoại" aria-live="polite" @scroll.passive="mark">
    <component :is="Action" v-if="hasMore" :variant="neutral" :disabled="loading" class="lotus-chat__older" @click="older">Xem tin cũ hơn</component>
    <p v-if="loading" class="lotus-chat__empty" role="status">Đang tải…</p>
    <p v-else-if="!messages.length" class="lotus-chat__empty">Gửi tin nhắn đầu tiên.</p>
    <template v-for="(message,index) in messages" :key="message.name">
     <span v-if="!index||message.creation.slice(0,10)!==messages[index-1].creation.slice(0,10)" class="lotus-chat__date">{{message.creation.slice(0,10).split('-').reverse().join('/')}}</span>
     <article class="lotus-chat__message" :class="{'is-mine':message.sender===user}">
      <small v-if="message.sender!==user&&current?.kind==='Group'" class="lotus-chat__sender">{{message.sender_name}}</small>
      <div class="lotus-chat__bubble"><p v-if="message.body">{{message.body}}</p><a v-if="message.file" :href="message.file.url" target="_blank" rel="noopener" class="lotus-chat__file" :aria-label="'Tải '+message.file.name"><img v-if="message.file.image" :src="message.file.preview_url" :alt="message.file.name" loading="lazy" @load="atBottom()&&bottom()"/><span><LotusIcon name="download"/><span>{{message.file.name}}<small>{{size(message.file.size)}}</small></span></span></a><small class="lotus-chat__time">{{time(message.creation)}}</small></div>
      <small v-if="message.sender===user&&message.name===messages.filter(m=>m.sender===user).at(-1)?.name" class="lotus-chat__seen">{{seen(message)}}</small>
     </article>
    </template>
   </div>
   <small v-if="typingLabel" class="lotus-chat__typing">{{typingLabel}} đang nhập…</small>
   <div v-if="files.length" class="lotus-chat__attachments"><span v-for="(item,index) in files" :key="item.id">{{item.file.name}}<component :is="Action" :variant="neutral" :disabled="busy" :aria-label="'Bỏ tệp '+item.file.name" @click="files.splice(index,1)"><LotusIcon name="x"/></component></span></div>
   <form class="lotus-chat__form" @submit.prevent="send">
    <input ref="fileInput" type="file" multiple hidden aria-label="Chọn tệp gửi chat" @change="picked"/>
    <Tooltip content="Gửi ảnh hoặc tệp, tối đa 20 MB/tệp"><component :is="Action" :variant="neutral" :disabled="busy" aria-label="Gửi tệp" @click="fileInput.click()"><LotusIcon name="paperclip"/></component></Tooltip>
    <LotusMobileInput v-if="mobile" ref="textInput" v-model="draft" type="textarea" rows="1" maxlength="6000" aria-label="Tin nhắn" placeholder="Nhập tin nhắn…" :disabled="busy" @keydown="keydown"/>
    <Textarea v-else ref="textInput" v-model="draft" rows="1" maxlength="6000" aria-label="Tin nhắn" placeholder="Nhập tin nhắn…" :disabled="busy" @keydown="keydown"/>
    <Tooltip content="Gửi tin nhắn"><component :is="Action" :variant="primary" type="submit" :disabled="busy||(!draft.trim()&&!files.length)" aria-label="Gửi tin nhắn"><LotusIcon name="send"/></component></Tooltip>
   </form>
   <small v-if="busy" class="lotus-chat__sending" role="status">Đang gửi…</small>
  </template>
  <p v-if="error" class="lotus-chat__error" role="alert">{{error}}</p>
 </div>
</template>

<style>
.lotus-chat{display:flex;flex:1;flex-direction:column;min-height:0;min-width:0;font-size:var(--lotus-text-base);color:var(--lotus-text);background:var(--lotus-page)}
.lotus-chat button{font:inherit}.lotus-chat__toolbar{display:flex;align-items:center;gap:var(--lotus-space-2);padding:var(--lotus-space-2) var(--lotus-space-3);background:var(--lotus-surface);border-bottom:1px solid var(--lotus-border);flex:none}
.lotus-chat__toolbar>strong{flex:1}.lotus-chat__new{margin-left:auto}.lotus-chat__rooms,.lotus-chat__people{flex:1;min-height:0;overflow:auto;overscroll-behavior:contain}
.lotus-chat__room,.lotus-chat__person{display:flex!important;align-items:center;justify-content:flex-start!important;gap:var(--lotus-space-3);width:100%;max-width:100%;height:auto!important;min-height:72px;padding:var(--lotus-space-3)!important;border:0;border-bottom:1px solid var(--lotus-border);border-radius:0!important;background:var(--lotus-surface);text-align:left;color:var(--lotus-text)}
.lotus-chat__person[aria-pressed=true]{background:var(--lotus-primary-subtle)}.lotus-chat__room .van-button__content,.lotus-chat__person .van-button__content{width:100%;min-width:0}.lotus-chat__room .van-button__text,.lotus-chat__person .van-button__text{display:flex;align-items:center;gap:var(--lotus-space-3);width:100%;min-width:0;text-align:left}
.lotus-chat__avatar{display:grid;place-items:center;position:relative;flex:none;width:42px;height:42px;border-radius:50%;background:var(--lotus-primary-subtle);color:var(--lotus-primary);font-size:var(--lotus-text-md);font-weight:700}
.lotus-chat__avatar.is-group{background:var(--lotus-hover)}.lotus-chat__online{position:absolute;bottom:0;right:0;width:10px;height:10px;border-radius:50%;background:var(--lotus-success);border:2px solid var(--lotus-surface)}
.lotus-chat__room-text{display:flex;flex:1;flex-direction:column;min-width:0;gap:var(--lotus-space-1)}.lotus-chat__room-text strong,.lotus-chat__room-text small{overflow:hidden;white-space:nowrap;text-overflow:ellipsis;display:block}.lotus-chat__room-text small{color:var(--lotus-muted);font-size:var(--lotus-text-sm);font-weight:400}
.lotus-chat__room-meta{display:flex;align-items:flex-end;flex-direction:column;gap:var(--lotus-space-1);color:var(--lotus-muted);font-size:var(--lotus-text-xs)}.lotus-chat__count{min-width:20px;padding:0 var(--lotus-space-1);border-radius:var(--lotus-radius-lg);background:var(--lotus-primary);color:var(--lotus-on-primary);text-align:center;line-height:20px}
.lotus-chat__new-form{padding:var(--lotus-space-3);display:grid;gap:var(--lotus-space-3);background:var(--lotus-surface)}.lotus-chat__switch{display:flex;gap:var(--lotus-space-2)}.lotus-chat__create{padding:var(--lotus-space-3);background:var(--lotus-surface)}.lotus-chat__create>button{width:100%}
.lotus-chat__heading{display:flex;flex:1;flex-direction:column;min-width:0}.lotus-chat__heading strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.lotus-chat__heading small,.lotus-chat__members small{font-size:var(--lotus-text-xs);color:var(--lotus-muted)}
.lotus-chat__members{display:flex;flex-wrap:wrap;gap:var(--lotus-space-2);padding:var(--lotus-space-2) var(--lotus-space-3);max-height:100px;overflow:auto;background:var(--lotus-surface);font-size:var(--lotus-text-sm)}
.lotus-chat__messages{display:flex;flex-direction:column;gap:var(--lotus-space-2);flex:1;min-height:0;overflow:auto;overscroll-behavior:contain;padding:var(--lotus-space-3)}.lotus-chat__date{align-self:center;color:var(--lotus-muted);font-size:var(--lotus-text-xs);padding:var(--lotus-space-2)}
.lotus-chat__message{display:flex;flex-direction:column;align-items:flex-start;align-self:flex-start;max-width:88%;min-width:0;gap:var(--lotus-space-1)}.lotus-chat__message.is-mine{align-self:flex-end;align-items:flex-end}.lotus-chat__sender,.lotus-chat__seen{font-size:var(--lotus-text-xs);color:var(--lotus-muted)}
.lotus-chat__bubble{max-width:100%;min-width:0;padding:var(--lotus-space-2) var(--lotus-space-3);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-lg);background:var(--lotus-surface);overflow-wrap:anywhere}.lotus-chat__bubble p{margin:0;white-space:pre-wrap;line-height:1.5}.lotus-chat__message.is-mine .lotus-chat__bubble{background:var(--lotus-primary-subtle);border-color:var(--lotus-primary-subtle)}
.lotus-chat__time{display:block;text-align:right;font-size:var(--lotus-text-xs);color:var(--lotus-muted);margin-top:var(--lotus-space-1)}.lotus-chat__file{display:block;max-width:100%;color:var(--lotus-primary-text);text-decoration:none}.lotus-chat__file>span{display:flex;gap:var(--lotus-space-2);align-items:center;font-weight:600;padding:var(--lotus-space-1) 0}.lotus-chat__file>span>span{min-width:0;overflow-wrap:anywhere}.lotus-chat__file small{display:block;font-weight:400;font-size:var(--lotus-text-xs);color:var(--lotus-muted)}.lotus-chat__file img{display:block;width:auto;max-width:100%;max-height:220px;border-radius:var(--lotus-radius-md);margin-bottom:var(--lotus-space-1)}
.lotus-chat__typing,.lotus-chat__sending{padding:var(--lotus-space-1) var(--lotus-space-3);color:var(--lotus-muted);font-size:var(--lotus-text-sm)}.lotus-chat__empty{padding:var(--lotus-space-6);margin:0;color:var(--lotus-muted);font-size:var(--lotus-text-md);text-align:center;line-height:1.5}
.lotus-chat__error{padding:var(--lotus-space-2) var(--lotus-space-3);margin:0;color:var(--lotus-danger);font-size:var(--lotus-text-md);background:var(--lotus-surface);flex:none}
.lotus-chat__form{display:flex;align-items:flex-end;gap:var(--lotus-space-2);padding:var(--lotus-space-2);border-top:1px solid var(--lotus-border);background:var(--lotus-surface);flex:none}.lotus-chat__form>button{display:grid;place-items:center;min-width:var(--lotus-touch);height:var(--lotus-touch);padding:var(--lotus-space-2);border-radius:var(--lotus-radius-lg);flex:none}.lotus-chat__form textarea{min-height:var(--lotus-touch);max-height:120px;resize:none}.lotus-chat__form .lotus-pwa-field{flex:1;min-width:0;padding:var(--lotus-space-2);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-lg)}
.lotus-chat__attachments{display:flex;flex-wrap:wrap;gap:var(--lotus-space-1);padding:var(--lotus-space-2);max-height:100px;overflow:auto;background:var(--lotus-surface);font-size:var(--lotus-text-sm)}.lotus-chat__attachments>span{display:flex;align-items:center;min-width:0;max-width:100%;overflow-wrap:anywhere;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);padding-left:var(--lotus-space-2)}.lotus-chat__attachments button{padding:var(--lotus-space-1);flex:none}
.lotus-chat.is-mobile button{min-height:var(--lotus-touch)}.lotus-chat.is-mobile textarea{font-size:var(--lotus-text-lg)}.lotus-chat__toolbar .lotus-icon,.lotus-chat__form .lotus-icon{flex:none}.lotus-chat.is-mobile .lotus-chat__form .van-button__text{display:grid;place-items:center}
.lotus-chat-tabs{display:flex;gap:var(--lotus-space-1);padding:var(--lotus-space-2) var(--lotus-space-3);border-bottom:1px solid var(--lotus-border);background:var(--lotus-surface);flex:none}.lotus-chat-tabs button{display:flex;align-items:center;justify-content:center;gap:var(--lotus-space-2);flex:1;min-height:36px;border:0;border-radius:var(--lotus-radius-md);font:inherit;font-size:var(--lotus-text-md);font-weight:600;background:transparent;color:var(--lotus-muted);cursor:pointer}.lotus-chat-tabs button[aria-selected=true]{background:var(--lotus-primary-subtle);color:var(--lotus-primary)}.lotus-chat-tabs b{padding:0 var(--lotus-space-1);border-radius:var(--lotus-radius-md);background:var(--lotus-primary);color:var(--lotus-on-primary);font-size:var(--lotus-text-xs)}
.lotus-chat-badge{display:grid;place-items:center;position:absolute;top:-4px;right:-4px;min-width:20px;height:20px;padding:0 var(--lotus-space-1);border-radius:var(--lotus-radius-lg);background:var(--lotus-danger);color:var(--lotus-on-primary);font-size:var(--lotus-text-xs);border:2px solid var(--lotus-surface)}
</style>
