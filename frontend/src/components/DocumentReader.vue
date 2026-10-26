<script setup>
import {ref} from 'vue'
import {call,upload} from '../api'
import LotusIcon from './LotusIcon.vue'
import {FilePickerButton} from './ui/file-input'
// "Đọc chứng từ bằng AI": photo / PDF of a quote, invoice or delivery note → suggested supplier and lines.
// Emits read(result, file) so the form fills itself; nothing is saved until the user saves the form.
const props=defineProps({mobile:Boolean,disabled:Boolean,camera:Boolean,label:{type:String,default:'Đọc chứng từ bằng AI'}})
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
 <div class="lotus-doc-reader" :class="{'lotus-doc-reader--mobile':mobile,'lotus-doc-reader--camera':camera}">
  <div class="lotus-doc-reader__actions">
   <FilePickerButton v-if="camera" as="button" button-class="lotus-doc-btn lotus-doc-btn--primary" accept="image/*" capture="environment" label="Chụp chứng từ bằng camera" :disabled="disabled||busy" @files="pick"><span v-if="busy" class="lotus-spinner" aria-hidden="true"></span><LotusIcon v-else name="switch-camera"/>{{busy?'Đang đọc…':'Chụp phiếu'}}</FilePickerButton>
   <FilePickerButton as="button" :button-class="camera?'lotus-doc-btn':'lotus-doc-btn lotus-doc-btn--soft'" accept="image/*,application/pdf" label="Chọn ảnh hoặc PDF chứng từ" :disabled="disabled||busy" @files="pick"><span v-if="busy&&!camera" class="lotus-spinner" aria-hidden="true"></span><LotusIcon v-else :name="camera?'upload':'scan'"/>{{camera?'Ảnh / PDF':busy?'AI đang đọc…':label}}</FilePickerButton>
  </div>
  <div v-if="busy" class="lotus-doc-reader__busy" role="status" aria-live="polite"><span class="lotus-spinner lotus-spinner--lg" aria-hidden="true"></span>AI đang đọc chứng từ, vui lòng chờ…</div>
  <p v-else-if="error" class="lotus-doc-reader__error" role="alert">{{error}}</p>
  <div v-else-if="summary" class="lotus-doc-reader__summary" role="status">
   <b>Đã đọc {{summary.lines}} dòng, khớp {{summary.matched}} vật tư<template v-if="summary.supplier"> · NCC: {{summary.supplier}}</template>.</b> Kiểm tra lại số lượng, đơn giá trước khi lưu.
   <ul v-if="summary.warnings.length"><li v-for="w in summary.warnings" :key="w">{{w}}</li></ul>
  </div>
 </div>
</template>
<style>
.lotus-doc-reader{display:grid;gap:8px;justify-items:start;grid-column:1/-1}
.lotus-doc-reader__actions{display:flex;flex-wrap:wrap;gap:8px;width:100%}
/* Reader buttons: own styles so they look the same in the workspace and the phone apps. */
.lotus-doc-btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:38px;padding:0 16px;border:1px solid var(--lotus-border,#e3e3e3);border-radius:999px;background:var(--lotus-surface,#fff);color:var(--lotus-text,#222);font:inherit;font-size:14px;font-weight:600;line-height:1;cursor:pointer;white-space:nowrap;transition:background .15s,border-color .15s,box-shadow .15s}
.lotus-doc-btn .lotus-icon{width:17px;height:17px;flex:0 0 auto}
.lotus-doc-btn:hover:not(:disabled){border-color:var(--lotus-primary,#c62828);box-shadow:0 1px 4px rgba(198,40,40,.12)}
.lotus-doc-btn:focus-visible{outline:2px solid var(--lotus-primary,#c62828);outline-offset:2px}
.lotus-doc-btn:disabled{opacity:.65;cursor:progress}
.lotus-doc-btn--primary{border-color:transparent;background:var(--lotus-primary,#c62828);color:#fff}
.lotus-doc-btn--primary:hover:not(:disabled){background:var(--lotus-primary-hover,#b71c1c)}
.lotus-doc-btn--soft{border-color:color-mix(in srgb,var(--lotus-primary,#c62828) 35%,transparent);background:var(--lotus-primary-subtle,#fdecea);color:var(--lotus-primary-text,#b71c1c)}
.lotus-doc-reader--mobile .lotus-doc-reader__actions{display:grid;grid-template-columns:repeat(auto-fit,minmax(0,1fr));gap:10px}
.lotus-doc-reader--mobile .lotus-doc-btn{min-height:46px;font-size:15px}
/* Spinner while the AI reads the document (respects reduced motion). */
.lotus-spinner{display:inline-block;width:16px;height:16px;flex:0 0 auto;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;animation:lotus-spin .8s linear infinite}
.lotus-spinner--lg{width:22px;height:22px;border-width:3px;color:var(--lotus-primary,#c62828)}
.lotus-doc-reader__busy{display:flex;align-items:center;gap:10px;width:100%;padding:10px 12px;border-radius:var(--lotus-radius-md,8px);background:var(--lotus-primary-subtle,#fdecea);color:var(--lotus-text);font-size:var(--lotus-text-sm,13px);font-weight:600}
@keyframes lotus-spin{to{transform:rotate(360deg)}}
@media(prefers-reduced-motion:reduce){.lotus-spinner{animation-duration:2.4s}}
.lotus-doc-reader__error{margin:0;color:var(--lotus-danger);font-size:var(--lotus-text-sm)}
.lotus-doc-reader__summary{width:100%;padding:10px 12px;border-radius:var(--lotus-radius-md);background:var(--lotus-primary-subtle);color:var(--lotus-text);font-size:var(--lotus-text-sm)}
.lotus-doc-reader__summary ul{margin:6px 0 0;padding-left:18px;color:var(--lotus-warning-700,var(--lotus-text))}
</style>
