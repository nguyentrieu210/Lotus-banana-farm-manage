<script setup>
import {formatNumber} from '../../agri-format.js'
// Map legend (FR-036, FR-049): categories with a swatch and a count, or a sequential scale with its two ends.
// items: [{label, colour (a CSS colour or var()), count?}]; scale: [colour, …] with `ends: [low, high]`.
defineProps({title:{type:String,required:true},items:{type:Array,default:()=>[]},scale:{type:Array,default:()=>[]},ends:{type:Array,default:()=>[]}})
</script>
<template>
 <div class="lotus-map-legend" role="group" :aria-label="title">
  <p class="lotus-map-legend__title">{{title}}</p>
  <ul v-if="items.length" class="lotus-map-legend__rows"><li v-for="item in items" :key="item.label" class="lotus-map-legend__row"><span class="lotus-map-legend__swatch" :style="{'--swatch':item.colour}" aria-hidden="true"/>{{item.label}}<b v-if="item.count!==undefined&&item.count!==null">{{formatNumber(item.count)}}</b></li></ul>
  <template v-if="scale.length"><div class="lotus-map-legend__scale" aria-hidden="true"><i v-for="c in scale" :key="c" :style="{'--swatch':c}"/></div><div v-if="ends.length" class="lotus-map-legend__ends"><span>{{ends[0]}}</span><span>{{ends[1]}}</span></div></template>
 </div>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-map-legend{display:grid;gap:7px;min-width:170px;padding:10px 12px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-lg);background:var(--lotus-raised);box-shadow:var(--lotus-shadow-md);color:var(--lotus-text);font-size:var(--lotus-text-sm)}
.lotus-map-legend__title{margin:0;color:var(--lotus-text-strong);font-size:var(--lotus-text-sm);font-weight:var(--lotus-weight-bold)}
.lotus-map-legend__rows{display:grid;gap:5px;margin:0;padding:0;list-style:none}
.lotus-map-legend__row{display:flex;align-items:center;gap:8px}
.lotus-map-legend__row b{margin-left:auto;color:var(--lotus-text-strong);font-variant-numeric:tabular-nums}
.lotus-map-legend__swatch{flex:none;width:14px;height:14px;border-radius:4px;background:var(--swatch);box-shadow:inset 0 0 0 1px rgb(0 0 0/.18)}
.lotus-map-legend__scale{display:flex;height:8px;overflow:hidden;border-radius:4px}
.lotus-map-legend__scale i{flex:1;background:var(--swatch)}
.lotus-map-legend__ends{display:flex;justify-content:space-between;color:var(--lotus-muted);font-size:var(--lotus-text-xs)}
</style>
