<script setup>
// Người giao hàng khi nhận theo đơn (spec 003, FR-041, FR-042): chữ ký tay trên màn hình kèm họ tên, hoặc ảnh phiếu
// giao hàng có chữ ký; cùng ảnh hàng và hóa đơn. Mọi thứ chờ ở trình duyệt đến lúc xác nhận nhập kho: collect() tải
// tệp lên (mỗi tệp một lần, bấm lại không tải lại) và trả đúng các tham số của warehouse_planning.receive_order.
import {computed,ref,watch} from 'vue'
import SignaturePad from '../signing/SignaturePad.vue'
import LotusField from '../form/LotusField.vue'
import FormSection from '../form/FormSection.vue'
import LotusMobileButton from '../LotusMobileButton.vue'
import LotusMobileInput from '../LotusMobileInput.vue'
import LotusSignatureDraw from '../LotusSignatureDraw.vue'
import LotusIcon from '../LotusIcon.vue'
import {Button} from '../ui/button'
import {FilePickerButton} from '../ui/file-input'
import {upload} from '../../api'

const props=defineProps({mobile:Boolean,disabled:Boolean,required:Boolean,uploader:Function})
const emit=defineEmits(['update:valid'])
const name=ref(''),signature=ref(''),drawn=ref(false),proof=ref(null),photos=ref([]),drawing=ref(false),pad=ref(null)
const uploaded=new Map()
const signed=computed(()=>props.mobile?!!signature.value:drawn.value)
// One of the two is enough: the deliverer's signature with their name, or the signed delivery note.
const complete=computed(()=>(signed.value&&name.value.trim().length>0)||!!proof.value)
const valid=computed(()=>!props.required||complete.value)
const missing=computed(()=>valid.value?'':signed.value&&!name.value.trim()?'Ghi họ tên người giao hàng bên cạnh chữ ký.':'Cần chữ ký kèm họ tên của người giao hàng, hoặc ảnh phiếu giao hàng có chữ ký.')
watch(valid,value=>emit('update:valid',value),{immediate:true})
const label=file=>file?.name||'tệp'
function addPhotos(files){photos.value=[...photos.value,...files].slice(0,20)}
function clearSignature(){signature.value='';drawn.value=false;pad.value?.clear()}
function reset(){name.value='';proof.value=null;photos.value=[];uploaded.clear();clearSignature()}
const dirty=()=>!!(name.value.trim()||signed.value||proof.value||photos.value.length)
async function collect(){
 const send=props.uploader||upload
 const url=async file=>{if(!uploaded.has(file))uploaded.set(file,(await send(file)).file_url);return uploaded.get(file)}
 const delivery_proof=proof.value?await url(proof.value):''
 const files=[]
 for(const file of photos.value)files.push(await url(file))
 return {deliverer_name:name.value.trim(),deliverer_signature:props.mobile?signature.value:(drawn.value?pad.value?.toDataURL()||'':''),delivery_proof,files}
}
defineExpose({collect,reset,dirty,valid})
</script>

<template>
 <section v-if="mobile" class="delivery-evidence delivery-evidence--mobile" aria-label="Người giao hàng">
  <h3>Người giao hàng</h3>
  <p class="delivery-evidence__note">{{required?'Cần một trong hai: người giao ký trên màn hình kèm họ tên, hoặc ảnh phiếu giao hàng có chữ ký.':'Người giao ký trên màn hình, hoặc chụp phiếu giao hàng có chữ ký.'}}</p>
  <LotusMobileInput v-model="name" label="Họ tên người giao hàng" :disabled="disabled" maxlength="140" placeholder="Người của nhà cung cấp hoặc nhà xe"/>
  <img v-if="signature" class="delivery-evidence__signature" :src="signature" alt="Chữ ký người giao hàng">
  <LotusMobileButton type="button" :disabled="disabled" @click="drawing=true">{{signature?'Người giao ký lại':'Người giao ký trên màn hình'}}</LotusMobileButton>
  <FilePickerButton :as="LotusMobileButton" accept="image/*" capture="environment" label="Chụp phiếu giao hàng có chữ ký" :disabled="disabled" @files="files=>proof=files[0]">{{proof?'Chụp lại phiếu giao hàng':'Chụp phiếu giao hàng có chữ ký'}}</FilePickerButton>
  <p v-if="proof" class="delivery-evidence__file"><span>Phiếu giao hàng: {{label(proof)}}</span><LotusMobileButton type="button" :aria-label="'Bỏ '+label(proof)" :disabled="disabled" @click="proof=null">Bỏ</LotusMobileButton></p>
  <FilePickerButton :as="LotusMobileButton" accept="image/*,application/pdf" multiple label="Thêm ảnh hàng, hóa đơn" :disabled="disabled" @files="addPhotos">Thêm ảnh hàng, hóa đơn</FilePickerButton>
  <p v-for="(file,index) in photos" :key="index+label(file)" class="delivery-evidence__file"><span>{{label(file)}}</span><LotusMobileButton type="button" :aria-label="'Bỏ '+label(file)" :disabled="disabled" @click="photos=photos.filter((_,i)=>i!==index)">Bỏ</LotusMobileButton></p>
  <p v-if="missing" class="delivery-evidence__missing" role="status">{{missing}}</p>
  <LotusSignatureDraw v-if="drawing" :show="drawing" title="Người giao hàng ký" @save="data=>{signature=data;drawing=false}" @cancel="drawing=false"/>
 </section>
 <FormSection v-else class="delivery-evidence" title="Người giao hàng" :description="required?'Cần một trong hai: chữ ký kèm họ tên của người giao hàng, hoặc ảnh phiếu giao hàng có chữ ký.':'Chữ ký kèm họ tên của người giao hàng, hoặc ảnh phiếu giao hàng có chữ ký.'">
  <div class="delivery-evidence__columns">
   <div class="delivery-evidence__sign">
    <LotusField v-model="name" label="Họ tên người giao hàng" :disabled="disabled" maxlength="140" placeholder="Người của nhà cung cấp hoặc nhà xe"/>
    <span class="lotus-form-note">Người giao ký vào khung dưới (chuột hoặc màn hình cảm ứng).</span>
    <SignaturePad ref="pad" :height="150" label="Chữ ký người giao hàng" @change="drawn=$event"/>
    <Button type="button" variant="outline" size="sm" :disabled="disabled||!drawn" @click="clearSignature">Xóa và ký lại</Button>
   </div>
   <div class="delivery-evidence__files">
    <span class="lotus-form-note">Hoặc đính kèm phiếu giao hàng đã có chữ ký của người giao.</span>
    <FilePickerButton accept="image/*,application/pdf" label="Ảnh phiếu giao hàng có chữ ký" size="sm" :disabled="disabled" @files="files=>proof=files[0]"><LotusIcon name="upload"/>{{proof?'Đổi ảnh phiếu giao hàng':'Ảnh phiếu giao hàng có chữ ký'}}</FilePickerButton>
    <p v-if="proof" class="delivery-evidence__file"><span>{{label(proof)}}</span><Button type="button" variant="ghost" size="sm" :aria-label="'Bỏ '+label(proof)" :disabled="disabled" @click="proof=null"><LotusIcon name="x"/></Button></p>
    <FilePickerButton accept="image/*,application/pdf" multiple label="Ảnh hàng, hóa đơn" size="sm" :disabled="disabled" @files="addPhotos"><LotusIcon name="upload"/>Thêm ảnh hàng, hóa đơn</FilePickerButton>
    <p v-for="(file,index) in photos" :key="index+label(file)" class="delivery-evidence__file"><span>{{label(file)}}</span><Button type="button" variant="ghost" size="sm" :aria-label="'Bỏ '+label(file)" :disabled="disabled" @click="photos=photos.filter((_,i)=>i!==index)"><LotusIcon name="x"/></Button></p>
   </div>
  </div>
  <p v-if="missing" class="delivery-evidence__missing" role="status">{{missing}}</p>
 </FormSection>
</template>

<style>
.delivery-evidence__columns{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:var(--lotus-space-4,16px)}
.delivery-evidence__sign,.delivery-evidence__files{display:grid;gap:var(--lotus-space-2,8px);align-content:start;min-width:0}
.delivery-evidence__file{display:flex;align-items:center;justify-content:space-between;gap:var(--lotus-space-2,8px);margin:0;min-width:0;font-size:var(--lotus-text-sm)}
.delivery-evidence__file span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.delivery-evidence__missing{margin:0;color:var(--lotus-warning-800,var(--lotus-text));font-size:var(--lotus-text-sm)}
.delivery-evidence--mobile{display:grid;gap:var(--lotus-space-2,8px);min-width:0}
.delivery-evidence--mobile h3{margin:0;font-size:var(--lotus-text-md)}
.delivery-evidence__note{margin:0;color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.delivery-evidence__signature{max-width:100%;max-height:120px;justify-self:start;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px);background:var(--lotus-surface)}
</style>
