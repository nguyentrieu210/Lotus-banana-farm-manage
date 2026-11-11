<script setup>
import {computed} from 'vue'
import LotusIcon from '../../LotusIcon.vue'
import {statusMeta,TONES} from '../../../ui-status.js'
// One chip for every document and work state (spec 004, FR-005, FR-008): label, tone and icon come from ui-status.js,
// so "Chờ duyệt" looks the same in Kho, Mua hàng and Tài chính. `status` is the raw state; `label` replaces the
// caption (e.g. stateLabel(status)); `tone` and `icon` override the vocabulary for one-off states.
const props=defineProps({status:{type:[String,Number],default:''},label:String,tone:String,icon:{type:String,default:undefined},solid:Boolean,size:{type:String,default:'md'}})
const meta=computed(()=>statusMeta(props.status,props.label))
const tone=computed(()=>TONES.includes(props.tone)?props.tone:meta.value.tone)
const icon=computed(()=>props.icon===undefined?meta.value.icon:props.icon)
</script>
<template>
 <span class="lotus-chip" :class="['lotus-chip--'+tone,{'lotus-chip--solid':solid,'lotus-chip--sm':size==='sm','lotus-chip--lg':size==='lg','lotus-chip--bare':!icon}]" :data-kind="meta.kind||undefined"><LotusIcon v-if="icon" :name="icon"/><span class="lotus-chip__text">{{meta.label}}</span></span>
</template>
