<script setup>
import {computed} from 'vue'
import RibbonDot from './RibbonDot.vue'
import WeekChip from './WeekChip.vue'
import {Progress} from '../ui/progress'
import {StatusChip} from '../ui/status-chip'
import {ribbonLabel} from '../../ribbon-colors.js'
import {formatNumber} from '../../agri-format.js'
// One ribbon batch on the ribbon board (FR-031, FR-032): colour, cutting week, age, lots, and how many bunches were
// cut, bagged, harvested and are still on the plants, with harvest progress.
// batch: {code, label?, week, year?, age, lots?, cut, bagged, harvested, left, status?: waiting|due|overdue|done,
//         statusLabel?, ripe?}. status (from the ribbon board) wins over ripe (a plain "in the harvest window" flag).
const props=defineProps({batch:{type:Object,required:true},today:String,interactive:Boolean})
const emit=defineEmits(['open'])
const STATUS={waiting:{label:'Đang nuôi',tone:'info',icon:'leaf'},due:{label:'Đến tuổi thu',tone:'warning',icon:'bunch'},overdue:{label:'Quá tuổi thu',tone:'danger',icon:'alert'},done:{label:'Đã thu hết',tone:'success',icon:'check-circle'}}
const name=computed(()=>props.batch.label||ribbonLabel(props.batch.code)||props.batch.code)
const state=computed(()=>STATUS[props.batch.status]||(props.batch.ripe?STATUS.due:null))
const ripe=computed(()=>['due','overdue'].includes(props.batch.status)||(!props.batch.status&&props.batch.ripe))
const n=v=>v===null||v===undefined?'—':formatNumber(v)
</script>
<template>
 <component :is="interactive?'button':'article'" class="lotus-batch" :type="interactive?'button':undefined" :data-ripe="ripe?'true':undefined" :data-status="batch.status||undefined" :data-flag="state?'true':undefined" @click="interactive&&emit('open',batch)">
  <div class="lotus-batch__head"><RibbonDot :code="batch.code" size="lg" decorative/><div class="lotus-batch__title"><strong>{{name}}</strong><span><WeekChip v-if="batch.week" :year="batch.year||2026" :week="batch.week" :today="today"/>{{batch.age}} tuần tuổi<template v-if="batch.lots"> · {{batch.lots}} lô</template></span></div></div>
  <StatusChip v-if="state" class="lotus-batch__ripe" :label="batch.statusLabel||state.label" :tone="state.tone" :icon="state.icon" size="sm"/>
  <dl class="lotus-batch__figures"><div><dt>Cắt bắp</dt><dd>{{n(batch.cut)}}</dd></div><div><dt>Bao</dt><dd>{{n(batch.bagged)}}</dd></div><div><dt>Đã thu</dt><dd>{{n(batch.harvested)}}</dd></div><div class="lotus-batch__left"><dt>Còn trên cây</dt><dd>{{n(batch.left)}}</dd></div></dl>
  <Progress :value="batch.harvested||0" :max="batch.cut||0" label="Đã thu" :value-text="n(batch.harvested)+' / '+n(batch.cut)" :tone="batch.status==='overdue'?'danger':ripe?'warning':'success'"/>
 </component>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-batch{position:relative;display:grid;gap:12px;width:100%;min-width:0;padding:var(--lotus-card-padding);border:1px solid var(--lotus-border);border-radius:var(--lotus-card-radius);background:var(--lotus-surface);box-shadow:var(--lotus-shadow-xs);color:var(--lotus-text);font:inherit;text-align:left}
button.lotus-batch{cursor:pointer;transition:box-shadow var(--lotus-motion) var(--lotus-ease),border-color var(--lotus-motion) var(--lotus-ease)}
button.lotus-batch:hover{border-color:var(--lotus-border-strong);box-shadow:var(--lotus-shadow-md)}
button.lotus-batch:focus-visible{outline:none;box-shadow:var(--lotus-focus)}
.lotus-batch[data-ripe="true"]{border-color:var(--lotus-tone-warning-border);background:linear-gradient(180deg,var(--lotus-tone-warning-soft),var(--lotus-surface) 60%)}
.lotus-batch__head{display:flex;align-items:center;gap:10px;min-width:0}
.lotus-batch__ripe{position:absolute;top:10px;right:10px}
.lotus-batch[data-flag="true"] .lotus-batch__head{padding-right:112px}
.lotus-batch[data-status="overdue"]{border-color:var(--lotus-tone-danger-border);background:linear-gradient(180deg,var(--lotus-tone-danger-soft),var(--lotus-surface) 60%)}
.lotus-batch[data-status="done"]{opacity:.8}
.lotus-batch__title{display:grid;gap:2px;min-width:0}
.lotus-batch__title strong{overflow:hidden;color:var(--lotus-text-strong);font-size:var(--lotus-text-base);text-overflow:ellipsis;white-space:nowrap}
.lotus-batch__title span{display:flex;align-items:center;gap:6px;color:var(--lotus-muted);font-size:var(--lotus-text-sm);white-space:nowrap}
.lotus-batch__figures{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));align-items:end;gap:6px;margin:0}
.lotus-batch__figures>div{display:grid;gap:1px}
.lotus-batch__figures dt{color:var(--lotus-muted);font-size:var(--lotus-text-xs)}
.lotus-batch__figures dd{margin:0;color:var(--lotus-text);font-size:var(--lotus-text-base);font-weight:var(--lotus-weight-semibold);font-variant-numeric:tabular-nums}
.lotus-batch__left dd{color:var(--lotus-text-strong);font-weight:var(--lotus-weight-bold)}
.lotus-batches{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
</style>
