<script setup>
import {computed} from 'vue'
import {ribbonBackground,ribbonLabel} from '../../ribbon-colors.js'
// A ribbon (màu dây) swatch: one colour or two halves, always outlined so Trắng and Đen show on any surface (FR-031).
const props=defineProps({code:{type:String,default:''},label:String,size:{type:String,default:'sm'},band:Boolean,decorative:Boolean})
const name=computed(()=>props.label||ribbonLabel(props.code)||props.code)
</script>
<template>
 <span class="lotus-ribbon" :class="{'lotus-ribbon--md':size==='md','lotus-ribbon--lg':size==='lg','lotus-ribbon--band':band}" :style="{'--ribbon':ribbonBackground(code)}" :role="decorative?undefined:'img'" :aria-hidden="decorative?'true':undefined" :aria-label="decorative?undefined:'Màu dây '+name" :title="name"/>
</template>
