<script setup>
import {computed,nextTick,onMounted,onUnmounted,ref} from 'vue'
const props=defineProps({params:Object})
const opened=ref(false),trigger=ref(null),popup=ref(null),search=ref(''),selected=ref([]),position=ref({})
const choices=computed(()=>props.params.choices||[])
const visible=computed(()=>choices.value.filter(row=>String(row.label??row.value).toLocaleLowerCase('vi').includes(search.value.toLocaleLowerCase('vi'))))
const active=computed(()=>Array.isArray(props.params.selection))
const all=computed(()=>selected.value.length===choices.value.length)
async function open(event){event.stopPropagation();if(opened.value){opened.value=false;return}search.value='';selected.value=(active.value?props.params.selection:choices.value.map(row=>row.value)).map(String);const rect=trigger.value.getBoundingClientRect();position.value={left:Math.max(8,Math.min(rect.left,window.innerWidth-280))+'px',top:(rect.bottom+4)+'px',maxHeight:Math.max(160,window.innerHeight-rect.bottom-16)+'px'};opened.value=true;await nextTick();popup.value?.showPopover?.()}
function toggle(value){const key=String(value);selected.value=selected.value.includes(key)?selected.value.filter(v=>v!==key):[...selected.value,key]}
function apply(){props.params.apply(choices.value.filter(row=>selected.value.includes(String(row.value))).map(row=>row.value));opened.value=false}
function clear(){props.params.apply(null);opened.value=false}
function outside(event){if(opened.value&&!popup.value?.contains(event.target)&&!trigger.value?.contains(event.target))opened.value=false}
onMounted(()=>document.addEventListener('pointerdown',outside))
onUnmounted(()=>document.removeEventListener('pointerdown',outside))
</script>
<template><div class="excel-header"><button type="button" class="excel-sort" @click="params.progressSort($event.shiftKey)" :title="'Sắp xếp '+params.displayName">{{params.displayName}}</button><button ref="trigger" type="button" class="excel-trigger" :class="{active}" :aria-label="'Lọc '+params.displayName" :aria-expanded="opened" @click="open">▾</button><div v-if="opened" ref="popup" popover="manual" class="excel-popup" :style="position" :aria-label="'Lọc '+params.displayName" role="dialog" @keydown.esc="opened=false"><strong>{{params.displayName}}</strong><input v-model="search" aria-label="Tìm trong danh sách" placeholder="Tìm trong danh sách…"><label><input type="checkbox" :checked="all" @change="selected=all?[]:choices.map(row=>String(row.value))">Chọn tất cả ({{choices.length}})</label><div class="excel-values"><label v-for="row in visible" :key="String(row.value)"><input type="checkbox" :checked="selected.includes(String(row.value))" @change="toggle(row.value)"><span>{{row.label??row.value??'(Trống)'}}</span></label><p v-if="!visible.length">Không có giá trị.</p></div><footer><button type="button" @click="clear">Bỏ lọc</button><button type="button" @click="apply">Áp dụng</button></footer></div></div></template>
