<script setup>
import LotusField from './form/LotusField.vue'
// Kept for existing callers: the shared field is form/LotusField.vue (same props: label, type, options, searchable, required, hint, error, mobile).
defineOptions({inheritAttrs:false})
</script>
<template><LotusField v-bind="$attrs"/></template>
