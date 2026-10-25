<script setup>
// The one form layout: `columns` equal columns on desktop, a single column on narrow screens. Wide fields: <LotusField wide/> or class "lotus-form-grid__wide".
defineProps({columns:{type:[Number,String],default:2}})
</script>
<template><div class="lotus-form-grid" :style="{'--lotus-form-columns':columns}"><slot/></div></template>
<style>
.lotus-form-grid{display:grid;grid-template-columns:repeat(var(--lotus-form-columns,2),minmax(0,1fr));gap:14px 16px;align-items:start;min-width:0}
.lotus-form-grid>.lotus-form-grid__wide{grid-column:1/-1}
@media(max-width:720px){.lotus-form-grid{grid-template-columns:minmax(0,1fr)}}
</style>
