<script setup>
import {ICON_PATHS} from '../icon-paths.js'
defineProps({name:{type:String,default:'boxes'}})
const paths=ICON_PATHS
</script>
<template><svg class="lotus-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path v-for="(d,i) in paths[name]||paths.boxes" :key="i" :d="d"/></svg></template>
