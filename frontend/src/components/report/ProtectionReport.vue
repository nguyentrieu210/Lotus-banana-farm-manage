<script setup>
import WorkGroupReport from './WorkGroupReport.vue'
defineProps({embedded:Boolean,navigationKey:String})
</script>

<template><WorkGroupReport method="protection" filename="Bao-cao-BVTV" empty="Chưa có báo cáo phun thuốc, bón phân trong phần đang lọc." protection/></template>
