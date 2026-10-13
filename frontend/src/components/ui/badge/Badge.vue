<script setup>
import {cn} from '@/lib/utils'
import {badgeVariants} from './index.js'
defineOptions({inheritAttrs:false})
defineProps({variant:{type:String,default:'default'}})
</script>
<template><span v-bind="$attrs" :class="cn(badgeVariants({variant}),$attrs.class)"><slot/></span></template>
