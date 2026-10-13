<script setup>
import {cn} from '@/lib/utils'
defineOptions({inheritAttrs:false})
</script>
<template><div v-bind="$attrs" :class="cn('flex flex-col space-y-1.5 p-6',$attrs.class)"><slot/></div></template>
