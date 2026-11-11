<script setup>
import RibbonDot from './RibbonDot.vue'
import {ribbonLabel} from '../../ribbon-colors.js'
import {formatNumber} from '../../agri-format.js'
// The ribbon colours in use, with an optional count each (FR-031). items: [{code, label?, count?}]
defineProps({items:{type:Array,required:true},label:{type:String,default:'Chú giải màu dây'}})
</script>
<template>
 <ul class="lotus-ribbon-legend" :aria-label="label"><li v-for="item in items" :key="item.code"><RibbonDot :code="item.code" decorative size="md"/><span>{{item.label||ribbonLabel(item.code)||item.code}}</span><b v-if="item.count!==undefined&&item.count!==null" class="lotus-num">{{formatNumber(item.count)}}</b></li></ul>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-ribbon-legend{display:flex;flex-wrap:wrap;gap:6px 14px;margin:0;padding:0;list-style:none;color:var(--lotus-text-secondary);font-size:var(--lotus-text-sm)}
.lotus-ribbon-legend li{display:inline-flex;align-items:center;gap:6px}
</style>
