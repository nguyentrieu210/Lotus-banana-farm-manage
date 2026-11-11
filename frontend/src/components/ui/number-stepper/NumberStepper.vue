<script setup>
import {computed,onBeforeUnmount,useId} from 'vue'
import LotusIcon from '../../LotusIcon.vue'
// Number with − and + (spec 004, FR-023, User Story 4): large targets on phones (size="lg"), holding a button
// repeats, the keyboard stays numeric, a comma or a dot both work as the decimal mark. Empty stays empty (null):
// a count that was not entered is not 0.
const props=defineProps({label:{type:String,required:true},min:{type:Number,default:0},max:{type:Number,default:Number.POSITIVE_INFINITY},step:{type:Number,default:1},decimals:{type:Number,default:0},unit:String,size:{type:String,default:'md'},block:Boolean,disabled:Boolean})
const model=defineModel({type:[Number,String],default:null})
const id=useId()
const number=computed(()=>{const v=model.value;if(v===null||v===undefined||v==='')return null;const n=Number(String(v).replace(',','.'));return Number.isFinite(n)?n:null})
const shown=computed(()=>number.value===null?'':String(number.value).replace('.',','))
const clamp=v=>Math.min(props.max,Math.max(props.min,v))
const round=v=>Number(v.toFixed(props.decimals))
function bump(direction){
 if(props.disabled)return
 const base=number.value===null?(direction>0?props.min-props.step:props.min):number.value
 model.value=round(clamp(base+direction*props.step))
}
function typed(text){
 const clean=String(text).trim().replace(',','.')
 if(clean===''){model.value=null;return}
 const n=Number(clean)
 if(Number.isFinite(n))model.value=n
}
function settle(){if(number.value!==null)model.value=round(clamp(number.value))}
// Hold to repeat: after 400 ms, one step every 90 ms. The click that ends a hold is ignored.
let timer=null,repeated=false
function hold(direction){
 release();repeated=false
 timer=setTimeout(function tick(){repeated=true;bump(direction);timer=setTimeout(tick,90)},400)
}
function release(){clearTimeout(timer);timer=null}
function click(direction){if(repeated){repeated=false;return}bump(direction)}
onBeforeUnmount(release)
</script>
<template>
 <div class="lotus-stepper" :class="{'lotus-stepper--lg':size==='lg','lotus-stepper--block':block,'lotus-stepper--unit':unit}">
  <button type="button" class="lotus-stepper__btn" :disabled="disabled||(number!==null&&number<=min)" :aria-label="'Bớt '+String(step).replace('.',',')+(unit?' '+unit:'')" :aria-controls="id" @click="click(-1)" @pointerdown="hold(-1)" @pointerup="release" @pointerleave="release" @pointercancel="release"><LotusIcon name="minus"/></button>
  <input :id="id" class="lotus-stepper__input" type="text" :inputmode="decimals?'decimal':'numeric'" autocomplete="off" :value="shown" :aria-label="label+(unit?' ('+unit+')':'')" :disabled="disabled" @input="typed($event.target.value)" @blur="settle" @keydown.up.prevent="bump(1)" @keydown.down.prevent="bump(-1)">
  <span v-if="unit" class="lotus-stepper__unit" aria-hidden="true">{{unit}}</span>
  <button type="button" class="lotus-stepper__btn" :disabled="disabled||(number!==null&&number>=max)" :aria-label="'Thêm '+String(step).replace('.',',')+(unit?' '+unit:'')" :aria-controls="id" @click="click(1)" @pointerdown="hold(1)" @pointerup="release" @pointerleave="release" @pointercancel="release"><LotusIcon name="plus"/></button>
 </div>
</template>
