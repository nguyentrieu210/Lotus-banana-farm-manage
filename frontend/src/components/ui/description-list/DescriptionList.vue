<script setup>
// Name–value pairs for a document or a lot (spec 004, User Story 3). An empty value shows "—", never a made-up one.
// items: [{label, value, key?, wide?}]; slot `value-<key>` replaces one value (a chip, a link).
defineProps({items:{type:Array,required:true},columns:{type:Number,default:2}})
const empty=v=>v===null||v===undefined||v===''
</script>
<template>
 <dl class="lotus-dl" :style="{'--dl-cols':columns}">
  <div v-for="(item,index) in items" :key="item.key||index" class="lotus-dl__item" :class="{'lotus-dl__item--wide':item.wide}"><dt>{{item.label}}</dt><dd><slot :name="'value-'+(item.key||index)" :item="item"><span v-if="empty(item.value)" class="lotus-missing">—</span><template v-else>{{item.value}}</template></slot></dd></div>
 </dl>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-dl{display:grid;grid-template-columns:repeat(var(--dl-cols,2),minmax(0,1fr));gap:12px 24px;margin:0}
.lotus-dl__item{display:grid;gap:2px;min-width:0}
.lotus-dl__item--wide{grid-column:1/-1}
.lotus-dl dt{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.lotus-dl dd{margin:0;color:var(--lotus-text);font-weight:var(--lotus-weight-medium);overflow-wrap:anywhere}
@media (max-width:640px){.lotus-dl{grid-template-columns:minmax(0,1fr)}}
</style>
