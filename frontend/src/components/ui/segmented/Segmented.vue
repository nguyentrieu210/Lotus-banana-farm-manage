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

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-segmented{display:inline-flex;max-width:100%;padding:3px;gap:2px;overflow-x:auto;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-sunken)}
.lotus-segmented__item{display:inline-flex;align-items:center;justify-content:center;gap:6px;flex:1 0 auto;min-height:calc(var(--lotus-control-height) - 8px);padding:0 12px;border:0;border-radius:calc(var(--lotus-radius-md) - 2px);background:transparent;color:var(--lotus-text-secondary);font:inherit;font-size:var(--lotus-text-md);font-weight:var(--lotus-weight-medium);white-space:nowrap;cursor:pointer}
.lotus-segmented__item:hover{color:var(--lotus-text-strong)}
.lotus-segmented__item[data-state="on"]{background:var(--lotus-surface);color:var(--lotus-text-strong);font-weight:var(--lotus-weight-semibold);box-shadow:var(--lotus-shadow-sm)}
.lotus-segmented__item:focus-visible{outline:none;box-shadow:var(--lotus-focus)}
.lotus-segmented__count{padding:1px 6px;border-radius:var(--lotus-radius-full);background:var(--lotus-hover);color:var(--lotus-muted);font-size:var(--lotus-text-xs);font-variant-numeric:tabular-nums}
.lotus-segmented--block{display:flex;width:100%}
</style>
