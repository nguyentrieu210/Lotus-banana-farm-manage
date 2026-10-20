<script setup>
// Named signatures on a posted document (phiếu kho, …): the preparer picks who signs each step,
// each one is notified on their turn and signs here; the print shows every signature (lotus_farm.signing).
import {computed,onMounted,ref,watch} from 'vue'
import SignerPicker from './SignerPicker.vue'
import LotusSignatureTimeline from './LotusSignatureTimeline.vue'
import {call} from '../api'
import '../signer-picker.css'

const props=defineProps({doctype:{type:String,required:true},name:{type:String,required:true},company:{type:String,default:''},online:{type:Boolean,default:true}})
const emit=defineEmits(['notice','error','changed'])
const info=ref(null),options=ref(null),signers=ref({}),busy=ref(false),reason=ref(''),returning=ref(false)
const api=(method,args,write=false)=>call('lotus_farm.signing.'+method,args,write)
const missing=computed(()=>(options.value?.steps||[]).slice(1).filter(s=>!signers.value[s.key]))

async function load(){
 busy.value=true
 try{
  info.value=await api('chain_status',{doctype:props.doctype,name:props.name})
  if(info.value.can_start&&!options.value){
   options.value=await api('candidates',{chain:info.value.chain,company:props.company||undefined})
   signers.value=Object.fromEntries(info.value.steps.slice(1).filter(s=>s.assignee).map(s=>[s.key,s.assignee]))
  }
 }catch(e){emit('error',e.message||String(e))}finally{busy.value=false}
}
async function run(method,args,message){
 if(busy.value)return
 busy.value=true
 try{info.value={...await api(method,{doctype:props.doctype,name:props.name,...args},true),can_start:false};reason.value='';returning.value=false;emit('notice',message);emit('changed')}
 catch(e){emit('error',e.message||String(e))}finally{busy.value=false}
}
const start=()=>run('request_signatures',{signers:signers.value},'Đã ký và báo người ký tiếp theo.')
const sign=()=>run('confirm',{},'Đã ký phiếu.')
const sendBack=()=>run('return_document',{reason:reason.value},'Đã trả lại cho người lập.')
watch(()=>[props.doctype,props.name],()=>{options.value=null;load()})
onMounted(load)
</script>

<template>
<section v-if="info" class="signing-panel" aria-label="Chữ ký trên phiếu">
 <h3>Chữ ký · {{info.label}}</h3>
 <LotusSignatureTimeline v-if="info.round" :steps="info.steps" :current="info.returned?-1:(info.current??-1)" title=""/>
 <p v-else class="signing-panel__hint">Chưa gửi ký. Chọn người ký để mỗi người được báo khi đến lượt.</p>
 <template v-if="info.can_start">
  <SignerPicker v-model="signers" :options="options" :disabled="busy"/>
  <button type="button" class="signing-panel__primary" :disabled="busy||!online||missing.length>0" @click="start">Ký người lập và gửi ký</button>
 </template>
 <template v-if="info.can_sign">
  <button type="button" class="signing-panel__primary" :disabled="busy||!online" @click="sign">Ký: {{info.steps[info.current].title}}</button>
  <button v-if="info.can_return&&!returning" type="button" class="signing-panel__ghost" :disabled="busy" @click="returning=true">Trả lại người lập</button>
  <div v-if="returning" class="signing-panel__return">
   <label for="signing-return">Lý do trả lại</label>
   <textarea id="signing-return" v-model="reason" rows="2" maxlength="500" placeholder="Nêu rõ cần kiểm tra gì…"></textarea>
   <button type="button" class="signing-panel__danger" :disabled="busy||!online||reason.trim().length<3" @click="sendBack">Trả lại</button>
  </div>
 </template>
</section>
</template>

