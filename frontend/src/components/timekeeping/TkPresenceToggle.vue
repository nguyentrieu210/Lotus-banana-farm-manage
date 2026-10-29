<script setup>
import {computed} from 'vue'
import {Button} from '../ui/button'
import LotusIcon from '../LotusIcon.vue'
const props=defineProps({row:{type:Object,required:true},session:{type:String,required:true},disabled:Boolean})
const emit=defineEmits(['toggle'])
const present=computed(()=>!!Number(props.row[props.session+'_present']))
const time=computed(()=>props.row[props.session+'_time']?String(props.row[props.session+'_time']).slice(11,16):'')
const label=computed(()=>props.session==='morning'?'Sáng':'Chiều')
</script>
<template>
 <Button type="button" variant="outline" size="sm" class="tk-presence-toggle" :class="{'is-present':present}" :aria-label="label+' '+row.employee_name" :aria-pressed="present" :disabled="disabled" :title="present?(time?'Máy chấm '+time:'Có mặt · xác nhận tay'):(session==='morning'?'Trước 07:00':'Sau 17:00')+' · ½ công'" @click.stop="emit('toggle',!present)">
  <LotusIcon :name="present?'tick':'plus'"/><span>{{present?(time||'Có mặt'):'Chấm'}}</span>
 </Button>
</template>
<style>
.tk-presence-toggle{display:inline-flex;align-items:center;justify-content:center;gap:var(--lotus-space-1);width:88px;height:26px;min-height:26px;padding:0 var(--lotus-space-2);font-size:var(--lotus-text-sm);font-variant-numeric:tabular-nums;white-space:nowrap;border-color:var(--lotus-border);color:var(--lotus-muted);background:var(--lotus-surface)}
.tk-presence-toggle .lotus-icon{width:13px;height:13px;flex:none}
.tk-presence-toggle.is-present{border-color:var(--lotus-primary);background:var(--lotus-primary-subtle);color:var(--lotus-primary-text);font-weight:600}
.tk-presence-toggle:disabled{opacity:.75}
</style>
