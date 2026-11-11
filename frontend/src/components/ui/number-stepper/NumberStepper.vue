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
 // From empty, + gives one step (1 buồng, 0,5 kg) or the minimum if that is larger; − gives the minimum.
 if(number.value===null){model.value=round(clamp(direction>0?Math.max(props.min,props.step):props.min));return}
 model.value=round(clamp(number.value+direction*props.step))
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

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-stepper{display:inline-grid;grid-template-columns:auto minmax(56px,1fr) auto;align-items:stretch;min-width:0;border:1px solid var(--lotus-border-control);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);overflow:hidden}
.lotus-stepper:focus-within{box-shadow:var(--lotus-focus)}
.lotus-stepper__btn{display:grid;place-items:center;width:var(--lotus-control-height);min-height:var(--lotus-control-height);padding:0;border:0;background:var(--lotus-soft);color:var(--lotus-text-strong);cursor:pointer;touch-action:manipulation;user-select:none}
.lotus-stepper__btn:hover{background:var(--lotus-hover)}
.lotus-stepper__btn:active{background:var(--lotus-active)}
.lotus-stepper__btn:disabled{color:var(--lotus-disabled);cursor:not-allowed;background:var(--lotus-soft)}
.lotus-stepper__btn .lotus-icon{width:18px;height:18px;stroke-width:2.2}
.lotus-stepper .lotus-stepper__input{width:100%;min-width:0;min-height:var(--lotus-control-height);margin:0;padding:0 4px;border:0;border-left:1px solid var(--lotus-border);border-right:1px solid var(--lotus-border);border-radius:0;background:transparent;color:var(--lotus-text-strong);font:inherit;font-size:var(--lotus-text-lg);font-weight:var(--lotus-weight-semibold);font-variant-numeric:tabular-nums;text-align:center;box-shadow:none;outline:none;-moz-appearance:textfield}
.lotus-stepper .lotus-stepper__input::-webkit-inner-spin-button,.lotus-stepper .lotus-stepper__input::-webkit-outer-spin-button{-webkit-appearance:none;margin:0}
.lotus-stepper__unit{align-self:center;padding:0 10px 0 0;color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.lotus-stepper--lg .lotus-stepper__btn{width:var(--lotus-touch-lg);min-height:var(--lotus-touch-lg)}
.lotus-stepper--lg .lotus-stepper__btn .lotus-icon{width:24px;height:24px}
.lotus-stepper--lg .lotus-stepper__input{min-height:var(--lotus-touch-lg);font-size:var(--lotus-text-2xl)}
.lotus-stepper--block{display:grid;width:100%}
.lotus-stepper--unit{grid-template-columns:auto minmax(48px,1fr) auto auto}
.lotus-stepper--unit .lotus-stepper__input{border-right:0}
.lotus-stepper--unit .lotus-stepper__unit{border-right:1px solid var(--lotus-border)}
</style>
