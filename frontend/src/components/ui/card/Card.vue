<script setup>
import {cn} from '@/lib/utils'
defineOptions({inheritAttrs:false})
</script>
<template><div v-bind="$attrs" :class="cn('rounded-lg border border-border bg-card text-card-foreground shadow-sm',$attrs.class)"><slot/></div></template>
