<script setup>
import {Field} from 'vant'
defineOptions({inheritAttrs:false})
</script>
<template><Field class="lotus-pwa-field lotus-pwa-file" :border="false"><template #input><input v-bind="$attrs" type="file" class="van-field__control"/></template></Field></template>
