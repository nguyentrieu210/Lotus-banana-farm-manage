<script setup>
import {ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import {money,amountText} from '../../lot-entry-model.js'
// Tiền khoán so far in a month for the tổ the user leads or supervises: confirmed khoán-số-lượng lines and khoán lô that
// passed inspection, split by buổi (lotus_farm.lot_report.my_pay). Tạm tính: bảng lương is the final word.
const props=defineProps({farm:{type:String,required:true},mobile:Boolean})
const month=ref(new Date().toISOString().slice(0,7)),data=ref(null),error=ref(''),busy=ref(false),open=ref('')
async function load(){
 busy.value=true;error.value=''
 try{data.value=await call('lotus_farm.lot_report.my_pay',{farm:props.farm,month:month.value})}
 catch(e){error.value=e.message;data.value=null}
 finally{busy.value=false}
}
watch(()=>[props.farm,month.value],load,{immediate:true})
</script>

<template>
 <section class="my-pay" :aria-busy="busy">
  <LotusField v-model="month" label="Tháng" type="month" :mobile="mobile"/>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p class="lotus-form-note">Tiền khoán tạm tính từ số đã xác nhận, chia theo buổi. Bảng lương cuối tháng là số chính thức.</p>
  <template v-if="data">
   <p v-if="!data.teams.length" class="lotus-form-note">Tài khoản không phụ trách tổ nào.</p>
   <article v-for="t in data.teams" :key="t.team" class="my-pay__team">
    <button type="button" class="my-pay__head" :aria-expanded="open===t.team" @click="open=open===t.team?'':t.team">
     <strong>{{t.team_name}}</strong><span>{{money(t.total)}} · {{t.people.length}} người</span>
    </button>
    <ul v-if="open===t.team"><li v-for="p in t.people" :key="p.employee"><span>{{p.employee_name}}</span><small>{{amountText(p.sessions)}} buổi</small><b>{{money(p.amount)}}</b></li></ul>
   </article>
  </template>
 </section>
</template>

<style>
.my-pay{display:grid;gap:10px}
.my-pay__team{border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.my-pay__head{display:flex;justify-content:space-between;gap:8px;width:100%;padding:10px 12px;font:inherit;color:inherit;background:none;border:0;cursor:pointer;text-align:left}
.my-pay__head span{color:var(--lotus-muted)}
.my-pay__team ul{list-style:none;margin:0;padding:0 12px 10px;display:grid;gap:4px}
.my-pay__team li{display:flex;gap:8px;align-items:baseline;font-size:var(--lotus-text-sm)}
.my-pay__team li span{flex:1 1 auto}
.my-pay__team li small{color:var(--lotus-muted)}
</style>
