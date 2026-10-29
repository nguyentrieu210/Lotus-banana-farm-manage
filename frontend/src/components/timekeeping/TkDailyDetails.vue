<script setup>
import {computed} from 'vue'
import {Sheet} from '../ui/sheet'
import {Button} from '../ui/button'
import LotusField from '../form/LotusField.vue'
import TkPresenceToggle from './TkPresenceToggle.vue'
import {presenceDays} from '../../attendance-presence'
const props=defineProps({row:Object,busy:Boolean,editable:Boolean,canCorrect:Boolean})
const emit=defineEmits(['close','edit','presence','machine','save','correct'])
const disabled=computed(()=>props.busy||!props.editable||props.row?.docstatus===1||props.row?.legacy_conflict||props.row?.status==='On Leave')
function toggle(session,value){props.row[session+'_present']=value?1:0;emit('presence',props.row)}
</script>
<template>
 <Sheet :open="!!row" :title="row?.employee_name||'Chi tiết công'" :description="row?row.employee+' · '+row.date:undefined" @update:open="value=>{if(!value)emit('close')}">
  <template v-if="row">
   <div class="tk-daily-details__sessions">
    <div><span>Sáng &lt; 7h · ½ công</span><TkPresenceToggle :row="row" session="morning" :disabled="disabled" @toggle="toggle('morning',$event)"/></div>
    <div><span>Chiều &gt; 17h · ½ công</span><TkPresenceToggle :row="row" session="afternoon" :disabled="disabled" @toggle="toggle('afternoon',$event)"/></div>
    <div><span>Tổng công</span><strong>{{presenceDays(row).toLocaleString('vi-VN')}}</strong></div>
   </div>
   <p v-if="row.legacy_conflict" class="tk-banner is-info" role="status">Có nhiều phiếu công cũ trong ngày. Kiểm tra từng phiếu trước khi sửa.</p>
   <p v-if="row.manual" class="tk-banner is-info" role="status">Đã chỉnh tay, khác máy.</p>
   <Button v-if="!disabled&&row.machine?.checkins&&row.manual" variant="outline" @click="emit('machine',row)">Dùng số máy</Button>
   <div class="tk-daily-details__fields">
    <LotusField v-model="row.note" label="Ghi chú" type="textarea" maxlength="2000" :disabled="disabled" @update:model-value="emit('edit',row)"/>
   </div>
   <p v-if="row.edited" class="tk-hint">Có thay đổi chưa lưu.</p>
  </template>
  <template #footer>
   <Button variant="outline" @click="emit('close')">Đóng</Button>
   <Button v-if="canCorrect&&row?.docstatus===1&&row?.name" :disabled="busy" @click="emit('correct',row)">Sửa công đã duyệt</Button>
   <Button v-if="!disabled" :disabled="busy||!row?.edited" @click="emit('save')">Lưu thay đổi</Button>
  </template>
 </Sheet>
</template>
<style>
.tk-daily-details__sessions{display:grid;grid-template-columns:1fr 1fr 1fr;gap:var(--lotus-space-2);padding-bottom:var(--lotus-space-4);border-bottom:1px solid var(--lotus-border)}
.tk-daily-details__sessions>div{display:flex;flex-direction:column;gap:var(--lotus-space-2);align-items:flex-start}
.tk-daily-details__sessions>div>span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.tk-daily-details__sessions strong{font-size:var(--lotus-text-xl);font-variant-numeric:tabular-nums}
.tk-daily-details__fields{display:grid;gap:var(--lotus-space-4);margin-top:var(--lotus-space-4)}
</style>
