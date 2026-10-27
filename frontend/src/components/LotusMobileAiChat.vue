<script setup>
import {nextTick,onBeforeUnmount,onMounted,ref,watch} from 'vue'
import {Button,Field,Icon,Popup} from 'vant'
import {call} from '../api'
import {renderMarkdown} from '../ai-markdown'
import {useChatConnection} from '../chat-client'
import InternalChat from './InternalChat.vue'

// The same component is mounted by LotusMobileShell in every phone app.
// It calls the existing read-only, permission-aware Lotus AI endpoint.
const props=defineProps({
 user:{type:String,default:''},
 pushApp:{type:String,default:''},
 disabled:{type:Boolean,default:false},
 keyboardOpen:{type:Boolean,default:false}
})
const show=ref(false),draft=ref(''),busy=ref(false),error=ref('')
const chat=useChatConnection(()=>props.user),tab=ref('ai'),chatBusy=ref(false)
const messages=ref([]),list=ref(null),input=ref(null),trigger=ref(null)
const online=ref(typeof navigator==='undefined'?true:navigator.onLine)
const popupStyle=ref({height:'min(84dvh,740px)'})
let requestId=0

const key=()=> 'lotus-ai-chat|'+props.user
function load(){
 try{
  const stored=JSON.parse(window.sessionStorage.getItem(key())||'[]')
  return Array.isArray(stored)?stored.filter(m=>m&&['user','assistant'].includes(m.role)&&typeof m.content==='string')
   .slice(-30).map(m=>({role:m.role,content:m.content,steps:Array.isArray(m.steps)?m.steps:[]})):[]
 }catch{return []}
}
messages.value=load()
watch(messages,rows=>{
 if(!props.user)return
 try{window.sessionStorage.setItem(key(),JSON.stringify(rows.slice(-30)))}catch{}
},{deep:true,flush:'sync'})
watch(()=>props.user,()=>{
 requestId++;messages.value=load();draft.value='';error.value='';busy.value=false;show.value=false;tab.value='ai';chatBusy.value=false
},{flush:'sync'})
onBeforeUnmount(()=>{requestId++})

const suggestions=['Tồn kho hiện tại ở các kho là bao nhiêu?','Đơn mua nào đang chờ nhận hàng?','Hôm nay có bao nhiêu nhân viên đi làm?']
const sources=steps=>[...new Set((steps||[]).filter(s=>s&&!s.error&&s.tool!=='search_doctypes'&&s.doctype).map(s=>s.doctype))].join(' · ')
function updateOnline(){online.value=navigator.onLine}
// Follow the usable viewport when the soft keyboard covers part of the screen.
function updateViewport(){
 const view=window.visualViewport
 if(!view)return
 popupStyle.value={height:Math.max(160,Math.min(740,Math.floor(view.height-12)))+'px',
  bottom:Math.max(0,Math.round(window.innerHeight-view.offsetTop-view.height))+'px'}
}
onMounted(()=>{
 window.addEventListener('online',updateOnline);window.addEventListener('offline',updateOnline)
 window.visualViewport?.addEventListener?.('resize',updateViewport)
 window.visualViewport?.addEventListener?.('scroll',updateViewport)
 updateViewport()
 const url=new URL(window.location.href)
 if(url.searchParams.get('chat')==='1'){
  show.value=true;tab.value='chat'
  url.searchParams.delete('chat')
  window.history.replaceState(window.history.state,'',url.pathname+url.search+url.hash)
 }
})
onBeforeUnmount(()=>{
 window.removeEventListener('online',updateOnline);window.removeEventListener('offline',updateOnline)
 window.visualViewport?.removeEventListener?.('resize',updateViewport)
 window.visualViewport?.removeEventListener?.('scroll',updateViewport)
})
async function scrollToBottom(){await nextTick();if(list.value)list.value.scrollTop=list.value.scrollHeight}
function focusInput(){nextTick(()=>input.value?.$el?.querySelector('textarea')?.focus())}
watch(show,async opened=>{
 if(opened){await scrollToBottom();focusInput()}
 else nextTick(()=>trigger.value?.$el?.focus())
})
function reset(){if(busy.value)return;messages.value=[];draft.value='';error.value='';focusInput()}
function keydown(event){
 if(event.key==='Escape'){show.value=false;return}
 if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){
  event.preventDefault();send()
 }
}
async function send(text){
 const question=String(text??draft.value).trim()
 if(!question||question.length>4000||busy.value||!props.user)return
 if(!online.value){error.value='Đang mất mạng. Hãy kết nối rồi gửi lại.';return}
 const id=++requestId
 const before=messages.value.slice()
 draft.value='';error.value=''
 messages.value=[...before,{role:'user',content:question}].slice(-30)
 busy.value=true
 scrollToBottom()
 try{
  const response=await call('lotus_farm.ai_chat.ask',{
   messages:messages.value.slice(-12).map(({role,content})=>({role,content}))
  },true)
  if(id!==requestId)return
  messages.value=[...messages.value,{role:'assistant',content:String(response?.answer||'Chưa tìm được câu trả lời.'),steps:Array.isArray(response?.steps)?response.steps:[]}].slice(-30)
 }catch(e){
  if(id!==requestId)return
  messages.value=before
  draft.value=question
  error.value=e.code==='AuthenticationError'?'Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.':
   'Chưa nhận được câu trả lời. '+(e.message||'Thử lại sau.')
 }finally{
  if(id===requestId){busy.value=false;scrollToBottom()}
 }
}
</script>

<template>
 <div v-if="user&&user!=='Guest'" class="lotus-mobile-ai">
  <Button v-show="!keyboardOpen&&!show" ref="trigger" class="lotus-mobile-ai__fab" type="primary"
   icon="chat-o" aria-label="Hỏi trợ lý Lotus AI" :disabled="disabled" @click="show=true">AI · Chat<b v-if="chat.unread.value" class="lotus-chat-badge">{{chat.unread.value>99?'99+':chat.unread.value}}</b></Button>
  <Popup v-model:show="show" teleport="body" position="bottom" round :close-on-click-overlay="!busy&&!chatBusy"
   class="lotus-mobile-ai__popup" :style="popupStyle">
   <section class="lotus-mobile-ai__panel" role="dialog" aria-modal="true" aria-label="Trợ lý Lotus AI" @keydown.esc.stop="!chatBusy&&(show=false)">
    <header class="lotus-mobile-ai__header">
     <span class="lotus-mobile-ai__mark"><Icon name="chat-o" size="22"/></span>
     <div class="lotus-mobile-ai__heading"><strong>{{tab==='ai'?'Trợ lý Lotus AI':'Lotus Chat'}}</strong><small>{{tab==='ai'?'Đọc dữ liệu theo quyền tài khoản':'Chat riêng và nhóm'}}</small></div>
     <Button v-if="messages.length&&tab==='ai'" plain icon="replay" size="small" :disabled="busy"
      aria-label="Cuộc hỏi mới" @click="reset"/>
     <Button plain icon="cross" size="small" aria-label="Đóng trợ lý AI" :disabled="chatBusy" @click="show=false"/>
    </header>
    <div class="lotus-chat-tabs" role="tablist" aria-label="Trợ lý và tin nhắn"><Button role="tab" :aria-selected="tab==='ai'" :disabled="chatBusy" @click="tab='ai'">Trợ lý AI</Button><Button role="tab" :aria-selected="tab==='chat'" @click="tab='chat'">Tin nhắn<b v-if="chat.unread.value">{{chat.unread.value>99?'99+':chat.unread.value}}</b></Button></div>
    <InternalChat v-show="tab==='chat'" :user="user" :client="chat" :active="show&&tab==='chat'" :push-app="pushApp" mobile @busy="chatBusy=$event"/>
    <div v-show="tab==='ai'" class="lotus-mobile-ai__ai">
    <div ref="list" class="lotus-mobile-ai__messages" aria-live="polite">
     <div v-if="!messages.length" class="lotus-mobile-ai__welcome">
      <p>Hỏi về kho, đơn mua, nhân sự, dự thu… AI sẽ tra cứu số liệu bạn được phép xem.</p>
      <Button v-for="s in suggestions" :key="s" class="lotus-mobile-ai__suggestion" plain block
       :disabled="busy" @click="send(s)">{{s}}</Button>
     </div>
     <article v-for="(m,i) in messages" :key="i" class="lotus-mobile-ai__message"
      :class="'is-'+m.role">
      <div v-if="m.role==='assistant'" class="lotus-mobile-ai__bubble ai-md" v-html="renderMarkdown(m.content)"></div>
      <div v-else class="lotus-mobile-ai__bubble">{{m.content}}</div>
      <small v-if="m.role==='assistant'&&sources(m.steps)" class="lotus-mobile-ai__source">Đã tra: {{sources(m.steps)}}</small>
     </article>
     <p v-if="busy" class="lotus-mobile-ai__waiting" role="status"><Icon name="clock-o"/> Đang tra cứu dữ liệu…</p>
     <p v-if="error" class="lotus-mobile-ai__error" role="alert">{{error}}</p>
    </div>
    <form class="lotus-mobile-ai__form" @submit.prevent="send()">
     <Field ref="input" v-model="draft" type="textarea" rows="2" autosize maxlength="4000"
      :disabled="busy" placeholder="Nhập câu hỏi về dữ liệu Lotus…" aria-label="Câu hỏi cho trợ lý AI"
      class="lotus-mobile-ai__input" @keydown="keydown"/>
     <Button native-type="submit" type="primary" icon="guide-o" class="lotus-mobile-ai__send"
      aria-label="Gửi câu hỏi" :disabled="busy||!draft.trim()||!online"/>
    </form>
    <p v-if="!online" class="lotus-mobile-ai__offline">Không có mạng, chưa thể gửi câu hỏi.</p>
    </div>
   </section>
  </Popup>
 </div>
</template>

<style>
.lotus-mobile-ai__ai{display:flex;flex:1;flex-direction:column;min-height:0}.lotus-mobile-ai .lotus-chat-tabs .van-button{height:auto;border:0}.lotus-mobile-ai__popup .lotus-chat-tabs .van-button{height:auto;border:0;min-height:var(--lotus-touch)}.lotus-mobile-ai__fab.van-button{overflow:visible}
.lotus-mobile-ai__fab.van-button{position:fixed;right:max(14px,calc((100vw - var(--lotus-pwa-width))/2 + 14px));bottom:calc(76px + env(safe-area-inset-bottom));z-index:75;min-height:52px;min-width:88px;padding:0 14px;border-radius:28px;box-shadow:var(--lotus-shadow-lg);font-weight:700;gap:6px}
.lotus-mobile-ai__popup.van-popup{max-width:600px;left:50%;transform:translateX(-50%);background:var(--lotus-surface);color:var(--lotus-text);font-family:var(--lotus-font);overflow:hidden}
.lotus-mobile-ai__panel{display:flex;flex-direction:column;height:100%;min-height:0}
.lotus-mobile-ai__header{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid var(--lotus-border);flex:none}
.lotus-mobile-ai__mark{display:grid;place-items:center;width:40px;height:40px;flex:none;background:var(--lotus-primary-subtle);color:var(--lotus-primary);border-radius:12px}
.lotus-mobile-ai__heading{display:flex;flex-direction:column;min-width:0;flex:1;line-height:1.4}
.lotus-mobile-ai__heading strong{font-size:16px}.lotus-mobile-ai__heading small{font-size:11px;color:var(--lotus-muted)}
.lotus-mobile-ai__header .van-button{min-width:44px;min-height:44px;flex:none;padding:0;border-color:transparent;color:var(--lotus-text)}
.lotus-mobile-ai__messages{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain;display:flex;flex-direction:column;gap:12px;padding:16px;background:var(--lotus-page)}
.lotus-mobile-ai__welcome p{font-size:14px;color:var(--lotus-muted);margin:0 0 14px;line-height:1.55}
.lotus-mobile-ai__suggestion.van-button{min-height:48px;height:auto;text-align:left;white-space:normal;justify-content:flex-start;padding:10px 12px;margin-bottom:9px;border-color:var(--lotus-border);border-radius:12px;background:var(--lotus-surface);color:var(--lotus-text)}
.lotus-mobile-ai__suggestion .van-button__content,.lotus-mobile-ai__suggestion .van-button__text{white-space:normal;text-align:left;line-height:1.4}
.lotus-mobile-ai__message{display:flex;flex-direction:column;gap:5px;max-width:95%;min-width:0;align-self:flex-start}
.lotus-mobile-ai__message.is-user{align-self:flex-end;align-items:flex-end}
.lotus-mobile-ai__bubble{max-width:100%;min-width:0;padding:10px 12px;border:1px solid var(--lotus-border);border-radius:14px;background:var(--lotus-surface);font-size:14px;line-height:1.55;overflow-wrap:anywhere;white-space:pre-wrap}
.lotus-mobile-ai__message.is-user .lotus-mobile-ai__bubble{background:var(--lotus-primary-600);color:#fff;border-color:var(--lotus-primary-600);border-bottom-right-radius:4px}
.lotus-mobile-ai__source{font-size:11px;color:var(--lotus-muted);padding:0 4px}
.lotus-mobile-ai__waiting{font-size:13px;color:var(--lotus-muted)}
.lotus-mobile-ai__error{margin:0;padding:10px;border-radius:10px;background:var(--lotus-primary-subtle);color:var(--lotus-primary);font-size:13px}
.lotus-mobile-ai__form{display:flex;gap:8px;align-items:flex-end;padding:10px 12px 8px;background:var(--lotus-surface);border-top:1px solid var(--lotus-border);flex:none}
.lotus-mobile-ai__input.van-cell{min-width:0;flex:1;overflow:hidden;border:1px solid var(--lotus-border);border-radius:12px;padding:10px;font-size:16px}
.lotus-mobile-ai__input .van-field__control{font-size:16px;max-height:130px;overflow-y:auto}
.lotus-mobile-ai__send.van-button{width:48px;min-width:48px;height:48px;border-radius:12px;flex:none}
.lotus-mobile-ai__offline{padding:0 12px 8px;margin:0;color:var(--lotus-muted);font-size:12px}
.lotus-mobile-ai__panel .ai-md p{margin:0 0 8px}.lotus-mobile-ai__panel .ai-md p:last-child{margin:0}
.lotus-mobile-ai__panel .ai-md .ai-md-heading{font-weight:700}
.lotus-mobile-ai__panel .ai-md ul,.lotus-mobile-ai__panel .ai-md ol{padding-left:20px;margin:0 0 8px;list-style:revert}
.lotus-mobile-ai__panel .ai-md code{background:var(--lotus-soft);padding:1px 4px;border-radius:5px}
.lotus-mobile-ai__panel .ai-md-table{max-width:100%;overflow-x:auto;border:1px solid var(--lotus-border);border-radius:8px;margin:6px 0}
.lotus-mobile-ai__panel .ai-md table{border-collapse:collapse;font-size:12px}
.lotus-mobile-ai__panel .ai-md th,.lotus-mobile-ai__panel .ai-md td{padding:6px;border-bottom:1px solid var(--lotus-border);white-space:nowrap;text-align:left}
.lotus-mobile-ai__panel .ai-md th{background:var(--lotus-soft)}.lotus-mobile-ai__panel .ai-md td.num{text-align:right}
@media(max-width:360px){.lotus-mobile-ai__header{padding:10px 8px;gap:5px}.lotus-mobile-ai__heading strong{font-size:14px}.lotus-mobile-ai__heading small{font-size:10px}.lotus-mobile-ai__messages{padding:10px}.lotus-mobile-ai__fab.van-button{right:10px}}
@media(prefers-reduced-motion:reduce){.lotus-mobile-ai__popup *{animation:none!important;transition:none!important}}
</style>
