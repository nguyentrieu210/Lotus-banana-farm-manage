<script setup>
import {ref,watch} from 'vue'
import {Icon} from 'vant'
import {call} from '../api'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileDialog from './LotusMobileDialog.vue'
import {useMobileConfirm} from '../use-mobile-confirm'
import './lotus-mobile-signature.css'

const props=defineProps({user:{type:String,default:''}})
const expanded=ref(false),loading=ref(false),saving=ref(false),loaded=ref(false)
const profile=ref(null),error=ref(''),notice=ref(''),selectedFile=ref(''),uploadStep=ref('')
const endpoint='lotus_farm.digital_signature.'
const {dialog:deleteDialog,message:deleteMessage,ask:askDelete,finish:finishDelete}=useMobileConfirm()
watch(()=>props.user,()=>{expanded.value=false;loaded.value=false;profile.value=null;error.value='';notice.value='';selectedFile.value='';uploadStep.value=''})
async function load(){
 if(!props.user)return
 loading.value=true;error.value=''
 try{profile.value=await call(endpoint+'my_signature_profile');loaded.value=true}
 catch(e){error.value=e.message||'Không tải được chữ ký.'}
 finally{loading.value=false}
}
async function toggle(){expanded.value=!expanded.value;if(expanded.value&&!loaded.value)await load()}
function asBase64(file){
 return new Promise((resolve,reject)=>{
  const reader=new FileReader()
  reader.onload=()=>resolve(String(reader.result||''))
  reader.onerror=()=>reject(new Error('Không đọc được ảnh chữ ký.'))
  reader.readAsDataURL(file)
 })
}
async function chooseFile(event){
 const input=event.target
 const file=input.files?.[0]
 if(!file||saving.value)return
 selectedFile.value=file.name+' · '+(file.size/1000000).toFixed(1)+' MB'
 uploadStep.value='Đã chọn ảnh, đang kiểm tra…'
 input.value=''
 error.value='';notice.value=''
 const knownMime=['image/png','image/jpeg'].includes(file.type)
 const extension=/\.(png|jpe?g)$/i.test(file.name)
 if(!knownMime&&!(extension&&(!file.type||file.type==='application/octet-stream'))){
  error.value='Chỉ nhận ảnh PNG hoặc JPG. Nếu là HEIC, hãy đổi sang JPG.'
  uploadStep.value='Định dạng ảnh không hỗ trợ'
  return
 }
 if(file.size>10000000){error.value='Ảnh phải nhỏ hơn 10 MB.';uploadStep.value='Ảnh vượt giới hạn';return}
 saving.value=true
 try{
  uploadStep.value='Đang đọc ảnh…'
  const image_data=await asBase64(file)
  uploadStep.value='Đang gửi ảnh lên Lotus…'
  profile.value=await call(endpoint+'save_my_signature_image',{image_data},true)
  uploadStep.value='Đã lưu thành công'
  notice.value='Đã lưu ảnh chữ ký cho tài khoản của bạn.'
 }catch(e){uploadStep.value='Lưu ảnh thất bại';error.value=e.message||'Không lưu được ảnh chữ ký.'}
 finally{saving.value=false}
}
async function remove(){
 if(saving.value||!profile.value?.has_signature)return
 if(!(await askDelete('Xóa ảnh chữ ký đã lưu của tài khoản này?')))return
 saving.value=true;error.value='';notice.value=''
 try{
  profile.value=await call(endpoint+'remove_my_signature_image',{},true)
  notice.value='Đã xóa ảnh chữ ký.'
 }catch(e){error.value=e.message||'Không xóa được ảnh.'}
 finally{saving.value=false}
}
</script>

<template>
 <section class="lotus-signature-settings">
  <LotusMobileButton class="lotus-signature-toggle" type="button" :aria-expanded="expanded" @click="toggle">
   <span class="lotus-signature-heading"><Icon name="edit" aria-hidden="true"/><span>Chữ ký điện tử</span></span>
   <span class="lotus-signature-trailing">{{profile?.has_signature?'Đã thiết lập':'Thiết lập'}} <Icon :name="expanded?'arrow-up':'arrow-down'" aria-hidden="true"/></span>
  </LotusMobileButton>
  <div v-if="expanded" class="lotus-signature-body">
   <p v-if="loading" role="status">Đang tải ảnh chữ ký…</p>
   <p v-if="error" class="lotus-signature-error" role="alert">{{error}}</p>
   <template v-if="profile">
    <div class="lotus-signature-row"><span>Người ký</span><strong>{{profile.full_name}}</strong></div>
    <div class="lotus-signature-row"><span>Trạng thái</span><strong :class="profile.has_signature?'lotus-signature-ready':'lotus-signature-pending'">{{profile.has_signature?'Đã lưu ảnh chữ ký':'Chưa có chữ ký'}}</strong></div>
    <div v-if="profile.has_signature" class="lotus-signature-preview">
     <img :src="profile.signature_preview" alt="Ảnh chữ ký đã lưu của bạn"/>
     <small v-if="profile.updated_at">Cập nhật: {{profile.updated_at}}</small>
    </div>
    <div class="lotus-signature-uploader">
     <label for="lotus-signature-photo-file" class="lotus-signature-upload-label">Chọn ảnh chữ ký từ điện thoại (tối đa 10 MB)</label>
     <input id="lotus-signature-photo-file" type="file" class="lotus-signature-visible-input"
      accept="image/jpeg,image/png,.jpg,.jpeg,.png" name="signature-image" :disabled="saving||!profile.configured"
      aria-label="Chọn ảnh chữ ký từ điện thoại" @change="chooseFile"/>
     <p v-if="selectedFile" class="lotus-signature-selected-file">{{selectedFile}}</p>
     <p v-if="uploadStep" class="lotus-signature-upload-step" role="status">{{uploadStep}}</p>
     <small>Nên dùng ảnh PNG nền trong suốt hoặc ảnh JPG chụp trên giấy trắng, chỉ chứa chữ ký.</small>
    </div>
    <LotusMobileButton v-if="profile.has_signature" type="button" :disabled="saving" @click="remove">Xóa chữ ký</LotusMobileButton>
    <p v-if="notice" class="lotus-signature-notice" role="status">{{notice}}</p>
    <p class="lotus-signature-warning">Ảnh chữ ký chỉ được gắn vào chứng từ sau khi tài khoản có quyền bấm Duyệt. Đây là chữ ký bằng hình ảnh, không phải chữ ký số có chứng thư.</p>
   </template>
  </div>
  <LotusMobileDialog ref="deleteDialog" class="mobile-leave-dialog" @cancel.prevent="finishDelete(false)">
   <div class="mobile-leave-content"><h2>Xóa chữ ký?</h2><p>{{deleteMessage}}</p><div><LotusMobileButton type="button" @click="finishDelete(false)">Hủy</LotusMobileButton><LotusMobileButton type="button" variant="danger" @click="finishDelete(true)">Xóa</LotusMobileButton></div></div>
  </LotusMobileDialog>
 </section>
</template>