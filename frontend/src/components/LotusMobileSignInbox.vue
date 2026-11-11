<script setup>
// Chờ tôi ký on every Lotus phone app (spec 003, FR-011): a header button with the count, the list of documents
// waiting for me (any kind), Ký nhiều with one confirmation, and the signing sheet. A link
// /<app>?sign_dt=&sign_dn= (push alert, e-mail on a phone) opens that document's sheet directly.
import {onBeforeUnmount,onMounted,ref,watch} from 'vue'
import {Badge,Icon,Popup,Cell,Checkbox,Empty} from 'vant'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileDialog from './LotusMobileDialog.vue'
import LotusMobileSignSheet from './LotusMobileSignSheet.vue'
import {useMobileConfirm} from '../use-mobile-confirm'
import {readDeepLink,clearDeepLink} from '../mobile-deep-link'
import * as signing from '../use-signing'

const props=defineProps({online:{type:Boolean,default:true},callFn:Function})
const show=ref(false),rows=ref([]),count=ref(0),picked=ref([]),busy=ref(false),error=ref(''),failures=ref([]),sheet=ref(false),current=ref(null),notice=ref('')
const confirm=useMobileConfirm()
const key=r=>r.doctype+'::'+r.name
let timer

// Home screens show the same number and open this list (events keep the apps free of shell internals).
watch(count,value=>window.dispatchEvent(new CustomEvent('lotus-sign-count',{detail:value})))
async function refreshCount(){if(document.visibilityState!=='visible')return;try{count.value=await signing.inboxCount(props.callFn)}catch{}}
async function load(){
 busy.value=true;error.value=''
 try{const result=await signing.inbox({},props.callFn);rows.value=result?.rows||[];count.value=result?.total??rows.value.length;picked.value=picked.value.filter(k=>rows.value.some(r=>key(r)===k))}
 catch(e){error.value=e.message||String(e)}
 finally{busy.value=false}
}
async function openList(){show.value=true;failures.value=[];notice.value='';await load()}
function openRow(row){current.value=row;sheet.value=true}
function toggle(row,on){const k=key(row);picked.value=on?[...new Set([...picked.value,k])]:picked.value.filter(x=>x!==k)}
async function signPicked(){
 const list=rows.value.filter(r=>picked.value.includes(key(r)))
 if(!list.length||!await confirm.ask(signing.confirmText(list)))return
 busy.value=true;error.value=''
 try{const result=await signing.signDocuments(list,props.callFn);failures.value=(result?.results||[]).filter(r=>!r.ok);notice.value='Đã ký '+(result?.signed||0)+'/'+list.length+' chứng từ.';picked.value=[]}
 catch(e){error.value=e.message||String(e)}
 finally{busy.value=false}
 await load()
}
async function done({message}){notice.value=message;await load()}
async function openFromLink(){
 const link=readDeepLink(location.search)
 if(link?.kind!=='sign')return
 clearDeepLink()
 try{openRow({doctype:link.doctype,name:link.name,...await signing.signingApi('open_targets',{doctype:link.doctype,name:link.name},false,props.callFn)})}
 catch(e){error.value=e.message||String(e);show.value=true}
}
function visible(){if(document.visibilityState==='visible')refreshCount()}
onMounted(()=>{refreshCount();openFromLink();timer=setInterval(refreshCount,60000);document.addEventListener('visibilitychange',visible);window.addEventListener('lotus-open-sign-inbox',openList)})
onBeforeUnmount(()=>{clearInterval(timer);document.removeEventListener('visibilitychange',visible);window.removeEventListener('lotus-open-sign-inbox',openList)})
defineExpose({open:openRow,refresh:load})
</script>

<template>
 <div class="lotus-sign-inbox">
  <button type="button" class="lotus-notification-trigger" :aria-label="count?'Chờ tôi ký: '+count+' chứng từ':'Chờ tôi ký'" @click="openList">
   <Badge :content="count>99?'99+':count" :show-zero="false" :max="99"><Icon name="sign" size="24"/></Badge>
  </button>
  <Popup v-model:show="show" position="bottom" round closeable teleport="body" :style="{height:'min(86dvh,700px)'}">
   <section class="lotus-sign-inbox__panel" aria-label="Chờ tôi ký">
    <h2>Chờ tôi ký <small v-if="count">({{count}})</small></h2>
    <p v-if="error" class="lotus-sign-inbox__error" role="alert">{{error}}</p>
    <p v-if="notice" class="lotus-sign-inbox__ok" role="status">{{notice}}</p>
    <ul v-if="failures.length" class="lotus-sign-inbox__error"><li v-for="f in failures" :key="f.doctype+f.name">{{f.name}}: {{f.message}}</li></ul>
    <Empty v-if="!busy&&!rows.length" description="Không có chứng từ nào chờ bạn ký"/>
    <Cell v-for="row in rows" :key="key(row)" is-link @click="openRow(row)">
     <template #icon><Checkbox :model-value="picked.includes(key(row))" :aria-label="'Chọn '+row.name" @click.stop @update:model-value="on=>toggle(row,on)"/></template>
     <template #title><strong>{{row.chain_label}} · {{row.name}}</strong></template>
     <template #label><span>{{[row.step_title,row.creator_name,row.amount!=null&&row.amount!==''?signing.money(row.amount,row.currency):''].filter(Boolean).join(' · ')}}</span></template>
    </Cell>
    <LotusMobileButton v-if="rows.length" variant="primary" class="lotus-sign-inbox__bulk" :disabled="busy||!online||!picked.length" @click="signPicked">{{picked.length?'Ký '+picked.length+' chứng từ đã chọn':'Chọn chứng từ để ký nhiều'}}</LotusMobileButton>
   </section>
  </Popup>
  <LotusMobileSignSheet v-model:show="sheet" :row="current" :online="online" :call-fn="callFn" @done="done"/>
  <LotusMobileDialog :ref="el=>confirm.dialog.value=el" @cancel="confirm.finish(false)">
   <h3>Ký nhiều chứng từ</h3><p>{{confirm.message.value}}</p>
   <LotusMobileButton @click="confirm.finish(false)">Quay lại</LotusMobileButton>
   <LotusMobileButton variant="primary" @click="confirm.finish(true)">Ký</LotusMobileButton>
  </LotusMobileDialog>
 </div>
</template>

<style>
.lotus-sign-inbox__panel{display:grid;gap:var(--lotus-space-2,8px);padding:var(--lotus-space-4,16px) 0 max(24px,env(safe-area-inset-bottom))}
.lotus-sign-inbox__panel h2{margin:0 var(--lotus-space-4,16px);font-size:18px}
.lotus-sign-inbox__panel .van-cell__left-icon,.lotus-sign-inbox__panel .van-checkbox{margin-right:var(--lotus-space-2,8px)}
.lotus-sign-inbox__error{margin:0 var(--lotus-space-4,16px);color:var(--lotus-danger)}
.lotus-sign-inbox__ok{margin:0 var(--lotus-space-4,16px);color:var(--lotus-success-700,var(--lotus-text))}
.lotus-sign-inbox__bulk{margin:var(--lotus-space-2,8px) var(--lotus-space-4,16px) 0}
</style>
