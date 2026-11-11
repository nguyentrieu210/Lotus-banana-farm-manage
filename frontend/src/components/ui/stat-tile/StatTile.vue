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
  </span>
 </component>
</template>
