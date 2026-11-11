<script setup>
import RibbonDot from './RibbonDot.vue'
import {ribbonLabel} from '../../ribbon-colors.js'
// Pick the ribbon batch for a bunch entry (FR-031, User Story 4): large radio buttons with the colour, name and week.
// options: [{code, label?, week?, hint?}]; v-model is the chosen code. Arrow keys move between options.
const props=defineProps({options:{type:Array,required:true},label:{type:String,required:true}})
const model=defineModel({type:String,default:''})
function move(event,index){
 const step=event.key==='ArrowRight'||event.key==='ArrowDown'?1:event.key==='ArrowLeft'||event.key==='ArrowUp'?-1:0
 if(!step)return
 event.preventDefault()
 const next=(index+step+props.options.length)%props.options.length
 model.value=props.options[next].code
 event.currentTarget.parentElement?.children[next]?.focus()
}
</script>
<template>
 <div class="lotus-ribbon-pick" role="radiogroup" :aria-label="label">
  <button v-for="(o,i) in options" :key="o.code+(o.week||'')" type="button" role="radio" class="lotus-ribbon-pick__item" :aria-checked="model===o.code" :tabindex="model===o.code||(!model&&i===0)?0:-1" @click="model=o.code" @keydown="move($event,i)">
   <RibbonDot :code="o.code" size="lg" decorative/><span class="lotus-ribbon-pick__text"><strong>{{o.label||ribbonLabel(o.code)}}</strong><small v-if="o.week||o.hint">{{o.week?'Tuần '+o.week:''}}{{o.week&&o.hint?' · ':''}}{{o.hint}}</small></span>
  </button>
 </div>
</template>
