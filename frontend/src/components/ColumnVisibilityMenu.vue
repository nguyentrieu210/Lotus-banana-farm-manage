<script setup>
import {computed} from 'vue'
import {Button as UiButton} from './ui/button'
import {Popover,PopoverTrigger,PopoverContent} from './ui/popover'
import LotusIcon from './LotusIcon.vue'
import {columnId,selectableColumns,normalizeHiddenColumns} from '../grid-visibility'
const props=defineProps({columns:{type:Array,required:true},hidden:{type:Array,default:()=>[]}})
const emit=defineEmits(['toggle','reset'])
const choices=computed(()=>selectableColumns(props.columns))
const hiddenIds=computed(()=>normalizeHiddenColumns(props.columns,props.hidden))
const visibleCount=computed(()=>choices.value.length-hiddenIds.value.length)
</script>

<template>
 <Popover>
  <PopoverTrigger as-child>
   <UiButton type="button" variant="outline" size="sm" aria-label="Chọn cột hiển thị"><LotusIcon name="list"/>Cột hiển thị<span v-if="hiddenIds.length"> ({{hiddenIds.length}} ẩn)</span></UiButton>
  </PopoverTrigger>
  <PopoverContent align="end" class="lotus-column-picker">
   <div class="lotus-column-picker__head"><strong>Chọn cột cần xem</strong><UiButton type="button" variant="ghost" size="sm" @click="emit('reset')">Mặc định</UiButton></div>
   <small>{{visibleCount}} / {{choices.length}} cột đang hiển thị</small>
   <div class="lotus-column-picker__options" role="group" aria-label="Các cột của bảng">
    <label v-for="col in choices" :key="columnId(col)" class="lotus-column-picker__item">
     <input type="checkbox" :checked="!hiddenIds.includes(columnId(col))" :disabled="visibleCount===1&&!hiddenIds.includes(columnId(col))" @change="emit('toggle',columnId(col))">
     <span>{{col.headerName||columnId(col)}}</span>
    </label>
   </div>
  </PopoverContent>
 </Popover>
</template>
<style>
.lotus-column-picker{width:min(330px,calc(100vw - 28px));padding:12px}
.lotus-column-picker__head{display:flex;align-items:center;justify-content:space-between;gap:8px}
.lotus-column-picker__head strong{font-size:var(--lotus-text-sm)}
.lotus-column-picker__options{display:grid;gap:2px;max-height:min(360px,55vh);overflow-y:auto;margin-top:9px}
.lotus-column-picker__item{display:flex;align-items:center;gap:9px;min-height:34px;padding:5px 7px;border-radius:6px;cursor:pointer;font-size:var(--lotus-text-sm)}
.lotus-column-picker__item:hover{background:var(--lotus-hover)}
.lotus-column-picker__item input{accent-color:var(--lotus-primary);width:16px;height:16px;flex:none}
.lotus-column-picker__item input:disabled{cursor:not-allowed;opacity:.5}
</style>
