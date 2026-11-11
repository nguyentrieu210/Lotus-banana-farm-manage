<script setup>
// Chữ ký của tôi trên máy tính (spec 003, FR-018). Same rules and endpoints as the phone settings:
// PNG/JPG under 10 MB, paper background removed and cropped to the ink, or drawn with the mouse/pen.
import {computed,ref,watch} from 'vue'
import WorkspaceModal from '../WorkspaceModal.vue'
import WorkspaceConfirm from '../WorkspaceConfirm.vue'
import SignaturePad from './SignaturePad.vue'
import LotusField from '../form/LotusField.vue'
import {Button as UiButton} from '../ui/button'
import {FileInput} from '../ui/file-input'
import {useWorkspaceConfirm} from '../../use-workspace-confirm'
import {removeBackground} from '../../signature-background'
import * as profileApi from '../../use-signature-profile'

const props=defineProps({modelValue:Boolean,callFn:Function})
const emit=defineEmits(['update:modelValue'])
const profile=ref(null),busy=ref(false),error=ref(''),notice=ref(''),drawing=ref(''),drawn=ref(false),pad=ref(null)
const confirm=useWorkspaceConfirm()
const kinds=[{key:'signature',label:'Chữ ký',preview:'signature_preview',has:'has_signature'},{key:'initials',label:'Ký nháy',preview:'initials_preview',has:'has_initials'}]
const formats=computed(()=>[{value:'DD/MM/YYYY',label:'10/11/2026'},{value:'DD-MM-YYYY',label:'10-11-2026'},{value:'LONG_VI',label:'Ngày 10 tháng 11 năm 2026'}])

async function run(work,message){
 busy.value=true;error.value='';notice.value=''
 try{const result=await work();if(result)profile.value=result;if(message)notice.value=message}
 catch(e){error.value=e.message||String(e)}
 finally{busy.value=false}
}
watch(()=>props.modelValue,open=>{if(open){drawing.value='';run(()=>profileApi.loadProfile(props.callFn))}},{immediate:true})

// Read the photo, take out the paper and crop to the ink, as the phone editor does.
function cleanImage(file){
 return new Promise((resolve,reject)=>{
  const url=URL.createObjectURL(file),image=new Image()
  image.onload=()=>{
   try{
    const scale=Math.min(1,1600/Math.max(image.width,image.height))
    const canvas=document.createElement('canvas')
    canvas.width=Math.round(image.width*scale);canvas.height=Math.round(image.height*scale)
    const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0,canvas.width,canvas.height)
    const data=ctx.getImageData(0,0,canvas.width,canvas.height),box=removeBackground(data)
    if(!box)throw Error('Không thấy nét chữ ký trong ảnh. Chụp lại trên giấy trắng, đủ sáng.')
    ctx.putImageData(data,0,0)
    const out=document.createElement('canvas');out.width=box.width;out.height=box.height
    out.getContext('2d').drawImage(canvas,box.x,box.y,box.width,box.height,0,0,box.width,box.height)
    resolve(out.toDataURL('image/png'))
   }catch(e){reject(e)}finally{URL.revokeObjectURL(url)}
  }
  image.onerror=()=>{URL.revokeObjectURL(url);reject(Error('Không đọc được ảnh.'))}
  image.src=url
 })
}
async function upload(kind,file){
 const problem=profileApi.imageFileProblem(file)
 if(problem){error.value=problem;return}
 await run(async()=>profileApi.saveImage(kind,await cleanImage(file),props.callFn),'Đã lưu '+(kind==='initials'?'ký nháy':'chữ ký')+' mới.')
}
async function saveDrawing(){
 const data=pad.value?.toDataURL()
 if(!data)return
 const kind=drawing.value
 await run(()=>profileApi.saveImage(kind,data,props.callFn),'Đã lưu '+(kind==='initials'?'ký nháy':'chữ ký')+' vẽ tay.')
 if(!error.value)drawing.value=''
}
async function remove(kind){
 if(!await confirm.ask(kind==='initials'?'Xóa mẫu ký nháy đã lưu?':'Xóa ảnh chữ ký đã lưu? Chứng từ đã ký trước đây không đổi.','Xóa'))return
 await run(()=>profileApi.removeImage(kind,props.callFn),'Đã xóa.')
}
const saveFormat=value=>run(()=>profileApi.saveDateFormat(value,props.callFn),'Đã lưu định dạng ngày ký.')
</script>

<template>
 <WorkspaceModal :model-value="modelValue" title="Chữ ký của tôi" :busy="busy" width="760px" @update:model-value="emit('update:modelValue',$event)">
  <div class="signature-settings">
   <p v-if="error" class="signature-settings__error" role="alert">{{error}}</p>
   <p v-if="notice" class="signature-settings__ok" role="status">{{notice}}</p>
   <section v-for="kind in kinds" :key="kind.key" class="signature-settings__card" :aria-label="kind.label">
    <strong>{{kind.label}}</strong>
    <img v-if="profile?.[kind.preview]" :src="profile[kind.preview]" :alt="kind.label+' đã lưu'" class="signature-settings__preview">
    <p v-else class="signature-settings__muted">Chưa có {{kind.label.toLowerCase()}}.</p>
    <template v-if="drawing===kind.key">
     <SignaturePad ref="pad" :height="170" @change="drawn=$event"/>
     <div class="signature-settings__row">
      <UiButton type="button" :disabled="busy||!drawn" @click="saveDrawing">Lưu bản vẽ</UiButton>
      <UiButton type="button" variant="outline" @click="pad?.clear()">Vẽ lại</UiButton>
      <UiButton type="button" variant="outline" @click="drawing=''">Hủy</UiButton>
     </div>
    </template>
    <div v-else class="signature-settings__row">
     <FileInput accept="image/jpeg,image/png,.jpg,.jpeg,.png" :disabled="busy" :aria-label="'Tải ảnh '+kind.label.toLowerCase()" @update:model-value="file=>file&&upload(kind.key,file)"/>
     <UiButton type="button" variant="outline" :disabled="busy" @click="drawing=kind.key;drawn=false">Vẽ {{kind.label.toLowerCase()}}</UiButton>
     <UiButton v-if="profile?.[kind.has]" type="button" variant="outline" :disabled="busy" @click="remove(kind.key)">Xóa</UiButton>
    </div>
   </section>
   <LotusField v-if="profile" :model-value="profile.date_format" label="Định dạng ngày ký trên bản in" :options="formats" :searchable="false" @update:model-value="saveFormat"/>
   <p class="signature-settings__muted">Chữ ký bằng hình ảnh, không phải chữ ký số có chứng thư. Đổi ảnh không làm thay đổi chứng từ đã ký.</p>
  </div>
 </WorkspaceModal>
 <WorkspaceConfirm :open="confirm.open.value" :title="confirm.title.value" :message="confirm.message.value" confirm-label="Xóa" cancel-label="Quay lại" @answer="confirm.finish"/>
</template>

<style>
.signature-settings{display:grid;gap:var(--lotus-space-3,12px)}
.signature-settings__card{display:grid;gap:var(--lotus-space-2,8px);padding:var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px)}
.signature-settings__preview{max-height:90px;max-width:100%;object-fit:contain;background:white;border-radius:var(--lotus-radius-md,8px)}
.signature-settings__row{display:flex;gap:var(--lotus-space-2,8px);flex-wrap:wrap;align-items:center}
.signature-settings__muted{margin:0;color:var(--lotus-muted)}
.signature-settings__error{margin:0;color:var(--lotus-danger)}
.signature-settings__ok{margin:0;color:var(--lotus-success-700,var(--lotus-text))}
</style>
