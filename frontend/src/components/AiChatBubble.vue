<script setup>
import {nextTick,onBeforeUnmount,ref,watch} from 'vue'
import {call} from '../api'
import {Button as UiButton} from './ui/button'
import {Tooltip} from './ui/tooltip'
import {Textarea} from './ui/textarea'
import LotusIcon from './LotusIcon.vue'
import {renderMarkdown} from '../ai-markdown'
// Bong bóng "Trợ lý Lotus AI": hỏi đáp dữ liệu. The server reads data only, with the signed-in user's permissions.
// The conversation is kept for this browser tab only (sessionStorage).
const props=defineProps({user:{type:String,default:''}})
const open=ref(false),draft=ref(''),busy=ref(false),error=ref(''),list=ref(null),input=ref(null),fab=ref(null)
let requestId=0
const storageKey=()=>'lotus-ai-chat|'+props.user
const load=()=>{try{const value=JSON.parse(window.sessionStorage.getItem(storageKey())||'[]');return Array.isArray(value)?value.filter(m=>m&&['user','assistant'].includes(m.role)&&typeof m.content==='string').slice(-30).map(m=>({...m,steps:Array.isArray(m.steps)?m.steps:[]})):[]}catch{return []}}
const messages=ref(load())
watch(messages,value=>{try{window.sessionStorage.setItem(storageKey(),JSON.stringify(value.slice(-30)))}catch{}},{deep:true,flush:'sync'})
watch(()=>props.user,()=>{requestId++;messages.value=load();draft.value='';error.value='';busy.value=false;open.value=false},{flush:'sync'})
onBeforeUnmount(()=>{requestId++})
const suggestions=['Tồn kho hiện tại ở từng kho, vật tư nào sắp hết?','Chi phí tháng này theo tài khoản là bao nhiêu?','Có bao nhiêu nhân viên đang làm việc ở mỗi vườn?','Đơn mua nào đang chờ nhận hàng?']
async function scroll(){await nextTick();if(list.value)list.value.scrollTop=list.value.scrollHeight}
async function send(text){
 const question=String(text??draft.value).trim()
 if(!question||question.length>4000||busy.value)return
 const id=++requestId
 draft.value='';error.value=''
 messages.value=[...messages.value,{role:'user',content:question}].slice(-30)
 busy.value=true;scroll()
 try{
  const result=await call('lotus_farm.ai_chat.ask',{messages:messages.value.slice(-12).map(({role,content})=>({role,content}))},true)
  if(id!==requestId)return
  messages.value=[...messages.value,{role:'assistant',content:String(result?.answer||'Chưa có câu trả lời; hãy thử lại.'),steps:Array.isArray(result?.steps)?result.steps:[]}].slice(-30)
 }catch(e){if(id===requestId){error.value=e.code==='AuthenticationError'?'Phiên đăng nhập đã hết; hãy đăng nhập lại.':'Chưa nhận được câu trả lời. '+e.message;draft.value=question}}
 finally{if(id===requestId){busy.value=false;scroll();await nextTick();input.value?.$el?.focus()}}
}
function keydown(event){if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();send()}}
function reset(){if(busy.value)return;messages.value=[];error.value=''}
function close(){open.value=false;nextTick(()=>fab.value?.$el?.focus())}
const stepText=steps=>[...new Set((steps||[]).filter(s=>s&&!s.error&&s.tool!=='search_doctypes'&&s.doctype).map(s=>s.doctype))].join(' · ')
watch(open,async value=>{if(value){await scroll();input.value?.$el?.focus()}})
</script>
<template>
 <div class="ai-chat" :class="{'is-open':open}">
  <section v-if="open" class="ai-chat__panel" role="dialog" aria-label="Trợ lý Lotus AI" @keydown.esc.stop="close">
   <header class="ai-chat__head">
    <span class="ai-chat__badge"><LotusIcon name="sparkle"/></span>
    <div><strong>Trợ lý Lotus AI</strong><small>Chỉ đọc dữ liệu, theo quyền của bạn</small></div>
    <Tooltip v-if="messages.length" content="Cuộc hỏi mới"><UiButton variant="ghost" size="icon" class="ai-chat__icon-btn" aria-label="Cuộc hỏi mới" :disabled="busy" @click="reset"><LotusIcon name="refresh"/></UiButton></Tooltip>
    <Tooltip content="Đóng trợ lý AI"><UiButton variant="ghost" size="icon" class="ai-chat__icon-btn" aria-label="Đóng trợ lý AI" @click="close"><LotusIcon name="x"/></UiButton></Tooltip>
   </header>
   <div ref="list" class="ai-chat__list" aria-live="polite">
    <div v-if="!messages.length" class="ai-chat__empty">
     <p>Hỏi bất cứ điều gì về số liệu: tồn kho, mua hàng, chi phí, nhân sự, thu hoạch… Trợ lý tự tra cứu và trả lời.</p>
     <UiButton v-for="s in suggestions" :key="s" variant="outline" class="ai-chat__chip" @click="send(s)">{{s}}</UiButton>
    </div>
    <article v-for="(m,i) in messages" :key="i" class="ai-chat__msg" :class="'is-'+m.role">
     <div v-if="m.role==='assistant'" class="ai-chat__bubble ai-md" v-html="renderMarkdown(m.content)"></div>
     <div v-else class="ai-chat__bubble">{{m.content}}</div>
     <small v-if="m.role==='assistant'&&stepText(m.steps)" class="ai-chat__source">Đã tra: {{stepText(m.steps)}}</small>
    </article>
    <div v-if="busy" class="ai-chat__msg is-assistant"><div class="ai-chat__bubble ai-chat__thinking"><span class="ai-chat__spinner" aria-hidden="true"></span>Đang tra cứu dữ liệu…</div></div>
    <p v-if="error" class="ai-chat__error" role="alert">{{error}}</p>
   </div>
   <form class="ai-chat__form" @submit.prevent="send()">
    <Textarea ref="input" v-model="draft" rows="2" maxlength="4000" placeholder="Hỏi về tồn kho, chi phí, nhân sự…" aria-label="Câu hỏi cho trợ lý AI" :disabled="busy" @keydown="keydown"/>
    <Tooltip content="Gửi câu hỏi"><UiButton type="submit" class="ai-chat__send" :disabled="busy||!draft.trim()" aria-label="Gửi câu hỏi"><LotusIcon name="send"/></UiButton></Tooltip>
   </form>
  </section>
  <UiButton ref="fab" class="ai-chat__fab" :aria-expanded="open" :aria-label="open?'Đóng trợ lý AI':'Hỏi Trợ lý Lotus AI'" :title="open?'Đóng':'Hỏi Trợ lý Lotus AI'" @click="open?close():open=true"><LotusIcon :name="open?'x':'chat'"/><span v-if="!open" class="ai-chat__fab-label">Hỏi AI</span></UiButton>
 </div>
</template>
<style>
.ai-chat{position:fixed;right:var(--lotus-space-6);bottom:var(--lotus-space-6);z-index:60;display:flex;flex-direction:column;align-items:flex-end;gap:var(--lotus-space-3);font-size:var(--lotus-text-base)}
.ai-chat__fab{display:inline-flex;align-items:center;gap:var(--lotus-space-2);height:48px;padding:0 var(--lotus-space-4);border:0;border-radius:999px;background:var(--lotus-primary);color:var(--lotus-on-primary);font:inherit;font-weight:700;box-shadow:var(--lotus-shadow-lg);cursor:pointer;transition:transform var(--lotus-motion),box-shadow var(--lotus-motion)}
.ai-chat__fab:hover{transform:translateY(-1px);box-shadow:var(--lotus-shadow-lg)}
.ai-chat__fab .lotus-icon{width:22px;height:22px}
.ai-chat.is-open .ai-chat__fab{width:48px;padding:0;justify-content:center}
.ai-chat__panel{display:flex;flex-direction:column;width:min(420px,calc(100vw - 32px));height:min(620px,calc(100dvh - 110px));border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-xl);background:var(--lotus-surface);box-shadow:var(--lotus-shadow-lg);overflow:hidden}
.ai-chat__head{display:flex;align-items:center;gap:10px;padding:12px 12px 12px 14px;border-bottom:1px solid var(--lotus-border)}
.ai-chat__head>div{display:grid;flex:1;min-width:0}
.ai-chat__head strong{font-size:15px;color:var(--lotus-text-strong)}
.ai-chat__head small{color:var(--lotus-muted);font-size:12px}
.ai-chat__badge{display:grid;place-items:center;width:32px;height:32px;border-radius:10px;background:var(--lotus-primary-subtle);color:var(--lotus-primary)}
.ai-chat__badge .lotus-icon{width:18px;height:18px}
.ai-chat__icon-btn{display:grid;place-items:center;width:32px;height:32px;border:0;border-radius:8px;background:transparent;color:var(--lotus-muted);cursor:pointer}
.ai-chat__icon-btn:hover{background:var(--lotus-hover)}
.ai-chat__icon-btn .lotus-icon{width:17px;height:17px}
.ai-chat__list{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:12px;background:var(--lotus-page)}
.ai-chat__empty p{margin:0 0 10px;color:var(--lotus-muted);line-height:1.5}
.ai-chat__chip{display:block;width:100%;margin:0 0 8px;padding:9px 12px;border:1px solid var(--lotus-border);border-radius:10px;background:var(--lotus-surface);color:var(--lotus-text);font:inherit;font-size:13px;text-align:left;cursor:pointer}
.ai-chat__chip:hover{border-color:var(--lotus-primary)}
.ai-chat__msg{display:flex;flex-direction:column;gap:4px;max-width:92%;min-width:0}
.ai-chat__msg.is-user{align-self:flex-end;align-items:flex-end}
.ai-chat__msg.is-assistant{align-self:flex-start}
.ai-chat__bubble{padding:10px 12px;border-radius:14px;line-height:1.5;overflow-wrap:anywhere;white-space:pre-wrap;max-width:100%;min-width:0}
.ai-chat__msg.is-user .ai-chat__bubble{background:var(--lotus-primary);color:var(--lotus-on-primary);border-bottom-right-radius:4px}
.ai-chat__msg.is-assistant .ai-chat__bubble{background:var(--lotus-surface);color:var(--lotus-text);border:1px solid var(--lotus-border);border-bottom-left-radius:4px;white-space:normal}
.ai-chat__source{color:var(--lotus-muted);font-size:11px;padding-left:4px}
.ai-chat__thinking{display:flex;align-items:center;gap:10px;color:var(--lotus-muted)}
.ai-chat__spinner{width:16px;height:16px;border:2px solid var(--lotus-primary);border-right-color:transparent;border-radius:50%;animation:ai-chat-spin .8s linear infinite}
@keyframes ai-chat-spin{to{transform:rotate(360deg)}}
.ai-chat__error{margin:0;color:var(--lotus-danger);font-size:13px}
.ai-chat__form{display:flex;align-items:flex-end;gap:8px;padding:10px;border-top:1px solid var(--lotus-border);background:var(--lotus-surface)}
.ai-chat__form textarea{flex:1;min-height:44px;max-height:140px;resize:none;border-radius:12px}
.ai-chat__send{display:grid;place-items:center;width:44px;height:44px;flex:0 0 auto;border:0;border-radius:12px;background:var(--lotus-primary);color:var(--lotus-on-primary);cursor:pointer}
.ai-chat__send:disabled{opacity:.45;cursor:default}
.ai-chat__send .lotus-icon{width:19px;height:19px}
.ai-md p{margin:0 0 8px}.ai-md p:last-child{margin-bottom:0}
.ai-md .ai-md-heading{font-weight:700;color:var(--lotus-text-strong)}
.ai-md ul,.ai-md ol{margin:0 0 8px;padding-left:20px}
.ai-md code{padding:1px 5px;border-radius:5px;background:var(--lotus-soft);font-size:12px}
.ai-md-table{overflow-x:auto;margin:4px 0 8px;border:1px solid var(--lotus-border);border-radius:8px}
.ai-md table{width:100%;border-collapse:collapse;font-size:12.5px}
.ai-md th,.ai-md td{padding:6px 8px;border-bottom:1px solid var(--lotus-border);text-align:left;white-space:nowrap}
.ai-md th{background:var(--lotus-soft);font-weight:600}
.ai-md td.num{text-align:right;font-variant-numeric:tabular-nums}
.ai-md tr:last-child td{border-bottom:0}
@media(max-width:720px){.ai-chat{right:12px;bottom:calc(76px + env(safe-area-inset-bottom,0px))}.ai-chat__fab-label{display:none}.ai-chat__fab{width:52px;height:52px;padding:0;justify-content:center}.ai-chat__panel{width:calc(100vw - 24px);height:calc(100dvh - 164px - env(safe-area-inset-bottom,0px))}.ai-chat__icon-btn{width:var(--lotus-touch);height:var(--lotus-touch)}.ai-chat__form textarea{font-size:var(--lotus-text-lg)}}
</style>
