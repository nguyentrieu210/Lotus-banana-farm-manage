<script setup>
import {computed} from 'vue'
import {Button} from './ui/button'
import LotusIcon from './LotusIcon.vue'
import TkPresenceToggle from './timekeeping/TkPresenceToggle.vue'
import {presenceDays} from '../attendance-presence'
const props=defineProps({params:{type:Object,required:true}})
const row=computed(()=>props.params.getRow?.(props.params.data)||props.params.data||{})
const a=computed(()=>props.params)
const field=computed(()=>props.params.colDef.field)
const disabled=computed(()=>a.value.saving()||row.value.docstatus===1||row.value.legacy_conflict||row.value.status==='On Leave'||!a.value.canEditStaff())
function toggle(value){row.value[field.value]=value?1:0;a.value.onPresence(row.value)}
// Phụ cấp may still be ticked on an approved day while the month is open; never on a day with no công.
const allowanceDisabled=computed(()=>a.value.saving()||row.value.legacy_conflict||row.value.status==='On Leave'||!a.value.canEditStaff()||(!presenceDays(row.value)&&!Number(row.value.allowance)))
const allowanceOn=computed(()=>!!Number(row.value.allowance))
</script>
<template>
 <div class="tk-grid-cell" :class="{'tk-grid-cell--presence':['morning_present','afternoon_present','allowance'].includes(field)}">
  <strong v-if="field==='employee_name'" :title="row.employee_name+' · '+row.employee">{{row.employee_name}}</strong>
  <template v-else-if="field==='morning_present'||field==='afternoon_present'">
   <TkPresenceToggle :row="row" :session="field==='morning_present'?'morning':'afternoon'" :disabled="disabled" @toggle="toggle"/>
   <small v-if="(row.khoan_sessions||[]).includes(field==='morning_present'?'morning':'afternoon')" class="tk-khoan" title="Buổi này làm phiếu khoán: trả theo phiếu, không tính công nhật">Khoán</small>
  </template>
  <Button v-else-if="field==='allowance'" type="button" variant="outline" size="sm" class="tk-presence-toggle tk-allowance-toggle" :class="{'is-present':allowanceOn}" :aria-label="'Phụ cấp '+row.employee_name" :aria-pressed="allowanceOn" :disabled="allowanceDisabled" :title="allowanceOn?'Có phụ cấp công việc'+(row.allowance_amount&&!row.edited?' · '+Number(row.allowance_amount).toLocaleString('vi-VN')+' đ':''):'Bấm để tick phụ cấp công việc'" @click.stop="a.onAllowance(row)">
   <LotusIcon :name="allowanceOn?'tick':'plus'"/><span>{{allowanceOn?'Có PC':'Không'}}</span>
  </Button>
  <template v-else-if="field==='row_state'">
   <span class="tk-pill" :class="'is-'+a.rowState(row)" :title="row.manual?'Đã chỉnh tay, khác máy':a.stateLabel(a.rowState(row))">{{row.edited?'Chưa lưu':a.stateLabel(a.rowState(row))}}</span>
   <Button variant="ghost" size="icon" class="tk-daily-detail-button" :aria-label="'Chi tiết công '+row.employee_name" title="Chi tiết công" @click.stop="a.openDetails(row)"><LotusIcon name="more"/></Button>
  </template>
 </div>
</template>
<style>
/* AG Grid mounts framework cells outside the SFC scope. */
.tk-daily-roster .tk-grid-cell{height:100%;display:flex;align-items:center;gap:var(--lotus-space-2);min-width:0;width:100%}
.tk-daily-roster .tk-grid-cell strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.tk-daily-roster .tk-grid-cell--presence{justify-content:center}
.tk-daily-roster .tk-khoan{padding:1px 5px;border-radius:999px;background:var(--lotus-warning-soft);font-size:var(--lotus-text-xs,11px);font-weight:600;color:var(--lotus-text-strong)}
.tk-daily-roster .tk-daily-detail-button{width:26px;height:26px;min-height:26px;margin-left:auto;padding:0;color:var(--lotus-muted)}
.tk-daily-roster .tk-daily-detail-button .lotus-icon{width:16px;height:16px}
</style>
