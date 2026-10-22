<script setup>
import {computed} from 'vue'
const props=defineProps({params:{type:Object,required:true}})
const row=computed(()=>props.params.data||{})
const opts=computed(()=>props.params)
</script>
<template>
 <div v-if="params.colDef.field==='employee_select'" class="lotus-grid-edit-cell">
  <select :value="opts.getChoice(row)" :aria-label="'Nhân viên cho mã '+row.device_user_id" :disabled="!opts.canManage()||opts.isSaving()" @change="opts.setChoice(row,$event.target.value)">
   <option value="">Chọn nhân viên…</option>
   <option v-for="e in opts.employees()" :key="e.name" :value="e.name">{{e.employee_name}} · {{e.name}}{{e.name===row.suggested?' (gợi ý)':''}}</option>
  </select>
 </div>
 <div v-else-if="params.colDef.field==='map_action'" class="lotus-grid-edit-cell">
  <button v-if="opts.canManage()" type="button" :disabled="opts.isSaving()||!opts.getChoice(row)" @click.stop="opts.onMap(row)">Gắn</button>
 </div>
 <div v-else-if="params.colDef.field==='select_log'" class="lotus-grid-edit-cell">
  <input v-if="opts.canSelect(row)" type="checkbox" :checked="opts.isChecked(row)" :aria-label="'Chọn log '+row.punched_at" @change="opts.toggle(row,$event.target.checked)" />
 </div>
</template>
<style scoped>
.lotus-grid-edit-cell{display:flex;align-items:center;min-height:32px;height:100%;gap:6px}
.lotus-grid-edit-cell select{min-width:0;width:100%;padding:5px;border:1px solid var(--lotus-neutral-300);border-radius:5px;background:#fff;color:inherit}
.lotus-grid-edit-cell button{cursor:pointer;padding:5px 12px;border:1px solid var(--lotus-neutral-300);border-radius:5px;background:var(--lotus-accent);color:white}
.lotus-grid-edit-cell button:disabled{opacity:.5;cursor:not-allowed}
</style>