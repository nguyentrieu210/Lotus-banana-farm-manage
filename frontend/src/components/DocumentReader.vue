<script setup>
import {ref} from 'vue'
import {call,upload} from '../api'
import {Button as UiButton} from './ui/button'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusIcon from './LotusIcon.vue'
import {FilePickerButton} from './ui/file-input'
// "Đọc chứng từ bằng AI": photo / PDF of a quote, invoice or delivery note → suggested supplier and lines.
// Emits read(result, file) so the form fills itself; nothing is saved until the user saves the form.
const props=defineProps({mobile:Boolean,disabled:Boolean,label:{type:String,default:'Đọc chứng từ bằng AI'}})
const emit=defineEmits(['read'])
const busy=ref(false),error=ref(''),summary=ref(null)
async function pick([file]){
 busy.value=true;error.value='';summary.value=null
 try{
  const stored=await upload(file)
  const result=await call('lotus_farm.document_ai.read',{file_url:stored.file_url},true)
  const matched=result.lines.filter(line=>line.item).length
  summary.value={lines:result.lines.length,matched,supplier:result.supplier.match?.label||result.supplier.text,warnings:result.warnings}
  emit('read',result,stored)
 }catch(e){error.value=e.message}finally{busy.value=false}
}
</script>
<template>
 <div class="lotus-doc-reader">
  <FilePickerButton :as="mobile?LotusMobileButton:UiButton" accept="image/*,application/pdf" label="Chọn ảnh hoặc PDF chứng từ" :disabled="disabled||busy" @files="pick"><LotusIcon name="scan"/>{{busy?'AI đang đọc chứng từ…':label}}</FilePickerButton>
  <p v-if="error" class="lotus-doc-reader__error" role="alert">{{error}}</p>
  <div v-else-if="summary" class="lotus-doc-reader__summary" role="status">
   <b>Đã đọc {{summary.lines}} dòng, khớp {{summary.matched}} vật tư<template v-if="summary.supplier"> · NCC: {{summary.supplier}}</template>.</b> Kiểm tra lại số lượng, đơn giá trước khi lưu.
   <ul v-if="summary.warnings.length"><li v-for="w in summary.warnings" :key="w">{{w}}</li></ul>
  </div>
 </div>
</template>
<style>
.lotus-doc-reader{display:grid;gap:8px;justify-items:start;grid-column:1/-1}
.lotus-doc-reader__error{margin:0;color:var(--lotus-danger);font-size:var(--lotus-text-sm)}
.lotus-doc-reader__summary{width:100%;padding:10px 12px;border-radius:var(--lotus-radius-md);background:var(--lotus-primary-subtle);color:var(--lotus-text);font-size:var(--lotus-text-sm)}
.lotus-doc-reader__summary ul{margin:6px 0 0;padding-left:18px;color:var(--lotus-warning-700,var(--lotus-text))}
</style>
