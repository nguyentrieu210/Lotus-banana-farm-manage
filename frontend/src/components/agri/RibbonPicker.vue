<script setup>
import RibbonDot from './RibbonDot.vue'
import {ribbonLabel} from '../../ribbon-colors.js'
// Pick the ribbon batch for a bunch entry (FR-031, User Story 4): large radio buttons with the colour, name and week.
// options: [{code, value?, label?, week?, hint?}]; v-model is the option's value (its code when it has none), so two
// batches of one colour (different weeks) stay apart. Arrow keys move between options.
const props=defineProps({options:{type:Array,required:true},label:{type:String,required:true}})
const model=defineModel({type:String,default:''})
const valueOf=o=>o.value??o.code
function move(event,index){
 const step=event.key==='ArrowRight'||event.key==='ArrowDown'?1:event.key==='ArrowLeft'||event.key==='ArrowUp'?-1:0
 if(!step)return
 event.preventDefault()
 const next=(index+step+props.options.length)%props.options.length
 model.value=valueOf(props.options[next])
 event.currentTarget.parentElement?.children[next]?.focus()
}
</script>
<template>
 <div class="lotus-ribbon-pick" role="radiogroup" :aria-label="label">
  <button v-for="(o,i) in options" :key="valueOf(o)+(o.week||'')" type="button" role="radio" class="lotus-ribbon-pick__item" :aria-checked="model===valueOf(o)" :tabindex="model===valueOf(o)||(!model&&i===0)?0:-1" @click="model=valueOf(o)" @keydown="move($event,i)">
   <RibbonDot :code="o.code" size="lg" decorative/><span class="lotus-ribbon-pick__text"><strong>{{o.label||ribbonLabel(o.code)}}</strong><small v-if="o.week||o.hint">{{o.week?'Tuần '+o.week:''}}{{o.week&&o.hint?' · ':''}}{{o.hint}}</small></span>
  </button>
 </div>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-ribbon-pick{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:6px}
.lotus-ribbon-pick__item{display:flex;align-items:center;gap:10px;min-height:var(--lotus-touch);padding:6px 10px;border:1px solid var(--lotus-border-control);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);color:var(--lotus-text);font:inherit;text-align:left;cursor:pointer}
.lotus-ribbon-pick__item:hover{background:var(--lotus-hover)}
.lotus-ribbon-pick__item:focus-visible{outline:none;box-shadow:var(--lotus-focus)}
.lotus-ribbon-pick__item[aria-checked="true"]{border-color:var(--lotus-primary);background:var(--lotus-tone-primary-soft);box-shadow:inset 0 0 0 1px var(--lotus-primary)}
.lotus-ribbon-pick__text{display:grid;min-width:0;line-height:var(--lotus-leading-tight)}
.lotus-ribbon-pick__text strong{color:var(--lotus-text-strong);font-weight:var(--lotus-weight-semibold)}
.lotus-ribbon-pick__text small{color:var(--lotus-muted);font-size:var(--lotus-text-xs)}
</style>
