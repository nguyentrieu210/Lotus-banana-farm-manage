<script setup>
import {Separator as SeparatorPrimitive} from 'reka-ui'
import {cn} from '@/lib/utils'
defineOptions({inheritAttrs:false})
defineProps({
  orientation:{type:String,default:'horizontal'},
  decorative:{type:Boolean,default:true},
})
</script>
<template>
  <SeparatorPrimitive v-bind="$attrs" :orientation="orientation" :decorative="decorative" :class="cn('shrink-0 bg-border',orientation==='horizontal'?'h-[1px] w-full':'h-full w-[1px]',$attrs.class)"/>
</template>
