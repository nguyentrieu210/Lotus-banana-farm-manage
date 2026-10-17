<script setup>
defineProps({name:{type:String,default:'boxes'}})
const paths={
 boxes:['M3 7 12 3l9 4-9 4-9-4Z','M3 7v10l9 4 9-4V7','M12 11v10','M7.5 5 16.5 9'],
 cart:['M3 3h2l3 12h11l2-8H6','M9 20h.01','M18 20h.01'],
 receive:['M12 3v10','m8 9 4 4 4-4','M4 14v6h16v-6'],
 issue:['M12 15V3','m8 7 4-4 4 4','M4 14v6h16v-6'],
 transfer:['M4 7h16','m16 3 4 4-4 4','M20 17H4','m8 13-4 4 4 4'],
 check:['M9 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-4','m9 11 4 4L21 5'],
 list:['M8 6h13','M8 12h13','M8 18h13','M3 6h.01','M3 12h.01','M3 18h.01'],
 document:['M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z','M14 2v6h6','M8 13h8','M8 17h6'],
 settings:['M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z','M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1 1-3Z'],
 leaf:['M20 3c0 13-5 18-12 16C1 17 4 4 20 3Z','M4 21 16 9'],
 people:['M9 4a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z','M3 21v-3a6 6 0 0 1 12 0v3','M16 4a3 3 0 0 1 0 6','M21 21v-3a6 6 0 0 0-3-5'],
 warehouse:['M3 21V8l9-5 9 5v13','M7 21V11h10v10','M7 15h10','M7 18h10'],
 chevron:['m9 5 7 7-7 7'],
}
</script>
<template><svg class="lotus-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path v-for="(d,i) in paths[name]||paths.boxes" :key="i" :d="d"/></svg></template>
