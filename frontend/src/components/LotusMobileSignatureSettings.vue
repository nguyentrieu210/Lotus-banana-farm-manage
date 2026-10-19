<script setup>
import {ref,watch,onBeforeUnmount} from 'vue'
import {Icon} from 'vant'
import {call} from '../api'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileDialog from './LotusMobileDialog.vue'
import LotusSignatureImageEditor from './LotusSignatureImageEditor.vue'
import LotusSignatureDraw from './LotusSignatureDraw.vue'
import {useMobileConfirm} from '../use-mobile-confirm'
import './lotus-mobile-signature.css'

const props=defineProps({user:{type:String,default:''}})
const expanded=ref(false),loading=ref(false),saving=ref(false),loaded=ref(false)
const profile=ref(null),error=ref(''),notice=ref(''),selectedFile=ref(''),uploadStep=ref(''),editorSrc=ref(''),editingKind=ref('signature'),showDraw=ref(false),dateBusy=ref(false)
const endpoint='lotus_farm.digital_signature.'
const {dialog:deleteDialog,message:deleteMessage,ask:askDelete,finish:finishDelete}=useMobileConfirm()
watch(()=>props.user,()=>{cancelEdit();expanded.value=false;loaded.value=false;profile.value=null;error.value='';notice.value='';selectedFile.value='';uploadStep.value=''})
onBeforeUnmount(cancelEdit)
function cancelEdit(){const old=editorSrc.value;editorSrc.value='';showDraw.value=false;if(old)URL.revokeObjectURL(old)}
async function load(){
 if(!props.user)return
 loading.value=true;error.value=''
 try{profile.value=await call(endpoint+'my_signature_profile');loaded.value=true}
 catch(e){error.value=e.message||'Không tải được chữ ký.'}
 finally{loading.value=false}
}
async function toggle(){expanded.value=!expanded.value;if(expanded.value&&!loaded.value)await load()}
async function chooseFile(event,kind='signature'){
 editingKind.value=kind
 const input=event.target
 const file=input.files?.[0]
 if(!file||saving.value)return
 input.value=''
 error.value='';notice.value=''
 if(!['image/png','image/jpeg'].includes(file.type)&&!(/\.(png|jpe?g)$/i.test(file.name)&&(!file.type||file.type==='application/octet-stream'))){
  error.value='Chỉ nhận ảnh PNG hoặc JPG. Nếu là HEIC, hãy đổi sang JPG.'
  return
 }
 if(file.size>10000000){error.value='Ảnh phải nhỏ hơn 10 MB.';return}
 cancelEdit()
 selectedFile.value=file.name+' · '+(file.size/1000000).toFixed(1)+' MB'
 uploadStep.value='Cắt và xác nhận ảnh trước khi lưu.'
 editorSrc.value=URL.createObjectURL(file)
}
async function saveEdited(dataUrl){
 if(saving.value)return
 saving.value=true;error.value='';notice.value=''
 try{
  uploadStep.value='Đang gửi ảnh đã cắt lên Lotus…'
  profile.value=await call(endpoint+(editingKind.value==='initials'?'save_my_initials_image':'save_my_signature_image'),{image_data:dataUrl},true)
  uploadStep.value='Đã lưu ảnh chữ ký.'
  notice.value='Đã lưu chữ ký mới cho tài khoản của bạn.'
  cancelEdit()
 }catch(e){uploadStep.value='Lưu ảnh thất bại';error.value=e.message||'Không lưu được chữ ký. Hãy thử lại.'}
 finally{saving.value=false}
}
function startDrawing(kind){cancelEdit();editingKind.value=kind;showDraw.value=true}
async function updateDateFormat(event){
 if(!profile.value||dateBusy.value)return
 dateBusy.value=true;error.value=''
 try{profile.value=await call(endpoint+'save_my_signature_date_format',{date_format:event.target.value},true)}
 catch(e){error.value=e.message||'Không lưu được định dạng ngày ký.'}
 finally{dateBusy.value=false}
}
async function removeInitials(){
 if(saving.value||!profile.value?.has_initials)return
 if(!await askDelete('Xóa mẫu ký nháy đã lưu của tài khoản?'))return
 saving.value=true;error.value=''
 try{profile.value=await call(endpoint+'remove_my_initials_image',{},true);notice.value='Đã xóa mẫu ký nháy.'}
 catch(e){error.value=e.message||'Không xóa được ký nháy.'}
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
      aria-label="Chọn ảnh chữ ký từ điện thoại" @change="event=>chooseFile(event,'signature')"/>
     <p v-if="selectedFile" class="lotus-signature-selected-file">{{selectedFile}}</p>
     <p v-if="uploadStep" class="lotus-signature-upload-step" role="status">{{uploadStep}}</p>
     <small>Nên dùng ảnh PNG nền trong suốt hoặc ảnh JPG chụp trên giấy trắng, chỉ chứa chữ ký.</small>
     <LotusMobileButton type="button" :disabled="saving" @click="startDrawing('signature')">Vẽ chữ ký bằng ngón tay</LotusMobileButton>
    </div>
    <LotusMobileButton v-if="profile.has_signature" type="button" :disabled="saving" @click="remove">Xóa chữ ký</LotusMobileButton>
    <div class="lotus-signature-initials">
     <strong>Ký nháy (ký tắt)</strong>
     <p class="lotus-signature-hint">Lưu riêng mẫu ký nháy để dùng ở bước kiểm tra chứng từ, không thay quyền duyệt.</p>
     <div v-if="profile.has_initials" class="lotus-signature-preview">
      <img :src="profile.initials_preview" alt="Mẫu ký nháy đã lưu"/>
     </div>
     <label for="lotus-initials-photo-file" class="lotus-signature-upload-label">Chọn ảnh ký nháy</label>
     <input id="lotus-initials-photo-file" class="lotus-signature-visible-input" type="file"
      accept="image/jpeg,image/png,.jpg,.jpeg,.png" :disabled="saving||!profile.configured"
      aria-label="Tải ảnh ký nháy" @change="event=>chooseFile(event,'initials')"/>
     <LotusMobileButton type="button" :disabled="saving" @click="startDrawing('initials')">Vẽ ký nháy</LotusMobileButton>
     <LotusMobileButton v-if="profile.has_initials" type="button" :disabled="saving" @click="removeInitials">Xóa ký nháy</LotusMobileButton>
    </div>
    <label class="lotus-signature-date-settings">Cách hiển thị ngày ký trên PDF
     <select :value="profile.date_format||'DD/MM/YYYY'" :disabled="dateBusy" @change="updateDateFormat">
      <option value="DD/MM/YYYY">19/10/2026</option>
      <option value="DD-MM-YYYY">19-10-2026</option>
      <option value="LONG_VI">Ngày 19 tháng 10 năm 2026</option>
     </select>
    </label>
    <p class="lotus-signature-hint">Chỉ đổi kiểu hiển thị; thời điểm duyệt thực luôn lấy từ máy chủ.</p>
    <p v-if="notice" class="lotus-signature-notice" role="status">{{notice}}</p>
    <p class="lotus-signature-warning">Ảnh chữ ký chỉ được gắn vào chứng từ sau khi tài khoản có quyền bấm Duyệt. Đây là chữ ký bằng hình ảnh, không phải chữ ký số có chứng thư.</p>
   </template>
  </div>
  <LotusSignatureImageEditor :show="!!editorSrc" :source="editorSrc" :type-label="editingKind==='initials'?'ký nháy':'chữ ký'" @cancel="cancelEdit" @save="saveEdited"/>
  <LotusSignatureDraw :show="showDraw" :title="editingKind==='initials'?'Vẽ ký nháy':'Vẽ chữ ký'" @cancel="cancelEdit" @save="saveEdited"/>
  <LotusMobileDialog ref="deleteDialog" class="mobile-leave-dialog" @cancel.prevent="finishDelete(false)">
   <div class="mobile-leave-content"><h2>Xóa chữ ký?</h2><p>{{deleteMessage}}</p><div><LotusMobileButton type="button" @click="finishDelete(false)">Hủy</LotusMobileButton><LotusMobileButton type="button" variant="danger" @click="finishDelete(true)">Xóa</LotusMobileButton></div></div>
  </LotusMobileDialog>
 </section>
</template>