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
