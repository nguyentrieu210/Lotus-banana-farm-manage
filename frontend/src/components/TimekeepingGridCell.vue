<script setup>
import {computed} from 'vue'
import {Button as UiButton} from './ui/button'
import UiSelect from './ui/select/Select.vue'
import {Input as UiInput} from './ui/input'
import Checkbox from './ui/checkbox/Checkbox.vue'
const props=defineProps({params:{type:Object,required:true}})
const row=computed(()=>props.params.getRow?.(props.params.data)||props.params.data||{})
const a=computed(()=>props.params)
const field=computed(()=>props.params.colDef.field)
const disabled=computed(()=>a.value.saving()||row.value.docstatus===1||row.value.legacy_conflict||row.value.status==='On Leave'||!a.value.canEditStaff())
const allFlags=computed(()=>[...a.value.punchFlags(row.value),...(row.value.machine?.needs_review?['Cần kiểm tra']:[]),...(row.value.manual?['Đã chỉnh tay, khác máy']:[])])
</script>
<template>
 <div class="tk-grid-cell" :class="{'tk-grid-cell--punch':field==='machine_punch','tk-grid-cell--presence':['morning_present','afternoon_present'].includes(field)}">
  <input v-if="field==='selected'" v-model="row.selected" type="checkbox" :aria-label="'Chọn '+row.employee_name">
  <template v-else-if="field==='employee_name'"><strong>{{row.employee_name}}</strong><small>{{row.employee}} · {{row.designation||row.department||''}}</small></template>
  <template v-else-if="field==='morning_present'||field==='afternoon_present'">
   <Checkbox :model-value="!!Number(row[field])" :aria-label="(field==='morning_present'?'Sáng ':'Chiều ')+row.employee_name" :disabled="disabled" @update:model-value="value=>{row[field]=value?1:0;a.onPresence(row)}"/>
   <span class="tk-presence-time" :title="Number(row[field])&&!row[field.replace('_present','_time')]?'Có mặt · xác nhận tay':''">{{row[field.replace('_present','_time')]?String(row[field.replace('_present','_time')]).slice(11,16):'—'}}</span>
  </template>
  <template v-else-if="field==='status'">
   <UiSelect v-model="row.status" :aria-label="'Trạng thái '+row.employee_name" :disabled="disabled||row.status==='On Leave'" @change="a.chooseStatus(row)">
    <option value="">Chưa chấm</option>
    <option v-if="row.status==='On Leave'" value="On Leave">Nghỉ phép (HRMS)</option>
    <option v-for="[v,label] in a.editableStatuses()" :key="v" :value="v">{{label}}</option>
   </UiSelect>
  </template>
  <template v-else-if="field==='machine_punch'">
   <span :title="allFlags.join('; ')">{{a.punchText(row)||'—'}}<small v-if="allFlags.length"> · {{allFlags.join(', ')}}</small></span>
   <UiButton v-if="a.canEditStaff()&&row.docstatus===0&&row.machine?.status&&(row.manual||!row.matches)" variant="link" size="sm" @click.stop="a.useMachine(row)">Dùng số máy</UiButton>
  </template>
  <UiInput v-else-if="field==='working_hours'" v-model.number="row.working_hours" type="number" min="0" max="24" step="0.25" :aria-label="'Giờ làm '+row.employee_name" :disabled="disabled||row.status==='On Leave'" @input="a.onEdit(row)"/>
  <UiInput v-else-if="field==='overtime_hours'" v-model.number="row.overtime_hours" type="number" min="0" max="16" step="0.25" :aria-label="'Giờ tăng ca '+row.employee_name" :disabled="disabled||['On Leave','Absent'].includes(row.status)" @input="a.onEdit(row)"/>
  <UiInput v-else-if="field==='note'" v-model="row.note" :aria-label="'Ghi chú '+row.employee_name" :disabled="disabled" @input="a.onEdit(row)"/>
  <template v-else-if="field==='row_state'">
   <span class="tk-pill" :class="'is-'+a.rowState(row)">{{a.stateLabel(a.rowState(row))}}</span>
   <small v-if="row.edited">Chưa lưu</small>
   <small v-if="row.manual">Đã chỉnh tay, khác máy</small>
   <UiButton v-if="a.canEditStaff()&&row.docstatus===0&&row.manual&&row.machine?.checkins" variant="link" size="sm" @click.stop="a.useMachine(row)">Dùng số máy</UiButton>
   <UiButton v-if="a.canCorrect()&&row.docstatus===1&&row.name" variant="link" size="sm" :aria-label="'Sửa công đã duyệt của '+row.employee_name" @click.stop="a.openCorrection(row)">Sửa công</UiButton>
  </template>
 </div>
</template>
<style scoped>
.tk-grid-cell{height:100%;display:flex;align-items:center;gap:5px;min-width:0}
.tk-grid-cell strong{font-weight:600}.tk-grid-cell small{font-size:11px;color:var(--lotus-muted)}
.tk-grid-cell select,.tk-grid-cell input:not([type=checkbox]){width:100%;min-width:0;max-height:34px}
.tk-grid-cell--punch span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.tk-grid-cell--punch button{flex-shrink:0}
.tk-grid-cell--presence{display:grid;grid-template-columns:18px 5ch;column-gap:var(--lotus-space-2);justify-content:center;align-content:center;width:100%}
.tk-grid-cell--presence .lotus-checkbox{width:18px;height:18px;min-width:18px;min-height:18px;padding:0;margin:0}
.tk-presence-time{width:5ch;text-align:center;white-space:nowrap;font-variant-numeric:tabular-nums;line-height:18px}
</style>
