<script setup>
import {computed} from 'vue'
import LotusIcon from '../LotusIcon.vue'
import {daysBetween} from '../../ui-status.js'
import {shortDate} from '../../agri-format.js'
// Spray quarantine (FR-033): "Cách ly còn 4 ngày, đến 14/11", hatched like a hazard sign, danger tone.
// Nothing is shown once the quarantine has ended.
const props=defineProps({until:{type:String,default:''},today:{type:String,required:true}})
const days=computed(()=>props.until?daysBetween(props.today,props.until):null)
const text=computed(()=>days.value===null||days.value<0?'':days.value===0?`Cách ly đến hết hôm nay (${shortDate(props.until)})`:`Cách ly còn ${days.value} ngày, đến ${shortDate(props.until)}`)
</script>
<template>
 <span v-if="text" class="lotus-quarantine"><span class="lotus-quarantine__mark" aria-hidden="true"><LotusIcon name="shield"/></span><span class="lotus-quarantine__text">{{text}}</span></span>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-quarantine{display:inline-flex;align-items:stretch;max-width:100%;overflow:hidden;border:1px solid var(--lotus-tone-danger-border);border-radius:var(--lotus-radius-sm);background:var(--lotus-tone-danger-soft);color:var(--lotus-tone-danger-text);font-size:var(--lotus-chip-font);font-weight:var(--lotus-weight-semibold);line-height:1.2}
.lotus-quarantine__mark{display:grid;place-items:center;flex:none;width:24px;background-color:var(--lotus-lot-quarantine);background-image:repeating-linear-gradient(135deg,var(--lotus-lot-quarantine-stripe) 0 3px,transparent 3px 7px)}
.lotus-quarantine__mark .lotus-icon{width:14px;height:14px;stroke-width:2.2}
.lotus-quarantine__text{padding:4px 9px 4px 7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
</style>
