<script setup>
// Pick the named signer of every later step of a signing chain (lotus_farm.signing.candidates).
// Only employees with a login and the step's role are offered, so each one can be notified.
import {computed,watch} from 'vue'
import MobileLinkField from './MobileLinkField.vue'
import '../signer-picker.css'

const props=defineProps({options:{type:Object,default:null},modelValue:{type:Object,default:()=>({})},disabled:Boolean,
 accountsHint:{type:String,default:'Gắn tài khoản đăng nhập cho nhân sự trong mục Nhân sự để chọn được.'}})
const emit=defineEmits(['update:modelValue'])
const steps=computed(()=>(props.options?.steps||[]).slice(1))
const choices=key=>(props.options?.candidates?.[key]||[]).map(c=>({value:c.user,label:c.name,subtitle:[c.designation,c.department].filter(Boolean).join(' · ')||c.user}))
const missing=computed(()=>steps.value.filter(s=>!props.modelValue?.[s.key]).map(s=>s.title))
function set(key,user){emit('update:modelValue',{...props.modelValue,[key]:user})}
// Prefill once from the signer's last choices, keeping only people still offered for that step.
watch(()=>props.options,options=>{
 if(!options)return
 const next={...props.modelValue}
 for(const s of steps.value){
  const allowed=choices(s.key).map(c=>c.value)
  if(next[s.key]&&!allowed.includes(next[s.key]))delete next[s.key]
  if(!next[s.key]&&allowed.includes(options.remembered?.[s.key]))next[s.key]=options.remembered[s.key]
  if(!next[s.key]&&allowed.length===1)next[s.key]=allowed[0]
 }
 emit('update:modelValue',next)
},{immediate:true})
defineExpose({missing})
</script>

<template>
<fieldset class="signer-picker" :disabled="disabled">
 <legend>Người ký duyệt</legend>
 <p class="signer-picker__hint">Mỗi người được báo trên ứng dụng và e-mail khi đến lượt ký.</p>
 <div v-for="(s,i) in steps" :key="s.key" class="signer-picker__row">
  <label :for="'signer-'+s.key"><span class="signer-picker__no">{{i+2}}</span>{{s.title}}</label>
  <MobileLinkField :id="'signer-'+s.key" :model-value="modelValue?.[s.key]||''" :options="choices(s.key)" :searchable="choices(s.key).length>6"
   placeholder="Chọn người ký…" :aria-label="'Người ký: '+s.title" required :disabled="disabled||!choices(s.key).length" @update:modelValue="set(s.key,$event)"/>
  <small v-if="!choices(s.key).length" class="signer-picker__empty">Chưa có nhân sự nào có quyền ký bước này. {{accountsHint}}</small>
 </div>
</fieldset>
</template>
