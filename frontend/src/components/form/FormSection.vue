<script setup>
// A titled block inside a form (thông tin chung, hàng hóa, chi phí…); actions slot sits on the right of the title.
defineProps({title:String,description:String})
</script>
<template>
 <section class="lotus-form-section">
  <header v-if="title||$slots.actions" class="lotus-form-section__header"><div v-if="title||description"><h3 v-if="title">{{title}}</h3><p v-if="description">{{description}}</p></div><div v-if="$slots.actions" class="lotus-form-section__actions"><slot name="actions"/></div></header>
  <slot/>
 </section>
</template>
<style>
.lotus-form-section{display:grid;gap:12px;min-width:0;padding-top:16px;margin-top:16px;border-top:1px solid var(--lotus-border)}
.lotus-form-section:first-child{padding-top:0;margin-top:0;border-top:0}
/* Title, then its actions on the left (same rule as list toolbars: actions start at the left edge). */
.lotus-form-section__header{display:flex;flex-direction:column;align-items:flex-start;gap:8px}
.lotus-form-section__header h3{margin:0;font-size:var(--lotus-text-md);font-weight:600;color:var(--lotus-text-strong)}
.lotus-form-section__header p{margin:2px 0 0;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.lotus-form-section__actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
</style>
