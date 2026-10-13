<script setup>
import {Primitive} from 'reka-ui'
import {cn} from '@/lib/utils'
import {buttonVariants} from './index.js'

defineOptions({inheritAttrs:true})
const props=defineProps({
  variant:{type:String,default:'default'},
  size:{type:String,default:'default'},
  as:{type:String,default:'button'},
  asChild:{type:Boolean,default:false},
  type:{type:String,default:'button'},
  loading:{type:Boolean,default:false},
  disabled:{type:Boolean,default:false},
})
</script>

<template>
  <Primitive
    :as="as"
    :as-child="asChild"
    :type="as==='button'?type:undefined"
    :disabled="disabled||loading"
    :aria-busy="loading||undefined"
    :class="cn(buttonVariants({variant,size}), $attrs.class)"
  >
    <span v-if="loading" class="lotus-button-spinner" aria-hidden="true"></span>
    <slot/>
  </Primitive>
</template>
