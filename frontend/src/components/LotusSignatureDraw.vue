<script setup>
import {ref,watch,nextTick,onBeforeUnmount} from 'vue'
import {Popup,Icon} from 'vant'
const props=defineProps({show:Boolean,title:{type:String,default:'Vẽ chữ ký'}})
const emit=defineEmits(['save','cancel'])
const canvas=ref(null),drawn=ref(false)
let down=false,previous=null
function initCanvas(){
 const el=canvas.value
 if(!el)return
 const ratio=Math.min(3,window.devicePixelRatio||1)
 const width=el.clientWidth||320
 el.width=Math.floor(width*ratio)
 el.height=Math.floor(190*ratio)
 const ctx=el.getContext('2d')
 ctx.scale(ratio,ratio)
 ctx.strokeStyle='#133b86'
 ctx.lineWidth=2.4
 ctx.lineCap='round'
 ctx.lineJoin='round'
 drawn.value=false
 previous=null
}
watch(()=>props.show,async showing=>{if(showing){await nextTick();initCanvas()}},{flush:'post'})
function pos(event){const rect=canvas.value.getBoundingClientRect();return {x:event.clientX-rect.left,y:event.clientY-rect.top}}
function start(event){
 if(!canvas.value)return
 down=true;previous=pos(event)
 canvas.value.setPointerCapture?.(event.pointerId)
 event.preventDefault()
}
function move(event){
 if(!down||!previous)return
 const next=pos(event),ctx=canvas.value.getContext('2d')
 ctx.beginPath();ctx.moveTo(previous.x,previous.y);ctx.lineTo(next.x,next.y);ctx.stroke()
 previous=next;drawn.value=true
 event.preventDefault()
}
function stop(){down=false;previous=null}
function clear(){initCanvas()}
function save(){
 if(!drawn.value||!canvas.value)return
 emit('save',canvas.value.toDataURL('image/png'))
}
onBeforeUnmount(stop)
</script>
<template>
 <Popup :show="show" position="bottom" round :close-on-click-overlay="false" class="lotus-signature-draw" @update:show="open=>{if(!open)emit('cancel')}">
  <div class="lotus-signature-draw-body">
   <header><strong>{{title}}</strong><button type="button" aria-label="Đóng vẽ chữ ký" @click="emit('cancel')"><Icon name="cross"/></button></header>
   <p>Dùng ngón tay vẽ chữ ký trên khung trắng. Bản vẽ chỉ lưu sau khi bấm Dùng chữ ký này.</p>
   <canvas ref="canvas" class="lotus-signature-draw-canvas" aria-label="Vùng vẽ chữ ký" @pointerdown="start" @pointermove="move" @pointerup="stop" @pointercancel="stop" @lostpointercapture="stop"></canvas>
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