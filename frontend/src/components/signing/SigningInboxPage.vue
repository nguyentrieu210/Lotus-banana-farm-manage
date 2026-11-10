<script setup>
// /lotus/cho-ky (spec 003, FR-011): mọi chứng từ đang đến lượt tôi ký, mọi loại. Bấm một dòng mở tấm ký;
// chọn nhiều rồi Ký nhiều với một lần xác nhận (FR-017). Link /lotus/cho-ky?sign_dt=&sign_dn= mở thẳng tấm ký.
import {computed,inject,onMounted,onUnmounted,ref,watch} from 'vue'
import {routeLocationKey} from 'vue-router'
import DataTable from '../DataTable.vue'
import WorkspaceConfirm from '../WorkspaceConfirm.vue'
import SignSheet from './SignSheet.vue'
import {Button as UiButton} from '../ui/button'
import {useWorkspaceConfirm} from '../../use-workspace-confirm'
import {toast} from '../../use-toast'
import * as signing from '../../use-signing'

const props=defineProps({callFn:Function,navigationKey:String})
const route=inject(routeLocationKey,null)
const rows=ref([]),busy=ref(false),error=ref(''),picked=ref([]),sheet=ref(false),current=ref(null),failures=ref([])
const confirm=useWorkspaceConfirm()
const key=r=>r.doctype+'::'+r.name
const data=computed(()=>rows.value.map(r=>({...r,key:key(r)})))
const columns=[
 {field:'chain_label',headerName:'Loại chứng từ',minWidth:170},
 {field:'name',headerName:'Số chứng từ',minWidth:170},
 {field:'step_title',headerName:'Bước ký',minWidth:170},
 {field:'creator_name',headerName:'Người lập',minWidth:150},
 {field:'amount',headerName:'Số tiền',type:'numericColumn',valueFormatter:p=>signing.money(p.value,p.data?.currency)},
 {field:'posting_date',headerName:'Ngày chứng từ',valueFormatter:p=>signing.shortDate(p.value)},
 {field:'notified_at',headerName:'Báo lúc',valueFormatter:p=>signing.shortDate(p.value)},
]
const changed=()=>window.dispatchEvent(new CustomEvent('lotus-signing-changed'))

async function load(){
 busy.value=true;error.value=''
 try{
  const result=await signing.inbox({},props.callFn)
  rows.value=result?.rows||[]
  const present=new Set(rows.value.map(key))
  picked.value=picked.value.filter(k=>present.has(k))
 }catch(e){error.value=e.message||String(e)}
 finally{busy.value=false}
}
function toggle(id,on){picked.value=on?[...new Set([...picked.value,id])]:picked.value.filter(k=>k!==id)}
function open(row){current.value=row;sheet.value=true}
async function signPicked(){
 const list=data.value.filter(r=>picked.value.includes(r.key))
 if(!list.length||!await confirm.ask(signing.confirmText(list),'Ký nhiều chứng từ'))return
 busy.value=true;error.value='';failures.value=[]
 try{
  const result=await signing.signDocuments(list,props.callFn)
  failures.value=(result?.results||[]).filter(r=>!r.ok)
  toast({title:'Đã ký '+(result?.signed||0)+'/'+list.length+' chứng từ',tone:failures.value.length?'info':'success'})
  picked.value=[]
 }catch(e){error.value=e.message||String(e)}
 finally{busy.value=false}
 await load();changed()
}
async function done({message}){toast({title:message,tone:'success'});await load();changed()}
// A link to one document (e-mail on a computer, a stock document without its own desktop screen).
async function openFromLink(){
 const q=route?.query||{}
 if(!q.sign_dt||!q.sign_dn)return
 const row=rows.value.find(r=>r.doctype===q.sign_dt&&r.name===q.sign_dn)
 if(row)return open(row)
 try{open({doctype:String(q.sign_dt),name:String(q.sign_dn),...await signing.signingApi('open_targets',{doctype:q.sign_dt,name:q.sign_dn},false,props.callFn)})}
 catch(e){error.value=e.message||String(e)}
}
function focus(){if(document.visibilityState==='visible')load()}
onMounted(async()=>{await load();await openFromLink();document.addEventListener('visibilitychange',focus)})
onUnmounted(()=>document.removeEventListener('visibilitychange',focus))
watch(()=>props.navigationKey,async()=>{await load();await openFromLink()})
</script>

<template>
 <section class="sign-inbox" aria-label="Chờ tôi ký">
  <div class="sign-inbox__tools">
   <UiButton type="button" :disabled="busy||!picked.length" @click="signPicked">{{picked.length?'Ký '+picked.length+' chứng từ đã chọn':'Chọn chứng từ để ký nhiều'}}</UiButton>
   <UiButton type="button" variant="outline" :disabled="busy" @click="load">Làm mới</UiButton>
  </div>
  <p v-if="error" class="sign-inbox__error" role="alert">{{error}}</p>
  <ul v-if="failures.length" class="sign-inbox__failures" aria-label="Chứng từ chưa ký được">
   <li v-for="f in failures" :key="f.doctype+f.name"><strong>{{f.name}}</strong>: {{f.message}}</li>
  </ul>
  <DataTable :rows="data" :columns="columns" row-key="key" interactive :row-detail="false" :loading="busy" :fill="0"
   empty="Không có chứng từ nào chờ bạn ký." storage-key="lotus-sign-inbox" :selected-row-keys="picked"
   @open="open" @row-selection-change="({id,selected})=>toggle(id,selected)"
   @page-selection-change="({rows:page,selected})=>page.forEach(r=>toggle(key(r),selected))" @selection-clear="picked=[]"/>
  <SignSheet v-model="sheet" :row="current" :call-fn="callFn" @done="done"/>
  <WorkspaceConfirm :open="confirm.open.value" :title="confirm.title.value" :message="confirm.message.value" confirm-label="Ký" cancel-label="Quay lại" @answer="confirm.finish"/>
 </section>
</template>

<style>
.sign-inbox{display:grid;gap:var(--lotus-space-3,12px)}
.sign-inbox__tools{display:flex;gap:var(--lotus-space-2,8px);flex-wrap:wrap}
.sign-inbox__error{margin:0;color:var(--lotus-danger)}
.sign-inbox__failures{margin:0;padding-left:var(--lotus-space-5,20px);color:var(--lotus-danger)}
</style>
