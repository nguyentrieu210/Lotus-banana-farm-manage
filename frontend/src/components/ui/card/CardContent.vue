<script setup>
import {cn} from '@/lib/utils'
defineOptions({inheritAttrs:false})
</script>
<template><div v-bind="$attrs" :class="cn('p-6 pt-0',$attrs.class)"><slot/></div></template>
