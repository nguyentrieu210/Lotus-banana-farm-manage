<script setup>
import {computed,ref,watch} from 'vue'
import {call,upload} from '../../api'
import {Button as UiButton} from '../ui/button'
import LotusIcon from '../LotusIcon.vue'
import {FilePickerButton} from '../ui/file-input'
// Chứng từ / ảnh bằng chứng của phiếu kho. With a saved document (name) files upload and attach at once;
// while the document is still being written they wait in `pending` and the form calls flush(doctype, name) after saving.
const props=defineProps({doctype:String,name:String,disabled:Boolean,title:{type:String,default:'Chứng từ, ảnh bằng chứng'}})
const pending=defineModel('pending',{type:Array,default:()=>[]})
const rows=ref([]),busy=ref(false),error=ref('')
const saved=computed(()=>Boolean(props.doctype&&props.name))
async function load(){if(!saved.value){rows.value=[];return}try{rows.value=await call('lotus_farm.stock_attachments.files',{doctype:props.doctype,name:props.name})}catch(e){error.value=e.message}}
watch(()=>[props.doctype,props.name],load,{immediate:true})
async function attachAll(doctype,name,files){
 for(const file of files){const url=file.file_url||(await upload(file)).file_url;rows.value=await call('lotus_farm.stock_attachments.attach',{doctype,name,file_url:url},true)}
}
async function add(files){
 if(!saved.value){pending.value=[...pending.value,...files];return}
 busy.value=true;error.value=''
 try{await attachAll(props.doctype,props.name,files)}catch(e){error.value=e.message}finally{busy.value=false}
}
async function remove(row){
 busy.value=true;error.value=''
 try{rows.value=await call('lotus_farm.stock_attachments.remove',{doctype:props.doctype,name:props.name,file:row.name},true)}catch(e){error.value=e.message}finally{busy.value=false}
}
// Called by the document form right after the draft is saved.
async function flush(doctype,name){if(!pending.value.length)return;const files=pending.value;await attachAll(doctype,name,files);pending.value=[]}
const preview=file=>file.file_url?(/\.(jpe?g|png|webp)$/i.test(file.file_url)?file.file_url:''):file.type?.startsWith('image/')?URL.createObjectURL(file):''
const fileName=file=>file.name||file.file_name||'tệp'
defineExpose({flush,reload:load})
</script>
<template>
 <section class="stock-evidence" :aria-label="title">
  <header><h4>{{title}}</h4><span class="lotus-form-note">Ảnh chụp hàng, phiếu giao hàng, hóa đơn… (ảnh hoặc PDF, tối đa 20 tệp)</span></header>
  <div class="stock-evidence__actions">
   <FilePickerButton accept="image/*" capture="environment" label="Chụp ảnh bằng chứng" size="sm" :disabled="disabled||busy" @files="add"><LotusIcon name="switch-camera"/>Chụp ảnh</FilePickerButton>
   <FilePickerButton accept="image/*,application/pdf" multiple label="Chọn tệp chứng từ" size="sm" :disabled="disabled||busy" @files="add"><LotusIcon name="upload"/>{{busy?'Đang tải lên…':'Chọn tệp'}}</FilePickerButton>
  </div>
  <p v-if="error" class="stock-evidence__error" role="alert">{{error}}</p>
  <ul v-if="rows.length||pending.length" class="stock-evidence__list">
   <li v-for="row in rows" :key="row.name">
    <a :href="row.file_url" target="_blank" rel="noopener"><img v-if="row.is_image" :src="row.file_url" alt=""><LotusIcon v-else name="document"/><span>{{row.file_name}}</span></a>
    <UiButton v-if="row.mine&&!disabled" type="button" variant="ghost" size="sm" :aria-label="'Xóa '+row.file_name" :disabled="busy" @click="remove(row)"><LotusIcon name="x"/></UiButton>
   </li>
   <li v-for="(file,index) in pending" :key="'p'+index+fileName(file)" class="is-pending">
    <span class="stock-evidence__file"><img v-if="preview(file)" :src="preview(file)" alt=""><LotusIcon v-else name="document"/><span>{{fileName(file)}} · gắn vào phiếu khi lưu</span></span>
    <UiButton type="button" variant="ghost" size="sm" :aria-label="'Bỏ '+fileName(file)" @click="pending=pending.filter((_,i)=>i!==index)"><LotusIcon name="x"/></UiButton>
   </li>
  </ul>
  <p v-else class="lotus-form-note">Chưa có tệp đính kèm.</p>
 </section>
</template>
<style>
.stock-evidence{display:grid;gap:8px;min-width:0}
.stock-evidence header{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px}
.stock-evidence h4{margin:0;font-size:var(--lotus-text-md);font-weight:600}
.stock-evidence__actions{display:flex;flex-wrap:wrap;gap:8px}
.stock-evidence__error{margin:0;color:var(--lotus-danger);font-size:var(--lotus-text-sm)}
.stock-evidence__list{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px;margin:0;padding:0;list-style:none}
.stock-evidence__list li{display:flex;align-items:center;gap:6px;min-width:0;padding:6px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.stock-evidence__list li.is-pending{border-style:dashed}
.stock-evidence__list a,.stock-evidence__file{display:flex;align-items:center;gap:8px;flex:1;min-width:0;color:var(--lotus-text);text-decoration:none;font-size:var(--lotus-text-sm)}
.stock-evidence__list img{width:44px;height:44px;object-fit:cover;border-radius:6px;flex:0 0 auto}
.stock-evidence__list span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
</style>
