<script setup>
import {ToggleGroupRoot,ToggleGroupItem} from 'reka-ui'
import LotusIcon from '../../LotusIcon.vue'
// One choice among a few (spec 004, FR-023): "Sáng nay · Tuần · Tháng", the metric of the lot grid…
// options: [{value, label, count?, icon?}]. A choice can be changed but never cleared.
defineProps({options:{type:Array,required:true},label:{type:String,required:true},block:Boolean,disabled:Boolean})
const model=defineModel({type:[String,Number],default:undefined})
function choose(value){if(value!==undefined&&value!==null&&value!=='')model.value=value}
</script>
<template>
 <ToggleGroupRoot type="single" :model-value="model" class="lotus-segmented" :class="{'lotus-segmented--block':block}" :aria-label="label" :disabled="disabled" @update:model-value="choose">
  <ToggleGroupItem v-for="o in options" :key="o.value" :value="o.value" class="lotus-segmented__item"><LotusIcon v-if="o.icon" :name="o.icon"/>{{o.label}}<span v-if="o.count!==undefined&&o.count!==null" class="lotus-segmented__count">{{o.count}}</span></ToggleGroupItem>
 </ToggleGroupRoot>
</template>
