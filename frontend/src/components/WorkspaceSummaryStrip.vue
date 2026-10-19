<script setup>
defineProps({items:{type:Array,default:()=>[]}})
</script>
<template><dl class="workspace-summary-strip"><div v-for="item in items" :key="item.label"><dt>{{item.label}}</dt><dd>{{item.value}}</dd></div></dl></template>