<script setup>
import {computed,ref} from 'vue'
import {call} from '../api'
import ModalForm from './form/ModalForm.vue'
import LotusField from './form/LotusField.vue'
// Nạp sổ cắt bắp: pick the farm's Excel book, see what would be written, then write it. Any error in the file stops the import.
const props=defineProps({farm:{type:String,required:true}})
const emit=defineEmits(['close','done'])
const preview=ref(null),busy=ref(false),error=ref('')
const fmt=n=>Number(n||0).toLocaleString('vi-VN')
const label=computed(()=>preview.value?.summary.new_bunches?'Ghi '+fmt(preview.value.summary.new_bunches)+' buồng vào sổ':'Ghi vào sổ')
async function readFile(event){
 const file=event.target.files?.[0];if(!file)return
 busy.value=true;preview.value=null;error.value=''
 try{
  const content=await new Promise((ok,fail)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=fail;r.readAsDataURL(file)})
  preview.value=await call('lotus_farm.bunch_opening_import.preview',{farm:props.farm,content,filename:file.name},true)
 }catch(e){error.value=e.message}
 finally{busy.value=false;event.target.value=''}
}
async function commit(){
 busy.value=true;error.value=''
 try{emit('done',await call('lotus_farm.bunch_opening_import.commit',{farm:props.farm,token:preview.value.token},true))}
 catch(e){error.value=e.message}
 finally{busy.value=false}
}
</script>

<template>
 <ModalForm class="bunch-opening-modal" :model-value="true" title="Nạp sổ cắt bắp" width="640px" :busy="busy" busy-label="Đang xử lý…" :error="error" :submit-label="label" :submit-disabled="!preview?.ready" @update:model-value="v=>!v&&emit('close')" @submit="commit">
  <LotusField label="File sổ cắt bắp (.xlsx)" type="file" accept=".xlsx" :disabled="busy" @change="readFile"/>
  <template v-if="preview">
   <p class="lotus-form-note">{{fmt(preview.summary.bunches)}} buồng · {{preview.summary.blocks}} lô · {{preview.summary.lines}} dòng<template v-if="preview.summary.colours.length"> · {{preview.summary.colours.map(c=>c.label+' '+fmt(c.bunches)).join(', ')}}</template></p>
   <p v-if="preview.summary.already" class="lotus-form-note">{{preview.summary.already}} dòng đã có trong sổ buồng, sẽ bỏ qua.</p>
   <p v-if="!preview.errors.length&&!preview.ready" class="lotus-form-note">Toàn bộ sổ này đã được nạp, không có gì để ghi thêm.</p>
   <ul v-if="preview.errors.length" class="work-bunch__errors" role="alert">
    <li v-for="(e,i) in preview.errors" :key="i">Dòng {{e.row}}<template v-if="e.code"> ({{e.code}})</template>: {{e.message}}</li>
   </ul>
   <p v-if="preview.errors.length" class="lotus-modal-form__error">File còn {{preview.errors.length}} lỗi nên chưa ghi được. Sửa file rồi chọn lại.</p>
  </template>
 </ModalForm>
</template>

<style>
.bunch-opening-modal .work-bunch__errors{max-height:40vh;overflow:auto;margin:0;padding-left:18px;font-size:var(--lotus-text-sm);color:var(--lotus-danger)}
</style>
