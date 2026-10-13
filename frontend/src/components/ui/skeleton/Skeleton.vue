<script setup>
import {cn} from '@/lib/utils'
defineOptions({inheritAttrs:false})
</script>
<template><div v-bind="$attrs" :class="cn('animate-pulse rounded-md bg-muted',$attrs.class)"/></template>
