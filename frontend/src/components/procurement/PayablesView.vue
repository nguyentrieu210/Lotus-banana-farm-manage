<script setup>
// Công nợ nhà cung cấp tại ngày chốt (spec 003, FR-057, FR-058): phải trả, tạm ứng, tuổi nợ theo hạn trả, các khoản đến
// hạn trong 7 ngày, hàng đã nhận chưa có hóa đơn, từng nhà cung cấp; từ đây mở sổ chi tiết và lập phiếu chi.
import {computed,onMounted,ref,watch} from 'vue'
import LotusField from '../form/LotusField.vue'
import LotusMobileButton from '../LotusMobileButton.vue'
import SupplierStatement from './SupplierStatement.vue'
import PaymentForm from './PaymentForm.vue'
import {Button} from '../ui/button'
import {lotusMethod} from './use-procurement'
import {money,shortDate} from '../../use-signing'

const props=defineProps({company:String,mobile:Boolean,today:String,canPay:Boolean,suppliers:{type:Array,default:()=>[]},callFn:Function})
const emit=defineEmits(['open','notice','error','paid'])
const call=(name,args={})=>props.callFn?props.callFn('lotus_farm.procurement_queries.'+name,args):lotusMethod('procurement_queries',name,args)
const data=ref(null),busy=ref(false),asOf=ref(props.today||''),supplier=ref(''),statement=ref(false),paying=ref(false),chosen=ref(''),preset=ref([])
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const BUCKETS=['current','d1_30','d31_60','d61_90','d90_plus','no_due']
const aging=computed(()=>BUCKETS.map(key=>({key,label:data.value?.aging_labels?.[key]||key,amount:data.value?.aging?.[key]||0})).filter(b=>b.amount>0.5))
const overdue=computed(()=>['d1_30','d31_60','d61_90','d90_plus'].reduce((sum,key)=>sum+(data.value?.aging?.[key]||0),0))
const cards=computed(()=>data.value?[{label:'Phải trả',value:data.value.owed},{label:'Trong đó quá hạn',value:overdue.value},{label:'Đến hạn trong 7 ngày',value:data.value.due_7d},
 {label:'Tạm ứng cho NCC',value:data.value.advance},{label:'Hàng đã nhận, chưa có hóa đơn',value:data.value.unbilled_waiting??data.value.unbilled},
 // Goods sent back after their invoice: the supplier owes them until the credit note (kept apart from goods waiting).
 ...(data.value.unbilled_claims>0.5?[{label:'Hàng trả sau hóa đơn, chờ hóa đơn điều chỉnh',value:data.value.unbilled_claims}]:[])]:[])
const late=s=>['d1_30','d31_60','d61_90','d90_plus'].reduce((sum,key)=>sum+(s.aging?.[key]||0),0)
const dueRows=computed(()=>(data.value?.rows||[]).filter(r=>r.due_soon).sort((a,b)=>String(a.due_date).localeCompare(String(b.due_date))))
async function load(){
 busy.value=true;emit('error','')
 try{data.value=await call('payables',{company:props.company,as_of:asOf.value||null,supplier:supplier.value||null,page_length:500})}
 catch(e){emit('error',e.message||String(e))}finally{busy.value=false}
}
function openStatement(s){chosen.value=s.supplier;statement.value=true}
function pay(s,invoices=[]){chosen.value=s.supplier;preset.value=invoices;paying.value=true}
async function created(result){emit('notice','Đã lập phiếu chi '+result.voucher+' và gửi người ký.');emit('paid',result);await load()}
watch([asOf,supplier],load)
onMounted(load)
defineExpose({reload:load,pay})
</script>

<template>
 <section class="payables-view" aria-label="Công nợ nhà cung cấp">
  <div class="payables-view__filters">
   <LotusField v-model="asOf" :mobile="mobile" label="Ngày chốt" type="date"/>
   <LotusField v-model="supplier" :mobile="mobile" label="Nhà cung cấp" :options="suppliers" empty-option="Tất cả nhà cung cấp"/>
  </div>
  <p v-if="busy&&!data" class="lotus-form-note" role="status">Đang tải…</p>
  <template v-if="data">
   <dl class="payables-view__cards"><div v-for="card in cards" :key="card.label"><dt>{{card.label}}</dt><dd>{{money(card.value)}}</dd></div></dl>
   <p class="lotus-form-note" role="status">Số tại ngày {{shortDate(data.as_of)}} · {{data.ledger_matches?'khớp sổ cái tài khoản phải trả':'lệch sổ cái tài khoản phải trả ('+money(data.ledger_balance)+')'}}<template v-if="data.unbilled_matches!=null"> · hàng chưa có hóa đơn {{data.unbilled_matches?'khớp':'lệch'}} sổ cái 3388 + 33881 ({{money(data.unbilled_ledger)}})</template>.</p>
   <section v-if="aging.length" aria-label="Tuổi nợ">
    <h3>Tuổi nợ theo hạn trả</h3>
    <ul class="payables-view__aging"><li v-for="b in aging" :key="b.key" :class="'is-'+b.key"><span>{{b.label}}</span><b>{{money(b.amount)}}</b></li></ul>
   </section>
   <section v-if="dueRows.length" aria-label="Đến hạn trong 7 ngày">
    <h3>Đến hạn trong 7 ngày tới</h3>
    <ul class="payables-view__list"><li v-for="row in dueRows" :key="row.name"><div><strong>{{row.supplier_name}}</strong><small>{{row.bill_no||row.name}} · hạn {{shortDate(row.due_date)}}</small></div><b>{{money(row.balance)}}</b>
     <component :is="button" type="button" variant="outline" size="sm" @click="emit('open',row,'invoices')">Xem</component></li></ul>
   </section>
   <section aria-label="Theo nhà cung cấp">
    <h3>Theo nhà cung cấp</h3>
    <ul class="payables-view__list">
     <li v-for="s in data.suppliers||[]" :key="s.supplier">
      <div><strong>{{s.supplier_name}}</strong>
       <small>Phải trả {{money(s.invoiced)}}<template v-if="late(s)>0.5"> · quá hạn {{money(late(s))}}</template><template v-if="s.due_7d>0.5"> · đến hạn 7 ngày {{money(s.due_7d)}}</template><template v-if="s.advance>0.5"> · tạm ứng {{money(s.advance)}}</template><template v-if="s.unbilled>0.5"> · hàng chưa có hóa đơn {{money(s.unbilled)}}</template><template v-if="s.claim>0.5"> · hàng trả sau hóa đơn, chờ hóa đơn điều chỉnh {{money(s.claim)}}</template></small></div>
      <b>{{money(s.net)}}</b>
      <span class="payables-view__actions"><component :is="button" type="button" variant="outline" size="sm" @click="openStatement(s)">Sổ chi tiết</component>
       <component :is="button" v-if="canPay" type="button" size="sm" @click="pay(s)">Trả tiền</component></span>
     </li>
    </ul>
    <p v-if="!data.suppliers?.length" class="lotus-form-note">Không có công nợ nhà cung cấp tại ngày chốt.</p>
   </section>
  </template>
  <SupplierStatement v-model="statement" :supplier="chosen" :company="company" :as-of="asOf" :mobile="mobile" :call-fn="callFn" @open="(row,type)=>emit('open',row,type)"/>
  <PaymentForm v-model="paying" :supplier="chosen" :company="company" :preset="preset" :mobile="mobile" :today="today" :call-fn="callFn" @created="created"/>
 </section>
</template>

<style>
.payables-view{display:grid;gap:var(--lotus-space-4,16px);min-width:0}
.payables-view h3{margin:0 0 var(--lotus-space-2,8px);font-size:var(--lotus-text-md)}
.payables-view__filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:var(--lotus-space-3,12px)}
.payables-view__cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:var(--lotus-space-2,8px);margin:0}
.payables-view__cards div{padding:var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px);background:var(--lotus-surface)}
.payables-view__cards dt{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.payables-view__cards dd{margin:2px 0 0;font-weight:600}
.payables-view__aging{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:var(--lotus-space-2,8px);margin:0;padding:0;list-style:none}
.payables-view__aging li{display:grid;gap:2px;padding:var(--lotus-space-2,8px) var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px)}
.payables-view__aging li:not(.is-current):not(.is-no_due){border-color:var(--lotus-danger)}
.payables-view__aging span{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.payables-view__list{display:grid;gap:var(--lotus-space-2,8px);margin:0;padding:0;list-style:none}
.payables-view__list li{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:var(--lotus-space-3,12px);padding:var(--lotus-space-2,8px) var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px);min-width:0}
.payables-view__list div{display:grid;gap:2px;flex:1;min-width:180px}
.payables-view__list small{color:var(--lotus-muted);font-size:var(--lotus-text-sm);overflow-wrap:anywhere}
.payables-view__actions{display:flex;gap:var(--lotus-space-2,8px)}
</style>
