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
