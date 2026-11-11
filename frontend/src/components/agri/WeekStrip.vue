<script setup>
import {computed} from 'vue'
import RibbonDot from './RibbonDot.vue'
import {isoWeek,addWeeks,isoWeekMonday,weekRange,weekKey,shortDate,formatNumber} from '../../agri-format.js'
// A run of ISO weeks around today (FR-032): this week marked, harvest weeks marked, the ribbons cut in each week,
// and an optional figure per week (forecast bunches). v-model is the chosen week key 'YYYY-Www'.
const props=defineProps({
 today:{type:String,required:true},before:{type:Number,default:2},after:{type:Number,default:9},
 harvest:{type:Array,default:()=>[]},ribbons:{type:Object,default:()=>({})},values:{type:Object,default:()=>({})},unit:{type:String,default:''},
 label:{type:String,default:'Các tuần'},
})
const model=defineModel({type:String,default:''})
const now=computed(()=>isoWeek(props.today))
const harvestKeys=computed(()=>new Set(props.harvest.map(h=>typeof h==='string'?h:weekKey(h))))
const weeks=computed(()=>{
 if(!now.value)return []
 const list=[]
 for(let i=-props.before;i<=props.after;i++){const w=addWeeks(now.value,i),key=weekKey(w);list.push({...w,key,offset:i,harvest:harvestKeys.value.has(key),ribbons:props.ribbons[key]||[],value:props.values[key]})}
 return list
})
function describe(w){return ['Tuần '+w.week+'/'+w.year,weekRange(w),w.offset===0?'tuần này':'',w.harvest?'tuần thu':'',w.value!==undefined&&w.value!==null?formatNumber(w.value)+(props.unit?' '+props.unit:''):''].filter(Boolean).join(', ')}
</script>
<template>
 <ol class="lotus-weekstrip" :aria-label="label">
  <li v-for="w in weeks" :key="w.key">
   <button type="button" class="lotus-weekstrip__cell" :class="{'lotus-weekstrip__cell--current':w.offset===0,'lotus-weekstrip__cell--harvest':w.harvest,'lotus-weekstrip__cell--past':w.offset<0}" :aria-pressed="model===w.key" :aria-current="w.offset===0?'date':undefined" :aria-label="describe(w)" :title="describe(w)" @click="model=w.key">
    <span class="lotus-weekstrip__num">T{{w.week}}</span>
    <span class="lotus-weekstrip__sub">{{w.value!==undefined&&w.value!==null?formatNumber(w.value):shortDate(isoWeekMonday(w.year,w.week))}}</span>
    <span class="lotus-weekstrip__mark" aria-hidden="true"><RibbonDot v-for="code in w.ribbons.slice(0,3)" :key="code" :code="code" decorative/></span>
   </button>
  </li>
 </ol>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-weekstrip{display:flex;gap:4px;margin:0;padding:2px;overflow-x:auto;list-style:none;scrollbar-width:thin}
.lotus-weekstrip li{flex:1 0 50px;display:flex}
.lotus-weekstrip__cell{position:relative;display:grid;flex:1;gap:3px;justify-items:center;min-width:50px;min-height:58px;padding:7px 4px 6px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);color:var(--lotus-text);font:inherit;cursor:pointer}
.lotus-weekstrip__cell:hover{border-color:var(--lotus-border-strong)}
.lotus-weekstrip__cell:focus-visible{outline:none;box-shadow:var(--lotus-focus)}
.lotus-weekstrip__num{font-size:var(--lotus-text-md);font-weight:var(--lotus-weight-bold);font-variant-numeric:tabular-nums}
.lotus-weekstrip__sub{color:var(--lotus-muted);font-size:10.5px;font-variant-numeric:tabular-nums;white-space:nowrap}
.lotus-weekstrip__cell--harvest{border-color:var(--lotus-tone-success-border);background:var(--lotus-tone-success-soft)}
.lotus-weekstrip__cell--harvest::after{content:"";position:absolute;inset:auto 6px 3px;height:3px;border-radius:2px;background:var(--lotus-tone-success-solid)}
.lotus-weekstrip__cell--current{border-color:var(--lotus-primary);box-shadow:inset 0 0 0 1px var(--lotus-primary)}
.lotus-weekstrip__cell--current .lotus-weekstrip__num{color:var(--lotus-primary-text)}
.lotus-weekstrip__cell[aria-pressed="true"]{background:var(--lotus-tone-primary-soft);border-color:var(--lotus-primary)}
.lotus-weekstrip__cell--past{opacity:.6}
</style>
