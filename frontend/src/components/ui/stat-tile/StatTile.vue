<script setup>
import {computed} from 'vue'
import LotusIcon from '../../LotusIcon.vue'
import {formatNumber,formatDelta} from '../../../agri-format.js'
// KPI tile (spec 004, FR-034): label, a big number with its unit, and the change against a reference.
// No number → "—" and the reason; never a 0 that was not measured (constitution I).
// goodWhen: 'up' (more is better), 'down' (less is better) — decides whether the change is shown as good or bad.
const props=defineProps({
 label:{type:String,required:true},value:{type:[Number,String],default:null},unit:String,digits:{type:Number,default:0},
 icon:String,tone:{type:String,default:'neutral'},
 delta:{type:Number,default:null},deltaDigits:{type:Number,default:0},deltaUnit:{type:String,default:''},deltaLabel:String,goodWhen:{type:String,default:'up'},
 missing:String,hint:String,as:{type:String,default:'article'},
})
const text=computed(()=>{
 const v=props.value
 if(typeof v==='string'&&v.trim()!==''&&!Number.isFinite(Number(v)))return v
 return formatNumber(v,{digits:props.digits})
})
const missingNow=computed(()=>text.value===null)
const trend=computed(()=>{
 if(missingNow.value||props.delta===null||props.delta===undefined)return null
 const d=Number(props.delta)
 if(!Number.isFinite(d))return null
 const dir=d>0?'up':d<0?'down':'flat'
 return {dir,good:dir==='flat'?'flat':dir===props.goodWhen?'good':'bad',text:formatDelta(d,{digits:props.deltaDigits})+props.deltaUnit}
})
</script>
<template>
 <component :is="as" class="lotus-stat" :class="['lotus-stat--'+tone,{'lotus-stat--missing':missingNow}]" :type="as==='button'?'button':undefined">
  <span class="lotus-stat__head"><span v-if="icon" class="lotus-stat__icon"><LotusIcon :name="icon"/></span><span class="lotus-stat__label">{{label}}</span></span>
  <p class="lotus-stat__value"><template v-if="!missingNow">{{text}}<span v-if="unit" class="lotus-stat__unit">{{unit}}</span></template><template v-else>—</template></p>
  <span class="lotus-stat__foot">
   <span v-if="missingNow">{{missing||'Chưa có số'}}</span>
   <template v-else>
    <span v-if="trend" class="lotus-stat__delta" :class="'lotus-stat__delta--'+trend.good"><LotusIcon v-if="trend.dir!=='flat'" :name="trend.dir==='up'?'arrow-up':'arrow-down'"/>{{trend.text}}<span class="lotus-sr-only">{{trend.good==='good'?' (tốt)':trend.good==='bad'?' (xấu)':''}}</span></span>
    <span v-if="trend&&deltaLabel">{{deltaLabel}}</span>
    <span v-if="hint">{{hint}}</span>
   </template>
   <slot name="foot"/>
  </span>
 </component>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-stat{--stat-accent:var(--lotus-border-strong);--stat-soft:var(--lotus-tone-neutral-soft);--stat-fg:var(--lotus-tone-neutral-text);
 position:relative;display:flex;flex-direction:column;gap:6px;min-width:0;padding:var(--lotus-card-padding);padding-top:calc(var(--lotus-card-padding) + 2px);
 border:1px solid var(--lotus-border);border-radius:var(--lotus-card-radius);background:var(--lotus-surface);box-shadow:var(--lotus-shadow-xs);overflow:hidden}
.lotus-stat::before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:var(--stat-accent)}
.lotus-stat__head{display:flex;align-items:center;gap:8px;min-width:0;color:var(--lotus-text-secondary);font-size:var(--lotus-text-sm);font-weight:var(--lotus-weight-medium)}
.lotus-stat__icon{flex:none;display:grid;place-items:center;width:26px;height:26px;border-radius:var(--lotus-radius-sm);background:var(--stat-soft);color:var(--stat-fg)}
.lotus-stat__icon .lotus-icon{width:16px;height:16px}
.lotus-stat__label{display:-webkit-box;overflow:hidden;-webkit-line-clamp:2;-webkit-box-orient:vertical;line-height:var(--lotus-leading-snug);overflow-wrap:anywhere}
.lotus-stat__value{margin:0;color:var(--lotus-text-strong);font-size:var(--lotus-text-3xl);font-weight:var(--lotus-weight-bold);letter-spacing:-.02em;line-height:1.1;font-variant-numeric:tabular-nums;white-space:nowrap}
.lotus-stat__unit{margin-left:5px;color:var(--lotus-muted);font-size:var(--lotus-text-base);font-weight:var(--lotus-weight-medium);letter-spacing:0}
.lotus-stat__foot{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;color:var(--lotus-muted);font-size:var(--lotus-text-sm);line-height:var(--lotus-leading-snug)}
.lotus-stat--missing .lotus-stat__value{color:var(--lotus-subtle);font-weight:var(--lotus-weight-semibold)}
.lotus-stat--primary{--stat-accent:var(--lotus-primary);--stat-soft:var(--lotus-tone-primary-soft);--stat-fg:var(--lotus-tone-primary-text)}
.lotus-stat--success{--stat-accent:var(--lotus-tone-success-solid);--stat-soft:var(--lotus-tone-success-soft);--stat-fg:var(--lotus-tone-success-text)}
.lotus-stat--warning{--stat-accent:var(--lotus-warning-400);--stat-soft:var(--lotus-tone-warning-soft);--stat-fg:var(--lotus-tone-warning-text)}
.lotus-stat--danger{--stat-accent:var(--lotus-tone-danger-solid);--stat-soft:var(--lotus-tone-danger-soft);--stat-fg:var(--lotus-tone-danger-text)}
.lotus-stat--info{--stat-accent:var(--lotus-tone-info-solid);--stat-soft:var(--lotus-tone-info-soft);--stat-fg:var(--lotus-tone-info-text)}
button.lotus-stat{font:inherit;text-align:left;cursor:pointer;transition:box-shadow var(--lotus-motion) var(--lotus-ease),border-color var(--lotus-motion) var(--lotus-ease)}
button.lotus-stat:hover{border-color:var(--lotus-border-strong);box-shadow:var(--lotus-shadow-md)}
button.lotus-stat:focus-visible{outline:none;box-shadow:var(--lotus-focus)}
.lotus-stat-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}
</style>
