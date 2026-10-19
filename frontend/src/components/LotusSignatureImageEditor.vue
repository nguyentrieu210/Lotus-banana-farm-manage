<script setup>
import {ref,watch,nextTick,onBeforeUnmount} from 'vue'
import {Popup,Slider,Switch,Icon} from 'vant'
import Cropper from 'cropperjs'
import './lotus-signature-editor.css'

const props=defineProps({show:Boolean,source:{type:String,default:''}})
const emit=defineEmits(['cancel','save'])
const host=ref(null),image=ref(null),preview=ref('')
const screen=ref('crop'),removeBackground=ref(true),strength=ref(38),busy=ref(false),message=ref('')
let cropper=null

function teardown(){
 try{cropper?.destroy()}catch{}
 cropper=null
 preview.value=''
 screen.value='crop'
 busy.value=false
 message.value=''
}
async function setup(){
 teardown()
 if(!props.show||!props.source)return
 await nextTick()
 // Cropper.js controls a native image element, including touch/pinch gestures.
 if(!host.value||!image.value)return
 cropper=new Cropper(image.value,{container:host.value})
 cropper.getCropperSelection()?.$reset?.()
}
watch(()=>[props.show,props.source],()=>setup(),{flush:'post'})
onBeforeUnmount(teardown)
function transformImage(method,arg){
 const el=cropper?.getCropperImage()
 if(!el)return
 if(method==='rotate')el.$rotate(arg)
 if(method==='zoom')el.$zoom(arg)
}
function reset(){cropper?.getCropperImage()?.$resetTransform?.();cropper?.getCropperSelection()?.$reset?.();preview.value='';screen.value='crop'}
function processCanvas(source){
 const factor=Math.min(1,1200/source.width,700/source.height)
 const canvas=document.createElement('canvas')
 canvas.width=Math.max(1,Math.round(source.width*factor))
 canvas.height=Math.max(1,Math.round(source.height*factor))
 const context=canvas.getContext('2d',{willReadFrequently:true})
 if(!context)throw Error('Thiết bị không hỗ trợ chỉnh ảnh này.')
 context.drawImage(source,0,0,canvas.width,canvas.height)
 if(removeBackground.value){
  const pixels=context.getImageData(0,0,canvas.width,canvas.height)
  const data=pixels.data
  const low=172+(100-strength.value)*0.53 // Default near-white background removal
  for(let index=0;index<data.length;index+=4){
   const r=data[index],g=data[index+1],b=data[index+2]
   const minimum=Math.min(r,g,b)
   // Preserve blue ink and dark strokes; transparent only near-neutral, light paper.
   const spread=Math.max(r,g,b)-minimum
   if(spread<32&&minimum>low){
    const alpha=Math.max(0,Math.min(255,(245-minimum)*13))
    data[index+3]=Math.min(data[index+3],alpha)
   }
  }
  context.putImageData(pixels,0,0)
 }
 return canvas.toDataURL('image/png')
}
async function seePreview(){
 if(busy.value)return
 busy.value=true;message.value=''
 try{
  const selection=cropper?.getCropperSelection()
  if(!selection)throw Error('Không nhận được vùng cắt ảnh. Hãy chọn ảnh khác.')
  const canvas=await selection.$toCanvas({width:1100})
  if(!canvas?.width||!canvas?.height)throw Error('Vùng chọn quá nhỏ. Hãy cắt lại.')
  preview.value=processCanvas(canvas)
  screen.value='preview'
 }catch(error){message.value=error.message||'Không thể xử lý ảnh này.'}
 finally{busy.value=false}
}
function save(){if(preview.value&&!busy.value)emit('save',preview.value)}
function cancel(){emit('cancel')}
</script>

<template>
 <Popup :show="show" position="bottom" round :close-on-click-overlay="false" :close-on-popstate="false"
  class="lotus-signature-editor" @update:show="value=>{if(!value)cancel()}">
  <div class="lotus-signature-editor-layout">
   <header class="lotus-signature-editor-header">
    <button type="button" aria-label="Hủy chỉnh ảnh" @click="cancel"><Icon name="cross"/></button>
    <strong>{{screen==='crop'?'Cắt ảnh chữ ký':'Xem trước chữ ký'}}</strong>
    <button v-if="screen==='crop'" type="button" @click="reset">Đặt lại</button>
    <button v-else type="button" @click="screen='crop'">Sửa lại</button>
   </header>
   <div v-show="screen==='crop'" class="lotus-signature-editor-workspace">
    <div ref="host" class="lotus-signature-cropper-area">
     <img ref="image" :src="source" alt="Ảnh chữ ký đang cắt" style="display:block;max-width:100%"/>
    </div>
    <p class="lotus-signature-editor-help">Kéo khung để giữ phần chữ ký. Dùng hai ngón để phóng to ảnh.</p>
    <div class="lotus-signature-editor-tools">
     <button type="button" @click="transformImage('rotate','-90deg')"><Icon name="replay"/> Xoay trái</button>
     <button type="button" @click="transformImage('rotate','90deg')"><Icon name="replay" class="lotus-signature-rotate-right"/> Xoay phải</button>
     <button type="button" @click="transformImage('zoom',0.12)"><Icon name="plus"/> Phóng to</button>
     <button type="button" @click="transformImage('zoom',-0.12)"><Icon name="minus"/> Thu nhỏ</button>
    </div>
    <div class="lotus-signature-editor-background">
     <span>Xóa nền giấy</span>
     <Switch v-model="removeBackground" size="22px" aria-label="Xóa nền trắng tự động"/>
    </div>
    <label v-if="removeBackground" class="lotus-signature-editor-strength">
     <span>Độ mạnh xóa nền: {{strength}}%</span>
     <Slider v-model="strength" :min="0" :max="100" :step="5" aria-label="Độ mạnh xóa nền"/>
    </label>
   </div>
   <div v-if="screen==='preview'" class="lotus-signature-editor-preview">
    <p>Ảnh sau cắt và xử lý nền:</p>
    <div class="lotus-signature-editor-paper"><img :src="preview" alt="Chữ ký trong suốt xem trước"/></div>
    <p class="lotus-signature-editor-help">Đây là mẫu chữ ký sẽ dùng trên phiếu PDF. Chỉ lưu khi đã đúng.</p>
   </div>
   <p v-if="message" class="lotus-signature-editor-error" role="alert">{{message}}</p>
   <footer class="lotus-signature-editor-footer">
    <button type="button" class="lotus-signature-editor-secondary" @click="cancel">Hủy</button>
    <button v-if="screen==='crop'" type="button" class="lotus-signature-editor-primary" :disabled="busy" @click="seePreview">{{busy?'Đang xử lý…':'Xem trước'}}</button>
    <button v-else type="button" class="lotus-signature-editor-primary" :disabled="busy" @click="save">Dùng ảnh này</button>
   </footer>
  </div>
 </Popup>
</template>
