<script setup>
// A titled block inside a form (thông tin chung, hàng hóa, chi phí…); actions slot sits on the right of the title.
defineProps({title:String,description:String})
</script>
<template>
 <section class="lotus-form-section">
  <header v-if="title||$slots.actions" class="lotus-form-section__header"><div><h3>{{title}}</h3><p v-if="description">{{description}}</p></div><div v-if="$slots.actions" class="lotus-form-section__actions"><slot name="actions"/></div></header>
  <slot/>
 </section>
</template>
<style>
.lotus-form-section{display:grid;gap:12px;min-width:0;padding-top:16px;margin-top:16px;border-top:1px solid var(--lotus-border)}
.lotus-form-section:first-child{padding-top:0;margin-top:0;border-top:0}
.lotus-form-section__header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.lotus-form-section__header h3{margin:0;font-size:var(--lotus-text-md);font-weight:600;color:var(--lotus-text-strong)}
.lotus-form-section__header p{margin:2px 0 0;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.lotus-form-section__actions{display:flex;gap:8px;flex-wrap:wrap}
</style>
