<script setup>
// Canvas for a hand-drawn signature, without any UI kit: the phone sheet (Vant), the desktop modal and the
// deliverer's signature at receiving all use it. Ink colour comes from --lotus-signature-ink.
import {ref,onMounted,onBeforeUnmount,nextTick} from 'vue'
const props=defineProps({height:{type:Number,default:190},label:{type:String,default:'Vùng vẽ chữ ký'}})
const emit=defineEmits(['change'])
const canvas=ref(null),drawn=ref(false)
let down=false,previous=null
function setup(){
 const el=canvas.value
 if(!el)return
 const ratio=Math.min(3,globalThis.devicePixelRatio||1)
 const width=el.clientWidth||320
 el.width=Math.floor(width*ratio)
 el.height=Math.floor(props.height*ratio)
 const ctx=el.getContext?.('2d')
 if(!ctx)return
 ctx.scale(ratio,ratio)
 const ink=globalThis.getComputedStyle?.(el).getPropertyValue('--lotus-signature-ink').trim()
 ctx.strokeStyle=ink||'black'
 ctx.lineWidth=2.4
 ctx.lineCap='round'
 ctx.lineJoin='round'
 drawn.value=false
 previous=null
 emit('change',false)
}
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
 previous=next
 if(!drawn.value){drawn.value=true;emit('change',true)}
 event.preventDefault()
}
function stop(){down=false;previous=null}
function clear(){setup()}
function toDataURL(){return drawn.value&&canvas.value?canvas.value.toDataURL('image/png'):''}
onMounted(async()=>{await nextTick();setup()})
onBeforeUnmount(stop)
defineExpose({clear,toDataURL,reset:setup,isEmpty:()=>!drawn.value})
</script>
<template>
 <canvas ref="canvas" class="lotus-signature-pad" :style="{height:height+'px'}" :aria-label="label" role="img"
  @pointerdown="start" @pointermove="move" @pointerup="stop" @pointercancel="stop" @lostpointercapture="stop"></canvas>
</template>
<style>
.lotus-signature-pad{width:100%;background:white;border:2px dashed var(--lotus-border);border-radius:12px;touch-action:none;display:block}
</style>
