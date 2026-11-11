<script setup>
// Phone sheet around the shared SignaturePad (spec 003, FR-018): draw, clear, use.
import {ref,watch,nextTick} from 'vue'
import {Popup,Icon} from 'vant'
import SignaturePad from './signing/SignaturePad.vue'
const props=defineProps({show:Boolean,title:{type:String,default:'Vẽ chữ ký'}})
const emit=defineEmits(['save','cancel'])
const pad=ref(null),drawn=ref(false)
watch(()=>props.show,async showing=>{if(showing){await nextTick();pad.value?.reset()}},{flush:'post'})
function clear(){pad.value?.clear()}
function save(){const data=pad.value?.toDataURL();if(data)emit('save',data)}
</script>
<template>
 <Popup :show="show" position="bottom" round :close-on-click-overlay="false" class="lotus-signature-draw" @update:show="open=>{if(!open)emit('cancel')}">
  <div class="lotus-signature-draw-body">
   <header><strong>{{title}}</strong><button type="button" aria-label="Đóng vẽ chữ ký" @click="emit('cancel')"><Icon name="cross"/></button></header>
   <p>Dùng ngón tay vẽ chữ ký trên khung trắng. Bản vẽ chỉ lưu sau khi bấm Dùng chữ ký này.</p>
   <SignaturePad ref="pad" class="lotus-signature-draw-canvas" :height="190" @change="drawn=$event"/>
   <footer><button type="button" @click="clear">Xóa và vẽ lại</button><button type="button" :disabled="!drawn" @click="save">Dùng chữ ký này</button></footer>
  </div>
 </Popup>
</template>
<style>
.lotus-signature-draw.van-popup{width:100%;max-width:650px;left:50%;transform:translateX(-50%);background:var(--lotus-surface);color:var(--lotus-text)}
.lotus-signature-draw-body{padding:16px 16px max(24px,env(safe-area-inset-bottom))}
.lotus-signature-draw header{display:flex;align-items:center;justify-content:space-between}
.lotus-signature-draw strong{font-size:18px}.lotus-signature-draw p{font-size:13px;color:var(--lotus-muted)}
.lotus-signature-draw button{border:1px solid var(--lotus-border);background:var(--lotus-surface);color:var(--lotus-text);border-radius:10px;padding:10px;min-height:46px}
.lotus-signature-draw-canvas{width:100%;height:190px;background:#fff;border:2px dashed var(--lotus-border);border-radius:12px;touch-action:none;display:block}
.lotus-signature-draw footer{display:flex;gap:10px;margin-top:16px}
.lotus-signature-draw footer button{flex:1}
.lotus-signature-draw footer button:last-child{background:var(--lotus-primary);color:var(--lotus-on-primary)}
.lotus-signature-draw button:disabled{opacity:.5}
</style>