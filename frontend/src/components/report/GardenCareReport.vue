<script setup>
import WorkGroupReport from './WorkGroupReport.vue'
defineProps({embedded:Boolean,navigationKey:String})
</script>

<template><WorkGroupReport method="field_care" filename="Bao-cao-cham-soc-vuon" empty="Chưa có báo cáo chăm sóc vườn trong phần đang lọc."/></template>
