<script setup>
import {computed} from 'vue'
import {Button as UiButton} from './ui/button'
const props=defineProps({params:{type:Object,required:true}})
const row=computed(()=>props.params.data||{})
const opts=computed(()=>props.params)
const date=computed(()=>props.params.rosterDate)
const cell=computed(()=>row.value.cells?.find(c=>c.date===date.value))
const shiftNames=computed(()=>cell.value?.shifts||[cell.value?.shift].filter(Boolean))
const shiftLabel=computed(()=>shiftNames.value.join(' + '))
const picked=computed(()=>cell.value&&opts.value.isPicked(row.value,cell.value.date))
const disabled=computed(()=>!opts.value.canManage()||opts.value.isClosed(date.value))
</script>
<template>
 <div class="tk-roster-grid-cell">
  <UiButton v-if="params.colDef.field==='employee'" variant="ghost" :disabled="!opts.canManage()" :title="row.designation||row.department||row.employee" @click.stop="opts.pickRow(row)">{{row.employee_name}}</UiButton>
  <button v-else-if="cell" type="button" class="tk-cell" :class="{picked,empty:!cell.shift}" :style="cell.shift?{'--shift':opts.colors()[cell.shift]||'#4b5563'}:null"
   :disabled="disabled" :aria-pressed="picked?'true':'false'"
   :aria-label="row.employee_name+' '+opts.dm(cell.date)+': '+(shiftLabel||'không xếp ca')+(cell.worked?', đã có công duyệt':'')"
   :title="(shiftLabel||'Không xếp ca')+(cell.worked?' · đã có công duyệt':'')"
   @pointerdown.prevent="opts.down(row,cell)" @pointerenter="opts.enter(row,cell)"
  >{{shiftNames.length?shiftNames.map(opts.shortShift).join('+'):'—'}}<i v-if="cell.worked" class="tk-cell__done" aria-hidden="true"></i></button>
 </div>
</template>
<style scoped>
.tk-roster-grid-cell{height:100%;display:flex;align-items:center;justify-content:center}
.tk-roster-grid-cell .tk-cell{width:100%;min-height:30px;cursor:pointer}
.tk-roster-grid-cell .tk-cell:disabled{cursor:not-allowed;opacity:.6}
</style>
