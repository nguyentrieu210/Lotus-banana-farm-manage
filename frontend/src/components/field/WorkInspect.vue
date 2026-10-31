<script setup>
import {ref,watch} from 'vue'
import {call} from '../../api'
import ModalForm from '../form/ModalForm.vue'
import WorkTicket from './WorkTicket.vue'
import {formatDate} from '../../format'
import {payShort,groups,money,amountText} from '../../field-work-model.js'
// Nghiệm thu: the khoán lô phiếu the đội trưởng approved, waiting for a Kỹ thuật vườn (never the đội's own leader).
// Opening one shows the phiếu with the inspection form (sample drawn by the system, pass mark by work group).
const props=defineProps({farm:{type:String,required:true},setup:{type:Object,required:true},mobile:Boolean})
const rows=ref([]),busy=ref(false),error=ref(''),detail=ref(null)
async function load(){
 busy.value=true;error.value=''
 try{rows.value=await call('lotus_farm.field_report.inspections_due',{farm:props.farm})}
 catch(e){error.value=e.message;rows.value=[]}
 finally{busy.value=false}
}
watch(()=>props.farm,load,{immediate:true})
</script>

<template>
 <section class="work-inspect" :aria-busy="busy">
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p class="lotus-form-note">Phiếu khoán lô đội trưởng đã duyệt, chờ nghiệm thu. Kiểm mẫu theo cách hệ thống chọn; đạt thì khoá và tính tiền cả lô, không đạt thì tổ làm lại.</p>
  <p v-if="!busy&&!rows.length" class="lotus-form-note">Không có phiếu nào chờ nghiệm thu.</p>
  <div class="work-today__cards" :class="{'work-today--mobile':mobile}">
   <button v-for="r in rows" :key="r.name" type="button" class="work-today__card is-warning work-today__main" @click="detail=r.name">
    <strong>{{r.block_code}} · {{r.work_name}}</strong>
    <span>{{r.team_name}} · {{groups[r.work_group]}} · {{payShort[r.pay_mode]}}</span>
    <span>Duyệt {{formatDate(r.approved_at)}} · {{amountText(r.area_ha)}} ha · {{amountText(r.trees)}} cây<template v-if="r.rate"> · {{money(r.rate)}}</template></span>
   </button>
  </div>
  <ModalForm :model-value="!!detail" title="Nghiệm thu phiếu" width="880px" :readonly="true" @update:model-value="v=>!v&&(detail=null)">
   <WorkTicket v-if="detail" :name="detail" :setup="setup" :mobile="mobile" @changed="load"/>
  </ModalForm>
 </section>
</template>

<style>
.work-inspect{display:grid;gap:12px;min-width:0}
</style>
