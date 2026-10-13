<script setup>
import {computed} from 'vue'

// Local, shadcn-vue-style primitive: intentionally small and owned by Lotus.
// No React or additional UI runtime; Frappe's data/session integration stays intact.
const props=defineProps({
  variant:{type:String,default:'default'},
  size:{type:String,default:'default'},
  type:{type:String,default:'button'},
  loading:{type:Boolean,default:false},
  disabled:{type:Boolean,default:false},
})
const classes=computed(()=>['lotus-button','lotus-button--'+props.variant,'lotus-button--'+props.size])
</script>

<template>
  <button :type="type" :class="classes" :disabled="disabled||loading" :aria-busy="loading||undefined">
    <span v-if="loading" class="lotus-button-spinner" aria-hidden="true"></span>
    <slot/>
  </button>
</template>
