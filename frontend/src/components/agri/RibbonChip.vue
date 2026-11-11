<script setup>
import {computed} from 'vue'
import RibbonDot from './RibbonDot.vue'
import {ribbonLabel} from '../../ribbon-colors.js'
import {formatNumber} from '../../agri-format.js'
// A ribbon batch: colour, name, ISO week of cutting and bunches still on the plants (FR-031).
const props=defineProps({code:{type:String,default:''},label:String,week:Number,count:{type:Number,default:null},unit:{type:String,default:'buồng'}})
const name=computed(()=>props.label||ribbonLabel(props.code)||props.code)
const aria=computed(()=>['Màu dây '+name.value,props.week?'tuần '+props.week:'',props.count!==null?'còn '+formatNumber(props.count)+' '+props.unit:''].filter(Boolean).join(', '))
</script>
<template>
 <span class="lotus-ribbon-chip" :aria-label="aria" role="group"><RibbonDot :code="code" decorative/><span class="lotus-ribbon-chip__label" aria-hidden="true">{{name}}</span><span v-if="week" class="lotus-ribbon-chip__week" aria-hidden="true">T{{week}}</span><span v-if="count!==null" class="lotus-ribbon-chip__count" aria-hidden="true">{{formatNumber(count)}}</span></span>
</template>
