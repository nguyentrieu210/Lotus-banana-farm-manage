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
