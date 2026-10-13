<script setup>
import {cn} from '@/lib/utils'
defineOptions({inheritAttrs:false})
</script>
<template><h3 v-bind="$attrs" :class="cn('text-lg font-semibold leading-none tracking-tight',$attrs.class)"><slot/></h3></template>
