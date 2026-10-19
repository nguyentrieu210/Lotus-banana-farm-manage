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
 scan:['M3 7V5a2 2 0 0 1 2-2h2','M17 3h2a2 2 0 0 1 2 2v2','M21 17v2a2 2 0 0 1-2 2h-2','M7 21H5a2 2 0 0 1-2-2v-2','M7 12h10'],
 sun:['M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z','M12 2v2','M12 20v2','m4.93 4.93 1.41 1.41','m17.66 17.66 1.41 1.41','M2 12h2','M20 12h2','m6.34 17.66-1.41 1.41','m19.07 4.93-1.41 1.41'],
 moon:['M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z'],
 'switch-camera':['M11 19H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5','M13 5h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-5','M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z','m18 22-3-3 3-3','m6 2 3 3-3 3'],
 flashlight:['M12 13v1','M17 2a1 1 0 0 1 1 1v4a3 3 0 0 1-.6 1.8l-.6.8A4 4 0 0 0 16 12v8a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2v-8a4 4 0 0 0-.8-2.4l-.6-.8A3 3 0 0 1 6 7V3a1 1 0 0 1 1-1z','M6 6h12'],
 'flashlight-off':['M11.652 6H18','M12 13v1','M16 16v4a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-8a4 4 0 0 0-.8-2.4l-.6-.8A3 3 0 0 1 6 7V6','m2 2 20 20','M7.649 2H17a1 1 0 0 1 1 1v4a3 3 0 0 1-.6 1.8l-.6.8a4 4 0 0 0-.55 1.007'],
}
</script>
<template><svg class="lotus-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path v-for="(d,i) in paths[name]||paths.boxes" :key="i" :d="d"/></svg></template>
