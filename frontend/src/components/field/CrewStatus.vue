<script setup>
import {ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import {formatDate} from '../../format'
import {stateLabels,stateTone} from '../../lot-entry-model.js'
// For the đội trưởng: every tổ of the đội on a day (not sent, waiting for confirmation, confirmed), numbers that look
// wrong and lô past their due date. Tap a tổ to open its day (lotus_farm.lot_report.status).
const props=defineProps({farm:{type:String,required:true},crew:{type:String,required:true},date:String,current:String,compact:Boolean,mobile:Boolean})
const emit=defineEmits(['pick'])
const day=ref(props.date||''),data=ref(null),error=ref(''),busy=ref(false)
async function load(){
 busy.value=true;error.value=''
 try{data.value=await call('lotus_farm.lot_report.status',{farm:props.farm,crew:props.crew,date:day.value||undefined});if(!day.value)day.value=data.value.date}
 catch(e){error.value=e.message;data.value=null}
 finally{busy.value=false}
}
watch(()=>[props.farm,props.crew,day.value],load,{immediate:true})
watch(()=>props.date,v=>{if(v)day.value=v})
const tone=t=>stateTone[t.state]||(t.state?'neutral':'danger')
</script>

<template>
 <section class="crew-status" :class="{'crew-status--compact':compact}" :aria-busy="busy">
  <LotusField v-if="!compact" v-model="day" label="Ngày" type="date" :mobile="mobile"/>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <template v-if="data">
   <div class="crew-status__teams">
    <button v-for="t in data.teams" :key="t.team" type="button" class="crew-status__team" :class="['is-'+tone(t),{'is-current':t.team===current}]" @click="emit('pick',t.team)">
     <strong>{{t.team_name}}</strong>
     <span>{{t.state?stateLabels[t.state]:'Chưa có báo cáo'}}<template v-if="t.lines"> · {{t.lines}} việc</template></span>
    </button>
   </div>
   <p v-if="!compact" class="lotus-form-note">Báo cáo ngày {{formatDate(data.date)}}<template v-if="data.overdue"> · {{data.overdue}} lô quá hạn chăm sóc</template></p>
   <ul v-if="data.anomalies.length" class="crew-status__warn" role="status"><li v-for="a in data.anomalies" :key="a.block+a.kind"><b>{{a.block}}</b>: {{a.message}}</li></ul>
  </template>
 </section>
</template>

<style>
.crew-status{display:grid;gap:8px}
.crew-status__teams{display:flex;flex-wrap:wrap;gap:6px}
.crew-status__team{display:grid;gap:2px;min-width:120px;padding:6px 10px;text-align:left;font:inherit;color:inherit;border:1px solid var(--lotus-border);border-left-width:4px;border-radius:var(--lotus-radius-md);background:var(--lotus-surface);cursor:pointer}
.crew-status__team strong{font-weight:600}
.crew-status__team span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.crew-status__team.is-current{outline:2px solid var(--lotus-primary)}
.crew-status__team.is-success{border-left-color:var(--lotus-success)}
.crew-status__team.is-info{border-left-color:var(--lotus-primary)}
.crew-status__team.is-warning,.crew-status__team.is-neutral{border-left-color:var(--lotus-warning)}
.crew-status__team.is-danger{border-left-color:var(--lotus-danger)}
.crew-status__warn{margin:0;padding-left:18px;color:var(--lotus-warning);font-size:var(--lotus-text-sm)}
.crew-status:not(.crew-status--compact) .crew-status__teams{display:grid;grid-template-columns:1fr}
</style>
